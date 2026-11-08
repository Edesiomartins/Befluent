# Contrato de idioma e de seleção

Este texto descreve o código local. Não descreve o que está publicado no Coolify. O painel não foi consultado.

## Papéis

- Língua-alvo: `reply`, `opening`, exemplos, sugestões e textos de prática.
- Língua nativa, quando existe: `reply_translation` e o apoio. Sem língua nativa declarada, o português legado não é inferido nem exibido.
- Feedback: explicação e justificativa. Texto incompatível fica marcado como `review_required` e não é apagado.
- O tutor de apoio pode responder na língua nativa ou na língua-alvo. Uma terceira língua, com confiança alta, é recusada.
- A citação em `corrections.original` é a fala do aluno e não entra na validação.
- Termo curto, inclusive em japonês, mandarim ou latim, não é bloqueado só por não ter várias palavras separadas por espaço. Frase em japonês ou mandarim entra na medição pelos caracteres.

## O que é recusado

- Fala principal ou sugestão com confiança alta em outra língua: ação `blocked`. O texto permanece no payload rejeitado, mas não é gravado como fala válida.
- Apoio numa língua distante do par (por exemplo inglês quando o par é francês e pt-BR): `blocked`. O texto não é apagado.
- Abertura enviada pelo cliente com idioma incompatível: a conversa abre e `opening_rejected` vem verdadeiro. A abertura não vira mensagem do assistente.
- Há no máximo duas tentativas do mesmo provedor. Não há troca de provedor.
- Histórico de outra língua nativa responde `409` e não é apagado nem reenviado ao modelo.

A fala principal não pede tradução entre parênteses. Se a tradução já está em `reply_translation` e também aparece entre parênteses no fim da fala, ela sai da fala.

Metadados `target_language` no envelope não provam o idioma do corpo. O detector olha o texto, inclusive listas de sugestões e campos aninhados.

Há dois detectores. O do texto-alvo usa os oito idiomas ensinados, com o limiar que já existia. O dos papéis acrescenta o português, para o apoio nativo não ser lido como espanhol. Os dois não são o mesmo objeto: incluir o português no primeiro rebaixava frases francesas que já passavam.

## Seleção

- `POST /lessons/generate` exclui unidades já entregues àquele perfil de idioma.
- Outro aluno não herda essa exclusão.
- Se ainda existe unidade aprovada, mas todas já foram praticadas, a resposta traz `exhausted: true` e `selection_trace.exhaustion = curated_pool_exhausted`. O gerador não fabrica outra lição com o mesmo material e essa resposta não grava lição nem sessão novas.
- Retomada da mesma tela, no mesmo modo e idioma, não dispara outro `generate` enquanto o componente permanece montado. Recarregar a página ainda pede uma lição; isso continua pendente.
- Embaralhar alternativas não muda o fingerprint da questão. Retry legado continua olhando a mesma lição e não devolve item já revelado como avaliação inédita.
- O roteiro simulado da conversa usa a contagem real de falas do tutor, não a janela de dez mensagens.
- Revisão SRS e vocabulário em outra tarefa continuam nos caminhos que já existiam. O placement não foi reescrito.

## Conteúdo

Nenhum lote novo foi gerado nem aprovado. O pipeline é `generate_incremental_batches`: o chamador gera, a função valida e não promove sozinha um item a aprovado. Não há cota automática de 200.

O catálogo estático do código, contado em 2026-11-07, não é o inventário aprovado do banco:

| Língua | Vocabulário no banco estático | Leitura | Escuta | Placement |
|---|---:|---:|---:|---:|
| en | 98 | 4 | 4 | 33 |
| es-ES, fr, ja, zh-CN | 24 | 4 | 4 | 33 |
| it, de | 24 | 4 | 4 | 28 |
| la | 30 | 4 | 4 | 34 |

Cada língua tem 21 payloads iniciais (7 modos × A1, A2, B1). Quantidade aprovada e elegível no Postgres de produção não foi medida.

## Publicação

Não houve push nem deploy. Não há migração nesta mudança. Se a publicação for autorizada: backend primeiro, depois frontend, porque `NEXT_PUBLIC_API_URL` entra no build. Rollback: no Coolify, publicar de novo a imagem anterior. O último commit em `origin/main` é `d6cd9d4`. Esse SHA não foi lido no painel.
