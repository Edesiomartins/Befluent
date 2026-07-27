# BeFluent

BeFluent é um webapp para aprendizado de idiomas com apoio de inteligência artificial.

**BeFluent é uma aplicação independente, com autenticação e banco próprios.**

O subdomínio de produção planejado é `befluent.medquesthub.com.br` (backend sugerido: `api-befluent.medquesthub.com.br`).

Slogan: **Aprenda. Pratique. Fale.**  
Assinatura: *Uma plataforma MedQuestHub AI* · *Powered by MedQuestHub AI*

## Idiomas iniciais

- Inglês (`en`)
- Espanhol da Espanha (`es-ES`)
- Francês (`fr`)
- Japonês (`ja`)
- Mandarim (`zh-CN`)

## Objetivo

Criar um tutor acessível pelo navegador, com foco em conversação, compreensão auditiva, vocabulário, gramática, pronúncia, revisão e acompanhamento de progresso.

## Arquitetura

- **Frontend:** Next.js 15 (App Router), TypeScript, Tailwind CSS
- **Backend:** FastAPI, SQLAlchemy, Alembic, Pydantic
- **Banco:** PostgreSQL 18
- **IA:** OpenRouter (modular) com modo mock
- **Áudio:** STT/TTS modulares com provedor `mock` por padrão
- **Auth:** cookie HTTP-only `befluent_session` (sem JWT em `localStorage`)
- **Infra:** Docker Compose (preparado para Coolify no futuro)

Documentação detalhada em `docs/`.

## Estado atual

Primeira versão funcional local, com integrações externas em modo simulado por padrão. Cadastro público e multi-usuário autorizados. Sem deploy nesta etapa.

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
4. Em produção futura: `COOKIE_SECURE=true`, HTTPS, CORS restrito ao domínio real.

## Variáveis

Veja `.env.example`. Nunca coloque segredos no frontend. Apenas `NEXT_PUBLIC_API_URL` é pública.

Locais padrão:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

## Execução sem Docker

### Banco

Suba um PostgreSQL e ajuste `DATABASE_URL` (exemplo: `postgresql+psycopg://befluent:CHANGE_ME@localhost:5432/befluent`).

### Backend

```powershell
cd backend
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
npm run dev
```

## Docker Compose

Serviços: `befluent-frontend`, `befluent-backend`, `befluent-postgres`.

```powershell
docker compose up --build
```

### Volume legado

Instalações antigas usavam o volume `fluentia_pg_data`. O Compose atual cria `befluent_pg_data`. Para preservar dados locais antigos, mapeie o volume antigo explicitamente ou faça dump/restore — não apague volumes sem backup.

## Autenticação

Fluxo:

1. Cadastro público (`POST /api/v1/auth/register`) — **sem** login automático
2. Redirecionamento para `/login?cadastro=ok`
3. Login (`POST /api/v1/auth/login`) com cookie `befluent_session`
4. Onboarding / dashboard

Logout revoga a sessão. CSRF protegido nas rotas mutáveis (login/register isentos quando necessário).

## OpenRouter / STT / TTS

Integrações modulares. Com `AI_MOCK_MODE=true` e provedores `mock`, a API responde sem chaves externas.

## Migrations

Alembic em `backend/alembic`. Não apague migrations existentes.

- `0001_initial` — criação inicial (`create_all`).
- `0002_ensure_schema` — **obrigatória em bancos já existentes**: adiciona colunas/tabelas ausentes sem DROP.

No Coolify, o entrypoint do backend executa `alembic upgrade head` no start. Após redeploy do backend, confira logs e `python scripts/check_schema.py`.

Não use `stamp head` sem auditoria. Não apague volumes nem o PostgreSQL.

## Testes

```powershell
cd backend
python -m pytest -q

cd ../frontend
npm install
npm run typecheck
npm test
npm run build
```

## Coolify (futuro)

Ver `docs/deployment-coolify.md`. Não fazer deploy nesta etapa. Domínio planejado: `https://befluent.medquesthub.com.br`.

## Histórico técnico

O projeto nasceu como **Fluentia**. Em 2026 a identidade foi renomeada para **BeFluent**, mantendo código, funcionalidades e stack. Referências residuais ao nome antigo podem existir apenas em histórico Git, migrations antigas ou volumes legados.

## Licença / uso

Uso pessoal e institucional MedQuestHub AI. Sem integração de login com MedQuestHub nesta fase.
