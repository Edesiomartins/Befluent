# Auditoria editorial — prioridades antes das correções

Baseline: `d6e6516`; árvore limpa. Escopo: conteúdo backend, frontend somente leitura, SQLite local somente leitura. Sem produção.

| Prioridade | Evidência | Decisão |
|---|---|---|
| CRÍTICA | Italiano: `pesca` pêssego ensinada com e fechado e pesca com e aberto; Treccani confirma o inverso | Corrigir conteúdo e contraste com português |
| CRÍTICA | EN B1: `I ____ to Paris three times` e `I ____ that film` rejeitam `went`/`saw` apesar de serem frases possíveis; feedback afirma que passado simples exige data explícita | Especificar a estrutura solicitada e corrigir justificativas |
| ALTA | `/lessons/generate` e progressão sobrescrevem título pedagógico com `[starter] reading/grammar…` | Exibir título do payload para identificadores starter; preservar título editorial de outras unidades |
| ALTA | Foco FR B1 fala de experiência acumulada, mas exemplos/exercícios ensinam imparfait/passé composé/depuis | Alinhar explicação ao conteúdo já existente; sem criar novo curso |
| ALTA | Fallback de código desconhecido retorna inglês em acessores de conteúdo | Rejeitar código desconhecido; não ensinar idioma substituto |
| ALTA | Validação de lição OpenRouter só exige título; aceita metadado de outro idioma e gabarito ausente | Guard determinístico de contrato, metadados e contaminação inglesa conhecida; sem detector probabilístico |
| ALTA | Envelope substitui nível da unidade pelo nível solicitado; biblioteca admite níveis próximos | Expor `content_level` real separadamente, preservar `level` contratado |
| MÉDIA | Uma pergunta genérica de leitura/escuta por faixa; mesmo gabarito independentemente do texto; conteúdo e contexto de conversa derivados do vocabulário | Recomendar revisão humana; não inventar banco substituto |
| MÉDIA | PRE_A1 copia A1; B2/C1/C2 compartilham upper; tema curricular não garante alinhamento do texto escolhido | Registrar lacunas, sem reclassificação CEFR arbitrária |
| MÉDIA | Piper sem ja/zh-CN; fallback frontend para en-US em códigos desconhecidos | Registrar limite e FRONTEND ISSUE; não alterar fala ou frontend |

Não foi fornecido o título exato nem a URL da ocorrência francesa. O vazamento `[starter]` foi reproduzido por código; não se afirma que ele explique qualquer outro título inglês observado.

Complemento identificado durante a revisão do gerador: transfer/guided/distratores de preenchimento em inglês (CRÍTICO), tokenização ASCII que perdia acentos e gap de expressão única que expunha o gabarito. Corrigidos sem inventar conteúdo: atividades sem pedagogia autoral omitidas; Unicode e lacuna segura. Revisão independente apontou variantes aceitas e duplicatas usadas como distratores; filtro e regressão corrigidos.

Medição completa de estrutura e igualdade textual: `editorial-audit-before.json`. Ausência de apontamentos automatizados não é aprovação linguística de todo o banco. Dados de pesquisa com 63 respostas são contexto informado pelo usuário, não revalidado nesta rodada.
