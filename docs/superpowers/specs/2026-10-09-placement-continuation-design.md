# Placement continuation / evidence carry-forward — desenho para revisão

Data: 2026-10-09. Segundo Cérebro: `2bbf6b59c0cb0b5b`.
Estado: **desenho aprovado pelo usuário em 2026-10-09; implementação não iniciada**.
Contrato: **NOT READY FOR FRONTEND CONTRACT** até concluir os gates de implementação.

## Intenção e limites

Retomar coleta aberta e complementar assessments incompletos sem reapresentar
itens vistos, perder evidências válidas ou fabricar suficiência. Escopo: backend,
engine, persistência, contrato API e testes. Sem frontend, commit, push, deploy,
produção, reset executado ou limpeza de exposure.

O relato de produção é contexto fornecido pelo usuário. Não houve acesso ao
banco de produção nesta tarefa; os achados abaixo foram verificados no checkout.

## Auditoria confirmada

| Componente | Comportamento atual | Implicação |
| --- | --- | --- |
| `create_test` | Lock em User; retoma pending/in_progress do idioma, excluindo checkpoints | A retomada básica já existe; faltam compatibilidade, expiração e descoberta de continuation |
| `/current` | Só retorna pending/in_progress | Incomplete encerrado não é descoberto como complementável |
| `next-item` | Retoma delivery aberto válido; depois coverage-first | Preservar ordem e identidade da delivery |
| `_state_from` / `_records` | Estado reconstruído das respostas; keys de exposure quando existem | Há base para deduplicação, mas fallback atual não prova elegibilidade histórica |
| `PlacementItemExposure` | Keys semânticas, hash do grading contract, versão, skill/CEFR, exposure e timestamps | Não armazena resposta, score e avaliação completos |
| `PlacementTestAnswer` | Resposta/produção, score, avaliador, feedback e data | É a fonte de evidência; exposure sozinho não a substitui |
| Speaking | Transcript e metadados do áudio persistidos; arquivo temporário removido | Carry usa transcript/provenance; nunca arquivo temporário ou avaliação acústica |
| `production_result` | Writing/speaking provisórios, `eligible_for_overall=False` | Carry preserva essa restrição; quotas completas não implicam global |
| Reset normal | Apaga tests/answers/sections/deliveries e preserva exposures | Evidência já apagada não é recuperável a partir do ledger |
| Reset técnico | Já existe `--clear-placement-exposure`, com guarda de ambiente/database | Reutilizar a guarda e documentar QA total; não acrescentar flag duplicada |

Fontes: `backend/app/api/placement_tests.py`, `backend/app/models/__init__.py`,
`backend/app/services/placement_exposure.py`, `placement_delivery.py`,
`placement_production.py`, `placement_engine.py` e
`backend/scripts/reset_test_user_learning.py`.

## Alternativas consideradas

1. **Nova sessão vinculada + snapshots em result_json — recomendada.** Preserva
   assessments encerrados; reaproveita JSON e locks existentes; dispensa copiar
   `PlacementTestAnswer` e criar exposições artificiais. Exige um serviço único
   de evidências efetivas para todas as leituras/cálculos.
2. Reabrir o mesmo assessment encerrado. Evita vínculo novo, mas mistura resultado
   histórico, retry de complete e estado aplicado ao perfil/currículo. Rejeitada.
3. Ledger dedicado de assessment evidence com migration aditiva. Facilita
   preservação independente do reset, mas amplia retenção e altera a semântica
   atual de apagar dados pedagógicos. Não necessário para esta versão, cujo
   reset normal explicitamente invalida e apaga evidência.

## Active / continuation / new

`POST /api/v1/placement-tests` mantém os campos existentes e recebe
`start_mode: "auto" | "new"`, padrão `auto`.

Sob lock User e locks dos tests relevantes, em ordem consistente:

1. Em `auto`, retomar o assessment ativo mais recente e compatível no mesmo
   idioma. Preservar ID, respostas, produções, selection_trace e deliveries.
2. Sem ativo compatível, buscar o **último** assessment normal do idioma. Se
   encerrado incomplete, compatível, não expirado, com pelo menos uma evidência
   elegível e orçamento restante, criar filho continuation. Não agregar tests
   arbitrários nem ignorar um assessment posterior completo.
3. Sem fonte válida, criar `new` conforme gates de retake existentes. Motivos
   de rejeição são explícitos; ausência de evidência nunca é compensada por seen.
4. `new` não faz carry e respeita cooldown/policy atuais. Se houver assessment
   ativo utilizável, devolver conflito `placement_active_exists`: esse modo
   não abandona silenciosamente uma coleta em andamento. Retry de auto retorna
   o mesmo filho ativo, inclusive sob concorrência PostgreSQL.

Continuation persiste em `result_json.continuation`:

```json
{
  "mode": "continuation",
  "continued_from_test_id": "source-test-id",
  "root_assessment_id": "root-test-id",
  "continuation_sequence": 1,
  "policy_version": "placement-evidence-carry-v1",
  "validity_days": 7,
  "created_at": "ISO-UTC"
}
```

Childs subsequentes usam IDs originais das evidências, a mesma raiz e sequência
incremental. Nunca recebem nova data de coleta para evidência herdada.

Estados públicos ficam em `placement_resume.status`, separados de
`PlacementTest.status` e de `assessment_status`: `active`, `continuable`,
`incomplete`, `completed`, `expired`, `superseded`. `incomplete` significa
encerrado sem continuation permitida; `continuable` informa incomplete elegível.
`superseded` é derivado da existência de descendente vigente. A descoberta é
read-only; não reescreve results históricos. Writers rejeitam expired/superseded
antes de aceitar resposta, next-item ou complete. Checkpoints ficam fora.

Reason allowlist v1: `bank_freshness_exhausted`, `bank_exhausted`, `user_skipped`,
`microphone_unavailable`, `production_unavailable`, `hard_technical_failure`,
`user_interruption`, `technical_failure`. Motivos desconhecidos não recebem
permissão automática. `maximum_reached` não reinicia orçamento em continuation.

## Policy e janela

Proposta: `placement-evidence-carry-v1`, configuração
`PLACEMENT_EVIDENCE_VALIDITY_DAYS=7`, inteiro entre 1 e 30. **Sete dias é uma
escolha operacional conservadora proposta, sem base psicométrica alegada**;
independe de exposure cooldown. Configuração e versão são persistidas na raiz.

Validade: `collected_at <= now < collected_at + validity_days`, em UTC; timestamp
futuro/malformado é rejeitado. Raiz expira em `root.started_at + validity_days`;
continuations não renovam esse prazo. Uma alteração de configuração não prolonga
evidências existentes: usa-se o menor prazo entre policy persistida e atual.
Compatibilidade exige coverage v3, mesma policy de estimativa/exposure e versões
de avaliação suportadas explicitamente; nunca comparar só um nome genérico.

Ativo expirado continua disponível para leitura histórica, mas não para coleta.
O fluxo pode iniciar new respeitando retake; exposure permanece. Expiração ou
revogação durante a coleta é revalidada em operações dependentes de evidência.
Results já finalizados permanecem snapshots históricos, sem recálculo em GET.

## Fonte e snapshot imutável

Novo serviço `placement_continuation.py` centraliza validação, seleção da fonte,
snapshots, deduplicação e contexto. `placement_evidence.py` expõe evidências
efetivas a coverage, adaptação, candidate/confirmation, resultado e planning.

Novas respostas recebem snapshot versionado no `feedback_json`, na mesma
transação da resposta. O manifest do filho guarda snapshots e referências
originais em `result_json`; **não cria respostas/deliveries/exposures fictícias**.

Snapshot mínimo: evidence_id original, source_test_id/root, user/language,
skill/CEFR/item_type, collected_at, policy bundle, item version, grading contract,
keys semânticas, elegibilidade e freshness originais explícitas, score finito,
response_time_ms, collection_phase, origem current/carried e produção/avaliação
quando aplicável. Hash de integridade para detectar alterações de snapshot,
sem alegar proteção criptográfica contra um administrador do banco.

O manifest privado pode conter resposta/transcript; o payload público só expõe
contadores, IDs de proveniência e motivos. Não devolver gabarito, rubric privada,
texto de outras contas, keys internas ou caminho de áudio temporário.

Históricos intactos podem ser adaptados no POST somente quando answer original
e exposure snapshot original estão presentes, metadata explícita comprova
freshness/eligibilidade, keys/skill/CEFR/version conferem, grading contract
persistido confere com o item atual e provenance de avaliação é suficiente.
Salvar o snapshot apenas no filho; não alterar a fonte encerrada. Se houver
fallback legado, missing snapshot ou contrato editorial divergente, rejeitar
como `insufficient_historical_provenance`/`item_contract_changed`. Nenhum backfill
silencioso, independência por ID ou reconstrução de respostas após reset.

## Elegibilidade por skill

Todas exigem mesmo usuário/idioma, fonte compatível, validade temporal,
provenance completa, identidade semântica íntegra, não invalidação e nenhuma
reutilização/revelação de feedback invalidante. Revalidar flags de revogação e
feedback no banco original; alteração posterior invalida carry em coleta.

| Skill | Evidência aceita | Evidência rejeitada |
| --- | --- | --- |
| VG / R / L | Resposta fresh originalmente elegível, score válido e keys imutáveis; independência pela mesma relação semântica do engine | Reused, clone, exposure sem answer, revealed, snapshot ausente, score inválido |
| Writing | Texto persistido, avaliação válida, provenance/rubric version/score/reportado/aceito preservados | Skip, texto ausente, avaliação inválida/indisponível, versão não suportada |
| Speaking | Transcript persistido, STT real/provenance e avaliação linguística válida | STT mock, skip, transcript vazio, avaliação inválida; nenhum uso de arquivo apagado |

Writing/speaking continuam provisional e não são reavaliados automaticamente.
Produções enviadas mas sem avaliação válida podem contar como coleta current
sob o contrato atual, mas não se tornam carry elegível. Essa diferença é pública.

Deduplicar primeiro por evidence_id original e depois por grupos conectados de
keys semânticas (exact/prompt/passage/audio/family), incluindo colisões que unem
grupos antes separados. Não escolher duas evidências de um grupo porque a
skill/faixa/ID mudou. Desempate determinístico por collected_at e evidence_id,
sem selecionar pelo melhor score. Duplicatas aparecem em rejected. Snapshot
herdado continua apontando para answer original; não para o snapshot do filho.

## Contagem, selector e orçamento

Quotas permanecem VG6/R4/L4/W1/S1. `skills.*.completed` é elegível e independente.
No topo, `completed_current` preserva a contagem bruta de atividades realmente
concluídas nesta sessão; `completed_carried` conta apenas carry aceito e único;
`completed_total` é a soma, para orçamento 20. Por skill, current/carried são os
componentes elegíveis de completed. Publicar ainda `activities_completed_current`
e `eligible_completed_total` para distinguir bruto de suporte válido.
Skip e delivery aberto não contam como atividade concluída.

Manifest é limitado a evidências necessárias para quotas e confirmação dentro
do limite 20. Não pode descartar evidência contraditória apenas para melhorar
candidate/global. Se a fonte ultrapassar o limite ou faltar provenance da fase,
não escolher um subconjunto favorável: tornar a fonte incompatível com esta v1.
Fases adaptive herdadas contam no teto quatro e não são renovadas por filho.

Selector usa a união deduplicada current + carried, antes de escolher déficit.
Mantém retomada de delivery válido; depois ratio completed/required das
objetivas, produções faltantes e, por último, confirmação/adaptividade. Carry
não é reapresentado e não gera novo exposure. Ledger continua bloqueando esses
itens e clones. Exceptions/skips da fonte não são herdados como resolução dos
déficits do filho: nele deve haver disponibilidade nova ou motivo atual explícito.

Exemplo obrigatório: VG6/R3/L2/W1/S0 herdados = 12 atividades válidas;
faltam R1/L2/S1 = 4, portanto remaining_mandatory=4. Não selecionar VG ou W
durante quotas. Após satisfazê-las, uma objetiva dessas skills só poderá ser
selecionada se a policy existente exigir confirmação e houver conteúdo fresh.

## Contrato aditivo

Reutilizar `POST /placement-tests`, `GET /current`, `GET /{id}` e result;
não criar endpoint duplicado. `/current` preserva `test` e acrescenta discovery
read-only `placement_resume`, inclusive quando `test=null` e fonte é continuable.
Nenhum GET cria continuation, snapshot ou marca expiração.

```json
{
  "placement_resume": {
    "mode": "continuation",
    "status": "continuable",
    "test_id": "source-or-active-test-id",
    "carried_evidence": true,
    "completed_total": 12,
    "remaining_mandatory": 4,
    "missing_skills": ["reading", "listening", "speaking"],
    "open_delivery": null
  },
  "assessment_coverage": {
    "minimum_total": 16,
    "maximum_total": 20,
    "completed_current": 0,
    "completed_carried": 12,
    "completed_total": 12,
    "mandatory_complete": false,
    "skills": {
      "reading": {
        "required": 4,
        "completed_current": 0,
        "completed_carried": 3,
        "completed": 3,
        "deficit": 1,
        "satisfied": false
      }
    }
  },
  "evidence_carry_forward": {
    "policy_version": "placement-evidence-carry-v1",
    "validity_days": 7,
    "source_test_ids": ["source-test-id"],
    "carried_total": 12,
    "by_skill": {"vocabulary_grammar": 6, "reading": 3, "listening": 2, "writing": 1, "speaking": 0},
    "rejected": [{"evidence_id": "original-answer-id", "reason": "feedback_revealed"}]
  }
}
```

Exemplo de formato, não medição da conta real; a API real retorna as cinco skills.
Discovery de continuation fornece o ID fonte, sem criar um filho em GET;
POST retorna o ID filho e seu contexto. Open delivery publica ID/item/expiração,
sem resposta correta. Históricos continuam com result_schema_version existente;
campos aditivos não reinterpretam planning aplicado.

## Candidate / global / planning / downstream

Uma única coleção de evidências efetivas alimenta `_state_from`, quotas,
independent_answers, candidate, confirmation, skill_results e build_result.
Cada registro tem evidence_origin e source id. Nenhuma estimativa usa contagem
bruta ou ledger como evidência. `adjust_result` também usa a união, para não
apagar carry ao contar somente answers atuais.

Planning trace identifica current/carried por skill, IDs fonte, policy, janela,
assessment_status e contexto de continuation, inclusive no caminho
retained_prior_planning. Não recalcular planning aplicado de resultados antigos.
Completion continua idempotente e serializada, preservando o guard downstream
de perfil/currículo. Só o filho aplica o novo resultado, uma vez.

O teste de overall sufficient verifica a função existente com cinco resultados
elegíveis; integração real com produções provisórias deve continuar global nulo.
Tornar writing/speaking eligible_for_overall seria mudança de policy fora deste
pedido, não uma maneira legítima de fazer passar o teste 19.

## Reset

**Decisão proposta: reset normal invalida/apaga assessment evidence, preserva
exposure**, mantendo o comportamento atual. Acrescentar no dry-run/report
`assessment_evidence_policy=discard_and_invalidate`, IDs/contagens afetados e
postcondições de ausência de carry. Não preservar clandestinamente textos ou
transcripts em exposure. O retorno para onboarding continua igual.

QA total usa a flag existente `--clear-placement-exposure`; também apaga carry
junto dos tests. Guarda deve exigir ambiente explicitamente test/development
(não apenas diferente da string production) e database `_test`/`_dev` ou SQLite
efêmero. Não permitir um parâmetro environment ocultar configuração efetiva de
produção; ambos devem ser não produtivos. Nenhum reset será executado aqui.

Se o requisito mudar para preservar evidência após reset, será necessária uma
decisão de retenção separada; a alternativa ledger dedicado terá de ser revista.
Os dados apagados pelo reset anterior não são restaurados por esta implementação.

## Migration / arquivos previstos

Sem migration proposta: snapshots em feedback_json/result_json; ancestry em
result_json; unicidade lógica protegida pelo lock User que já serializa todas
as criações. Testes PostgreSQL são obrigatórios para provar esse desenho.
Nenhuma FK/constraint existente é removida e nenhuma resposta é copiada.

Arquivos de aplicação previstos: novos serviços `placement_continuation.py` e
`placement_evidence.py`; `placement_tests.py`, `placement_coverage.py`,
`placement_engine.py` (somente provenance), `placement_planning.py` se necessário,
`schemas/__init__.py`, `core/config.py`, `reset_test_user_learning.py` e docs.
Testes: continuation policy/API/PostgreSQL, coverage/exposure/planning/reset e
fixtures que comprovem provenance real. Não mudar frontend ou providers.

## Matriz de validação a executar após aprovação

| Casos do pedido | Evidência de aceitação |
| --- | --- |
| 1–2 | Dez respostas, mesmo test_id; mesmo delivery_id/item_id no retry e retomada |
| 3–6 | VG6/R3/L2/W1/S0, quatro déficits; selector R/L/S; somas current+carried exatas |
| 7–12 | Duplicação, clone conectado, reused, revealed, idioma/policy/data incompatíveis rejeitados com motivo |
| 13–16 | Writing e speaking válidos preservam produção/avaliação; versões/avaliações inválidas rejeitadas |
| 17–18 | Candidate e confirmation iguais ao conjunto original único; duplicação não infla banda |
| 19–20 | Overall só com cinco skills eligible; produções provisórias continuam bloqueando global |
| 21–23 | Trace current/carried, ledger intacto, nenhum carried entregue novamente |
| 24–26 | Completo não retomado; new explícito sujeito à policy; retry auto mesmo filho |
| 27–28 | PostgreSQL real: duas requisições geram um filho; retry complete não duplica perfil/currículo |
| 29–30 | Reset normal explicitamente descarta carry e preserva ledger; QA total recusa produção/ambiente desconhecido |
| Caso real semântico | 31 seen + answers originais válidos produzem coverage herdada; 31 seen sem answers não produzem evidência |
| Adicionais P1 | Expiração no limite, UTC ingênuo, revogação após carry, cadeia transitiva, orçamento adaptive herdado, GET sem writes, IDOR |

Executar teste vermelho antes da implementação, focais, placement/coverage/
exposure/planning/reset/curriculum, backend integral com PostgreSQL dedicado,
compileall e git diff --check. Exigir 0 failed e 0 skip obrigatório PostgreSQL.
Histórico de testes de rodadas anteriores não certifica esta alteração.

## Riscos e parada

P1 a impedir: dupla contagem, fonte errada, clone/seen como evidência, estado
perdido, dado apagado reconstruído, orçamento renovado, overall indevido,
concorrência duplicando filho ou aplicação downstream.

P2 backlog: validade longitudinal/calibração científica, preservação de evidence
após reset, melhoria de UI e expansão editorial. Não implementar refinamentos
depois dos gates verdes.

O usuário aprovou este desenho em 2026-10-09, incluindo a janela operacional
de sete dias e o reset normal descartando evidência e preservando exposure.
Nenhum teste da nova feature foi executado, nenhum gate de implementação foi
concluído e nenhuma consulta/escrita de produção ocorreu. Plano de implementação
em `docs/superpowers/plans/2026-10-09-placement-continuation.md`.
