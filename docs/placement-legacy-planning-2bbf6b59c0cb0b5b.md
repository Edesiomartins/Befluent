# Compatibilidade de planejamento legado — backend

ID2bbf6b59c0cb0b5b ·08/10/2026 · local, sem frontend/commit/push/deploy/produção.

Bug confirmado: `_result_payload` tratava `planning_decision(result)` (proposta recalculada) como planejamento aplicado quando o resultado não tinha planning persistido. O snapshot de resultados novos era correto, mas a projeção legado podia apresentar A1 mesmo com B2 aplicado no perfil. Cinco regressões falharam antes da correção.

## Regra de leitura corrigida

- Resultado v2 com planejamento persistido: não alterar os campos existentes nem seguir mutações do perfil.
- Resultado sem planejamento: reconstruir somente a proposta isolada da avaliação, publicada em `assessment_proposed_level` e também no trace.
- Se o perfil da mesma conta/idioma contém planning_level válido: devolver esse planejamento operacional vigente; source=`legacy_current_profile`, action=`retained_prior_planning`, resolution=`current_profile`. Trace conserva profile_id, last_assessment_id e origem do planning do perfil. `historical_application_known=false`: não afirmar que esse era o planejamento aplicado na época do teste.
- Sem planning vigente válido: planning_level=null, source/action=`legacy_planning_unknown`. Mesmo um current_level anterior qualificado não autoriza inventar uma decisão de planejamento aplicada que nunca foi persistida.
- Essa abordagem usa a opção explícita autorizada de planejamento vigente com provenance, inclusive quando não há global qualificado. Não é reexecução nem aplicação da policy durante GET: nada se grava. Perfil vigente pode mudar depois; o legado sem snapshot acompanha esse estado por definição e identifica essa origem. Repetir GET em estado inalterado é determinístico.
- Overall legado continua passando pela qualificação de evidência já existente; o nível global antigo salvo não vira medido. Nenhuma migração/backfill/recomplete/reparo histórico.

Exemplo: planning vigente B2 e assessment reconstruído propõe A1 -> applied planning_level=B2, source=legacy_current_profile, assessment_proposed_level=A1, trace.action=retained_prior_planning e historical_application_known=false. Sem perfil/planning conhecido -> planning null, proposta ainda explícita.

## Caminhos

- `backend/app/services/placement_planning.py`: helper puro `legacy_planning_projection`, que separa proposta da resolução operacional com provenance.
- `backend/app/api/placement_tests.py`: adapter consulta UserLanguage apenas para a mesma conta/idioma quando o resultado não contém planning; mantém snapshot persistido de v2 intacto.
- `backend/tests/test_legacy_placement_planning.py`: integração HTTP e observação de SQL para assegurar GET read-only.

## Validação

Cobertura: v1 reconstruído de respostas, v2 antigo sem planning, ausência de planejamento, planning vigente B2/proposta A1, perfil com global anterior qualificado, global anterior sem planning aplicado conhecido, overall parcial não promovido, snapshot v2 intacto, GET sem escrita, repetição determinística e coerência do valor com fallback de perfil.

Rodada final:35 passed em27,37s (legado, planning, integração partial, complete e auditoria). Diff-check e compileall passaram. SQL observada em GET v1/v2 sem INSERT/UPDATE/DELETE; dados persistidos inalterados, repeat GET estável. Ensaios locais SQLite/TestClient; produção e PostgreSQL não certificados. Próximo passo de integração: apresentar provenance legacy_current_profile/legacy_planning_unknown de forma explícita ao consumidor; nenhum frontend foi modificado.
