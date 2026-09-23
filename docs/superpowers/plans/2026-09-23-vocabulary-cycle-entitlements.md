# Vocabulary Learning Cycle V2 + Language Entitlements — Implementation Plan

> **Spec:** `docs/superpowers/specs/2026-09-23-vocabulary-cycle-entitlements-design.md`

**Goal:** Implementar o ciclo lexical no Teaching Engine V2 e a fundação de
entitlements por idioma sem billing, sem bloquear usuários e sem alterar
STT/TTS.

**Architecture:** TeachingFlowSession, LearningAttempt e LearningEvidence são
estendidos de forma aditiva para atividades ligadas a VocabularyItem. O estado
lexical usa MemorySchedule. LanguageEntitlement é uma concessão independente de
pagamento, consultada por um serviço central e desativada por flag.

**Stack:** FastAPI, SQLAlchemy, Alembic, pytest, Next.js/React, TypeScript,
Vitest/Testing Library.

## Global Constraints

- Trabalhar diretamente na `main` por autorização explícita do usuário.
- TDD: cada comportamento novo deve ser observado falhando antes da implementação.
- Não alterar Piper, TTS, STT, Speech Coach, fases existentes, scoring ou
  mastery de objetivos não lexicais.
- Campos e migrations devem ser aditivos e retrocompatíveis.
- `LANGUAGE_ENTITLEMENTS_ENABLED` deve ter default `false`.
- Não implementar billing, checkout, preços, gateway ou webhook.
- Não fazer push nem deploy.
- Interface permanece em português.

---

### Task 1: Modelo e serviço central de entitlement

**Files:**
- Create: `backend/alembic/versions/0012_language_entitlements.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/core/config.py`
- Create: `backend/app/services/language_access.py`
- Test: `backend/tests/test_language_entitlements.py`

**Steps:**
1. Escrever testes para flag desligada, grant vigente, expirado/cancelado,
   origens `admin`/`trial` sem pagamento e ausência de grant com flag ligada.
2. Rodar o teste e confirmar falha pela ausência do modelo/serviço.
3. Criar `LanguageEntitlement` e migration aditiva com índices e backfill de
   todos os pares existentes em `user_languages`.
4. Implementar `user_can_access_language` e helper idempotente de grant
   `legacy`; períodos usam timestamps UTC.
5. Rodar `pytest tests/test_language_entitlements.py`.

### Task 2: Aplicar entitlement no backend e expor estado ao frontend

**Files:**
- Modify: `backend/app/api/helpers.py`
- Modify: `backend/app/api/languages.py`
- Modify: `backend/app/api/language_profiles.py`
- Modify: `backend/app/api/onboarding.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/.env.example`
- Modify: `.env.example`
- Modify: `frontend/hooks/use-active-language.ts`
- Create: `frontend/components/language-access.tsx`
- Test: `backend/tests/test_language_access_api.py`
- Test: `frontend/tests/language-access.test.tsx`

**Steps:**
1. Escrever testes API que provem: flag desligada preserva ativação; flag ligada
   nega sem grant; grant permite; novas ativações com flag desligada criam
   `legacy`; payloads expõem `available|entitled|locked`.
2. Escrever teste do componente/estado reutilizável do frontend.
3. Confirmar falhas.
4. Fazer `user_language` e a ativação consultarem somente o serviço central.
   Endpoints de catálogo apenas informam estado; não ocultam idiomas.
5. Ajustar onboarding para respeitar a mesma autorização e criar grant legacy
   somente com a flag desligada.
6. Implementar tipos/componente frontend sem preço ou checkout.
7. Rodar os testes backend/frontend focados.

### Task 3: Persistência lexical integrada ao Teaching Engine

**Files:**
- Create: `backend/alembic/versions/0013_vocabulary_learning_cycle.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/core/teaching.py`
- Modify: `backend/app/services/teaching_engine.py`
- Modify: `backend/app/services/memory_engine.py`
- Create: `backend/app/services/vocabulary_learning.py`
- Test: `backend/tests/test_vocabulary_learning.py`

**Steps:**
1. Escrever testes para matrícula idempotente de `VocabularyItem` e
   `VocabularyExample`, tentativa/evidência por item e cinco modalidades.
2. Confirmar falhas.
3. Adicionar vínculos opcionais de `lesson_id`/`vocabulary_item_id` necessários
   a TeachingFlowSession, LearningAttempt, LearningEvidence e LearningError.
4. Adicionar EvidenceType lexical sem mudar a política padrão dos objetivos.
5. Implementar matrícula e registro lexical usando LearningAttempt/Evidence.
6. Criar/atualizar MemorySchedule de vocabulário; manter ReviewItem sincronizado.
7. Implementar domínio lexical por diversidade de evidência e produção, nunca
   por um único acerto.
8. Rodar os testes focados e regressões do Teaching Engine/memória.

### Task 4: Gerador determinístico do ciclo lexical

**Files:**
- Modify: `backend/app/services/activity_generator.py`
- Modify: `backend/app/services/teaching_flow.py`
- Modify: `backend/app/services/teaching_slice.py`
- Test: `backend/tests/test_vocabulary_activity_generator.py`

**Steps:**
1. Escrever testes do conjunto completo: presentation, recognition,
   reverse_recognition, listening_recognition e production.
2. Asserir contratos de áudio separados:
   `audio_target_type=vocabulary_item|example_sentence` e `audio_text` exato.
3. Asserir que listening oculta texto/resposta e usa termo, não frase.
4. Asserir que erro lexical avança e agenda review posterior, sem repetir
   imediatamente o mesmo exercício.
5. Asserir que item forte/dominado tem frequência reduzida.
6. Confirmar falhas e implementar o gerador/adaptador lexical.
7. Preservar o gerador de objetivos gerais sem mudança de comportamento.
8. Rodar os testes focados e `test_teaching_engine_v2.py`.

### Task 5: Endpoints do ciclo para lição e currículo

**Files:**
- Modify: `backend/app/api/lessons.py`
- Modify: `backend/app/api/curriculum.py`
- Modify: `backend/app/services/curriculum_teaching.py`
- Modify: `backend/app/services/progression.py`
- Modify: `backend/app/schemas/__init__.py`
- Test: `backend/tests/test_vocabulary_cycle_api.py`

**Steps:**
1. Escrever testes de start/restore/answer para lição standalone e bloco de
   vocabulário do currículo.
2. Cobrir ownership, entitlement no backend e compatibilidade de lição antiga.
3. Confirmar falhas.
4. Iniciar/restaurar TeachingFlowSession lexical a partir da Lesson persistida.
5. Submeter respostas pelo Teaching Engine; produção oral recebe apenas a
   transcrição.
6. No fechamento do bloco, evitar duplicar matrícula/review já criados pelo
   ciclo.
7. Rodar os testes de API, currículo, progressão e memória relacionados.

### Task 6: Interface do ciclo e acessibilidade

**Files:**
- Modify: `frontend/types/teaching.ts`
- Modify: `frontend/components/teaching-activity.tsx`
- Modify: `frontend/components/lesson-modes.tsx`
- Modify: `frontend/app/(app)/cronograma/dia/[id]/page.tsx`
- Modify: `frontend/app/(app)/learn/[mode]/page.tsx`
- Test: `frontend/tests/vocabulary-cycle.test.tsx`
- Modify/Test: testes existentes de Teaching Activity e áudio

**Steps:**
1. Escrever testes de presentation com áudio separado de termo/frase e labels
   acessíveis.
2. Escrever testes de recognition, reverse, listening oculto e production.
3. Cobrir conteúdo antigo e falha independente de um controle de áudio.
4. Confirmar falhas.
5. Renderizar as atividades lexicais no componente compartilhado, mantendo o
   estilo atual.
6. Para fala, reutilizar `Recorder`; enviar somente transcript ao endpoint.
7. Manter fallback para o card legado quando não houver sessão de ciclo.
8. Rodar Vitest focado, typecheck e lint dos arquivos alterados.

### Task 7: Review adaptativo e compatibilidade

**Files:**
- Modify: `backend/app/api/reviews.py`
- Modify: `backend/app/services/memory_engine.py`
- Modify: `backend/app/services/vocabulary_selection.py`
- Modify: `frontend/app/(app)/learn/[mode]/page.tsx`
- Test: `backend/tests/test_vocabulary_review_cycle.py`
- Test: `frontend/tests/vocabulary-review.test.tsx`

**Steps:**
1. Escrever testes que provem retorno posterior de erro, prioridade de item
   fraco e redução de item dominado.
2. Cobrir ReviewItem legado sem MemorySchedule e conteúdo antigo sem exemplo.
3. Confirmar falhas.
4. Adaptar fila e payload para modalidade de revisão sem quebrar ratings atuais.
5. Garantir sincronização MemorySchedule → ReviewItem.
6. Atualizar UI de review apenas onde houver payload lexical V2; preservar
   fallback legado.
7. Rodar testes focados e regressões de review/memory.

### Task 8: Documentação e verificação integral

**Files:**
- Create/Modify: documentação arquitetural pertinente em `docs/`
- Modify: exemplos de ambiente, se ainda necessário

**Steps:**
1. Documentar fluxo lexical, evidências, entitlement e procedimento futuro para
   ligar a flag com segurança.
2. Rodar migrations em banco de teste.
3. Backend: `pytest`.
4. Backend: `ruff check app tests`.
5. Frontend: `npm test`.
6. Frontend: `npm run typecheck`.
7. Frontend: `npm run lint`.
8. Frontend: `npm run build`.
9. Verificar `git diff`, ausência de secrets e ausência de alterações em
   Piper/STT/TTS.
10. Fazer revisão final de aderência à spec. Não fazer push/deploy.
