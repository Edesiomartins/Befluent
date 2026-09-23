# Task 2 — Aplicar entitlement no backend e expor estado ao frontend

## Escopo
- Fonte de requisitos: `.superpowers/sdd/2026-09-23-vocabulary-cycle-entitlements/task-2-brief.md` e `AGENTS.md`.
- Backend como autoridade: ativação, onboarding e lookups protegidos consultam `user_can_access_language`.
- Catálogos continuam exibindo todos os idiomas ativos e passam a anotar `access_state`.
- Contrato documentado no código: `available`, `entitled`, `locked`.
- Sem preços, checkout, TTS, STT, Piper, push ou deploy.

## RED
- `pytest tests/test_language_access_api.py`
  - Resultado esperado: falhou.
  - Saída principal: 7 falhas e 1 sucesso.
  - Falhas esperadas: ausência de `access_state`; ativação/onboarding não criavam grant `legacy`; flag ligada ainda permitia acesso sem grant; lookup de perfil existente ignorava o serviço central.
- `npm test -- language-access.test.tsx`
  - Resultado esperado: falhou.
  - Saída principal: import `@/components/language-access` não resolvido porque o componente ainda não existia.

## GREEN
- `pytest tests/test_language_access_api.py`
  - `8 passed in 4.67s`
- `npm test -- language-access.test.tsx`
  - `1 passed`, `2 passed`
- Repetição após ajuste frontend:
  - `pytest tests/test_language_access_api.py`
  - `8 passed in 8.42s`
  - `npm test -- language-access.test.tsx languages.test.tsx onboarding.test.tsx`
  - `3 passed`, `15 passed`

## Regressão focada
- `pytest tests/test_language_entitlements.py tests/test_api.py tests/test_language_access_api.py`
  - `61 passed, 2 warnings in 36.07s`
  - Warnings: `DeprecationWarning` do Alembic sobre `path_separator`; não relacionado à tarefa.
- `npm test -- language-access.test.tsx languages.test.tsx onboarding.test.tsx`
  - `3 passed`, `15 passed`

## Typecheck/Lints
- `npm run typecheck`
  - Falhou em arquivo não alterado: `tests/tts-lab.test.tsx(105,68)` usa opção `exact` em `getAllByRole`, incompatível com o tipo atual de `ByRoleOptions`.
- `ReadLints` nos arquivos editados:
  - Sem erros.

## Arquivos alterados
- `.env.example`
- `backend/.env.example`
- `backend/app/api/helpers.py`
- `backend/app/api/language_profiles.py`
- `backend/app/api/languages.py`
- `backend/app/api/onboarding.py`
- `backend/app/schemas/__init__.py`
- `backend/app/services/language_access.py`
- `backend/tests/test_language_access_api.py`
- `frontend/app/(app)/languages/page.tsx`
- `frontend/components/language-access.tsx`
- `frontend/hooks/use-active-language.ts`
- `frontend/tests/language-access.test.tsx`

## Decisões
- `available`: flag `LANGUAGE_ENTITLEMENTS_ENABLED=false`; preserva o acesso atual.
- `entitled`: flag ligada e entitlement vigente pelo serviço central.
- `locked`: flag ligada e ausência de entitlement vigente.
- `/languages` e `/languages/mine` apenas anotam `access_state`; não escondem idiomas.
- `activate` e onboarding negam `locked` com `403 language_locked`.
- `activate` e onboarding criam grant `legacy` idempotente quando a flag está desligada.
- `user_language` protege rotas de estudo que já dependem desse helper.
- `language_profiles` filtra a listagem para perfis acessíveis e retorna `403 language_locked` em lookup direto de perfil bloqueado.
- Frontend exibe estado via `LanguageAccessBadge`, desabilita ativação de idioma bloqueado e o hook de idioma ativo ignora perfis bloqueados.

## Riscos e observações
- `npm run typecheck` permanece bloqueado por erro pré-existente em `tests/tts-lab.test.tsx`.
- A proteção central cobre rotas que usam `user_language`; endpoints que não usam esse helper precisam continuar sendo revisados em tarefas futuras se acessarem conteúdo protegido por outro caminho.
- Não executei push/deploy.
