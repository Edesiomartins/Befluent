# Backend BeFluent
API FastAPI do BeFluent, com PostgreSQL, sessões opacas em cookie HTTP-only e integrações modulares em modo mock.

## Desenvolvimento
1. Crie um ambiente virtual e execute `pip install -r requirements.txt`.
2. Copie `.env.example` para `.env` e ajuste apenas valores locais.
3. Execute `alembic upgrade head` (aplica `0001_initial` e `0002_ensure_schema`).
4. Opcional: `python scripts/check_schema.py` para listar colunas/tabelas ausentes.
5. Defina `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_PASSWORD` e rode `python scripts/create_admin.py`.
6. Inicie com `uvicorn app.main:app --reload`.

No Docker/Coolify, o `scripts/entrypoint.sh` já roda `alembic upgrade head` antes do Uvicorn.

Testes: `pytest`. A API usa `/api/v1`; o healthcheck é `GET /health`.

## Migrations
- `0001_initial`: cria tabelas via `create_all` (legado; não altera colunas de tabelas existentes).
- `0002_ensure_schema`: adiciona tabelas/colunas/índices ausentes de forma não destrutiva.
