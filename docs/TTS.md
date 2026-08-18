# TTS de Produção — BeFluent

Documentação da síntese de voz (text-to-speech) usada de verdade pelas
aulas, pelo Speech Coach e por qualquer outro lugar que reproduza fala do
BeFluent. Para o laboratório de comparação de modelos/vozes (ferramenta
administrativa, não usada pelo aluno), ver [TTS_LAB.md](TTS_LAB.md) — os
dois documentos são deliberadamente separados: este aqui é produção, o
outro é experimentação. As vozes documentadas aqui foram escolhidas
**depois de** testes manuais no Kokoro Voice Lab (seção do TTS Lab), mas o
TTS Lab em si não decide nem altera a configuração de produção — ela é
sempre uma edição manual deste lado.

## Provider principal e modelo

```text
Provider: OpenRouter (mesma OPENROUTER_API_KEY já usada por IA/STT)
Modelo:   hexgrad/kokoro-82m
Formato:  mp3 (Content-Type: audio/mpeg)
```

## Arquitetura

```text
Texto a falar + idioma explícito da lição/turno
                 │
                 ▼
   Frontend: AudioPlayer.play() (components/study.tsx)
                 │  POST /api/v1/speech/synthesize
                 │  { text, language_code, speed }
                 ▼
   Backend: app/api/speech.py → synthesize_audio()
                 │
        ┌────────┴─────────┐
        │                  │
  idioma no allowlist   idioma fora do allowlist
        │                  │
        ▼                  ▼
  Kokoro via OpenRouter   400 tts_unsupported_language
  (voz por idioma)          (nunca "adivinha" voz)
        │
   sucesso? ──── não (rede/timeout/4xx/5xx/API key ausente)
        │                  │
       sim                 ▼
        │            APIError (tts_unavailable / tts_unsupported_language)
        ▼                  │
  audio/mpeg (bytes) ◄──────┘ (erro sobe pro frontend, sem stack trace)
        │
        ▼
  Frontend: toca no <audio>
        │
   falhou (fetch/erro HTTP/<audio> onError)?
        │
       sim
        ▼
  window.speechSynthesis (Web Speech API do navegador)
```

O frontend **nunca** chama a OpenRouter diretamente — só conhece
`text`/`language_code`/`speed`. Modelo, voz e `OPENROUTER_API_KEY` só
existem no backend (`app/services/speech.py`).

## Endpoint

```text
POST /api/v1/speech/synthesize
```

Já existia antes desta tarefa (usado por `AudioPlayer` desde a introdução
do Kokoro em produção) — nenhum endpoint novo foi criado, só evoluído:

Request:

```json
{ "text": "Could you say that again?", "language_code": "en", "speed": 1.0 }
```

- `text`: 1–2000 caracteres (mesmo limite do TTS Lab; ver "Tamanho do
  texto" abaixo).
- `language_code`: código do projeto (`en`, `es-ES`, `fr`, `ja`, `zh-CN`,
  etc.) — 1 a 20 caracteres. A voz é decidida **inteiramente pelo
  backend**; o frontend nunca envia `voice` nem `model`.
- `speed`: opcional, 0.5–2.0. Repassado de verdade ao Kokoro (não é
  `playbackRate` do navegador).

Resposta: bytes de áudio, `Content-Type: audio/mpeg` (200) ou um erro
JSON estruturado (ver "Erros" abaixo) — nunca base64 desnecessário.

## Voice mapping final

Escolhido manualmente por escuta comparativa no Kokoro Voice Lab — **não**
é um ranking automático e não deve ser sobrescrito por um. Única fonte de
verdade: `_KOKORO_VOICE_BY_LANGUAGE` em `backend/app/services/speech.py`.

```text
en     → af_sky      (Sky)
es-ES  → em_alex      (Alex)
fr     → ff_siwis     (Siwis)
ja     → jf_nezumi    (Nezumi)
zh-CN  → zf_xiaoxiao  (Xiaoxiao)
```

`language_code` é reduzido ao prefixo ISO-639-1 antes do lookup
(`_language_hint`: `"es-ES".split("-")[0].lower()` → `"es"`) — é um
`dict.get` exato sobre esse prefixo, não `startsWith`/substring matching,
então não há risco de casar o idioma errado.

### Idioma fora do allowlist

Só os 5 idiomas acima têm voz Kokoro configurada. Um `language_code` fora
disso (`de`, `it`, etc.) **não** cai silenciosamente em `af_sky` nem em
nenhuma voz "parecida" — mandar texto de um idioma desconhecido para a
voz errada produziria fala incorreta, não uma rede de segurança. O backend
devolve `400 tts_unsupported_language` sem sequer chamar a OpenRouter, e o
`AudioPlayer` cai no Web Speech do navegador (que lê qualquer idioma
BCP-47 corretamente). Não há detecção de idioma a partir do texto em
nenhum ponto deste fluxo.

### Como trocar uma voz no futuro

1. Compare vozes no Kokoro Voice Lab (`/admin/tts-lab`) — escolha por
   clareza/inteligibilidade para o aluno, não só por naturalidade (ver
   docs/TTS_LAB.md).
2. Edite o valor correspondente em `_KOKORO_VOICE_BY_LANGUAGE`
   (`backend/app/services/speech.py`).
3. Rode `pytest backend/tests/test_ai_speech_providers.py` — os testes de
   mapeamento (`test_tts_openrouter_picks_voice_by_language`) travam o
   voice ID esperado por idioma; atualize-os junto.
4. Nenhuma migration, nenhum dado a migrar — é só uma constante em código.

`TTS_VOICE` (env var) força uma voz única para **todos** os idiomas,
ignorando o mapeamento — é uma escolha explícita do operador (ex. teste
manual em produção), não um mecanismo de seleção por idioma.

## Configuração / env vars

Já existiam antes desta tarefa (`backend/app/core/config.py`); nenhuma
duplicada. Não há `.env.example` neste projeto — variáveis são
documentadas em Markdown (mesmo padrão de `docs/TTS_LAB.md`) e definidas
no `.env` real de cada ambiente (não versionado; ver
[deployment-coolify.md](deployment-coolify.md)).

```env
OPENROUTER_API_KEY=...        # já usada por IA/STT — não duplicar
TTS_PROVIDER=openrouter       # openrouter | mock | web_speech (rollback)
TTS_MODEL=hexgrad/kokoro-82m  # já é o default no código
TTS_VOICE=                    # vazio = usa o mapeamento por idioma
TTS_SPEED=1.0                 # velocidade default quando o cliente não envia `speed`
```

- `TTS_PROVIDER=mock`: síntese fake (`RIFF` vazio), permitida só fora de
  `production`; em produção falha explicitamente (nunca fabrica áudio).
- `TTS_PROVIDER=openrouter`: Kokoro-82M via OpenRouter — modo de produção.
- `TTS_PROVIDER=web_speech`: **rollback** — ver seção abaixo.

**Este documento não altera nem lê o `.env` real de nenhum ambiente.**
Mudar essas variáveis em produção é uma ação humana deliberada (Coolify),
fora do escopo desta implementação.

## Fallback (Web Speech)

`AudioPlayer` (`frontend/components/study.tsx`) tenta o backend primeiro;
cai no `window.speechSynthesis` do navegador nas seguintes condições, sem
mostrar o erro técnico ao aluno (só loga internamente, no backend):

- erro de rede ao chamar `/speech/synthesize`;
- qualquer status HTTP de erro (`400`, `401`/`403`, `429`, `5xx`) —
  `apiBlob` lança `ApiError` para todo `!response.ok`, capturado por um
  `catch` genérico;
- `400 tts_unsupported_language` (idioma sem voz Kokoro configurada);
- `503 tts_unavailable` (API key ausente/inválida, provider indisponível,
  timeout, ou rollback via `TTS_PROVIDER=web_speech`);
- o elemento `<audio>` disparar `onError` (blob corrompido/formato
  inválido) — mesmo depois de já ter recebido bytes do backend;
- `audio.play()` rejeitar (autoplay bloqueado, etc.).

Se o navegador também não tiver `SpeechSynthesis`, aí sim aparece um aviso
visível ("Este navegador não oferece leitura em voz alta. Leia o texto na
tela.") — é o único caso em que o aluno vê algo, e mesmo assim sem detalhe
técnico.

Não há retry automático contra a OpenRouter antes do fallback — uma
tentativa, timeout de 30s (`REQUEST_TIMEOUT_SECONDS`-equivalente do
`httpx.post`), e cai pro navegador. Falar rápido demais esperando retries
numa conversa não é aceitável.

## Cancelamento / playback

- Cada `play()` cria um `AbortController` novo e cancela qualquer geração
  anterior ainda em voo (`abortRef.current?.abort()`) antes de começar —
  evita que uma resposta tardia comece a tocar depois que o aluno já pediu
  outro áudio.
- `stop()` também aborta a requisição em voo, pausa o `<audio>` e cancela
  qualquer fala pendente do `window.speechSynthesis`.
- Cancelamento intencional (`AbortError`) nunca aciona o fallback — só
  falhas reais do provedor acionam.
- `URL.createObjectURL`/`URL.revokeObjectURL`: a URL anterior é liberada
  antes de criar a próxima, e no unmount do componente — sem memory leak.
- Autoplay: `audio.play()` só é chamado dentro do handler de clique do
  próprio botão (gesto do usuário) — nenhum hack de autoplay foi
  adicionado.

## Estado de UI

Enquanto o backend gera o áudio, só a legenda do próprio player muda para
"Gerando áudio…" — a página não é bloqueada, e o aluno pode clicar em
"Pausar áudio" a qualquer momento (inclusive durante a geração) para
cancelar.

## Segmentação / pausas

Nenhuma segmentação nova foi introduzida — o texto enviado é o mesmo texto
pedagógico já usado pelo produto (frase/parágrafo da lição), sem chunking
por palavra nem blocos gigantes artificiais. Nenhuma tag SSML é enviada
(suporte não confirmado pelo Kokoro/OpenRouter).

## Erros

| Código | Status | Quando |
|---|---|---|
| `tts_unavailable` | 503 | API key ausente, provider indisponível, timeout, erro 5xx do provedor, ou `TTS_PROVIDER=web_speech` (rollback) |
| `tts_unsupported_language` | 400 | `language_code` fora do allowlist Kokoro (nunca chega a chamar a OpenRouter) |
| `422` (validação Pydantic) | 422 | `text` vazio ou acima de 2000 caracteres; `speed` fora de 0.5–2.0 |

Nenhum erro devolve stack trace, corpo bruto do provedor, nem a
`OPENROUTER_API_KEY` — mensagens genéricas, chave nunca logada.

## Tamanho do texto

Limite de 2000 caracteres (`Field(max_length=2000)` em `TTSIn`), o mesmo
já usado pelo TTS Lab — reaproveitado, não reinventado. É generoso o
bastante para qualquer frase/parágrafo pedagógico real do produto; textos
maiores devem ser quebrados pela camada que gera o conteúdo (Teaching
Engine), não truncados silenciosamente aqui.

## Segurança

- `OPENROUTER_API_KEY` só é lida no backend.
- `voice` e `model` nunca vêm do frontend — decididos inteiramente pelo
  backend a partir de `language_code`.
- `language_code`/`text` validados (tamanho) antes de qualquer chamada
  externa.
- Logs (`app/services/speech.py`) nunca incluem `Authorization` nem a
  chave — só `provider=... model=... language=... status=...
  latency_ms=...` (ver "Logs" abaixo).

## Logs

`OpenRouterTTSProvider`/`synthesize_audio` logam via `logger.warning`/
`logger.info` em falha (provider, tipo de erro, idioma sem voz
configurada); sucesso não é logado individualmente hoje (mesmo padrão que
o resto do módulo de fala). Nenhum log inclui texto completo do aluno,
áudio, ou a chave da API.

## Custo

Não há preço hardcoded no código. A resposta da OpenRouter para
`/audio/speech` não traz custo estruturado — se isso mudar no futuro, deve
ser lido do response/headers, nunca inventado.

## Rollback

Para desativar o Kokoro de servidor sem tocar em código:

```env
TTS_PROVIDER=web_speech
```

Todo pedido de síntese passa a devolver `503 tts_unavailable`
imediatamente (sem tentar a OpenRouter), e o `AudioPlayer` cai no
`window.speechSynthesis` do navegador para 100% dos alunos. Reverter é só
voltar `TTS_PROVIDER=openrouter`. Nenhuma mudança de código é necessária
em nenhum dos dois sentidos — **esta implementação não altera o `.env` de
nenhum ambiente**; a troca é sempre manual, feita por quem administra a
implantação.

## Troubleshooting

| Sintoma | Causa provável | Onde olhar |
|---|---|---|
| Todo mundo ouve voz do navegador, nunca a do BeFluent | `OPENROUTER_API_KEY` ausente/inválida, ou `TTS_PROVIDER` != `openrouter` | logs do backend (`tts_unavailable`), `.env` do ambiente |
| Um idioma específico sempre cai no navegador | `language_code` enviado não bate com nenhuma chave de `_KOKORO_VOICE_BY_LANGUAGE` (checar alias) | log `tts_unsupported_language`, valor exato de `language_code` |
| Áudio soa em inglês para outro idioma | `TTS_VOICE` setado globalmente (força uma voz única) | `.env`, variável `TTS_VOICE` |
| Latência alta / timeouts frequentes | Provedor (OpenRouter/Kokoro) lento — não é bug do BeFluent | comparar com o TTS Lab, que mede latência isoladamente |
| Quero comparar vozes antes de trocar uma | Use o Kokoro Voice Lab, não produção | [TTS_LAB.md](TTS_LAB.md) |

## Limitações conhecidas

- Sem cache de áudio repetido (mesmo texto+idioma gera de novo a cada
  play) — não implementado nesta tarefa; TTS Lab também não tem.
- Sucesso de síntese não é logado individualmente (só falhas) — telemetria
  agregada (contagem de sucesso/erro/fallback) não existe ainda; não foi
  adicionada plataforma de analytics externa para esta tarefa (fora de
  escopo).
- `speed` agora é repassado de verdade ao Kokoro (antes desta tarefa, o
  seletor de velocidade da UI existia mas era ignorado pelo backend — ver
  `test_speech_synthesize_sends_ui_speed_to_provider`).
