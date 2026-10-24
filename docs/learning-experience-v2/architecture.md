# Arquitetura — Learning Experience V2

A experiência de estudo separa o que o aluno produz do que o servidor decide. O frontend não inventa exercício, gabarito nem domínio.

## Idioma

O contrato vive em `backend/app/services/learner_language_contract.py`. O estímulo do aluno fica no idioma-alvo (`prompt` / `prompt_target`). O apoio na língua nativa só entra nos campos nativos, e o português legado só quando a língua nativa é `pt`, `pt-BR` ou `pt-PT`. `prompt_pt` não é promovido a `prompt_native`.

A família de interação sai do `type`. O mapa está em `docs/learning-experience-v2/interaction-families.md`. Tipo desconhecido vira `unknown` e não vira texto livre na tela.

## Como uma sessão nasce

O ciclo de vocabulário da lição (`POST /api/v1/lessons/{id}/vocabulary-cycle/start`) monta candidatos da própria lição, do objetivo e do banco curado. A fatia FR B1 entra por `curated_bank.candidates_for` quando o alvo é `fr`, o nativo é `pt-BR` e o nível é B1, com prioridade 0. O seletor (`plan_session`) corta visto, família repetida e conteúdo que não pode ser entregue. A dose do dia pede o orçamento curto (12 exercícios). A sessão longa fica para o aluno escolher no resumo.

A resposta de início e a de cada tentativa trazem `status` no topo e de novo em `flow.status`. Sem o status do topo, a tela tratava a primeira resposta como fim de sessão.

## Acerto, erro e retry

Erro não lexical fica na mesma atividade: o payload traz remediação e a fase `needs_remediation` ou `retrying`. Erro lexical aposenta a família nesta sessão e segue. O acerto no retry grava a reparação no motor que já existia.

A tela só diz que tentar novamente mantém a atividade quando a sessão ainda está nessa remediação. Se o fluxo já avançou, a correção anterior aparece com o rótulo «Correção da resposta anterior» e sem essa frase.

## Onde a interface entra

`frontend/lib/activity-registry.ts` liga cada tipo a um renderizador. `TeachingActivityBody` desenha a família e marca `data-interaction-family`. O shell, o caminho do dia e o resumo leem o payload; não calculam domínio.

## Banco local

Produção continua no PostgreSQL. O servidor de inspeção (`backend/scripts/dev_sqlite.py`) usa SQLite. Nesse motor, cada transação começa com `BEGIN IMMEDIATE` e espera até 30s se o arquivo estiver ocupado, para duas requisições seguidas não derrubarem a segunda com `database is locked`. A suíte pytest segue no SQLite em memória próprio do `tests/conftest.py`, não nesse motor.
