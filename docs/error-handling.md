# Tratamento de Erros — Fluentia

Relacionados: [api-specification.md](api-specification.md), [user-flows.md](user-flows.md), [observability.md](observability.md).

## Princípios

- Mensagens em português, claras, sem jargão.
- Não esconder falhas.
- Não vazar internals em produção.
- Indicar se pode tentar novamente.
- Registrar log quando útil para operação.

## Catálogo

### Erro de validação

- **API:** 400 `validation_error`
- **Mensagem:** “Não foi possível validar os dados enviados.”
- **Ação:** corrigir campos
- **Log:** warning com detalhes técnicos sem PII excessiva
- **Retry:** não, até corrigir

### Não autenticado

- **API:** 401 `unauthenticated`
- **Mensagem:** “Você precisa entrar para continuar.”
- **Ação:** ir ao login
- **Log:** info/audit leve
- **Retry:** após login

### Não autorizado

- **API:** 403 `forbidden`
- **Mensagem:** “Você não tem permissão para esta ação.”
- **Ação:** voltar
- **Log:** warning/audit
- **Retry:** não

### Não encontrado

- **API:** 404 `not_found`
- **Mensagem:** “Conteúdo não encontrado.”
- **Ação:** dashboard / lista
- **Log:** info
- **Retry:** não

### Conflito

- **API:** 409 `conflict`
- **Mensagem:** “Esta operação conflita com o estado atual.”
- **Ação:** atualizar tela e tentar de novo
- **Log:** info/warning
- **Retry:** sim, após refresh

### Limite de tamanho

- **API:** 413 `payload_too_large`
- **Mensagem:** “O arquivo ou texto é grande demais.”
- **Ação:** reduzir tamanho / gravar trecho menor
- **Log:** info
- **Retry:** sim, com payload menor

### Indisponibilidade do banco

- **API:** 503 `database_unavailable`
- **Mensagem:** “O serviço está temporariamente indisponível.”
- **Ação:** tentar mais tarde
- **Log:** error/critical
- **Retry:** sim, depois

### Timeout de IA

- **API:** 503 `ai_timeout`
- **Mensagem:** “O tutor demorou demais para responder.”
- **Ação:** tentar novamente
- **Log:** warning (model, latency)
- **Retry:** sim (controlado)

### Resposta inválida da IA

- **API:** 503 `invalid_ai_response`
- **Mensagem:** “Não foi possível interpretar a resposta do tutor.”
- **Ação:** tentar novamente
- **Log:** warning (sem dump completo)
- **Retry:** sim; fallback de modelo se configurado

### Falha de STT

- **API:** 503 `stt_failed`
- **Mensagem:** “Não foi possível transcrever o áudio.”
- **Ação:** repetir gravação ou usar texto
- **Log:** warning
- **Retry:** sim + fallback textual

### Falha de TTS

- **API:** 503 `tts_failed`
- **Mensagem:** “Não foi possível gerar o áudio.”
- **Ação:** ler o texto / tentar de novo
- **Log:** warning
- **Retry:** sim; UI segue com texto

### Falha de microfone

- **API:** não necessariamente (erro de cliente)
- **Mensagem:** “Sem acesso ao microfone.”
- **Ação:** permissões do navegador ou modo texto
- **Log:** opcional no cliente
- **Retry:** após conceder permissão

### Perda de conexão

- **API:** falha de rede no cliente
- **Mensagem:** “Sem conexão. Verifique a internet.”
- **Ação:** tentar novamente
- **Log:** quando a requisição chegar parcialmente — conforme caso
- **Retry:** sim

### Erro inesperado

- **API:** 500 `internal_error`
- **Mensagem:** “Ocorreu um erro inesperado.”
- **Ação:** tentar de novo / voltar ao dashboard
- **Log:** error com stack no servidor
- **Retry:** sim, com cautela

## Padrão de resposta (ilustrativo)

```json
{
  "error": {
    "code": "ai_timeout",
    "message": "O tutor demorou demais para responder.",
    "retryable": true,
    "request_id": "exemplo-nao-real"
  }
}
```

## UI

- Mapear `code` → mensagem amigável (fallback para `message`).
- Botão “Tentar novamente” se `retryable`.
- Preservar progresso local já confirmado pelo servidor.
