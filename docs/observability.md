# Observabilidade — Fluentia

Relacionados: [error-handling.md](error-handling.md), [security.md](security.md), [privacy.md](privacy.md), [deployment-coolify.md](deployment-coolify.md).

## Objetivo

Entender saúde, erros e desempenho sem expor dados sensíveis de estudo.

## Logs estruturados

Formato preferencial: JSON em stdout.

Campos típicos:

- timestamp
- level
- message
- request_id
- route
- status_code
- latency_ms
- task_type (se IA)
- error_code

## Níveis de log

| Nível | Uso |
|---|---|
| DEBUG | Só desenvolvimento |
| INFO | Eventos normais |
| WARNING | Degradação / retry |
| ERROR | Falha de requisição/serviço |
| CRITICAL | Sistema indisponível |

## Correlação de requisições

- Gerar `request_id` no edge/backend.
- Propagar nos logs e, se útil, na resposta de erro.
- Não usar dados pessoais como correlator.

## Métricas (planejadas)

- Taxa de erro HTTP
- Latência p50/p95 das rotas críticas
- Contagem de falhas de IA / STT / TTS
- Tempo de queries lentas (quando instrumentado)
- Uso estimado de tokens (agregado)

Ferramenta específica de métricas = decisão pendente (pode começar com logs + health).

## Saúde da aplicação

- `GET /health`: liveness básica.
- Opcionalmente: readiness incluindo DB (sem vazar detalhes internos).

## Erros de IA

Logar: provider, model label, timeout/invalid/fallback, latency.

Não logar: prompt completo, resposta completa com dados do aluno (por padrão).

## Tempo de resposta

- Medir rotas de auth, conversa, speech, reviews.
- Alertar futuramente se p95 ultrapassar limiar (limiar = decisão pendente).

## Falhas de áudio

- Contadores de permissão/format/size/provider failure.
- Separar falha de cliente vs provedor.

## Uso de banco

- Pool exhaustion / erros de conexão.
- Migrações falhas no boot.

## Alertas futuros

Quando houver base estável:

- health failing
- taxa de 5xx
- falha contínua OpenRouter
- disco/volume

Canal de alerta = decisão pendente.

## Privacidade dos logs

Proibido por padrão:

- senhas, cookies, Authorization
- chaves de API
- áudio
- textos longos de conversa/redação

## Retenção

- Prazo de logs = decisão pendente.
- Menor retenção possível compatível com operação.

## Endpoint de healthcheck

- `GET /health` público (sem dados sensíveis).
- Usado por Docker/Coolify.
- Não autenticar (para probes), mas não expor secrets/config.
