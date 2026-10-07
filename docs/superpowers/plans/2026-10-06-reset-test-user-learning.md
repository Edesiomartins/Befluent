# Reset de aprendizagem de um usuário de teste

Pedido/especificação: rodada 2bbf6b59c0cb0b5b, instruções anexadas pelo proprietário.
Execução local autorizada; nenhuma escrita de produção, commit, push ou deploy.

## Decisões após auditoria

- Usar CLI independente, SQLAlchemy Core e transação única; nenhuma alteração de API, modelo, migration ou motor pedagógico.
- Usuário obrigatório por ID ou email (opções mutuamente exclusivas), exatamente uma correspondência; saída sem senha/token/URL de conexão.
- Preservar todas as colunas de User exceto native_language=NULL, incluindo timestamps; preservar login, perfil, entitlement, auditoria e revisão editorial.
- Preservar UserPreference, timezone, TTS/UI; limpar default_language_id e minutes_per_day/skills/primary_goal.
- Remover todos os registros pedagógicos por posse explícita e filhos; catálogos/cache globais preservados.
- Comparar schema real com mapa auditado, recusar novos modelos/tabelas/colunas/FKs relevantes e referências entre contas. Incluir vínculos sem FK lesson_ref/placement_test_id.
- PostgreSQL: snapshot SERIALIZABLE, timeout e locks FOR UPDATE sobre usuário/registros pessoais. SQLite: arquivo existente, FK habilitada, BEGIN IMMEDIATE na escrita; leitura mode=ro/query_only.
- Reversibilidade transacional por --apply --rollback. Depois do commit, recuperação requer backup externo verificado. Nenhum backup sensível exportado automaticamente.

## Etapas

1. [x] Testes com dois usuários, dados em todas as tabelas resetadas, globais/auth preservados, FKs reais SQLite; observar red.
2. [x] Script: schema, resolução, posse, contagens, conflitos, exclusão filhos→pais, reset parcial de preferências/User, pós-condições, CLI/rollback.
3. [x] Testar dry-run/commit/rollback/falha parcial/idempotência/login/onboarding/identificador inválido/ambíguo/schema divergente/referências cruzadas.
4. [x] Documentar mapa completo de FKs e ordem, comandos, limites PostgreSQL e recuperação pós-commit; verificar diff/status e registrar Segundo Cérebro.

## Verificação

pytest tests/test_reset_test_user_learning.py; focais de auth/onboarding/native; suíte geral quando necessário para mudança compartilhada (nenhuma planejada).
Não chamar bancos do projeto ou produção: somente bancos temporários construídos pelos testes.

