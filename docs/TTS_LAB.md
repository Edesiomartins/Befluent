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

## Kokoro Voice Lab

Seção dentro do TTS Lab (mesma página `/admin/tts-lab`, mesmo acesso por
allow-list — ver "Acesso" acima) para comparar as **vozes do
`hexgrad/kokoro-82m` dentro de um idioma**, com o mesmo texto, e escolher
empiricamente a melhor voz por idioma. Não substitui a comparação de
modelos acima — é uma ferramenta adicional, isolada, só para Kokoro.

**Não altera a voz de produção.** A voz padrão por idioma usada pelas aulas
continua em `_KOKORO_VOICE_BY_LANGUAGE` (`app/services/speech.py`), que o
Kokoro Voice Lab não lê nem escreve. Escolher uma "preferida da sessão" no
laboratório é só um resultado experimental em memória do navegador — mudar
a voz de produção continua sendo uma edição manual desse dicionário, feita
por decisão humana depois de comparar os áudios.

### Fonte de verdade dos voice IDs

`backend/app/services/kokoro_voices.py` — único lugar com a lista de
idiomas/vozes (backend e frontend leem daqui via
`GET /api/v1/tts-lab/kokoro/voices`; nenhuma lista duplicada no frontend).
Os voice IDs foram confirmados em `VOICES.md` do repositório oficial do
modelo (https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md,
consultado em 2026-08-18) — não foram inventados, mas também **não foram
testados um a um contra a OpenRouter real** nesta implementação (seriam
~50 chamadas pagas só para popular a config; o contrato de geração em si
já é o mesmo `model + voice + text` usado pelo TTS Lab genérico e por
`speech.py` em produção).

### Idiomas configurados

| Código | Nome | Vozes |
|---|---|---|
| `en-US` | English — US | 11 female (`af_*`) + 9 male (`am_*`) |
| `en-GB` | English — UK | 4 female (`bf_*`) + 4 male (`bm_*`) |
| `es-ES` | Spanish | `ef_dora` + `em_alex`, `em_santa` |
| `fr-FR` | French | `ff_siwis` |
| `ja-JP` | Japanese | 4 female (`jf_*`) + `jm_kumo` |
| `zh-CN` | Chinese | 4 female (`zf_*`) + 4 male (`zm_*`) |
| `it-IT` | Italian | `if_sara` + `im_nicola` |
| `pt-BR` | Portuguese — Brazil | `pf_dora` + `pm_alex`, `pm_santa` |
| `hi-IN` | Hindi | 2 female (`hf_*`) + 2 male (`hm_*`) |

Os seis primeiros cobrem os idiomas atuais do BeFluent (inglês
diferenciado em US/UK, como pedido). `it-IT`/`pt-BR`/`hi-IN` são extras que
o Kokoro já suporta e ficam disponíveis só para exploração — não fazem
parte do currículo do produto e não devem ser tratados como tal.

### Como adicionar uma nova voz

Adicione o voice ID em `KOKORO_LANGUAGES` (`kokoro_voices.py`), dentro do
idioma certo, usando o helper `_voices("female"|"male", "xx_nome", ...)`.
`name` é derivado automaticamente do próprio ID; nenhuma outra mudança de
código é necessária — o endpoint `/kokoro/voices` e a página já leem dessa
config. Confirme o ID contra a fonte oficial antes de adicionar (não
inventar IDs).

### Endpoints

- `GET /api/v1/tts-lab/kokoro/voices` — lista idiomas e vozes (mesma
  allow-list do TTS Lab).
- `POST /api/v1/tts-lab/kokoro/generate` — recebe `{language, voice, text,
  speed?}`. Valida, nessa ordem: idioma existe na config; voz existe **e
  pertence a esse idioma** (uma voz `bf_*` enviada com `language=en-US` é
  rejeitada com `400 tts_lab_kokoro_invalid_voice`, mesmo sendo uma voz
  Kokoro válida para `en-GB`); texto (1–2000 caracteres, igual ao TTS Lab
  genérico); `speed` opcional (0.5–2.0). Depois de validar, chama o mesmo
  `service.generate("hexgrad/kokoro-82m", text, speed, voice)` já usado
  pelo `/generate` genérico — mesmo client HTTP, mesmo tratamento de
  erro/timeout/429/5xx, sem duplicar código.

### Comparação e teste cego

- **Gerar** (voz selecionada) e **Comparar todas as vozes** (todas as vozes
  do idioma atual, com o mesmo texto e velocidade) — chamadas sequenciais
  (uma por vez, não em paralelo), com botão desabilitado e contador de
  progresso enquanto roda. Erro em uma voz (429/timeout/5xx/erro genérico)
  não interrompe as demais — cada card mantém seu próprio estado.
- **Modo teste cego**: esconde nome, voice ID e gênero de cada voz (mostra
  "Voz A"/"Voz B"/...) até clicar em "Revelar vozes". A ordem é
  re-embaralhada a cada rodada de "Comparar todas" e a cada vez que o modo
  é ligado — só a rotulagem muda; texto, velocidade e demais parâmetros são
  idênticos entre vozes na mesma rodada, para manter a comparação válida.
- **Trocar idioma** limpa áudios gerados, avaliações e revela/oculta do
  idioma anterior (`URL.revokeObjectURL` nos áudios antes de descartar) —
  não faz sentido comparar avaliações de vozes de outro idioma.

### Avaliação manual

Por voz: **Clareza** (1–5, destacada como critério pedagógico principal —
inteligibilidade para o aluno, não naturalidade), Naturalidade, Entonação,
Ritmo (1–5 cada) e Velocidade percebida (Lenta/Boa/Rápida). Botão "⭐ Minha
preferida" marca uma voz preferida por idioma (não persiste entre idiomas
diferentes, mas fica guardada por idioma durante a sessão).

### Presets por idioma

5 frases estáticas por idioma (`frontend/lib/kokoro-presets.ts`) cobrindo
frase curta, pergunta, conversação natural, feedback pedagógico e frase
mais longa — mapeadas em Short/Medium/Long para o filtro de tamanho (a
qualidade do TTS pode variar com o tamanho do texto, então vale testar os
três). Inglês usa exatamente os exemplos do briefing original; espanhol,
francês, japonês e chinês foram escritos à mão com o mesmo espírito (não
são traduções automáticas) — não têm a mesma revisão nativa que o inglês,
tratar como ponto de partida. `en-GB`/`it-IT`/`pt-BR`/`hi-IN` não têm
presets dedicados; o campo de texto fica editável livremente.

### Velocidade

O seletor "Velocidade (geração)" envia `speed` de verdade para a API
Kokoro (mesmo parâmetro do TTS Lab genérico) — não é `playbackRate` do
navegador. Nenhum controle de velocidade de reprodução local foi
adicionado nesta versão (ficaria fácil de confundir com velocidade de
geração); o `<audio controls>` nativo do navegador já oferece isso se
necessário.

### Exportação do resultado

Botão "Copiar resultado" copia (via `navigator.clipboard`) um resumo em
texto simples da voz preferida do idioma atual: notas de clareza,
naturalidade, entonação, ritmo e latência média das vozes já geradas. Não
grava arquivo nenhum.

### Persistência

Nenhuma migration, nenhuma tabela nova. Vozes/idiomas são config estática
em código (não banco). Avaliações, preferida por idioma, áudios gerados e
estado de teste cego vivem só no `state` do React durante a sessão do
navegador — perdidos ao recarregar a página, como o TTS Lab genérico.

### Como escolher a voz vencedora (fora desta ferramenta)

O laboratório só **mede**; não decide. Depois de comparar manualmente,
promover uma voz a padrão de produção é uma edição manual e deliberada de
`_KOKORO_VOICE_BY_LANGUAGE` em `app/services/speech.py` — fora do escopo
desta ferramenta, e não algo que o Kokoro Voice Lab faz sozinho.

### Limitações conhecidas (Kokoro Voice Lab)

- Voice IDs confirmados contra a lista oficial do modelo, não contra
  chamadas reais da OpenRouter (ver "Fonte de verdade dos voice IDs" acima)
  — se a OpenRouter não suportar algum ID específico, o card mostra o erro
  do provedor sem travar os demais, mas isso só aparece no uso real. Não
  executamos um teste real contra a OpenRouter para o Kokoro Voice Lab
  nesta implementação (sem `OPENROUTER_API_KEY` disponível no ambiente
  local em que foi implementado); ver "Teste real OpenRouter" acima para o
  precedente com os 4 modelos genéricos do TTS Lab, feito em uma sessão
  anterior que tinha a chave configurada.
- Presets de espanhol/francês/japonês/chinês são traduções manuais, sem
  revisão por falante nativo.
- Sem cache de áudio repetido nesta versão (gerar a mesma voz+texto duas
  vezes chama a API de novo) — não implementado para manter o escopo
  pequeno; nada impede adicionar depois se o custo de chamadas repetidas
  incomodar no uso real.
- `en-GB`/`it-IT`/`pt-BR`/`hi-IN` não têm presets dedicados.

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
