# Progresso — Learning Experience V2

Rodada 1 de 3: somente backend. Sem push e sem deploy.

| Fase | Status | Testes | Resultado |
|---|---|---|---|
| 0 baseline | registrado | ver diagnosis.md | frontend 335 passed / typecheck exit 0 / lint exit 1 baseline failure / backend focal exit 0 |
| 1 language contract | implementado | `tests/test_language_contract_v2.py` + `test_activity_pool.py` + `test_family_exclusion.py` | exit 0 |
| 2 conversation situations | implementado | `tests/test_conversation_situations.py` junto com `tests/test_quality_gate_v2.py` | exit 0, 34 testes no comando, 19,5s, avisos Alembic `path_separator` |
| 3 interaction family | implementado | mapa já coberto por `tests/test_language_contract_v2.py` (fase 1, exit 0); enum `dictation` nesta fase | exit 0 na fase 1; carimbo na entrega entra nas fases 4 e 5 |
| 4 selector diversity | implementado | os três testes de seletor em `tests/test_learning_experience_v2.py` | exit 0, 3 testes, 7,2s; o arquivo de teste e a fatia FR entram na fase 6 |
