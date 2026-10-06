# FR B1: reuso legado e reparo limitado

Data: 2026-10-06. Rodada `2bbf6b59c0cb0b5b`; continuação de `2bbf6b59c0b5b`.

## Evidência de produção

Resultado PostgreSQL fornecido pelo usuário, sem nova consulta ou escrita de produção por Codex: exatamente uma correspondência, Lesson `f2ab192f-36ef-42d0-b7aa-1038c8d230d2`, status active, alvo fr/B1, usuário atual pt-BR, snapshot nativo SQL NULL, provider/content_origin openrouter, modelo `nvidia/nemotron-3.5-lightning`, título `Logical Structure for Opinion & Justification in French`, title/explanation contaminados. Nenhum ContentUnit relacionado. Bloco grammar/pending/B1, tópico `Opinião e justificativa — estruturas-chave`. Seu ID não foi fornecido; o dry-run de reparo descobre esse ID e exige que ele seja informado explicitamente para escrever.

O SQL `payload->>'native_language'` retorna NULL tanto para chave ausente quanto para JSON null. O código anterior reproduz o bypass quando a chave está ausente; null explícito já causava mismatch com pt-BR. A correção cobre os dois casos. O resultado comprova origem e persistência; a data exata de geração não foi inspecionada nesta rodada.

## Causa e caminho exato

`POST /api/v1/curriculum/block/{block_id}/start` → `curriculum.start_block` → `progression.build_block_lesson` → encontra `block.lesson_ref` → carrega Lesson → chama `ensure_stored_content_language` → retorna content_json sem regeneração. O guard tratava snapshot ausente como legado estático PT aceito para pt-BR, mesmo quando provider=openrouter. Seu detector finito de quatro prefixos não conhecia `Logic: In French`; o título também não era validado na retomada. `GET /api/v1/lessons/{lesson_id}` usava o mesmo guard limitado. Na geração, `_english_targets` reconhecia clones ingleses do banco estático, não este título novo de IA.

## Correção

- `editorial_validation.has_known_incompatible_english` compartilha marcadores finitos do incidente e clones/prefixos ingleses já conhecidos entre geração e entrega. Verifica campos pedagógicos, incluindo title/logic_title/explanation e apoio separado; não lê metadata de provider/model como texto do aluno. Preserva inglês como alvo ou apoio nativo legítimo, sem permitir clone inglês como título/texto-alvo de outro curso. Não é detector universal de idioma ou certificado de CEFR.
- `valid_generated_lesson` também recusa target_language conflitante e snapshot nativo conflitante quando o nativo foi informado. OpenRouter já usa esse validator; o envelope aplica o mesmo bloqueio antes de entrega/persistência, inclusive nos caminhos curados/mock. Provedor/modelos não foram trocados.
- `ensure_stored_content_language` verifica target_language/language_code, metadados inválidos, snapshot nativo, markers e status language_invalid. Lições dinâmicas ou com par declarado sem snapshot não são certificadas por serem antigas. Fonte estática declarada mock/curated e revisão interna explicitamente provider=srs + mode=review + source=srs_queue conservam compatibilidade com apoio PT somente para pt-BR, sem backfill. Não basta declarar provider=srs em gramática. Wrappers legados vazios e EN/PT sem par/provenance declarados conservam caminho limitado depois das verificações conhecidas; não são reetiquetados como lições modernas.
- Reuso do cronograma e GET da lição conferem o título da tabela separadamente do JSON e o idioma real da matrícula. Antes de invalidar por script, a Lesson contaminada recebe 409 e nenhum registro é alterado pela tentativa de entrega.
- Depois do reparo revisado, somente language_invalid + bloco pending permite tentativa de substituição. O bloco é bloqueado/refrescado; se outra requisição já instalou uma substituta, ela é reutilizada. A referência antiga fica intacta até sucesso da geração e troca atômica no mesmo fluxo. Falha de IA deixa referência e história intactas.
- Concluir essa lição ou seu bloco não registra progresso enquanto o conteúdo está incompatível. Abandonar uma lição invalidada não sobrescreve sua quarentena; a leitura da Lesson é bloqueada/refrescada antes dessa verificação para evitar sobrescrita por estado anterior ao reparo. Não houve alteração da lógica de Session Builder/mastery/entitlement/speech/pricing.

## Reparo preservando histórico

`backend/scripts/repair_fr_b1_incident.py` tem o lesson_id confirmado fixo. Por padrão, executa somente SELECT em transação READ ONLY no PostgreSQL ou SQLite mode=ro, mostrando lesson_id, bloco/day_id, status/ref atuais, respostas históricas contadas, ação proposta e resultado esperado. Não chama IA.

A escrita exige `--apply --block-id ID_EXATO_DO_DRY_RUN`. Antes de escrever, o script verifica FR/pt-BR/B1, provider/origin/model/título/contaminação confirmados, ausência de ContentUnit, um único vínculo, proprietário correspondente, currículo ativo, dia aberto, bloco grammar/pending com tópico confirmado e sem score. Bloqueia Lesson, matrícula, idioma, usuário, bloco, dia, semana e currículo no PostgreSQL, com lock_timeout 2 s e statement_timeout 15 s. Mudança de pré-condição recusa o reparo inteiro.

O script escreve **somente `Lesson.status = language_invalid`**. Mantém curriculum_block.lesson_ref, payload, título, objective, sessões, respostas, matrícula, currículo e progresso. Não faz DELETE ou reescrita editorial histórica. Repetir antes da substituição é idempotente. Se a lição/bloco já foi concluída, mudou de proprietário/tema/nativo, adquiriu outra referência ou já foi substituída, o script recusa aplicar sem nova revisão.

Na próxima abertura normal do bloco, o backend gera uma Lesson compatível, persiste outro ID e atualiza lesson_ref na mesma transação. A Lesson antiga e suas tentativas permanecem. O script não escolhe provedor, não fecha a sessão antiga e não fabrica evidência/progresso. As rotas de conteúdo continuam bloqueando a lição incompatível; o armazenamento histórico é preservado, sem prometer que a UI atual exibirá seu conteúdo inglês ou boletim.

`--apply --rollback` ensaia a escrita na mesma transação e faz rollback explícito. Exceções/timeout também abortam sem commit. Após commit, não religar automaticamente um conteúdo contaminado como ativo: o histórico e os IDs continuam preservados, mas qualquer reversão posterior exige revisão do estado atual e backup. Não há rollback destrutivo automático de progresso.

## Instrução para produção após revisão

Pré-condição: revisar a pendência da suíte geral registrada abaixo antes de liberar o backend; esta correção instalada em uma atualização autorizada, script disponível no mesmo ambiente com DATABASE_URL já configurada e backup verificado. Não aplicar o script com o backend antigo: ele não conhece o fluxo seguro de substituição. Nada foi publicado nesta rodada.

No diretório `backend` ou na raiz equivalente do container backend:

```sh
python scripts/repair_fr_b1_incident.py
```

Revisar o JSON. A ação deve ser `invalidate_lesson_pending_regeneration`; conferir lesson_id fixo, um bloco pending/grammar/B1 e o tópico confirmado. Copiar o ID do bloco dessa saída, substituindo `UUID_EXATO_DO_DRY_RUN` abaixo pelo UUID real (não usar o texto placeholder).

Ensaio transacional, se aprovado:

```sh
python scripts/repair_fr_b1_incident.py --apply --rollback --block-id UUID_EXATO_DO_DRY_RUN
```

Esperado: `write_performed=true`, `transaction=rolled_back`, `write_committed=false`. O dry-run seguinte ainda mostra active/ref antiga.

Aplicação somente depois de revisar/autorizar a escrita:

```sh
python scripts/repair_fr_b1_incident.py --apply --block-id UUID_EXATO_DO_DRY_RUN
```

Esperado: `transaction=committed`, `write_committed=true`, Lesson antiga language_invalid, bloco ainda pending/ref antiga. Repetir o dry-run com `--block-id` antes de abrir a jornada deve mostrar already_applied. Abrir normalmente Descobrir/Gramática; conferir novo lesson_id, target fr/native pt-BR, explicação francesa e apoio português separados, ausência dos markers ingleses conhecidos e lesson_ref novo. Se o provedor falhar, o bloco mantém a referência antiga, continua pending e não entrega o conteúdo contaminado.

## Validação e arquivos

- Os dois xfail viraram testes normais. Red observado: 10 falhas do guard/reuso/generation antes da implementação; todos esses casos passaram depois.
- Focal final com incidente, integridade editorial e native: **122 passed, 4 warnings**, exit 0, 88,23 s. Inclui arquivo real de SQLite para CLI default/dry-run/rollback/commit, recusa de flag/ID/precondições, igualdade de todas as outras tabelas e campos, respostas preservadas, substituição FR/PT, falha de geração, identidades desatualizadas, revisão interna SRS e contaminação no campo objective. Warnings de configuração Alembic.
- A primeira tentativa da suíte completa foi interrompida após revelar a regressão da revisão interna SRS sem snapshot; não representa aprovação. Corrigida a compatibilidade restrita à origem interna existente; teste original de conclusão com fila vazia e dois novos testes de allow/refuse passaram (3 passed). A suíte completa foi reiniciada do zero com fail-fast.
- A segunda execução parou com 1 failed e 364 passed por uma fixture nova que usava matrícula inexistente no teste de outro proprietário. A fixture agora cria uma matrícula real de outro usuário e mantém a integridade referencial; os cinco casos de pré-condições passaram depois. Uma execução posterior foi interrompida para incluir a regressão objective; nenhuma execução interrompida representa aprovação.
- Revisão independente final sem bloqueadores restantes, somente leitura. Simulação de identidade antiga em SQLite não valida concorrência PostgreSQL real. Não executados reparo no PostgreSQL, provedor real ou jornada autenticada de produção.
- Suíte backend geral com fail-fast: **1 failed, 1559 passed, 38 warnings**, exit 1, 1076,11 s. Falhou `test_vocabulary_learning.py::test_post_lapse_epoch_requires_four_new_correct_signals`, ao esperar recognition após lapso. A suíte geral **não está aprovada**.
- Checagem limitada da falha: esse teste passou isolado (1 passed); o módulo completo deu 1 failed, 13 passed, agora em `test_replaying_processed_lapse_preserves_remastered_state`. Instrumentação temporária somente de diagnóstico também deu 1 failed, 13 passed e mostrou tentativas corretas com evaluated_at igual ao started_at do lapso, excluídas pela comparação estrita `>` em memory_engine. Teaching Engine, memory_engine, vocabulary_learning e esse teste não têm diff. Não corrigidos ou mascarados: mastery foi explicitamente excluído pelo usuário. Isso não é certificação de baseline nem aprovação da suíte; registrar a pendência e tratar em rodada autorizada.
- Os arquivos restantes após a parada foram executados: `test_vocabulary_review_cycle.py` + `test_vocabulary_selection.py`, **10 passed**, exit 0, 4,97 s. Não somar resultados de reruns com testes sobrepostos como se fossem uma suíte verde.
- Alterados: `backend/app/services/editorial_validation.py`, `language_policy.py`, `progression.py`, `backend/app/api/lessons.py`. Novos nesta correção: script de reparo, `test_fr_b1_legacy_reuse.py`, `test_fr_b1_incident_repair.py`, este relatório e plano. O teste/diagnóstico/SQL/relatório da rodada anterior permanecem locais e untracked; não confundir com fontes de produção.
- Sem frontend, modelo, migration 0016, commit, push, deploy ou escrita de produção.
- Segundo Cérebro: nota existente `02_DECISOES/DECISAO_BEFLUENT_LINGUA_NATIVA.md` atualizada pela ponte protegida e verificada por leitura, seção `2bbf6b59c0cb0b5b`. Inclui evidência PostgreSQL fornecida, causa/correção, reparo, resultados reais e pendência lexical; nenhuma aprovação de suíte geral ou produção foi registrada.

Comandos de validação executados no diretório `backend`:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_fr_b1_incident_diagnostic.py tests/test_fr_b1_legacy_reuse.py tests/test_fr_b1_incident_repair.py tests/test_native_language.py tests/test_editorial_integrity.py --tb=short
.venv/Scripts/python.exe -m pytest -x --tb=short
```
