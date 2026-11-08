# Etapa 3 — o que a auditoria de 7 de novembro deixou aberto

Data local: 2026-11-08. Branch `cursor/stage-3-audit-followups-c6e0`, base `e1a28a3`. Sem merge. O Coolify não foi aberto. Nenhum banco de produção foi lido ou alterado. Nenhuma chamada paga de modelo. Nenhum texto de aluno entrou neste relato.

A auditoria de 7 de novembro permanece em `docs/delivery-audit-2026-11-07/report.md`. Ela descreve o código daquele dia. Este arquivo descreve o que foi medido agora.

## Três lugares, três estados

| Lugar | O que é | Estado nesta rodada |
|---|---|---|
| Código deste branch | Commits abaixo, a partir de `e1a28a3` | Os cinco itens de código foram implementados e testados aqui |
| Git remoto | `origin/main` continua `e1a28a3e3cdea809d0592a295d3d2b8482320875` até alguém integrar o pull request | O branch foi enviado só como pull request. `main` não recebeu push |
| Produção | `befluent.medquesthub.com.br` e `api-befluent.medquesthub.com.br` | Painel não consultado. SHA publicado desconhecido. Nada disto está resolvido em produção |

## Commits

| SHA | O que fecha |
|---|---|
| `5149a17` | O chat no React StrictMode deixa de abrir duas conversas. O portão muda na renderização quando idioma, situação, abertura ou sessão mudam |
| `cedaa76` | Abertura com `opening_rejected` não aparece no chat. A fala só entra depois da resposta de criação |
| `cc6c742` | Recarregar ou repetir `POST /lessons/generate` no mesmo modo devolve a prática `active`. Pedidos concorrentes passam por um lock. Unidade entregue continua excluída da próxima seleção |
| `51f27bd` | O teste do lote FR B1 não regrava `backend/scripts/out/fr_b1_review_batches.json`. Os ids de objetivo no arquivo passam a ser estáveis (`fr-b1-vocabulary`, e os equivalentes) |
| `00dec2f` | `backend/scripts/diagnose_mixed_objectives.py` lista objetivos mistos e o inventário. Não grava lição e recusa PostgreSQL cujo nome não termina em `_test` |

## O que cada item fez

O efeito do chat criava um portão novo a cada execução. `claimConversation` só junta chamadas que compartilham o mesmo portão, então o StrictMode do Next (ligado por padrão no `next dev`) disparava dois `POST /conversations`. O portão agora vive no `ref` e só é trocado quando a chave da conversa muda. O teste de componente em `frontend/tests/chat-strict-mode.test.tsx` roda dentro de `<StrictMode>` e cobre também o envio enquanto a abertura ainda responde, e a troca de idioma.

A tela colocava a abertura do tutor no estado antes de o backend responder, e o tipo da criação só lia `id`. A resposta já traz `opening_rejected`. Com esse campo verdadeiro, a conversa continua existindo e o texto da abertura não é mostrado. `frontend/tests/chat-opening.test.tsx` cobre a recusa e a abertura aceita.

`practiced_content_unit_ids` significa unidade **entregue**, gravada em `LessonContentUsage` na criação da lição. Conclusão não entra nesse critério: a unidade permanece fora da próxima seleção se a lição for concluída ou abandonada. Afrouxar isso devolveria material já entregue. A decisão foi manter o critério. O que mudou é a prática ainda `active`: o segundo `generate` do mesmo modo e idioma devolve essa lição, com `selection_trace.reason = resumed_active_practice`, sem nova unidade e sem nova chamada de modelo. Dois pedidos ao mesmo tempo pegam um lock do processo antes da leitura e, no PostgreSQL, `SELECT … FOR UPDATE` na linha do perfil. Fingerprint, cooldown, SRS e validação editorial não foram alterados. Outro modo não reutiliza a mesma lição. Depois de `complete`, a próxima prática é outra e a unidade já entregue continua de fora.

O lote FR B1 de revisão continua com 10 gerados, 9 em revisão e 1 rejeitado por `review_required`. Nenhum item foi aprovado. O teste chama `build_report()` e confere que o arquivo não muda.

O diagnóstico foi executado aqui só sem URL. `writes` ficou 0, `production` ficou falso e `historical_lessons` ficou nulo: nenhuma lição histórica foi lida. O inventário estático, contado no código, repetiu a tabela de 7 de novembro:

| Língua | Vocabulário | Leitura | Escuta | Placement |
|---|---:|---:|---:|---:|
| en | 98 | 4 | 4 | 33 |
| es-ES, fr, ja, zh-CN | 24 | 4 | 4 | 33 |
| it, de | 24 | 4 | 4 | 28 |
| la | 30 | 4 | 4 | 34 |

Isso não é o inventário aprovado do Postgres de produção.

## Testes medidos nesta máquina

Backend, com `POSTGRES_TEST_URL` apontando para um PostgreSQL 18 local (`server_version_num` 180006) e o banco descartável `befluent_test` em `127.0.0.1`. Esse banco foi criado para a suíte. Os testes de reset criam e apagam só schemas com nome UUID dentro dele.

`/tmp/befluent-venv/bin/python -m pytest --tb=line`, exit 0: **1917 passed, 43 warnings in 767.68s (0:12:47)**. A linha final não tem `skipped` nem `failed`. Os cinco testes que antes saltavam sem essa URL passaram dentro dessa suíte. Isolados, antes da suíte completa: **5 passed, 2 warnings in 5.22s**, exit 0 (`test_placement_completion_postgres.py`, `test_placement_exposure_postgres.py`, `test_reset_test_user_learning_postgres.py`).

Frontend, em sequência, exit 0:

- `npm test`: **410 passed**, 55 arquivos, 21,25 s;
- `npm run lint`: 0 erros, 5 warnings anteriores (`objective-choice.tsx`, `lesson-adaptation.test.tsx`, `speech-ui.test.tsx`);
- `npm run typecheck`: exit 0.

Playwright, jornada já existente `e2e/fr-b1-session.spec.ts`, desktop 1280×800 e mobile 390×844, exit 0: **1 passed (18,1 s)**. Servidores locais, IA/STT/TTS em mock, sqlite descartável em `/tmp/e2e-fr-b1.sqlite3`. A configuração usada para o Linux ficou fora do commit. Os arquivos de `docs/stage-1-reference/evidence/` foram restaurados depois da rodada; o manifesto antigo da Etapa 1 não foi substituído.

Nessa jornada local, a abertura e o turno de texto usaram o mesmo id de conversa. A retomada mobile do vocabulário manteve o mesmo fluxo (`mobile_resume_same_flow` verdadeiro). Microfone físico e audição humana continuam pendentes. Esgotamento do plano de 12 não apareceu. Abrir de novo a tela de conversa no mobile criou outra conversa; a anterior continuou consultável. Isso já estava anotado no spec e não foi tratado como defeito desta rodada.

## O que continua aberto

- Publicar. Enquanto o pull request não for integrado e o Coolify não receber backend e depois frontend, o comportamento acima existe só neste branch.
- SHA, provedor e inventário aprovado de produção. Não foram lidos.
- Lições já gravadas com objetivo misto. O script está pronto e não foi apontado para dados reais. Não houve correção.
- `practiced` continua sendo entrega, não conclusão. Uma lição abandonada não devolve a unidade ao pool.
- TTS/STT reais e audição humana.
- Voltar à tela de conversa depois de sair dela abre outra conversa. O StrictMode na mesma montagem é que deixou de duplicar o `POST`.
