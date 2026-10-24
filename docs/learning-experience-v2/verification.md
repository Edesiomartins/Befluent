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

## Rodada 3 — sessão FR B1 no navegador

Data: 2026-10-23. API em SQLite local (`backend/tmp/e2e-fr-b1.sqlite3`, `127.0.0.1:8011`) e frontend em `127.0.0.1:3011`. `NEXT_PUBLIC_API_URL` apontava para essa API. Sem PostgreSQL de produção.

Passos executados por `frontend/e2e/fr-b1-session.spec.ts` (`npm run test:e2e`): cadastro, login, língua nativa pt-BR, francês, nível B1 informado, objetivo Viajar, plano, `/learn/vocabulary`.

Resultado da última execução: 1 passed, 10,9s de teste, 21,0s com a subida dos servidores.

Famílias vistas: presentation, choice, audio_choice, dictation, inline_gap. Houve resposta errada, acerto, retry na mesma lacuna e o ditado `Je suis d'accord avec cette idée.` O resumo «Sessão concluída» apareceu ao fim da dose.

Capturas em `docs/learning-experience-v2/evidence/`: `fr-b1-inicio.png`, `fr-b1-ditado.png`, `fr-b1-resumo.png`. O passo a passo está em `fr-b1-session.log`.

Bugs encontrados e corrigidos nesta sessão:

- O SQLite local respondia `database is locked` quando o cronograma e o início da sessão escreviam juntos. O motor SQLite do aplicativo agora espera 30s e abre a transação com `BEGIN IMMEDIATE`. A suíte continua no SQLite em memória do `tests/conftest.py`.
- A resposta de cada tentativa não trazia `status` no topo. A tela encerrava a sessão no primeiro Continuar. O payload passou a incluir `status`, e a tela também lê `flow.status`.
- A correção da resposta anterior aparecia na atividade seguinte com a frase de que tentar novamente mantém aquela atividade. A frase só aparece se a sessão ainda está em remediação. Fora isso, o bloco se chama «Correção da resposta anterior».

Observação de conteúdo, sem correção nesta rodada: numa escolha gerada antes do ditado, o gabarito mostrado foi «implementar». A fatia curada do ditado continuou em francês.

## Rodada 3 — gate PostgreSQL

Docker Desktop estava parado. Foi iniciado só para um container descartável, fora do volume e da porta do projeto:

`docker run --rm -d --name befluent-pg-test -e POSTGRES_PASSWORD=befluent_local_test -e POSTGRES_DB=befluent_test -p 5433:5432 postgres:18-alpine`

Versão confirmada no container: PostgreSQL 18.6. Banco `befluent_test`. URL só no processo do pytest: `postgresql+psycopg://postgres:befluent_local_test@127.0.0.1:5433/befluent_test`.

O driver `psycopg[binary]==3.2.13`, já declarado em `backend/requirements.txt`, não estava instalado neste Python. Foi instalado no ambiente local. Sem mudança de dependência no repositório.

Os cinco testes do gate passaram em 14,55s: recusa de cascade entre schemas, cerca de escrita da outra conta, exposição paralela e os dois casos de conclusão de placement.

A suíte backend inteira, com a mesma URL, fechou em **1864 passed, 0 skipped, 41 warnings, exit 0**, 1521,72s. Os cinco skips de quando `POSTGRES_TEST_URL` falta rodaram nesta passagem. O container foi removido ao fim.

