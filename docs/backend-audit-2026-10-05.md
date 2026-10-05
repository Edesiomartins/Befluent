# Auditoria do backend BeFluent — 2026-10-05

## Estado inicial e escopo

Checkout `main` inicialmente limpo. Stack mantida: FastAPI, SQLAlchemy,
PostgreSQL em produção, pytest com banco SQLite em memória nesta execução.
Backend, domínio, persistência, APIs e testes foram o escopo desta rodada.
Alterações de frontend surgiram durante a execução por outra ferramenta;
nenhuma foi editada ou revertida por esta auditoria. Sem commit, merge, push
ou deploy. Nenhuma migration ou mudança de schema.

## Arquitetura identificada

- `app/core/teaching.py`: fases, transições, resultados e política de domínio.
- `services/teaching_engine.py`: tentativas, evidência, erros, remediação e mastery.
- `services/teaching_flow.py`: sessão pedagógica, cursor, fases e lock de resposta.
- `services/teaching_slice.py`: avaliação, retry e orquestração determinística.
- `services/session_budget.py`, `session_engine.py`, `session_progress.py`:
  orçamento, seleção, ordenação por fase e progresso da sessão.
- `services/curriculum_teaching.py`, `api/curriculum.py`: Journey sobre
  currículo/blocos existentes; iniciar, restaurar, responder, retry e completar.
- `api/lessons.py`, `services/lesson_attempts.py`: lições, respostas objetivas
  legadas, sessões lexicais e encerramento administrativo.
- `services/study_sessions.py`, `api/conversations.py`: ciclo de vida e
  transação conjunta de Conversation/StudySession.
- `services/progress.py`, `language_progress.py`, `memory_engine.py`: métricas,
  eventos com dedupe, memória lexical e revisão de objetivos.
- `services/language_access.py`, `api/helpers.py`: concessão vigente por
  usuário/idioma, condicionada à flag existente.
- `api/speech.py`, `services/speech.py`: STT/TTS, temporários, limites e cache.
  Provedores, credenciais, vozes e seleção de modelo não foram alterados.

Uma TeachingFlowSession e uma StudySession são entidades distintas. Esgotar
o fluxo pedagógico não substitui a conclusão administrativa da lição/bloco.
Mastery continua dependendo da política de evidência e de erros bloqueadores.

## Achados corrigidos e causas

| Prioridade | Falha reproduzida | Causa e correção |
| --- | --- | --- |
| CRÍTICO | Retry podia avaliar uma remediação de outro aluno | Só o fluxo era autorizado; serviço não vinculava remediação à atividade pendente. Agora valida o ID pendente após lock e rejeita outro fluxo. |
| ALTO | `__ack__` pulava exercícios e gerava evidência sem resposta | Marcador enviado pelo cliente era tratado como sucesso independente do tipo. Agora somente atividades passivas permitem acknowledgement. |
| ALTO | Continuar gerava compreensão; exposição aparecia como domínio no progresso/histórico | Evidência padrão e tentativas administrativas entravam na agregação. Passivas não criam compreensão; exposição lexical permanece, mas fica fora da agregação de mastery; timeline ignora acknowledgement. |
| ALTO | Conversation abandonada podia virar concluída com StudySession abandonada | Complete não validava status da Conversation e pulava sessões encerradas. Agora valida ambos, rejeita vínculo ausente/incompatível e mantém a transação conjunta. |
| ALTO | Mensagens continuavam após encerrar StudySession | Só status da Conversation era verificado. Agora exige StudySession ativa antes de persistir mensagem/chamar IA. |
| ALTO | Estado desatualizado podia sobrescrever StudySession concluída | Helpers liam a identidade antiga sem lock. Complete/abandon compartilham lock e refresh da StudySession; Conversation também é serializada. Teste cobre identidade desatualizada; concorrência PostgreSQL ainda precisa execução real. |
| ALTO | Transferência não consumia o cursor e fluxo esgotado continuava ativo | Ramo transfer não avançava; faltava fechamento sem domínio. Agora avança e encerra em `needs_review` se a política não sustenta `mastered`. |
| ALTO | Falha de integridade ao gravar evento era engolida e conclusão recebia 200 | Todo IntegrityError era considerado duplicidade. Agora somente evento efetivamente existente é duplicidade; outra falha propaga e reverte a conclusão. |
| ALTO | Idioma bloqueado podia ser estudado por IDs existentes ou STT/TTS | Guard de entitlement só existia em parte das entradas. Teaching por ID, mensagens e fala verificam o direito atual. Flag desligada preserva o legado; encerrar Conversation continua possível. |
| MÉDIO | Resposta errada retornava mastery anterior ao erro | Avaliação ocorria antes de registrar o LearningError. Recalcula após o erro, alinhando resposta e persistência. |
| MÉDIO | Último retry incorreto deixava fluxo sem encerramento persistível | Limite só fechava numa transição posterior, seguida de operações incompatíveis. Agora encerra no último retry incorreto permitido. |
| MÉDIO | Retry passivo resolvia erro crítico sem demonstrar reparo | Continuar era CORRECT/ERROR_REPAIRED. Agora é PARTIAL, sem score/evidência de reparo; erro continua aberto e cursor avança para revisão. Fallback público apresenta Continuar, sem reabrir o gabarito. |

As correções foram motivadas por reproduções e pelos invariantes já existentes:
concluir não é dominar; erro só é reparado por resposta avaliada; sessões
encerradas não voltam à atividade por reenvio. Não houve alteração de quotas,
faixas CEFR, seleção de provedor ou trilha de idiomas por preferência pessoal.

## Contrato e persistência

As mudanças efetivas estão em `frontend-backend-contract.md`. Mantidos rotas,
campos obrigatórios e formatos de sucesso; documentados os erros 403/404/409/422
de solicitações inválidas e o resultado existente `partial` no retry passivo.
Sem migration. Dados históricos não foram apagados nem reinterpretados no banco.
Repetir conclusão válida de Conversation não duplica evento, horário ou sessão.
Falhas simuladas de commit e de gravação de evento mantêm ambos os registros ativos.

## Testes e evidência

- Seleção inicial: 44 testes passaram.
- Novos: 40 casos parametrizados em `test_backend_integrity_audit.py`.
  Cobrem bypass, passivas, transferência, duplicação, estado abandonado,
  vínculo ausente, isolamento de retry, commit/rollback, entitlement, timeline,
  limite de retry, identidade desatualizada e erro de evento não duplicado.
- Testes de antirrepetição e piloto curricular passaram a responder a questão
  efetivamente apresentada. Antes usavam bypass ou o gabarito pré-retry.
- Rodadas focadas: 47, 77, 58, 41, 66, 90 e 85 testes passaram em diferentes
  etapas. Cada correção principal teve regressão observada antes de implementar.
- Primeira suíte completa: 1.435 passaram, 4 falharam, 34 warnings. As quatro
  falhas eram `test_conversation_missing_session_rejects_completion`,
  `test_teaching_attempt_evidence_error_remediation_retry_transfer`,
  `test_te_multi_retry_no_cycle`, `test_te_retry_correct_is_error_repaired`.
  Causas: FK rejeita criação artificial de órfão; teste respondia questão antiga;
  dois setups pulavam exercícios com `__ack__`. Corrigidos e revalidados.
- Suíte final: **1.454 passed, 0 failed, 34 warnings**, código de saída 0,
  em 578,27 s. Comando: `.venv/Scripts/python.exe -m pytest --tb=short`
  a partir de `backend`, Python local 3.11.15. Warnings são a depreciação
  já existente de `path_separator` no Alembic.
  Log local: `backend/tmp/backend-audit-final-pytest.log`.
- `git diff --check -- backend docs`: sem erros de whitespace; Git avisa
  conversão LF/CRLF em arquivos existentes.
- Revisão independente: os dois achados adicionais foram corrigidos e
  reavaliados; nenhuma nova falha bloqueadora identificada no diff revisado.

## Session builder e regra dos 36

Orçamento longo: alvo 36, teto 40; curto: alvo 12, teto 14. Seleção respeita
quotas por área e diversidade disponível, limita modalidades por item e
ordena por fase. Conteúdo insuficiente reduz a sessão; não inventa exercícios
para completar o número. Banco/gerador lexical omitem alternativas ambíguas.
Os testes existentes cobrem vazio, insuficiência, repetição, ordem, correto,
incorreto, encerramento, ausência de conteúdo e rollback de matrícula.
O carregamento de exemplos, evidências e schedules usa consultas em lote;
não foi introduzido N+1 por item nesta rodada.

## Riscos e limites pendentes

- **ALTO — PostgreSQL real:** a suíte usa SQLite; não prova contenção,
  deadlocks ou corridas entre workers. Validar locks em banco de teste isolado
  antes de deploy. Nenhum acesso ou teste foi feito no banco de produção.
- **ALTO — histórico:** evidências falsas já gravadas por acknowledgements
  anteriores não foram removidas. Revisão de dados deve identificar origem
  com as tentativas, backup e plano de reparo específico; não excluir em massa.
- **MÉDIO — contratos legados:** resposta sem `activity_index` em fluxo não
  lexical não permite distinguir reenvio de resposta da próxima atividade.
  Inícios de sessão/conversa e mensagem textual não têm chave de idempotência
  de requisição. Não foi inventada uma deduplicação por texto: repetir texto
  pode ser uma produção legítima. Negociar contrato de retry com frontend.
- **MÉDIO — concorrência fora do slice:** tentativas/manipulações de fases
  expostas diretamente na API Teaching e criação de fluxos precisam auditoria
  concorrente própria. Dedupe de eventos usa constraint; isso não substitui
  serialização de todos os registros de evidência.
- **MÉDIO — escala:** agregações carregam histórico inteiro e mastery lê
  evidências/erros do objetivo em cada avaliação. Sem benchmark com dados
  reais nesta rodada; não houve refactor especulativo de performance.
- **MÉDIO — áudio:** WAV tem limite de duração; formatos comprimidos têm
  limite em bytes, e upload é lido antes da validação. Não foram adicionadas
  dependências de sistema para medir WebM/OGG. Piper/STT reais não foram
  exercitados contra serviços externos; testes usam provedores/dublês locais.
- **BAIXO — Alembic:** warning existente sobre `path_separator`, sem mudança
  de configuração ou migration nesta rodada.

Encerramento administrativo repetido de Lesson mantém o 409 existente;
StudySession e Conversation preservam conclusão idempotente. Um HTTP 409 em
Lesson já concluída não representa duplicação de progresso. A distinção
foi preservada para não alterar silenciosamente o consumidor paralelo.

## Arquivos desta rodada

Criados:
- `backend/tests/test_backend_integrity_audit.py`
- `docs/frontend-backend-contract.md`
- `docs/backend-audit-2026-10-05.md`
- `docs/superpowers/plans/2026-10-05-backend-integrity-audit.md`

Alterados:
- `backend/app/api/conversations.py`
- `backend/app/api/speech.py`
- `backend/app/api/teaching.py`
- `backend/app/services/language_progress.py`
- `backend/app/services/progress.py`
- `backend/app/services/study_sessions.py`
- `backend/app/services/teaching_flow.py`
- `backend/app/services/teaching_slice.py`
- `backend/tests/test_curriculum_te_pilot.py`
- `backend/tests/test_retry_antirrepeticao.py`

## Git status --short após a suíte

Arquivos frontend abaixo pertencem ao trabalho paralelo.

```text
 M backend/app/api/conversations.py
 M backend/app/api/speech.py
 M backend/app/api/teaching.py
 M backend/app/services/language_progress.py
 M backend/app/services/progress.py
 M backend/app/services/study_sessions.py
 M backend/app/services/teaching_flow.py
 M backend/app/services/teaching_slice.py
 M backend/tests/test_curriculum_te_pilot.py
 M backend/tests/test_retry_antirrepeticao.py
 M frontend/components/lesson-modes.tsx
 M frontend/components/study.tsx
 M frontend/tests/lesson-adaptation.test.tsx
 M frontend/tests/speech-ui.test.tsx
 M frontend/tests/voice-journey.test.tsx
?? backend/tests/test_backend_integrity_audit.py
?? docs/backend-audit-2026-10-05.md
?? docs/frontend-backend-contract.md
?? docs/superpowers/plans/2026-10-05-backend-integrity-audit.md
```
