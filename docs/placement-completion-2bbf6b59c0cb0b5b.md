# Incidente placement: conclusão idempotente

Data: 2026-10-07. ID: `2bbf6b59c0cb0b5b`.
Teste informado: `14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e`.
Escopo: backend local. Sem commit, push, deploy ou alteração do banco de produção.

## Causa comprovada no código e reprodução

`SessionLocal` usa `autoflush=False`. Os testes usavam autoflush ativo.
`_records` exclui produção (writing/speaking) das evidências objetivas.
`engine.build_result` inclui writing em `not_assessed_skills`.
O complete antigo tinha dois caminhos sobrepostos:

1. Loop not_assessed: SELECT writing; adiciona uma section pendente.
2. Bloco writing_answer: outro SELECT writing; não enxerga o INSERT pendente.
3. Adiciona outra section, agora score 0.96/status calibrating.
4. Flush em `_apply_to_profile`/geração de currículo/commit envia ambos INSERTs.
5. A constraint rejeita a segunda linha e a transação não conclui.

Reproduzido antes da correção com SQLite e autoflush de produção: mesmo par
test_id/skill, score 0.96, max_score 1.0, status calibrating no INSERT rejeitado.
O DETAIL do PostgreSQL não prova que writing já existia antes da request:
a primeira linha pode ter sido inserida pela própria transação.
Não houve consulta ao banco nem à versão implantada em produção nesta tarefa.

## Fluxo rastreado e escritores

- POST /placement-tests cria/retoma PlacementTest; nenhum INSERT de section.
- next-item reconstrói estado adaptativo, entrega item e persiste delivery.
- answers corrige no backend e persiste PlacementTestAnswer.
- writing chama evaluate_writing e persiste resposta/feedback; não cria section.
- next-item após redação retorna ready_to_complete; não cria section.
- complete exige mínimo de evidência objetiva, calcula CEFR por skill e agregado,
  consolida sections, grava resultado no próprio PlacementTest, atualiza/cria
  UserLanguage, e assegura currículo ativo quando diagnostic_status=ready.
- Checkpoints passam por apply_checkpoint_outcome; não geram currículo novo nem
  promovem CEFR curricular; apenas registram a origem checkpoint no perfil.
- Não há tabela separada de placement result nem criação de LearningGoal no
  complete. Descendentes do currículo e objetivos autorais usam o gerador atual.
- Busca global: criação de PlacementTestSection só em complete; migration 0003
  cria a tabela/constraint, e o reset apenas referencia a tabela para limpeza.
- Frontend chama complete via POST e navega para resultado. O cliente api não
  contém retry automático; isso não elimina requests paralelas/reenvio externo.

## Decisão e implementação

- Manter `uq_placement_sections_test_skill`; migrations/schema inalterados.
- Construir valores finais em mapa por skill, aplicando writing antes de
  persistir. Um único loop get-or-update reutiliza IDs existentes.
- Serializar escritores placement por `SELECT ... FOR UPDATE` em User e depois
  PlacementTest. O lock de User coordena inclusive placements diferentes que
  poderiam disputar criação do mesmo perfil/currículo. next-item, answers,
  writing e complete usam a mesma ordem; locks duram até commit/rollback/close.
- Recarregar PlacementTest com populate_existing depois de esperar pelo lock;
  status em cache não pode disparar outra finalização após conclusão concorrente.
- O early return para completed devolve resultado sem repetir efeitos.
- Uma única transação inclui status, sections, perfil e currículo. Geradores
  envolvidos usam flush, não commit. Falha antes do commit permite rollback e
  retry; falha da resposta depois do commit permite retorno do resultado salvo.
- Remover captura ampla de APIError do gerador: não concluir silenciosamente
  sem consolidar currículo quando o diagnóstico está ready.
- Writing sem score mantém calibrating/CEFR ausente; score=0/max_score=0 atende
  as colunas NOT NULL e não representa uma avaliação 0/1.
- Alinhar TestingSession a autoflush=False para exercitar a configuração real.

Um upsert isolado de sections não protegeria status/perfil/currículo. Os locks
dos pais permitem get-or-update seguro entre os escritores atuais e preservam
identidade das sections. Novos escritores precisam respeitar esse protocolo.
SQLite ignora FOR UPDATE; seus testes não comprovam concorrência PostgreSQL.

## Testes e validação

- test_placement_completion.py: escrita sem section prévia; escrita/leitura
  prévias preservam IDs; outras skills corretas; complete repetido compara
  todas as tabelas; constraint efetivamente rejeita duplicata; escrita sem score;
  falha RuntimeError/APIError após geração faz rollback e aceita retry;
  consolidação parcial reutiliza perfil, currículo e todos os IDs descendentes.
- test_placement_migration.py: upgrade preserva unicidade test_id/skill.
  Caminho 0001/0002 via metadata pode criar constraint sem nome; 0003 declara
  explicitamente uq_placement_sections_test_skill. Nenhum caminho foi alterado.
- test_placement_completion_postgres.py: duas sessions independentes com status
  antigo em cache concluem em paralelo; verifica resultado igual, uma seção por
  skill, um perfil, um currículo e retry sem alteração em qualquer tabela.
- PostgreSQL opt-in usa exclusivamente POSTGRES_TEST_URL, banco PG18 *_test e
  schemas temporários isolados. Não usa DATABASE_URL de produção.
- Reprodução antes do fix: 1 failed, 2 passed; failure era o INSERT writing
  duplicado. Reprodução da APIError engolida também falhou antes de removê-la.
- Específicos finais + constraint migration: 8 passed, 2 warnings, exit 0.
- Placement/API/delivery/engine/migrations/checkpoints: 114 passed, 1 skipped,
  21 warnings Alembic, exit 0 (rodada anterior à adição do teste de constraint,
  que passou separadamente). PostgreSQL skipped por URL ausente.
- compileall e git diff --check passaram.
- Suíte completa executada: 1613 passed, 1 failed, 3 skipped, 40 warnings,
  exit 1, 1149.01s. A única falha foi
  test_quality_gate_v2::test_double_answer_rejected, pelo setup sem flush.
  Corrigido o setup e reexecutado seu arquivo inteiro: 24 passed, 4 warnings,
  exit 0. A suíte completa não foi repetida após esse ajuste exclusivo no teste;
  não afirmar uma rodada integral verde. Os três skips são os testes PostgreSQL
  sem POSTGRES_TEST_URL (placement paralelo e dois testes anteriores de reset).

Arquivos desta alteração: backend/app/api/placement_tests.py;
backend/tests/conftest.py; backend/tests/test_placement_completion.py;
backend/tests/test_placement_completion_postgres.py;
backend/tests/test_placement_migration.py; backend/tests/test_quality_gate_v2.py;
este relatório.
Os documentos de reset/plano já estavam untracked antes da tarefa e foram
preservados sem alteração.

A suíte geral identificou uma dependência implícita de autoflush no setup de
test_quality_gate_v2::test_double_answer_rejected: o rewind de cursor simulado
não era persistido antes do refresh sob lock já existente no Teaching Engine.
Adicionado db_session.flush() explícito no teste; nenhuma alteração no serviço
Teaching Engine. O caso falhou antes e passou após esse ajuste de setup.

## Riscos, pendências e retomada

- Sem o lock, qualquer skill e os efeitos downstream poderiam disputar INSERT
  em chamadas paralelas. A duplicação intrarrequest identificada era writing.
- POSTGRES_TEST_URL ausente: teste paralelo escrito mas execução real pendente.
- Locks serializam requests de placement da mesma conta durante a geração do
  currículo. Outros endpoints que geram currículo/onboarding não foram alterados
  e não são certificados como concorrentes com placement nesta correção.
- Criação simultânea de placements (POST /placement-tests) não integra o
  protocolo novo: a garantia aqui cobre os escritores/conclusão de cada teste.
- Risco preexistente entre contas diferentes: ensure_theme_objective usa
  SELECT/INSERT/flush para LearningObjective global único por language_id/code.
  Currículos B2+ de duas contas podem disputar um tema ainda ausente; User locks
  distintos não cercam esse recurso global. A constraint evita duplicatas, mas
  uma conclusão pode falhar e precisar de retry. Agora a falha reverte a
  conclusão inteira. Pendência separada: criação atômica do objetivo compartilhado
  e teste PostgreSQL com duas contas. Não afirmar sucesso de primeira tentativa
  para todas as finalizações entre contas diferentes.
- Testes já completed mas corrompidos por versões/importações anteriores não
  são reconstruídos automaticamente pelo early return; exigem diagnóstico.
- O placement deste incidente pode ser retomado após deploy do backend: respostas
  e redação foram commitadas antes; finalização falha não faz commit parcial.
  Sections prévias legítimas são reutilizadas. Não é necessário resetar o teste
  nem apagar writing. Essa recomendação pressupõe o fluxo/transação investigados;
  o estado atual daquele ID em produção não foi lido nesta tarefa.
- Próximos passos: executar teste PG18 dedicado; revisar alterações; autorizar
  publicação/deploy do backend; repetir complete do mesmo ID e verificar resultado.
- Revisão independente: nenhuma falha crítica/importante nas alterações deste
  incidente; validou protocolo e atomicidade por inspeção. Identificou a corrida
  global acima como risco importante preexistente, fora da garantia por conta.
