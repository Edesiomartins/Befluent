# Progresso do aluno

O progresso visível tem três medidas que não se misturam.

| Medida | Fonte | O que não entra |
|---|---|---|
| Sessão | orçamento de exercícios (alvo 36, teto 40) | domínio, CEFR |
| Habilidade | evidência por `skill_focus` no CEFR atual | XP, minutos |
| Idioma | `UserLanguage.current_level` | promoção automática |

## Sessão (Session Engine V2)

A sessão é planejada por exercícios, não por “completar o ciclo de cada palavra”.
Configuração em `session_budget.py`:

- alvo 36, máximo 40;
- vocabulary 8, listening 8, grammar 8, production 6, conversation 6;
- no máximo 3 exercícios consecutivos da mesma modalidade, quando houver alternativa.

Evidências lexicais (recognition, reverse, listening, production) podem
ficar em sessões diferentes. Revisão vencida disputa o orçamento; o restante
volta depois. Retomar a sessão ativa continua de onde parou. “Continuar
estudando” abre uma sessão nova.

## Domínio visto × cobertura × progresso efetivo

Quando existir catálogo oficial de objetivos para `idioma + CEFR + skill`:

- `coverage` = evidenciados / total;
- `mastery_seen` = média do domínio só nos evidenciados;
- `effective_progress` = soma dos percentuais (não vistos = 0) / total.

Hoje **não** existe esse catálogo fechado. `LearningObjective` guarda um
can-do A1, a semana piloto B2 e âncoras de tema do cronograma. Contar essas
linhas inventaria o denominador.

Enquanto `official_curriculum_total(...)` retornar `None`:

- a API expõe `mastery_seen_percent` e a contagem de evidências;
- `coverage_percent`, `effective_progress_percent` e a barra principal
  ficam ausentes;
- o marco derivado também fica ausente (ele depende do progresso efetivo).

A menor correção para coverage real: um inventário estável de objetivos
por idioma, CEFR e skill (seed ou tabela), e só então ligar o denominador.

## Marco

Com progresso efetivo disponível, as faixas são:

| Progresso efetivo | Marco |
|---|---|
| 0–19,99% | 1 |
| 20–39,99% | 2 |
| 40–59,99% | 3 |
| 60–79,99% | 4 |
| 80–100% | 5 |

O marco 5 não promove o CEFR. Não há percentual “até o próximo CEFR”.

## CEFR automático

`CEFR_AUTO_PROMOTION_ENABLED` está desligado.

Existe hoje: nível do perfil (teste, autodeclaração ou admin), níveis por
competência do nivelamento e domínio de objetivos. Não existe evidência
sustentada de que o aluno desempenha as competências do nível seguinte.
Repetir objetivos fáceis não pode subir A1 para A2.

A menor alteração futura, se o produto quiser promoção automática:

1. catálogo oficial de objetivos do nível atual (para coverage);
2. tarefas do nível seguinte nas competências reais;
3. evidência correta nessas tarefas, não só conclusão;
4. limiar estável, sem pular faixa;
5. só então ligar a promoção no domínio, nunca no frontend.

## Transição

`observe_language_progress` grava o primeiro estado sem celebrar. Celebração
só nasce quando o marco avança dentro da mesma faixa, ou quando o CEFR do
perfil sobe exatamente um degrau por um fluxo que já existia (nivelamento).
Reabrir o dashboard não gera o evento de novo.

## Interesse

`LearningGoal` do idioma escolhe o exemplo, quando existe variante. O termo
obrigatório permanece. Sem variante, fica o exemplo geral.
