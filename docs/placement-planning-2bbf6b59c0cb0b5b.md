# Planejamento operacional do placement parcial — backend

ID: 2bbf6b59c0cb0b5b. Implementação local em 08/10/2026; frontend intocado, sem commit/push/deploy ou produção.

## Auditoria antes da mudança

- `placement_tests._apply_to_profile`: copiava o menor nível objetivo estimated para `UserLanguage.planning_level`, apenas se o campo ainda estivesse vazio. Ignorava produção provisional e desempenho sem faixa. Motivo/trace ausentes; result_json/API do teste não expunham decisão de planejamento.
- Persistência existente: `UserLanguage.planning_level`, `planning_level_source`, `assessment_summary_json` (migration0017). Resultado em `PlacementTest.result_json`. Não há tabela de resultado separada.
- Leituras: languages/mine, language-profiles, dashboard, progress, learner_context e início de sessão em lessons. Projeções mostravam apenas o valor, sem motivo/origem detalhada.
- `learner_context`: cadeia current_level -> planning_level -> level_estimate -> default com origem herdada do perfil; prompt chamava a faixa de CEFR do aluno. Isso podia usar um placement antigo sem cobertura como medido, ou apresentar planejamento como autodeclaração.
- `curriculum_generator`: entrada pela mediana de skills; `ensure_active_curriculum` podia hidratar skills vazias e current_level a partir de nível único. `generate_curriculum` bloqueava placement parcial; `complete` só criava currículo se diagnostic_status=ready.
- `progression.apply_checkpoint_outcome`: não promove CEFR nem reescreve semanas; preservado. Learning plans antigos são deprecated e não calculam nível; Journey usa currículo/atividades.

## Regra adotada

Policy versionada `placement-planning-v1` em `services/placement_planning.py`:

1. Overall sufficient válido: entrada operacional igual ao overall, source=sufficient_overall. Não muda a regra de qualificação global.
2. Perfil parcial: somente evidências válidas/independentes já qualificadas pelo backend. Nível estimated ou provisional pode apoiar entrada A1 se >=A1. Níveis mais altos ficam limitados ao teto operacional A1 nesta policy.
3. Insufficient_evidence objetivo pode apoiar entrada A1 somente com >=4 itens independentes e desempenho elegível >=75%; não ganha estimated_level, status measured ou elegibilidade global. Score bruto contendo reuso não serve para esse apoio. Produção heurística/unavailable não vira desempenho objetivo.
4. Exigir apoio de pelo menos duas competências distintas para entrada A1; do contrário PRE_A1. Mediana inferior dos níveis disponíveis, candidato, teto, sinais incluídos/excluídos e corroboradores ficam no trace. O requisito de duas competências prevalece sobre um nível alto isolado.
5. Sem evidência: PRE_A1 é faixa operacional de acolhimento, não diagnóstico de iniciante comprovado. Não preencher competências desconhecidas. Itens reutilizados não podem sustentar decisão.

São limiares operacionais, não probabilidades ou validação psicométrica. Teto A1 é conservador e pode subestimar a melhor atividade inicial de um aluno avançado sem global válido; nova policy poderá revisar esse teto após observação de uso.

Caso francês: VG PRE_A1 5/8 permanece medido apenas nessa skill; R/L 4/4 permanecem insufficient. Writing B1 e speaking A1 permanecem provisional. R/L são sinais de desempenho, W/S sinais linguísticos de planejamento. Apoio em quatro competências permite A1; overall continua null, profile partial. Nenhum hardcode de idioma, usuário ou combinação exata.

## Persistência, compatibilidade e Journey

- Result_json registra planning_level/source/reason/trace; UserLanguage guarda level/source existentes e reason/trace em assessment_summary_json.planning. Sem coluna nova ou migration.
- Partial atualiza planejamento quando não há nível global vigente qualificado. Global anterior válido permanece em current_level/level_estimate, origem e vinculação anteriores. Planejamento anterior existente é preservado nesse caso; se vazio, recebe o global anterior com source=prior_global. Checkpoint não substitui global nem planejamento de global vigente.
- Resultado expõe o planejamento efetivamente aplicado. Se a proposta isolada do assessment seria A1 mas uma entrada anterior B2 é mantida, retorna B2 e trace.action=retained_prior_planning; assessment_proposed_level registra A1. A decisão aplicada também é persistida antes do commit para repetir complete sem alteração.
- Skills persistidas só recebem status estimated real; provisional e insufficient continuam no resumo do assessment, não viram colunas medidas. Hidratação de skills é bloqueada para parcial, inclusive se algum outro fluxo chamar o helper.
- Complete parcial cria currículo operacional com generated_from=planning e entry_level=planning_level. Blocos usam a faixa operacional sem preencher skills no perfil. Plano-meta é organização pedagógica, não promoção global garantida.
- Currículo ativo anterior é reaproveitado, preservando trabalho; novo planning_level não regenera automaticamente jornadas já criadas. Mudança de entry_level de plano existente é operação separada.
- Contexto escolhe global qualificado antes de planning. Legado level_estimate sem current/assessment/plan só conserva autodeclaração operacional com source=legacy_declared, nunca vira global medido. Prompts identificam planning explicitamente.
- Repeat complete retorna resultado persistido, sem recalcular ou regravar planejamento. Resultado legado sem esses campos ganha projeção de leitura da decisão, sem backfill em banco. Histórico apagado não é reconstruído.

## Contrato

Placement result: overall_level, overall_estimate_status, profile_status, planning_level, planning_level_source, planning_level_reason, planning_level_trace; skills com status, estimated_level, score, max_score, accuracy/evidence_counts quando disponíveis. Scores objetivos são desempenho observado; não converter score em CEFR quando insufficient.

Perfis/languages/dashboard/progress: planning e último assessment explícitos; current_level continua a projeção qualificada do global vigente. assessment_skills conserva último teste separadamente de colunas históricas. Language-profiles.skills acrescenta status/score/evidência atual sem fabricar níveis.

Currículo: generated_from=planning persistido; entry_level_source=planning; entry_is_measured_global=false. Outros currículos mantêm provenance histórica, sem afirmar retroativamente que sua origem prova um global suficiente.

## Validação e limites

Regressões novas começaram com6 falhas: serviço/contrato ausente, parcial sem Journey e origem pending no contexto. Novos casos depois passaram: francês, overall null/planning válido, suficiente, produção provisional, R/L insufficient, ausência/reuso excluído, skills vazias, Journey, complete idempotente, global/checkpoint preservados, prompt e hidratação protegidos. Duas expectativas antigas de currículo null foram atualizadas para planning. Fixtures de global medido passaram a declarar coverage suficiente; autodeclaração antiga foi mantida como tal.

Validação:258 testes placement/currículo/atividades passaram;192 testes contexto/interesses/língua nativa/progresso passaram (4 avisos Alembic);16 testes finais planning/complete passaram após a correção de retenção aplicada. API/planning final:46 passed,1 skipped (PostgreSQL sem banco dedicado). Últimos9 cenários planning passaram após excluir competências não reconhecidas. Diff-check e compileall passaram. As rodadas têm interseção; não somar como total de testes únicos. PostgreSQL/concorrência real não executados; produção não consultada. A validação focal não certifica toda a suíte backend. Integração visual/UX fica com o responsável pelo frontend; este trabalho só prepara o contrato. Alterações paralelas de frontend apareceram no checkout e foram preservadas sem intervenção desta tarefa.

Próximos passos: responsável do frontend consumir source/reason/status e distinguir entrada operacional de global; ensaiar concorrência em PG dedicado; validar editorialmente/observar dificuldade da primeira Journey antes de revisar limites da policy. Deploy/migrations/dados de produção exigem autorização separada; nada publicado aqui.
