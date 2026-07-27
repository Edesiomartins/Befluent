# Deploy no Coolify — Fluentia

**Não executar deploy nesta etapa.** Planejamento apenas.

Relacionados: [architecture.md](architecture.md), [security.md](security.md), [testing-strategy.md](testing-strategy.md), [observability.md](observability.md).

## Objetivo

Publicar o Fluentia em VPS própria via Coolify, com HTTPS, após testes locais.

## Componentes

- Repositório Git
- Dockerfile do frontend (Next.js)
- Dockerfile do backend (FastAPI)
- Docker Compose (local e referência de serviços)
- PostgreSQL
- Domínio + HTTPS
- Variáveis de ambiente / secrets
- Volumes (dados do Postgres; temporários de áudio se necessário)
- Healthchecks
- Backups
- Logs
- Atualização e rollback
- Smoke test pós-deploy

## Repositório Git

- Código versionado.
- Sem secrets commitados.
- Tags/releases para deploys rastreáveis (prática recomendada).

## Dockerfiles

- Frontend: build multi-stage; variáveis públicas apenas se não secretas.
- Backend: imagem Python enxuta; migrations controladas no start ou job dedicado (decisão na Fase 1/7).
- Usuário não-root quando viável.

## Docker Compose

Uso principal: desenvolvimento local e documentação de dependências.

Serviços típicos:

- `frontend`
- `backend`
- `db` (PostgreSQL)

Redis: **não** incluir como obrigatório.

## Frontend / Backend / PostgreSQL

- Frontend fala com backend via URL interna/pública configurada.
- Backend conecta no Postgres por variável `DATABASE_URL` (nome exato na implementação).
- Credenciais só em secrets.

## Domínio e HTTPS

- Domínio apontando à VPS.
- HTTPS via Coolify/proxy.
- Necessário para cookies Secure e captura de áudio.

## Variáveis de ambiente

Grupos:

- Database
- Auth/session
- OpenRouter
- STT/TTS (quando definidos)
- CORS / URLs públicas
- Flags de ambiente (`production`)

Nunca inventar valores reais neste documento.

## Volumes

- Volume persistente do PostgreSQL.
- Diretório temporário de áudio com limpeza (não como arquivo eterno).
- Armazenamento externo = decisão pendente.

## Healthchecks

- `GET /health` no backend.
- Health do frontend (HTTP 200 na home/login).
- Postgres ready antes do backend receber tráfego.

## Backups

- Backup automático do Postgres.
- Teste de restore periódico.
- Retenção alinhada a [privacy.md](privacy.md).

## Logs

- Coletar logs stdout dos containers.
- Sem segredos.
- Retenção limitada.

## Atualização

1. Testar localmente.
2. Merge/tag.
3. Deploy no Coolify.
4. Rodar migrações.
5. Smoke test.
6. Monitorar erros.

## Rollback

- Manter imagem/versão anterior.
- Reverter app se smoke falhar.
- Cuidado com migrações irreversíveis — preferir migrações expansivas/compatíveis.

## Smoke test pós-deploy

- Health ok
- HTTPS ok
- Login
- Dashboard carrega
- Logout

## Checklist antes de desligar qualquer serviço anterior

Só aplicável se houver versão antiga rodando:

1. Backup completo do banco atual.
2. Nova versão saudável (smoke ok) por período de observação.
3. Variáveis e DNS conferidos.
4. Plano de rollback testado.
5. Confirmação explícita do proprietário para desligar o antigo.
6. Só então desligar o serviço anterior.

## Fora de escopo agora

- Executar deploy.
- Criar infraestrutura real.
- Escolher provedores de áudio.
