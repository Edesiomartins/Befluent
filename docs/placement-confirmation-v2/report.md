# Placement: candidato e confirmação — 2bbf6b59c0cb0b5b

Data: 08/10/2026. Escopo: backend/engine/catálogo local. Nenhum commit, push, deploy ou escrita de produção; nenhuma migration/seed aplicada a banco persistente. Seeds de teste são locais e efêmeros. Frontend não editado nesta tarefa. Alterações preexistentes em API/planning/relatórios e alterações frontend de trabalho paralelo foram preservadas.

## 1. Causa atual

O catálogo anterior tinha 155 itens versionados, mas apenas 60 reading/listening testáveis. Cada uma das 80 células idioma × reading/listening × PRE_A1/A1/A2/B1/B2 tinha menos de duas evidências independentes. Reading/listening de italiano/alemão tinham lacunas adicionais. Quatro acertos distribuídos entre quatro faixas não satisfazem duas evidências na faixa decisória. A auditoria anterior não indicava perda das respostas pelo engine; esta inspeção confirma a incompatibilidade estrutural entre banco e policy. Produção não foi consultada nesta tarefa.

## 2. Regra determinística de candidate_level

`AnswerRecord` aceita chaves de identidade e elegibilidade. Apenas scores finitos entre 0 e 1, não booleanos, em faixas testáveis e elegíveis sustentam candidato. Itens reutilizados, feedback revelado e registros inelegíveis não sustentam classificação. Snapshot do ledger tem prioridade; legado sem snapshot usa identidade atual com limitação histórica explícita.

Identidades de passagem, áudio, prompt/exact e stimulus_family formam componentes conectados. Um componente contribui uma resposta independente, a primeira válida. Uma ponte entre família e passagem também colapsa o grupo; mudar ID/família não torna passagem igual independente. Não existe detector universal de paráfrases: clones sem texto compartilhado precisam da família editorial correta.

Candidato = maior faixa testável com pelo menos um sinal independente de score >=0,65. É uma hipótese de coleta, não domínio da faixa; pode permanecer candidato diante de erro ou contradição. Accuracy e conflitos determinam confirmação, e não promoção automática. Não representa probabilidade de CEFR. `highest_supported_signal` explicita essa origem. Sem sinal positivo, candidato null.

Contrato objetivo inclui `candidate_level`, `confirmation_required`, `confirmation_count`, `confirmation_needed`, `candidate_reason`, `selection_phase`, `independent_accuracy`, contagens brutas por CEFR e contagens independentes por CEFR. Objetivas não coletadas também têm candidato null/contagens independentes vazias. Produção conserva sua policy anterior.

## 3. Regra de confirmação

Nível medido conserva mínimo quatro evidências independentes na skill e duas na faixa decisória, com média >=0,65. Erro na faixa candidata ou desempenho abaixo do limiar em faixa inferior com >=2 observações exige três na faixa candidata e o mesmo limiar de média. Quantidade sozinha nunca confirma. `confirmation_needed` é mínimo total de observações, não saldo restante.

A1/A2/B1/B2 corretos uma vez: candidato B2, faixa medida null, confirmation_count=1/needed=2. Segunda B2 correta: B2 estimado. Segunda B2 errada: candidato B2, média 0,5, confirmação pendente/needed=3. Terceira B2 correta: média 2/3, permitindo B2 se demais critérios forem satisfeitos. Perfil contraditório pode permanecer parcial por esgotamento; não reduzimos mínimos para terminá-lo.

Uma faixa inferior já sustentada pode continuar medida enquanto uma candidata superior aguarda confirmação. O campo candidato nunca substitui essa medida. `eligible_for_overall` depende exclusivamente da estimativa sustentada, e overall continua exigindo todas as cinco skills elegíveis.

## 4. Selector e persistência

`next_skill` preserva exploração inicial/rotação e prioriza candidata deficitária após quatro observações. Dentro da skill, selector tenta a faixa candidata, depois as adjacentes por distância; desempate favorece inferior, depois exploração mais distante. Só depois considera outra skill. O fallback é explícito no trace (`skill_fallback`), com skill preferida e banda realmente entregue.

Estado distingue exploration/candidate/confirmation/confirmed. `selection_trace` e `last_selection` são persistidos em result_json; progress devolve o motivo. Motivos: candidate_band_confirmation, adjacent_band_evidence, broader_band_exploration ou adaptive_exploration. Ledger da sessão exclui estímulos já vistos mesmo após alteração editorial do item. Entrega aberta retoma o mesmo item compatível; não cria nova evidência.

`should_stop` não encerra por cobertura enquanto existir candidata superior não confirmada. Hard cap segue 30 respostas objetivas brutas, com stop_reason=maximum_reached e déficits preservados. Sem itens, mantém bank_exhausted/bank_freshness_exhausted e acrescenta stop_detail=confirmation_bank_exhausted/confirmation_freshness_exhausted quando aplicável. Déficits são persistidos e aparecem em assessment_coverage. Nenhum encerramento inventa nível global.

## 5. Catálogo antes/depois

- Total: 155 -> 255 itens. Acrescentados 100, somente reading/listening.
- R/L nas cinco faixas testáveis: 60 -> 160.
- Oito idiomas × duas skills × cinco faixas: todas as 80 células agora têm dois grupos independentes e dois itens.
- Novo conteúdo: sinais/notas PRE_A1; atividade infantil e encontro A1; viagem interrompida e encomenda A2; negociação de uso de terreno e motivação voluntária B1; acesso digital e consentimento de assinatura B2. Lacunas de it/de recebem ainda análise de tarifa/transporte e redução de desperdício. São estímulos e tarefas distintos dentro de cada idioma; traduções entre idiomas não são clones dentro da mesma avaliação.
- Passagens e audio_scripts no alvo; pergunta/opções em PT, conforme apoio disponível. Novos itens declaram native_language=pt-BR/target_language e são excluídos para nativo incompatível. Retomada/submissão após mudança de nativo retorna 409 native_support_unavailable. Não introduzimos inglês como apoio universal. Apoio novo fora PT permanece indisponível.
- Options têm posição da resposta variada; nenhuma resposta depende apenas do enunciado. Não foram duplicados IDs nem reusados estímulos existentes.
- Fixtures versionados e seed idempotente existente. Approved no seed significa liberado operacionalmente, não validado por especialista. Metadados novos deixam revisão especializada pendente.

Matriz legível: [catalog-matrix.md](catalog-matrix.md). Matrizes completas por language_code/skill/CEFR/item_type/fresh independent stimulus groups/total items: [antes](catalog-before.json) e [depois](catalog-after.json). O audit_placement_coverage agora reproduz também independência. Fresh aqui significa conta hipotética sem exposição e apoio PT; disponibilidade de conta existente depende do ledger. Não representa inventário de produção.

## 6. Planning e exposure

Policy placement-planning-v1 mantida: desempenho objetivo insuficiente só apoia entrada com >=4 observações independentes e accuracy elegível >=75%; duas competências apoiando e teto parcial A1. A faixa candidata não entra na mediana de níveis medidos nem determina diretamente a faixa de entrada. O trace registra candidate_level/candidate_influenced_planning/candidate_use quando seu desempenho sustenta entrada. Accuracy independente evita que clones/reuso distorçam planning.

Sem caminho candidate -> overall, skill medida ou current_level global. Snapshot/retenção de planning anterior e adapter legado existentes foram preservados. Writing/speaking continuam provisional/inelegíveis para global conforme policy vigente. Cooldown 30 dias e ledger preservado após reset permanecem. Forms usam os mesmos componentes independentes, não prioridade de family que pudesse esconder passagem duplicada. Audit read-only do resultado aceita ORM e registros SimpleNamespace, usando snapshot quando disponível.

## 7. Arquivos desta tarefa

Aplicação: backend/app/services/placement_engine.py, placement_coverage.py, placement_exposure.py, placement_planning.py; backend/app/api/placement_tests.py. Conteúdo: backend/app/data/placement_items/{en,es-ES,fr,it,de,ja,zh-CN,la}.json.

Ferramentas: backend/scripts/audit_placement_coverage.py e audit_placement_result.py. Testes: backend/tests/test_placement_confirmation.py (novo), test_placement_api.py, test_placement_coverage_v2.py, test_placement_exposure.py, test_placement_planning.py e test_placement_partial_integration.py. Cenários históricos com déficit usam catálogo legado explícito; expectativa de target passa a refletir banco ampliado. Relatórios/artefatos nesta pasta. Sem novas dependências/schema.

API/planning já tinham alterações locais de legacy_planning_projection; não são integralmente atribuíveis a esta tarefa. test_legacy_placement_planning.py e documentos anteriores também eram preexistentes. Git status completo está em git-status.txt; inclui frontend paralelo, não editado pelo agente desta tarefa.

## 8. Testes e resultados

Rodada final: **223 passed, 4 skipped, zero falhas, exit 0**, em 160,66s. Inclui 39 casos novos e regressões de engine, API, delivery, coverage, completion/idempotência, exposure/cooldown, planning/legado/partial HTTP, audit e reset. Suíte local SQLite/TestClient, com mock explícito. Compileall e git diff --check passaram. Audit standalone verificou 255 itens e todas as 80 células R/L no piso de dois grupos independentes.

Quatro skips por POSTGRES_TEST_URL não configurado: parallel completion/stale status/downstream; parallel session creation/delivery/exposure; cross-schema cascade refusal; fencing de ponteiros de outra conta no reset. Concorrência/segurança PostgreSQL real permanecem não verificadas. Não existem resultados de produção nesta tarefa.

Evidência final: [test-results.txt](test-results.txt).

Novos casos cobrem reading/listening 4 faixas + confirmação certa/errada, candidato fora de overall/current, planning operacional e trace, reused/feedback inelegível, passagem/áudio/família e ponte semântica, selector/faixa adjacente, persistência do motivo, snapshot editado, hard cap bruto, esgotamento parcial, native incompatível e troca durante entrega, piso em oito idiomas, seed idempotente, forms clonados e contagens brutas versus independentes. HTTP comprova persistência e paridade complete/GET, sem promover global.

Comando final usa Python de backend/.venv, cwd backend, DATABASE_URL=sqlite://, SESSION_SECURE=false, COOKIE_DOMAIN vazio e AI_MOCK_MODE=true no processo de teste. Não modifica configuração persistida. Rodada preliminar da raiz carregou cookies/IA externos de .env; não certifica provider real. Suíte integral de todo backend não executada; verificação cobre os módulos relevantes listados no log final.

## 9. Déficits remanescentes

Nenhuma célula R/L testável deficitária no catálogo implementado com apoio PT e conta inédita. Não há garantia de duas confirmações após exposição anterior ou em perfil contraditório que exige três. Apoio para outros nativos, margem editorial quatro, faixas VG ainda incompletas e produção de amostra única continuam pendências. C1/C2 não foram ampliados nem tornados testáveis. Overall pode e deve continuar parcial.

## 10. Riscos e próximos passos

Revisão independente por leitura apontou snapshot mutável, guard nativo e hard cap; todos reproduzidos e corrigidos com regressões. Rechecagem final sem bloqueador concreto nos caminhos revistos.

Limiares e níveis/difficulty editoriais são heurísticos, sem calibração psicométrica; exigem especialista por idioma, especialmente ja/zh-CN/latim eclesiástico. Script de listening distinto não comprova áudio inteligível ou renderização TTS. Validar acusticamente antes de rollout. Identidade semântica não descobre todos os clones paráfrases automaticamente. Conteúdo legado sem declaração nativa requer auditoria separada; não foi reescrito silenciosamente.

Dois itens são piso operacional, não margem para repetição ou conflito; déficit após exposição é legítimo. Resultados antigos completos não são reclassificados/backfilled. PostgreSQL, inventário live, produção e providers não certificados. Antes de publicação, revisão editorial/auditiva, ensaio PG, revisão do diff e autorização de atualização; manter ordem backend -> frontend. Frontend pode consumir campos novos em tarefa própria, sem alterar significado de measured/global.
