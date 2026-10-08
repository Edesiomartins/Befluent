# Estabilização final do placement v2 — 2bbf6b59c0cb0b5b

Data: 2026-10-08. Escopo: backend local, sem alteração de policy, migration ou infraestrutura.

## Decisão

**NOT READY FOR DEPLOY.** PostgreSQL 18 exclusivo de teste não está disponível. O usuário confirmou que existe somente o banco real. Esse banco não foi usado para testes. A certificação PostgreSQL permanece pendente mesmo quando a suíte SQLite passa.

## Correções concretas

- P1: catálogo estático legado com instruções/opções PT era entregue para nativo EN aprendendo FR. O seed conhecido agora tem apoio PT reconhecido também sem metadado antigo; seleção, retomada e submissão recusam apoio incompatível com `409 native_support_unavailable`, sem registrar erro cognitivo.
- P1: resultado de produção não expunha `accepted_level`. Campo aditivo preserva `reported_level` e o nível limitado à tarefa; avaliação linguística continua provisional e inelegível para overall. Heurística continua sem CEFR público.
- P1: payload de IA com nível em objeto/lista causava `TypeError: unhashable type` no validador. Reprodução isolada do código em HEAD confirmou ambos; tipos inválidos agora ficam sem nível relatado/aceito/estimado.

Não foram encontrados P0. Revisão independente do diff não encontrou P0/P1 introduzido pelas correções.

## Gates

| Gate | Status | Evidência / limite |
|---|---|---|
| 1 Candidate/confirmation | **PASS** | `test_placement_confirmation.py`: R/L, confirmação correta/errada, terceira evidência, HTTP e fronteira de perfil |
| 2 Catálogo | **PASS** | 8 idiomas × R/L × PRE_A1–B2, 80 células com dois grupos independentes; matriz em `../placement-confirmation-v2/catalog-matrix.md`. Revisão editorial especializada não certificada |
| 3 Apoio nativo | **PASS** | Teste novo EN→FR recusa banco PT; testes existentes PT→FR e alteração de nativo; não foi criado banco EN |
| 4 Writing | **PASS** | Relatado/aceito, provenance, provisional, heurística sem CEFR e payload inválido; avaliadores controlados, sem chamada a provedor real |
| 5 Speaking | **PASS** | Multipart autenticado, entrega, transcript servidor, hash/bytes/MIME, limpeza no sucesso/falha, retry e skip; sem alegação acústica |
| 6 Planning | **PASS** | `test_placement_planning.py`, `test_legacy_placement_planning.py`, `test_placement_partial_integration.py`: aplicado/proposto, global anterior e GET somente leitura |
| 7 Journey parcial | **PASS** | Integração de nova conta, active/today/day, origem planning, primeiro bloco e currículo existente |
| 8 Ledger | **PASS** | Exposure/reteste, reuso excluído, identidade independente e preservação no reset |
| 9 Reset | **PASS** | Dry-run/apply/rollback, autenticação/conta, nativo, globais e outra conta em SQLite; PostgreSQL tratado no gate 10 |
| 10 PostgreSQL 18 real | **FAIL** | `POSTGRES_TEST_URL` ausente; quatro testes obrigatórios não executados. Runtime portátil encontrado não inicia (`0xC0000135`, dependência ausente); nenhum servidor de teste iniciado |
| 11 Suíte completa | **FAIL** | 1.733 passed, 4 skipped, 0 failed; os quatro skips são de gate obrigatório e impedem PASS estrito |
| 12 Inventário de regressões | **PASS** | Áreas abaixo cobertas pela suíte completa local; sem validação de frontend/produção |

## Inventário de regressões

| Área | Arquivos de testes representativos |
|---|---|
| Auth, onboarding, dashboard | `test_api.py` |
| Native language, learner_context | `test_native_language.py`, `test_placement_planning.py` |
| Placement, writing, speaking | `test_placement_api.py`, `test_placement_engine.py`, `test_placement_confirmation.py`, `test_placement_coverage_v2.py`, `test_placement_stabilization.py`, `test_placement_completion.py`, `test_placement_delivery.py` |
| Reset, exposure | `test_reset_test_user_learning.py`, `test_placement_exposure.py` |
| Curriculum, Journey, progression | `test_curriculum_api.py`, `test_curriculum_sequence.py`, `test_curriculum_progression.py`, `test_curriculum_flexible.py`, `test_placement_partial_integration.py` |
| Checkpoints, progress | `test_language_progress.py`, `test_progress_service.py`, `test_progress_sessions.py`, `test_teaching_engine.py`, `test_teaching_engine_v2.py` |
| Vocabulary, reviews | `test_vocabulary_learning.py`, `test_vocabulary_cycle_api.py`, `test_vocabulary_review_cycle.py`, `test_memory_review_sync.py` |

PostgreSQL pendente: conclusão paralela, criação/entrega paralela de exposure, referência recebida de outro schema e concorrência de soft pointers no reset.

## Validação

- Novos testes: **9 passed**.
- Candidate/confirmation + dois primeiros testes novos: **41 passed**.
- `compileall -q app tests`: PASS.
- `git diff --check`: PASS.
- Suíte completa final: **1.733 passed, 4 skipped, 0 failed, 40 warnings**, 1.737 casos coletados, em 1285,23s (21min25s), exit 0. Os 40 warnings são de depreciação da configuração Alembic `path_separator`. Nenhuma falha foi classificada como flaky. Evidência: [full-suite-final.log](full-suite-final.log).
- Primeira suíte, antes dos fixes: 1.724 passed, 4 skipped, 0 failed, 40 warnings em 1174,41s.
- Comando final: `python -m pytest -o addopts='' -q -rs`, com DATABASE_URL=sqlite://, ENVIRONMENT=development, AI_MOCK_MODE=true, SESSION_SECURE=false, COOKIE_DOMAIN vazio. Nenhum POSTGRES_TEST_URL configurado.
- PostgreSQL real: **não executado**, não há resultado PASS de PostgreSQL. Próximo gate: banco PostgreSQL 18 exclusivo com nome terminado em `_test`; rodar os quatro testes PostgreSQL e suíte final sem esses skips.

## Arquivos desta estabilização

- `backend/app/api/placement_tests.py`
- `backend/app/services/writing_evaluation.py`
- `backend/app/services/placement_production.py`
- `backend/tests/test_placement_stabilization.py`
- Este relatório e evidência de testes.

Alteração externa em `frontend/tests/placement-speaking.test.tsx` foi preservada; não foi feita nem certificada por esta tarefa.

## Backlog P2/P3

- P2: endurecer reconstrução de feedback histórico com `estimated_level` objeto/lista em `production_result`; risco teórico sem registro afetado comprovado, novas entradas protegidas pelo validador.
- P2: revisão editorial especializada, calibração empírica do banco e expansão de apoio nativo além de PT. Dois grupos por faixa são disponibilidade, não validação psicométrica.
- P3: nenhuma alteração estética/refactor solicitada ou realizada.

Sem commit, push, deploy ou escrita em produção. Testes usam banco local efêmero SQLite e provedores mock/controlados. Nenhum seed/migration aplicado a banco persistente.
