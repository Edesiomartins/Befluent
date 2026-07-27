# Estratégia de Prompts — BeFluent

Modelos conceituais e contratos de saída. **Não escrever prompts finais gigantes nesta etapa.**

Relacionados: [ai-architecture.md](ai-architecture.md), [language-strategies.md](language-strategies.md), [learning-engine.md](learning-engine.md).

## Princípios

- Um prompt/tarefa = um objetivo.
- Saída preferencialmente estruturada e validável.
- Texto do usuário é dado, não instrução de sistema.
- Explicações ao aluno em português quando o nível exigir; reduzir progressivamente.
- Respeitar variante: espanhol da Espanha; japonês e mandarim com regras próprias.

## Contrato comum de saída (ilustrativo)

```json
{
  "task": "grammar_correction",
  "language_code": "es-ES",
  "result": {},
  "explanations_pt": [],
  "errors": [],
  "next_suggestion": null
}
```

Campos exatos variam por tarefa; o backend valida com schema.

---

## Diagnóstico

- **Objetivo:** estimar nível e dificuldades iniciais sem falsa precisão.
- **Entradas:** idioma; respostas do usuário; habilidades cobertas.
- **Saída:** nível estimado (faixa); forças; fraquezas; recomendações; limitações da estimativa.
- **Regras:** não afirmar equivalência rígida CEFR/JLPT/HSK; ser conservador.
- **Riscos:** superestimar nível; vieses do modelo.
- **Validação:** schema; faixas permitidas; presença de limitações explícitas.

## Professor conversacional

- **Objetivo:** conduzir diálogo natural e útil.
- **Entradas:** idioma/variante; nível; tema; histórico resumido; erros recentes.
- **Saída:** resposta do tutor; correções opcionais; dicas curtas; sinal de continuar/encerrar.
- **Regras:** tom adulto; não infantilizar; priorizar comunicação real.
- **Riscos:** monólogos longos; misturar variantes (especialmente espanhol).
- **Validação:** idioma da resposta; tamanho máximo; campos de correção bem formados.

## Correção gramatical

- **Objetivo:** corrigir e explicar erros gramaticais.
- **Entradas:** texto; idioma; nível; contexto.
- **Saída:** texto corrigido; lista de erros (trecho, tipo, explicação_pt, sugestão).
- **Regras:** explicar, não só marcar; priorizar erros mais importantes.
- **Riscos:** overcorrection; pedantismo inútil.
- **Validação:** erros referenciam trechos existentes; explicações não vazias.

## Correção de escrita

- **Objetivo:** feedback de produção escrita.
- **Entradas:** prompt da tarefa; texto do aluno; critérios.
- **Saída:** nota relativa opcional; pontos fortes; melhorias; versão revisada parcial; próximos exercícios.
- **Regras:** respeitoso; acionável; alinhado ao nível.
- **Riscos:** reescrever tudo e impedir aprendizado.
- **Validação:** separação clara entre feedback e reescrita.

## Explicação de erros

- **Objetivo:** aprofundar um erro específico.
- **Entradas:** erro; idioma; exemplos do aluno.
- **Saída:** explicação_pt; contraste com português se útil; 1–2 exemplos; mini-prática.
- **Regras:** curta e clara.
- **Riscos:** jargão excessivo.
- **Validação:** presença de exemplo correto.

## Geração de aula

- **Objetivo:** montar aula guiada.
- **Entradas:** idioma; objetivo; nível; duração alvo; dificuldades.
- **Saída:** título; objetivo; seções; atividades; critérios de conclusão.
- **Regras:** seguir [language-strategies.md](language-strategies.md).
- **Riscos:** aula genérica demais.
- **Validação:** estrutura mínima; coerência de nível.

## Geração de exercícios

- **Objetivo:** criar exercícios objetivos.
- **Entradas:** habilidade; tópico; nível; quantidade.
- **Saída:** lista de itens com tipo, prompt, gabarito/rubrica.
- **Regras:** sem excesso; foco no objetivo.
- **Riscos:** ambiguidade de gabarito.
- **Validação:** cada item tem critério de correção.

## Vocabulário

- **Objetivo:** selecionar/ensinar itens lexicais.
- **Entradas:** idioma; tema; nível; itens já conhecidos.
- **Saída:** termos; leitura/pinyin se aplicável; tradução_pt; exemplos; notas de uso (ex.: vosotros no es-ES).
- **Regras:** evitar lista solta sem contexto.
- **Riscos:** traduções falsas amigas não explicadas.
- **Validação:** exemplos no idioma alvo.

## Compreensão auditiva

- **Objetivo:** gerar script + questões.
- **Entradas:** idioma; nível; tema; duração.
- **Saída:** script; questões; respostas; pontos de vocabulário.
- **Regras:** áudio natural; perguntas verificáveis.
- **Riscos:** script irreal para TTS.
- **Validação:** respostas batem com o script.

## Revisão espaçada

- **Objetivo:** apoiar criação/priorização de cartões e prompts de revisão.
- **Entradas:** item; histórico de erros; idioma.
- **Saída:** frente/verso; dica; exemplo; tags.
- **Regras:** cartão simples; um foco.
- **Riscos:** cartões sobrecarregados.
- **Validação:** campos mínimos presentes.

## Relatório de sessão

- **Objetivo:** sintetizar a sessão.
- **Entradas:** atividades; erros; duração; idioma.
- **Saída:** resumo_pt; conquistas; erros a revisar; próxima atividade sugerida.
- **Regras:** honesto; sem falsa precisão.
- **Riscos:** inventar progresso.
- **Validação:** só citar atividades que existiram na entrada.

## Adaptação de nível

- **Objetivo:** sugerir ajuste de dificuldade.
- **Entradas:** métricas recentes; erros; conclusão de atividades.
- **Saída:** direção (manter/subir/descer); justificativa; cuidados.
- **Regras:** conservador; evidência mínima.
- **Riscos:** oscilação frequente.
- **Validação:** justificativa baseada nos dados de entrada.

## Inglês médico

- **Objetivo:** módulo separado de inglês médico.
- **Entradas:** subtema clínico; nível; restrição de não aconselhar pacientes reais.
- **Saída:** conteúdo de estudo linguístico; glossário; diálogos profissionais.
- **Regras:** não substituir aconselhamento médico real; foco em linguagem.
- **Riscos:** conteúdo clínico inadequado.
- **Validação:** disclaimer linguístico; ausência de prescrição.

## Espanhol da Espanha

- **Objetivo:** garantir variante peninsular.
- **Entradas:** tarefa base + flag `es-ES`.
- **Saída:** vocabulário/pronúncia/uso alinhados à Espanha; vosotros quando cabível; notas se houver contraste com LatAm.
- **Regras:** não misturar variantes sem explicação.
- **Riscos:** mexicanismos/argentinismos não marcados.
- **Validação:** checklist de variante no schema.

## Francês

- **Objetivo:** priorizar pronúncia, liaison, gênero e conjugação.
- **Entradas:** tarefa + nível.
- **Saída:** conteúdo com apoio de pronúncia quando relevante.
- **Regras:** escrita e pronúncia juntas quando útil.
- **Riscos:** ignorar gênero.
- **Validação:** campos de gênero/conjugação quando aplicáveis.

## Japonês

- **Objetivo:** respeitar hiragana/katakana, partículas, formalidade, kanji progressivo.
- **Entradas:** tarefa + política de romaji.
- **Saída:** texto preferencialmente em kana/kanji adequados; romaji só apoio inicial; notas de formalidade.
- **Regras:** reduzir romaji progressivamente; poucos kanji novos por vez.
- **Riscos:** excesso de romaji; formalidade inadequada.
- **Validação:** flags de script e formalidade.

## Mandarim

- **Objetivo:** pinyin, tons, caracteres simplificados graduais.
- **Entradas:** tarefa + política de pinyin.
- **Saída:** texto com pinyin/tons conforme nível; caracteres simplificados; notas tonais.
- **Regras:** não adiar tons; pinyin como apoio, não destino final.
- **Riscos:** omitir tons; misturar tradicional/simplificado.
- **Validação:** presença de informação tonal quando houver fala/leitura inicial.
