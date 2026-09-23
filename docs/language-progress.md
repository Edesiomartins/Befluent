# Progresso do aluno

O progresso visível tem três medidas que não se misturam.

| Medida | Fonte | O que não entra |
|---|---|---|
| Sessão | cursor das atividades já geradas | domínio, CEFR |
| Habilidade | `UserObjectiveProgress` com `LearningEvidence`, no `skill_focus` real | skill sem evidência |
| Idioma | `UserLanguage.current_level` e marco derivado | XP, minutos, número de lições |

## Marco

Só entram objetivos do CEFR atual que já têm evidência. A média usa os
percentuais existentes de estado (`25`, `35`, `45`, `50`, `100`). Os cortes
ficam entre esses valores:

| Média | Marco |
|---|---|
| abaixo de 30 | 1 |
| abaixo de 43 | 2 |
| abaixo de 56 | 3 |
| abaixo de 85 | 4 |
| 85 ou mais | 5 |

O marco 5 não promove o CEFR. Não há percentual “até o próximo CEFR”.

## CEFR automático

`CEFR_AUTO_PROMOTION_ENABLED` está desligado.

Existe hoje: nível do perfil (teste, autodeclaração ou admin), níveis por
competência do nivelamento e domínio de objetivos. Não existe evidência
sustentada de que o aluno desempenha as competências do nível seguinte.
Repetir objetivos fáceis não pode subir A1 para A2.

A menor alteração futura, se o produto quiser promoção automática:

1. tarefas do nível seguinte nas competências reais (`vocabulary_grammar`,
   `reading`, `listening`, `writing`, `speaking`);
2. evidência correta nessas tarefas, não só conclusão;
3. limiar estável (mais de uma amostra), sem pular faixa;
4. só então ligar a promoção no domínio, nunca no frontend.

## Transição

`observe_language_progress` grava o primeiro estado sem celebrar. Celebração
só nasce quando o marco avança dentro da mesma faixa, ou quando o CEFR do
perfil sobe exatamente um degrau por um fluxo que já existia (nivelamento).
Reabrir o dashboard não gera o evento de novo.

## Interesse

`LearningGoal` do idioma escolhe o exemplo, quando existe variante. O termo
obrigatório permanece. Sem variante, fica o exemplo geral.
