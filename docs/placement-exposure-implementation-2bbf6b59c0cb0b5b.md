# Placement exposure — execução local

Proposta aprovada pelo usuário em 08/10/2026: placement-exposure-proposal-2bbf6b59c0cb0b5b.md. Execução inline com TDD; nenhuma publicação, produção, IRT, provider/modelo novo.

Ruling: source_test_id/source_item_id do ledger são identificadores históricos de proveniência, sem FK para dados pedagógicos apagáveis; apenas user_id é FK CASCADE. Isso preserva a identificação da fonte após reset, sem criar ponteiros navegáveis inválidos. Ledger é preservado; exclusão definitiva da conta o elimina.

Ruling: não ativar reuso por padrão no assessment. O seletor permite fallback explícito para integração/teste, mas a API normal encerra parcial quando falta conteúdo inédito; não gastar tempo do aluno com evidência inelegível. Reuso não altera streak ou CEFR. Retomada da mesma delivery é idempotente.

Ruling: cooldown completo de30dias é operacional; um parcial pode complementar antes se existir conteúdo aprovado inédito disponível. Cada complemento conserva exposição da conta; não soma scores antigos ao teste novo.

Implementado: ledger/migration0018, snapshots de chaves, leitura de delivery/answer legadas, prioridade a inéditos em faixa permitida, isolamento por conta/idioma, produção também sujeita a exposição, exposição antes de responder, score descritivo separado do suporte fresco, fim por bank_freshness_exhausted, forms operacionais validadas por matriz e metadados. Sem detector de paráfrases nem equivalência psicométrica.

Reset: padrão preserva ledger e arquiva fontes legadas antes de apagar sessões. Ajuste autorizado: --clear-placement-exposure exige environment != production e banco explicitamente identificado pelo sufixo *_test ou *_dev (SQLite em memória também é banco técnico efêmero). Produção é recusada mesmo com nome de teste. Dry-run e rollback mantidos. CLI não expõe override de ambiente.

Policy placement-exposure-v2: cooldown_days=30 é configuração versionada em EXPOSURE_POLICY e seu snapshot é persistido no teste e resultado; mudar o prazo exige nova versão. Prazo operacional, sem fundamento psicométrico alegado. Reuso pode ser exibido/respondido pelo fallback explícito quando esgotam inéditos compatíveis, mas não contribui para adaptação, faixa, sufficient evidence ou overall. Assessment mantém encerramento parcial como padrão.

Validação dos quatro ajustes posteriores:88 testes backend de exposição/API/reset passaram; diff-check passou. Cinco novos casos primeiro falharam antes da implementação; verificam proteção em produção/banco não marcado, liberação test/dev e snapshot da configuração. Sem nova migration, mudança de frontend ou produção.

UX: atividades submetidas e puladas separadas; contagem por skill; sem target ou barra percentual como promessa. Encerramento diferencia banco esgotado, critério e limite. Sem gabarito imediato em assessment. Hook de revelação existe somente para futuros fluxos explícitos de review.

Revisão independente encontrou duas falhas de edição durante a entrega: recuperação sem delivery e avaliação contra opções/CEFR mutáveis. Quatro regressões falharam antes da correção; contrato de avaliação imutável agora é separado da identidade semântica. Edição relevante invalida a entrega e next-item recupera uma atividade respondível. Snapshot legado sem contrato conserva apenas a proteção que sua fonte permite.

Validação final: backend exposição/API/delivery62 passed; cobertura/reset/revisões52 passed e1 skipped; migrations12 passed (126 testes aprovados nas rodadas finais,27 avisos de depreciação Alembic). Frontend integral309 passed em39 arquivos; typecheck, build, lint dos arquivos frontend alterados e git diff --check passaram. A suíte integral backend anterior (1642 passed) é pré-exposição e não certifica este diff. PostgreSQL/concurrency permanece pendente sem POSTGRES_TEST_URL; não foi executado diagnóstico em produção.

Limites: dados históricos já apagados são irrecuperáveis sem fonte externa. Dados legados sem snapshot usam conteúdo atual e origem explicitada. Snapshot não prova leitura ou playback. Migração não executada em produção; ensaio PG pendente de banco dedicado.
