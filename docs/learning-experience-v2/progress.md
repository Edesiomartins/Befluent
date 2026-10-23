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
