# Contrato de atividade exposto na API

A rodada 1 não muda o frontend. `public_activity` aplica `apply_language_contract` e omite a atividade quando `deliverable` é falso (`quality_status` `language_invalid` ou clone inglês conhecido).

Campos que o frontend da rodada 2 pode ler, quando já existem na atividade:

- `target_language`, `native_language`
- `prompt_target` copiado de `prompt` quando o campo novo falta
- `title_target` copiado de `title` na mesma condição
- `prompt_native`, `scenario_target`, `scenario_native`, `instruction_native` somente se o produtor os gravou
- `interaction_family`
- `quality_status` quando o conteúdo já o tem; ausência não é gravada como `unknown` nem como `approved`
- `support_visibility` quando o conteúdo já o tem (a fatia FR B1 usa `spot`)

`prompt_pt` continua no payload legado e não é promovido a `prompt_native`.

Ditado entregue pela API: `type=dictation`, `show_text=false`, `response_mode=typing`, `compare=normalized_text`, `audio_text` separado do enunciado.
