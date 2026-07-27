# Repetição Espaçada — Fluentia

Relacionados: [learning-engine.md](learning-engine.md), [database.md](database.md), [decisions.md](decisions.md).

## Objetivo

Agendar revisões de vocabulário, caracteres, erros e exemplos para combater o esquecimento, sem transformar o app em só flashcards.

## Comparação conceitual: SM-2 vs FSRS

As duas abordagens são válidas. Esta seção apenas compara; **não confirma** a escolha final.

| Aspecto | SM-2 | FSRS |
|---|---|---|
| Maturidade | Clássico, simples, amplamente conhecido | Mais moderno, baseado em modelos de memória |
| Complexidade de implementação | Menor | Maior |
| Ajuste fino | Limitado | Melhor calibração com histórico |
| Dados necessários | Baixos | Beneficia-se de mais reviews |
| Risco | Agendamentos subótimos | Over-engineering cedo |

## Recomendação técnica provisória (não confirmada)

**FSRS** é uma **recomendação técnica inicial**, útil se houver biblioteca/algoritmo maduro e testável, pela aderência ao esquecimento real e ao histórico rico (erros, áudio, exemplos).

**SM-2** permanece **alternativa válida**, especialmente se FSRS atrasar a Fase 5 ou aumentar risco técnico demais.

Regras obrigatórias desta documentação:

- a escolha final **ainda é decisão pendente** (ver P-010 em [decisions.md](decisions.md));
- **nenhuma implementação** deve assumir FSRS sem autorização explícita;
- até a decisão ser confirmada no registro de decisões, o desenho deve permanecer agnóstico o bastante para acomodar SM-2 ou FSRS.

## Implementação provisória da primeira versão (D-019)

Na primeira versão do código, o Fluentia usa um **agendador simples isolado e substituível** (não FSRS e não SM-2 completo).

Regras provisórias do scheduler `simple`:

- `again`: próxima revisão em ~10 minutos;
- `hard`: +1 dia;
- `good`: dobra o intervalo (mínimo 1 dia);
- `easy`: triplica o intervalo;
- suporte a suspender e marcar como dominado.

**Status: recomendação técnica provisória. A decisão final permanece pendente em docs/decisions.md.**

Esta implementação existe para desbloquear revisão espaçada com API/testes. Trocar o algoritmo exige autorização e atualização de P-010/D-019.

Fontes:

- vocabulário novo;
- erros recorrentes;
- caracteres/kanji/pinyin;
- frases-modelo;
- itens marcados pelo usuário.

Regras:

- um foco por cartão;
- frente/verso claros;
- exemplo de uso quando possível;
- metadados de idioma/variante (es-ES, etc.).

## Revisão

Fluxo:

1. Buscar devidos (`next_review_at <= agora`, não suspensos).
2. Apresentar cartão.
3. Usuário responde / revela.
4. Registrar grade (de novo / difícil / bom / fácil — escala exata na implementação).
5. Atualizar estabilidade/intervalo conforme o algoritmo **autorizado** (SM-2, FSRS ou outro aprovado).

## Dificuldade

- Grade do usuário + acerto objetivo (quando houver).
- Itens com erro em conversação/escrita podem aumentar prioridade mesmo fora do ciclo puro de flashcard.

## Esquecimento

- Intervalos crescem com sucesso.
- Falhas encurtam intervalo e podem gerar explicação/mini-prática.

## Prioridade

Ordem típica da fila do dia:

1. Erros críticos recentes.
2. Itens vencidos há mais tempo.
3. Vocabulário padrão devido.
4. Reforço opcional.

## Suspensão

- Usuário ou sistema pode suspender item (irrelevante, duplicado, domínio estável).
- Suspensos saem da fila até reativação.

## Domínio

- Critérios alinhados ao motor pedagógico.
- Item dominado: baixa prioridade, revisões raras ou arquivamento suave.

## Revisão contextual

Preferir, quando possível:

- revisar palavra dentro de frase;
- ligar a erro real da sessão;
- não só tradução isolada.

## Áudio

- Cartões podem ter TTS sob demanda.
- Não armazenar áudio permanente por cartão sem necessidade.
- Falha de TTS não bloqueia revisão textual.

## Exemplos

- Manter 1 exemplo forte > muitos exemplos fracos.
- Para espanhol da Espanha, exemplos na variante correta.
- Para japonês/mandarim, cuidado com script/tons.

## Caracteres

- Japonês: kanji progressivo; não inundar a fila.
- Mandarim: caracteres simplificados + reforço tonal.
- Permitir cartões de leitura separados de significado quando útil.

## Erros recorrentes

- Criar `ReviewItem` ligado ao tipo de erro.
- Exigir explicação curta na primeira falha repetida.
- Remover da urgência após evidência de correção em uso real.

## Não fazer nesta etapa

- Implementar algoritmo.
- Assumir FSRS (ou SM-2) como decisão fechada sem autorização.
- Ajustar hiperparâmetros sem dados reais.
- Prometer retenção perfeita.
