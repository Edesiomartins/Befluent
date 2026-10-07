# Reset dos dados de aprendizagem de um usuário de teste

Rodada: `2bbf6b59c0cb0b5b`, 2026-10-06. Script: `backend/scripts/reset_test_user_learning.py`.
Implementação local; nenhum acesso/escrita de produção, commit, push ou deploy.

## Resultado e limites

CLI para um usuário explícito, abrangendo todos os idiomas, inclusive matrículas inativas
e placement sem matrícula. Default é dry-run SELECT-only. Um único identificador:
`--user-id` OU `--user-email`; zero/duas opções, usuário inexistente ou email ambíguo são recusados.
Saída inclui apenas ID/email da conta encontrada, contagens, ordem e campos resetados;
não imprime senha, hashes/tokens, conteúdo de respostas ou URL do banco.

**Reversibilidade:** `--apply --rollback` executa DELETEs e UPDATEs reais, valida o reset,
reverte a transação e compara fingerprint interno de todos os registros pessoais/preservados
com o estado anterior. `transaction=rolled_back`, `write_committed=false`, `rollback_verified=true`.
`after` são as contagens dentro do ensaio; `persisted_after` são as contagens restauradas.
Depois do commit real, desfazer exige backup externo verificado: não existe undo automático.
O script não exporta credenciais/dados sensíveis para arquivo de backup.

## Decisões de preservação

- **users:** mesma conta, ID, email, hash de senha, nome, is_active, created_at, updated_at e last_login_at.
  Única mudança: native_language=NULL. Nullable confirmado no modelo; também exigido no schema real.
  Conta previamente inativa permanece inativa; o reset não libera acesso nem altera credenciais.
- **user_preferences:** preservar linha, timezone, tts_speed, updated_at e demais UI prefs.
  Limpar somente default_language_id e chaves minutes_per_day, skills e primary_goal.
  Preferências JSON malformadas são recusadas; não são silenciosamente descartadas.
- **sessions/password_reset_tokens:** preservar integralmente, incluindo sessões existentes.
- **language_entitlements:** preservar direitos concedidos, cancelados e metadados; não resetar pricing/acesso.
  Escolher/ativar idioma novamente usa as regras de entitlement existentes.
- **audit_logs/content_reviews:** preservar auditoria e revisões editoriais, mesmo feitas por esse usuário.
- **onboarding:** não é outra tabela ou flag global; `/onboarding/status` usa user_languages.
  Sem matrículas, completed=false e languages=[]; native NULL exige nova escolha.
- **cache:** ai_response_cache é global, sem FK user/lesson, destinado a conteúdo não pessoal.
  Não apagar nem reconstruir cache global. Payloads pessoais de lições/flow/memory/boletim são removidos
  junto de suas linhas. Caches de processo/browser não são controlados por este CLI: fechar telas antigas
  e reabrir após reset. Conteúdo contaminado no cache global exige investigação separada.

## Segurança transacional e schema

Mapa explícito de 56 tabelas: 42 resetadas, 7 preservadas (duas com atualização limitada)
e 7 globais. `alembic_version` pode existir e não é tocada. Nenhuma tabela/coluna/FK nova
é aceita automaticamente; divergência exige revisão do mapa, sem migration automática.
PKs, FKs/ondelete e nullable de native são verificados no banco real; nenhum schema é criado pelo CLI.
Somente SQLite existente ou PostgreSQL. User triggers e RLS são recusados nos caminhos auditados.
FKs entrantes de outros schemas também são recusadas, evitando cascades fora do escopo.

Posse é determinada pela FK principal de cada tabela. FKs secundárias não expandem o usuário-alvo.
Antes de DELETE, conferir referências cruzadas em ambos os sentidos e vínculos sem FK
`curriculum_blocks.lesson_ref`/`user_languages.placement_test_id`; inconsistência recusa todo o reset.
DELETEs são por IDs capturados, em lotes limitados e filhos antes dos pais (inclusive SET NULL).
Retry autorreferente é removido na própria tabela. Não há TRUNCATE/DROP/DELETE global no script.
Após DELETE, conferir todas as categorias, IDs capturados, conta, credenciais e dados preservados.
Qualquer erro anterior ao commit faz rollback total. Segunda execução não muda estado já limpo.

- SQLite: FK ON, BEGIN IMMEDIATE para escrita; mode=ro + query_only no CLI default.
- PostgreSQL: SERIALIZABLE, lock_timeout=2s, statement_timeout=60s; FOR UPDATE em usuário
  e grafo pessoal. SHARE ROW EXCLUSIVE em curriculum_blocks/user_languages protege os vínculos
  sem FK durante a operação. **Esses locks podem bloquear brevemente escritas de outras contas.**
- **Operação futura exige drenar/pausar escritores da API e jobs durante o reset**, sem requests
  antigos em voo. Depois do commit, um escritor antigo pode tentar gravar IDs já removidos em campos
  sem FK; locks do script não corrigem a validação futura de todos os escritores.
- Rollback deixa eventual request bloqueado prosseguir com os registros existentes. Não repetir
  --apply cegamente após erro de conectividade/commit ambíguo: consultar estado com dry-run primeiro.

## Uso futuro no container da API (a partir de backend)

Troque `usuario@exemplo.com` pelo email exato do usuário de teste; nenhum usuário foi escolhido nesta rodada.
Use o script atualizado e schema compatível. Antes da escrita: backup restaurável verificado,
writers/jobs pausados e contagens revisadas. Os comandos abaixo são instruções, não foram executados em produção.

```bash
python scripts/reset_test_user_learning.py --user-email 'usuario@exemplo.com'
python scripts/reset_test_user_learning.py --user-email 'usuario@exemplo.com' --apply --rollback
python scripts/reset_test_user_learning.py --user-email 'usuario@exemplo.com'
python scripts/reset_test_user_learning.py --user-email 'usuario@exemplo.com' --apply
python scripts/reset_test_user_learning.py --user-email 'usuario@exemplo.com'
```

Alternativa: `--user-id 'ID_EXATO_REVISADO'` no lugar de --user-email; nunca ambos.
1. Dry-run e revisão de todas as contagens, ID/email, campos e exclusão de outros usuários.
2. Ensaio: rolled_back, write_committed=false, rollback_verified=true; novo dry-run deve repetir before.
3. Apply real: committed; zero em after e native NULL; zero em novo dry-run.
4. Encerrar abas antigas e reabrir/login com mesma senha; verificar auth/me/native_language_required.
5. Escolher língua nativa, onboarding, placement e ativação do idioma; iniciar Journey nova.
6. Não reutilizar IDs antigos. Retomar jobs/escritores depois de validar o estado inicial.
7. Se qualquer guard recusar, investigar o campo/schema; não remover proteção para forçar reset.

## Validação local

Testes: `backend/tests/test_reset_test_user_learning.py` e
`backend/tests/test_reset_test_user_learning_postgres.py` (opt-in).
Fixture SQLite temporária com FK ON, dois usuários, dados em todas as 42 tabelas pedagógicas,
globais/auth/editorial/entitlement e preferências. HTTP real comprova sessão existente, novo login e onboarding.
Cobertura: identificadores/ambiguidade/schema desconhecido, nenhuma escrita no dry-run,
arquivos SQLite não criados, conta/campos/timestamps/outro aluno/catálogos intactos,
todos os idiomas/inativos/placement standalone, rollback/idempotência, falha após DELETEs
e após native update, pós-condição incompleta e FKs/soft links cruzados em ambos os sentidos.

Testes PostgreSQL exigem POSTGRES_TEST_URL de PostgreSQL 18 com nome de banco terminado em _test;
criam somente schemas temporários UUID nesse banco dedicado. Verificam inbound FK cross-schema
e bloqueio concorrente de soft link com duas conexões. Sem configuração, são skipped;
isso **não certifica PostgreSQL/concurrency/produção**. Nenhuma dependência instalada silenciosamente.
Suíte geral e provedores externos não são certificados pelos testes focais deste script.

## Auditoria completa dos modelos e FKs

Mapa abaixo extraído dos modelos atuais; o script compara com schema real antes de qualquer operação.
`CASCADE`/`SET NULL` são propriedades das FKs existentes, não comandos globais de exclusão.

| Tabela | Decisão | FKs (coluna → tabela.coluna; ondelete) |
|---|---|---|
| users | PRESERVAR/UPDATE LIMITADO | — |
| languages | GLOBAL: NÃO TOCAR | — |
| user_languages | RESETAR | language_id → languages.id; RESTRICT/NO ACTION; user_id → users.id; CASCADE |
| language_entitlements | PRESERVAR | language_id → languages.id; RESTRICT/NO ACTION; user_id → users.id; CASCADE |
| learning_goals | RESETAR | user_language_id → user_languages.id; CASCADE |
| learning_plans | RESETAR | user_language_id → user_languages.id; CASCADE |
| learning_plan_items | RESETAR | plan_id → learning_plans.id; CASCADE |
| curricula | RESETAR | user_language_id → user_languages.id; CASCADE |
| curriculum_weeks | RESETAR | curriculum_id → curricula.id; CASCADE |
| curriculum_days | RESETAR | week_id → curriculum_weeks.id; CASCADE |
| curriculum_blocks | RESETAR | day_id → curriculum_days.id; CASCADE; objective_id → learning_objectives.id; SET NULL |
| study_sessions | RESETAR | user_language_id → user_languages.id; CASCADE |
| lessons | RESETAR | study_session_id → study_sessions.id; SET NULL; user_language_id → user_languages.id; CASCADE |
| lesson_activities | RESETAR | lesson_id → lessons.id; CASCADE |
| lesson_activity_attempts | RESETAR | lesson_id → lessons.id; CASCADE; retry_of_id → lesson_activity_attempts.id; SET NULL; user_language_id → user_languages.id; CASCADE |
| exercises | RESETAR | lesson_activity_id → lesson_activities.id; SET NULL; user_language_id → user_languages.id; CASCADE |
| exercise_attempts | RESETAR | exercise_id → exercises.id; CASCADE; study_session_id → study_sessions.id; SET NULL |
| conversations | RESETAR | study_session_id → study_sessions.id; CASCADE; user_language_id → user_languages.id; CASCADE |
| conversation_messages | RESETAR | conversation_id → conversations.id; CASCADE |
| vocabulary_items | RESETAR | user_language_id → user_languages.id; CASCADE |
| vocabulary_examples | RESETAR | vocabulary_item_id → vocabulary_items.id; CASCADE |
| review_items | RESETAR | user_language_id → user_languages.id; CASCADE |
| grammar_topics | GLOBAL: NÃO TOCAR | language_id → languages.id; RESTRICT/NO ACTION |
| user_grammar_progress | RESETAR | grammar_topic_id → grammar_topics.id; RESTRICT/NO ACTION; user_language_id → user_languages.id; CASCADE |
| pronunciation_attempts | RESETAR | study_session_id → study_sessions.id; SET NULL; user_language_id → user_languages.id; CASCADE |
| listening_activities | RESETAR | study_session_id → study_sessions.id; SET NULL; user_language_id → user_languages.id; CASCADE |
| writing_submissions | RESETAR | study_session_id → study_sessions.id; SET NULL; user_language_id → user_languages.id; CASCADE |
| assessments | RESETAR | user_language_id → user_languages.id; CASCADE |
| assessment_questions | RESETAR | assessment_id → assessments.id; CASCADE |
| assessment_attempts | RESETAR | assessment_id → assessments.id; CASCADE; question_id → assessment_questions.id; SET NULL |
| placement_tests | RESETAR | user_id → users.id; CASCADE |
| placement_test_sections | RESETAR | test_id → placement_tests.id; CASCADE |
| placement_items | GLOBAL: NÃO TOCAR | — |
| placement_test_answers | RESETAR | item_id → placement_items.id; CASCADE; test_id → placement_tests.id; CASCADE |
| progress_metrics | RESETAR | user_language_id → user_languages.id; CASCADE |
| user_preferences | PRESERVAR/UPDATE LIMITADO | default_language_id → languages.id; SET NULL; user_id → users.id; CASCADE |
| placement_item_deliveries | RESETAR | item_id → placement_items.id; CASCADE; test_id → placement_tests.id; CASCADE |
| content_sources | GLOBAL: NÃO TOCAR | language_id → languages.id; SET NULL |
| content_units | GLOBAL: NÃO TOCAR | language_id → languages.id; SET NULL; source_id → content_sources.id; CASCADE |
| content_reviews | PRESERVAR | content_unit_id → content_units.id; CASCADE; reviewer_user_id → users.id; SET NULL |
| lesson_content_usages | RESETAR | content_unit_id → content_units.id; CASCADE; lesson_id → lessons.id; CASCADE |
| audit_logs | PRESERVAR | user_id → users.id; SET NULL |
| sessions | PRESERVAR | user_id → users.id; CASCADE |
| password_reset_tokens | PRESERVAR | user_id → users.id; CASCADE |
| learning_objectives | GLOBAL: NÃO TOCAR | language_id → languages.id; RESTRICT/NO ACTION |
| user_objective_progress | RESETAR | objective_id → learning_objectives.id; CASCADE; user_language_id → user_languages.id; CASCADE |
| learning_attempts | RESETAR | curriculum_block_id → curriculum_blocks.id; SET NULL; lesson_id → lessons.id; SET NULL; objective_id → learning_objectives.id; CASCADE; user_language_id → user_languages.id; CASCADE; vocabulary_item_id → vocabulary_items.id; SET NULL |
| learning_evidence | RESETAR | attempt_id → learning_attempts.id; CASCADE; objective_id → learning_objectives.id; CASCADE; user_language_id → user_languages.id; CASCADE; vocabulary_item_id → vocabulary_items.id; SET NULL |
| learning_errors | RESETAR | attempt_id → learning_attempts.id; SET NULL; objective_id → learning_objectives.id; SET NULL; user_language_id → user_languages.id; CASCADE; vocabulary_item_id → vocabulary_items.id; SET NULL |
| remediations | RESETAR | error_id → learning_errors.id; CASCADE; next_attempt_id → learning_attempts.id; SET NULL |
| teaching_flow_sessions | RESETAR | curriculum_block_id → curriculum_blocks.id; SET NULL; lesson_id → lessons.id; SET NULL; objective_id → learning_objectives.id; CASCADE; user_language_id → user_languages.id; CASCADE |
| memory_schedules | RESETAR | review_item_id → review_items.id; SET NULL; user_language_id → user_languages.id; CASCADE |
| memory_review_events | RESETAR | memory_schedule_id → memory_schedules.id; CASCADE |
| learning_progress_snapshots | RESETAR | user_language_id → user_languages.id; CASCADE |
| learning_progress_events | RESETAR | user_language_id → user_languages.id; CASCADE |
| ai_response_cache | GLOBAL: NÃO TOCAR | — |

## Ordem exata dos DELETEs

1. remediations
2. learning_evidence
3. learning_errors
4. teaching_flow_sessions
5. learning_attempts
6. exercise_attempts
7. exercises
8. curriculum_blocks
9. memory_review_events
10. lesson_content_usages
11. lesson_activity_attempts
12. lesson_activities
13. curriculum_days
14. conversation_messages
15. assessment_attempts
16. writing_submissions
17. vocabulary_examples
18. pronunciation_attempts
19. memory_schedules
20. listening_activities
21. lessons
22. learning_plan_items
23. curriculum_weeks
24. conversations
25. assessment_questions
26. vocabulary_items
27. user_objective_progress
28. user_grammar_progress
29. study_sessions
30. review_items
31. progress_metrics
32. placement_test_sections
33. placement_test_answers
34. placement_item_deliveries
35. learning_progress_snapshots
36. learning_progress_events
37. learning_plans
38. learning_goals
39. curricula
40. assessments
41. user_languages
42. placement_tests

Depois: UPDATE pontual users.native_language, UPDATE pontual user_preferences, pós-condições; COMMIT ou ROLLBACK.

## Resultado verificado desta rodada

- Comando no backend: `.venv/Scripts/python.exe -m pytest tests/test_reset_test_user_learning.py tests/test_reset_test_user_learning_postgres.py tests/test_native_language.py tests/test_admin_users.py -o addopts= --tb=short`.
- **76 passed, 2 skipped, 4 warnings em 66.18s; exit 0**. Os 2 skips são PostgreSQL ausente. Warnings existentes de path_separator Alembic.
- 28 casos do reset SQLite/HTTP passaram; 43 casos native_language e 5 admin existentes também passaram.
- A revisão independente identificou inbound FK entre schemas e concorrência de soft pointers; proteções adicionadas. Depois apontou 3 campos obrigatórios ausentes na fixture PG; corrigidos e seed validado sob SQLite com FKs/NOT NULL. Nenhum teste PostgreSQL foi efetivamente executado.
- py_compile dos três arquivos Python passou; git diff --check passou (avisos de conversão LF/CRLF nos arquivos anteriores).
- Não foram alterados frontend, migration 0016, Session Builder, regra 36/12, Teaching Engine, lógica mastery, pricing, STT/TTS ou dados globais. Suíte geral não reexecutada; diagnóstico anterior FLAKY_TIMING_TEST não foi modificado nem somado como aprovação da suíte.
- Arquivos novos do reset são untracked. git diff --stat sem --no-index mostra apenas alterações da rodada anterior de reparo, preservadas: 3 files changed, 49 insertions(+), 10 deletions(-).
- Estado ao finalizar: M repair_fr_b1_incident.py, M test_fr_b1_incident_repair.py, M test_fr_b1_legacy_reuse.py (anteriores); ?? reset_test_user_learning.py, ?? test_reset_test_user_learning.py, ?? test_reset_test_user_learning_postgres.py, ?? este relatório e ?? plano de reset.
- Nenhuma execução no banco local do projeto nem produção; testes usam bancos temporários. Nenhum commit, push ou deploy.
