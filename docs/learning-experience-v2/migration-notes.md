# Notas de migração

Não há migration nesta rodada. Os campos novos vivem no JSON da atividade e no traço da sessão (`selection_trace`).

- `quality_status` ausente continua elegível no seletor da sessão e no pool. Status explícito `draft`, `generated`, `review_required`, `rejected` ou `language_invalid` não entra no plano.
- `generated` não é tratado como aprovado. `validate_batch` continua exigindo `approved` e proveniência.
- O pipeline segue `generate_incremental_batches` → `validate_batch`. Não há geração silenciosa durante a sessão nem preenchimento até 150–250.
- Conteúdo legado sem `interaction_family` recebe a família na hora do plano, a partir do `type`. O banco antigo não é reescrito.
- `family_key`, `seen_activity_ids`, `retired_families`, exposição, cooldown de 7 dias e vocabulário adiado permanecem.
