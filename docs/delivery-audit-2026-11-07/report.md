# Auditoria de idioma, repetição e entrega

Data local: 2026-11-07. Sem push, sem merge e sem deploy. O Coolify não foi aberto. Nenhum texto de aluno foi copiado para este relato.

## Onde está o código

- HEAD local no início desta rodada: `255458d`, três commits à frente de `origin/main`.
- `origin/main`: `d6cd9d4b75fda0072bae2ed63088713959fd4784`.
- A auditoria anterior inspecionou esse mesmo `d6cd9d4`. Os achados foram relidos no código atual, que já inclui a Etapa 2 de contrato (`f643aab`, `701258f`, `255458d`) e alterações locais ainda não commitadas no começo da rodada.
- SHA publicado no Coolify: não verificado. `d6cd9d4` e o `57f4da7` citado em notas anteriores são declarações ou o remoto Git, não uma leitura do painel.
- Provedor em produção: desconhecido. No código, o padrão é `ai_mock_mode = true`, `stt_provider = mock` e `tts_provider = mock`. O ambiente da VPS pode sobrescrever isso. A chave e o modelo não foram lidos.

## Etapa 1 — caminhos

| Superfície | Rota | O que entrega |
|---|---|---|
| Prática livre | `POST /api/v1/lessons/generate` a partir de `/learn/[mode]` | Unidade curada aprovada, ou lição do provedor, ou estado de esgotamento |
| Cronograma | `POST /api/v1/curriculum/block/{id}/start` e `/teaching/answer` | Fluxo do bloco, com `selection_trace` |
| Conversação por texto | `POST /api/v1/conversations` e `POST /.../messages` | Abertura e falas do tutor |
| Voz | Os mesmos endpoints; o áudio usa a fala, não a tradução | |
| Retry de bloco | `POST /api/v1/curriculum/block/{id}/teaching/retry` | Variante ou o mesmo item, com motivo no trace |
| Retry legado | `lesson_attempts` | Pool da mesma lição |
| Revisão | `GET /api/v1/reviews/due` e `POST /reviews/{id}/answer` | Fila SRS, repetição intencional |
| Placement | `/api/v1/placement-tests/...` | Exposição própria, não alterada nesta rodada |
| Apoio livre | `POST /api/v1/tutor-chat` | Sem gravação de histórico |

`selection_trace` registra motivo, exclusões e esgotamento. Não guarda a resposta do aluno. Limitações que continuam: várias atividades antigas têm `source` desconhecido; o trace não prova o SHA do Coolify; o esgotamento do pool de retry (`no_candidates`) é outro evento, distinto de `curated_pool_exhausted`.

Produção não foi lida. Consultas só de leitura, sem colunas de texto do aluno:

```sql
SELECT l.code, u.cefr_level, u.skill, u.mode, u.validation_status, count(*)
FROM content_units u
JOIN languages l ON l.id = u.language_id
GROUP BY 1, 2, 3, 4, 5;
```

O `selection_trace` de `POST /lessons/generate` vai na resposta e no log `activity_selection`. A lição gravada não recebe esse trace. Não há consulta SQL que recupere o motivo de exclusão sem ler o log. A consulta acima não seleciona texto de aluno nem o corpo da unidade.

Esta etapa fica parcial: o mapa do código está fechado; o diagnóstico de produção está bloqueado por falta de acesso.

## Etapa 2 — idioma

Revalidado no código, não só na nota antiga.

| Achado antigo | No código atual |
|---|---|
| `conversation_turn` aceitava qualquer `reply` não vazio | O provedor ainda exige só `reply` não vazio. A API valida o idioma antes de gravar e tenta no máximo mais uma vez |
| O prompt pedia tradução entre parênteses | O texto do prompt agora manda a tradução para `reply_translation` |
| Abertura do cliente era gravada sem validação | Abertura incompatível não vira mensagem |
| O detector olhava poucos campos e não tinha português | O classificador de papéis inclui português. O detector do texto-alvo continua nos oito idiomas ensinados, para não rebaixar frase francesa que já passava. Sugestões e campos aninhados entram na visita |
| A validação editorial só pegava inglês conhecido | O contrato de papéis olha o corpo. O envelope não serve de prova |
| Apoio nativo não era validado | Apoio em língua distante fica `blocked` |

Exceções preservadas: citação em `original`, termo curto, frase em japonês ou mandarim medida por caracteres, e espanhol/italiano como confusão conhecida com português. Feedback incompatível fica em revisão, com o texto conservado.

## Etapa 3 — repetição

| Achado antigo | No código atual |
|---|---|
| `generate` não excluía unidades já usadas | Exclui, por perfil de idioma |
| O seletor pega a unidade mais recente | Continua entre as que ainda não foram praticadas |
| Retry legado olha a mesma lição | Continua. Não foi alargado para outra lição |
| O mock repete a faixa | Continua, quando não há unidade curada |
| A conversa mock usava a janela de dez mensagens | O índice é a contagem real de falas do tutor |

Esgotamento da biblioteca curada devolve `exhausted: true` e não grava outra lição. Não fabrica variante. Recarregar a página ainda chama `generate` de novo: se houver outra unidade, nasce outra prática; se não houver, a resposta é o esgotamento, sem sessão nova. Pedidos concorrentes de `generate` não têm trava. Isso deixa a etapa parcial.

Fingerprint, família, cooldown e revisão SRS não foram afrouxados. O placement não foi reescrito.

## Etapa 4 — tela

O chat usa um portão para não abrir duas conversas na mesma tentativa e descarta a resposta se o id da conversa mudou. Trocar modo, idioma ou abertura zera as mensagens. Tradução só aparece com língua nativa declarada. `supportText` não usa o português legado quando a nativa está ausente ou é outra língua. O áudio do objetivo usa só `objective_target`. Esgotamento mostra um aviso e não monta a atividade.

Pendência: não houve passagem no navegador nesta rodada. A proteção de `useLesson` contra resposta atrasada já existia e foi mantida.

## Etapa 5 — conteúdo

Nenhum lote foi gerado. Nenhuma chamada paga. Nenhum item foi promovido a aprovado. O pipeline existente é `generate_incremental_batches`, com lote máximo declarado de 50 e sem loop até 200. Itens rejeitados continuam indisponíveis.

Contagem do catálogo estático do código, não do banco aprovado: inglês tem 98 itens de vocabulário; as outras línguas faladas têm 24; latim tem 30. Leitura e escuta têm 4 textos por língua. Placement: 33 itens em en, es-ES, fr, ja e zh-CN; 28 em it e de; 34 em la. Não há, neste workspace, um SQLite com `content_units` para separar bruto, aprovado e elegível. Essa separação em produção fica bloqueada.

## Etapa 6 — publicação

Não há migração. Rollback não precisa desfazer schema.

Quando houver aprovação explícita:

1. Publicar o backend no Coolify e esperar o health.
2. Publicar o frontend em seguida. `NEXT_PUBLIC_API_URL` é lida no build.
3. Smoke: login, uma prática livre, uma conversa, uma revisão. Sem isso, o problema não está resolvido em produção.
4. Se o smoke falhar, republicar a imagem anterior. O último commit remoto conhecido é `d6cd9d4`. Confirme no Coolify qual SHA está no ar antes de usar esse valor como rollback.

## Testes desta rodada

Backend, suíte completa, antes de separar os dois detectores: **1 failed, 1903 passed, 5 skipped, 41 warnings in 1625.35s**, exit 1. A falha foi `test_select_activity_names_every_exclusion_and_keeps_the_choice`. A frase francesa `Quel est le train de ce soir ?` caía para 0,492 porque o português disputava o mesmo detector do texto-alvo e passava a ser `review_required`. Sem o português, a mesma frase fica em 0,532 e continua elegível. O classificador de papéis é que guarda o português.

Depois dessa separação, os arquivos de seleção, contrato, papéis, repositório e adaptação: **179 passed in 125.23s**, exit 0. Isso inclui o teste que tinha falhado, o esgotamento que não grava lição e o apoio em português reconhecido como `pt`. A suíte completa não foi repetida depois dessa separação.

Frontend, depois do ajuste final do chat: `npm test` **405 passed**, 53 arquivos, exit 0, 22,50 s. `npm run lint` exit 0, 0 erros, 5 warnings anteriores. `npm run typecheck` exit 0.

Não houve navegador, Coolify nem Postgres de produção. O problema não está declarado como resolvido em produção.
