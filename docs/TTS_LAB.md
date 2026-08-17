# TTS Lab

## Objetivo

Ferramenta administrativa e temporária para comparar modelos de Text-to-Speech
disponíveis pela OpenRouter, usando exatamente o mesmo texto: qualidade,
latência, tamanho do áudio e (quando disponível) custo.

**Não faz parte do fluxo de TTS de produção.** As aulas, o Speech Coach e o
tutor de apoio continuam usando `app/services/speech.py`
(`hexgrad/kokoro-82m` fixo, configurado por `TTS_PROVIDER`/`TTS_MODEL`). O
TTS Lab é um módulo isolado (`app/services/tts_lab.py` +
`app/api/tts_lab.py`) que não é importado por nenhum desses fluxos e não os
altera.

## Rota

- Frontend: `/admin/tts-lab` (dentro do grupo `(app)`, logo exige sessão
  autenticada como qualquer outra tela).
- Backend: `GET /api/v1/tts-lab/models`, `POST /api/v1/tts-lab/generate`.

## Acesso

O projeto ainda **não tem papel de admin/role no `User`** (só
`email`/`password_hash`/`name`/`is_active`). Em vez de criar um sistema de
autorização novo para esta ferramenta temporária, o acesso é restrito por
allow-list de e-mail:

```
TTS_LAB_ALLOWED_EMAILS=prof.edesio@gmail.com
```

Comportamento:

- Lista vazia (padrão) → **ninguém** acessa, em qualquer ambiente
  (fail-closed).
- Comparação por e-mail, case-insensitive, contra o usuário autenticado
  (`current_user`, mesma sessão por cookie usada no resto da API).
- Fora da allow-list → `403 tts_lab_forbidden`.

**Para desativar a ferramenta**, basta remover/limpar
`TTS_LAB_ALLOWED_EMAILS` no `.env` — não precisa remover rota nem código.

**Limitação conhecida:** isso não é um sistema de autorização de verdade
(não há papéis, não há auditoria de acesso além dos logs padrão da API). É
suficiente para uma ferramenta interna de uso pontual por uma única pessoa;
não deve ser usado como modelo para features com múltiplos administradores.

## Modelos configurados

Definidos em `TTS_LAB_MODELS` (`backend/app/services/tts_lab.py`) — única
fonte de verdade, sem hardcode espalhado pelo backend ou frontend:

| id | provider | supports_speed | supports_voice | formato | free |
|---|---|---|---|---|---|
| `deepgram/flux-tts:free` | deepgram | não (rejeita, 400) | sim (obrigatória) | mp3 | sim |
| `fish-audio/s2.1-pro-free:free` | fish-audio | sim | não (não testada) | mp3 | sim |
| `hexgrad/kokoro-82m` | hexgrad | sim | sim | mp3 | não |
| `google/gemini-3.1-flash-tts-preview` | google | não (não testado, modelo pago) | sim (obrigatória) | **pcm** (não mp3/wav) | não |

Essas capacidades foram **confirmadas com chamadas reais à OpenRouter**
durante a implementação (ver "Teste real OpenRouter" abaixo), não
presumidas — os primeiros testes (com os quatro modelos sem `voice`)
retornaram `400` para Deepgram e Gemini com a mensagem
`"An explicit voice is required for this TTS provider."`; ajustar
`voice`/`response_format` corrigiu os dois:

- **Deepgram Flux** exige `voice` de uma lista fixa (`flux-alexis-en`,
  `flux-bree-en`, `flux-brittany-en`, … 35 vozes `flux-*-en` no total,
  devolvida pelo próprio erro 400) e **rejeita `speed`** (400 mesmo com
  `voice` válida).
- **Fish Audio S2.1 Pro** aceitou `speed=1.2` sem erro (200); `voice`
  explícita não foi testada (lista de vozes desconhecida), por isso
  `supports_voice` continua `False` — não presumimos um valor que
  funcionaria.
- **Kokoro 82M** é o modelo já validado em produção (mesmo contrato de
  `speech.py`).
- **Gemini 3.1 Flash TTS (Preview)** exige `voice` (testado com `"Kore"`,
  aceito) e **só devolve `response_format="pcm"`** — pedir `mp3` dá 400
  (`Gemini TTS only supports response_format="pcm". Got "mp3".`). O
  header de resposta confirma `audio/pcm;rate=24000;channels=1`. `speed`
  não foi testado para não multiplicar chamadas pagas num modelo preview;
  fica `False` por precaução.

### Como adicionar um novo modelo

Adicione uma entrada em `TTS_LAB_MODELS` com `display_name`, `provider`,
`supports_speed`, `supports_voice`, `supported_formats`, `default_voice` e
`free`. Nenhuma outra mudança de código é necessária — o endpoint
`/models` e a página já leem dessa config.

## Como os áudios são enviados ao frontend

`POST /generate` chama `POST {OPENROUTER_BASE_URL}/audio/speech`
diretamente (mesmo contrato OpenAI-compatível já usado em produção) e
devolve, em uma única resposta JSON:

```json
{
  "model": "hexgrad/kokoro-82m",
  "audio_base64": "...",
  "content_type": "audio/mpeg",
  "latency_ms": 620,
  "audio_size_bytes": 86016,
  "free_model": false,
  "cost_available": false,
  "estimated_cost": null
}
```

O frontend decodifica o base64 para `Blob`, cria um `object URL` e toca no
`<audio controls>` nativo. Nenhum arquivo é gravado em disco no servidor;
`object URL`s são revogados (`URL.revokeObjectURL`) antes de cada nova
geração do mesmo modelo e no unmount da página, evitando vazamento de
memória no navegador.

## Como a latência é medida

`time.monotonic()` antes e depois da chamada `httpx.post` a
`/audio/speech`; a diferença vira `latency_ms`. Como a chamada não é
streamada, não há como medir `time_to_first_byte` separadamente sem mudar o
contrato HTTP — não inventamos essa métrica.

### PCM da Gemini vira WAV antes de chegar ao frontend

O `<audio controls>` nativo do navegador não decodifica PCM cru. Como a
Gemini só devolve PCM, `app/services/tts_lab.py::_pcm_to_wav` envolve os
bytes num cabeçalho WAV mínimo (`wave.open`, `sampwidth=2` — 16 bits,
padrão de PCM de TTS; taxa e canais lidos do `content-type` real da
resposta, com fallback 24000 Hz/mono se o header não vier). O
`content_type` devolvido ao frontend nesse caso é `audio/wav`, não
`audio/pcm`. Profundidade de 16 bits não tem confirmação por header — é a
única suposição não verificada nesta implementação; se a Gemini mudar
esse detalhe, o áudio toca com velocidade/tom errado (sintoma fácil de
notar num teste manual).

## Custo

A resposta da OpenRouter para `/audio/speech` não traz uso/custo
estruturado, então `estimated_cost` é sempre `null` e `cost_available` é
sempre `false`. `free_model` reflete apenas se o id do modelo termina em
`:free` na config estática — não é uma garantia de preço real, só uma
etiqueta informativa.

## Pausa entre parágrafos

Nenhum dos quatro modelos tem suporte a SSML confirmado. A opção "Pausa
entre parágrafos" no frontend é só uma heurística de espaçamento de texto
(`\n` extras entre parágrafos antes de enviar `input`) — não é uma pausa
garantida pelo provedor, e nenhuma tag SSML é enviada.

## Segurança

- `OPENROUTER_API_KEY` só é lida no backend; nunca é enviada ao frontend.
- Logs (`TTS Lab request model=... status=... latency_ms=... response_size=...`)
  nunca incluem o header `Authorization` nem a chave.
- Erros do provedor viram mensagens genéricas (`APIError`) — sem stack
  trace nem corpo bruto da resposta do provedor.

## Rate limiting / proteção

- "Gerar em todos" dispara no máximo **uma chamada por modelo**, em série
  (não em paralelo), e fica desabilitado enquanto a sequência roda.
- Cada card de modelo também desabilita seu próprio botão "Gerar" enquanto
  a chamada dele está em andamento.
- Timeout de 30s por chamada (`REQUEST_TIMEOUT_SECONDS`) → `504
  tts_lab_timeout`.
- `429` do provedor → `429 tts_lab_rate_limited`. `5xx` → `503
  tts_lab_unavailable`. Nenhum retry automático é feito.
- Erro em um modelo não interrompe os demais — cada card trata seu próprio
  estado (`ok` / `error` / `timeout` / `rate_limited`) de forma
  independente.

## Sem persistência

Nenhuma migration, nenhuma tabela nova. Avaliações manuais (naturalidade,
clareza, entonação, pausas, velocidade percebida) e resultados de geração
vivem só no `state` do React durante a sessão do navegador.

## Como testar manualmente

1. Configure `.env` do backend com `OPENROUTER_API_KEY` válida e
   `TTS_LAB_ALLOWED_EMAILS=prof.edesio@gmail.com` (ou o e-mail da conta que
   vai testar).
2. Suba o backend (`uvicorn app.main:app --reload`) e o frontend
   (`npm run dev`).
3. Faça login com a conta cujo e-mail está na allow-list.
4. Acesse `/admin/tts-lab`.
5. Clique em "Gerar em todos" — os quatro modelos foram confirmados
   funcionando contra a OpenRouter real durante a implementação (ver
   "Teste real OpenRouter" abaixo). Se algum vier a falhar (a OpenRouter
   pode descontinuar/alterar um modelo a qualquer momento), o card mostra
   o erro sem travar os demais.
6. Compare latência/tamanho na tabela final e registre as avaliações
   manuais (1–5) por modelo.

## Teste real OpenRouter

Executado durante a implementação, com a `OPENROUTER_API_KEY` real já
presente no ambiente (chave nunca impressa/logada — só usada no header
`Authorization` das chamadas):

| modelo | resultado inicial (sem voice) | resultado final |
|---|---|---|
| `hexgrad/kokoro-82m` | — | OK, 4322 ms, 17112 bytes (sanity check do caminho já usado em produção) |
| `fish-audio/s2.1-pro-free:free` | OK, 1512 ms, 35943 bytes | sem mudança necessária |
| `deepgram/flux-tts:free` | 400 `"An explicit voice is required..."` | OK após enviar `voice=flux-bree-en` |
| `google/gemini-3.1-flash-tts-preview` | 400 `"An explicit voice is required..."` | OK após enviar `voice=Kore` e descobrir (por outro 400) que só aceita `response_format=pcm` |

```text
REAL OPENROUTER TEST: PASS
```

Isso é o que motivou a correção da config inicial (que tinha assumido,
conservadoramente, `supports_voice=False` para os quatro exceto Kokoro) —
o teste real mostrou que dois modelos na verdade **exigem** voice, o
oposto do que a suposição conservadora presumia. Sem esse teste, o TTS Lab
teria ficado quebrado para Deepgram e Gemini.

## Limitações conhecidas

- Profundidade de bits do PCM da Gemini (assumida em 16 bits) não tem
  confirmação por header — ver "PCM da Gemini vira WAV" acima.
- `fish-audio/s2.1-pro-free:free` aceitou `speed` sem erro, mas não há
  confirmação de que o parâmetro realmente altera a velocidade percebida
  (só que o provedor não rejeitou a chamada).
- `speed` da Gemini não foi testado (modelo pago, preview) — fica marcado
  como não suportado por precaução, não porque foi confirmado que falha.
- `voice` do Fish Audio não foi testada (lista de vozes desconhecida) —
  fica marcado como não suportado até alguém descobrir e testar um valor
  válido.
- `estimated_cost` nunca é calculado (a API não expõe essa informação de
  forma confiável).
- Duração do áudio (`audio_duration_seconds`) não é calculada — exigiria
  decodificar o MP3, dependência considerada desnecessária para uma
  ferramenta de comparação manual (a duração do WAV gerado para a Gemini
  poderia ser lida do próprio cabeçalho, mas não foi exposta na API por
  consistência com os outros três modelos).
- Acesso restrito por allow-list de e-mail, não por um sistema de papéis
  real (ver seção "Acesso").
