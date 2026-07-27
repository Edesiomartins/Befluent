# Fluentia

Fluentia é um webapp pessoal e privado para aprendizado de idiomas com apoio de inteligência artificial.

## Idiomas iniciais

- Inglês (`en`)
- Espanhol da Espanha (`es-ES`)
- Francês (`fr`)
- Japonês (`ja`)
- Mandarim (`zh-CN`)

## Objetivo

Criar um tutor pessoal acessível pelo navegador, com foco em conversação, compreensão auditiva, vocabulário, gramática, pronúncia, revisão e acompanhamento de progresso.

## Arquitetura

- **Frontend:** Next.js 15 (App Router), TypeScript, Tailwind CSS
- **Backend:** FastAPI, SQLAlchemy, Alembic, Pydantic
- **Banco:** PostgreSQL 18
- **IA:** OpenRouter (modular) com modo mock
- **Áudio:** STT/TTS modulares com provedor `mock` por padrão
- **Auth:** cookie HTTP-only (sem JWT em `localStorage`)
- **Infra:** Docker Compose (Redis não obrigatório)

Documentação detalhada em `docs/`.

## Estado atual

Primeira versão funcional local, com integrações externas em modo simulado por padrão.

## Requisitos

- Python **3.11 ou 3.12** (recomendado; evite 3.14 sem wheels)
- Node.js 22+
- PostgreSQL 18 (local ou via Docker)
- Docker Desktop (opcional, para Compose)

## Configuração

1. Copie `.env.example` para `.env` e preencha os valores.
2. Defina pelo menos:
   - `POSTGRES_PASSWORD`
   - `SESSION_SECRET`
   - `INITIAL_ADMIN_NAME`
   - `INITIAL_ADMIN_EMAIL`
   - `INITIAL_ADMIN_PASSWORD` (mín. 8 caracteres)
3. Mantenha `AI_MOCK_MODE=true`, `STT_PROVIDER=mock` e `TTS_PROVIDER=mock` até configurar chaves reais.

## Variáveis

Veja `.env.example`. Nunca coloque segredos no frontend. Apenas `NEXT_PUBLIC_API_URL` é pública.

## Execução sem Docker

### Banco

Suba um PostgreSQL e ajuste `DATABASE_URL`.

### Backend

```powershell
cd backend
# Preferir Python 3.11/3.12
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
python -c "from app.core.database import SessionLocal; from app.services.seed import seed_languages; db=SessionLocal(); seed_languages(db); db.close()"
$env:INITIAL_ADMIN_EMAIL="seu@email.local"
$env:INITIAL_ADMIN_PASSWORD="sua-senha-forte"
$env:INITIAL_ADMIN_NAME="Seu Nome"
python scripts/create_admin.py
uvicorn app.main:app --reload --port 8000
```

### Frontend

```powershell
cd frontend
npm install
$env:NEXT_PUBLIC_API_URL="http://localhost:8000"
npm run dev
```

## Execução com Docker

```powershell
copy .env.example .env
# edite .env
docker compose up --build
```

Serviços:

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Health: http://localhost:8000/health
- PostgreSQL: localhost:5432

Criar admin (com Compose no ar):

```powershell
docker compose exec fluentia-backend python scripts/create_admin.py
```

## Migrations

```powershell
cd backend
alembic upgrade head
alembic current
```

## Testes

```powershell
# Backend
cd backend
.\.venv\Scripts\python.exe -m pytest -q

# Frontend
cd frontend
npm test
npm run typecheck
```

## Modo mock

Quando `AI_MOCK_MODE=true` ou chaves vazias:

- conversação usa respostas simuladas;
- STT/TTS usam provedores mock;
- a UI indica modo demonstração;
- a aplicação **não** deve falhar por falta de chave.

## SRS provisório

A primeira versão usa agendador **simples substituível** (D-019). FSRS permanece decisão pendente (P-010).

## Resolução de erros comuns

| Problema | Causa provável | Ação |
|---|---|---|
| `pip` falha no `pydantic-core` | Python 3.14 sem wheel | Use Python 3.11/3.12 |
| Login 401 | Admin não criado | Rode `create_admin.py` |
| CSRF 403 | Cookie/header ausente | Garanta `credentials: include` e header `X-CSRF-Token` |
| CORS | Origem diferente | Ajuste `CORS_ORIGINS` / `FRONTEND_URL` |
| Microfone bloqueado | Permissão do navegador | Use alternativa textual |

## Preparação para Coolify

- Use os Dockerfiles de `frontend/` e `backend/`
- Configure secrets no Coolify (nunca no git)
- HTTPS obrigatório em produção (`COOKIE_SECURE=true`)
- Rode migrations no start (entrypoint do backend)
- Não faça deploy nesta etapa sem testes locais

## Documentação

Consulte `docs/` para visão, stack, API, segurança, roadmap e critérios de aceitação.
