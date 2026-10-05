# Contrato frontend–backend: correções de integridade (2026-10-05)

Rotas, payloads de sucesso e schemas permanecem compatíveis. Ajustes abaixo
tratam solicitações inválidas que antes podiam ser aceitas.

- `POST /conversations/{id}/complete`: Conversation abandonada responde
  409 `conversation_already_abandoned`. StudySession abandonada responde
  409 `session_already_abandoned`; vínculo ausente responde 404 `session_not_found`.
  Repetir conclusão válida mantém 200, sem novo evento ou horário.
- Mensagem em Conversation cuja StudySession já foi encerrada responde
  409 `session_not_active`; não persiste mensagens nem chama o provedor.
- `POST /teaching/slice/flows/{id}/answer` (e consumidores do mesmo serviço):
  `__ack__` em atividade avaliativa responde 422 `invalid_acknowledgement`.
  Atividades passivas continuam aceitando Continuar/resposta vazia; não geram
  evidência de compreensão. Apresentação lexical mantém evidência `exposure`.
- `POST /teaching/slice/flows/{id}/retry`: remediação que não é a pendente
  do fluxo responde 409 `remediation_flow_mismatch`; não altera outros alunos.
  Fluxo encerrado responde 409 `flow_closed`. Marcador `__ack__` não dispensa
  resposta em retry avaliativo (422 `invalid_acknowledgement`).
- Responder transferência avança o cursor. Esgotar atividades fecha o fluxo
  como `needs_review` quando a política não sustenta `mastered`.
- Com `LANGUAGE_ENTITLEMENTS_ENABLED=true`, mensagens de conversa, acesso por
  ID na Teaching Engine e STT/TTS validam o direito atual do idioma e retornam
  403 `language_locked` quando ausente, expirado ou cancelado. A flag desligada
  mantém acesso legado. Encerramento da conversa continua disponível.
- Progresso de mastery com apenas `exposure` permanece `calibrating`, sem
  percentual de domínio; exposição lexical continua persistida na memória.
- Abandonar Conversation vinculada a StudySession concluída responde
  409 `session_already_completed`, preservando ambos os estados.
- Respostas incorretas retornam mastery calculado após registrar o erro.
  Ao falhar no último retry permitido, o fluxo encerra em `needs_review` na
  mesma resposta, preservando a tentativa e o histórico; novo retry recebe 409.
- Retry passivo/fallback Continue avança com resultado existente `partial`,
  sem evidência `error_repaired` e sem resolver o erro anterior. A atividade
  pública de fallback é `recognition`, sem gabarito, para permitir Continuar.

Os prefixes acima são relativos a `/api/v1`. Falhas de persistência continuam
sem sucesso parcial: a transação da requisição é revertida ao fechar a sessão.
