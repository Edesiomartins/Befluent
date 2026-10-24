# Progresso — Learning Experience V2

Rodada 1 de 3: somente backend. Sem push e sem deploy.

| Fase | Status | Testes | Resultado |
|---|---|---|---|
| 0 baseline | registrado | ver diagnosis.md | frontend 335 passed / typecheck exit 0 / lint exit 1 baseline failure / backend focal exit 0 |
| 1 language contract | implementado | `tests/test_language_contract_v2.py` + `test_activity_pool.py` + `test_family_exclusion.py` | exit 0 |
| 2 conversation situations | implementado | `tests/test_conversation_situations.py` junto com `tests/test_quality_gate_v2.py` | exit 0, 34 testes no comando, 19,5s, avisos Alembic `path_separator` |
| 3 interaction family | implementado | mapa já coberto por `tests/test_language_contract_v2.py` (fase 1, exit 0); enum `dictation` nesta fase | exit 0 na fase 1; carimbo na entrega entra nas fases 4 e 5 |
| 4 selector diversity | implementado | os três testes de seletor em `tests/test_learning_experience_v2.py` | exit 0, 3 testes, 7,2s; o arquivo de teste e a fatia FR entram na fase 6 |
| 5 activity bank pipeline | implementado | `tests/test_activity_pool.py` + `test_validate_batch_rejects_generated_and_third_language` + `tests/test_quality_gate_v2.py` | exit 0, 51 testes, 25,6s, avisos Alembic `path_separator` |
| 6 FR B1 slice | implementado | `tests/test_learning_experience_v2.py` + contrato, situações, família e retry da mesma atividade; depois `test_session_engine.py` + `test_lesson_bank_coverage.py` | exit 0, 28 testes em 15,6s; exit 0, 640 testes em 220s |
| 1.5.1 native language | implementado | `test_conversation_candidate_omits_portuguese_support_for_other_natives` + `test_fr_b1_slice_is_french_and_varied` | exit 0, 2 testes, 6,8s |
| 1.5.2 curated bank | implementado | `test_curated_bank_matches_metadata_and_the_selector` + `test_fr_b1_slice_is_french_and_varied` | exit 0, 2 testes, 6,9s |
| 1.5.3 retry objective | implementado | `test_interaction_retry_requires_the_same_objective` + retry da mesma atividade e da outra interação | exit 0, 3 testes, 7,3s |
| 1.5.4 third language guard | implementado | `tests/test_language_contract_v2.py` + fatia e exclusão de idioma | exit 0, 19 testes, 12,5s |
| 1.5.5 selection trace | implementado | `test_selector_breaks_three_identical_interaction_families` | exit 0, 1 teste, 6,5s; `excluded_diversity` 1 e `diversity_adjustment` igual à soma das linhas |
| 1.5.6 FR B1 review batches | implementado | `tests/test_activity_pool.py` + `test_validate_batch_rejects_generated_and_third_language`; `tests/test_fr_b1_review_batches.py` | pool exit 0, 27 testes, 15,6s; lote exit 0, 1 teste, 6,5s. Script: 10 gerados, 9 em revisão, 1 rejeitado por `review_required`. IA bloqueada (mock) |
| 1.5.7 lint baseline | implementado | `npx vitest run tests/speech-ui-latin.test.tsx`; `npm run lint` | 9 passed, exit 0; lint exit 0, 0 erros, 5 warnings anteriores |
| 1.5.8 suíte completa | registrado | `py -3 -m pytest -o addopts= --tb=line -q`; `npm test`; `npm run typecheck`; `npm run lint` | backend 1859 passed, 5 skipped, 41 warnings, exit 0, 1533,20s; frontend 335 passed / 39 arquivos, exit 0; typecheck exit 0; lint exit 0, 0 erros, 5 warnings |

Rodada 2 de 3: somente frontend. Sem push e sem deploy.

| Fase | Status | Testes | Resultado |
|---|---|---|---|
| 7 activity registry | implementado | `frontend/tests/activity-registry.test.ts` | 4 passed. Commit `0ce8505`. Família explícita desconhecida não vira texto livre |
| 8 interactive components | implementado | `frontend/tests/activity-interactions.test.tsx` + `activity-feedback.test.tsx` | Commit `4979821`. Ordem por toque, pares, lacuna, ditado sem transcript, escuta sem texto, nativo não português |
| 9 activity shell | implementado | `frontend/tests/activity-shell.test.tsx` + `teaching-slice.test.tsx` | Commit `a58d29a`. Fase pedagógica no lugar do rótulo antigo |
| 10 daily journey | implementado | coberto por `frontend/tests/cronograma.test.tsx` na suíte | Commit `a58d29a`. "Ao terminar, você será capaz de…" no dia |
| 11 feedback + remediation | implementado | `frontend/tests/activity-feedback.test.tsx` | Componente no `4979821`. A página diz que tentar novamente mantém atividade, objetivo e idioma |
| 12 session summary | implementado | `frontend/tests/session-summary.test.tsx` | Commit `48cfb57`. Dominado só com `mastered` do backend |
| 13 accessibility | implementado | backspace em `activity-interactions.test.tsx`; alvos de toque e `motion-reduce` no caminho do dia | Commits `4979821` e `a58d29a` |
| 2 suíte frontend | registrado | `npm test`; `npm run typecheck`; `npm run lint` | 354 passed, 44 arquivos, exit 0; typecheck exit 0; lint exit 0, 0 erros, 5 warnings anteriores |
| 2 suíte backend | registrado | `py -3 -m pytest -o addopts= --tb=line -q` | 1859 passed, 5 skipped, 41 warnings, exit 0, 823,96s. Os 5 skips continuam o gate PostgreSQL (`POSTGRES_TEST_URL` ausente). Sem mudança de backend nesta rodada |

Rodada 3 de 3: testes, sessão FR B1 no navegador, documentação e gate PostgreSQL local. Sem push e sem deploy.

| Fase | Status | Testes | Resultado |
|---|---|---|---|
| 14 testes de família | implementado | `activity-a11y.test.tsx`, `activity-diversity.test.tsx` | Commit `f73035b`. Tipo oficial tem renderizador; famílias diferentes não caem na mesma interação. axe sem contraste no jsdom |
| 14 jornada | implementado | `daily-journey.test.tsx` | Commit `6862b3c`. Objetivo, progresso, dia vazio e erro. Dia vazio não é missão concluída |
| 15 sessão FR B1 | implementado e validado pelo Playwright | `npm run test:e2e` | 1 passed, 10,9s. Commit `3272718`. Evidência em `verification.md` e `evidence/` |
| correção da sessão | implementado | `vocabulary-cycle.test.tsx` | Commit `e6acda4`. A resposta traz `status`; o SQLite local espera em vez de falhar com `database is locked` |
| correção do retry | implementado | `activity-feedback.test.tsx` | Commit `d330c8a`. A frase de manter a atividade só aparece na remediação |
| 16 documentação | implementado | `architecture.md`, `ui-system.md`, `verification.md` | Sem migration |
| gate PostgreSQL | executado | os 5 testes que usam `POSTGRES_TEST_URL` | 5 passed, 14,55s. PostgreSQL 18.6, banco `befluent_test`, porta 5433, container descartável. Sem volume de produção |
| 3 suíte frontend | registrado | `npm test`; `npm run typecheck`; `npm run lint` | 379 passed, 47 arquivos, exit 0; typecheck exit 0; lint exit 0, 0 erros, 5 warnings anteriores |
| 3 suíte backend | registrado | `py -3 -m pytest -o addopts= --tb=line -q` com `POSTGRES_TEST_URL` no Postgres 18.6 local | 1864 passed, 0 skipped, 41 warnings, exit 0, 1521,72s. Os 5 testes do gate entraram nesta suíte |
| 17 segundo cérebro | registrado | `BEFLUENT.md` no Obsidian, sem nota nova | Sem git nessa pasta |


