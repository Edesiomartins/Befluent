# BeFluent — seleção de atividades e remediação

Projeto `2bbf6b59c0cb0b5b` · implementação local de 2026-10-13.

## Problema e evidência

O teste de regressão reproduziu a seleção de uma questão já acertada em outra
`activity_key` da mesma lição. `_seen_question_fingerprints` filtrava pelo par
lição/chave; `_build_legacy_retry_activity` procurava entre irmãos da lição e,
depois, no banco da mesma faixa. Mesma faixa não prova mesmo objetivo. A variante
emprestada também podia continuar em uma posição futura da sessão. No Teaching
Engine, fingerprints anteriores eram acumulados sobretudo ao preparar retries;
o planejador não deduplicava candidatos por identidade/conteúdo.

Isso demonstra o mecanismo no checkout local. Não houve consulta à sessão ou à
versão implantada em produção; o relato do usuário não foi reconstruído em PG.

Antes: A → erro → irmão B já respondido em outra chave → reapresentação de B;
historicamente, com exclusão insuficiente, A → B → A era possível.

Agora: A / objetivo X → erro registrado + feedback → B inédita / objetivo X.
Se B não existe com qualidade e metadados seguros: continuar e revisar depois,
sem repetir A, fabricar acerto ou completar quota.

## Arquitetura e dados

- `activity_pool.py`: identidade, deduplicação, gates, ranking, lotes e histórico.
- Pool editorial em `LearningObjective.pedagogy_json.activity_pool`, vinculado a
  `ContentUnit`/`ContentSource` existentes e aprovados. Não há tabela paralela.
- `TeachingFlowSession.payload_json`: `seen_activity_ids`, fingerprints,
  `activity_exposures` (primeira entrega, snapshot privado), `selection_trace`.
- `LessonActivityAttempt`: snapshots e reservas de variantes em `feedback_json`;
  o histórico é consultado na lição inteira. Novos snapshots retêm IDs declarados.
- `Lesson.content_json.activity_pool`: candidatos legados explicitamente ligados
  ao objetivo, separados das questões planejadas e com metadados/revisão completos.
- Nenhuma coluna, tabela, dependência ou migration nova. Não houve backfill
  global. Slots legados comprovadamente submetidos/concluídos recuperam exclusões
  sem inventar data histórica de exposição.

## Selector, exposição e retomada

1. Excluir o mesmo ID e estímulos iguais/quase iguais já entregues nesta sessão.
2. Usar objetivo explícito, idioma-alvo, apoio nativo, CEFR exato e skill;
   rejeitar qualidade inadequada, unidade/fonte revogada e referências de aluno
   em pools compartilhados.
3. Priorizar inéditas, depois exposição fora do cooldown de sete dias, depois
   exposição recente. Histórico recente reduz prioridade; não proíbe SRS futuro.
4. Preferir contexto/modalidade diferente e dificuldade numérica próxima quando
   esses dados existem. Não preencher dificuldade/objetivo ausentes por inferência.
5. Respeitar fases, cotas e orçamento existentes. No fluxo de objetivo, teto 36.
   Planejador lexical mantém os parâmetros existentes de 12/36 e tetos 14/40.
   Menos candidatos elegíveis significa sessão menor; nenhuma duplicata de padding.
6. Snapshot, cursor, tentativas e ledger persistem. A retomada da atividade atual
   não conta uma exposição nova. Um slot futuro já usado como retry é pulado.

## Retry e legado

O erro e o resultado continuam registrados pelo Teaching Engine. Acerto após
feedback permanece `ERROR_REPAIRED`, não evidência de primeira tentativa. O tipo
da tentativa agora é a modalidade realmente entregue, inclusive MCQ → fill-gap.

Remediação escolhe candidato aprovado do mesmo objetivo. O fallback determinístico
de padrões do objetivo continua disponível, com identidade recalculada e exclusão
de estímulos vistos. Esgotamento produz `fallback_continue`, sem falso reparo.

O ciclo lexical antigo continua adiando revisão quando não possui metadados e
candidatos apropriados. Novos itens de objetivo com pool podem usar remediação.
Vocabulário privado de aluno não entra no pool global; futuras variantes lexicais
compartilhadas precisam de binding explícito ao item do aluno.

No legado, ausência de objetivo/metadados seguros é `legacy_objective_unknown`
no trace. Não se usa uma questão aleatória da mesma faixa como reparo. Questões
originais da lição são reservadas para suas próprias posições; só candidatos
separados do pool podem virar retry. Preparar uma oferta existente é idempotente.
Resposta que reapresente conteúdo já consumido recebe 409. Alterações são
serializadas pelo lock da lição; tentativas anteriores são preservadas.

## Geração incremental e gates

`generate_incremental_batches` recebe callback explícito de geração/revisão,
`batch_size` (default 50) e `batch_count`. Cada chamada recebe os candidatos
persistidos anteriormente. `append_objective_batch` trava/refresca o objetivo,
valida, deduplica e persiste um lote; o chamador controla commit/rollback.
Não escolhe provedor/modelo, não chama IA implicitamente e não gera 200 fillers.

Há capacidade para pools de aproximadamente 200 ou maiores por unidade/conjunto
de objetivos, mas esta mudança não fornece um catálogo editorial de 200 itens.
Conteúdo gerado só fica utilizável após aprovação editorial/provenance e gates.

Gates automáticos: metadados obrigatórios, idioma/nativo/CEFR válidos, guards
existentes de mistura de idiomas, objetivo/skill/unidade/fonte compatíveis, tipo
suportado, resposta presente e avaliável, opções únicas, um gabarito, variantes
aceitas não usadas como distratores, tokens de word-order coerentes e dedup.
`answer` é normalizado para `canonical_answer`, sem inventar gabarito.

Idioma arbitrário, plausibilidade pedagógica de distratores, ausência completa de
ambiguidade e adequação CEFR/skill/unidade exigem revisão editorial registrada.
Os gates determinísticos não certificam essas propriedades semanticamente.
`language_invalid`, native provenance e idioma autoritativo são conferidos após
o lock da lição. Conteúdo incompatível requer regeneração pelo fluxo existente.

Dedup: normalização Unicode/caixa/espaços/pontuação/prefixos, gabarito e opções
ordenadas; mesmo ID; estímulos de atividades expositivas; similaridade conservadora
de prompts longos com mesmos gabarito/opções; troca de um token em construção
curta equivalente. Não há embeddings ou infraestrutura nova. Não cobre toda
paráfrase semântica: diversidade conceitual ainda depende de revisão editorial.

## Concorrência, telemetria e segurança

Writers do pool e refresh do seed usam o mesmo `FOR UPDATE` com
`populate_existing=True`, evitando preservar uma cópia antiga do JSON. Locks de
flow e lição mantêm seleção/reserva/tentativa na transação existente.

Trace de seleção contém IDs, objetivo, contagens, exclusões, razão e fallback.
Logging de remediação em DEBUG, sem respostas/prompts do aluno. Snapshots completos
ficam privados no banco. Não há nova API pública de escrita editorial.

## Arquivos

Criados: `backend/app/services/activity_pool.py`,
`backend/tests/test_activity_pool.py`, este relatório.

Alterados: `backend/app/api/lessons.py`,
`backend/app/schemas/__init__.py`,
`backend/app/services/{lesson_attempts,objective_seed,session_engine,teaching_flow,teaching_slice}.py`,
`backend/tests/{test_lesson_activity_attempts,test_retry_antirrepeticao}.py`,
`frontend/components/lesson-modes.tsx`, `frontend/tests/vocabulary-cycle.test.tsx`.

Dependência inevitável de frontend: o ciclo standalone precisa enviar
`remediation_id` para distinguir retry de reenvio da resposta original no mesmo
cursor. Campo opcional no schema; endpoint verifica cursor/flow/remediação.
Envio antigo durante remediação recebe 409, sem ser reinterpretado como retry.
Mudança de três linhas no corpo da requisição, sem alterar layout.

Fixtures antigas que tratavam irmãos planejados como variantes passaram a
declarar pool editorial separado. A fixture FR agora pertence a um perfil FR;
o teste de pool insuficiente usa um idioma válido, sem simular `zz` como conteúdo
aceitável. Não enfraquecemos o guard de idioma para manter fixtures inconsistentes.

## Validação

Rodada focal ampliada: **239 passed, 0 failed, 0 skipped, 7 warnings** (105,33 s).
Após as últimas proteções de ID, gabarito público e ledger legado, núcleo final:
**58 passed, 0 failed, 0 skipped, 3 warnings** (23,98 s), incluindo o contrato
legado de `canonical_answer` e alternativas tipadas.
Frontend geral final: **335 passed, 0 failed em 39 arquivos**, com avisos jsdom
de áudio não implementado e React `act(...)`. Typecheck e ESLint dos dois arquivos
alterados passaram. O teste novo inicialmente consultava um radio onde a UI usa
button; corrigida a consulta do teste, sem alterar a UI.
Suíte geral backend: **1782 passed, 0 failed, 5 skipped, 40 warnings** (886,80 s).
Os cinco skips são testes PostgreSQL: dois de completion paralelo, um de exposição
paralela e dois de reset/isolamento de schema; `POSTGRES_TEST_URL` não configurada.
Avisos de depreciação do Alembic (`path_separator`).
Validação complementar após os últimos ajustes de contrato/compatibilidade:
**132 passed, 0 failed, 0 skipped, 3 warnings** (63,68 s), incluindo HTTP de
erro A → B inédita → retry correto, reenvio original recusado e gabarito privado.
`git diff --check` e compileall passaram. Revisão independente: achados anteriores
resolvidos, sem bloqueadores restantes naquela revisão; PG concorrente pendente.
30 casos novos: 26 no módulo de pool (incluindo parametrização), três no legado
e um no frontend. A suíte geral não foi rerodada inteira após o último ajuste
do contrato standalone; a rodada complementar cobre esse diff final explicitamente.

Comandos executados a partir de `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_activity_pool.py tests/test_lesson_activity_attempts.py tests/test_retry_antirrepeticao.py -q -o addopts='' --junitxml=tmp/activity-core-final.xml
.\.venv\Scripts\python.exe -m pytest -q -o addopts='' --junitxml=tmp/activity-full-final.xml
```

`TestClient` travou no sandbox em `socketpair()` do asyncio antes de entrar na
aplicação; o traceback confirmou o bloqueio. As rodadas HTTP foram executadas
fora do sandbox, com SQLite/testes temporários. Nenhuma URL de PG foi configurada.
Uma rodada geral intermediária foi interrompida para incorporar achados da revisão;
não foi contada como suíte concluída. A rodada geral final foi complementada pela
rodada focal após o ajuste de compatibilidade do ledger.

Novas regressões cobrem erro/retry, mesmo objetivo, ID/conteúdo vistos, acerto em
outra chave, retomada, continuação, inédita/antiga/recente, pool insuficiente,
filtros de idioma/CEFR/qualidade, dedup literal/near/batches, rollback, seed,
modalidade persistida, aliases de gabarito, distractor ambíguo, tokens inválidos,
referências privadas de aluno e `language_invalid`. Artefatos JUnit em `backend/tmp`.

## Deploy e limites

Não houve commit, push ou deploy; nenhuma operação de produção foi executada.
Não há migration a aplicar nesta entrega. Após revisão e autorização explícita
do proprietário para cada deploy, publicar backend primeiro e depois frontend.
Não habilitar pools editoriais novos no standalone antes de o frontend que envia
`remediation_id` estar publicado. Não houve E2E autenticado no navegador.

PG de produção é o único disponível: locks, concorrência e comportamento real
continuam sem ensaio PostgreSQL. Não executar migrations/importação editorial em
produção automaticamente. O pool pode ser expandido localmente por lotes revisados;
aplicação editorial em produção exige autorização própria.

JSON é uma decisão proporcional para pools de centenas de candidatos. Histórico
consulta flows do mesmo perfil e dedup usa comparação local; volumes grandes
podem justificar tabelas/indexação depois. Editorial precisa fornecer IDs/objetivos,
contextos, modalidades, dificuldade, revisão e provenance verdadeiros. Legado sem
esses dados continuará com menos retries; essa redução é deliberada e segura.
