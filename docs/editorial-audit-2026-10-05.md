# BeFluent — auditoria editorial e pedagógica multilíngue

Data: 2026-10-05. Baseline `d6e6516` (`auditoria1`), árvore inicialmente limpa. Escopo exclusivo desta rodada: conteúdo e contrato editorial backend; frontend lido, sem edição. Sem commit, push ou deploy.

## 1. Resumo executivo

O banco entrega conteúdo nos oito idiomas configurados, mas há defeitos concretos e lacunas pedagógicas. Corrigidos: vazamento de identificadores internos ingleses nos títulos, preenchimentos ingleses no gerador genérico, perda de acentos na ordenação, distratores duplicados/aceitos como respostas, explicação FR B1 incompatível com os exercícios, pronúncia italiana invertida e duas perguntas inglesas ambíguas. Código desconhecido agora falha em vez de ensinar inglês. O guard de IA passou a validar contrato mínimo, alternativas, idioma declarado e contaminação inglesa conhecida.

Não se afirma que todo o conteúdo esteja pedagogicamente aprovado. A revisão manual foi dirigida pelos achados, não uma certificação por falantes de oito idiomas. A varredura automática foi ampla e reproduzível. Nenhum dado histórico foi reescrito.

## 2. Idiomas realmente encontrados

Catálogo configurado por `seed.LANGUAGES`, bancos e fixtures: `en`, `es-ES`, `fr`, `it`, `de`, `ja`, `zh-CN`, `la`. `la` é eclesiástico/Vulgata; `la-classical` está explicitamente aposentado. Não há curso `pt`/`pt-BR`; português é idioma de interface/apoio.

Configuração local carregada: development, SQLite, AI mock, STT mock, TTS mock. O SQLite `backend/befluent.db` foi aberto com `mode=ro` e `query_only=ON`: **zero registros de idiomas e zero ContentUnits**. Assim, oito são idiomas configurados no código; não se afirma que oito estejam ativos no banco de produção. Produção não foi consultada nesta rodada.

## 3. Armazenamento e geração

| Fonte/caminho | Conteúdo e papel |
|---|---|
| `app/services/lesson_bank.py`, `lesson_bank_it/de/la.py` | Vocabulário, exemplos, exercícios, leitura, escuta, escrita, situações e fonética; quatro faixas |
| `grammar_practice.py` | Três exercícios extras por faixa para os cinco idiomas do banco principal; it/de/la registram seus quatro exercícios em módulos próprios |
| `curriculum_bank.py`, `curriculum_generator.py` | Temas/ângulos semanais, níveis de blocos e cronograma; assunto do bloco não garante conteúdo temático compatível |
| `content_seed.py` | Materializa ContentSources/ContentUnits aprovadas: sete modos × A1/A2/B1 e cópia A1→PRE_A1; marcador dev_starter |
| `content_repository.py` | Busca idioma/skill/mode/nível; aceita níveis vizinhos e, sem assunto compatível, unidade mais recente |
| `api/lessons.py`, `progression.py`, `lesson_envelope.py` | Escolha biblioteca/IA, título público e metadados entregues ao aluno |
| `ai.py`, `prompts/library.py`, `learner_context.py` | Builders mock e prompts com idioma-alvo, português, CEFR, contexto, escrita e variantes regionais; geração OpenRouter |
| `objective_seed.py`, `objective_seed_b2_week1.py` | Slice editorial detalhado EN A1/B2 e objetivos temáticos leves nos demais cursos |
| `activity_generator.py`, `session_engine.py` | Atividades declarativas, ciclo lexical, exemplos/questões/áudio/conversa de apoio; orçamento 36/12 preservado |
| `app/data/placement_items/*.json`, `placement_seed.py` | Oito fixtures de nivelamento, metadados de idioma/CEFR e gabaritos |
| `lesson_thread.py`, `lesson_envelope.py` | Carryover e continuidade; não necessariamente inserem as palavras no texto fixo |
| `narrative_en.py` | Bell & Sons é série explicitamente só inglesa; não foi indevidamente generalizada |
| `speech.py`, frontend `study.tsx` | Texto/código para Piper; navegador como fallback. Não houve mudança no motor de fala |

Fixtures de testes não são consideradas conteúdo de produção. Não foi identificado banco YAML separado. Conteúdo persistido pode existir em ContentUnits, Lessons, atividades, objetivos e caches; a base local vazia não permite avaliar seus valores reais.

## 4. Quantidade auditada por idioma

Varredura final: **560 payloads mock + 168 payloads starter + 1.354 atividades lexicais + 144 itens placement**. Cada mock percorre sete níveis × dez modos, inclusive voice/guided/review. Starter percorre três níveis × sete modos; cópia PRE_A1 foi inspecionada no seed, sem ser contada como payload gerado separado. As contagens não representam usuários, cursos publicados ou aulas únicas.

| Idioma | Léxico | Exemplos gram. | Exercícios gram. | Textos / áudios distintos | Atividades lexicais | Placement | Mock / starter |
|---|---:|---:|---:|---:|---:|---:|---:|
| en | 98 | 12 | 16 | 4 / 4 | 490 | 20 | 70 / 21 |
| es-ES | 24 | 12 | 16 | 4 / 4 | 120 | 20 | 70 / 21 |
| fr | 24 | 12 | 16 | 4 / 4 | 120 | 20 | 70 / 21 |
| it | 24 | 12 | 16 | 4 / 4 | 120 | 12 | 70 / 21 |
| de | 24 | 12 | 16 | 4 / 4 | 120 | 12 | 70 / 21 |
| ja | 24 | 12 | 16 | 4 / 4 | 114 | 20 | 70 / 21 |
| zh-CN | 24 | 12 | 16 | 4 / 4 | 120 | 20 | 70 / 21 |
| la | 30 | 12 | 16 | 4 / 4 | 150 | 20 | 70 / 21 |

Todos têm quatro tarefas de escrita, quatro situações de conversa e três focos fonéticos. Vocabulário/review reutilizam o mesmo banco: não somar review como léxico novo. **62.097 campos string** percorridos no corpus banco/payload/atividade final, incluindo ocorrências repetidas; placement foi validado separadamente quanto a alternativas/metadados. Dados completos em `editorial-audit-after.json`. A versão before é mais estreita, anterior à inclusão de atividades/placement/foco; não comparar seus totais de campos como melhora de qualidade.

## 5. Achados por prioridade

**CRÍTICOS corrigidos:** ensino fonético italiano invertido; perguntas com mais de uma resposta linguisticamente possível; defaults ingleses genéricos em objetivos de outros idiomas; variantes aceitas usadas como distratores; tokens sem acentos tornando impossível reconstruir a frase canônica.

**ALTOS corrigidos:** títulos `[starter]` com modos em inglês; foco francês B1 desalinhado; fallback de idioma para inglês; validação insuficiente do JSON gerado; nível original de unidade ocultado no envelope.

**ALTOS pendentes de revisão editorial:** defaults genéricos de perguntas de compreensão; cenário de conversa versus abertura; afirmações absolutas de tempo/aspecto nos exercícios de outros idiomas; explicação gramatical comum que não cobre morfologia latina. Não foram inventados textos/exercícios substitutos.

**MÉDIOS:** repetição por pequeno acervo, PRE_A1 reutilizando A1, upper compartilhado entre B2/C1/C2, tópico curricular sem garantia de correspondência, carryover solicitado mesmo quando o texto não contém o termo, gramática no ciclo lexical com explicação principalmente no feedback.

**BAIXOS:** rótulos/nomenclatura editorial e fluidez das instruções. Sem reescrita cosmética extensa.

## 6. Exemplos concretos

Identificadores abaixo são células do banco, pois não há IDs persistidos locais.

| Idioma / módulo / lição | Campo e conteúdo atual no baseline | Esperado / origem / impacto |
|---|---|---|
| fr / biblioteca / leitura A1 | API `title=[starter] reading · A1`; payload `Une matinée ordinaire · A1` | Título pedagógico; origem: precedência no endpoint/progressão. Corrigido |
| en / gramática / B1 | `I ____ to Paris three times`, `have been` vs `went`; `I ____ that film`, `have seen` vs `saw` | Enunciado explicita present perfect; passado simples possível deixa de ser declarado impossível. Dois prompts/feedbacks corrigidos. [Cambridge confirma tempo passado sem referência explícita](https://dictionary.cambridge.org/us/grammar/british-grammar/past-simple/) |
| it / pronúncia / todas as faixas | pêssego e fechado / pesca e aberto | Pêssego /ɛ/, pesca /e/; correção confirmada pela [Treccani](https://www.treccani.it/enciclopedia/pesca-o-pesca_%28La-grammatica-italiana%29/). Também removida falsa ausência de contraste aberto/fechado em português |
| fr / gramática / B1 | foco `Experiência × tempo encerrado`, mas exemplos `Quand j'étais petit…`, exercício `allais` | Explicação imparfait/passé composé/depuis; corrigida usando estruturas já presentes |
| es-ES / gramática / B1 | `____ esa película` aceita He visto e rejeita Vi por supostamente exigir data explícita | Contextualizar ou solicitar pretérito perfecto explicitamente; alto risco de rejeitar resposta possível. Revisão humana pendente |
| de / gramática / B1 | `Ich ____ 2019 hingefahren`, rejeita war como se não formasse outra estrutura | Solicitar Perfekt explicitamente ou revisar contexto/alternativas; não tratar ano como prova de que Perfekt é obrigatório. Revisão pendente |
| ja / gramática / B1 | feedback: `ことがある não combina com ano explícito` | Evitar regra temporal absoluta importada do inglês; revisão por especialista. Não se certifica aqui qual resposta é adequada em todo contexto |
| zh-CN / gramática / B1 | `我看____那部电影` fixa 过 e rejeita 了; feedback nega 过 com ano explícito | Explicitar intenção experiencial e revisar aspecto/contexto. Alternativas sem contexto são suspeitas; não alteradas sem revisão especializada |
| la / gramática / A1–B1 | explicação comum não cobre Dominus/Domine/Domini, Verbum/Verbi/Verbo ou caro/carnis/carnem | Explicação morfológica antes da avaliação, baseada no banco existente; pendente, sem aula inventada |
| la / escuta / upper | Credo; gabarito genérico `Uma informação prática sobre uma situação concreta` | Pergunta realmente sobre trecho litúrgico. Template atual é pouco informativo/desalinhado; precisa edição autoral |
| todos / conversa / A2 | situação restaurante; abertura `I'm looking for the train station` / `Je cherche la gare` / equivalentes em sete idiomas; la `Kyrie, eleison…` | Abertura e réplicas relacionadas à situação. Oito células starter demonstram incoerência; não criado diálogo substituto |
| fr / gerador genérico / objetivo sem pedagogia | guided: `Tell me about yourself`, scaffold `My name is…`; transfer: irmão mora onde | Sem conteúdo autoral, omitir atividade em vez de importar inglês. Corrigido para todos os idiomas |
| fr / gerador / ordenação | canônica `Je viens du Brésil.` → tokens ASCII perdiam é | Tokens Unicode preservados; regressão criada |
| ja/zh-CN / gerador / lacuna | expressão única ficava `你好 ___`, com gabarito 你好 | Lacuna `___`, sem entregar/repetir o gabarito. Corrigido |

## 7. Título francês em inglês: causa

**Defeito reproduzido e corrigido:** títulos internos `[starter] reading/grammar…` venciam o título francês/português no payload em dois caminhos backend. Teste HTTP confirma `Une matinée ordinaire · A1`, código fr, content_level A1 após correção.

**Ocorrência original do usuário: NÃO CONFIRMADA integralmente.** Não foram fornecidos título exato, rota, ID ou payload observado. Caso o título original fosse um título inglês diferente do marcador starter, esta investigação não prova que tenha a mesma causa. O banco francês de leitura tem títulos franceses e não foi encontrado clone textual inglês nos campos-alvo comparados. Produção e histórico/cache não foram acessados.

## 8. Problemas sistêmicos e medidas

- Dois caminhos de entrega sobrescreviam título; fix cobre todos os idiomas/modos starter, sem alterar títulos editoriais normais. Seed pode materializar 224 unidades (8×4×7); isso é capacidade do código, não quantidade persistida encontrada.
- Um gerador genérico continha transfer/guided/distratores ingleses de preenchimento. Removidos; prompt de instrução de escolha em português. Objetivos ingleses com pedagogia explícita continuam usando seu conteúdo.
- Dois exercícios ingleses corrigidos; uma célula FR B1 corrigida; um foco fonético italiano corrigido.
- Uma regra comum de fallback para inglês eliminada dos acessores; código ausente/sem tabela falha explicitamente.
- Zero duplicatas textuais normalizadas ou gabaritos ausentes nas opções string examinadas; zero inconsistências de código/CEFR nas 144 fixtures placement. Isso não mede equivalência semântica.
- Zero igualdade exata detectada entre campos-alvo dos bancos não ingleses e os mesmos campos ingleses. Scaffolding em português é permitido e não contado como contaminação.
- Cada idioma usa quatro leituras e quatro escutas em sete níveis; não há textos distintos para B2/C1/C2 nesse banco.
- Oito situações starter A2 têm abertura alheia ao restaurante. Builders mock também escolhem exemplos de vocabulário, mas podem variar por contexto; não se extrapola uma contagem fixa a todos os usuários.

## 9. Problemas isolados

Italiano: inversão lexical/fonética em pesca. Francês: explicação B1. Inglês: duas instruções insuficientes. Outros exemplos da tabela são candidatos à revisão humana, sem certificar regras não verificadas de japonês/mandarim/latim.

## 10. Correções realizadas

Título público do seed vem do payload; conteúdo curado mantém `content_level` original sem romper o campo `level` solicitado; defaults ingleses removidos; Unicode nas palavras; gap de expressão única não entrega a resposta; distratores excluem variantes aceitas e duplicatas; idioma desconhecido rejeitado; ajustes objetivos EN/FR/IT; prompt reforça separação idioma-alvo/português; guard mínimo valida campos exigidos por modo, questões, código/nível declarado, gabarito único e clones ingleses conhecidos.

Guard não é detector linguístico geral, tradutor, verificador CEFR ou esquema JSON integral. Um texto inglês novo não presente no banco pode passar. Conteúdo com listas vazias ou outros campos semanticamente ruins ainda requer revisão/validação mais completa. Falhas seguem a cadeia existente de fallback de modelo; fora de produção pode haver mock, em produção indisponibilidade é explícita.

## 11. Arquivos modificados

`backend/app/api/lessons.py`; `backend/app/prompts/library.py`; `backend/app/services/activity_generator.py`; `ai.py`; `content_repository.py`; `grammar_practice.py`; `lesson_bank.py`; `lesson_bank_it.py`; `lesson_envelope.py`; `progression.py`.

## 12. Arquivos criados

`backend/app/services/editorial_validation.py`; `backend/scripts/audit_editorial.py`; `backend/tests/test_editorial_integrity.py`; `docs/editorial-audit-before.json`; `docs/editorial-audit-after.json`; `docs/editorial-audit-priorities-2026-10-05.md`; este relatório.

## 13. Conteúdo persistido: reparação futura

Local encontrado: zero unidades, nenhum reparo executado. Produção: contagem desconhecida. Atualização de código não reescreve Lessons/atividades/cache históricos. Seed idempotente pode atualizar starter quando executado; isso não autoriza execução em produção nesta rodada.

Plano antes de qualquer reparo: exportar backup e verificar restauração/cópia; identificar source.notes_json origin=lesson_bank_seed e unidades afetadas por idioma/modo/CEFR; emitir dry-run com IDs/contagens/diff; editar só campos verificados; transação e verificação pós-reparo. Não copiar todo o banco nem alterar provas históricas. Script corretivo/migration de dados depende do inventário real; nenhum foi executado ou inventado sem dados.

Consulta somente de identificação, para revisão posterior em PostgreSQL:

```sql
SELECT l.code, u.mode, u.cefr_level, COUNT(*) AS units
FROM content_units u JOIN languages l ON l.id=u.language_id
JOIN content_sources s ON s.id=u.source_id
WHERE s.notes_json->>'origin'='lesson_bank_seed'
GROUP BY l.code,u.mode,u.cefr_level;

SELECT u.id,l.code,u.mode,u.cefr_level,u.title,u.payload_json->>'title' AS payload_title
FROM content_units u JOIN languages l ON l.id=u.language_id
WHERE u.title LIKE '[starter] %';
```

Não executadas em produção. Confirmar tipos de JSON/modelos e política de backup no ambiente antes de qualquer script de escrita.

## 14. FRONTEND ISSUE

**Evidência estática, sem observação de tela:** `frontend/components/study.tsx:155` define voz `SPEECH_LANGS[languageCode] ?? en-US`. Se um payload receber código desconhecido, o fallback pode pronunciar em inglês. Não houve reprodução visual nem payload real desconhecido; oito códigos oficiais estão mapeados. Rota consumidora: lições/cronograma com AudioPlayer; exemplo de payload hipotético `language_code=pt-BR` — hipótese, não registro real. Componente provável/confirmado por fonte: AudioPlayer. Não editado.

Leitura usa `lesson.title` em `lesson-modes.tsx`; áudio de escuta usa `lesson.transcript` e `lesson.language_code`. O marcador inglês demonstrado vinha do backend, não foi atribuído erroneamente à UI. `missionTitle` prioriza objetivo/tópico/tema; não há evidência suficiente para responsabilizá-lo pela ocorrência francesa original.

## 15. Testes criados

`test_editorial_integrity.py`: título francês HTTP e helper; manutenção de título editorial; content_level versus level; foco FR; fonética IT; instruções EN; acessores sem fallback; rotas Piper seis idiomas e rejeição de ja/zh/unknown; texto francês preservado no request de áudio simulado; guard contra metadados incorretos, gabaritos ausentes, duplicatas, questões sem opções/scalar e clones ingleses longos/curtos; todos os modos mock/níveis/idiomas; gerador sem conteúdo inglês inventado, Unicode/apóstrofo, CJK, variantes aceitas e distratores duplicados.

## 16. Resultados de validação

**Suíte completa final: 1.492 passed, zero failed, 34 warnings existentes do Alembic, 989,63 segundos; exit code 0 confirmado.** 38 casos editoriais novos; execução focal final: 38 passed em 22,36 s. Ampliação com Teaching Engine/quality gate: 83 passed, quatro warnings. A primeira suíte completa foi interrompida para reiniciar sobre as correções finais; não é apresentada como validação concluída. Um teste de Piper inicialmente falhou por faltar chave no dublê, corrigido sem alterar o provedor. Revisão independente: brechas de guard e distratores corrigidas; inspeção final sem achados pendentes. compileall passou; git diff --check passou (apenas avisos de conversão CRLF do Git). Piper/STT externos não chamados.

## 17. Riscos e limites

Produção/DB histórica/cache não inspecionados; base local vazia. Áudio validado por contrato, sem ouvir síntese real; ja/zh-CN continuam sem voz Piper configurada no mapa. `content_level` é metadado de origem, não certificação de dificuldade; mock upper/IA sem level não têm nível editorial independente. Omissão de guided/transfer sem pedagogia pode reduzir a lista genérica; mecanismo existente fecha objetivo incompleto como needs_review, sem inventar domínio. Testes finais devem confirmar preservação do slice autoral EN.

## 18. Recomendações pedagógicas não implementadas

1. Revisar contexto e alternativas dos exercícios ES/DE/JA/ZH/LA com especialistas; priorizar respostas possíveis marcadas erradas. Revisar também nuances de tradução: FR upper traduz `sans doute` como certeza, enquanto o exercício ensina probabilidade; [Larousse registra o sentido provavelmente](https://www.larousse.fr/dictionnaires/francais/doute/26648/locution?q=sans+doute). O valor depende do contexto, por isso não houve troca global de tradução.
2. Criar perguntas específicas para cada texto/áudio, com evidência no trecho e distratores plausíveis. Gabarito genérico fixo não verifica compreensão.
3. Alinhar cenário, abertura e sugestões da conversa; no latim escolher objetivos de leitura/liturgia compatíveis com a variante autorizada.
4. Explicar casos/morfologia antes de avaliá-los; separar gramática por idioma, com progressão real, sem copiar distinções inglesas.
5. Ampliar textos/contextos por faixa, sobretudo C1/C2 e PRE_A1, sem trocar apenas rótulo. Manter repetição útil/SRS e orçamento 36/12; não concluir que toda repetição é defeito.
6. Inserir ou verificar carryover em conteúdo fixo antes de prometer que o aluno encontrará a palavra no áudio/texto; flexões precisam tratamento linguístico, não substring ingênua.
7. Pesquisa de 63 respostas, fornecida pelo usuário: repetição/conversa/gramática e pouco tempo orientam prioridades, mas não justificam regra universal ou reestruturação automática.

## 19. git diff --stat

```text
backend/app/api/lessons.py                 |   4 +-
 backend/app/prompts/library.py             |   6 ++
 backend/app/services/activity_generator.py | 102 ++++++++++++++---------------
 backend/app/services/ai.py                 |   3 +-
 backend/app/services/content_repository.py |   8 +++
 backend/app/services/grammar_practice.py   |   4 +-
 backend/app/services/lesson_bank.py        |  25 +++++--
 backend/app/services/lesson_bank_it.py     |   4 +-
 backend/app/services/lesson_envelope.py    |   1 +
 backend/app/services/progression.py        |   4 +-
 10 files changed, 91 insertions(+), 70 deletions(-)
```

Untracked não aparecem no diff stat padrão e são listados no status.

## 20. git status --short

```text
M backend/app/api/lessons.py
 M backend/app/prompts/library.py
 M backend/app/services/activity_generator.py
 M backend/app/services/ai.py
 M backend/app/services/content_repository.py
 M backend/app/services/grammar_practice.py
 M backend/app/services/lesson_bank.py
 M backend/app/services/lesson_bank_it.py
 M backend/app/services/lesson_envelope.py
 M backend/app/services/progression.py
?? backend/app/services/editorial_validation.py
?? backend/scripts/audit_editorial.py
?? backend/tests/test_editorial_integrity.py
?? docs/editorial-audit-2026-10-05.md
?? docs/editorial-audit-after.json
?? docs/editorial-audit-before.json
?? docs/editorial-audit-priorities-2026-10-05.md
```

Nenhuma alteração de frontend, preço, entitlement, infraestrutura ou fala estrutural.
