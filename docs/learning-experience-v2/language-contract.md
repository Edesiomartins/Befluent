# Contrato de idioma — Learning Experience V2

O aluno tem um idioma-alvo e uma língua nativa. O conteúdo principal fica no alvo. O apoio fica na língua nativa. Uma terceira língua não é entregue.

Campos aditivos, sem migration:

- `target_language`, `native_language`
- `title_target`, `title_native`
- `instruction_target`, `instruction_native`
- `prompt_target`, `prompt_native`
- `scenario_target`, `scenario_native`
- `hint_target`, `hint_native`
- `feedback_target`, `feedback_native`
- `support_visibility` (já existia na política de língua)
- `quality_status`
- `interaction_family`

`prompt` continua sendo o estímulo no idioma-alvo. `prompt_pt` é legado e não vira `prompt_native` sozinho.

`language_invalid` usa o guarda editorial já existente (clones conhecidos de inglês e status gravado). Item nesse status não é entregue. O guarda não certifica qualquer texto.

Ditado, quando o backend monta a atividade: `audio_text`, resposta digitada, `canonical_answer`, `compare=normalized_text`, `show_text=false`. O transcript não vai no enunciado.
