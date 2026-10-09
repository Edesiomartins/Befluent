# Placement: cobertura obrigatória 16 + até 4

ID: `2bbf6b59c0cb0b5b`. Backend local, 2026-10-09.

## Policy e ordem efetiva

Novos placements normais usam `placement-coverage-v3`: VG6, Reading4, Listening4, Writing1, Speaking1. A quota conta atividades independentes e elegíveis; o total bruto não substitui a quota. Depois da cobertura, até quatro objetivas adicionais quando há candidata não confirmada ou faixa ainda insuficiente. Limite absoluto: 20 atividades concluídas. As policies de estimativa, produção provisória e planning foram preservadas.

1. Retomar delivery aberto.
2. Buscar apenas skills deficitárias. Objetivas primeiro, ordenadas pela menor razão completed/required; desempate VG, Reading, Listening. Writing e Speaking vêm depois das objetivas disponíveis, antes de qualquer extra.
3. Dentro da skill, usar a adaptividade de faixa existente e exigir conteúdo fresh/independente, com apoio no idioma nativo declarado.
4. Sem conteúdo elegível, persistir a exceção da skill e continuar as outras quotas.
5. Com quotas satisfeitas ou exceções reais explícitas, priorizar confirmação pendente mais próxima de resolver; depois faixa insuficiente. Não coletar extra só para aumentar confiança.
6. Encerrar assim que não houver necessidade disponível, após quatro extras ou ao atingir 20 concluídas.

## Encerramento e produção

`complete` recusa atividade aberta ou coleta necessária disponível. `ready_to_complete` exige quotas satisfeitas ou motivos explícitos por skill: `user_skipped`, `microphone_unavailable`, `production_unavailable`, `hard_technical_failure`, `bank_freshness_exhausted`, `bank_exhausted`, `maximum_reached`. Motivos de skip são informados pelo usuário e identificados como `user_reported`; não são diagnóstico automático do dispositivo.

Writing enviado conta como produção coletada e continua sujeito à policy provisória atual. Speaking usa o banco versionado existente de fala espontânea/semiespontânea, sem substituir pela leitura em voz alta; upload, transcrição no servidor, retry, limpeza de áudio e limite técnico de 90 segundos permanecem. Falha de reconhecimento não cria resposta concluída. Skip é separado e não fabrica nível.

Normalmente são 16 concluídas; necessidade resolvida permite parar em 17/18; conflito pode consumir quatro extras e parar em 20 mantendo perfil parcial. Exceções podem resultar em menos de 16 concluídas, com `assessment_status=incomplete` e déficit explícito.

## Contrato aditivo

`progress.assessment_coverage` e o resultado final expõem:

```json
{
  "coverage_policy_version": "placement-coverage-v3",
  "minimum_total": 16,
  "maximum_total": 20,
  "completed_total": 16,
  "completed_activities_total": 16,
  "objective_answered": 14,
  "writing_submitted": true,
  "speaking_submitted": true,
  "skipped_productions": {"writing": 0, "speaking": 0},
  "mandatory_complete": true,
  "mandatory_resolved": true,
  "adaptive_completed": 0,
  "adaptive_budget": 4,
  "skills": {
    "vocabulary_grammar": {"required": 6, "completed": 6, "satisfied": true, "deficit": 0, "skipped": 0, "reason": null},
    "reading": {"required": 4, "completed": 4, "satisfied": true, "deficit": 0, "skipped": 0, "reason": null},
    "listening": {"required": 4, "completed": 4, "satisfied": true, "deficit": 0, "skipped": 0, "reason": null},
    "writing": {"required": 1, "completed": 1, "satisfied": true, "deficit": 0, "skipped": 0, "reason": null},
    "speaking": {"required": 1, "completed": 1, "satisfied": true, "deficit": 0, "skipped": 0, "reason": null}
  }
}
```

Valores acima são exemplo de contrato, não medição de uma conta. `completed_total` é bruto: objetivas respondidas + produções enviadas. Reused/clones podem estar no bruto e não contar em `skills.*.completed`. Delivery aberto e skip não entram no bruto. `mandatory_complete` significa cobertura; `mandatory_resolved` também aceita exceções explicadas, sem dizer que a cobertura foi satisfeita.

Resultado também expõe os contadores no topo, `assessment_status=complete|incomplete` e os status de perfil/global já existentes. Cobertura completa + global suficiente, cobertura completa + perfil parcial e cobertura incompleta são distintos. `planning_level_trace` inclui assessment_status, mandatory_complete, policy e déficits. Candidate continua separado de estimated/overall; planning continua sendo a decisão aplicada/preservada.

Por skill objetiva: `confirmation_count` é a quantidade de evidências independentes na faixa candidata; `confirmation_required_total` é o total exigido pela policy atual; `confirmation_remaining=max(total-count,0)`. `confirmation_needed` mantém o significado antigo de TOTAL. Exemplo: count1/total2/remaining1. Remaining0 não garante confirmação se há conflito ou acurácia insuficiente; consumir `confirmation_required` e `candidate_reason` também.

Resultados históricos e checkpoints mantêm suas policies. Sem migration, backfill ou reclassificação. Fixtures antigas são explicitamente históricas; testes v3 criam sessão pelo endpoint público real.

## Alterações e defeitos

- `backend/app/api/placement_tests.py`: coverage-first, fase extra, guards de complete, contadores, exceções e trace.
- `backend/app/services/placement_coverage.py`: quotas e snapshot separado da suficiência CEFR.
- `backend/app/services/placement_engine.py`: aliases aditivos de confirmação, sem alterar limiares.
- `backend/app/schemas/__init__.py`: motivo explícito de skip compatível com payload anterior.
- `backend/tests/test_placement_mandatory_coverage.py`: regressões do fluxo v3.
- `backend/tests/test_placement_api.py`: fixture v2 explícita para regressões históricas.
- `backend/tests/test_placement_completion_postgres.py`: completion paralelo também parametrizado para v3.

P0: nenhum identificado. P1 reproduzidos e corrigidos: conclusão antecipada com quotas abertas; confirmação de R/L tomando prioridade sobre déficit de outra skill; contrato sem quota/contadores explícitos e sem quantidade restante de confirmação. Os seis testes iniciais falharam antes da implementação e passaram depois.

Backlog P2: quando extras necessários não têm item disponível, o motivo terminal ainda é `bank_freshness_exhausted`, mesmo quando falta conteúdo editorial; quotas deficitárias têm distinção específica. Calibração psicométrica, expansão editorial e apoio nativo além do catálogo atual continuam fora desta rodada. Sem P3 novo.

## Validação

- Focal v3 + compatibilidade: **150 passed, 0 skipped, 0 failed**, 141,54s, exit0. Inclui 23 casos v3. Evidência: [focal.log](focal.log).
- Suíte backend integral local sem túnel: **1.756 passed, 5 skipped, 0 failed**, 40 warnings, 1119,28s, exit0. Os cinco skips PostgreSQL desta rodada não são aceitos como certificação; a suíte será repetida com a conexão disponível.
- PostgreSQL obrigatório: preflight PASS após o usuário restaurar o túnel. SQL confirmou **PostgreSQL18.6**, `server_version_num=180006`, database e usuário **befluent_test**, endpoint autorizado `127.0.0.1:55432`, nome terminado em `_test`. `DATABASE_URL=sqlite://` no processo da aplicação; credencial de PostgreSQL somente no processo de teste. Evidência sem senha: [postgres-preflight.json](postgres-preflight.json).
- PostgreSQL focal: **5 passed, 0 skipped, 0 failed**, 314,09s, exit0. Completion paralelo/stale/downstream aprovado em v2 e v3; criação/delivery/exposure paralelo aprovado; cross-schema cascade refusal aprovado; fencing de soft pointers de outra conta no reset aprovado. Evidências: [postgres-tests.log](postgres-tests.log), [exit code](postgres-tests-exit.json).
- Suíte backend integral final com POSTGRES_TEST_URL disponível: **1.761 passed, 0 skipped, 0 failed**, 40 warnings Alembic preexistentes, 1171,80s (19min31s), exit0. Todos os cinco casos PostgreSQL executados novamente. Evidências: [full-suite.log](full-suite.log), [exit code](full-suite-exit.json). Substitui a rodada local com skips como evidência final; contagens dos conjuntos focal/integral se sobrepõem.
- `python -m compileall -q app tests`: **PASS**, exit0. `git diff --check`: **PASS**, exit0. Evidência: [checks.json](checks.json).

Cobertura dos cenários obrigatórios: 1–3 guards de conclusão/quota e speaking0; 4–10 fluxo normal, prioridade R/L, paradas16/17/18 e quatro extras/20; 11–14 skips parametrizados, microfone/falha técnica e banco vazio; 15 independência/reuso/clones; 16–17 candidate/overall/planning; 18–19 repeat complete/GET e histórico intacto; 20–21 total/restante de confirmação; 22 banco espontâneo e recusa de leitura em voz alta; 23 idioma nativo; 24 currículo parcial e planning anterior; 25 regressões existentes de reset/exposure incluídas na suíte integral. Concorrência PostgreSQL exige o gate real, não é certificada por SQLite.

Somente backend/testes/documentação. Nenhuma senha salva; nenhum acesso à produção, frontend alterado, commit, push ou deploy.

Ambiente PostgreSQL: mesma implementação Python do psycopg3.2.13 com libpq18.3 já instalada e permitida pelo Windows, configurada somente no processo. Sem mudança de driver/dependências ou de políticas do sistema; é o mesmo procedimento da certificação anterior.

**READY FOR FRONTEND CONTRACT**. Todos os gates obrigatórios concluídos. Nenhum refinamento adicional nesta rodada.
