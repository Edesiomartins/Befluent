# Ciclo de aprendizagem lexical V2

Relacionados: [teaching-engine-v2.md](teaching-engine-v2.md), [spaced-repetition.md](spaced-repetition.md), [language-entitlements.md](language-entitlements.md).

## Objetivo

O modo Vocabulário deixa de ser só um deck de apresentação. Cada conjunto
percorre o Teaching Engine V2:

`ACTIVATING/INPUT` → `NOTICING/PRACTICING` → `PRODUCING` → revisão pela memória.

Não existe um segundo motor pedagógico. Tentativas, evidências, erros e
domínio continuam em `LearningAttempt`, `LearningEvidence` e `MemorySchedule`.

## Sequência

| Etapa | Fase | Atividade | Evidência |
|---|---|---|---|
| Presentation | activating / input | termo, tradução, frase e dois áudios | exposição |
| Recognition | noticing / practicing | termo → significado | `recognition` |
| Reverse recognition | practicing | significado → termo | `reverse_recognition` |
| Listening | practicing | áudio do termo, sem revelar a resposta | `listening_recognition` |
| Production | producing | digitação ou fala via `Recorder`/STT | `lexical_production` |
| Review | needs_review | fila adaptativa (`/reviews/due`) | memória / rating |

Um único acerto não marca domínio. O item só é `mastered` quando as quatro
evidências avaliadas existem no epoch atual. A lista obrigatória mora em
`lexical_policy.lexical_mastery_policy`, não em constantes soltas.

## Contrato de áudio

Toda atividade auditiva declara o alvo:

- `vocabulary_item` → sintetiza o termo;
- `example_sentence` → sintetiza a frase.

A apresentação e a revisão V2 expõem controles separados. Listening usa o
termo, nunca a frase. Piper, STT e Speech Coach não mudam neste fluxo.

## Identidade

- `VocabularyItem` é o termo persistido por usuário/idioma.
- `VocabularyExample` guarda a frase quando existir.
- Conteúdo antigo sem exemplo, forma contextual ou schedule continua
  utilizável. O frontend não inventa flexão por comparação de strings.

## Review

`vocabulary_review.select_due_reviews` escolhe a sessão:

- itens fracos (lapsos, baixa força) entram primeiro;
- com itens fracos vencidos, no máximo um item dominado entra;
- `ReviewItem` legado sem `MemorySchedule` permanece na fila;
- ratings `again/hard/good/easy` não mudam.

Erro no ciclo não repete o mesmo exercício imediatamente. O item volta
depois, pela fila de memória.
