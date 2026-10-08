# Execução: placement coverage v2

Spec: placement-coverage-plan-2bbf6b59c0cb0b5b.md, aprovada para implementação em 08/10/2026, acrescida de speaking.

Execução local no checkout atual conforme preferência existente. Sem commit/push/deploy. Frontend incluído pelo pedido atual. Não escolher provedor/modelo novo.

Etapas: (1) resultado canônico/evidências; (2) selector/encerramento; (3) avaliações de produção e áudio autenticado; (4) projeções/legado/planejamento; (5) UI; (6) testes e relatório.

Speaking: reutilizar STT configurado e avaliar conteúdo linguístico da transcrição como provisório; acústica/pronúncia não medida. Decisão sobre avaliador de áudio real pendente de resposta do usuário. Não declarar CEFR global por transcrição somente.

## Implementação local

- Resultado v2 canônico com coverage, contagens, razões, proveniência e status por skill. Sessão completed pode retornar partial; overall exige cinco skills elegíveis. Síntese conservadora pela menor faixa, sem renormalização de subconjunto e sem confidence_score público.
- Seletor prioriza déficit de competência e confirmação de faixa; fallback não altera streak de outra faixa. Parada por cobertura objetiva, máximo ou esgotamento. Preflight calcula target possível e déficits; tarefas idênticas com IDs diferentes não ampliam capacidade nem são reapresentadas.
- Writing da IA conserva CEFR reportado, CEFR aceito conservador, critérios/modelo e limites como provisório; score heurístico não vira CEFR público. Tarefa entra no prompt do avaliador. Valores não finitos/booleanos são rejeitados.
- Speaking recebe arquivo multipart autenticado, exige delivery própria, usa STT no servidor, rejeita transcrição enviada como texto e mock. Áudio temporário é removido; transcript, hash/bytes/MIME e proveniência são persistidos. UI MediaRecorder com parada em 90 segundos, retry e skip. Análise textual específica para resposta oral, sem penalizar redação/pontuação e sem inferir acústica. Não é avaliação de pronúncia ou fluência acústica.
- Migração aditiva 0017: último assessment, resumo, planning_level e origem. Links seguem padrão legado de referência lógica, sem novo FK; reset valida referência cruzada também. Nenhum backfill ou reparo de histórico.
- Projeções públicas de dashboard/perfil/idiomas/progresso qualificam níveis históricos de placement; um parcial preserva nível anterior suficientemente coberto. Planejamento não equivale a nível medido. Parcial não gera currículo longo; currículos existentes são mantidos e prática continua acessível.
- Oito tarefas de fala e três de escrita extensa adicionadas ao catálogo versionado; rubricas marcadas dev_not_calibrated. Inventário em placement-coverage-fixtures-v2.json: 155 itens. Não foram clonados objetivos para simular cobertura.

## Limites e gates

- Banco objetivo ainda é insuficiente para reading/listening em todos os idiomas. A proteção está implementada; cobertura suficiente não pode ser garantida com este catálogo. Ampliação editorial independente e revisão humana continuam necessárias.
- Uma única produção writing/speaking permanece provisória e não elegível para overall. Política validada de produção e avaliador acústico não existem; nenhum provedor/modelo novo foi escolhido. Consequentemente, os novos resultados atuais permanecem parciais globalmente, embora úteis por skill.
- STT/IA reais dependem da configuração existente. Testes usam stubs; não certificam qualidade de reconhecimento dos oito idiomas, latim incluído. Nenhuma chamada paga foi feita.
- Áudio comprimido tem limite de bytes no servidor; duração de 90 segundos é limite do recorder cliente. Não há decodificador servidor para comprovar duração de formatos comprimidos. Não há retenção do áudio para reavaliação acústica futura.
- Migração e seed não executados em produção. PostgreSQL de concorrência depende de POSTGRES_TEST_URL; teste em SQLite não o substitui.

## Verificação

- Revisão independente: corrigidos exposição de global histórico sem cobertura, CEFR derivado de score IA inválido, ausência da tarefa no prompt, escopo confundido com global e impasse de catálogo vazio.
- Núcleo backend final: 104 passed, 2 warnings (Alembic), incluindo engine/API, conclusão idempotente e rollback, adapter legado, escrita/fala, esgotamento e migração.
- Frontend: 304 testes em 39 arquivos; typecheck e build concluídos. Novos testes verificam multipart, permissão negada e liberação do microfone. Gravação física de microfone e provedores reais não foram ensaiados em navegador autenticado.
- Compatibilidade backend: 85 passed (progresso por idioma, API e provedores com stubs). Reset/integridade de referências passou na rodada focal.
- Lint dos arquivos alterados passou; lint geral falha em erro preexistente no tests/speech-ui-latin.test.tsx:57 e tem cinco warnings fora deste diff. git diff --check passou.
- Rodada integral backend final: **1642 passed, 3 skipped, 40 warnings**, exit0, em 1121,19 segundos. Três testes PG ignorados por ausência de POSTGRES_TEST_URL; warnings de depreciação da configuração Alembic. Primeira rodada tinha seis falhas, resolvidas e verificadas nesta rodada completa. Log local: backend/placement-final-full.log.

Sem commit, push, deploy ou escrita em produção. ID de acompanhamento: 2bbf6b59c0cb0b5b.
