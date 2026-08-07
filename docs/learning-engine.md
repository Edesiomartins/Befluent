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

## Cronograma estruturado (currículo)

O motor deixou de decidir apenas "a próxima atividade" e passou a organizar um
**cronograma com data por dia**, do nível diagnosticado até uma meta declarada.
Implementação: `services/curriculum_generator.py`, `services/progression.py`,
`services/curriculum_bank.py` e `api/curriculum.py`.

### Do nivelamento ao plano

Os níveis por competência gravados em `user_languages` pelo teste de nivelamento
são a entrada obrigatória. Sem eles a geração recusa (`placement_required`) em
vez de assumir um nível — o mesmo princípio do restante do sistema: não
fabricar avaliação.

- **Entrada:** mediana dos níveis por competência. Com número par de
  competências usa a **menor** das duas centrais: superestimar trava o aluno
  numa faixa que ele não sustenta.
- **Meta:** B2 no plano de 180 dias; entrada + 2 subníveis no de 90, teto B2.
  C1/C2 estão fora porque não há banco de itens validado nessas faixas.
- **Semanas por nível:** proporcionais à distância entrada→meta, com as semanas
  que sobram alocadas nos níveis finais (consolidar a meta custa mais do que
  atravessar o nível de entrada).

### Estrutura do dia

Oito áreas: vocabulário, gramática, pronúncia, escuta, leitura, conversação,
escrita e revisão. O dia cheio soma cerca de 45–60 minutos.

- Vocabulário e gramática todo dia.
- Um bloco de **entrada** (escuta *ou* leitura) e um de **saída** (conversação
  *ou* escrita), alternando.
- Pronúncia diária em japonês e mandarim (onde o erro fonético muda o
  significado); 3x por semana nos demais.
- Revisão fecha o dia, consumindo a fila real do SRS
  ([spaced-repetition.md](spaced-repetition.md)) — nunca uma revisão fabricada.
- **Domingo é dia leve:** só revisão e leitura. Cronograma sem folga é abandonado.

### Pesos adaptativos

Competência abaixo da mediana recebe mais minutos (×1,5) e mais blocos (2 de
cada 3 dias no seu par); acima da mediana entra em manutenção (×0,7). É assim
que o resultado do nivelamento vira tempo de estudo, e não só um rótulo.

Particularidades por idioma ([language-strategies.md](language-strategies.md)):
japonês abre com kana e progride para kanji; mandarim trabalha tons desde o dia
1 e hanzi progressivo; francês e espanhol ganham escuta extra, porque a
transparência lexical com o português faz o aluno superestimar a compreensão.

### Checkpoint e promoção

Semanas pares levam uma mini-avaliação que reusa o motor do nivelamento em
amostra curta. O nível resultante é gravado com origem `checkpoint`, distinta de
`placement_test`: uma estimativa de ~14 itens não tem o peso do teste completo,
e a interface precisa poder dizer isso.

Promoção exige **dois checkpoints consecutivos** com ≥80% na mesma faixa. Um só
não distingue aprendizado de um dia bom. Promover reescreve o nível das semanas
**pendentes**; semanas já cumpridas e blocos já concluídos nunca são alterados.

### Atraso

A partir de 5 dias vencidos o cronograma oferece duas saídas, e o aluno escolhe:

- **Comprimir:** redistribui os blocos essenciais (vocabulário, gramática,
  revisão) dos dias vencidos pelos dias restantes e descarta o resto daqueles
  dias. O prazo original é mantido.
- **Estender:** desloca as datas de todos os dias não concluídos.

Em nenhum dos dois o atraso é apagado: o dia vencido fica marcado como pulado.
Zerar o atraso silenciosamente seria mentir sobre o progresso.

### O que o cronograma não promete

Um plano de 90 dias **não garante B1**. Ele organiza o estudo necessário para
tentar. A distribuição de semanas e os pesos são heurísticas explícitas e
auditáveis, não um modelo validado de aquisição — toda resposta da API e a tela
do aluno carregam essa ressalva.

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
