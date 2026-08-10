# Auditoria — Currículo 90 jornadas · entrada B2 (EN)

**Modo:** diagnóstico somente (SQLite em memória). Sem alteração em produção.
**Gerado em:** script `backend/scripts/audit_curriculum_b2_90.py`
**Premissa:** placement B2 em todas as competências; duração 90; idioma `en`.
**Conteúdo lexical simulado:** `MockAIProvider` + `lesson_bank` (estado atual sem OpenRouter ativo).

## Classificação: **A** — Progressão adequada

## 0. Resumo executivo

- Jornadas: **90** | Semanas: **13** | Blocos: **453**
- Entry → target: **B2 → B2**
- Estágios de nível: [(<CEFRLevel.B2: 'B2'>, 13)]
- Temas únicos nas 90 jornadas: **10** (tema semanal compartilhado por ~7 dias)
- Itens léxicos no banco UPPER (B2): **80** — com tags de tema
- Itens únicos observados na simulação mock: **80**
- Ocorrências totais de termos (soma dias×itens): **80**
- Sobreposição média Dia N ∩ Dia N+1 (Jaccard): **0%**
- Primeiras exposições (soma `items` novos): **80**
- Revisitações spirais (soma `revisited_items`): **267**
- Média de exposições por termo (new+revisited): **4.34**
- Violações new←já-exposto: **0**
- Semana 1 blocos com `objective_id`: **28/35**
- Semana 1 Can-Dos: **['EN-B2-CAN-001', 'EN-B2-CAN-002', 'EN-B2-CAN-003', 'EN-B2-CAN-004', 'EN-B2-CAN-005', 'EN-B2-CAN-006', 'EN-B2-CAN-007']**
- Blocos com `objective_id` (Teaching Engine): **100/453** (22.1%)
- Objetivos LearningObjective no banco: **18** (['EN-A1-CAN-001', 'EN-B2-CAN-001', 'EN-B2-CAN-002', 'EN-B2-CAN-003', 'EN-B2-CAN-004', 'EN-B2-CAN-005', 'EN-B2-CAN-006', 'EN-B2-CAN-007', 'EN-B2-TH-NEGOCIACAO-E-MERCADO-DE-', 'EN-B2-TH-CIENCIA-DADOS-E-EVIDENCI', 'EN-B2-TH-MIDIA-FONTES-E-DESINFORM', 'EN-B2-TH-SOCIEDADE-E-POLITICAS-PU']…)
- Dias com sequência de fases Activate→…→Consolidate coerente: **78/90**

### Separação A / B / C (não misturar)

| Tipo | O que é neste currículo |
|---|---|
| **A. Conteúdo novo** | `select_daily_vocabulary` devolve ~5 itens novos/dia do pool temático da semana (`items` + `content_roles.items=new`). |
| **B. Carryover / spiral** | **Dentro do dia:** `lesson_thread`. **Entre dias:** `revisited_items` (spiral). |
| **C. SRS temporal** | Bloco `review` consome `ReviewItem` com `next_review_at <= agora`. Independente do tema semanal. |

## 1. Mapa das 90 jornadas (resumo por semana)

### Semana 1 · Argumentar e refutar · CEFR B2

| Dia | Blocos (skills) | Vocab simulado (mock) |
|---|---|---|
| 1 | vocabulary → grammar → pronunciation → listening → conversation → review | a compelling argument, a slippery slope, by and large, for the sake of argument, … |
| 2 | vocabulary → grammar → reading → writing → review | on the contrary, the crux of the matter, to account for, to back up, … |
| 3 | vocabulary → grammar → pronunciation → listening → conversation → review | to bring about, to call into question, to concede that, to hold that, … |
| 4 | vocabulary → grammar → reading → writing → review | to rebut, to stand by |
| 5 | vocabulary → grammar → pronunciation → listening → conversation → review |  |
| 6 | vocabulary → grammar → reading → writing → review |  |
| 7 | reading → review |  |

### Semana 2 · Negociação e mercado de trabalho · CEFR B2 · **CHECKPOINT**

| Dia | Blocos (skills) | Vocab simulado (mock) |
|---|---|---|
| 8 | vocabulary → grammar → pronunciation → reading → writing → review | a sticking point, for the time being, in good faith, leverage, … |
| 9 | vocabulary → grammar → listening → conversation → review | to bargain for, to meet halfway, to push back against, to settle for, … |
| 10 | vocabulary → grammar → pronunciation → reading → writing → review |  |
| 11 | vocabulary → grammar → listening → conversation → review |  |
| 12 | vocabulary → grammar → pronunciation → reading → writing → review |  |
| 13 | vocabulary → grammar → listening → conversation → review |  |
| 14 | reading → review |  |

### Semana 3 · Ciência, dados e evidência · CEFR B2

| Dia | Blocos (skills) | Vocab simulado (mock) |
|---|---|---|
| 15 | vocabulary → grammar → pronunciation → listening → conversation → review | a confounding factor, a primary source, a trade-off, a working hypothesis, … |
| 16 | vocabulary → grammar → reading → writing → review | peer-reviewed, statistically significant, to bear out, to control for, … |
| 17 | vocabulary → grammar → pronunciation → listening → conversation → review | to shed light on |
| 18 | vocabulary → grammar → reading → writing → review |  |
| 19 | vocabulary → grammar → pronunciation → listening → conversation → review |  |
| 20 | vocabulary → grammar → reading → writing → review |  |
| 21 | reading → review |  |

### Semana 4 · Mídia, fontes e desinformação · CEFR B2 · **CHECKPOINT**

| Dia | Blocos (skills) | Vocab simulado (mock) |
|---|---|---|
| 22 | vocabulary → grammar → pronunciation → reading → writing → review | biased coverage, clickbait, echo chamber, out of touch, … |
| 23 | vocabulary → grammar → listening → conversation → review | to go viral, to take with a grain of salt, to verify |
| 24 | vocabulary → grammar → pronunciation → reading → writing → review |  |
| 25 | vocabulary → grammar → listening → conversation → review |  |
| 26 | vocabulary → grammar → pronunciation → reading → writing → review |  |
| 27 | vocabulary → grammar → listening → conversation → review |  |
| 28 | reading → review |  |

### Semana 5 · Sociedade e políticas públicas · CEFR B2

| Dia | Blocos (skills) | Vocab simulado (mock) |
|---|---|---|
| 29 | vocabulary → grammar → pronunciation → listening → conversation → review | a safety net, grassroots, public interest, social mobility, … |
| 30 | vocabulary → grammar → reading → writing → review | to phase out, to roll out, unintended consequences |
| 31 | vocabulary → grammar → pronunciation → listening → conversation → review |  |
| 32 | vocabulary → grammar → reading → writing → review |  |
| 33 | vocabulary → grammar → pronunciation → listening → conversation → review |  |
| 34 | vocabulary → grammar → reading → writing → review |  |
| 35 | reading → review |  |

### Semana 6 · Ética e dilemas · CEFR B2 · **CHECKPOINT**

| Dia | Blocos (skills) | Vocab simulado (mock) |
|---|---|---|
| 36 | vocabulary → grammar → pronunciation → reading → writing → review | informed consent, the status quo, to draw the line, to turn a blind eye |
| 37 | vocabulary → grammar → listening → conversation → review |  |
| 38 | vocabulary → grammar → pronunciation → reading → writing → review |  |
| 39 | vocabulary → grammar → listening → conversation → review |  |
| 40 | vocabulary → grammar → pronunciation → reading → writing → review |  |
| 41 | vocabulary → grammar → listening → conversation → review |  |
| 42 | reading → review |  |

### Semana 7 · Economia pessoal e global · CEFR B2

| Dia | Blocos (skills) | Vocab simulado (mock) |
|---|---|---|
| 43 | vocabulary → grammar → pronunciation → listening → conversation → review | a downturn, purchasing power, supply chain, to break even, … |
| 44 | vocabulary → grammar → reading → writing → review | to hedge against, to write off |
| 45 | vocabulary → grammar → pronunciation → listening → conversation → review |  |
| 46 | vocabulary → grammar → reading → writing → review |  |
| 47 | vocabulary → grammar → pronunciation → listening → conversation → review |  |
| 48 | vocabulary → grammar → reading → writing → review |  |
| 49 | reading → review |  |

### Semana 8 · Arte, crítica e interpretação · CEFR B2 · **CHECKPOINT**

| Dia | Blocos (skills) | Vocab simulado (mock) |
|---|---|---|
| 50 | vocabulary → grammar → pronunciation → reading → writing → review | a nuanced reading, derivative, to convey, to fall flat, … |
| 51 | vocabulary → grammar → listening → conversation → review | understated |
| 52 | vocabulary → grammar → pronunciation → reading → writing → review |  |
| 53 | vocabulary → grammar → listening → conversation → review |  |
| 54 | vocabulary → grammar → pronunciation → reading → writing → review |  |
| 55 | vocabulary → grammar → listening → conversation → review |  |
| 56 | reading → review |  |

### Semana 9 · Mudanças sociais e gerações · CEFR B2

| Dia | Blocos (skills) | Vocab simulado (mock) |
|---|---|---|
| 57 | vocabulary → grammar → pronunciation → listening → conversation → review | a generational shift, to bridge the gap, to catch on, to come of age |
| 58 | vocabulary → grammar → reading → writing → review |  |
| 59 | vocabulary → grammar → pronunciation → listening → conversation → review |  |
| 60 | vocabulary → grammar → reading → writing → review |  |
| 61 | vocabulary → grammar → pronunciation → listening → conversation → review |  |
| 62 | vocabulary → grammar → reading → writing → review |  |
| 63 | reading → review |  |

### Semana 10 · Apresentar e defender uma ideia · CEFR B2 · **CHECKPOINT**

| Dia | Blocos (skills) | Vocab simulado (mock) |
|---|---|---|
| 64 | vocabulary → grammar → pronunciation → reading → writing → review | in a nutshell, to boil down to, to flesh out, to put forward, … |
| 65 | vocabulary → grammar → listening → conversation → review |  |
| 66 | vocabulary → grammar → pronunciation → reading → writing → review |  |
| 67 | vocabulary → grammar → listening → conversation → review |  |
| 68 | vocabulary → grammar → pronunciation → reading → writing → review |  |
| 69 | vocabulary → grammar → listening → conversation → review |  |
| 70 | reading → review |  |

### Semana 11 · Argumentar e refutar · CEFR B2

| Dia | Blocos (skills) | Vocab simulado (mock) |
|---|---|---|
| 71 | vocabulary → grammar → pronunciation → listening → conversation → review |  |
| 72 | vocabulary → grammar → reading → writing → review |  |
| 73 | vocabulary → grammar → pronunciation → listening → conversation → review |  |
| 74 | vocabulary → grammar → reading → writing → review |  |
| 75 | vocabulary → grammar → pronunciation → listening → conversation → review |  |
| 76 | vocabulary → grammar → reading → writing → review |  |
| 77 | reading → review |  |

### Semana 12 · Negociação e mercado de trabalho · CEFR B2 · **CHECKPOINT**

| Dia | Blocos (skills) | Vocab simulado (mock) |
|---|---|---|
| 78 | vocabulary → grammar → pronunciation → reading → writing → review |  |
| 79 | vocabulary → grammar → listening → conversation → review |  |
| 80 | vocabulary → grammar → pronunciation → reading → writing → review |  |
| 81 | vocabulary → grammar → listening → conversation → review |  |
| 82 | vocabulary → grammar → pronunciation → reading → writing → review |  |
| 83 | vocabulary → grammar → listening → conversation → review |  |
| 84 | reading → review |  |

### Semana 13 · Ciência, dados e evidência · CEFR B2

| Dia | Blocos (skills) | Vocab simulado (mock) |
|---|---|---|
| 85 | vocabulary → grammar → pronunciation → listening → conversation → review |  |
| 86 | vocabulary → grammar → reading → writing → review |  |
| 87 | vocabulary → grammar → pronunciation → listening → conversation → review |  |
| 88 | vocabulary → grammar → reading → writing → review |  |
| 89 | vocabulary → grammar → pronunciation → listening → conversation → review |  |
| 90 | vocabulary → grammar → reading → writing → review |  |

## 2. Progressão pedagógica

### Cada dia tem objetivo específico?

**Não.** `CurriculumDay` não possui can-do/objetivo próprio. Só herda o **tema semanal** (`CurriculumWeek.theme`) e cada bloco tem `topic` = ângulo do skill + tema (ex.: “Argumentar e refutar — vocabulário essencial”).

### Vários dias usam o mesmo tema semanal?

**Sim.** Em média **9.0** jornadas por tema. Distribuição: {'Argumentar e refutar': 14, 'Negociação e mercado de trabalho': 14, 'Ciência, dados e evidência': 13, 'Mídia, fontes e desinformação': 7, 'Sociedade e políticas públicas': 7, 'Ética e dilemas': 7, 'Economia pessoal e global': 7, 'Arte, crítica e interpretação': 7, 'Mudanças sociais e gerações': 7, 'Apresentar e defender uma ideia': 7}.

### Dia N ensina algo novo vs Dia N-1?

No léxico mock B2: overlap médio consecutivo **0%**. Com banco de 80 itens e `_rotate` por `day_number`, o Dia N quase sempre contém **o mesmo conjunto** que o Dia N-1, apenas reordenado. Isso **não** é spiral pedagógico deliberado com itens novos — é limitação do `lesson_bank` UPPER.

- Pares consecutivos com overlap ≥ 99%: **0** / 89

### Progressão Activate → Structure → Comprehension → Production → Consolidation?

**Sim na estrutura de blocos** (78/90 dias com fases em ordem). Gerado por `day_block_skills`: vocabulary → grammar → (pronunciation?) → listening|reading → conversation|writing → review. Domingos: reading → review.

### Semanas: começo, desenvolvimento, checkpoint?

- Checkpoint: semanas **pares** (`is_checkpoint_week`). Não há conteúdo diferente nos dias 1–6 vs 7 além do flag; o checkpoint é mini-placement, não uma jornada especial de síntese.
- Temas B2 ciclam: Argumentar e refutar → Negociação e mercado de trabalho → Ciência, dados e evidência → Mídia, fontes e desinformação → Sociedade e políticas públicas → ….
- Com entrada=B2 e target=B2, **todas as 13 semanas ficam em B2** (week_levels amostra: [<CEFRLevel.B2: 'B2'>, <CEFRLevel.B2: 'B2'>, <CEFRLevel.B2: 'B2'>, <CEFRLevel.B2: 'B2'>, <CEFRLevel.B2: 'B2'>]…).

### Complexidade progressiva dos objetivos?

**Parcial e só no eixo temático.** Temas B2 mudam (Argumentar → Negociação → Ciência…). O **léxico e exercícios mock** não sobem de complexidade: mesma banda UPPER, mesmos 6 itens, mesmos templates de grammar/reading/listening por banda.

## 3. Auditoria de repetição

| Métrica | Valor |
|---|---|
| Itens (ocorrências) | 80 |
| Itens únicos | 80 |
| Itens repetidos (≥2 dias) | 0 |
| Máx. aparições de um item | **1×** (`a compelling argument`) |
| Fingerprints lexicais idênticos (mesma ordem) | 70 dias em grupos |
| Dias cujo **conjunto** = banco UPPER inteiro | **0/90** |
| `lesson_ref` / content unit IDs no currículo gerado | **0** (lição só nasce no `/block/start`) |
| `objective_id` preenchido | **100** |

### Top itens por frequência (aparência em jornadas)

| Termo | Dias em que aparece (simulação vocab) |
|---|---|
| a compelling argument | 1 |
| a slippery slope | 1 |
| by and large | 1 |
| for the sake of argument | 1 |
| notwithstanding | 1 |
| on the contrary | 1 |
| the crux of the matter | 1 |
| to account for | 1 |
| to back up | 1 |
| to be inclined to | 1 |
| to bring about | 1 |
| to call into question | 1 |

### Repetição na mesma semana

- Semana 1: 17 termos únicos (banco UPPER tem 80) → parcial
- Semana 2: 10 termos únicos (banco UPPER tem 80) → parcial
- Semana 3: 11 termos únicos (banco UPPER tem 80) → parcial
- Semana 4: 8 termos únicos (banco UPPER tem 80) → parcial
- … (padrão se repete nas demais semanas B2)

## 4. Dia 1 × Dia 2 (investigação específica)

| | Dia 1 | Dia 2 |
|---|---|---|
| Tema/semana | Argumentar e refutar (sem. 1) | Argumentar e refutar (sem. 1) |
| Can-do / LearningObjective | *nenhum* | *nenhum* |
| Topic vocab | `Argumentar e refutar — vocabulário essencial` | `Argumentar e refutar — vocabulário essencial` |
| Skills | vocabulary → grammar → pronunciation → listening → conversation → review | vocabulary → grammar → reading → writing → review |
| Vocabulário mock | a compelling argument, a slippery slope, by and large, for the sake of argument, notwithstanding | on the contrary, the crux of the matter, to account for, to back up, to be inclined to |

- **Itens só no Dia 1:** ['a compelling argument', 'a slippery slope', 'by and large', 'for the sake of argument', 'notwithstanding']
- **Itens novos no Dia 2:** ['on the contrary', 'the crux of the matter', 'to account for', 'to back up', 'to be inclined to']
- **Itens repetidos Dia1∩Dia2:** []

### Por que reaparecem `to bring about`, `for the time being`, etc.?

1. Placement B2 → `lesson_bank.band_for('B2')` = **`upper`**.
2. `lesson_bank.vocabulary('en','upper')` contém **exatamente 80 itens fixos**:
   - `to bring about`
   - `to call into question`
   - `to hold that`
   - `on the contrary`
   - `to concede that`
   - `a compelling argument`
   - `to rebut`
   - `for the sake of argument`
   - `to bargain for`
   - `leverage`
   - `to meet halfway`
   - `a sticking point`
   - `to turn down`
   - `to back up`
   - `in good faith`
   - `to settle for`
   - `to account for`
   - `to bear out`
   - `a confounding factor`
   - `to extrapolate`
   - `peer-reviewed`
   - `statistically significant`
   - `to control for`
   - `an outlier`
   - `to fact-check`
   - `clickbait`
   - `to go viral`
   - `a primary source`
   - `to take with a grain of salt`
   - `echo chamber`
   - `to verify`
   - `biased coverage`
   - `notwithstanding`
   - `public interest`
   - `to roll out`
   - `a safety net`
   - `to crack down on`
   - `grassroots`
   - `to phase out`
   - `red tape`
   - `to be inclined to`
   - `a trade-off`
   - `to draw the line`
   - `unintended consequences`
   - `to turn a blind eye`
   - `informed consent`
   - `to outweigh`
   - `a slippery slope`
   - `for the time being`
   - `to hedge against`
   - `purchasing power`
   - `to break even`
   - `a downturn`
   - `to cut back on`
   - `supply chain`
   - `to write off`
   - `by and large`
   - `to convey`
   - `a nuanced reading`
   - `to fall flat`
   - `to resonate with`
   - `derivative`
   - `to shed light on`
   - `understated`
   - `a generational shift`
   - `to come of age`
   - `out of touch`
   - `to bridge the gap`
   - `social mobility`
   - `to push back against`
   - `the status quo`
   - `to catch on`
   - `to put forward`
   - `to spell out`
   - `to stand by`
   - `a working hypothesis`
   - `to boil down to`
   - `in a nutshell`
   - `to flesh out`
   - `the crux of the matter`
3. `_vocabulary` em `ai.py` chama `_rotate(lista, day_number)` e devolve **a lista inteira** (não um subconjunto novo por dia).
4. Dia 1: offset `(1-1)%6=0` → ordem original. Dia 2: offset `1` → mesma lista deslocada em 1 posição.
5. Portanto **todas** essas expressões reaparecem no Dia 2 (e em praticamente todos os 90 dias).
6. **`to back up`:** **não está** no banco UPPER atual. Se o usuário viu essa expressão, veio de **conteúdo curado** (`content_repository` / `seed_starter_content`) ou de outro modo — não do `lesson_bank` UPPER listado acima.

### “CONTINUA DE: BLOCOS ANTERIORES”

- **Origem UI:** `ThreadBanner` em `frontend/.../cronograma/dia/[id]/page.tsx`, texto fixo quando `thread.sources` existe.
- **Origem dados:** `lesson_thread.day_thread` / carryover em `learner_context` + `progression.build_block_lesson` → envelope com `thread.carried_terms`.
- **Algoritmo:** ao abrir um bloco **depois** do vocabulário no **mesmo dia**, o sistema extrai termos da lição anterior e força reuso (`_target_items` / `apply_to_terms` / `target_expressions`). Isso é **carryover intradía (tipo B)**, não SRS (tipo C) e não “conteúdo novo” (tipo A).
- No Dia 2, expressões **novas** no bloco de vocabulário vêm de `select_daily_vocabulary` (tipo A). Retomadas da semana entram em `revisited_items` (tipo B). O banner “Continua de…” continua sendo apenas carryover **intradía**.

## 5. Diversidade de atividades

A sequência de **skills** muda o tipo de bloco (vocab → grammar → input → output → review), o que em tese é a progressão apresentação → estrutura → compreensão → produção → consolidação.

Dias cujo multiset lexical ainda replica o banco UPPER inteiro: **0/90** (meta pós-correção: 0).

## 6. Teaching Engine V2

- LearningObjectives no banco: **18** (inclui stubs por tema B2 + slice EN-A1-CAN-001 se seedado)
- Blocos do currículo com `objective_id`: **100/453**
- Ligação leve: blocos `vocabulary` em B2+ recebem `objective_id` do objetivo temático da semana. O fluxo completo TE V2 (atividades → evidência → mastery) no path do cronograma ainda é parcial.

## 7. Padrões anormais (destaque automático)

1. Banco UPPER expandido: **80** itens (ok).
2. Sobreposição média Dia N/N+1: **0%**.
3. Blocos com `objective_id`: **100/453**.
4. Semana 1 B2 piloto: Can-Do distinto por jornada (7 objetivos). Demais semanas: âncora temática leve.
5. Checkpoint = semana par + mini-teste; Dia 7 do piloto também tem transfer Can-Do.
6. Entry B2→B2: sem escada CEFR no plano de 90 dias (esperado).

## 8. Correções aplicadas (lexical + piloto TE)

1. New/revisited por histórico curricular (`exposed_items`), não só semana.
2. Banco UPPER + seleção diária + papéis explícitos no payload.
3. Piloto Semana 1 B2: EN-B2-CAN-001…007 com pedagogia/mastery real.
4. Blocos pedagógicos da Semana 1 compartilham o Can-Do do dia; review sem objective.
5. Endpoints `/curriculum/block/{id}/teaching/*` para attempt/evidence/retry.
6. Carryover intradía (B) e SRS (C) mantidos separados.

---

*Fim da auditoria. Nenhuma alteração aplicada ao banco de produção nem aos dados do usuário.*
