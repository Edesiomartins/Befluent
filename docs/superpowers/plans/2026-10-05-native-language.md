# Native language implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Persistir língua nativa sem inferência e separar alvo/apoio no backend.

**Architecture:** User possui native_language global nullable. Política central alimenta prompts, guard, envelope e seleção de conteúdo; APIs existentes são estendidas compatibilmente.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Alembic, pytest; nenhuma dependência nova.

**Spec:** ../specs/2026-10-05-native-language-design.md

## Global constraints

Sem frontend, commit, push, deploy, backfill de usuários, tradução em massa ou refatoração de fala. Preservar alterações editoriais existentes. Documentar contrato antes dos endpoints.

## Review focus

Omissão vs null explícito; nativo igual ao alvo; material estático incompatível; conteúdo/cache anterior à troca; explicação inglesa fora do par permitido.

- [x] Contrato e testes iniciais: docs/frontend-backend-contract.md, tests/test_native_language.py.
- [x] Persistência e APIs: models, schemas, api/profile.py, onboarding.py, auth.py, migration0016 e teste de head/migration.
- [x] Política/contexto/prompts/guard: language_codes.py, language_policy.py, learner_context.py, prompts/library.py, editorial_validation.py, ai.py, envelope.
- [x] Seleção/entrega e conteúdo legado: lessons/progression/conversas/escrita/Teaching Engine; não reutilizar apoio incompatível; testes focais.
- [x] Revisão, suíte final, relatório20itens, status/diff, Segundo Cérebro pela ponte.

Execução inline conforme pedido direto de implementação do usuário; commits e deploys proibidos.
