# Placement: cobertura e resultado — proposta de arquitetura

Data: 08/10/2026. ID: `2bbf6b59c0cb0b5b`. Status: proposta para revisão; implementação NÃO autorizada nesta tarefa.

## Avaliação

O placement atual é arriscado como classificação global: a cobertura insuficiente é excluída do cálculo e os pesos restantes são renormalizados. A correção precisa começar pelo significado do resultado, antes de alterar pesos ou aumentar o target.

Pontos fortes: estado adaptativo por skill, evidência persistida, entrega controlada, níveis nullable, conclusão transacional/idempotente e distinção existente entre heurística e IA na avaliação escrita.

## Escopo e evidência

- Código local inspecionado: engine, endpoints, seed, delivery, writing_evaluation, modelos, dashboard, curriculum_generator, progression, progress/language_progress, tipos e telas de placement.
- Banco editorial versionado: TODOS os oito fixtures de `backend/app/data/placement_items/*.json`, agrupados por idioma/skill/CEFR/item_type. Total: 144 itens.
- Incidente real: relatório `docs/placement-result-audit-2bbf6b59c0cb0b5b.md`, baseado em exportação PostgreSQL read-only de 07/10/2026. Não consultei novamente produção nesta tarefa.
- A matriz abaixo é do catálogo versionado, NÃO um inventário live de todos os registros de produção. Itens importados podem coexistir com o seed; o seed não os desativa. A validação live do inventário por idioma permanece uma etapa necessária antes de rollout.
- Critérios propostos são regras operacionais, não validação psicométrica. Quantidade, aprovação editorial e score de IA não certificam validade CEFR.

## 1. Arquitetura atual e propagação

1. `placement_tests._records` transforma respostas objetivas com score em AnswerRecord; exclui writing/speaking.
2. `placement_engine.estimate_skill_level`: mínimo quatro respostas na skill; escolhe a maior faixa com pelo menos duas respostas e média >=0.65. Não exige consistência com faixas inferiores.
3. `skill_results` omite skills sem nível, perdendo no resumo contagens/acurácia dessas skills, embora as respostas permaneçam no banco.
4. `overall_level` aceita qualquer conjunto não vazio. `effective_weights` aplica perfis explícitos ou renormaliza os pesos presentes. Listening/speaking limitam o teto apenas se presentes; nenhuma delas é obrigatória.
5. `build_result` escreve overall, scores, skills e pesos em um dict. `_add_diagnostic_contract` define ready SOMENTE por overall não nulo.
6. `complete_test` persiste o dict em PlacementTest.result_json e duplica overall/confidence em colunas. Sections materializam skills; ausentes recebem 0/0. Writing é sobrescrita com nível null/calibrating mesmo quando a avaliação é IA.
7. `_apply_to_profile` copia overall para UserLanguage.current_level/level_estimate, níveis por skill, confidence e diagnostic_completed. Pode apagar nível anterior ao receber novo resultado sem overall.
8. Placement ready chama `ensure_active_curriculum` para 90 dias na mesma transação. Currículo usa mediana dos níveis por skill como entrada, não diretamente overall. `diagnostic_completed` libera geração PLACEMENT; basta haver uma skill para calcular mediana. Fallback/hydrate pode preencher skills vazias a partir do nível global/autodeclarado.
9. `_result_payload` usa overall da coluna e skills das sections, mas metadados de result_json: existem três representações que precisam manter o mesmo significado.
10. Dashboard usa current_level e considera placement necessário se nível null/origem pending. Progress/mastery e language_progress também usam current_level. Frontend usa diagnostic_status para título e currículo e exibe confidence em /100.
11. Checkpoints usam o mesmo complete/_apply_to_profile. `apply_checkpoint_outcome` não promove semanas do currículo, mas o perfil já foi atualizado antes: a nova política deve impedir que uma amostra curta substitua nível global ou apague avaliação anterior suficiente.

### Dependência obrigatória versus pressuposto

Não há obrigação estrutural de overall não nulo: PlacementTest.overall_level e UserLanguage.current_level/level_estimate são nullable; tipos frontend já aceitam null. A obrigação é semântica nos gates ready/diagnostic_completed, no dashboard, nos consumidores de current_level e no fallback curricular. Currículo precisa de ponto de entrada para planejar, mas esse ponto não precisa representar um CEFR global demonstrado.

## 2. Selector atual e falhas

- Começa A2 ou PRE_A1 quando iniciante declarado; estado isolado por skill.
- Três acertos consecutivos promovem; dois erros rebaixam. A streak não verifica que as respostas vieram da faixa corrente: fallback entre faixas pode mover a adaptação indevidamente.
- `next_skill` prioriza skills abaixo de quatro respostas, depois menor contagem, com desempate VG/reading/listening. É uma quota branda de volume, não uma garantia de cobertura decisória.
- `_pick_objective_item` tenta a faixa corrente da skill preferida, depois de outras skills; somente depois tenta quaisquer faixas na ordem PRE_A1,A1,A2,B1,B2. Pode trocar a skill deficitária por outra só porque esta tem item na faixa corrente. Não há ordenação explícita de itens na consulta.
- Filtros: idioma, approved, active e não respondido. Não usa difficulty/discrimination para seleção. Não filtra explicitamente tipo compatível, nem faixa testável na primeira passagem.
- `should_stop`: máximo 30; abaixo de 12 não para; a partir de 20 pode parar se houver quatro respostas na faixa corrente, SOMANDO skills. Não verifica evidência suficiente em cada skill nem a suposta consistência descrita no comentário.
- Sem item: passa para writing/conclusão mesmo sem cobertura. Progress continua target=20. Complete recusa menos de 12 objetivos, podendo criar um impasse se o catálogo elegível se esgotar antes disso.
- Writing é escolhida na faixa corrente global temporária, dependente da última skill objetiva, depois A2/A1. Não usa estimativa de escrita nem uma política própria de tarefa.

## 3. Matriz de cobertura

Cada linha agrega uma única combinação skill/item_type. Zero significa ausência no fixture; total inclui itens fora das faixas testáveis.

| Idioma | Skill | item_type | PRE_A1 | A1 | A2 | B1 | B2 | C1 | C2 | Total |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| en | vocabulary_grammar | multiple_choice | 2 | 0 | 2 | 2 | 2 | 0 | 0 | 8 |
| en | reading | reading_comprehension | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 4 |
| en | listening | listening_comprehension | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 4 |
| en | writing | short_writing | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 4 |
| es-ES | vocabulary_grammar | multiple_choice | 2 | 0 | 2 | 2 | 2 | 0 | 0 | 8 |
| es-ES | reading | reading_comprehension | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 4 |
| es-ES | listening | listening_comprehension | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 4 |
| es-ES | writing | short_writing | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 4 |
| fr | vocabulary_grammar | multiple_choice | 2 | 0 | 2 | 2 | 2 | 0 | 0 | 8 |
| fr | reading | reading_comprehension | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 4 |
| fr | listening | listening_comprehension | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 4 |
| fr | writing | short_writing | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 4 |
| it | vocabulary_grammar | multiple_choice | 2 | 0 | 2 | 1 | 1 | 0 | 0 | 6 |
| it | reading | reading_comprehension | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 3 |
| it | listening | listening_comprehension | 0 | 1 | 1 | 0 | 1 | 0 | 0 | 3 |
| de | vocabulary_grammar | multiple_choice | 2 | 0 | 2 | 1 | 1 | 0 | 0 | 6 |
| de | reading | reading_comprehension | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 3 |
| de | listening | listening_comprehension | 0 | 1 | 1 | 0 | 1 | 0 | 0 | 3 |
| ja | vocabulary_grammar | multiple_choice | 2 | 0 | 2 | 2 | 2 | 0 | 0 | 8 |
| ja | reading | reading_comprehension | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 4 |
| ja | listening | listening_comprehension | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 4 |
| ja | writing | short_writing | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 4 |
| zh-CN | vocabulary_grammar | multiple_choice | 2 | 0 | 2 | 2 | 2 | 0 | 0 | 8 |
| zh-CN | reading | reading_comprehension | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 4 |
| zh-CN | listening | listening_comprehension | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 4 |
| zh-CN | writing | short_writing | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 4 |
| la | vocabulary_grammar | multiple_choice | 2 | 1 | 2 | 2 | 2 | 0 | 0 | 9 |
| la | reading | reading_comprehension | 0 | 1 | 1 | 1 | 1 | 1 | 0 | 5 |
| la | listening | listening_comprehension | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 4 |
| la | writing | short_answer | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 1 |
| la | speaking | short_answer | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 |

Speaking ausente em en/es-ES/fr/it/de/ja/zh-CN; writing ausente em it/de. Essas combinações são zero em TODAS as faixas.

| Idiomas | Itens totais/idioma | Objetivos nas faixas testáveis | Writing válida para avaliação extensa |
|---|---:|---:|---|
| en, es-ES, fr, ja, zh-CN | 20 | 16 | 4 tarefas cadastradas, ainda exigem validação editorial |
| it, de | 12 | 12 | nenhuma |
| la | 20 | 17 | nenhuma comprovada; 1 fórmula curta B1 |

Latim tem 18 objetivos contando C1; C1 não aparece no fallback TESTABLE_LEVELS. Seu item de fala não é selecionado no fluxo objetivo e speaking permanece 501. `short_answer` não pertence a ItemType. A tarefa writing pede apenas “Deo gratias”: sua existência não sustenta rubrica de produção extensa B1.

### Incapacidade atual

Todos os oito idiomas são incapazes de estimar reading/listening pelos critérios atuais com esse catálogo: nenhuma faixa tem dois itens. It/de também falham no mínimo quatro por skill, não possuem writing e não sustentam VG B1/B2 por terem um item nessas faixas. VG A1 não é estimável em nenhum dos oito (zero itens ou um no latim). Nenhum idioma atinge target 20 objetivos nas faixas testáveis. Isso não significa que todos sejam incapazes de concluir hoje: a regra atual aceita 12 objetivos e pode gerar overall apenas de VG.

Inventário live futuro: agrupar `placement_items` por language_code, skill, cefr_level, item_type com COUNT(*), separando total, active/approved e elegíveis conforme modalidade/faixa. Auditar também sources, versões, tipos incompatíveis, clones e disponibilidade de estímulo. Não confundir catálogo seed com base live.

## 4. Alternativas e recomendação

1. RECOMENDADA: perfil por skill primeiro; overall global só com as cinco skills. Sem speaking, placement pode terminar, orientar estudo e ter cobertura suficiente do escopo disponível, mas permanece perfil parcial do idioma.
2. Síntese das quatro skills disponíveis: defensável como resumo com escopo explícito, mas usar campo distinto (`scoped_estimate`) e rótulo “estimativa das competências avaliadas”; não reutilizar overall_level nem copiar automaticamente para current_level global.
3. Relaxar mínimos ou aumentar pesos de VG: rejeitada. Não resolve ausência de evidência e mantém a aparência de nível global.

Consequência deliberada da recomendação: overall_level ficará null para novos placements enquanto speaking estiver indisponível. Isso exige ajustar a jornada de estudo; não autoriza bloquear aprendizagem até implementar fala.

## 5. Contrato proposto (v2)

Fonte única: um builder monta resultado canônico com TODAS as cinco skills. Sections e perfil são projeções desse resultado; nenhum override de writing após o builder. Persistir policy_version, result_schema_version, banco/revisões usados e motivo de parada.

```json
{
  "result_schema_version": 2,
  "policy_version": "placement-coverage-v2",
  "status": "completed",
  "profile_status": "partial",
  "overall_estimate_status": "partial",
  "overall_level": null,
  "overall": null,
  "weights_used": {},
  "assessment_coverage": {
    "required_for_overall": ["vocabulary_grammar", "reading", "listening", "writing", "speaking"],
    "supported_skills": ["vocabulary_grammar", "reading", "listening", "writing"],
    "sufficient_skills": ["vocabulary_grammar"],
    "missing_skills": ["reading", "listening", "writing", "speaking"],
    "supported_scope_status": "insufficient",
    "stop_reason": "bank_exhausted",
    "objective_answered": 16,
    "production_tasks_submitted": 1,
    "bank_feasibility": "insufficient"
  },
  "skills": [
    {
      "skill": "reading",
      "status": "insufficient_evidence",
      "estimated_level": null,
      "score": 4,
      "max_score": 4,
      "evidence_counts": {
        "answered": 4, "valid": 4, "excluded": 0,
        "by_cefr": {"A1": 1, "A2": 1, "B1": 1, "B2": 1},
        "deciding_band": null, "at_deciding_band": 0
      },
      "skill_confidence": {
        "basis": "rule_based_evidence", "label": "insufficient",
        "reasons": ["no_band_with_two_items"]
      },
      "eligible_for_overall": false
    }
  ]
}
```

Exemplo abreviado com uma skill; resposta real sempre contém cinco. Writing histórica do incidente integra sufficient_skills somente se cumprir a política de validade; o payload antigo tem rubrica incompleta, portanto não deve ser promovido automaticamente.

Estados por skill: `not_collected`, `unavailable`, `insufficient_evidence`, `provisional`, `estimated`. `status=completed` significa sessão encerrada, nunca avaliação suficiente. `profile_status=complete` exige todas cinco skills estimadas; caso contrário partial. `overall_estimate_status=sufficient` exige os gates de overall abaixo. `supported_scope_status` permite dizer que a coleta do escopo disponível foi suficiente sem declarar perfil global completo.

Evidência inclui itens/tarefas distintos, válidos/excluídos e motivos, contagem/acurácia por faixa, origem da modalidade e avaliação. Acerto não é sinônimo de evidência: resposta errada válida também informa. Score ausente permanece null no contrato v2; não transformar falta de medida em zero. Speaking unavailable tem estimated_level/score/max_score null, counts zero e reason `assessment_not_available`; não é fraqueza nem falha do aluno.

## 6. Regra explícita de overall e perfil parcial

Overall pode existir APENAS quando:

1. Todas cinco skills têm status estimated e eligible_for_overall=true na mesma avaliação/política.
2. VG/reading/listening cumprem mínimo quatro itens independentes válidos por skill, pelo menos dois na faixa decisória, acurácia >=0.65 nessa faixa e ausência de conflito não resolvido que impeça decisão. Esses valores preservam o piso atual; não representam precisão validada.
3. Writing possui avaliação linguística válida por rubrica versionada de amostra adequada; speaking deverá cumprir futura política própria antes de integrar o cálculo. Não presumir que STT sozinho avalia fala.
4. Nenhuma indisponibilidade, falta de estímulo ou fallback heurístico é contado como skill estimada; faixa emitida pertence ao alcance validado daquela skill.

Mesmo com cobertura suficiente, desempenho pode não sustentar faixa: não forçar PRE_A1 quando todas respostas forem erradas. Registrar insuficiência de decisão, limite inferior/alcance da tarefa e orientação de calibração. Conflito como A2 0/2 e B1 2/2 solicita confirmação; não descartar acertos nem exigir perfeição nas faixas inferiores.

Após gates, proposta conservadora de síntese: menor nível entre as cinco skills, com `aggregation_method=minimum_supported_skill`, sem pesos renormalizados. É uma escolha pedagógica conservadora, não um escalar CEFR validado; o perfil completo deve continuar visível. Média ponderada ordinal atual pode ser mantida apenas como alternativa futura explicitamente discutida; não tratar distância entre faixas como medida validada. No v2 recomendado weights_used={} mesmo quando suficiente, pois não há média ponderada.

Perfil parcial conserva todos os scores reais e estimativas locais válidas, inclusive writing provisória, com proveniência e limitações. Não gera overall de subset. Não usa prioridade “abaixo do geral” se overall null. Falta de banco vira déficit editorial; falta de coleta vira próxima avaliação; desempenho sustentado orienta prática. Não trocar déficit editorial por promessa de que prática livre resolverá automaticamente o placement.

## 7. Selector com adaptação e cobertura

Separar três decisões: viabilidade do banco, próxima evidência e critério de encerramento. Política compartilhada entre selector/scorer/complete; parâmetros versionados no início da sessão.

1. Preflight: candidatos active/approved, tipo compatível, skill/modality, faixa permitida, estímulo disponível. Calcular capacidade por skill/faixa e duplicatas semânticas. Se impossível, informar modo parcial e déficits antes de começar; jamais reduzir silenciosamente critérios.
2. Quota mínima rígida: reservar orçamento para quatro objetivos por cada uma das três skills (piso 12). Satisfazer primeiro déficit de volume válido; desempatar por déficit normalizado e capacidade restante, deterministicamente.
3. Depois, priorizar skills sem faixa decisória sustentada e conflitos pendentes. Selecionar a skill deficitária ANTES de tentar adaptar faixa. Preferir sua faixa candidata, itens confirmatórios nela e então vizinhas por distância; não ceder a outra skill apenas porque tem item na faixa corrente.
4. Separar exploration/confirmation: streak de exploração só usa respostas da faixa explorada. Movimentar faixa não encerra a necessidade de confirmar a candidata com dois itens. Em conflito, usar próximo item independente na faixa conflitante, dentro do orçamento.
5. Fallback somente entre faixas permitidas da mesma skill quando útil e explicitado; esgotamento marca déficit, não inventa evidência. Não repetir item/gabarito revelado nem contar clones como evidências independentes. Persistir motivo da escolha, desempate/revisão e item selecionado; retomar entrega aberta idempotentemente.
6. Encerrar por cobertura decisória do escopo disponível e confirmação concluída, limite máximo (30), esgotamento ou interrupção. Meta 20 passa a preferência de orçamento, não promessa fixa. Expor target planejado alcançável e capacidade/razão; meta alcançável não equivale a suficiente.
7. Permitir encerramento parcial abaixo de 12 quando banco esgotou/interrupção explícita; completion não deve exigir uma quantidade impossível. Nenhum global nesse caso. Retomada/complemento não deve ser bloqueado pelo cooldown de 30 dias reservado a reavaliação completa; novo suplemento deve ter ligação/revisão própria, sem reescrever snapshot concluído.
8. Writing usa sua própria política de tarefa. Não derivar nível-alvo da última skill respondida. Pode usar faixa candidata das evidências objetivas para escolher tarefa, identificando esse vínculo como planejamento, não nível de escrita comprovado.

Cobertura mínima é uma garantia de amostragem quando o banco permite; não é garantia de acertos ou de classificação. Para sustentar todas PRE_A1..B2 por cada skill objetiva, piso editorial proposto: quatro itens independentes por skill/faixa (3 para exploração + reserva de confirmação), portanto 60 objetivos/idioma. Não é requisito psicométrico; é margem operacional. Pelo menos duas tarefas extensas por faixa suportada de writing como alternativas editoriais; uma tarefa válida pode produzir estimativa provisória, não precisão elevada. C1/C2 continuam indisponíveis até banco e política próprios; latim exige validação de adequação do mapeamento CEFR ao propósito eclesiástico.

## 8. Writing: preservar sem certificar

Fluxo atual: evaluate_writing -> _ai_evaluation/_validate_ai_payload -> feedback_json da resposta -> complete. O provider retorna modelo, mas `_model` é descartado; estimated_level inválido é inferido do score e nível acima do alvo é limitado. Criteria pode ficar vazio/incompleto e scores não são integralmente validados.

Proposta:

- Preservar sempre avaliação recebida, score, feedback e nível aceito no histórico. Distinguir `reported_level`, `accepted_level`, `level_origin=model_reported|score_derived` e eventual teto da tarefa. Nunca elevar para B2 com base no elogio textual.
- Proveniência: provider/model reais, fallback usado, versão do prompt/rubrica/validator, item/revisão, idioma, timestamp, truncamento e limites da amostra. Modelo antigo desconhecido deve ser null, nunca inferido pela configuração atual.
- Validar números finitos (recusar bool/NaN/infinito), critérios obrigatórios e limites, idioma/aderência ao tema, amostra mínima adequada ao idioma, contrato de faixa e política de validação. Texto fornecido deve ser tratado como entrada, não instrução para avaliador.
- IA válida: preservar accepted_level como estimativa provisória da skill e exibir “Escrita: B1 — avaliação por IA de uma amostra”. Confiança qualitativa `provisional`, nunca 0.96 como probabilidade de CEFR.
- Para eligible_for_overall, exigir rubrica linguística completa e política de evaluator/tarefa aprovada, com limitações documentadas e validação humana representativa antes de liberar essa elegibilidade. Uma segunda amostra pode confirmar conflitos; não duplicar chamadas como substituto de validação.
- Heurística: feedback preliminar; score/metrics disponíveis, estimated_level CEFR público null e eligible_for_overall=false. Não equiparar volume/diversidade a gramática ou CEFR.
- Payload IA inválido: manter razão e avaliação original apropriada para auditoria; fallback identificado. Não converter score em CEFR e atribuí-lo silenciosamente ao modelo.
- Incidente: preservar B1/0.96 e três critérios existentes como provisórios com `incomplete_rubric`/proveniência incompleta; não afirmar que a avaliação é integralmente válida só porque status era assessed. Não reavaliar texto por IA sem autorização pertinente.
- Latim “Deo gratias” não conta como amostra extensa B1; precisa recategorização editorial futura, preservando histórico.

## 9. confidence_score atual e substituto

| Componente | Fórmula atual | O que mede/limitação |
|---|---|---|
| Base | 40 | constante arbitrária, não evidência |
| Volume | +25 se >=20; +15 se >=12; +5 abaixo | quantidade total, ignora concentração por faixa/skill |
| Abrangência | +4 por skill com nível, máximo cinco | número de estimativas emitidas, não todas as skills coletadas |
| Dispersão | -5 por diferença de índices máximo-mínimo | heterogeneidade do perfil; não prova baixa qualidade de medição |
| Rapidez | -20 × min(rapidas/total,0.5), rápida <1500 ms | proxy de comportamento; tempo null evita penalidade, não comprova cuidado |
| Essenciais ausentes | -7 por listening/speaking ausente | incompletude, sem impedir overall |
| Saída | saturação 0..100; 1 decimal | pontos heurísticos, não probabilidade/intervalo de confiança |
| Rótulo | >=70 alta; >=45 moderada; restante baixa | cortes arbitrários |

Incidente: 40+15+4-0-0-14=45. Com apenas VG, spread=0: parece consistente justamente por não haver outras estimativas para comparar. `_add_diagnostic_contract` apaga confidence só quando overall null; Section.confidence_score existe, mas não recebe cálculo por skill no complete.

Recomendação: retirar /100 da apresentação nova. Substituir por `evidence_support` e `skill_confidence` qualitativa (insufficient/provisional/supported), com `basis`, contagens e razões. Supported significa que regras operacionais foram satisfeitas, não “alta probabilidade”. Se precisar manter índice legado, denominá-lo `legacy_evidence_support_index`, mostrar componentes e marcar heuristic; não aplicar cortes antigos aos novos estados. Não calcular probabilidades, SEM/intervalos ou IRT com difficulty/discrimination cadastrados sem calibração.

## 10. Frontend, currículo e perfil

- Tela de resultado: “Perfil parcial de competências”; cards para cada skill com score real, evidência, faixa local e origem. Distinguir unavailable de coletada sem faixa. Writing provisória não deve desaparecer em “calibrando”.
- Progresso: substituir 16/20 prometido por orçamento planejado e cobertura por skill; explicar esgotamento como limitação do teste.
- Não mostrar nível global, descrição de fluência/conversa ou confiança percentual quando parcial. Speaking unavailable não deve figurar como “ponto fraco”.
- Dashboard/progresso/onboarding: separar último assessment, cobertura e origem de nível vigente. `needs_placement_test` não pode gerar ciclo infinito para banco incapaz; oferecer complementar quando houver capacidade e prática quando não houver.
- Separar `planning_level` de current_level global. Prática/entrada do currículo pode usar níveis locais válidos ou nível autodeclarado com origem explícita; não hidratar skills desconhecidas como avaliadas. Fallback de planejamento nunca escreve CEFR medido.
- Perfil novo parcial: current_level null; persistir níveis locais com seus estados/proveniência. Perfil com avaliação anterior suficiente: reteste parcial não apaga current_level/skill evidence anterior; registrar último teste separadamente e indicar data da avaliação vigente. Não misturar amostras históricas para fabricar resultado completo sem política longitudinal própria.
- Primeira etapa conserva currículos ativos. Sem geração PLACEMENT de 90 dias a partir de partial. Para usuário novo, manter entrada em prática/calibração existente; se precisar de plano curto dedicado, definir contrato próprio em etapa separada. Completar placement parcial deve funcionar mesmo sem currículo.
- Checkpoints: atualizar observações locais/prioridades; não alterar nível global vigente nem origem desse nível por uma amostra parcial. Gates de resultado e de planejamento são separados.
- Mudanças frontend devem ser coordenadas com responsável atual; este documento não altera sua implementação.

## 11. Migrations e compatibilidade

Primeira entrega pode usar result_json/feedback_json existentes com schema_version/policy_version; overall/estimated_level já nullable. Não é necessária migration só para adicionar campos ao JSON ou permitir overall null.

Evolução recomendada em migration ADITIVA: UserLanguage.last_assessment_id (FK nullable), assessment_summary_json (cobertura/estados/proveniência das skills/versão), planning_level e planning_level_source nullable. `placement_test_id` permanece referência da avaliação vigente que sustenta o global; last_assessment_id registra o teste parcial mais recente. Sections podem ganhar evidence_json nullable se precisarem ser consultadas isoladamente; evitar duplicar canônico sem necessidade. Não renomear/remover colunas de confidence nesta fase, nem relaxar constraints de unicidade.

Compatibilidade de leitura:

- Campos v1 permanecem com formas existentes; adapter traduz estimated->assessed, insufficient/provisional->calibrating, unavailable->not_available para clientes antigos. O v2 é canônico e contém detalhamento adicional, publicado com negociação de versão/rollout coordenado.
- Para v2, diagnostic_status legado ready somente se overall suficiente; demais calibrating. Não usar ready para liberar estudo parcial: criar gate próprio.
- Resultado antigo sem coverage não é automaticamente suficiente. Se respostas preservadas permitem reconstrução, calcular view v2 auditável com origem `legacy_reconstructed`; não alterar result_json/histórico no GET.
- Quando não houver evidência reconstruível: partial e razão `legacy_coverage_unknown`; manter nível histórico acessível como legacy_overall_level, sem vendê-lo como revalidado.
- Colunas antigas e currículos existentes são preservados até revisão de dados autorizada. O leitor v2 suprime afirmação global sem sustentação; telas antigas precisam atualização coordenada para impedir que o valor legado continue sendo apresentado como validado.
- Qualquer saneamento de perfis antigos é operação separada: inventário, dry-run, backup/rollback e aprovação explícita de produção. Não fazer backfill global silencioso, não recalcular IA em GET, não apagar sessões/cronogramas.
- Backend aditivo antes do frontend; ativar v2 após leitores/gates prontos. Deploy e produção exigem confirmação do proprietário.

## 12. Plano de implementação por etapas (não executado)

1. **Inventário e contrato:** relatório read-only live por todas combinações, policy/schema v2, fixtures de regressão do caso francês e contratos consumidores. Validar totais e diferença catálogo/live; sem writes de produção.
2. **Resultado canônico e gates:** coverage por skill, manutenção de scores sem CEFR, overall strict, motivos partial, projections consistentes. Testes unitários/API primeiro; manter atomicidade, autoflush=False e idempotência atuais.
3. **Writing:** preservar feedback/nível/proveniência, distinguir heurística/IA incompleta/IA aceita, validar payload e expor provisório; não escolher provider novo. Testes determinísticos com provider simulado, sem chamadas reais.
4. **Perfil e compatibilidade:** migration aditiva se aprovada, separar último assessment/nível vigente/planejamento, adapter legado e checkpoints; testar migração vazia e banco legado e rollback transacional.
5. **Frontend e jornada:** cards/status/progress/cooldown complemento, dashboard e entrada em prática parcial; implementar de forma coordenada com proprietário frontend. Validar todos fluxos com overall null antes de ativar política.
6. **Selector:** preflight, orçamento reservado, confirmação por skill/faixa, fallback próximo e stop por cobertura/esgotamento; simulações determinísticas por idioma/perfil e retomada.
7. **Banco editorial:** ampliar itens independentes e tarefas extensas; revisar níveis/tipos/áudio, inclusive latim. Conteúdo é seed versionado, não migration estrutural. Lançar capability por idioma apenas após critérios verificáveis.
8. **Rollout:** ensaio PostgreSQL, avaliação amostral humana, monitoramento de partial/stop_reason/deficits/IA fallback por idioma. Atualizar dados antigos somente em operação autorizada; backend antes frontend, deploy autorizado separadamente.

Nenhuma etapa contém commit/push/merge/deploy automático.

## 13. Testes necessários e critérios de aceite

- Caso francês: VG B1 preservado como local; reading 4/4 e listening 3/4 preservados com déficit de faixa; writing B1/0.96 provisória; speaking unavailable; overall null, weights {}, partial.
- Uma ou duas skills suficientes nunca geram overall; quatro disponíveis suficientes + speaking unavailable continuam partial global, podendo ter supported_scope suficiente.
- Cinco skills válidas liberam overall pela menor skill; falta/invalidez/conflict retira elegibilidade. Cobertura não vira aprovação e zero acertos não fabrica PRE_A1.
- Quotas garantem quatro evidências por skill se banco/orçamento permitem; duas na decisiva; streak/fallback não misturam faixas nem skills; empate determinístico; conflito inferior/superior pede confirmação; clones não contam duas vezes.
- Todos idiomas: contagens da matriz, capacidade de target, C1/C2 bloqueados, tipos desconhecidos/fórmula latina rejeitados para produção extensa; imported inactive/pending excluídos; exhausted antes de 12 encerra parcial sem impasse.
- Writing: IA completa/incompleta, heuristic/mock/fallback, nível acima do alvo, nível inválido, criteria ausente, bool/NaN/infinito, texto vazio/curto/truncado e línguas CJK; provenance real preservada, modelo legado null; 0.96 nunca vira 96% confiança.
- Listening: indisponibilidade/falha/skipped não vira erro cognitivo; resposta coletada sem confirmação de estímulo tem limitação explícita. Telemetria futura de reprodução é informação auxiliar, não prova absoluta de audição.
- API/persistência: resultado/sections/perfil coerentes, cinco skills únicas, complete repetido sem duplicação, rollback total de erro curricular, locks PostgreSQL concorrentes/stale session com autoflush=False, autorização por usuário e delivery intactas.
- Dados antigos: JSON v1 sem campos/respostas, reconstruível/não reconstruível, perfil manual/autodeclarado, nível antigo suficiente, parcial novo sem apagar evidência vigente; nenhum currículo ativo reescrito; nenhum GET escreve.
- Frontend: null overall, partial/complete/provisional/unavailable, scores 0 versus null, dashboard sem loop de retake, complemento permitido, currículo existente navegável, confiança sem percentual e sem extrapolação de fala.
- Migration: SQLite e PostgreSQL, upgrade vazio/legado, nullable/defaults sem inferência, FK e head Alembic; testes PostgreSQL não substituídos por SQLite.

Verificação desta tarefa: inspeção estática e agregação dos oito JSONs; nenhum teste de implementação rodado porque não houve implementação. Sem código, migration, banco, commit, push ou deploy alterado. Documento é proposta, não política já aprovada nem estado de produção certificado.
