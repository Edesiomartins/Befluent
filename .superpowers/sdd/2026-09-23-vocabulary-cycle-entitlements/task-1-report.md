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

---

## Fix round 1/5 — achados Important

Status: correções aplicadas localmente, sem push/deploy.

### Arquivos alterados no fix

- `backend/app/models/__init__.py` — adicionada `UniqueConstraint` nomeada em `(user_id, language_id, source)`.
- `backend/alembic/versions/0012_language_entitlements.py` — adicionada a mesma unicidade na criação da tabela e reforço via índice único quando a tabela já existe.
- `backend/app/services/language_access.py` — extraída função de domínio `entitlement_is_current`; helper `ensure_legacy_language_entitlement` agora usa savepoint e recupera a linha vencedora após `IntegrityError`.
- `backend/tests/test_language_entitlements.py` — testes de constraint, corrida/idempotência e estados inconsistentes.

### Decisões do fix

- A unicidade canônica é `uq_language_entitlements_user_language_source`, sobre `(user_id, language_id, source)`.
- O helper legado faz uma leitura inicial e, se precisar inserir, faz `db.begin_nested()` para isolar a tentativa em savepoint. Se a constraint colidir, ele consulta novamente e retorna o grant vencedor, sem `rollback()` na transação externa.
- A regra de vigência fica documentada e concentrada em `entitlement_is_current`: só `status == "active"` com `cancelled_at is None` e janela temporal vigente autoriza acesso.
- Estados inconsistentes negados explicitamente: `active` com `cancelled_at` preenchido e `cancelled` sem `cancelled_at`.

### Evidência RED do fix

Comando:

```powershell
pytest tests/test_language_entitlements.py
```

RED I-2 inicial:

```text
ImportError: cannot import name 'entitlement_is_current' from 'app.services.language_access'
1 error
```

RED I-1 após extração da regra canônica:

```text
FAILED test_constraint_impede_grant_duplicado_por_origem
Failed: DID NOT RAISE <class 'sqlalchemy.exc.IntegrityError'>

FAILED test_helper_legacy_recupera_grant_vencedor_apos_conflito
AssertionError: recovered.id != winner.id

FAILED test_migration_cria_entitlements_legacy_para_user_languages_existentes
Failed: DID NOT RAISE <class 'sqlalchemy.exc.IntegrityError'>

3 failed, 8 passed, 2 warnings
```

### Evidência GREEN do fix

Comando:

```powershell
pytest tests/test_language_entitlements.py
```

Saída:

```text
11 passed, 2 warnings in 7.17s
```

### Regressões proporcionais do fix

Comando:

```powershell
pytest tests/test_language_entitlements.py tests/test_alembic_revision_ids.py tests/test_placement_migration.py
```

Saída:

```text
23 passed, 25 warnings in 26.29s
```

Lints consultados via Cursor para os arquivos editados:

```text
No linter errors found.
```

### Commit do fix

Commit local do código/testes do fix round 1: `75007b7` (`Fix language entitlement invariants`).
