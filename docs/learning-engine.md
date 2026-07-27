# Motor Pedagógico — BeFluent

Regras conceituais, sem código.

Relacionados: [language-strategies.md](language-strategies.md), [assessment-system.md](assessment-system.md), [spaced-repetition.md](spaced-repetition.md), [prompt-strategy.md](prompt-strategy.md).

## Objetivo

Decidir **o que estudar a seguir**, com que dificuldade e com que equilíbrio de habilidades, respeitando o idioma e o desempenho real.

## Perfil do aluno

O perfil agrega:

- idiomas ativos;
- nível estimado por idioma (faixa, com incerteza);
- objetivos (`LearningGoal`);
- preferências;
- histórico resumido de sessões;
- erros recorrentes;
- vocabulário ativo/passivo;
- progresso gramatical.

O perfil vive no PostgreSQL; prompts recebem apenas resumo.

## Nível

- Representado como faixa, não como nota falsa.
- Referências CEFR/JLPT/HSK são orientativas ([assessment-system.md](assessment-system.md)).
- Atualização conservadora após evidências suficientes.

## Objetivos

- Curto prazo (ex.: sobreviver a conversas cotidianas).
- Médio prazo (ex.: leitura acadêmica em inglês).
- Especiais (ex.: inglês médico — módulo separado).

O plano prioriza objetivos ativos sem abandonar bases frágeis.

## Habilidades acompanhadas

- Conversação
- Compreensão auditiva
- Pronúncia
- Vocabulário
- Gramática
- Leitura
- Escrita

Nem toda sessão cobre todas. O motor busca equilíbrio ao longo do tempo.

## Dificuldades e erros recorrentes

- Registrar tipo, idioma, exemplo e frequência.
- Priorizar revisão quando o mesmo erro reaparece.
- Explicar o erro; não apenas marcar.

## Vocabulário ativo e passivo

- **Passivo:** reconhece.
- **Ativo:** usa com razoável precisão.
- Itens sobem/descem conforme uso em conversação/escrita/revisão.
- SRS agenda reforço ([spaced-repetition.md](spaced-repetition.md)).

## Recomendação da próxima atividade

Entradas típicas:

- idioma ativo e estratégia específica;
- itens de revisão devidos;
- item atual do plano;
- fadiga/recência (evitar repetir o mesmo tipo sem necessidade);
- falhas recentes de habilidade.

Prioridade conceitual:

1. Revisões críticas vencidas.
2. Continuidade do plano (aula/objetivo).
3. Correção de habilidade fraca identificada.
4. Prática de consolidação (conversação leve).

## Adaptação de dificuldade

- Se acertos altos e rápidos → subir um degrau.
- Se erros altos ou abandono → descer ou mudar formato.
- Evitar oscilação a cada item; usar janela de evidências.

## Equilíbrio entre habilidades

- Evitar semanas só de flashcards ou só de conversação.
- Respeitar prioridades do idioma:
  - francês: pronúncia/escuta cedo;
  - japonês: scripts e partículas;
  - mandarim: tons cedo;
  - espanhol da Espanha: variante e vosotros;
  - inglês: fluência + precisão e, depois, módulos específicos.

## Redução progressiva do português

- Iniciante: explicações em português.
- Intermediário: misturar.
- Avançado: feedback majoritariamente no idioma alvo, com opção de explicação em português.

## Personalização por idioma

Sempre carregar a estratégia de [language-strategies.md](language-strategies.md) ao gerar plano, aula ou conversa.

## Relatório de sessão

Ao encerrar:

- o que foi feito;
- o que melhorou;
- erros a revisar;
- próxima recomendação.

Sem inventar conquistas.

## Critérios de domínio (conceituais)

Um item/habilidade tende a “dominado” quando:

- desempenho consistente em janela recente;
- uso em contexto (não só reconhecimento);
- baixa necessidade de revisão urgente;
- ausência de erro recorrente associado.

Critérios numéricos finais = decisão pendente na implementação do SRS/avaliação.

## O que o motor não faz

- Não substitui julgamento humano absoluto.
- Não promete fluência em prazo fixo.
- Não usa gamificação infantil como motor de decisão.
- Não ignora falhas de IA: se dados faltarem, recomenda com cautela e declara incerteza.
