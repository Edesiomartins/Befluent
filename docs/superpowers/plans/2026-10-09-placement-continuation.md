# Placement continuation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (execução nativa recomendada) ou superpowers:subagent-driven-development se o
> usuário escolher delegação. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retomar assessment ativo e complementar incomplete com evidência
histórica elegível, auditável e única, mantendo exposure e critérios de nível.

**Architecture:** Evidência efetiva centralizada em um serviço, snapshots em
feedback_json/result_json e continuation como novo PlacementTest vinculado.
User lock existente serializa seleção da fonte/criação e complete. GET descobre
o fluxo sem gravar ou recalcular resultados históricos.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, SQLite para isolamento, PostgreSQL
dedicado para concorrência, pytest. Sem dependência ou migration nova prevista.

**Spec:** `docs/superpowers/specs/2026-10-09-placement-continuation-design.md`,
aprovada pelo usuário em 2026-10-09.

## Global Constraints

- Só backend, testes e documentação; sem frontend, commit, push, deploy ou produção.
- `placement-evidence-carry-v1`; default operacional sete dias, configurável 1–30.
- Quotas VG6/R4/L4/W1/S1; minimum16, maximum20; adaptive budget4, incluindo carry.
- Não apagar exposure; reset normal descarta/invalida assessment evidence.
- Writing/speaking continuam provisional e `eligible_for_overall=False`.
- Checkpoints e results históricos não são backfilled/reclassificados.
- Rodar red/green por etapa; gate final exige 0 failed e 0 skip obrigatório PG.
- Parar quando todos os gates ficarem verdes; P2 só backlog.

## Review Focus

1. JSON histórico malformado: rejeição explicada, sem TypeError ou elegibilidade default.
2. Mudança de configuração: não prolongar validade da raiz nem renovar collected_at.
3. Keys que conectam dois grupos: deduplicação transitiva antes de candidate/coverage.
4. Feedback/revogação posterior: coleta revalida, GET de result concluído preserva snapshot.
5. Manifest privado no result_json: nenhum endpoint pode devolver respostas/keys/rubricas internas.

## Arquivos e fronteiras

| Arquivo | Responsabilidade |
| --- | --- |
| `backend/app/services/placement_evidence.py` | Snapshot, validação, evidência efetiva e projeção pública |
| `backend/app/services/placement_continuation.py` | Fonte, lifecycle, vínculo, guard e discovery |
| `backend/app/api/placement_tests.py` | Integração nos handlers, snapshots transacionais e filtros de payload |
| `backend/app/services/placement_coverage.py` | Contadores current/carried e deficits sobre união |
| `backend/app/services/placement_engine.py` | Provenance aditiva em AnswerRecord; limiares intactos |
| `backend/app/services/placement_exposure.py` | Ajuste do resultado com evidência efetiva; ledger não vira evidência |
| `backend/app/schemas/__init__.py`, `core/config.py` | start_mode e validity_days validados |
| `backend/scripts/reset_test_user_learning.py` | Relatório explícito de descarte e guarda QA total |
| `backend/tests/placement_continuation_helpers.py` | Fixtures persistidas com answer/delivery/exposure genuínos e policy v3 |
| `backend/tests/test_placement_continuation_policy.py` | Validade, provenance, semântica e produção |
| `backend/tests/test_placement_continuation.py` | Fluxo API, selection, quota, resultado, idempotência e segurança |
| `backend/tests/test_placement_continuation_postgres.py` | Criação/complete concorrentes em PG real |
| `backend/tests/test_reset_test_user_learning.py` | Descarte/carry e ambientes QA |
| `docs/placement-continuation-2bbf6b59c0cb0b5b/` | Contrato, relatório final e evidências de execução |

Os serviços não importam o módulo API. O adapter preserva os fluxos históricos;
as novas interfaces têm parâmetros opcionais/aditivos quando chamadas existentes
precisam continuar válidas. Nenhum caller lê manifest privado diretamente.

## Task 1: Snapshot e policy de evidência

**Files:** placement_evidence.py, core/config.py, placement_engine.py,
placement_continuation_helpers.py, test_placement_continuation_policy.py.

**Interfaces produzidas:**

- `evidence_policy(validity_days: int = 7) -> dict`.
- `snapshot_answer(db: Session, test: PlacementTest, answer: PlacementTestAnswer,
  *, now: datetime) -> dict`: exige fonte/provenance; não commit; snapshot privado.
- `validate_snapshot(db: Session, snapshot: dict, target: PlacementTest,
  *, now: datetime) -> str | None`: reason ou elegível; sem writes.
- `deduplicate_snapshots(snapshots: list[dict]) -> tuple[list[dict], list[dict]]`:
  IDs originais + componentes conexos, vencedor mais antigo determinístico.
- Campos opcionais `evidence_id`, `evidence_origin`, `source_test_id` em AnswerRecord.

- [ ] Escrever testes: default7; recusa 0/31; limite temporal exato; timestamp
  futuro/inválido; configuração não prolonga; mesmo usuário/idioma; incompatível
  policy/skill; missing snapshot; exposure sem answer; grading contract alterado;
  reused/revealed/invalidation; score bool/NaN/inf/fora0–1; JSON lista/nulo/string.
- [ ] Escrever teste de clone transitive bridge: três snapshots conectados
  devem produzir uma evidência; score maior não muda vencedor.
- [ ] Escrever produção válida/inválida para W/S: texto/transcript persistido,
  reported/accepted/rubric/provenance preservados; STT mock e skip rejeitados;
  `eligible_for_overall` continua false; nenhuma avaliação/provider chamada.
- [ ] Rodar red: `.venv/Scripts/python.exe -m pytest tests/test_placement_continuation_policy.py -q`.
- [ ] Implementar interfaces com timestamps UTC, bundle de policy e digest
  canônico; snapshots históricos só adaptados se hash/provenance original conferem.
- [ ] Rodar green do mesmo arquivo, sem mudar o teste para aceitar defaults inseguros.

## Task 2: União current/carried e coverage

**Files:** placement_evidence.py, placement_coverage.py,
test_placement_continuation_policy.py, test_placement_continuation.py.

**Interfaces:** consome Task1; produz dataclass `EffectiveEvidence` com
`current_answers`, `carried_snapshots`, `objective_records`, `production_results`,
`coverage`, `public_carry`, `rejected` e IDs/keys usados para excluir delivery.

- `effective_evidence(db: Session, test: PlacementTest,
  answers: list[PlacementTestAnswer] | None = None, *, now: datetime) -> EffectiveEvidence`.
- `public_carry(evidence: EffectiveEvidence) -> dict`.
- `mandatory_snapshot` recebe componentes de origem opcionais, sem quebrar
  chamadas existentes; top current bruto, carried único válido, per-skill elegível.

- [ ] Escrever teste com VG6/R3/L2/W1/S0 carried: total12, remaining4, deficits
  VG0/R1/L2/W0/S1 e contadores por origem.
- [ ] Escrever teste: adicionar R1 current dá reading current1/carried3/total4;
  same original ID/clone não aumenta quotas nem confirmation; skip/open não soma.
- [ ] Escrever teste: raw current reused/clones continua bruto, mas quota não
  aumenta; união invalidada durante sessão reduz suporte de forma explícita.
- [ ] Escrever teste: adaptive carried4 bloqueia quinto extra; fonte >20 ou
  fase objetiva desconhecida não escolhe subconjunto de scores favoráveis.
- [ ] Rodar red focal policy/API; implementar EffectiveEvidence e contadores.
- [ ] Rodar green; quota engine e candidate devem usar a mesma união independente.

## Task 3: Lifecycle, criação e descoberta read-only

**Files:** placement_continuation.py, schemas/__init__.py, placement_tests.py,
test_placement_continuation.py.

**Interfaces:**

- `continuation_source(db: Session, user_id: str, language_code: str,
  *, now: datetime) -> tuple[PlacementTest | None, EffectiveEvidence | None, list[dict]]`.
- `continuation_context(source: PlacementTest, *, now: datetime) -> dict`.
- `resume_payload(db: Session, test: PlacementTest | None,
  evidence: EffectiveEvidence | None, *, now: datetime) -> dict`.
- `ensure_collectable(db: Session, test: PlacementTest, *, now: datetime) -> None`.
- `PlacementTestCreate.start_mode: Literal['auto', 'new'] = 'auto'`.

- [ ] Escrever API red: dez respostas volta com mesmo ID e open delivery;
  incomplete cria filho linked/root/sequence1, retry retorna mesmo filho;
  segunda continuation usa source evidence IDs originais e sequence2.
- [ ] Escrever GET red: /current descobre continuable com test=null; SQL spy
  prova zero INSERT/UPDATE/DELETE; /{id} mostra contexto; histórico intacto.
- [ ] Escrever new/expiry red: completo não carregado; diferente idioma/policy,
  expirado, maximum_reached e unknown reason não continuados; new não carry,
  respeita retake e retorna placement_active_exists se ativo utilizável.
- [ ] Escrever lifecycle guards em TODOS os writers: next/answer/writing/
  speaking/skip/complete recusam expired/superseded; checkpoint preservado.
- [ ] Rodar red; implementar latest determinístico por started_at/id,
  User lock antes de reconsultar fonte/ativo e locks dos tests em ordem consistente.
- [ ] Rodar green API/policy. Não reabrir fonte completa nem mutar seu result_json.

## Task 4: Selector, resultado e consolidação downstream

**Files:** placement_tests.py, placement_exposure.py, placement_planning.py se
necessário, test_placement_continuation.py, test_placement_completion_postgres.py.

**Interfaces:** handlers produzem EffectiveEvidence uma vez por operação;
`_state_from`, `_mandatory_coverage`, `_progress` e `_test_payload` recebem união
opcional; callers históricos continuam usando seus parâmetros anteriores.
`adjust_result(result, answers, ...)` recebe suporte efetivo explicitamente;
`_result_payload` sanitiza manifest privado antes de expandir result.

- [ ] Escrever red selector: carried VG6/R3/L2/W1/S0 só pergunta R/L/S antes
  das quotas; não reapresenta carried nem gera novo exposure; exceptions/skips
  da fonte não encerram imediatamente o filho.
- [ ] Escrever red caso31seen: source answers válidos dão coverage herdada;
  ledger31seen sem answers dá zero carry e motivos de provenance explícitos.
- [ ] Escrever red: original scores únicos mantêm candidate/confirmation;
  clone/reused não inflaciona deciding band; max20/adaptive4 intactos.
- [ ] Escrever red produção e overall: preserva provisórios W/S e overall=null;
  função overall_level calcula normal com cinco resultados elegíveis sintéticos;
  nenhuma policy real é relaxada para passar esse teste.
- [ ] Escrever red planning: trace current/carried/continuation/status presente
  em aplicação e retained_prior_planning; GET antigo preserva applied planning.
- [ ] Escrever red completed retry: fonte imutável, filho aplica perfil/currículo
  uma vez; reenvio complete devolve snapshot final sem revalidação retroativa.
- [ ] Escrever red privacy/IDOR: payload em cada endpoint não contém snapshot,
  answer_json, keys_json, rubric privada ou source de outra conta.
- [ ] Rodar red; snapshots novos são anexados à resposta na mesma transação,
  com ID após flush, nunca substituindo provenance/source timestamps.
- [ ] Implementar união em seleção/cálculo/adjust_result/planning; preservar
  guards e rollback downstream existentes. Rodar green focal + histórico v2/v3.

## Task 5: Reset explícito e guarda QA

**Files:** reset_test_user_learning.py, test_reset_test_user_learning.py,
test_placement_continuation.py.

**Interfaces:** manter flags CLI existentes; relatório recebe
`assessment_evidence_policy='discard_and_invalidate'` e IDs/contagens afetadas.
`validate_exposure_clear` exige test/development e database dedicado; run_reset
confere ambiente efetivo e argumento opcional, sem override de produção.

- [ ] Escrever red: dry-run sem writes informa descarte; apply em fixture local
  apaga tests/manifests/answers, mantém ledger/login/outra conta; rollback restaura.
- [ ] Escrever red QA: recusa production mesmo com environment='development';
  recusa staging/unknown/vazio e database não marcado; aceita fixture test/dev
  dedicado. Não executar CLI --apply contra ambiente real.
- [ ] Rodar red; acrescentar relatório/guarda/postcondições sem reter produções
  clandestinamente em exposure e sem flag nova desnecessária.
- [ ] Rodar green reset, exposure e continuation.

## Task 6: PostgreSQL, revisão e certificação final

**Files:** test_placement_continuation_postgres.py,
docs/placement-continuation-2bbf6b59c0cb0b5b/report.md e logs.

**Interfaces:** reutilizar fixture postgres_reset_database de *_test, schema UUID;
ambas as threads Session(autoflush=False), barrier e timeout finitos.

- [ ] Escrever teste PG que inicia duas auto requests sobre incomplete elegível:
  mesmo filho/root/manifest; uma nova linha de test; nenhuma answer/exposure copiada.
- [ ] Escrever teste PG complete concorrente do filho: um conjunto de sections,
  um perfil/currículo, fonte intacta; testar stale identity-map e retry.
- [ ] Verificar conectividade/identidade de PostgreSQL dedicado ANTES de testes;
  nunca usar DATABASE_URL de produção nem registrar senha. Sem conexão segura,
  completar trabalho local e reportar gate PG pendente, sem alegar READY.
- [ ] Rodar focais continuation + policy; depois placement/coverage/exposure/
  planning/reset/curriculum. Registrar comando, exit code, passed/failed/skipped.
- [ ] Rodar testes PG continuation e todos os arquivos *_postgres.py; exigir
  0 failed e 0 skipped. Não resolver skips com SQLite/mock.
- [ ] Rodar backend integral com POSTGRES_TEST_URL dedicado e app DATABASE_URL
  SQLite: `.venv/Scripts/python.exe -m pytest -o addopts= -q -rs` (backend cwd).
- [ ] Rodar `.venv/Scripts/python.exe -m compileall -q app tests scripts` e
  `git diff --check`; revisar diff completo com foco P0/P1 e fronteira frontend.
- [ ] Corrigir P0/P1 encontrados com red/green; repetir só conjuntos afetados
  e ampliar quando houver motivo. Não refinar P2 após gates verdes.
- [ ] Relatório final cobre os 16 pontos pedidos, migration ausente, matriz30,
  resultados exatos, limitações e `git status --short`. Registrar no Segundo
  Cérebro pela ponte; informar READY somente se todos os gates passaram.

## Estado da execução

- [x] Desenho aprovado pelo usuário.
- [x] Plano escrito e revisado contra a spec; inclui todos os casos1–30 e riscos.
- [ ] Plano revisado pelo usuário e método de execução escolhido.
- [ ] Tasks1–6 executadas e validadas.

Recomendação: **execução nativa nesta sessão**, sem delegação por tarefa, pois
policy, união de evidência e integração API compartilham interfaces estreitas.
A skill executing-plans prevê revisão independente ao final, antes do veredito.
Nenhum commit é permitido, apesar dos exemplos genéricos de skills.
