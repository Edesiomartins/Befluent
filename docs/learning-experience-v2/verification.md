# Verificação — rodada 1 (backend)

Data: 2026-10-23. Sem deploy. `POSTGRES_TEST_URL` ausente: gate PostgreSQL **NOT RUN**.

## Baseline (fase 0, antes das fases 1–6)

- `npm test` em `frontend/`: 335 passed, 39 arquivos, exit 0, 39,19s.
- `npm run typecheck`: exit 0.
- `npm run lint`: exit 1. **baseline failure**: `frontend/tests/speech-ui-latin.test.tsx:57` `no-this-alias`, mais 5 warnings.
- Pytest focal de pool, sessão, idioma, editorial, cobertura, quality gate e retry: exit 0. A linha de contagem não ficou no log.

## Desta rodada

- Situações + quality gate: exit 0, 34 testes, 19,5s. Avisos Alembic `path_separator`.
- Três testes de seletor: exit 0, 7,2s.
- Pool + validação de lote + quality gate: exit 0, 51 testes, 25,6s. Avisos Alembic `path_separator`.
- Contrato, situações, família, retry da mesma atividade e `tests/test_learning_experience_v2.py`: exit 0, 28 testes, 15,6s.
- `tests/test_session_engine.py` + `tests/test_lesson_bank_coverage.py`: exit 0, 640 testes, 220s.

A fatia FR B1 tem 10 atividades curadas. O banco estático de francês B1 que já existia continua no plano de apoio. Não houve preenchimento até 150–250.
