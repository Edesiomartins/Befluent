# Etapa 2 — Contrato de idioma

Data: 2026-11-06. Branch `main` local. Sem push e sem deploy.

A Etapa 1 fechou em `d6cd9d4`, publicado segundo o Dr. Edesio. Esta etapa não abriu o Coolify, não tocou o Postgres de produção e não criou migração.

Base: `docs/stage-1-reference/report.md`, incidente 3. Nas lições `c678eb78-001a-4df3-9cb0-833b4a58f4d8` e `1d7c3737-d810-4034-b0c0-16888854f64e`, o `objective` gravado era `Praticar opinion, raison et concession em uma situação realista.` O foco em francês vinha da biblioteca curada, dentro de uma frase em português.

## O que mudou

Commits de código: `f643aab` e `701258f`.

Antes de gravar ou devolver um turno, `apply_language_roles` olha cada campo com um papel:

- alvo (`target_language`): enunciado, abertura, resposta do tutor, termo, frase, áudio;
- apoio (`native_language`): objetivo, instrução, tradução, nota;
- feedback: explicação, justificativa, `why_correct`.

O detector continua o de `language_detection.py`. O achado vai para `language_role_findings` e, na resposta, para `selection_trace.language_roles`, com campo, papel, ação, motivo, idioma detectado e confiança. O texto da frase não entra no trace.

Ações:

| Ação | Quando | O que acontece com o texto |
|---|---|---|
| `repaired` | Um campo de apoio contém um trecho no idioma-alvo | O trecho vai para `{campo}_target`. O restante fica no campo. O original fica em `language_role_originals` |
| `review_required` | O campo inteiro de apoio ou de feedback está, com confiança alta, numa língua que não é a nativa, e não havia moldura para separar | O texto permanece. `language_role_status` fica `review_required` |
| `blocked` | Um campo de alvo está, com confiança alta, em outra língua | O texto permanece. `language_role_status` fica `blocked` |

O corte do trecho exige pelo menos quatro palavras, confiança mínima 0,50 no idioma-alvo, e nenhuma palavra funcional do português (`em`, `para`, `o`, `uma`…). O restante precisa continuar com pelo menos duas palavras. Assim, `Use o imparfait para descrever hábitos ou situações no passado.` não é partido: `o` e `para` seguram o termo solto.

Onde a validação roda, sem mudar quem é escolhido no retry:

- `apply_lesson_envelope`, antes de salvar a lição gerada, inclusive a unidade curada;
- a resposta da sessão (`_session_payload`), na atividade atual e no feedback, numa cópia — a sessão guardada não é reescrita;
- o turno de conversa, antes de gravar a mensagem do tutor;
- a variante já escolhida do retry legado.

A semente nova da conversa usa `focus_native`. Para francês B1 o objetivo passa a ser `Praticar opinião, motivo e ressalva em uma situação realista.`, com `objective_target` = `opinion, raison et concession` e `situation_native` separado. A chave `objective` continua existindo.

Na tela, o objetivo, a situação, o termo, a frase, a fala do tutor e o feedback ficam em regiões com `lang` (`fr`, `pt-BR`, …). O botão Ouvir do objetivo chama `speechText` só com `objective_target`. Instrução só em português não gera áudio.

## Decisões

- Reparar não traduz. Se não existe um trecho confiável, o texto fica e o achado pede revisão.
- `blocked` não apaga o item e não altera a ordem de seleção nem a regra de retry. Quem já marca `language_invalid` no pool continua fazendo isso. A etapa 3 é que mexe em repetição.
- Português não está no detector (os oito idiomas ensinados). Espanhol e italiano em confiança alta, com nativo `pt-BR`, não condenam um apoio: o detector confunde essas línguas com português. Se o idioma detectado é o próprio alvo, ou uma língua distante (`en`, `de`, `ja`, `zh-CN`, `la`) com confiança de pelo menos 0,80, o apoio ou o feedback vai para `review_required`.
- Texto com menos de quatro palavras fica fora desta camada, como já acontecia no detector.
- Lições já gravadas com o objective misturado não são reescritas no banco. A correção vale na próxima geração, quando o envelope passa pelo contrato. Não houve migração.
- O JSON sujo `backend/scripts/out/fr_b1_review_batches.json` apareceu de novo ao rodar a suíte. Não entrou no commit.

## Testes

Backend, `py -3 -m pytest --tb=line`, exit 0: **1889 passed, 5 skipped, 41 warnings in 1727.88s**. Os cinco saltos são os de sempre: dois sem `POSTGRES_TEST_URL` e três em `test_retry_antirrepeticao.py`.

O arquivo novo `backend/tests/test_language_roles.py` cobre alvo, apoio, feedback, exercício, vocabulário, conversa, retry legado e a regressão do objective misturado. A semente e o envelope entram no mesmo arquivo.

Frontend, na sequência, exit 0:

- `npm test`: **403 passed**, 52 arquivos, 29,13 s;
- `npm run lint`: 0 erros, 5 warnings anteriores (`objective-choice.tsx`, `lesson-adaptation.test.tsx`, `speech-ui.test.tsx`);
- `npm run typecheck`: exit 0.

`frontend/tests/language-contract.test.tsx` confere `lang="fr"` no trecho, `lang="pt-BR"` na instrução, e que o áudio recebe `opinion, raison et concession` e não a frase com «Praticar».

## Pendências

- Lições já persistidas com o objective misturado só se separam numa geração nova.
- O detector não confirma português; a proteção do apoio contra espanhol/italiano falso fica de fora de propósito.
- `blocked` avisa no trace e conserva o texto. Não tira o item de um pool que já o tenha escolhido.
- Retry, cooldown e ranking não foram alterados.
- TTS/STT de produção continuam em mock. Áudio real segue pendente.
- Sem push. O que está em `origin` não inclui esta etapa.
