# Teaching Engine V2 — BeFluent

Extensão do Teaching Engine V1 (`0007`). Princípio: **BeFluent é o método; a IA executa o método**.

## Eixos ortogonais

| Conceito | Significado |
|---|---|
| `CurriculumBlock.status` | Atividade concluída (administrativo) |
| `UserObjectiveProgress.state` | Domínio (`MasteryState`) |
| `TeachingFlowSession.phase` | Fase pedagógica da sessão (`FlowPhase`) |

Concluir ≠ dominar.

## Ciclo

```
OBJECTIVE → ACTIVATE → INPUT → NOTICE → PRACTICE → PRODUCE
→ ATTEMPT → EVALUATE → (ERROR → REMEDIATE → RETRY)*
→ TRANSFER → MASTERY → MEMORY
```

## Vertical slice

`EN-A1-CAN-001` — apresentar-se (A1).  
API: `/api/v1/teaching/slice/en-a1-can-001/*`  
UI: `/learn/objetivo`

## Determinístico primeiro

Multiple choice, variants, word order, fill-gap, alignment de transcript e SRS **não** chamam IA.

Avaliação distingue `lexical` / `structural` / `guided` / `transfer`.
Resposta só com a palavra-alvo (ex.: `professor`) **não** domina estrutura `I am + profession`.

## Memória

| Estrutura | Papel |
|---|---|
| `MemorySchedule` | Fonte da verdade V2 (`due_at`, estado, eventos) |
| `ReviewItem` | Projeção de compatibilidade (`/reviews`) |

Respostas legadas e V2 passam por `memory_engine.record_review` / `answer_review_item` (sem double-write).

## Retry / circuit (OpenRouter)

- Por modelo: **1** tentativa; 429 pode ter **1** retry curto; 5xx/timeout → fallback rápido (sem martelar o mesmo modelo).
- Máximo típico por ação: **1** (ok) · **2** (primary+fallback) · **3** (429 no primary + fallback).
- Circuit breaker in-process: threshold 3, cooldown 30s, half-open.

## Restore de flow

`GET /api/v1/teaching/slice/en-a1-can-001/active` restaura fase, cursor e remediação.
Frontend `/learn/objetivo` consulta o backend no mount (sem localStorage pedagógico).

## Cronograma flexível (jornadas)

`CurriculumDay` = unidade de progressão (jornada), não dia civil obrigatório.

- `current_day` = primeiro dia aberto (`pending` / `in_progress`), nunca “hoje no calendário”.
- Concluir Dia N libera Dia N+1 imediatamente (`next_day.available`), mesmo com `scheduled_date` futura.
- `scheduled_date` = ritmo recomendado / atraso / adiantamento (`pace_status`), **nunca** gate de acesso.
- Ordem de blocos **dentro** do dia permanece obrigatória.
- SRS (`ReviewItem` / `MemorySchedule`) continua temporal — avançar jornadas não antecipa `due_at`.
- Checkpoint: exige todas as jornadas da semana concluídas (progresso), não a data civil da semana.

## Fora desta iteração

- Currículo A1 completo / todos os idiomas
- Listening Lab (vídeo/YouTube/OCR)
- MeCab / pitch accent / FSRS
- TTS pago / score fonético
- Circuit breaker distribuído / Redis

## Conteúdo e frequência

O fallback atual de `lesson_bank` ainda pode servir unidades genéricas por faixa CEFR.  
`LearningObjective.pedagogy_json` e targets declarativos são a base para substituir isso progressivamente por utilidade comunicativa + frequência.
