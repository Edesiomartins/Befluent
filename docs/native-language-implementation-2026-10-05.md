# BeFluent — língua nativa e política pedagógica (2026-10-05)

## 1. Estado inicial
HEAD `d6e6516`; auditorias estrutural/editorial anteriores preservadas. Backend sem native_language persistido; LearnerContext fixava português do Brasil e prompts permitiam português como apoio universal. Mudanças de frontend feitas em paralelo pertencem a outro trabalho.

## 2. Arquitetura encontrada
User global; UserLanguage contém alvo e CEFR por competência; UserPreference.default_language_id é alvo, não nativo. LearnerContext alimenta biblioteca de prompts. Lições curadas/mock e IA compartilham envelope; conteúdo e tentativas são persistidos. Vocabulário/SRS possui campos legados translation_pt.

## 3. Armazenamento
User.native_language: String(32), nullable, sem default. Catálogo reutiliza language_codes, acrescentando pt-BR apenas como nativo. Códigos exatos; não cria curso português nem infere língua pelo navegador/interface/idioma estudado.

## 4. Migration
`backend/alembic/versions/0016_native_language.py`, após 0015_lesson_report. Adiciona coluna nullable sem backfill; downgrade remove coluna. Guard de existência atende revisions antigas que criam metadata atual. Teste restaura tabela realmente legada e verifica usuário existente NULL, ausência de default e roundtrip. Não aplicada ao banco do projeto ou produção.

## 5. Contrato final
Ver `docs/frontend-backend-contract.md`, documentado antes dos endpoints. Perfil/onboarding/auth expõem native_language, native_language_required e opções. Omissão preserva; null explícito limpa; código inválido 422. LessonPayload expõe target_language, native_language, política e support_visibility; apoio em *_native é separado de texto-alvo. Cadastro conserva formato antigo; escolha no onboarding/perfil.

## 6. Endpoints alterados
Auth login/register/me (respostas); GET/PATCH profile; onboarding status/complete; lessons geração/leitura/report/tentativas/ciclo; conversas start/messages/histórico; escrita e placement writing; vocabulário; SRS due; Teaching Flow/slice/geração de atividades. Encerrar/abandonar lições e conversas continua disponível mesmo após mudar o nativo. Nenhuma rota de fala foi refatorada.

## 7. Política pedagógica
`language_policy`: PRE_A1/A1 apoio frequente; A2 breve; B1 pontual; B2 quase só alvo; C1/C2 somente solicitado/necessário. Visibilidade prominent/discreet/spot/expandable/off, sem percentuais. Nativo ausente: só alvo e flag de escolha pendente. A política orienta geração e contrato, sem alegar que certifica linguisticamente a resposta de um modelo.

## 8. Builders/prompts
LearnerContext explicita target_language/native_language/CEFR e política por competência. Biblioteca remove apoio PT universal, exige separação *_native e a regra literal de nenhuma terceira língua. OpenRouter recebe par completo; corpus PT não é selecionado para outro nativo. Envelope declara provenance; cache aceita nativo na identidade. Escrita recebe o par; heurística preserva métricas e suprime aviso/feedback PT incompatível. Analogias PT e carryover traduzido PT não entram no contexto de outro nativo.

## 9. Bloco “A lógica”
Frontend consultado somente para leitura: GrammarLesson apresenta lesson.explanation. Falhas confirmadas na origem arquitetural: contexto fixava PT, prompt de apoio não refletia escolha nativa e guard anterior só verificava campos-alvo, deixando explanation sem controle. O guard agora rejeita exemplos conhecidos de explicação inglesa fora do par, inclusive em conteúdo persistido. Sem ID/payload da lição de produção, a origem exata (IA, template ou legado) permanece não comprovada; não atribuí o incidente a um gerador específico.

## 10. Correção aplicada
Persistência + política + contexto + prompts + guard determinístico + proteção de entrega/reuso. Lições incompatíveis com nativo atual recebem erro explícito, sem apagar dados. Conversas guardam snapshot no campo source já existente; não injetam histórico incompatível. SRS/Teaching Engine/ciclo e vocabulário PT não disfarçam traduções como inglês.

## 11. Compatibilidade
Usuários antigos permanecem NULL e podem acessar conta/perfil/onboarding/encerramento. Conteúdo dependente do apoio requer escolha (409 native_language_required). Nativo incompatível com corpus atual: native_support_unavailable. Lições históricas após troca: lesson_native_language_mismatch; conversas: conversation_native_language_mismatch. Login/cadastro não selecionam PT silenciosamente. Fixtures antigas de conteúdo PT agora declaram PT explicitamente; testes de legado anulam a escolha.

## 12. Arquivos criados nesta rodada
- backend/alembic/versions/0016_native_language.py
- backend/app/services/language_policy.py
- backend/tests/test_native_language.py
- docs/superpowers/specs/2026-10-05-native-language-design.md
- docs/superpowers/plans/2026-10-05-native-language.md
- docs/native-language-implementation-2026-10-05.md
Arquivos novos da auditoria anterior permanecem no status; não são novos resultados desta rodada.

## 13. Arquivos alterados nesta rodada
APIs: auth, profile, onboarding, lessons, conversations, writing, placement_tests, vocabulary, reviews, teaching. Modelo User e schemas; services language_codes, learner_context, language_policy (novo), ai, ai_cache, editorial_validation (já novo da auditoria), lesson_envelope, progression, writing_evaluation. Biblioteca de prompts; script audit_editorial apenas para declarar PT no contexto estático, sem reexecutar auditoria. Contrato; fixtures e testes de adaptação/providers/cobertura/interesses/forma/seleção/editorial/head. Frontend preservado, sem edição por este agente.

## 14. Testes adicionados
43 casos: persistência/consulta/update/omissão/null/invalidade/legado/onboarding; sete faixas CEFR; prompts de todos os modos com os três parâmetros; fr+PT/de+EN/en+PT com geração simulada e campos separados; guard inglês em apoio/alvo; ausência e corpus indisponível; cache; migration roundtrip; áudio mantém FR para nativo PT/EN/NULL; histórico conversa; SRS, ciclos nas duas direções e nova entrega curada com lógica inglesa conhecida.

## 15. Testes focais
241 passed, 6 warnings, 170.12s na integração inicial. Após reforços finais: 81 passed, 4 warnings, 43.32s (43 casos de língua nativa + 38 editoriais). O primeiro início da suíte completa foi interrompido para incluir guard no envelope de conteúdo curado; não é contado como validação. Avisos são de configuração Alembic path_separator. compileall passou; diff check sem erros de whitespace.

## 16. Suíte completa
Primeira execução completa: 1531 passed, 4 failed, 38 warnings, 720.31s, exit 1. Falhas em conteúdo legado de raiz list/string/number/bool: a nova checagem convertia para dict antes da validação. Corrigido centralmente com Mapping e preservado contrato vazio seguro. Regressão: 69 passed, 4 warnings, 40.54s (ciclos lexicais + língua nativa). Execução completa final: **1535 passed, zero failed, 38 warnings, 695.31s, exit 0**. Nenhum teste pulado.

## 17. Segundo Cérebro
Registro confirmado pela ponte em 02_DECISOES/DECISAO_BEFLUENT_LINGUA_NATIVA.md e 01_PROJETOS/BEFLUENT.md; INDEX_DECISOES atualizado. Nenhuma estrutura paralela de memória.

## 18. Riscos, pendências e próximos passos
- Corpus estático/mock só possui apoio PT; outro nativo depende de IA já configurada ou enriquecimento editorial futuro. Nenhum provedor/modelo foi escolhido/alterado.
- Gramática estática conserva explanation legado e declara explanation_native/support_language/primary_explanation_available=false. Não há tradução automática para criar explicação-alvo; adequação completa desse campo em níveis avançados permanece editorialmente pendente.
- Guard detecta textos ingleses conhecidos/padrões específicos; não é detector universal de línguas ou certificação CEFR. Geração real não foi validada com credenciais externas.
- SQLite migration validada; PostgreSQL/produção não executados. Antes de qualquer publicação futura, validar banco e migração com backup verificado, e coordenar contrato com o frontend paralelo.
- Campos translation_pt e corpus Teaching Engine continuam legados; suporte a novos nativos exigirá provenance e conteúdo correspondente, não simples renomeação.
- Origem da lição específica de produção requer seu ID/payload; histórico é preservado, mas reuso incompatível é bloqueado.
- Sem commit, push, merge ou deploy.

## 19. git diff --stat
Snapshot final inclui auditoria anterior e frontend paralelo; arquivos não rastreados não entram no diff stat padrão.

```text
 backend/app/api/auth.py                         |   8 +-
 backend/app/api/conversations.py                |  14 +++-
 backend/app/api/lessons.py                      |  28 ++++++-
 backend/app/api/onboarding.py                   |   5 ++
 backend/app/api/placement_tests.py              |   1 +
 backend/app/api/profile.py                      |  31 +++++--
 backend/app/api/reviews.py                      |   2 +
 backend/app/api/teaching.py                     |  16 ++++
 backend/app/api/vocabulary.py                   |   4 +
 backend/app/api/writing.py                      |   1 +
 backend/app/models/__init__.py                  |   1 +
 backend/app/prompts/library.py                  |  32 +++++---
 backend/app/schemas/__init__.py                 |   3 +
 backend/app/services/activity_generator.py      | 102 +++++++++++-------------
 backend/app/services/ai.py                      |  18 ++++-
 backend/app/services/ai_cache.py                |   4 +
 backend/app/services/content_repository.py      |   8 ++
 backend/app/services/grammar_practice.py        |   4 +-
 backend/app/services/language_codes.py          |  14 ++++
 backend/app/services/learner_context.py         |  14 +++-
 backend/app/services/lesson_bank.py             |  25 ++++--
 backend/app/services/lesson_bank_it.py          |   4 +-
 backend/app/services/lesson_envelope.py         |  15 +++-
 backend/app/services/progression.py             |  12 ++-
 backend/app/services/writing_evaluation.py      |  19 ++++-
 backend/tests/conftest.py                       |   4 +-
 backend/tests/test_ai_speech_providers.py       |   1 +
 backend/tests/test_alembic_revision_ids.py      |   2 +-
 backend/tests/test_learning_interests.py        |   2 +
 backend/tests/test_lesson_adaptation.py         |   1 +
 backend/tests/test_lesson_bank_coverage.py      |   1 +
 backend/tests/test_lexical_form.py              |   1 +
 backend/tests/test_vocabulary_selection.py      |   1 +
 docs/frontend-backend-contract.md               |  41 ++++++++++
 frontend/app/(app)/cronograma/dia/[id]/page.tsx |  37 +++++++--
 frontend/app/(app)/layout.tsx                   |   5 +-
 frontend/app/(app)/learn/[mode]/page.tsx        |  31 +++++--
 frontend/app/(app)/learn/objetivo/page.tsx      |   8 +-
 frontend/app/(app)/onboarding/page.tsx          |  92 ++++++++++++++++++---
 frontend/app/(app)/profile/page.tsx             |  64 ++++++++++++++-
 frontend/components/lesson-modes.tsx            |  68 +++++++++++++---
 frontend/components/teaching-activity.tsx       |  98 +++++++++++++++--------
 frontend/components/ui.tsx                      |  10 ++-
 frontend/hooks/use-active-language.ts           |   6 +-
 frontend/hooks/use-lesson.ts                    |   6 +-
 frontend/tests/lesson-adaptation.test.tsx       |  13 +--
 frontend/tests/onboarding.test.tsx              |   7 +-
 frontend/tests/use-active-language.test.tsx     |   5 +-
 frontend/types/api.ts                           |   2 +
 frontend/types/lesson.ts                        |  13 ++-
 frontend/types/teaching.ts                      |   7 +-
 51 files changed, 713 insertions(+), 198 deletions(-)
```

## 20. git status --short
Snapshot final; frontend paralelo preservado e não atribuído a esta rodada.

```text
 M backend/app/api/auth.py
 M backend/app/api/conversations.py
 M backend/app/api/lessons.py
 M backend/app/api/onboarding.py
 M backend/app/api/placement_tests.py
 M backend/app/api/profile.py
 M backend/app/api/reviews.py
 M backend/app/api/teaching.py
 M backend/app/api/vocabulary.py
 M backend/app/api/writing.py
 M backend/app/models/__init__.py
 M backend/app/prompts/library.py
 M backend/app/schemas/__init__.py
 M backend/app/services/activity_generator.py
 M backend/app/services/ai.py
 M backend/app/services/ai_cache.py
 M backend/app/services/content_repository.py
 M backend/app/services/grammar_practice.py
 M backend/app/services/language_codes.py
 M backend/app/services/learner_context.py
 M backend/app/services/lesson_bank.py
 M backend/app/services/lesson_bank_it.py
 M backend/app/services/lesson_envelope.py
 M backend/app/services/progression.py
 M backend/app/services/writing_evaluation.py
 M backend/tests/conftest.py
 M backend/tests/test_ai_speech_providers.py
 M backend/tests/test_alembic_revision_ids.py
 M backend/tests/test_learning_interests.py
 M backend/tests/test_lesson_adaptation.py
 M backend/tests/test_lesson_bank_coverage.py
 M backend/tests/test_lexical_form.py
 M backend/tests/test_vocabulary_selection.py
 M docs/frontend-backend-contract.md
 M frontend/app/(app)/cronograma/dia/[id]/page.tsx
 M frontend/app/(app)/layout.tsx
 M frontend/app/(app)/learn/[mode]/page.tsx
 M frontend/app/(app)/learn/objetivo/page.tsx
 M frontend/app/(app)/onboarding/page.tsx
 M frontend/app/(app)/profile/page.tsx
 M frontend/components/lesson-modes.tsx
 M frontend/components/teaching-activity.tsx
 M frontend/components/ui.tsx
 M frontend/hooks/use-active-language.ts
 M frontend/hooks/use-lesson.ts
 M frontend/tests/lesson-adaptation.test.tsx
 M frontend/tests/onboarding.test.tsx
 M frontend/tests/use-active-language.test.tsx
 M frontend/types/api.ts
 M frontend/types/lesson.ts
 M frontend/types/teaching.ts
?? backend/alembic/versions/0016_native_language.py
?? backend/app/services/editorial_validation.py
?? backend/app/services/language_policy.py
?? backend/scripts/audit_editorial.py
?? backend/tests/test_editorial_integrity.py
?? backend/tests/test_native_language.py
?? docs/editorial-audit-2026-10-05.md
?? docs/editorial-audit-after.json
?? docs/editorial-audit-before.json
?? docs/editorial-audit-priorities-2026-10-05.md
?? docs/native-language-implementation-2026-10-05.md
?? docs/superpowers/plans/2026-10-05-native-language.md
?? docs/superpowers/specs/2026-10-05-native-language-design.md
?? frontend/app/(app)/lingua-nativa/
?? frontend/components/bilingual-text.tsx
?? frontend/components/native-language-context.tsx
?? frontend/components/native-language-form.tsx
?? frontend/components/native-language-gate.tsx
?? frontend/lib/bilingual.ts
?? frontend/lib/native-language.ts
?? frontend/tests/bilingual.test.tsx
?? frontend/tests/native-language.test.tsx
```
