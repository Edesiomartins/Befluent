# Deploy no Coolify — BeFluent

**Não executar deploy nesta etapa.** Planejamento apenas.

Relacionados: [architecture.md](architecture.md), [security.md](security.md), [testing-strategy.md](testing-strategy.md), [observability.md](observability.md).

## Objetivo

Publicar o BeFluent em VPS própria via Coolify, com HTTPS, após testes locais.

Domínio planejado do frontend: `https://befluent.medquesthub.com.br`  
Backend sugerido: `https://api-befluent.medquesthub.com.br`

## Volume e nomes internos

Compose local preserva serviços/volumes `fluentia-*` / `fluentia_pg_data` por compatibilidade com instalações existentes.
A marca visual é **BeFluent**. No Coolify, **não** renomeie serviços, banco, usuário PostgreSQL ou volumes só por causa da marca.

## Migration segura no Coolify (obrigatória se login falha)

Sintoma típico: `UndefinedColumn` / `column does not exist` (ex.: `users.last_login_at`, `users.is_active`, `sessions.*`).

Causa: a migration `0001_initial` usava `create_all`, que **não adiciona colunas** em tabelas já existentes quando `alembic_version` já está em `0001_initial`.

Correção: revision `0002_ensure_schema` (incremental, sem DROP).

### Como aplicar sem recriar infraestrutura

1. Faça deploy/redeploy **apenas** do serviço backend (imagem nova com a migration).
2. O entrypoint já executa `alembic upgrade head` antes do Uvicorn.
3. Confirme nos logs: `Running migrations...` e ausência de erros de coluna.
4. Opcional, no container do backend:

```bash
alembic current
alembic heads
python scripts/check_schema.py
```

5. Não use `alembic stamp head` sem confirmar que o schema já está completo.
6. Não use `docker compose down -v`, drop database ou recriação do PostgreSQL.

### Variáveis a revisar manualmente no Coolify

- `FRONTEND_ORIGIN` / `FRONTEND_URL` / `CORS_ORIGINS` → origem real do frontend (não `localhost` em produção)
- `COOKIE_SECURE=true` com HTTPS
- `COOKIE_DOMAIN=.medquesthub.com.br` (obrigatório se frontend e API forem subdomínios diferentes; sem isso o CSRF falha com 403 porque o JS não lê o cookie)
- `SESSION_COOKIE_NAME` → `befluent_session` (ou mantenha `fluentia_session` se quiser preservar cookies atuais)
- `NEXT_PUBLIC_API_URL` no frontend → URL pública do backend
- Nunca versionar secrets (`DATABASE_URL`, `SESSION_SECRET`, chaves OpenRouter)

## Volume legado

Compose local continua com `fluentia_pg_data` / serviços `fluentia-*`.

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
- STT (`STT_PROVIDER`, `GROQ_API_KEY`, etc.)
- TTS (`TTS_PROVIDER=piper_api`, `TTS_BASE_URL=https://piper.medquesthub.com.br`, `TTS_API_KEY`, `TTS_SPEED=1.0`)
- CORS / URLs públicas
- E-mail (`RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `DAILY_EMAIL_KEY`)
- Flags de ambiente (`production`)

Nunca inventar valores reais neste documento.

## E-mail diário (tarefa agendada)

O e-mail com a missão do dia **não** sai sozinho: o backend não tem agendador.
Quem dispara é uma tarefa agendada (*Scheduled Task*) do Coolify chamando a
rota de disparo.

1. Gerar uma chave longa e aleatória e colocá-la em `DAILY_EMAIL_KEY` no
   serviço do backend. **Sem essa variável a rota responde 503 e nada é
   enviado** — é assim de propósito: ausência de configuração fecha a porta.
2. Criar a tarefa agendada no backend, com a frequência desejada (ex.: `0 7 * * *`
   para 7h no fuso do servidor) e o comando:

   ```sh
   curl -fsS -X POST https://api-befluent.medquesthub.com.br/api/v1/daily-email/dispatch -H "X-Dispatch-Key: $DAILY_EMAIL_KEY"
   ```

3. Conferir a resposta: `{"sent":n,"skipped":n,"failed":n,"date":"AAAA-MM-DD"}`.

### Segunda tarefa: e-mail de correção

O e-mail de correção sai depois que uma sessão é encerrada. O gatilho é interno
(a sessão fecha dentro de uma requisição do próprio aluno), mas o **envio** é
feito por varredura, para a resposta do último exercício não esperar o provedor
de e-mail e para uma falha do Resend ser tentada de novo em vez de perdida.

Criar uma segunda tarefa agendada, com a **mesma** `DAILY_EMAIL_KEY`:

- Frequência sugerida: `*/15 * * * *` (a cada 15 minutos).
- Comando:

  ```sh
  curl -fsS -X POST https://api-befluent.medquesthub.com.br/api/v1/correction-email/dispatch -H "X-Dispatch-Key: $DAILY_EMAIL_KEY"
  ```

- Resposta: `{"sent":n,"skipped":n,"failed":n,"window_hours":24}`.

Regras desta tarefa:

- **Uma correção por sessão.** Rodar de novo devolve `skipped`, não um segundo
  e-mail.
- **Janela de 24 horas.** Sessão encerrada há mais tempo não é varrida — é o que
  impede a primeira execução de despejar o histórico inteiro na caixa de
  entrada. A janela cobre com folga um cron de 15 minutos e ainda absorve horas
  de indisponibilidade do provedor.
- **Sessão sem resposta corrigível é pulada** (sessão só de "continuar", sem
  produção): não há o que corrigir, então não há e-mail.
- O conteúdo vem do boletim já gravado na hora da resposta. A correção nunca é
  recalculada no momento do envio.

Volume esperado, para dimensionar o plano do Resend: **um e-mail de cada tipo
por usuário ativo por dia** — o disparo diário usa o idioma ativo, e `is_active`
é exclusivo por usuário. Com o plano gratuito (3.000/mês, teto de 100/dia) o
limite prático é ~50 usuários ativos, não o volume de um dono só.

Regras que valem em produção:

- **Um e-mail por perfil por dia.** Rodar a tarefa duas vezes no mesmo dia não
  manda dois e-mails (o segundo volta como `skipped`).
- **Falha de envio não consome o dia:** `failed` significa que a próxima
  execução tenta de novo.
- **Perfil sem cronograma ativo é pulado**, sem e-mail dizendo "não há nada".
- **Desligar** = remover a tarefa agendada ou limpar `DAILY_EMAIL_KEY`. Não há
  link de descadastro no e-mail; o app é privado, de um dono.
- O dia usado é a data UTC do servidor, igual ao resto do cronograma. O horário
  de entrega é o horário do cron.

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
