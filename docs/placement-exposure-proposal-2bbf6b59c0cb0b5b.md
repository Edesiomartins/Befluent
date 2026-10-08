# Placement: exposição, reuso e progresso — proposta

ID: 2bbf6b59c0cb0b5b. Data: 08/10/2026. Status: decisão proposta, sem implementação ou alteração em produção.

## Auditoria verificável

- PlacementTest contém user_id e language_code. Delivery contém item_id, delivered_at, consumed_at e vínculo ao teste; Answer contém item_id e vínculo ao teste. Existem dados para reconstruir exposição por conta/idioma enquanto essas linhas existirem.
- Delivery comprova disponibilização pelo servidor, não leitura efetiva nem reprodução de áudio. Answer comprova submissão. Para histórico, entrega é tratada conservadoramente como seen; respostas sem delivery também contam como exposição, sem duplicar o evento quando ambos existem.
- Não há feedback_revealed no placement. O campo revealed_correct_answer encontrado pertence a outra estrutura de aprendizagem e não comprova revelação de placement. Desconhecido não será transformado em false confirmado.
- _pick_objective_item exclui answered_ids apenas da sessão atual. A proteção recente por fingerprint também se restringe aos itens respondidos na sessão atual. Entregas abandonadas e testes anteriores não são consultados. Produção escrita/fala também precisa consultar exposição.
- evidence_fingerprint atual considera prompt/passagem/audio_script/opções no mesmo hash. Mudar uma pergunta pode ocultar reuso da mesma passagem ou áudio; versões, gabarito e audio_url sem script não têm tratamento completo. É proteção contra duplicata literal, não detector geral de semântica.
- A API pública omite gabarito/rubrica/explicação do item. Submit objective retorna accepted/progress; runner chama next-item sem exibir correção imediata. Não há evidência de ensino de gabarito objetivo nesse fluxo. Histórico de terceiros/clientes antigos e playback não são certificados.
- Runner exibe “Atividade ... de aproximadamente target” e percentagem answered/target; intro de retomada exibe answered/target. answered hoje conta objetivos, não todas as atividades concluídas de escrita/fala. O texto de encerramento é genérico e não discrimina motivo.
- Reset inclui placement_tests, placement_test_answers e placement_item_deliveries no conjunto deletado. Usar apenas essas tabelas perderia exposição após reset.

## Decisão recomendada

### 1. Histórico durável por conta e idioma

Uma migration aditiva simples cria placement_item_exposures, independente de UserLanguage e do ciclo de reset pedagógico. Cada evento representa uma entrega lógica, com user_id, language_code, item_id opcional, test_id opcional, delivery_id/origin_key, first_seen_at, answered_at e feedback_revealed_at opcional; guardar também origem e estado de revelação known/unknown. IDs de teste/item podem ficar NULL após exclusão, mas snapshots das chaves de conteúdo permanecem. Exclusão definitiva da conta elimina seu histórico; reset pedagógico comum o preserva.

Guardar versão das chaves, item/version/skill/CEFR de origem e snapshot mínimo de hashes no momento da entrega. Não usar apenas conteúdo atual mutável para reconstituir o que alguém viu. Não armazenar áudio/texto pessoal nesse ledger. Entrega repetida da mesma delivery atual é idempotente: não vira nova exposição. Nova sessão/reentrega real representa outro evento.

Histórico legado será lido de delivery/answer além do ledger e deduplicado por evento. Importação histórica, se desejada, será operação separada com dry-run; não haverá escrita automática em produção nem alteração de resultados completed. Conteúdo antigo sem snapshot terá provenance=legacy_current_item, com limitação explícita.

### 2. Chaves determinísticas, com limites declarados

- exact_item_key: conteúdo normalizado da tarefa, opções ordenadas por conteúdo e gabarito representado por conteúdo, independente de item_id, external_key, CEFR atribuído, versão e ordem das opções. Incluir instruções relevantes e estímulo. Normalização versionada de Unicode/espaços/formatação; evitar remover distinções linguísticas relevantes.
- passage_key e audio_script_key: chaves independentes para estímulos substanciais. Pergunta diferente sobre a mesma passagem/áudio continua com estímulo conhecido. URL sem script usa chave de recurso com origem declarada; não comprova identidade de áudios servidos por URLs diferentes.
- prompt_key: ancora tarefas sem passagem/áudio e prompts de produção; instruções genéricas compartilhadas não tornam todo o banco um clone.
- stimulus_family_key opcional editorial reúne paráfrases, gravações alternativas e versões conhecidas de uma mesma tarefa. Não haverá embeddings, novo modelo ou promessa de detectar toda paráfrase.
- Opções/gabarito iguais com enunciados e estímulos distintos NÃO bastam para declarar clone. Dois itens sobre o mesmo estímulo podem conservar scores, mas não constituem duas fontes independentes para confirmar a faixa. Preflight e evidence support contarão grupos independentes, além de itens.

### 3. Seleção e evidência

Retomar delivery aberta da sessão atual sem marcar um falso retest. Para nova entrega, buscar exposição em todos os testes anteriores/abandonados/checkpoints da mesma conta e idioma, usando IDs e chaves fortes. Separar pools inéditos e conhecidos antes de ordenar por déficit de skill e proximidade CEFR.

Enquanto existir candidato inédito compatível com as skills necessárias e faixas testáveis permitidas, não escolher conhecido, mesmo que este esteja mais perto da faixa corrente. Compatibilidade não autoriza outra skill/idioma inválido nem faixa fora do escopo; fallback de faixa é explícito e não contamina streak.

Decisão conservadora inicial: reuso tem score observado preservado, mas eligible_for_level=false e eligible_for_overall=false. Não conta para mínimo de evidências válidas/independentes, confirmação, promoção/rebaixamento adaptativo nem confiança de suporte. Não multiplicar score por 0,5 ou outro peso inventado. Isso também se aplica a escrita/fala repetidas, que já são provisórias.

Quando não houver inéditos úteis, padrão assessment encerra com bank_freshness_exhausted e perfil parcial. Não obrigar repetição inútil para preencher volume. Se um fluxo explicitamente permitir fallback de reuso, ele precisa marcar reused=true, previous_exposure_count, exposure_status, stimulus_reused, reuse_reason e inelegibilidade antes da resposta; o teste de fallback verificará esse ramo. Escolher nunca revelados antes de revelados, depois menor exposição e maior intervalo; desconhecido é declarado. Nenhum gabarito revelado ganha preferência sobre inédito.

Orçamento máximo conta todas as atividades objetivas respondidas, inclusive reutilizadas; suporte e adaptação contam apenas inéditas válidas. Essa separação evita loop infinito ao excluir reutilizados da evidência. Conclusão permanece idempotente e atômica. Usar ordem consistente de locks User -> PlacementTest ao registrar/selecionar, inclusive duas sessões simultâneas da mesma conta; PostgreSQL precisa ensaio dedicado.

### 4. Resultado coverage v2

Adicionar policy_version/exposure_policy_version e campos:

- Por entrega/resposta: exposure_status=fresh|seen|answered|feedback_revealed|legacy_unknown, reused, previous_exposure_count, stimulus_reused, evidence_eligible e razões. Seen/answered/revealed são fatos acumuláveis; status é resumo, não substitui flags/timestamps.
- Por skill: evidence_counts answered/fresh/reused/excluded/independent; exposure_adjusted_evidence_support com suporte qualitativo suficiente/insuficiente e razões. Nenhuma probabilidade estatística.
- assessment_coverage.bank_freshness: grupos fresh/seen/revealed/unknown disponíveis por skill/CEFR; separar capacidade total de capacidade inédita pessoal. freshness_ratio, se usado internamente, mede proporção de catálogo, não confiança ou proficiência.
- stop_reason e missing_skills explícitos. Overall mantém os gates v2, agora exigindo evidência inédita independente. Reused evidence nunca aumenta suficiência.

### 5. Assessment, review e rotação

Assessment pontuado permanece sem gabarito ou explicação por item, inclusive no JSON retornado por submit. Resultado oferece perfil e recomendações, sem reproduzir gabaritos protegidos. Revisão/ensino será modo explícito separado; qualquer revelação de resposta correta registra feedback_revealed, tornando família/estímulo conhecido para retest.

Forms começam como metadados de banco (form_id, rotation_group, stimulus_family), com política/versionamento gravados no test.result_json. Validar a matriz independente por skill/CEFR antes de ativar uma form; preferir form com mais conteúdo inédito para a conta. Rotação é critério secundário: não ultrapassa exclusão de exposição ou déficit de skill.

Chamar “forms operacionais”, não “formas psicometricamente equivalentes”. Dividir o banco atual em A/B não cria cobertura nem equivalência e pode piorar a insuficiência. Sem banco suficiente, informar déficit e encerrar parcial.

### 6. Retest e reset — decisão a aprovar

Proposta operacional: 30 dias entre sessões completas de retest pontuado, inclusive quando a anterior terminou parcial. O intervalo não restaura ineditismo nem apaga exposição. Complemento de perfil parcial pode ocorrer antes somente com conteúdo novo suficiente/útil; não gerar novo global por repetir a mesma amostra. Retomada de sessão aberta não é retest. Expor available_at e motivos; número é regra operacional revisável, sem alegação científica.

**Reset real preserva exposure history por padrão.** CLI técnico terá --clear-placement-exposure explícito, no mesmo seletor de uma única conta, dry-run/--apply/--rollback e contagens separadas. Limpeza técnica permitida apenas em ambiente/banco de teste verificado; impedir opção em produção. Não contornar cooldown com limpeza de histórico de aluno real. Reset de dados de teste em produção permanece sujeito a operação distinta explicitamente autorizada, não a este flag.

### 7. UX proposta

- Remover denominador, “aproximadamente 20” e barra percentual baseada em target tanto do runner quanto da retomada.
- Mostrar “17 atividades concluídas”, contando respostas objetivas e produções efetivamente submetidas; puladas têm contador separado e não passam por concluídas com evidência.
- Por skill, mostrar contagem e estado: em coleta, evidência insuficiente, estimativa provisória, coleta encerrada. Não exibir porcentagem de domínio a partir de contagens.
- planned_target é orçamento interno; não promessa ao aluno. Não forçar vinte itens.
- ready_to_complete com cobertura: “Coleta concluída. As evidências previstas foram reunidas.” Não afirmar nível global suficiente antes do cálculo final.
- bank_exhausted/bank_freshness_exhausted: “A coleta foi encerrada porque não há mais atividades inéditas adequadas disponíveis. Você receberá um perfil parcial.” Sem fingir critério pedagógico satisfeito quando o motivo é limitação do banco.
- maximum_reached: “A coleta atingiu o limite desta sessão. Vamos apresentar as evidências disponíveis.”
- Não tratar item=null isoladamente como sucesso normal se stage/motivo são inválidos; mostrar recuperação de erro.

## Plano de execução após aprovação

1. Testes de exposição/normalização/deduplicação e auditoria read-only; migration/ledger e integração com reset preservador.
2. Seletor por freshness/skill/CEFR, snapshots na entrega, retomada e concorrência; incluir produção.
3. Exclusão de reuso do suporte/adaptação, contrato v2 e preflight pessoal; retest operacional e forms por metadados.
4. UX sem total prometido; encerramento por motivo, contadores por skill e modo assessment protegido.
5. Regressões focais, suíte relevante, migração e ensaio PostgreSQL dedicado; sem publicar ou alterar produção.

## Testes de aceitação

- Primeiro placement fresco; segundo evita entregas vistas inclusive sem resposta; inédito em faixa permitida vence conhecido na faixa preferida; reuso permitido apenas após esgotamento e explicitamente marcado.
- previous_exposure_count idempotente em retries, histórico sem delivery deduplicado, clones com IDs/versões/opções reordenadas, mesma passagem/áudio com perguntas diferentes, opções iguais com estímulos distintos não colidem.
- Reuso/revelação não contam para faixa/mínimo/confirmação/global; preservam score descritivo e motivo. Revelado nunca vence inédito. Unknown não vira confirmação de ausência de feedback.
- Contas e idiomas isolados; escrita/fala repetidas e duas sessões concorrentes; sessão aberta não gera falsa nova exposição; item editado não apaga snapshot.
- Reset padrão preserva ledger; flag técnico limpa só conta selecionada, recusa produção, dry-run não escreve, rollback restaura tudo. Exclusão definitiva da conta remove ledger.
- Frontend: 17 atividades e resultados abaixo/acima de20; target ausente/zero/20 não afeta total mostrado; ready_to_complete, bank_exhausted, bank_freshness_exhausted, máximo, partial; sem gabarito/explicação no fluxo assessment; puladas separadas de submetidas e barra sem porcentagem enganosa.

## Limites

Auditoria de código local; não foi consultado inventário live nem telemetria de leitura/playback. Histórico já apagado não pode ser recuperado sem fonte externa. Hash determinístico protege clones triviais/estímulos conhecidos, não toda equivalência semântica. Sem IRT, provider/modelo novo ou escrita em produção. Nenhum teste de implementação executado nesta etapa de decisão.
