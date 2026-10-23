# Famílias de interação

`interaction_family` é derivado do `type` em `learner_language_contract.INTERACTION_BY_TYPE`. Não é metadado inventado em conteúdo legado. Tipo ausente ou desconhecido vira `unknown` e não é escolhido como troca de interação no retry.

| type | interaction_family |
|---|---|
| presentation, review | presentation |
| recognition, reverse_recognition, multiple_choice | choice |
| listening_recognition | audio_choice |
| listen | audio_model |
| fill_gap | inline_gap |
| word_order | tap_order |
| matching | pair_match |
| lexical_production, controlled_recall, recall | recall |
| guided_production | guided_input |
| free_production | open_input |
| repeat | speech_repeat |
| shadow | speech_shadow |
| retell | speech_retell |
| conversation_prompt | dialogue |
| transfer_question | transfer |
| dictation | dictation |

O ditado é contrato de arquitetura: áudio, digitação, comparação por texto normalizado, `show_text` falso. O transcript não entra no enunciado.

`ActivityType.DICTATION` existe no enum. A área da sessão é listening. Matching continua sendo reconhecimento (acknowledgement) na correção.
