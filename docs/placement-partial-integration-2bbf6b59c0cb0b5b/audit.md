# Divergências de integração: verificação do checkout atual

08/10/2026 · ID2bbf6b59c0cb0b5b. Nenhuma alteração em código de produção ou frontend. Foram adicionados testes backend e evidências locais. Produção/deploy não consultados.

## Endpoint e resposta reais

A tela de resultado consome `GET /api/v1/placement-tests/{id}/result`. `POST /api/v1/placement-tests/{id}/complete` e GET usam `_result_payload`; não há response_model filtrando a resposta. Os quatro campos planning_level/source/reason/trace aparecem via `**result`. Complete calcula a proposta, aplica/retem planejamento, persiste a decisão aplicada em PlacementTest.result_json e retorna a projeção. GET lê esse snapshot; não busca o planning do perfil para substituir o valor do teste.

HTTP local capturado sem mock de complete/planejamento: `new-account-partial-a1.json` contém complete e GET idênticos, além de currículo ativo, today, primeiro dia e POST de plano180 em parcial. Conta recém-criada sem perfil linguístico, teste francês com respostas objetivas corretas do banco existente; escrita/fala não avaliadas. Não é replay literal das respostas do aluno citado nem payload de produção.

Campos observados: overall_level=null, overall_estimate_status=partial, profile_status=partial, planning_level=A1, source=partial_evidence, reason preenchido, trace.policy.version=placement-planning-v1, trace.corroborated=true. R/L continuam insufficient_evidence. Currículo: entry_level=A1, generated_from=planning, duration_days=90, day_href preenchido.

`retained-planning.json`: global anterior B2 qualificado, novo assessment parcial propõe A1; resultado retorna planning_level=B2, trace.action=retained_prior_planning e trace.assessment_proposed_level=A1. Mudar o perfil agregado para A2 dentro do banco de teste não muda os quatro campos devolvidos pelo GET desse placement.

OpenAPI atual: schema de resposta200 é `{}` em ambos endpoints. Portanto há payload funcional, mas não schema formal tipado que documente seus campos. O tipo TypeScript do frontend não filtra JSON: lib/api retorna response.json().

## Caminho completo da Journey

Conta nova -> placement FR -> respostas -> complete partial -> planejamentoA1 -> _apply_to_profile -> ensure_active_curriculum -> generate_curriculum com generated_from=planning -> commit -> resultado com day_href.

`/cronograma` usa os hooks que chamam:

- `GET /api/v1/curriculum/active?language_code=fr`:200, mesmo currículo do resultado.
- `GET /api/v1/curriculum/day/today?language_code=fr`:200, day_number=1.
- `GET /api/v1/curriculum/day/{id}`:200,5 blocos e primeiro bloco unlocked (locked=false).
- `POST /api/v1/curriculum` com duration_days=180:200 mesmo com diagnostic_completed=false, entryA1 e origemplanning. Não grava current_level nem reading_level.

Complete repetido devolve o mesmo resultado e não duplica currículo. Um currículo ativo anterior é reaproveitado por ensure_active_curriculum. Regenerar explicitamente arquiva o anterior como regra existente.

## Divergência e correção necessária

As afirmações de ausência do planning e bloqueio obrigatório por diagnóstico completo não descrevem o checkout atual. Frontend atual prioriza planning do resultado; consulta perfil somente como fallback de ausência. A oferta BuildCurriculum tem condicionamento visual para measured, que não prova bloqueio do endpoint backend. No gerador, a guarda diagnostic_not_ready ainda existe, mas planning válido muda generated_from para planning antes dela.

Não foi encontrada perda de projeção ou bloqueio backend no fluxo solicitado. A hipótese de relatório/versão implantada anterior permanece não verificada; não atribuir isso a produção sem conferir a versão e uma chamada autenticada real.

Não é necessária correção de produção para estas duas divergências locais. Pendência recomendada: formalizar response_model/OpenAPI em tarefa própria, sem alterar contrato agora. Observação: os quatro campos de decisão são snapshot do assessment; o campo curriculum é resumo do currículo ativo atual do perfil, não vínculo histórico imutável com o teste.

## Testes

`backend/tests/test_placement_partial_integration.py`:

1. Conta nova sem perfil/placement anterior: complete partialA1, campos persistidos/GET idênticos, currículo navegável, primeiro bloco desbloqueado, repetição idempotente e geração180 permitida sem global.
2. Planning anteriorB2 preservado versus propostaA1; GET não segue mutação posterior do planning agregado.

Rodada final com `test_placement_planning.py`:11 passed em10,38s. SQLite isolado/TestClient; nenhuma chamada a provider real. PG/produção e execução efetiva de atividade não certificados. Snapshot HTTP completo nas duas evidências JSON; sem autenticação/credenciais nesses artefatos.
