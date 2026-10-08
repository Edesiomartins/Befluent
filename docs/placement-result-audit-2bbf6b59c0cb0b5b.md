# Auditoria real do placement francês — 2bbf6b59c0cb0b5b

Placement: `14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e`.
Fonte: JSON PostgreSQL READ ONLY executado pelo usuário, capturado em 07/10/2026 às 21:41:06 (America/Sao_Paulo; 08/10 00:41:06 UTC). Esta análise não executou operações na produção.

## 1. Resumo executivo

**O resultado é reproduzível pelo código, mas é arriscado apresentá-lo como CEFR global.** Foram 17 atividades respondidas: 16 objetivas e uma escrita. Leitura e listening foram coletados, pontuados e incluídos no engine; não houve perda dessas skills. O banco francês contém apenas um item por faixa para cada uma, enquanto a decisão exige dois na mesma faixa. Portanto, o banco atual torna estruturalmente impossível emitir CEFR de leitura ou listening, mesmo com todos os acertos.

B1 geral vem exclusivamente de vocabulário/gramática. A confiança 45 é um índice heurístico, não probabilidade de acerto da classificação. A escrita foi avaliada por IA, não pela heurística: o feedback salvo possui `estimated_level=B1`, mas a finalização impõe `estimated_level=None` e `calibrating` sem distinguir os avaliadores.

Pontos positivos confirmados: rastreabilidade das 17 entregas e respostas; skills e idioma consistentes; resultado salvo coincide com o recalculado; uma section por skill e um UserLanguage francês no recorte exportado. Limitações: não há snapshots históricos dos itens, telemetria de reprodução nem exportação de currículo/goals. Não certifico ausência de duplicação desses estados downstream nesta auditoria.

## 2. Tabela real das atividades

Ordem por entrega; horário abaixo é o da resposta, em São Paulo. Nas 16 objetivas, item skill = answer skill = skill usada pelo engine. Todas têm texto de enunciado; somente RD tem passagem de leitura. LS tem `audio_script`, sem `audio_url`. Não há payload de voz em nenhuma resposta. Máximo 1 é a escala normalizada, não uma coluna de max_score da resposta. Discriminação cadastrada é 1.0 em todos os itens; isso não demonstra calibração psicométrica.

VG = vocabulary_grammar; RD = reading; LS = listening; WR = writing. Todos os itens VG são multiple_choice, RD reading_comprehension, LS listening_comprehension, WR short_writing.

| # | Resposta (SP) | Item | Skill | Faixa | Dificuldade | Resposta enviada | Correção | Score/max | _records / estimativa candidata | CEFR final |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 19:30:13 | fr-a2-vg-01 | VG | A2 | 0.38 | vais | errada | 0.0/1 | sim | B1 |
| 2 | 19:30:27 | fr-a2-rd-01 | RD | A2 | 0.4 | O proprietário tinha uma consulta médica | certa | 1.0/1 | sim | sem faixa com ≥2 itens |
| 3 | 19:31:01 | fr-a2-ls-01 | LS | A2 | 0.42 | 8h30 | errada | 0.0/1 | sim | sem faixa com ≥2 itens |
| 4 | 19:31:21 | fr-a2-vg-02 | VG | A2 | 0.36 | ont | errada | 0.0/1 | sim | B1 |
| 5 | 19:31:38 | fr-a1-rd-01 | RD | A1 | 0.2 | À Lyon | certa | 1.0/1 | sim | sem faixa com ≥2 itens |
| 6 | 19:32:00 | fr-a1-ls-01 | LS | A1 | 0.22 | Café e água | certa | 1.0/1 | sim | sem faixa com ≥2 itens |
| 7 | 19:32:03 | fr-pre-a1-vg-01 | VG | PRE_A1 | 0.1 | Bonjour | certa | 1.0/1 | sim | B1 |
| 8 | 19:32:35 | fr-b1-rd-01 | RD | B1 | 0.6 | O desaparecimento da comunicação informal | certa | 1.0/1 | sim | sem faixa com ≥2 itens |
| 9 | 19:32:55 | fr-b1-ls-01 | LS | B1 | 0.6 | Reservar o ingresso pela internet | certa | 1.0/1 | sim | sem faixa com ≥2 itens |
| 10 | 19:32:59 | fr-pre-a1-vg-02 | VG | PRE_A1 | 0.12 | suis | certa | 1.0/1 | sim | B1 |
| 11 | 19:33:10 | fr-b2-rd-01 | RD | B2 | 0.78 | A automação tende a criar mais ocupações, apesar de transições difíceis | certa | 1.0/1 | sim | sem faixa com ≥2 itens |
| 12 | 19:33:35 | fr-b2-ls-01 | LS | B2 | 0.8 | Parcialmente favorável, com reservas sobre o orçamento | certa | 1.0/1 | sim | sem faixa com ≥2 itens |
| 13 | 19:33:42 | fr-b1-vg-02 | VG | B1 | 0.52 | renoncer | certa | 1.0/1 | sim | B1 |
| 14 | 19:33:49 | fr-b1-vg-01 | VG | B1 | 0.56 | avais | certa | 1.0/1 | sim | B1 |
| 15 | 19:33:59 | fr-b2-vg-01 | VG | B2 | 0.72 | avait | certa | 1.0/1 | sim | B1 |
| 16 | 19:34:06 | fr-b2-vg-02 | VG | B2 | 0.74 | étais | errada | 0.0/1 | sim | B1 |
| 17 | 19:36:19 | fr-b1-wr-01 | WR | B1 | 0.6 | Texto completo no apêndice | — | 0.96/1 | não: produção | calibrating |

IDs completos de todas as entregas:

| # | placement_item_id | delivery_id |
| --- | --- | --- |
| 1 | 0b922c27-48e0-412a-b738-7114ed2935de | a6ab5127-72ad-4c84-bf4a-972ee00bae4e |
| 2 | 56937b8d-67be-4389-be03-6bed385c4cfa | 9baaffd4-bf06-438c-920a-7647b14962a9 |
| 3 | a43afd4e-29cf-45e4-81f8-6b7c517f01cd | 641b1806-b254-4858-8bc3-899c0dade490 |
| 4 | 69d72462-205f-4593-8ae7-190902d858c5 | fb7a8bfd-b6bb-4b10-a7c8-8d5f5e0a4277 |
| 5 | 51ef23af-489b-413d-b43b-5147a774a20c | 1ee16d43-8d17-47d0-88e2-c680acc7e16b |
| 6 | 1aacdb03-4d38-4565-b593-e29e550b8f82 | 955fda52-1347-4daa-a85e-4ac7c57248ad |
| 7 | 30b33211-ab56-4ef0-9c87-c6f559e2f5c2 | 53e00fb1-f6ec-47c6-a929-bf7b03f9823c |
| 8 | 7779c27f-c6d3-45fe-b1b2-c2d75a61ab3e | 5d42a6a9-928c-4f0b-9768-912e5c95670d |
| 9 | 418fbe0b-af20-420f-b948-45b6de32fe97 | 9ad56627-07aa-46b0-ab9f-0f65bea770f5 |
| 10 | edc8afd6-e846-448a-a90e-6e3040ba9e77 | 4cb35921-be77-49ca-9016-5b3dc3d39857 |
| 11 | 4046e878-0494-4970-8f2b-abb2433891ba | a629e362-0b79-46f3-92c5-f0811b266776 |
| 12 | b7b9ea78-7234-4652-9d8d-23ff93400a8f | 92592453-b365-4829-b8c8-3de4580de52b |
| 13 | ecd7f9e2-f31e-4d67-bb58-9169dbce605f | 97b3633b-76df-48e4-9f31-3ea08403d5bb |
| 14 | c6b6b810-568e-40bb-9204-3ecfeb3de169 | e59303a6-aee2-492b-98bb-2dc9ba716462 |
| 15 | 434ade8b-9ff4-445c-8132-fe3339133f71 | 21cddb96-adee-45a1-8dcf-a12f7cef183f |
| 16 | ca0c86bd-8747-4b2a-8505-87fb902acd2d | 34e9ab30-114b-457e-ab05-d8ee7b98731f |
| 17 | ad4e53d2-7ee5-4eff-837d-c79d5de4efd2 | a76e036b-ca04-47ff-b411-0e1c04e68a4d |

As 16 respostas objetivas entram na estimativa candidata de suas próprias skills. Somente VG produz estimativa final. WR é excluída de `_records` e de `skill_results` por ser produção. Nenhuma resposta objetiva tem score ausente, discrepância item-answer de skill/CEFR/idioma ou item atualizado depois da resposta segundo os timestamps exportados. Não há entrega pendente ou resposta órfã neste recorte.

## 3. Contagem de evidências por skill

| Skill | Entregues/respondidas | Pontuadas | Evidências objetivas | Score objetivo | CEFR final |
| --- | --- | --- | --- | --- | --- |
| vocabulary_grammar | 8 | 8 | 8 | 5.0 | B1 |
| reading | 4 | 4 | 4 | 4.0 | não emitido |
| listening | 4 | 4 | 4 | 3.0 | não emitido |
| writing | 1 | 1 | 0 | 0.96 | não emitido |
| speaking | 0 | 0 | 0 | 0 | não emitido |

Total objetivo: 12/16. WR: 0.96/1 separado, sem contribuição ao total objetivo. O `items_answered=16` do resultado conta objetivos; as 17 atividades incluem escrita.

## 4. Por que reading ficou não avaliada

Quatro itens legítimos de leitura, todos corretos: A1, A2, B1 e B2, um por faixa. Todos têm passage e entraram em `_records`. A regra exige ≥4 respostas na skill, ≥2 respostas na faixa decisória e média ≥0.65. O primeiro requisito foi satisfeito; o segundo falha em todas as faixas. `estimate_skill_level` retorna None; `skill_results` omite reading; complete cria section `not_assessed`, com score/max 0/0.

Logo, “não avaliada” mistura ausência de coleta com evidência coletada sem decisão. Os quatro acertos existem e o 0/0 da section não os representa. Não houve classificação de passagem legítima como VG nos dados apresentados: as passagens estão nos quatro RD; VG usa frases/vocabulário isolados.

## 5. Por que listening ficou não avaliada; auditoria do áudio

Quatro LS: A1 1/1, A2 0/1, B1 1/1, B2 1/1. Todos entraram em `_records`; novamente há apenas um item por faixa. Mesmo os três acertos não satisfazem ≥2 na faixa decisória. Resultado: None → omissão → section 0/0 `not_assessed`.

Os únicos quatro itens com áudio disponível são LS (#3, #6, #9, #12). O conteúdo relevante está no audio_script em francês; o enunciado/pergunta e alternativas não reproduzem a transcrição. Exemplos: horário do trem; pedido de café/água; recomendação de reservar ingresso; opinião com reservas orçamentárias. Segundo os campos e a implementação local da tela, as respostas dependem semanticamente do estímulo ouvido, não de TTS de uma passagem também exibida.

A tela local `frontend/app/(app)/placement-test/[id]/page.tsx` sintetiza audio_script com speechSynthesis; não exibe a transcrição. TTS pode fornecer um estímulo válido de listening: o que importa aqui é a compreensão auditiva exigida. Não foi fornecido hash/build do frontend em produção, portanto não certifico a interface efetivamente renderizada naquele momento. O banco prova disponibilidade, não que o áudio tenha tocado. Todos os quatro deveriam contar e efetivamente contaram como listening na arquitetura atual. Delivery guarda item_id, não snapshot de skill; a resposta guarda listening, preservado em `_records`.

## 6. Por que speaking ficou não avaliada

Zero itens entregues, zero respostas speaking e zero payloads de gravação. O endpoint `submit_speaking` é indisponível (501), e a tela examinada não coleta gravação. A section está `not_available`. É correto não emitir CEFR de fala; ouvir TTS não é amostra de produção oral. A exportação não pode excluir gravações em sistemas externos, mas não há coleta speaking neste fluxo registrado.

## 7. Por que writing ficou calibrating

Item B1 `fr-b1-wr-01`, resposta #17. `evaluated_by=ai`, feedback `status=assessed`, `normalized_score=0.96`, `target_level=B1`, `estimated_level=B1`. Critérios salvos: adequação 0.95, coerência 0.96, clareza 0.96; não vieram scores de vocabulário/gramática/organização. Não houve reavaliação nesta auditoria.

O feedback textual elogia a redação e sugere aproximadamente B2, mas o campo estruturado é B1. `_validate_ai_payload` limita o nível ao nível-alvo do item; isso explica por que um campo acima de B1 seria reduzido, porém o payload bruto anterior à validação não foi exportado: não afirmo que o modelo tenha originalmente retornado B2 no campo.

`submit_writing` salva a avaliação na resposta. `_records` exclui writing; `skill_results` também exclui produção. Em `complete_test`, o bloco `writing_answer` fixa sempre `estimated_level=None`, `status=calibrating`, independentemente de `evaluated_by` ou do nível no feedback. A section final é `840f9195-a9ef-44be-9438-fadf1e1d9596`, score 0.96/max 1, confidence None. Seu completed_at usa a data da resposta (19:36:19 SP), não a data de criação da section; esse timestamp não prova que ela tenha sido criada antes do complete.

A regra de não usar uma heurística como CEFR é deliberada. Sua aplicação indiscriminada à avaliação por IA é uma inconsistência funcional confirmada. Não é falta de quantidade mínima de escrita no caminho atual, nem falta de campo na avaliação: há nível salvo, que o complete não utiliza. Também não cabe promover automaticamente uma única nota de IA a certificação CEFR; a política de aceitação deve ser definida.

## 8. Cálculo exato do B1

VG: PRE_A1 2/2; A2 0/2; B1 2/2; B2 1/2. Não houve VG A1. PRE_A1 e B1 satisfazem ≥2 e média ≥0.65; B2 tem 0.50, A2 0.00. A maior faixa dominada é B1. Os oito VG somam 5/8 = 0.625, mas a decisão usa a maior faixa dominada, não o acerto global.

Somente VG aparece em `skills`. Pesos renormalizados: VG=1.0. Índice B1=3; soma ponderada 3×1=3; arredondamento 3; teto da skill+1=4; teto testável B2=4. Resultado final B1. **Sim, o geral depende exclusivamente de VG.** O padrão A2 0/2 e B1 2/2 é não monotônico; o algoritmo aceita a faixa superior sem exigir consistência inferior. Isso aumenta a fragilidade da inferência, sem autorizar descartar as respostas reais.

## 9. Cálculo exato da confiança 45

`40 + 15 + 4 − 0 − 0 − 14 = 45`.

- Base 40.
- Volume: 16 objetivos, bônus 15 (faixa de 12 a 19).
- Cobertura: uma skill com CEFR ×4 =4.
- Dispersão de níveis emitidos: zero, penalidade zero.
- Respostas abaixo de 1500ms: zero, penalidade zero.
- Essenciais sem nível: listening e speaking, 7 cada =14.

Reading não recebe penalidade direta de essencial; listening recebe apesar de quatro respostas, pois não possui CEFR. O volume dá bônus por RD/LS mesmo sem classificação. Com uma skill, a dispersão necessariamente fica zero: isso não demonstra concordância entre competências. 45/100 e o rótulo moderada são heurísticos, não intervalo estatístico ou probabilidade psicométrica. Os 4363 segundos são tempo até a conclusão, incluindo a espera do incidente; não medem exclusivamente tempo ativo de teste.

## 10. Há bug de código?

Não há erro aritmético ou perda de skill nas respostas objetivas. Campos comparados no exportador — overall, confidence, contagem, skills, pesos e listas — coincidem com os persistidos. As fontes backend exportadas coincidem com as locais após normalizar CRLF/LF; isso verifica a versão na captura, não uma versão histórica distinta.

Há inconsistência na escrita: feedback AI assessed/B1 versus section calibrating/None, por override incondicional. Há também defeito no contrato de estado/evidência: section 0/0 e not_assessed escondem respostas objetivas coletadas, e `diagnostic_status=ready` requer apenas um nível geral não nulo. A correção anterior de duplicação permitiu consolidar este teste: há exatamente cinco sections distintas no JSON. Não se deve atribuir as lacunas atuais ao IntegrityError anterior.

## 11. Há problema de classificação dos itens?

Não foi encontrada perda de taxonomia ou item RD/LS rotulado VG entre as 17 atividades. Os itens com áudio são LS, os de passagem são RD e a escrita é WR. Isso não valida os rótulos CEFR nem a qualidade psicométrica. Todos vêm de `befluent_dev_seed`, approved, discrimination 1.0; aprovação administrativa e parâmetro cadastrado não comprovam estudo de calibração.

## 12. Há problema de cobertura do banco?

**Sim: incompatibilidade estrutural entre banco e regra de decisão.** Matriz francesa atual, todos ativos e approved:

| Skill | PRE_A1 | A1 | A2 | B1 | B2 | C1 | C2 | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vocabulary_grammar | 2 | 0 | 2 | 2 | 2 | 0 | 0 | 8 |
| reading | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 4 |
| listening | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 4 |
| writing | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 4 |
| speaking | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Oito VG, quatro RD, quatro LS = somente 16 objetivos elegíveis; todos consumidos. Quatro WR, apenas uma usada; zero speaking. Não existem dois RD ou LS em nenhuma faixa. Portanto nenhum aluno consegue cumprir a regra decisória dessas skills com este inventário sem repetição de item. Writing não participa da matriz objetiva; os três restantes não completam target=20. C1/C2 não estão disponíveis no banco exportado nem são testáveis neste engine.

Inventário é o da captura. Os itens entregues não mostram atualização posterior às respostas, fortalecendo a reconstrução, mas não há snapshot que certifique inventário/query ordering em cada entrega.

## 13. Há problema no adaptive selector?

`next_skill` tenta equilibrar as três skills objetivas por número de respostas, priorizando menos de quatro. `_pick_objective_item` tenta primeiro a faixa atual de cada skill em ordem de preferência; depois relaxa para outras faixas. Não garante dois itens na faixa decisória, nem exige que cada skill produza CEFR antes de concluir.

No replay de preferências, as respostas #14–16 eram preferencialmente reading, mas receberam VG; naquele ponto os quatro RD já estavam consumidos. Não é perda de skill: é fallback. O replay reconstrói preferência a partir das respostas salvas, sem prova do ordering histórico das consultas.

`target=20` é quantidade recomendada de objetivos gerais (A), não matriz planejada por competência (B). `should_stop` usa contagem geral e faixa, com máximo 30. Como há apenas 16 objetivos elegíveis e todos foram consumidos, `next_item` cai no caminho de ausência de candidato, oferece writing e depois ready_to_complete, sem chegar a 20. O `complete` aceita ≥12 objetivos; não exige cobertura conclusiva por skill.

Risco equivalente: se RD/LS forem escassos, fallback pode concentrar mais respostas em VG. Neste teste a distribuição final foi 8/4/4, não quase exclusivamente VG, mas somente VG conseguiu emitir nível. O defeito é cobertura decisória, não apenas cobertura numérica.

## 14. Problema pedagógico do nível global

É defensável usar esse resultado como orientação provisória de início de conteúdo, com escopo explícito. Não é sustentado apresentar B1 como proficiência global demonstrada: somente oito questões VG determinaram o nível; leitura/audição não tiveram decisão possível pelo banco, fala não foi coletada e escrita foi excluída apesar da avaliação salva.

O CEFR permite perfis por atividade comunicativa e competências desiguais; isso apoia expor o perfil, não inferir as competências ausentes a partir de gramática. Fonte primária: [Conselho da Europa — Linguistic profiles and profiling](https://www.coe.int/it/web/lang-migrants/profile-language-/-profiling).

Recomendação: “Estimativa inicial B1 baseada em vocabulário e gramática; outras competências ainda sem nível confirmado”. Para RD/LS, informar “evidência coletada, insuficiente para estimar o nível”, preservando 4/4 e 3/4. Isso é proposta, não alteração aplicada. Não recomendo mudar silenciosamente para A2 ou B2: os dados atuais não sustentam essa substituição global.

## 15. Proposta de correção — não implementada

1. Definir contrato por skill: não coletada, indisponível, coletada sem decisão, preliminar e avaliada; preservar contagens/scores reais mesmo sem CEFR. Separar prontidão operacional da suficiência pedagógica/global.
2. Ampliar/revisar o banco francês por skill/faixa para cumprir a regra de pelo menos dois itens decisórios e permitir caminhos de confirmação. Dois por faixa é apenas o piso do código, não validação pedagógica; prever reserva e revisão dos níveis/dificuldades antes de considerar o banco calibrado.
3. Orientar seleção e parada por cobertura de evidência decisória, com limites e saída parcial explícita quando o banco acabar; persistir motivo de parada/fallback e snapshots de entrega. Não completar uma lacuna apenas aumentando target.
4. Definir política para escrita AI versus heurística: manter avaliação salva, origem, nível-alvo, limitação ao alvo e status coerentes. Se IA continuar preliminar por decisão pedagógica, mostrar isso e não alegar que foi heurística; se puder emitir nível, estabelecer critérios e validação antes de agregá-lo. Não mapear 0.96 mecanicamente para B2/C1.
5. Manter fala indisponível até existir coleta e avaliação autorizadas. Não atribuir CEFR de speaking por áudio ouvido.
6. Tratar nível agregado como parcial enquanto houver lacunas; revisar confiança e validar sua interpretação. Testar caso real 8/4/4/1, impossibilidade de banda, fallback, escassez, produção AI/heurística e consistência de resultados.

Não houve alteração de lógica, dados, reset, reavaliação por IA, commit, push ou deploy nesta etapa. Há apenas este relatório. O teste já está completed, com B1/45 também no UserLanguage; não precisa ser reiniciado para diagnosticar o problema. Uma futura correção não recalcula automaticamente completed, pois complete retorna o resultado salvo. Revisão de resultados históricos precisará de plano separado, dry-run e autorização antes de qualquer escrita. Currículo/goals não foram exportados, portanto seu estado real exige coleta adicional caso entre no escopo da correção.

## Apêndice — conteúdos, avaliações e rastreabilidade completos

Os registros abaixo preservam texto, resposta, alternativa correta, score bruto/normalizado, feedback, IDs, tipos, modalities, evidências, timestamps e motivos. Não contêm credenciais. Os campos de item são atuais; delivery não guarda snapshot histórico. A ausência de voz é baseada no payload; disponibilidade de áudio não prova reprodução.

### Atividade 1 — fr-a2-vg-01

```json
{
  "order": 1,
  "placement_item_id": "0b922c27-48e0-412a-b738-7114ed2935de",
  "delivery_id": "a6ab5127-72ad-4c84-bf4a-972ee00bae4e",
  "item_type": "multiple_choice",
  "item_skill": "vocabulary_grammar",
  "answer_skill": "vocabulary_grammar",
  "skill_used_by_engine": "vocabulary_grammar",
  "modality_inferred_from_fields": "text",
  "has_text": true,
  "has_reading_passage": false,
  "has_audio_available": false,
  "has_voice_recording": false,
  "voice_payload_keys": [],
  "response_kind": "selected_value",
  "normalized_max_score": 1.0,
  "max_score_basis": "normalized_0_to_1_scale_not_a_persisted_answer_column",
  "entered_records": true,
  "records_exclusion_reason": null,
  "entered_candidate_skill_estimation": true,
  "skill_cefr_emitted": true,
  "skill_no_cefr_reason": null,
  "item_answer_skill_mismatch": false,
  "item_answer_cefr_mismatch": false,
  "item_language_mismatch": false,
  "item_updated_after_answer": false,
  "item": {
    "external_key": "fr-a2-vg-01",
    "language_code": "fr",
    "cefr_level": "A2",
    "skill": "vocabulary_grammar",
    "item_type": "multiple_choice",
    "prompt": "Complete: \"Hier, je ___ allé au cinéma.\"",
    "instructions": null,
    "passage": null,
    "options_json": [
      "suis",
      "ai",
      "vais",
      "serai"
    ],
    "correct_answer_json": {
      "value": "suis"
    },
    "explanation": "O verbo \"aller\" forma o passé composé com o auxiliar \"être\".",
    "audio_url": null,
    "audio_script": null,
    "rubric_json": {},
    "difficulty": 0.38,
    "discrimination": 1.0,
    "is_active": true,
    "version": 1,
    "source": "befluent_dev_seed",
    "license": "proprietary",
    "attribution": null,
    "source_ref": null,
    "review_status": "approved",
    "created_at": "2026-07-28T00:22:45.374723+00:00",
    "updated_at": "2026-07-28T00:22:45.374724+00:00",
    "id": "0b922c27-48e0-412a-b738-7114ed2935de"
  },
  "delivery": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "0b922c27-48e0-412a-b738-7114ed2935de",
    "delivered_at": "2026-10-07T22:30:05.932503+00:00",
    "expires_at": "2026-10-07T23:00:05.932512+00:00",
    "consumed_at": "2026-10-07T22:30:13.614722+00:00",
    "created_at": "2026-10-07T22:30:05.936906+00:00",
    "id": "a6ab5127-72ad-4c84-bf4a-972ee00bae4e"
  },
  "answer": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "0b922c27-48e0-412a-b738-7114ed2935de",
    "skill": "vocabulary_grammar",
    "cefr_level": "A2",
    "answer_json": {
      "value": "vais"
    },
    "is_correct": false,
    "raw_score": 0.0,
    "normalized_score": 0.0,
    "response_time_ms": 7322,
    "evaluated_by": "auto",
    "feedback_json": {},
    "created_at": "2026-10-07T22:30:13.629667+00:00",
    "id": "45332f6d-5055-4ac8-86ec-2064d2259290"
  }
}
```

### Atividade 2 — fr-a2-rd-01

```json
{
  "order": 2,
  "placement_item_id": "56937b8d-67be-4389-be03-6bed385c4cfa",
  "delivery_id": "9baaffd4-bf06-438c-920a-7647b14962a9",
  "item_type": "reading_comprehension",
  "item_skill": "reading",
  "answer_skill": "reading",
  "skill_used_by_engine": "reading",
  "modality_inferred_from_fields": "text",
  "has_text": true,
  "has_reading_passage": true,
  "has_audio_available": false,
  "has_voice_recording": false,
  "voice_payload_keys": [],
  "response_kind": "selected_value",
  "normalized_max_score": 1.0,
  "max_score_basis": "normalized_0_to_1_scale_not_a_persisted_answer_column",
  "entered_records": true,
  "records_exclusion_reason": null,
  "entered_candidate_skill_estimation": true,
  "skill_cefr_emitted": false,
  "skill_no_cefr_reason": "no_band_meets_minimum_count_and_accuracy",
  "item_answer_skill_mismatch": false,
  "item_answer_cefr_mismatch": false,
  "item_language_mismatch": false,
  "item_updated_after_answer": false,
  "item": {
    "external_key": "fr-a2-rd-01",
    "language_code": "fr",
    "cefr_level": "A2",
    "skill": "reading",
    "item_type": "reading_comprehension",
    "prompt": "Por que a loja fechou mais cedo?",
    "instructions": null,
    "passage": "Le magasin a fermé à seize heures parce que le propriétaire avait un rendez-vous médical. Il ouvrira demain à l'heure habituelle.",
    "options_json": [
      "O proprietário tinha uma consulta médica",
      "Não havia clientes",
      "Faltou energia",
      "Era feriado"
    ],
    "correct_answer_json": {
      "value": "O proprietário tinha uma consulta médica"
    },
    "explanation": "O texto diz \"parce que le propriétaire avait un rendez-vous médical\".",
    "audio_url": null,
    "audio_script": null,
    "rubric_json": {},
    "difficulty": 0.4,
    "discrimination": 1.0,
    "is_active": true,
    "version": 1,
    "source": "befluent_dev_seed",
    "license": "proprietary",
    "attribution": null,
    "source_ref": null,
    "review_status": "approved",
    "created_at": "2026-07-28T00:22:45.374740+00:00",
    "updated_at": "2026-07-28T00:22:45.374741+00:00",
    "id": "56937b8d-67be-4389-be03-6bed385c4cfa"
  },
  "delivery": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "56937b8d-67be-4389-be03-6bed385c4cfa",
    "delivered_at": "2026-10-07T22:30:13.748643+00:00",
    "expires_at": "2026-10-07T23:00:13.748648+00:00",
    "consumed_at": "2026-10-07T22:30:27.695542+00:00",
    "created_at": "2026-10-07T22:30:13.749010+00:00",
    "id": "9baaffd4-bf06-438c-920a-7647b14962a9"
  },
  "answer": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "56937b8d-67be-4389-be03-6bed385c4cfa",
    "skill": "reading",
    "cefr_level": "A2",
    "answer_json": {
      "value": "O proprietário tinha uma consulta médica"
    },
    "is_correct": true,
    "raw_score": 1.0,
    "normalized_score": 1.0,
    "response_time_ms": 13806,
    "evaluated_by": "auto",
    "feedback_json": {},
    "created_at": "2026-10-07T22:30:27.699978+00:00",
    "id": "5da475c6-9e01-4326-b11d-804f231c1a15"
  }
}
```

### Atividade 3 — fr-a2-ls-01

```json
{
  "order": 3,
  "placement_item_id": "a43afd4e-29cf-45e4-81f8-6b7c517f01cd",
  "delivery_id": "641b1806-b254-4858-8bc3-899c0dade490",
  "item_type": "listening_comprehension",
  "item_skill": "listening",
  "answer_skill": "listening",
  "skill_used_by_engine": "listening",
  "modality_inferred_from_fields": "text_and_audio",
  "has_text": true,
  "has_reading_passage": false,
  "has_audio_available": true,
  "has_voice_recording": false,
  "voice_payload_keys": [],
  "response_kind": "selected_value",
  "normalized_max_score": 1.0,
  "max_score_basis": "normalized_0_to_1_scale_not_a_persisted_answer_column",
  "entered_records": true,
  "records_exclusion_reason": null,
  "entered_candidate_skill_estimation": true,
  "skill_cefr_emitted": false,
  "skill_no_cefr_reason": "no_band_meets_minimum_count_and_accuracy",
  "item_answer_skill_mismatch": false,
  "item_answer_cefr_mismatch": false,
  "item_language_mismatch": false,
  "item_updated_after_answer": false,
  "item": {
    "external_key": "fr-a2-ls-01",
    "language_code": "fr",
    "cefr_level": "A2",
    "skill": "listening",
    "item_type": "listening_comprehension",
    "prompt": "Que horas o trem parte?",
    "instructions": null,
    "passage": null,
    "options_json": [
      "7h30",
      "7h00",
      "3h30",
      "8h30"
    ],
    "correct_answer_json": {
      "value": "7h30"
    },
    "explanation": "\"Sept heures et demie\" significa sete e meia.",
    "audio_url": null,
    "audio_script": "Le train pour Marseille part à sept heures et demie, quai numéro trois.",
    "rubric_json": {},
    "difficulty": 0.42,
    "discrimination": 1.0,
    "is_active": true,
    "version": 1,
    "source": "befluent_dev_seed",
    "license": "proprietary",
    "attribution": null,
    "source_ref": null,
    "review_status": "approved",
    "created_at": "2026-07-28T00:22:45.374748+00:00",
    "updated_at": "2026-07-28T00:22:45.374749+00:00",
    "id": "a43afd4e-29cf-45e4-81f8-6b7c517f01cd"
  },
  "delivery": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "a43afd4e-29cf-45e4-81f8-6b7c517f01cd",
    "delivered_at": "2026-10-07T22:30:27.788513+00:00",
    "expires_at": "2026-10-07T23:00:27.788518+00:00",
    "consumed_at": "2026-10-07T22:31:01.222733+00:00",
    "created_at": "2026-10-07T22:30:27.788881+00:00",
    "id": "641b1806-b254-4858-8bc3-899c0dade490"
  },
  "answer": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "a43afd4e-29cf-45e4-81f8-6b7c517f01cd",
    "skill": "listening",
    "cefr_level": "A2",
    "answer_json": {
      "value": "8h30"
    },
    "is_correct": false,
    "raw_score": 0.0,
    "normalized_score": 0.0,
    "response_time_ms": 33200,
    "evaluated_by": "auto",
    "feedback_json": {},
    "created_at": "2026-10-07T22:31:01.238628+00:00",
    "id": "eef338e9-0c30-4e47-b787-7afe8c52263c"
  }
}
```

### Atividade 4 — fr-a2-vg-02

```json
{
  "order": 4,
  "placement_item_id": "69d72462-205f-4593-8ae7-190902d858c5",
  "delivery_id": "fb7a8bfd-b6bb-4b10-a7c8-8d5f5e0a4277",
  "item_type": "multiple_choice",
  "item_skill": "vocabulary_grammar",
  "answer_skill": "vocabulary_grammar",
  "skill_used_by_engine": "vocabulary_grammar",
  "modality_inferred_from_fields": "text",
  "has_text": true,
  "has_reading_passage": false,
  "has_audio_available": false,
  "has_voice_recording": false,
  "voice_payload_keys": [],
  "response_kind": "selected_value",
  "normalized_max_score": 1.0,
  "max_score_basis": "normalized_0_to_1_scale_not_a_persisted_answer_column",
  "entered_records": true,
  "records_exclusion_reason": null,
  "entered_candidate_skill_estimation": true,
  "skill_cefr_emitted": true,
  "skill_no_cefr_reason": null,
  "item_answer_skill_mismatch": false,
  "item_answer_cefr_mismatch": false,
  "item_language_mismatch": false,
  "item_updated_after_answer": false,
  "item": {
    "external_key": "fr-a2-vg-02",
    "language_code": "fr",
    "cefr_level": "A2",
    "skill": "vocabulary_grammar",
    "item_type": "multiple_choice",
    "prompt": "Escolha a forma correta: \"Il y ___ du lait dans le frigo.\"",
    "instructions": null,
    "passage": null,
    "options_json": [
      "a",
      "ont",
      "est",
      "sont"
    ],
    "correct_answer_json": {
      "value": "a"
    },
    "explanation": "A expressão fixa é \"il y a\".",
    "audio_url": null,
    "audio_script": null,
    "rubric_json": {},
    "difficulty": 0.36,
    "discrimination": 1.0,
    "is_active": true,
    "version": 1,
    "source": "befluent_dev_seed",
    "license": "proprietary",
    "attribution": null,
    "source_ref": null,
    "review_status": "approved",
    "created_at": "2026-07-28T00:22:45.374732+00:00",
    "updated_at": "2026-07-28T00:22:45.374733+00:00",
    "id": "69d72462-205f-4593-8ae7-190902d858c5"
  },
  "delivery": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "69d72462-205f-4593-8ae7-190902d858c5",
    "delivered_at": "2026-10-07T22:31:01.383334+00:00",
    "expires_at": "2026-10-07T23:01:01.383339+00:00",
    "consumed_at": "2026-10-07T22:31:21.987827+00:00",
    "created_at": "2026-10-07T22:31:01.383805+00:00",
    "id": "fb7a8bfd-b6bb-4b10-a7c8-8d5f5e0a4277"
  },
  "answer": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "69d72462-205f-4593-8ae7-190902d858c5",
    "skill": "vocabulary_grammar",
    "cefr_level": "A2",
    "answer_json": {
      "value": "ont"
    },
    "is_correct": false,
    "raw_score": 0.0,
    "normalized_score": 0.0,
    "response_time_ms": 20439,
    "evaluated_by": "auto",
    "feedback_json": {},
    "created_at": "2026-10-07T22:31:21.993695+00:00",
    "id": "66b45ac9-0571-4605-9538-149fddfe88eb"
  }
}
```

### Atividade 5 — fr-a1-rd-01

```json
{
  "order": 5,
  "placement_item_id": "51ef23af-489b-413d-b43b-5147a774a20c",
  "delivery_id": "1ee16d43-8d17-47d0-88e2-c680acc7e16b",
  "item_type": "reading_comprehension",
  "item_skill": "reading",
  "answer_skill": "reading",
  "skill_used_by_engine": "reading",
  "modality_inferred_from_fields": "text",
  "has_text": true,
  "has_reading_passage": true,
  "has_audio_available": false,
  "has_voice_recording": false,
  "voice_payload_keys": [],
  "response_kind": "selected_value",
  "normalized_max_score": 1.0,
  "max_score_basis": "normalized_0_to_1_scale_not_a_persisted_answer_column",
  "entered_records": true,
  "records_exclusion_reason": null,
  "entered_candidate_skill_estimation": true,
  "skill_cefr_emitted": false,
  "skill_no_cefr_reason": "no_band_meets_minimum_count_and_accuracy",
  "item_answer_skill_mismatch": false,
  "item_answer_cefr_mismatch": false,
  "item_language_mismatch": false,
  "item_updated_after_answer": false,
  "item": {
    "external_key": "fr-a1-rd-01",
    "language_code": "fr",
    "cefr_level": "A1",
    "skill": "reading",
    "item_type": "reading_comprehension",
    "prompt": "Onde mora Julie?",
    "instructions": null,
    "passage": "Julie est française. Elle habite à Lyon dans un petit appartement. Elle travaille dans une librairie.",
    "options_json": [
      "À Lyon",
      "À Paris",
      "Dans une librairie",
      "Dans une école"
    ],
    "correct_answer_json": {
      "value": "À Lyon"
    },
    "explanation": "O texto diz \"Elle habite à Lyon\".",
    "audio_url": null,
    "audio_script": null,
    "rubric_json": {},
    "difficulty": 0.2,
    "discrimination": 1.0,
    "is_active": true,
    "version": 1,
    "source": "befluent_dev_seed",
    "license": "proprietary",
    "attribution": null,
    "source_ref": null,
    "review_status": "approved",
    "created_at": "2026-07-28T00:22:45.374692+00:00",
    "updated_at": "2026-07-28T00:22:45.374693+00:00",
    "id": "51ef23af-489b-413d-b43b-5147a774a20c"
  },
  "delivery": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "51ef23af-489b-413d-b43b-5147a774a20c",
    "delivered_at": "2026-10-07T22:31:22.115460+00:00",
    "expires_at": "2026-10-07T23:01:22.115466+00:00",
    "consumed_at": "2026-10-07T22:31:38.785810+00:00",
    "created_at": "2026-10-07T22:31:22.115910+00:00",
    "id": "1ee16d43-8d17-47d0-88e2-c680acc7e16b"
  },
  "answer": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "51ef23af-489b-413d-b43b-5147a774a20c",
    "skill": "reading",
    "cefr_level": "A1",
    "answer_json": {
      "value": "À Lyon"
    },
    "is_correct": true,
    "raw_score": 1.0,
    "normalized_score": 1.0,
    "response_time_ms": 16498,
    "evaluated_by": "auto",
    "feedback_json": {},
    "created_at": "2026-10-07T22:31:38.790830+00:00",
    "id": "81baaeb6-83ea-4c7a-b929-a93fbcc63a8e"
  }
}
```

### Atividade 6 — fr-a1-ls-01

```json
{
  "order": 6,
  "placement_item_id": "1aacdb03-4d38-4565-b593-e29e550b8f82",
  "delivery_id": "955fda52-1347-4daa-a85e-4ac7c57248ad",
  "item_type": "listening_comprehension",
  "item_skill": "listening",
  "answer_skill": "listening",
  "skill_used_by_engine": "listening",
  "modality_inferred_from_fields": "text_and_audio",
  "has_text": true,
  "has_reading_passage": false,
  "has_audio_available": true,
  "has_voice_recording": false,
  "voice_payload_keys": [],
  "response_kind": "selected_value",
  "normalized_max_score": 1.0,
  "max_score_basis": "normalized_0_to_1_scale_not_a_persisted_answer_column",
  "entered_records": true,
  "records_exclusion_reason": null,
  "entered_candidate_skill_estimation": true,
  "skill_cefr_emitted": false,
  "skill_no_cefr_reason": "no_band_meets_minimum_count_and_accuracy",
  "item_answer_skill_mismatch": false,
  "item_answer_cefr_mismatch": false,
  "item_language_mismatch": false,
  "item_updated_after_answer": false,
  "item": {
    "external_key": "fr-a1-ls-01",
    "language_code": "fr",
    "cefr_level": "A1",
    "skill": "listening",
    "item_type": "listening_comprehension",
    "prompt": "O que a pessoa pediu?",
    "instructions": null,
    "passage": null,
    "options_json": [
      "Café e água",
      "Chá e suco",
      "Café e pão",
      "Leite e bolo"
    ],
    "correct_answer_json": {
      "value": "Café e água"
    },
    "explanation": "A frase menciona \"un café et une bouteille d'eau\".",
    "audio_url": null,
    "audio_script": "Je voudrais un café et une bouteille d'eau, s'il vous plaît.",
    "rubric_json": {},
    "difficulty": 0.22,
    "discrimination": 1.0,
    "is_active": true,
    "version": 1,
    "source": "befluent_dev_seed",
    "license": "proprietary",
    "attribution": null,
    "source_ref": null,
    "review_status": "approved",
    "created_at": "2026-07-28T00:22:45.374700+00:00",
    "updated_at": "2026-07-28T00:22:45.374701+00:00",
    "id": "1aacdb03-4d38-4565-b593-e29e550b8f82"
  },
  "delivery": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "1aacdb03-4d38-4565-b593-e29e550b8f82",
    "delivered_at": "2026-10-07T22:31:38.954225+00:00",
    "expires_at": "2026-10-07T23:01:38.954231+00:00",
    "consumed_at": "2026-10-07T22:32:00.370592+00:00",
    "created_at": "2026-10-07T22:31:38.954674+00:00",
    "id": "955fda52-1347-4daa-a85e-4ac7c57248ad"
  },
  "answer": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "1aacdb03-4d38-4565-b593-e29e550b8f82",
    "skill": "listening",
    "cefr_level": "A1",
    "answer_json": {
      "value": "Café e água"
    },
    "is_correct": true,
    "raw_score": 1.0,
    "normalized_score": 1.0,
    "response_time_ms": 21278,
    "evaluated_by": "auto",
    "feedback_json": {},
    "created_at": "2026-10-07T22:32:00.377580+00:00",
    "id": "cd70a7c5-7fe0-4487-be94-50671497d85d"
  }
}
```

### Atividade 7 — fr-pre-a1-vg-01

```json
{
  "order": 7,
  "placement_item_id": "30b33211-ab56-4ef0-9c87-c6f559e2f5c2",
  "delivery_id": "53e00fb1-f6ec-47c6-a929-bf7b03f9823c",
  "item_type": "multiple_choice",
  "item_skill": "vocabulary_grammar",
  "answer_skill": "vocabulary_grammar",
  "skill_used_by_engine": "vocabulary_grammar",
  "modality_inferred_from_fields": "text",
  "has_text": true,
  "has_reading_passage": false,
  "has_audio_available": false,
  "has_voice_recording": false,
  "voice_payload_keys": [],
  "response_kind": "selected_value",
  "normalized_max_score": 1.0,
  "max_score_basis": "normalized_0_to_1_scale_not_a_persisted_answer_column",
  "entered_records": true,
  "records_exclusion_reason": null,
  "entered_candidate_skill_estimation": true,
  "skill_cefr_emitted": true,
  "skill_no_cefr_reason": null,
  "item_answer_skill_mismatch": false,
  "item_answer_cefr_mismatch": false,
  "item_language_mismatch": false,
  "item_updated_after_answer": false,
  "item": {
    "external_key": "fr-pre-a1-vg-01",
    "language_code": "fr",
    "cefr_level": "PRE_A1",
    "skill": "vocabulary_grammar",
    "item_type": "multiple_choice",
    "prompt": "Como se diz \"bom dia\" em francês?",
    "instructions": null,
    "passage": null,
    "options_json": [
      "Bonjour",
      "Bonne nuit",
      "Au revoir",
      "Merci"
    ],
    "correct_answer_json": {
      "value": "Bonjour"
    },
    "explanation": "\"Bonjour\" é a saudação usada durante o dia.",
    "audio_url": null,
    "audio_script": null,
    "rubric_json": {},
    "difficulty": 0.1,
    "discrimination": 1.0,
    "is_active": true,
    "version": 1,
    "source": "befluent_dev_seed",
    "license": "proprietary",
    "attribution": null,
    "source_ref": null,
    "review_status": "approved",
    "created_at": "2026-07-28T00:22:45.374677+00:00",
    "updated_at": "2026-07-28T00:22:45.374678+00:00",
    "id": "30b33211-ab56-4ef0-9c87-c6f559e2f5c2"
  },
  "delivery": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "30b33211-ab56-4ef0-9c87-c6f559e2f5c2",
    "delivered_at": "2026-10-07T22:32:00.612002+00:00",
    "expires_at": "2026-10-07T23:02:00.612007+00:00",
    "consumed_at": "2026-10-07T22:32:03.423671+00:00",
    "created_at": "2026-10-07T22:32:00.612536+00:00",
    "id": "53e00fb1-f6ec-47c6-a929-bf7b03f9823c"
  },
  "answer": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "30b33211-ab56-4ef0-9c87-c6f559e2f5c2",
    "skill": "vocabulary_grammar",
    "cefr_level": "PRE_A1",
    "answer_json": {
      "value": "Bonjour"
    },
    "is_correct": true,
    "raw_score": 1.0,
    "normalized_score": 1.0,
    "response_time_ms": 2698,
    "evaluated_by": "auto",
    "feedback_json": {},
    "created_at": "2026-10-07T22:32:03.439533+00:00",
    "id": "d9e8facf-1a0d-4418-98dc-0a6771b144ef"
  }
}
```

### Atividade 8 — fr-b1-rd-01

```json
{
  "order": 8,
  "placement_item_id": "7779c27f-c6d3-45fe-b1b2-c2d75a61ab3e",
  "delivery_id": "5d42a6a9-928c-4f0b-9768-912e5c95670d",
  "item_type": "reading_comprehension",
  "item_skill": "reading",
  "answer_skill": "reading",
  "skill_used_by_engine": "reading",
  "modality_inferred_from_fields": "text",
  "has_text": true,
  "has_reading_passage": true,
  "has_audio_available": false,
  "has_voice_recording": false,
  "voice_payload_keys": [],
  "response_kind": "selected_value",
  "normalized_max_score": 1.0,
  "max_score_basis": "normalized_0_to_1_scale_not_a_persisted_answer_column",
  "entered_records": true,
  "records_exclusion_reason": null,
  "entered_candidate_skill_estimation": true,
  "skill_cefr_emitted": false,
  "skill_no_cefr_reason": "no_band_meets_minimum_count_and_accuracy",
  "item_answer_skill_mismatch": false,
  "item_answer_cefr_mismatch": false,
  "item_language_mismatch": false,
  "item_updated_after_answer": false,
  "item": {
    "external_key": "fr-b1-rd-01",
    "language_code": "fr",
    "cefr_level": "B1",
    "skill": "reading",
    "item_type": "reading_comprehension",
    "prompt": "Qual é a principal preocupação mencionada?",
    "instructions": null,
    "passage": "Le télétravail s'est répandu dans de nombreuses entreprises. Si les salariés apprécient souvent la souplesse, les responsables craignent que la communication informelle entre collègues ne disparaisse.",
    "options_json": [
      "O desaparecimento da comunicação informal",
      "O custo dos escritórios",
      "A falta de equipamentos",
      "O aumento das viagens"
    ],
    "correct_answer_json": {
      "value": "O desaparecimento da comunicação informal"
    },
    "explanation": "O texto cita o temor de que a comunicação informal desapareça.",
    "audio_url": null,
    "audio_script": null,
    "rubric_json": {},
    "difficulty": 0.6,
    "discrimination": 1.0,
    "is_active": true,
    "version": 1,
    "source": "befluent_dev_seed",
    "license": "proprietary",
    "attribution": null,
    "source_ref": null,
    "review_status": "approved",
    "created_at": "2026-07-28T00:22:45.374772+00:00",
    "updated_at": "2026-07-28T00:22:45.374772+00:00",
    "id": "7779c27f-c6d3-45fe-b1b2-c2d75a61ab3e"
  },
  "delivery": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "7779c27f-c6d3-45fe-b1b2-c2d75a61ab3e",
    "delivered_at": "2026-10-07T22:32:03.658218+00:00",
    "expires_at": "2026-10-07T23:02:03.658224+00:00",
    "consumed_at": "2026-10-07T22:32:35.488532+00:00",
    "created_at": "2026-10-07T22:32:03.658958+00:00",
    "id": "5d42a6a9-928c-4f0b-9768-912e5c95670d"
  },
  "answer": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "7779c27f-c6d3-45fe-b1b2-c2d75a61ab3e",
    "skill": "reading",
    "cefr_level": "B1",
    "answer_json": {
      "value": "O desaparecimento da comunicação informal"
    },
    "is_correct": true,
    "raw_score": 1.0,
    "normalized_score": 1.0,
    "response_time_ms": 31326,
    "evaluated_by": "auto",
    "feedback_json": {},
    "created_at": "2026-10-07T22:32:35.495225+00:00",
    "id": "8800155f-58e4-4c07-85ef-63682e1e6c13"
  }
}
```

### Atividade 9 — fr-b1-ls-01

```json
{
  "order": 9,
  "placement_item_id": "418fbe0b-af20-420f-b948-45b6de32fe97",
  "delivery_id": "9ad56627-07aa-46b0-ab9f-0f65bea770f5",
  "item_type": "listening_comprehension",
  "item_skill": "listening",
  "answer_skill": "listening",
  "skill_used_by_engine": "listening",
  "modality_inferred_from_fields": "text_and_audio",
  "has_text": true,
  "has_reading_passage": false,
  "has_audio_available": true,
  "has_voice_recording": false,
  "voice_payload_keys": [],
  "response_kind": "selected_value",
  "normalized_max_score": 1.0,
  "max_score_basis": "normalized_0_to_1_scale_not_a_persisted_answer_column",
  "entered_records": true,
  "records_exclusion_reason": null,
  "entered_candidate_skill_estimation": true,
  "skill_cefr_emitted": false,
  "skill_no_cefr_reason": "no_band_meets_minimum_count_and_accuracy",
  "item_answer_skill_mismatch": false,
  "item_answer_cefr_mismatch": false,
  "item_language_mismatch": false,
  "item_updated_after_answer": false,
  "item": {
    "external_key": "fr-b1-ls-01",
    "language_code": "fr",
    "cefr_level": "B1",
    "skill": "listening",
    "item_type": "listening_comprehension",
    "prompt": "O que o falante recomenda?",
    "instructions": null,
    "passage": null,
    "options_json": [
      "Reservar o ingresso pela internet",
      "Ir durante a semana",
      "Chegar antes da abertura",
      "Evitar o museu no verão"
    ],
    "correct_answer_json": {
      "value": "Reservar o ingresso pela internet"
    },
    "explanation": "O falante recomenda \"réserver votre billet en ligne\".",
    "audio_url": null,
    "audio_script": "Si vous visitez le musée le week-end, je vous conseille vivement de réserver votre billet en ligne, car la file d'attente peut être très longue.",
    "rubric_json": {},
    "difficulty": 0.6,
    "discrimination": 1.0,
    "is_active": true,
    "version": 1,
    "source": "befluent_dev_seed",
    "license": "proprietary",
    "attribution": null,
    "source_ref": null,
    "review_status": "approved",
    "created_at": "2026-07-28T00:22:45.374780+00:00",
    "updated_at": "2026-07-28T00:22:45.374781+00:00",
    "id": "418fbe0b-af20-420f-b948-45b6de32fe97"
  },
  "delivery": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "418fbe0b-af20-420f-b948-45b6de32fe97",
    "delivered_at": "2026-10-07T22:32:35.593080+00:00",
    "expires_at": "2026-10-07T23:02:35.593085+00:00",
    "consumed_at": "2026-10-07T22:32:55.500081+00:00",
    "created_at": "2026-10-07T22:32:35.594807+00:00",
    "id": "9ad56627-07aa-46b0-ab9f-0f65bea770f5"
  },
  "answer": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "418fbe0b-af20-420f-b948-45b6de32fe97",
    "skill": "listening",
    "cefr_level": "B1",
    "answer_json": {
      "value": "Reservar o ingresso pela internet"
    },
    "is_correct": true,
    "raw_score": 1.0,
    "normalized_score": 1.0,
    "response_time_ms": 19810,
    "evaluated_by": "auto",
    "feedback_json": {},
    "created_at": "2026-10-07T22:32:55.504543+00:00",
    "id": "819230f4-1f90-4641-8e60-b03c7f0c9d2f"
  }
}
```

### Atividade 10 — fr-pre-a1-vg-02

```json
{
  "order": 10,
  "placement_item_id": "edc8afd6-e846-448a-a90e-6e3040ba9e77",
  "delivery_id": "4cb35921-be77-49ca-9016-5b3dc3d39857",
  "item_type": "multiple_choice",
  "item_skill": "vocabulary_grammar",
  "answer_skill": "vocabulary_grammar",
  "skill_used_by_engine": "vocabulary_grammar",
  "modality_inferred_from_fields": "text",
  "has_text": true,
  "has_reading_passage": false,
  "has_audio_available": false,
  "has_voice_recording": false,
  "voice_payload_keys": [],
  "response_kind": "selected_value",
  "normalized_max_score": 1.0,
  "max_score_basis": "normalized_0_to_1_scale_not_a_persisted_answer_column",
  "entered_records": true,
  "records_exclusion_reason": null,
  "entered_candidate_skill_estimation": true,
  "skill_cefr_emitted": true,
  "skill_no_cefr_reason": null,
  "item_answer_skill_mismatch": false,
  "item_answer_cefr_mismatch": false,
  "item_language_mismatch": false,
  "item_updated_after_answer": false,
  "item": {
    "external_key": "fr-pre-a1-vg-02",
    "language_code": "fr",
    "cefr_level": "PRE_A1",
    "skill": "vocabulary_grammar",
    "item_type": "multiple_choice",
    "prompt": "Complete: \"Je ___ Ana.\"",
    "instructions": null,
    "passage": null,
    "options_json": [
      "suis",
      "es",
      "est",
      "sommes"
    ],
    "correct_answer_json": {
      "value": "suis"
    },
    "explanation": "Com \"je\", o verbo \"être\" fica \"suis\".",
    "audio_url": null,
    "audio_script": null,
    "rubric_json": {},
    "difficulty": 0.12,
    "discrimination": 1.0,
    "is_active": true,
    "version": 1,
    "source": "befluent_dev_seed",
    "license": "proprietary",
    "attribution": null,
    "source_ref": null,
    "review_status": "approved",
    "created_at": "2026-07-28T00:22:45.374685+00:00",
    "updated_at": "2026-07-28T00:22:45.374686+00:00",
    "id": "edc8afd6-e846-448a-a90e-6e3040ba9e77"
  },
  "delivery": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "edc8afd6-e846-448a-a90e-6e3040ba9e77",
    "delivered_at": "2026-10-07T22:32:55.583997+00:00",
    "expires_at": "2026-10-07T23:02:55.584002+00:00",
    "consumed_at": "2026-10-07T22:32:59.713675+00:00",
    "created_at": "2026-10-07T22:32:55.584311+00:00",
    "id": "4cb35921-be77-49ca-9016-5b3dc3d39857"
  },
  "answer": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "edc8afd6-e846-448a-a90e-6e3040ba9e77",
    "skill": "vocabulary_grammar",
    "cefr_level": "PRE_A1",
    "answer_json": {
      "value": "suis"
    },
    "is_correct": true,
    "raw_score": 1.0,
    "normalized_score": 1.0,
    "response_time_ms": 4043,
    "evaluated_by": "auto",
    "feedback_json": {},
    "created_at": "2026-10-07T22:32:59.718949+00:00",
    "id": "4cebe1f2-bef9-42bb-8611-22661ee10431"
  }
}
```

### Atividade 11 — fr-b2-rd-01

```json
{
  "order": 11,
  "placement_item_id": "4046e878-0494-4970-8f2b-abb2433891ba",
  "delivery_id": "a629e362-0b79-46f3-92c5-f0811b266776",
  "item_type": "reading_comprehension",
  "item_skill": "reading",
  "answer_skill": "reading",
  "skill_used_by_engine": "reading",
  "modality_inferred_from_fields": "text",
  "has_text": true,
  "has_reading_passage": true,
  "has_audio_available": false,
  "has_voice_recording": false,
  "voice_payload_keys": [],
  "response_kind": "selected_value",
  "normalized_max_score": 1.0,
  "max_score_basis": "normalized_0_to_1_scale_not_a_persisted_answer_column",
  "entered_records": true,
  "records_exclusion_reason": null,
  "entered_candidate_skill_estimation": true,
  "skill_cefr_emitted": false,
  "skill_no_cefr_reason": "no_band_meets_minimum_count_and_accuracy",
  "item_answer_skill_mismatch": false,
  "item_answer_cefr_mismatch": false,
  "item_language_mismatch": false,
  "item_updated_after_answer": false,
  "item": {
    "external_key": "fr-b2-rd-01",
    "language_code": "fr",
    "cefr_level": "B2",
    "skill": "reading",
    "item_type": "reading_comprehension",
    "prompt": "Qual é a posição do autor?",
    "instructions": null,
    "passage": "Bien que l'automatisation ait supprimé certains postes, la présenter uniquement comme une menace revient à ignorer une constante historique : chaque vague technologique a fini par créer plus de métiers qu'elle n'en a détruits, malgré des transitions douloureuses.",
    "options_json": [
      "A automação tende a criar mais ocupações, apesar de transições difíceis",
      "A automação destrói empregos definitivamente",
      "A automação não afeta o emprego",
      "A automação deve ser proibida"
    ],
    "correct_answer_json": {
      "value": "A automação tende a criar mais ocupações, apesar de transições difíceis"
    },
    "explanation": "O autor reconhece perdas, mas defende que historicamente surgem mais ocupações.",
    "audio_url": null,
    "audio_script": null,
    "rubric_json": {},
    "difficulty": 0.78,
    "discrimination": 1.0,
    "is_active": true,
    "version": 1,
    "source": "befluent_dev_seed",
    "license": "proprietary",
    "attribution": null,
    "source_ref": null,
    "review_status": "approved",
    "created_at": "2026-07-28T00:22:45.374803+00:00",
    "updated_at": "2026-07-28T00:22:45.374804+00:00",
    "id": "4046e878-0494-4970-8f2b-abb2433891ba"
  },
  "delivery": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "4046e878-0494-4970-8f2b-abb2433891ba",
    "delivered_at": "2026-10-07T22:32:59.814976+00:00",
    "expires_at": "2026-10-07T23:02:59.814980+00:00",
    "consumed_at": "2026-10-07T22:33:10.301266+00:00",
    "created_at": "2026-10-07T22:32:59.815362+00:00",
    "id": "a629e362-0b79-46f3-92c5-f0811b266776"
  },
  "answer": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "4046e878-0494-4970-8f2b-abb2433891ba",
    "skill": "reading",
    "cefr_level": "B2",
    "answer_json": {
      "value": "A automação tende a criar mais ocupações, apesar de transições difíceis"
    },
    "is_correct": true,
    "raw_score": 1.0,
    "normalized_score": 1.0,
    "response_time_ms": 10320,
    "evaluated_by": "auto",
    "feedback_json": {},
    "created_at": "2026-10-07T22:33:10.306790+00:00",
    "id": "cd5c05fd-dd5c-44e5-a6f0-359a49030647"
  }
}
```

### Atividade 12 — fr-b2-ls-01

```json
{
  "order": 12,
  "placement_item_id": "b7b9ea78-7234-4652-9d8d-23ff93400a8f",
  "delivery_id": "92592453-b365-4829-b8c8-3de4580de52b",
  "item_type": "listening_comprehension",
  "item_skill": "listening",
  "answer_skill": "listening",
  "skill_used_by_engine": "listening",
  "modality_inferred_from_fields": "text_and_audio",
  "has_text": true,
  "has_reading_passage": false,
  "has_audio_available": true,
  "has_voice_recording": false,
  "voice_payload_keys": [],
  "response_kind": "selected_value",
  "normalized_max_score": 1.0,
  "max_score_basis": "normalized_0_to_1_scale_not_a_persisted_answer_column",
  "entered_records": true,
  "records_exclusion_reason": null,
  "entered_candidate_skill_estimation": true,
  "skill_cefr_emitted": false,
  "skill_no_cefr_reason": "no_band_meets_minimum_count_and_accuracy",
  "item_answer_skill_mismatch": false,
  "item_answer_cefr_mismatch": false,
  "item_language_mismatch": false,
  "item_updated_after_answer": false,
  "item": {
    "external_key": "fr-b2-ls-01",
    "language_code": "fr",
    "cefr_level": "B2",
    "skill": "listening",
    "item_type": "listening_comprehension",
    "prompt": "Qual é a atitude do falante?",
    "instructions": null,
    "passage": null,
    "options_json": [
      "Parcialmente favorável, com reservas sobre o orçamento",
      "Totalmente favorável",
      "Totalmente contrário",
      "Indiferente"
    ],
    "correct_answer_json": {
      "value": "Parcialmente favorável, com reservas sobre o orçamento"
    },
    "explanation": "Reconhece méritos, mas questiona as premissas orçamentárias.",
    "audio_url": null,
    "audio_script": "Je comprends l'intérêt de cette proposition, et certains points sont vraiment bien pensés, mais je ne suis pas convaincu que les hypothèses budgétaires tiennent la route.",
    "rubric_json": {},
    "difficulty": 0.8,
    "discrimination": 1.0,
    "is_active": true,
    "version": 1,
    "source": "befluent_dev_seed",
    "license": "proprietary",
    "attribution": null,
    "source_ref": null,
    "review_status": "approved",
    "created_at": "2026-07-28T00:22:45.374811+00:00",
    "updated_at": "2026-07-28T00:22:45.374812+00:00",
    "id": "b7b9ea78-7234-4652-9d8d-23ff93400a8f"
  },
  "delivery": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "b7b9ea78-7234-4652-9d8d-23ff93400a8f",
    "delivered_at": "2026-10-07T22:33:10.392168+00:00",
    "expires_at": "2026-10-07T23:03:10.392174+00:00",
    "consumed_at": "2026-10-07T22:33:35.068886+00:00",
    "created_at": "2026-10-07T22:33:10.392570+00:00",
    "id": "92592453-b365-4829-b8c8-3de4580de52b"
  },
  "answer": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "b7b9ea78-7234-4652-9d8d-23ff93400a8f",
    "skill": "listening",
    "cefr_level": "B2",
    "answer_json": {
      "value": "Parcialmente favorável, com reservas sobre o orçamento"
    },
    "is_correct": true,
    "raw_score": 1.0,
    "normalized_score": 1.0,
    "response_time_ms": 24569,
    "evaluated_by": "auto",
    "feedback_json": {},
    "created_at": "2026-10-07T22:33:35.075924+00:00",
    "id": "8596cdd3-b38f-4172-90ce-d36b373f23a6"
  }
}
```

### Atividade 13 — fr-b1-vg-02

```json
{
  "order": 13,
  "placement_item_id": "ecd7f9e2-f31e-4d67-bb58-9169dbce605f",
  "delivery_id": "97b3633b-76df-48e4-9f31-3ea08403d5bb",
  "item_type": "multiple_choice",
  "item_skill": "vocabulary_grammar",
  "answer_skill": "vocabulary_grammar",
  "skill_used_by_engine": "vocabulary_grammar",
  "modality_inferred_from_fields": "text",
  "has_text": true,
  "has_reading_passage": false,
  "has_audio_available": false,
  "has_voice_recording": false,
  "voice_payload_keys": [],
  "response_kind": "selected_value",
  "normalized_max_score": 1.0,
  "max_score_basis": "normalized_0_to_1_scale_not_a_persisted_answer_column",
  "entered_records": true,
  "records_exclusion_reason": null,
  "entered_candidate_skill_estimation": true,
  "skill_cefr_emitted": true,
  "skill_no_cefr_reason": null,
  "item_answer_skill_mismatch": false,
  "item_answer_cefr_mismatch": false,
  "item_language_mismatch": false,
  "item_updated_after_answer": false,
  "item": {
    "external_key": "fr-b1-vg-02",
    "language_code": "fr",
    "cefr_level": "B1",
    "skill": "vocabulary_grammar",
    "item_type": "multiple_choice",
    "prompt": "Qual expressão tem sentido próximo de \"abandonner\"?",
    "instructions": null,
    "passage": null,
    "options_json": [
      "renoncer",
      "continuer",
      "améliorer",
      "commencer"
    ],
    "correct_answer_json": {
      "value": "renoncer"
    },
    "explanation": "\"Abandonner\" significa desistir, equivalente a \"renoncer\".",
    "audio_url": null,
    "audio_script": null,
    "rubric_json": {},
    "difficulty": 0.52,
    "discrimination": 1.0,
    "is_active": true,
    "version": 1,
    "source": "befluent_dev_seed",
    "license": "proprietary",
    "attribution": null,
    "source_ref": null,
    "review_status": "approved",
    "created_at": "2026-07-28T00:22:45.374764+00:00",
    "updated_at": "2026-07-28T00:22:45.374765+00:00",
    "id": "ecd7f9e2-f31e-4d67-bb58-9169dbce605f"
  },
  "delivery": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "ecd7f9e2-f31e-4d67-bb58-9169dbce605f",
    "delivered_at": "2026-10-07T22:33:35.167332+00:00",
    "expires_at": "2026-10-07T23:03:35.167336+00:00",
    "consumed_at": "2026-10-07T22:33:42.083773+00:00",
    "created_at": "2026-10-07T22:33:35.167980+00:00",
    "id": "97b3633b-76df-48e4-9f31-3ea08403d5bb"
  },
  "answer": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "ecd7f9e2-f31e-4d67-bb58-9169dbce605f",
    "skill": "vocabulary_grammar",
    "cefr_level": "B1",
    "answer_json": {
      "value": "renoncer"
    },
    "is_correct": true,
    "raw_score": 1.0,
    "normalized_score": 1.0,
    "response_time_ms": 6808,
    "evaluated_by": "auto",
    "feedback_json": {},
    "created_at": "2026-10-07T22:33:42.088148+00:00",
    "id": "1ae28495-16e0-4284-8034-a6e737c41e98"
  }
}
```

### Atividade 14 — fr-b1-vg-01

```json
{
  "order": 14,
  "placement_item_id": "c6b6b810-568e-40bb-9204-3ecfeb3de169",
  "delivery_id": "e59303a6-aee2-492b-98bb-2dc9ba716462",
  "item_type": "multiple_choice",
  "item_skill": "vocabulary_grammar",
  "answer_skill": "vocabulary_grammar",
  "skill_used_by_engine": "vocabulary_grammar",
  "modality_inferred_from_fields": "text",
  "has_text": true,
  "has_reading_passage": false,
  "has_audio_available": false,
  "has_voice_recording": false,
  "voice_payload_keys": [],
  "response_kind": "selected_value",
  "normalized_max_score": 1.0,
  "max_score_basis": "normalized_0_to_1_scale_not_a_persisted_answer_column",
  "entered_records": true,
  "records_exclusion_reason": null,
  "entered_candidate_skill_estimation": true,
  "skill_cefr_emitted": true,
  "skill_no_cefr_reason": null,
  "item_answer_skill_mismatch": false,
  "item_answer_cefr_mismatch": false,
  "item_language_mismatch": false,
  "item_updated_after_answer": false,
  "item": {
    "external_key": "fr-b1-vg-01",
    "language_code": "fr",
    "cefr_level": "B1",
    "skill": "vocabulary_grammar",
    "item_type": "multiple_choice",
    "prompt": "Complete: \"Si j'___ plus de temps, je voyagerais davantage.\"",
    "instructions": null,
    "passage": null,
    "options_json": [
      "avais",
      "ai",
      "aurai",
      "aurais"
    ],
    "correct_answer_json": {
      "value": "avais"
    },
    "explanation": "Condicional irreal: \"si\" + imparfait, seguido do conditionnel.",
    "audio_url": null,
    "audio_script": null,
    "rubric_json": {},
    "difficulty": 0.56,
    "discrimination": 1.0,
    "is_active": true,
    "version": 1,
    "source": "befluent_dev_seed",
    "license": "proprietary",
    "attribution": null,
    "source_ref": null,
    "review_status": "approved",
    "created_at": "2026-07-28T00:22:45.374755+00:00",
    "updated_at": "2026-07-28T00:22:45.374756+00:00",
    "id": "c6b6b810-568e-40bb-9204-3ecfeb3de169"
  },
  "delivery": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "c6b6b810-568e-40bb-9204-3ecfeb3de169",
    "delivered_at": "2026-10-07T22:33:42.191376+00:00",
    "expires_at": "2026-10-07T23:03:42.191380+00:00",
    "consumed_at": "2026-10-07T22:33:49.904298+00:00",
    "created_at": "2026-10-07T22:33:42.191952+00:00",
    "id": "e59303a6-aee2-492b-98bb-2dc9ba716462"
  },
  "answer": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "c6b6b810-568e-40bb-9204-3ecfeb3de169",
    "skill": "vocabulary_grammar",
    "cefr_level": "B1",
    "answer_json": {
      "value": "avais"
    },
    "is_correct": true,
    "raw_score": 1.0,
    "normalized_score": 1.0,
    "response_time_ms": 7648,
    "evaluated_by": "auto",
    "feedback_json": {},
    "created_at": "2026-10-07T22:33:49.909415+00:00",
    "id": "2df681b8-722b-480b-ba79-bbbf30930168"
  }
}
```

### Atividade 15 — fr-b2-vg-01

```json
{
  "order": 15,
  "placement_item_id": "434ade8b-9ff4-445c-8132-fe3339133f71",
  "delivery_id": "21cddb96-adee-45a1-8dcf-a12f7cef183f",
  "item_type": "multiple_choice",
  "item_skill": "vocabulary_grammar",
  "answer_skill": "vocabulary_grammar",
  "skill_used_by_engine": "vocabulary_grammar",
  "modality_inferred_from_fields": "text",
  "has_text": true,
  "has_reading_passage": false,
  "has_audio_available": false,
  "has_voice_recording": false,
  "voice_payload_keys": [],
  "response_kind": "selected_value",
  "normalized_max_score": 1.0,
  "max_score_basis": "normalized_0_to_1_scale_not_a_persisted_answer_column",
  "entered_records": true,
  "records_exclusion_reason": null,
  "entered_candidate_skill_estimation": true,
  "skill_cefr_emitted": true,
  "skill_no_cefr_reason": null,
  "item_answer_skill_mismatch": false,
  "item_answer_cefr_mismatch": false,
  "item_language_mismatch": false,
  "item_updated_after_answer": false,
  "item": {
    "external_key": "fr-b2-vg-01",
    "language_code": "fr",
    "cefr_level": "B2",
    "skill": "vocabulary_grammar",
    "item_type": "multiple_choice",
    "prompt": "Complete: \"Quand nous sommes arrivés, la réunion ___ déjà commencé.\"",
    "instructions": null,
    "passage": null,
    "options_json": [
      "avait",
      "a",
      "aura",
      "aurait"
    ],
    "correct_answer_json": {
      "value": "avait"
    },
    "explanation": "Ação anterior a outra no passado exige o plus-que-parfait.",
    "audio_url": null,
    "audio_script": null,
    "rubric_json": {},
    "difficulty": 0.72,
    "discrimination": 1.0,
    "is_active": true,
    "version": 1,
    "source": "befluent_dev_seed",
    "license": "proprietary",
    "attribution": null,
    "source_ref": null,
    "review_status": "approved",
    "created_at": "2026-07-28T00:22:45.374787+00:00",
    "updated_at": "2026-07-28T00:22:45.374788+00:00",
    "id": "434ade8b-9ff4-445c-8132-fe3339133f71"
  },
  "delivery": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "434ade8b-9ff4-445c-8132-fe3339133f71",
    "delivered_at": "2026-10-07T22:33:49.995891+00:00",
    "expires_at": "2026-10-07T23:03:49.995895+00:00",
    "consumed_at": "2026-10-07T22:33:59.642227+00:00",
    "created_at": "2026-10-07T22:33:49.996246+00:00",
    "id": "21cddb96-adee-45a1-8dcf-a12f7cef183f"
  },
  "answer": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "434ade8b-9ff4-445c-8132-fe3339133f71",
    "skill": "vocabulary_grammar",
    "cefr_level": "B2",
    "answer_json": {
      "value": "avait"
    },
    "is_correct": true,
    "raw_score": 1.0,
    "normalized_score": 1.0,
    "response_time_ms": 9536,
    "evaluated_by": "auto",
    "feedback_json": {},
    "created_at": "2026-10-07T22:33:59.650862+00:00",
    "id": "8c0241fa-5c1b-4e68-bd3f-96e1bf5e3b67"
  }
}
```

### Atividade 16 — fr-b2-vg-02

```json
{
  "order": 16,
  "placement_item_id": "ca0c86bd-8747-4b2a-8505-87fb902acd2d",
  "delivery_id": "34e9ab30-114b-457e-ab05-d8ee7b98731f",
  "item_type": "multiple_choice",
  "item_skill": "vocabulary_grammar",
  "answer_skill": "vocabulary_grammar",
  "skill_used_by_engine": "vocabulary_grammar",
  "modality_inferred_from_fields": "text",
  "has_text": true,
  "has_reading_passage": false,
  "has_audio_available": false,
  "has_voice_recording": false,
  "voice_payload_keys": [],
  "response_kind": "selected_value",
  "normalized_max_score": 1.0,
  "max_score_basis": "normalized_0_to_1_scale_not_a_persisted_answer_column",
  "entered_records": true,
  "records_exclusion_reason": null,
  "entered_candidate_skill_estimation": true,
  "skill_cefr_emitted": true,
  "skill_no_cefr_reason": null,
  "item_answer_skill_mismatch": false,
  "item_answer_cefr_mismatch": false,
  "item_language_mismatch": false,
  "item_updated_after_answer": false,
  "item": {
    "external_key": "fr-b2-vg-02",
    "language_code": "fr",
    "cefr_level": "B2",
    "skill": "vocabulary_grammar",
    "item_type": "multiple_choice",
    "prompt": "Escolha a opção correta: \"Il faut que tu ___ présent demain.\"",
    "instructions": null,
    "passage": null,
    "options_json": [
      "sois",
      "es",
      "seras",
      "étais"
    ],
    "correct_answer_json": {
      "value": "sois"
    },
    "explanation": "\"Il faut que\" exige subjuntivo: \"sois\".",
    "audio_url": null,
    "audio_script": null,
    "rubric_json": {},
    "difficulty": 0.74,
    "discrimination": 1.0,
    "is_active": true,
    "version": 1,
    "source": "befluent_dev_seed",
    "license": "proprietary",
    "attribution": null,
    "source_ref": null,
    "review_status": "approved",
    "created_at": "2026-07-28T00:22:45.374795+00:00",
    "updated_at": "2026-07-28T00:22:45.374796+00:00",
    "id": "ca0c86bd-8747-4b2a-8505-87fb902acd2d"
  },
  "delivery": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "ca0c86bd-8747-4b2a-8505-87fb902acd2d",
    "delivered_at": "2026-10-07T22:33:59.812327+00:00",
    "expires_at": "2026-10-07T23:03:59.812333+00:00",
    "consumed_at": "2026-10-07T22:34:06.927172+00:00",
    "created_at": "2026-10-07T22:33:59.813346+00:00",
    "id": "34e9ab30-114b-457e-ab05-d8ee7b98731f"
  },
  "answer": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "ca0c86bd-8747-4b2a-8505-87fb902acd2d",
    "skill": "vocabulary_grammar",
    "cefr_level": "B2",
    "answer_json": {
      "value": "étais"
    },
    "is_correct": false,
    "raw_score": 0.0,
    "normalized_score": 0.0,
    "response_time_ms": 6961,
    "evaluated_by": "auto",
    "feedback_json": {},
    "created_at": "2026-10-07T22:34:06.935494+00:00",
    "id": "09822c6d-9ace-4704-a69a-7d854b98c71b"
  }
}
```

### Atividade 17 — fr-b1-wr-01

```json
{
  "order": 17,
  "placement_item_id": "ad4e53d2-7ee5-4eff-837d-c79d5de4efd2",
  "delivery_id": "a76e036b-ca04-47ff-b411-0e1c04e68a4d",
  "item_type": "short_writing",
  "item_skill": "writing",
  "answer_skill": "writing",
  "skill_used_by_engine": null,
  "modality_inferred_from_fields": "text",
  "has_text": true,
  "has_reading_passage": false,
  "has_audio_available": false,
  "has_voice_recording": false,
  "voice_payload_keys": [],
  "response_kind": "writing_text",
  "normalized_max_score": 1.0,
  "max_score_basis": "normalized_0_to_1_scale_not_a_persisted_answer_column",
  "entered_records": false,
  "records_exclusion_reason": "production_skill_excluded_by_records",
  "entered_candidate_skill_estimation": false,
  "skill_cefr_emitted": false,
  "skill_no_cefr_reason": "production_skill_excluded_by_records_and_skill_results",
  "item_answer_skill_mismatch": false,
  "item_answer_cefr_mismatch": false,
  "item_language_mismatch": false,
  "item_updated_after_answer": false,
  "item": {
    "external_key": "fr-b1-wr-01",
    "language_code": "fr",
    "cefr_level": "B1",
    "skill": "writing",
    "item_type": "short_writing",
    "prompt": "Conte, em francês, uma experiência importante da sua vida e explique por que ela foi marcante.",
    "instructions": "Escreva em francês. Entre 60 e 900 caracteres.",
    "passage": null,
    "options_json": [],
    "correct_answer_json": {},
    "explanation": null,
    "audio_url": null,
    "audio_script": null,
    "rubric_json": {
      "criteria": [
        "adequação ao tema",
        "coerência",
        "vocabulário",
        "gramática",
        "clareza",
        "organização"
      ],
      "target_level": "B1",
      "min_chars": 60
    },
    "difficulty": 0.6,
    "discrimination": 1.0,
    "is_active": true,
    "version": 1,
    "source": "befluent_dev_seed",
    "license": "proprietary",
    "attribution": null,
    "source_ref": null,
    "review_status": "approved",
    "created_at": "2026-07-28T00:22:45.374847+00:00",
    "updated_at": "2026-07-28T00:22:45.374849+00:00",
    "id": "ad4e53d2-7ee5-4eff-837d-c79d5de4efd2"
  },
  "delivery": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "ad4e53d2-7ee5-4eff-837d-c79d5de4efd2",
    "delivered_at": "2026-10-07T22:34:07.064916+00:00",
    "expires_at": "2026-10-07T23:04:07.064920+00:00",
    "consumed_at": "2026-10-07T22:35:18.304270+00:00",
    "created_at": "2026-10-07T22:34:07.065202+00:00",
    "id": "a76e036b-ca04-47ff-b411-0e1c04e68a4d"
  },
  "answer": {
    "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
    "item_id": "ad4e53d2-7ee5-4eff-837d-c79d5de4efd2",
    "skill": "writing",
    "cefr_level": "B1",
    "answer_json": {
      "text": "Une expérience qui a profondément marqué ma vie s'est produite il y a quelques années, alors que je traversais une période de travail intense. Depuis mon plus jeune âge, ma vie était dictée par une discipline de fer, entièrement tournée vers les études, la performance et la réussite professionnelle. Je pensais que si je travaillais assez dur, je pourrais tout contrôler et tout planifier.\nCependant, tout a basculé lorsque mon père est tombé gravement malade.\nDu jour au lendemain, mes priorités ont été complètement bouleversées. Les journées de travail interminables ont été remplacées par de longues heures d'attente à l'hôpital. Face à cette situation, j'ai développé une immense anxiété. Pour la première fois de ma vie, mon travail et mes efforts ne pouvaient rien résoudre. Je me sentais totalement impuissant face à la maladie d'un être cher.\nCette expérience a été un tournant majeur pour deux raisons fondamentales :\nD'abord, elle m'a appris la résilience et l'importance de lâcher prise. J'ai compris que nous ne pouvons pas tout contrôler, et que l'anxiété naît souvent de notre refus d'accepter cette incertitude. J'ai dû apprendre à vivre un jour à la fois, en me concentrant uniquement sur ce que je pouvais faire à mon humble niveau : être présent, offrir du soutien et de l'amour.\nEnsuite, cela a redéfini ma vision de la réussite. Le travail et les études sont essentiels pour se réaliser, mais la santé et les moments passés avec les gens que nous aimons sont les seules choses qui ont une valeur absolue."
    },
    "is_correct": null,
    "raw_score": 0.96,
    "normalized_score": 0.96,
    "response_time_ms": 70720,
    "evaluated_by": "ai",
    "feedback_json": {
      "status": "assessed",
      "evaluated_by": "ai",
      "normalized_score": 0.96,
      "target_level": "B1",
      "estimated_level": "B1",
      "criteria": {
        "adequacao_ao_tema": 0.95,
        "coerencia": 0.96,
        "clareza": 0.96
      },
      "feedback": "Texte très bien structuré, avec un vocabulaire riche et une grammaire quasi sans faute. La narration est cohérente, claire et bien organisée, ce qui indique un niveau supérieur au B1 visé (environ B2)."
    },
    "created_at": "2026-10-07T22:36:19.966083+00:00",
    "id": "7e8009b1-c167-40a7-a9cd-ea3248bf4767"
  }
}
```

### Sections finais e UserLanguage

```json
{
  "sections": [
    {
      "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
      "skill": "vocabulary_grammar",
      "score": 5.0,
      "max_score": 8.0,
      "estimated_level": "B1",
      "confidence_score": null,
      "status": "assessed",
      "completed_at": "2026-10-07T23:42:48.363144+00:00",
      "id": "55de95c5-1158-4257-bf2b-e44087bd65cd"
    },
    {
      "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
      "skill": "listening",
      "score": 0.0,
      "max_score": 0.0,
      "estimated_level": null,
      "confidence_score": null,
      "status": "not_assessed",
      "completed_at": null,
      "id": "6ab26f9b-dad4-4c4b-88c0-3ad4ba957160"
    },
    {
      "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
      "skill": "reading",
      "score": 0.0,
      "max_score": 0.0,
      "estimated_level": null,
      "confidence_score": null,
      "status": "not_assessed",
      "completed_at": null,
      "id": "3acf4938-daa3-4092-9374-9e8284be60bd"
    },
    {
      "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
      "skill": "speaking",
      "score": 0.0,
      "max_score": 0.0,
      "estimated_level": null,
      "confidence_score": null,
      "status": "not_available",
      "completed_at": null,
      "id": "41ce745d-646d-459e-9651-a200050e9dab"
    },
    {
      "test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
      "skill": "writing",
      "score": 0.96,
      "max_score": 1.0,
      "estimated_level": null,
      "confidence_score": null,
      "status": "calibrating",
      "completed_at": "2026-10-07T22:36:19.966083+00:00",
      "id": "840f9195-a9ef-44be-9438-fadf1e1d9596"
    }
  ],
  "user_language": [
    {
      "user_id": "899068d6-d2b2-4fa8-91fc-7e773a453807",
      "language_id": "beef9c05-1cf6-4972-a116-1a4092e95889",
      "level_estimate": "B1",
      "onboarding_completed": true,
      "diagnostic_completed": true,
      "is_active": true,
      "started_at": "2026-10-07T22:30:04.108549+00:00",
      "updated_at": "2026-10-07T23:42:48.421893+00:00",
      "current_level": "B1",
      "level_source": "placement_test",
      "level_assessed_at": "2026-10-07T23:42:48.363144+00:00",
      "placement_test_id": "14110779-3cc4-4c2c-b66d-4aa8a5aa7a2e",
      "vocabulary_grammar_level": "B1",
      "reading_level": null,
      "listening_level": null,
      "writing_level": null,
      "speaking_level": null,
      "confidence_score": 45.0,
      "recommendations_json": [
        {
          "skill": "reading",
          "reason": "insufficient_evidence",
          "priority": 1,
          "href": "/learn"
        },
        {
          "skill": "listening",
          "reason": "insufficient_evidence",
          "priority": 1,
          "href": "/learn"
        },
        {
          "skill": "vocabulary_grammar",
          "reason": "lowest_accuracy",
          "priority": 2,
          "href": "/learn"
        }
      ],
      "id": "fc0fd0db-865e-4259-8367-54eb18db29e0"
    }
  ],
  "source_sha256": {
    "app/api/placement_tests.py": "5e518731c11b50d5afc790fbad49504e7d254e8c20a60f4169c3951998836503",
    "app/services/placement_engine.py": "887767a62ad24b8835437cfa75d448411a0702d91e7b94eb92d210ee7be4f105",
    "app/services/writing_evaluation.py": "53138de2dbfaabe80c1b688966521411d0dc40cbae03387780d803fa4e9098f5",
    "app/services/placement_delivery.py": "ee1b42106e46b73cacf198a50d6a77915b7784ac6289ec795789af019b9eecf9",
    "app/core/levels.py": "1bdf8b0f37e340cf14ff6603cc6b0cd9dfb5b1e63d83628d68cccd5d10397d13",
    "scripts/audit_placement_result.py": "3128b0470169a29da3ea3af623c637fac5909c92b990eeeed348112b81e40286"
  }
}
```
