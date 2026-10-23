# Correções da revisão dos exercícios — 2026-10-16

Escopo: backend, sobre `760ac12`. Sem frontend, migration, commit, push,
deploy ou operações em produção.

## Comportamento

- O bloqueio da última modalidade incorreta considera apenas o último resultado
  correto/incorreto avaliado do mesmo aluno e item. Expira em sete dias; um
  acerto posterior encerra o bloqueio. Tentativas parciais ou pendentes não
  comprovam recuperação. A exclusão por exposição recente continua independente.
- A fila de vocabulário adiado é reconciliada com essas tentativas: acerto
  posterior retira o adiamento da projeção; novo erro mantém a modalidade e o ID
  da tentativa mais recente, independentemente da ordem das sessões antigas.
  Snapshots não são alterados. Legado sem tentativa avaliável permanece pendente.
- Família lexical continua `vocab:<id>`. Família não lexical usa frase-modelo
  explícita ou enunciado com resposta, no escopo de objetivo, idiomas e nível.
  Resposta curta isolada não agrupa questões diferentes. Sem contexto suficiente,
  usa a identidade da atividade.
- Gerador inclui uma `pattern_key` opaca comum ao gap, ordenação e múltipla
  escolha da mesma frase-modelo. Snapshots antigos desses formatos permitem
  recompor a identidade a partir do modelo efetivamente armazenado. Chaves
  antigas amplas não são usadas sozinhas para excluir famílias novas.
- Retry não lexical continua repetindo a atividade; erro lexical continua saindo
  da sessão. Acerto pós-gabarito continua `ERROR_REPAIRED`.

## Arquivos

- `backend/app/services/session_engine.py`: resultados recentes e adiamentos.
- `backend/app/services/activity_pool.py`: famílias e compatibilidade histórica.
- `backend/app/services/activity_generator.py`: identidade comum de frase-modelo.
- `backend/tests/test_exercise_review_regressions.py`: regressões novas.
- `backend/tests/test_family_exclusion.py`: fixtures de irmãos com modelo explícito.
- `backend/tests/test_seen_activities_acceptance.py`: verificações usam o objetivo
  real da atividade planejada, em vez do objetivo fictício da fábrica de testes.

## Validação

- TDD: nove das dez regressões iniciais falharam pelos defeitos esperados; a
  proteção de resultado parcial já passava. Quatro regressões adicionais de
  compatibilidade falharam antes da correção correspondente. O caso vazio
  detectou e protegeu um erro intermediário de fallback.
- Focal final: **23 passed** (19 regressões novas + 4 testes de família).
- HTTP do boletim: **5 passed** fora do sandbox.
- Aceite A–H: **14 passed**. A primeira ampliação teve 92 passed e duas falhas
  nessas fixtures, corrigidas e revalidadas antes da execução integral final.
- Revisão independente final: sem bloqueadores identificados.
- Compilação dos módulos/testes alterados e `git diff --check`: passaram.
- Suíte backend integral: em execução; resultado será registrado ao término.

O sandbox bloqueou `socketpair` local do asyncio/Windows antes da aplicação;
o teste HTTP foi repetido fora dele com `DATABASE_URL=sqlite://`. Nenhuma
dependência ou configuração da aplicação foi alterada para contornar isso.
PostgreSQL, concorrência real, navegador autenticado e produção não certificados.
