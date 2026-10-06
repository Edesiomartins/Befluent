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

## Língua nativa — contrato desta rodada (2026-10-05)

Contrato documentado antes da alteração de endpoints. `native_language` pertence
ao usuário; `language_code`/`target_language` identificam o idioma estudado.
Interface continua portuguesa. Cadastro não muda: coleta no onboarding/perfil.

- `POST /onboarding/complete`: novo campo opcional `native_language` (string/null).
  Omitir preserva valor existente; null explícito limpa. Não inferir pelo navegador.
- `GET/PATCH /profile`: consulta/atualiza native_language; PATCH aceita somente
  idioma, somente name ou ambos. Campos omitidos preservados.
- `GET /auth/me`, respostas de perfil/onboarding/login: `native_language` e
  `native_language_required` (true quando null). Perfil/status expõem
  `native_language_options`; códigos reutilizam catálogo/mapa BCP47 alvo,
  mais `pt-BR` como apoio. Não existe curso pt-BR.
- Strings não reconhecidas: 422, sem alteração persistida. Campo nullable não
  tem default e migration não preenche usuários antigos.
- LessonPayload: preserva `language_code`=alvo e campos existentes; adiciona
  `target_language`, `native_language`, `native_language_required`,
  `language_policy`. Traduções continuam separadas de exemplos/texto/áudio.
- Material estático/mock possui apoio pt-BR: outro idioma nativo não recebe esse
  material como tradução nativa. Geração IA configurada recebe o par correto;
  sem material/provedor compatível, erro recuperável `native_support_unavailable`.
  Nativo ausente em material dependente de apoio: 409 `native_language_required`.
  Contas/login/perfil/onboarding e encerramento de sessões continuam acessíveis.
- Conteúdo persistido incompatível após mudar língua nativa não deve ser
  reinterpretado/reutilizado. Não há tradução automática do corpus nesta rodada.
- Piper/STT mantêm idioma-alvo; native_language não seleciona voz principal.

Cursor deve oferecer seleção de língua nativa e tratar ausência/indisponibilidade
de apoio. Nenhuma alteração de frontend é feita pelo Codex nesta rodada.

### Separação de campos e conteúdo legado

- Prompts pedem campos primários no alvo e apoio em `*_native`: explanation_native, instruction_native, hint_native, feedback_native, translation_native e scenario_native. Campos opcionais não são preenchidos por tradução automática.
- `support_visibility`: PRE_A1/A1 prominent, A2 discreet, B1 spot, B2 expandable, C1/C2 off; ausência de nativo off. Apoio avançado pode ser solicitado/necessário, mas nenhuma porcentagem é inventada.
- Gramática estática PT conserva `explanation` legado por compatibilidade e declara `explanation_native`, `support_language=pt-BR`, `primary_explanation_available=false`; não certifica explicação original no alvo. Enriquecimento editorial desse campo permanece pendente.
- Mudança de nativo: lição persistida incompatível retorna 409 `lesson_native_language_mismatch`; explicação inglesa conhecida fora do par retorna `lesson_language_invalid`. Dados não são apagados.
- Vocabulário/SRS/ciclos lexicais/Teaching Flow estáticos exigem apoio PT disponível; isso evita gravar inglês no campo legado `translation_pt`. Escrita heurística conserva métricas e suprime aviso/feedback PT para outro nativo ou nativo ausente.
- Histórico assistente de conversas guarda provenance no `source` existente (`native:<code>`/`native:unset`); histórico incompatível retorna `conversation_native_language_mismatch`, sem apagar mensagens. Mensagens legadas `source=text` só são reutilizadas com nativo PT explícito.
- Guard determinístico detecta apenas corpus inglês conhecido e padrões específicos; não é um detector universal de idiomas, nem garante a qualidade de um provedor real.
