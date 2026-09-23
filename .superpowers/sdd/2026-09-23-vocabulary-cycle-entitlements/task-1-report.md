# Task 1 — Modelo e serviço central de entitlement

Status: concluído localmente, sem push/deploy e sem alteração de secrets/produção.

## Arquivos alterados

- `backend/alembic/versions/0012_language_entitlements.py` — migration aditiva da tabela `language_entitlements`, índices e backfill `legacy`.
- `backend/app/models/__init__.py` — modelo `LanguageEntitlement`.
- `backend/app/core/config.py` — flag `language_entitlements_enabled` com default `False`.
- `backend/app/services/language_access.py` — serviço central `user_can_access_language` e helper `ensure_legacy_language_entitlement`.
- `backend/tests/test_language_entitlements.py` — testes TDD do serviço, helper e migration.
- `backend/tests/test_alembic_revision_ids.py` — atualização do head Alembic esperado para `0012_language_entitlements`.

## Decisões

- A flag `LANGUAGE_ENTITLEMENTS_ENABLED` fica desligada por padrão via `language_entitlements_enabled: bool = False`, preservando acesso aberto.
- `user_can_access_language(db, user_id, language_code)` retorna `True` imediatamente com a flag desligada. Com a flag ligada, exige idioma existente e pelo menos uma concessão vigente.
- Concessão vigente significa `status == "active"`, `cancelled_at is None`, `starts_at <= now UTC` e `expires_at` nulo ou futuro.
- `admin`, `trial`, `promotion`, `legacy` e futura `subscription` são tratados pela mesma regra de vigência; não há dependência de billing.
- `ensure_legacy_language_entitlement` é idempotente por `(user_id, language_id, source="legacy")`, usa timestamp UTC e não faz commit para respeitar a transação chamadora.
- A migration é tolerante ao padrão legado de `0001_initial` que usa `Base.metadata.create_all()` com models atuais: cria tabela/índices apenas se ausentes e sempre executa backfill.
- O backfill usa o próprio `user_languages.id` como id do grant legado para caber em `String(36)` e evitar ids `legacy-<uuid>` maiores que a coluna.

## Evidência RED

### RED inicial — modelo/serviço ausentes

Comando:

```powershell
cd C:\Users\DrEdesio\Documents\PROJETOS\Befluent\backend
pytest tests/test_language_entitlements.py
```

Saída relevante:

```text
ERROR collecting tests/test_language_entitlements.py
ImportError: cannot import name 'LanguageEntitlement' from 'app.models'
1 error
```

### RED de self-review — id de backfill longo

Comando:

```powershell
pytest tests/test_language_entitlements.py::test_migration_cria_entitlements_legacy_para_user_languages_existentes
```

Saída relevante:

```text
AssertionError: 'legacy-11111111-1111-4111-8111-111111111111' != '11111111-1111-4111-8111-111111111111'
1 failed
```

## Evidência GREEN

### Teste focado da Task 1

Comando:

```powershell
pytest tests/test_language_entitlements.py
```

Saída relevante:

```text
8 passed, 2 warnings in 5.29s
```

Warnings: `DeprecationWarning` do Alembic sobre `path_separator`, já existente no uso do `Config`.

### Correção do backfill

Comando:

```powershell
pytest tests/test_language_entitlements.py::test_migration_cria_entitlements_legacy_para_user_languages_existentes
```

Saída relevante:

```text
1 passed, 2 warnings in 1.21s
```

## Testes finais

Comando:

```powershell
pytest tests/test_language_entitlements.py tests/test_alembic_revision_ids.py tests/test_placement_migration.py
```

Saída:

```text
20 passed, 25 warnings in 21.77s
```

Lints consultados via Cursor para os arquivos editados:

```text
No linter errors found.
```

Checagem de diff:

```powershell
git diff --check
```

Resultado: exit code `0`, sem erros de whitespace.

## Riscos e observações

- A migration foi testada em SQLite, que é o ambiente dos testes; não foi executada contra PostgreSQL real nesta tarefa.
- Os warnings do Alembic sobre `path_separator` permanecem como ruído existente de configuração de testes.
- A Task 1 não aplica a autorização em endpoints nem frontend; isso permanece para as próximas tasks do plano.
- Não houve push, deploy, alteração de produção ou secrets.
