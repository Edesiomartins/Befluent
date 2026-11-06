# Etapa 1 — referência local FR B1 / pt-BR

Diagnóstico somente. Nenhuma regra de seleção, cooldown, retry ou elegibilidade foi alterada para “corrigir” o que apareceu. A execução abaixo é **local**, no SQLite `backend/tmp/e2e-fr-b1.sqlite3`, com IA, STT e TTS em modo mock. Não é homologação e não descreve o comportamento de produção.

## Referência publicada

Dr. Edesio informou que, após o push e o deploy por volta das 08:44 (America/Sao_Paulo) de 06/11/2026, **frontend e API passaram a ter `d7fba8d` como referência publicada**, no lugar de `57f4da7`. Isso fica registrado como declaração do usuário. Esta rodada não abriu, consultou nem alterou o Coolify, e não leu o PostgreSQL de produção. O SHA local não prova o que o deploy entregou.

No momento da jornada E2E, `git rev-parse HEAD` era `b93507c0dc7e3f9085bc7b6b5d0f81cb386a9d68`. Esse commit já estava à frente de `d7fba8d`. O spec do Playwright entrou em `2c86e5f`. `9a7f205` só aponta o logger do teste. `9725070` impede o Alembic de desligar os loggers da aplicação e reativa o logger nos dois testes de log. Nenhum desses commits muda a atividade escolhida. Nenhum deles foi enviado a produção nesta rodada.

## Como a jornada foi executada

Uma conta nova, língua nativa pt-BR, francês, nível informado B1. A mesma conta e o mesmo banco seguiram do desktop `1280×800` para o mobile `390×844`.

Comando: `npx playwright test e2e/fr-b1-session.spec.ts` em `frontend`, com API em `127.0.0.1:8011` e Next em `127.0.0.1:3011`. O `manifest.json` registra `result: concluiu` em `2026-11-06T12:12:03.585Z`. Artefatos em `docs/stage-1-reference/evidence/`. `session.log` existe na pasta; `*.log` está no `.gitignore`. A cópia rastreada é `evidence/session.txt`.

O `falha.png` na mesma pasta é de uma tentativa anterior desta rodada, interrompida antes da retomada mobile. Não é o resultado final.

## O que o trace da sessão de vocabulário mostrou

Lição `046d936d-e2fb-46b7-b3ef-482454a50b10`. Fluxo `1b3f8ea4-551e-4b2c-8d83-104060a435b6`. Abertura: 29 candidatos, 12 entregues, `fallback_used` falso, esgotamento agregado ausente. Motivo da seleção: `freshness_budget_modality_interaction`. Rota: `POST /api/v1/lessons/{id}/vocabulary-cycle/start` → `plan_session` em `backend/app/services/session_engine.py`.

Entregues com proveniência declarada `curated_fr_b1_slice`, `target_language=fr`, `native_language=pt-BR`, `cefr_level=B1`, `content_version` nulo (`content_version_status=unknown`), `provider` nulo, `content_source_id` nulo:

- `fr-b1-reading-opinion` (multiple_choice)
- `fr-b1-listen-train` (listening_recognition)
- `fr-b1-dictation-agree` (dictation)
- `fr-b1-gap-utile` (fill_gap)
- `fr-b1-guided-train` (guided_production)
- `fr-b1-repeat-agree` (repeat)
- `fr-b1-transfer-station` (transfer_question)

Cinco outras atividades entregues têm só um hash como id, `source=unknown`, `content_version_status=unknown` e, nesses registros, `target_language`, `native_language` e `cefr_level` nulos (quatro delas) ou só o par `fr`/`pt-BR` sem CEFR (`conversation_prompt`). A origem editorial e a versão não estão declaradas no payload. Não dá para afirmar, por este trace, que o enunciado está no idioma errado: o texto não entra no artefato.

Exclusões da abertura (17), por código:

- `family`: 1 hash
- `cooldown`: 1 hash
- `quality`: `fr-b1-order-disagree`
- `budget`: 14, entre eles `fr-b1-presentation-pourtant` e `fr-b1-match-courtesy`

O código `budget` é o que sobra depois que a dose curta fecha 12 atividades. Não é esgotamento do estoque: o plano não marcou `exhaustion`.

`fr-b1-order-disagree` está na fatia com `quality_status=approved`. Fora do navegador, a mesma função usada pelo plano (`language_safety` → `target_field_status` em `backend/app/services/language_detection.py`) devolveu `review_required` para esse item. `plan_session` grava isso como `quality`. O detector não nomeia, no trace, qual campo ficou incerto. Campo específico: **não determinado**.

## Incidentes desta execução

### 1. Duas conversas na abertura do chat por texto

Evidência: `evidence/session.log`, `evidence/traces.json` (`desktop-conversa-inicio` e `desktop-conversa-turno`), captura `desktop-conversa-texto.png`.

Passos: cadastro, onboarding FR B1 pt-BR, `/learn/conversation`, envio de uma frase curta.

- Abertura capturada: conversa `7c8d6daa-4c63-405a-8707-a96eab498d41`. `provider` nulo, `model` nulo, `source=unknown`, versão `unknown`.
- Turno que a tela usou: conversa `4292fb07-11cd-4288-bf6a-3cea9847ddb8`, mensagem no trace do turno, `provider=mock`, `model` nulo, `source=unknown`, `target_language=fr`, `native_language=pt-BR`, `cefr_level=B1`.

Caminho: `Chat` em `frontend/components/study.tsx` dispara `POST /api/v1/conversations` no efeito de montagem. O cleanup marca `cancelled`, mas não cancela o POST já enviado. No `next dev` o efeito roda de novo e nasce uma segunda conversa; a interface guarda a segunda. Rota: `conversations.start` e `conversations.message` em `backend/app/api/conversations.py`.

Origem do conteúdo da fala do tutor: **não determinado** além de `provider=mock` e `source=unknown`. Versão: **não determinado** (`unknown`). Não foi corrigido.

No mobile, `/learn/conversation` abriu uma terceira conversa, `b92ed7ae-2bde-4e48-8a91-31477ab77d27`. O `GET` da conversa do turno desktop (`4292fb07-…`) respondeu 200. São conversas diferentes da mesma conta, não uma retomada da mesma conversa.

### 2. Retry sem alternativa e a mesma atividade mantida

Evidência: `desktop-resposta-3` em `traces.json` e `desktop-vocabulario-erro.png`.

No terceiro envio do ciclo, o trace passou a `kind=interaction_retry`, `reason=same_activity_retry`, `chosen_activity=fr-b1-reading-opinion`, `fallback_used` falso, e `exhaustion.aggregate_reason=pool_exhausted` com `contributing_rules=["no_candidates"]`. O fluxo continuou `1b3f8ea4-551e-4b2c-8d83-104060a435b6`.

Caminho: `POST …/vocabulary-cycle/answer` → `teaching_slice._set_retry_activity` → `activity_pool.choose_interaction_retry`. Não havia candidato elegível; a mesma atividade curada foi mantida. Isso é esgotamento do pool de alternativa, não da sessão inteira. Não foi corrigido.

A retomada mobile leu o mesmo fluxo e o mesmo trace de retry (`mobile-retomada-api`).

### 3. Objetivo da conversa por texto mistura francês numa frase em português

Evidência no SQLite desta jornada, não deduzida pela aparência da tela.

Lições `c678eb78-001a-4df3-9cb0-833b4a58f4d8` (desktop) e `1d7c3737-d810-4034-b0c0-16888854f64e` (mobile). As duas têm `native_language=pt-BR`, `target_language=fr`, nível B1, modo `conversation`. O campo `objective` gravado é `Praticar opinion, raison et concession em uma situação realista.`

Origem comprovada: unidade `177afe56-ec93-46e2-9ed4-bc7aa6cbdb71`, fonte `19a77ffa-5641-4ebd-b30f-0f2a69c87e16` («BeFluent · biblioteca inicial», tipo `book`, revisão `APPROVED`). O mesmo texto já está no `payload_json` da unidade. Uso ligado por `lesson_content_usages`. `provider` e `content_origin`: `curated_library`. `model` nulo. Versão de conteúdo: **não determinado**.

Caminho: `POST /api/v1/lessons/generate` em `backend/app/api/lessons.py`, quando existe unidade aprovada para nativo `pt-BR`. Não foi corrigido.

A lição de voz da mesma conta, `c39493f3-af3b-4800-bbf7-9914d5b70c89`, veio de `provider=mock` e o objetivo é `Praticar opinião, motivo e ressalva em uma situação realista.`

## Comportamento esperado observado

- A dose curta entregou 12 de 29 e deixou 14 de fora por `budget`, sem marcar a sessão como esgotada.
- Itens da fatia `curated_fr_b1_slice` que passaram trazem `fr` / `pt-BR` / `B1` e versão desconhecida, sem inventar `content_version`.
- A abertura da conversa não grava provedor: o modelo ainda não foi chamado. O turno mock grava `provider=mock`.
- TTS: `POST /api/v1/speech/synthesize` status 200, `audio/wav`. STT: `POST /api/v1/speech/transcribe` status 200, `provider=mock`, `model` nulo. A transcrição não foi salva no artefato.

## Incidente histórico não reproduzido

`docs/fr-b1-incident-2bbf6b59c0b5b.md` e `docs/fr-b1-reuse-repair-2bbf6b59c0cb0b5b.md` descrevem uma lição FR B1 persistida com título/explicação em inglês, origem OpenRouter e modelo `nvidia/nemotron-3.5-lightning`. Esta rodada não consultou produção e rodou em mock. Esse conteúdo contaminado **não apareceu** nesta execução. As evidências antigas em `docs/learning-experience-v2/` não provam o estado atual.

## Áudio e produção

Microfone físico, fala humana e audição humana do TTS ficam **PENDENTES**. O que rodou foi dispositivo falso do Chromium e os stubs mock da API. A referência publicada `d7fba8d` não foi exercitada em homologação nesta rodada.

## Validação

A jornada Playwright ficou em `b93507c` (manifesto `2026-11-06T12:12:03.585Z`): **1 passed**. Não foi repetida depois de `9725070`, porque esse commit só mexe no logging do processo de teste e uma nova jornada substituiria os IDs já arquivados. O log da sessão está em `evidence/session.txt` (o `session.log` é o mesmo texto e o `.gitignore` cobre `*.log`).

A suíte `py -3 -m pytest -q --tb=line` iniciada às 12:32Z, já com `9a7f205`, terminou **exit 1** às 12:57Z (cerca de 1671 s). Falharam só `test_select_activity_names_every_exclusion_and_keeps_the_choice` (`assert 'good-a' in ''`) e `test_select_activity_records_each_exclusion_without_changing_the_choice` (`assert 'keep' in ''`). O trace da escolha estava certo. O `caplog` vinha vazio: `fileConfig` do Alembic, com o padrão `disable_existing_loggers=True`, desliga `app.services.activity_pool` depois que o `conftest` importa a aplicação.

`9725070` passa `disable_existing_loggers=False` e os dois testes reativam o logger antes de ler o log. A suíte refeita depois disso, o mesmo comando, das 12:59Z às 13:24Z, terminou **exit 0** em 1516 s. A barra tem **1878** pontos e **5** `s`, nenhum `F`. O modo quieto não deixou a linha final no log capturado; a contagem é a das marcas. Os únicos `pytest.skip` do backend são os dois testes de `test_reset_test_user_learning_postgres.py` (sem `POSTGRES_TEST_URL`) e três saltos condicionais em `test_retry_antirrepeticao.py`. Produção não foi configurada para eliminar esses skips. O log dessa suíte lista os warnings de `path_separator` do Alembic e o adaptador de datetime do sqlite3 em `test_ensure_schema_adds_missing_user_columns`.

Uma suíte paralela, `py -3 -m pytest --tb=line`, das 12:41Z às 13:06Z, imprimiu **1878 passed, 5 skipped, 41 warnings in 1523.99s**. Ela começou antes de `9725070` estar commitado. O número 41 é o dessa impressão, não uma segunda contagem inventada.

Frontend, depois de `9725070`, sem mudança de UI: `npm test` **400 passed**, 51 arquivos, exit 0, 25,00 s (início 10:25 local). `npm run lint` exit 0, 0 erros, 5 warnings anteriores. `npm run typecheck` exit 0. O jsdom avisou que `HTMLMediaElement.play/pause` e `canvas` não estão implementados; isso não derrubou teste.
