# Diagnóstico — Learning Experience V2 (rodada 1, backend)

Data: 2026-10-23. Sem deploy. PostgreSQL de produção não foi usado.

## O que existe

- Teaching Engine, Teaching Flow, objetivos, mastery, tentativas, evidência, erro, remediação, Memory Engine, Activity Pool, exposição, Session Engine V2, currículo e placement.
- O seletor já exclui atividade vista, família aposentada e exposição dentro do cooldown de 7 dias. Retry não lexical repete a mesma atividade (`760ac12`).
- `quality_status`, `target_language` e `native_language` já entram no pool editorial. `validate_batch` e `generate_incremental_batches` existem e não preenchem cota artificial.
- `CONVERSATION_SITUATIONS` era um dicionário só por faixa, em português, para todos os idiomas. `conversation_situation` ignorava o idioma-alvo.
- A interface ainda recebe `prompt` / `prompt_pt` sem papéis semânticos estáveis (`prompt_target`, `scenario_target`, `interaction_family`).

## O que será preservado

- Dados de aluno, sessões, progresso, exposure ledger, `family_key`, cooldown e vocabulário adiado.
- Retry da mesma atividade quando não houver outra interação segura do mesmo objetivo.
- Nada de migration destrutiva, `random()` puro ou padding de pool.

## O que muda nesta rodada

- Contrato explícito de idioma (alvo, nativo, apoio, terceira língua).
- Situações de conversa por idioma, com cenário principal no idioma-alvo.
- `interaction_family` derivado do tipo, mais diversidade no plano da sessão e no traço do seletor.
- Gates do pipeline reutilizam `quality_status` já existente, inclusive `language_invalid`.
- Fatia curada FR B1 + pt-BR, sem encher o banco até 200.

## Riscos

- Tratar `quality_status` ausente como `unknown` esvaziaria sessões legadas. Ausência continua aceita na entrega; o valor não é inventado como `approved` no conteúdo.
- `prompt_pt` permanece para o frontend atual. O contrato novo não copia esse campo para `prompt_native`.
- O detector de terceira língua continua sendo o guarda editorial já existente (clones conhecidos de inglês e marcadores do incidente FR). Não classifica qualquer texto do mundo.

## Baseline (antes das fases 1–6)

Comandos reais em 2026-10-23, na árvore que já continha as correções de 2026-10-16 (depois commitadas em `ac62bf3`).

- `npm test` em `frontend/`: 335 passed, 39 arquivos, exit 0, 39,19s.
- `npm run typecheck`: exit 0.
- `npm run lint`: exit 1. **baseline failure** pré-existente: `frontend/tests/speech-ui-latin.test.tsx:57` `no-this-alias`. Mais 5 warnings. Não é regressão desta rodada.
- `py -3 -m pytest` dos arquivos de pool, família, língua nativa, editorial, cobertura do banco, sessão, quality gate, aceite de atividades vistas e retry: exit 0, progresso 100%, avisos Alembic `path_separator`. A linha final de contagem não ficou no log.
- `py -3 -m pytest tests/test_exercise_review_regressions.py tests/test_family_exclusion.py tests/test_seen_activities_acceptance.py tests/test_activity_pool.py tests/test_session_engine.py --tb=line -q`: exit 0.
- `POSTGRES_TEST_URL` ausente. PostgreSQL gate: NOT RUN.
- `git status` inicial tinha alterações não commitadas de 2026-10-16. Os testes acima passaram e elas foram para `ac62bf3`.

## Compatibilidade

- Campos novos são aditivos. `situation` de conversa passa a ser o cenário no idioma-alvo; o apoio em português vai para `scenario_native` quando a língua nativa é pt-BR.
- Frontend não é alterado nesta rodada.
