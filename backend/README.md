# Backend Fluentia
API FastAPI do Fluentia, com PostgreSQL, sessões opacas em cookie HTTP-only e integrações modulares em modo mock.

## Desenvolvimento
1. Crie um ambiente virtual e execute `pip install -r requirements.txt`.
2. Copie `.env.example` para `.env` e ajuste apenas valores locais.
3. Execute `alembic upgrade head`.
4. Defina `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_PASSWORD` e rode `python scripts/create_admin.py`.
5. Inicie com `uvicorn app.main:app --reload`.

Testes: `pytest`. A API usa `/api/v1`; o healthcheck é `GET /health`.
