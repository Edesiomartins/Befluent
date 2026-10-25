# Progresso — Layout v1

Rodada 4, somente frontend, em 2026-10-24. Branch `main` local. Sem push, sem deploy e sem banco de produção.

Banco das capturas: SQLite `backend/tmp/layout-v1.sqlite3`. API em `127.0.0.1:8011`, Next em `127.0.0.1:3011`. IA em modo mock.

| Item | Status | Commit | Testes do item |
|---|---|---|---|
| 1 modo foco | implementado | `a465cba` | `tests/focus-session.test.tsx` + ciclo de vocabulário |
| 2 feedback em painel | implementado | `9c50542` | `tests/feedback-sheet.test.tsx` + ciclo |
| 3 dashboard enxuto | implementado | `05f71bf` | `tests/dashboard.test.tsx` |
| 4 navegação móvel | implementado | `453a20d` | `tests/shell.test.tsx` |
| 5 trilha do cronograma | implementado | `a3f201a` | `tests/journey-trail.test.tsx` |
| 6 paleta | implementado | `daedb9b` | `tests/language-accent.test.tsx` |
| 7 tipografia do alvo | implementado | `6b72365` | `tests/bilingual.test.tsx` |
| 8 resumo com celebração | implementado | `c192fe1` | `tests/session-summary.test.tsx` |

Cada item fechou com `npm test`, `npm run typecheck` e `npm run lint`. No item 8: 396 passed, 51 arquivos, typecheck exit 0, lint exit 0 com 0 erros e 5 warnings anteriores.

Suíte final, repetida depois das capturas: `npm test` 396 passed, 51 arquivos, exit 0, 12,89s. `npm run typecheck` exit 0. `npm run lint` exit 0, 0 erros, 5 warnings anteriores (`objective-choice.tsx`, `lesson-adaptation.test.tsx`, `speech-ui.test.tsx`). Backend sem mudança: a suíte de 1864 testes da rodada 3 não foi reexecutada.

## O que cada item fez

1. A sessão de vocabulário aberta esconde menu e cabeçalho. Barra de progresso fina no topo, atividade no centro e botão grande fixo embaixo (Verificar, ou Continuar quando a atividade só pede reconhecimento). Sair pede confirmação. Escape fecha o diálogo. O dia do cronograma e o objetivo continuam com o chrome reduzido de antes.
2. Acerto e erro abrem um painel inferior verde ou vermelho, com a correção, uma explicação curta, Continuar e, quando a mesma atividade segue aberta, Tentar novamente. A tela não troca. O foco vai para o título e o resultado é anunciado com `aria-live`.
3. A home tem um CTA, «Continuar a missão de hoje», com sequência e meta diária ao lado. Nível, plano, revisões, prática livre e atividade recente foram para `/dashboard/estudo` e `/dashboard/pratica`. A página de 563 linhas virou `home-focus`, `study-details`, `practice-details`, `level-block`, `dashboard-state`, `use-dashboard` e `types`.
4. No celular, a barra inferior tem Hoje, Aprender, Progresso e Perfil. No desktop, a lateral e o topo permanecem.
5. As semanas do plano viram uma trilha: concluída, atual e bloqueada. A atual é link. As bloqueadas recebem foco por seta e `aria-disabled`, sem ser botão `disabled`.
6. Acentos do chrome: azul primário, sucesso, erro e streak. `--gold`, `--violet`, `--teal`, `--rose` e `--info` saíram. Cada idioma alvo tem uma tinta própria em `--language-accent`. O teste de contraste exige 4,5:1 no branco e no fundo suave. O axe no jsdom não mede contraste de cor do Tailwind.
7. O texto no idioma alvo usa 20px e entrelinha 32px. A instrução na língua nativa fica numa faixa separada. O botão Ouvir fica ao lado do enunciado.
8. O resumo anima o título só com `motion-safe`. Acertos, palavras dominadas e minutos aparecem quando o payload traz `correct_count`, `mastered_words` e `elapsed_minutes`. «Dominado» continua só com `mastered`.

## Decisões

- O modo foco liga quando o ciclo de vocabulário está ativo. «Vocabulário em dia» mantém o cabeçalho reduzido «Voltar à prática».
- Tentar novamente e Continuar aplicam a mesma resposta da sessão. O painel só oferece Tentar novamente quando a atividade seguinte é a mesma.
- Sem feedback no payload, a sessão avança na hora. Reconhecimento sem item de vocabulário usa Continuar.
- Acento de idioma é token no `documentElement`, não uma cor nova de botão. `--warning` aponta para `--streak`.
- O backend não envia os três números da celebração. O resumo real mostra o título e o texto que já existia. Nenhuma mudança de backend nesta rodada.

## Capturas

Antes: `docs/layout-v1/before/`, 14 imagens, desktop 1280×800 e mobile 390×844.

Depois: `docs/layout-v1/after/`, as mesmas 14 telas.

O dashboard, a trilha e a barra inferior aparecem nas capturas. A sessão, o feedback e o resumo fotografados são a prática do dia: o ciclo livre de `/learn/vocabulary` respondeu `no_vocabulary_due` («Vocabulário em dia») para a conta local usada. O painel inferior e o modo foco ficaram cobertos pelos testes, não por essas três imagens.

## Pendências

- O resumo da sessão real não mostra acertos, palavras dominadas nem minutos até o backend enviar esses campos.
- A prática livre não abre o modo foco quando não há item devido.
- A página do dia ainda usa «Enviar tentativa» e o chrome «Voltar ao plano».
- Contraste AA foi medido nos tokens, não pelo axe no navegador.
- IA continua em modo mock. Sem escolha de provedor.

## Atualização — Reformulação Híbrida de Alta Precisão (2026-10-24)

- Direção aplicada: SaaS de alta precisão (estilo Linear / Stripe) com arquitetura híbrida (*Command Dark* `#0B1220` na sidebar, cabeçalho de estudo e hero cards de missão/plano/progresso + *Studio Light* `#F3F6FB`/`#FFFFFF` nos exercícios e listas).
- Especificação: `docs/superpowers/specs/2026-10-24-hybrid-precision-layout-design.md`.
- Validação completa: `npm test` (51 arquivos, 396 passed, exit 0), `npm run typecheck` (exit 0), `npm run lint` (0 erros, 5 warnings anteriores).
- Capturas `docs/layout-v1/after/` (14 PNGs desktop e mobile) atualizadas com o novo layout.

## Rodada 5 — Ajustes pós-layout híbrido (2026-10-25)

| Item | Status | Commit | Escopo |
|---|---|---|---|
| 1 cor do idioma no `.command-panel` | implementado | `867f675` | Brilho radial usa `color-mix(in srgb, var(--language-accent) 26%, transparent)` mantendo contraste AA >= 4,5:1 |
| 2 dashboard sem espaço vazio | implementado | `11dda67` | Bloco leve abaixo dos links secundários com revisões pendentes de hoje (quantidade e próximo item) e trilha da semana, com estado vazio honesto |
| 3 contraste real no navegador (Playwright + axe-core) | implementado | `8233d99` | `--command-muted` elevado para `#cbd5e1`, `MasteryProgressChart` adaptado ao `.command-panel` escuro e título do `FeedbackSheet` em `--danger-shadow`/`--success-shadow` |
| 4 página do dia alinhada ao FocusFrame | implementado | `1ea9c0d` | Botão da prática interativa do dia trocado de «Enviar tentativa» para «Verificar» e cabeçalho «Voltar ao plano» alinhado ao trilho superior do `FocusFrame` |
| 5 prática livre em modo foco mesmo sem itens devidos | implementado | `faf567d` | Quando `no_vocabulary_due`, abre `FocusFrame` com sessão curta de prática sem alterar nem inventar progresso de domínio |
| 6 resumo da sessão com métricas reais | implementado | `eec5609` | Backend envia `correct_count`, `mastered_words` e `elapsed_minutes` reais no encerramento da sessão; frontend exibe somente o que vier preenchido |
| 7 housekeeping `.gitignore` | implementado | `199dee4` | `backend/scripts/out/` adicionado ao `.gitignore` |

### Achados do axe no navegador (`docs/layout-v1/axe-contrast-report.json`)
- Antes das correções da Rodada 5, a auditoria com Playwright + `axe-core` detectou:
  1. `MasteryProgressChart` dentro do `.command-panel` em `/progress`: `figcaption` (`#475569` sobre `#111c33`, contraste `2.23:1`) e `summary` «Ver dados» (`#2563eb` sobre `#111c33`, contraste `3.28:1`), além de `scrollable-region-focusable` em `390px` causado por `min-w-[20rem]` no `<svg>`.
  2. `FeedbackSheet` aberto em estado de erro (`feedback`): `h2` «Resposta incorreta» com `#dc2626` sobre `#fbe9e9` (`bg-danger/10`) tinha contraste `4.12:1` (< 4,5:1).
- Após elevar `--command-muted` para `#cbd5e1`, ajustar `MasteryProgressChart` para o fundo escuro e usar `--danger-shadow` (`#a51818`, contraste `6.45:1`) e `--success-shadow` (`#0f7a37`, contraste `5.12:1`) no título do `FeedbackSheet`: **0 violações** (`violations=0`, `flatContrast=0`, `lowCommandNodes=0`, contraste mínimo em superfícies escuras `>= 5.17:1`) nas 12 telas auditadas (`dashboard`, `cronograma`, `dia`, `sessao`, `feedback`, `progresso` em desktop `1280×800` e mobile `390×844`).

### Suíte final da Rodada 5
- Frontend: `npm test` **400 passed** (51 arquivos, exit 0), `npm run typecheck` exit 0, `npm run lint` exit 0 (0 erros, 5 warnings anteriores).
- Backend: `py -3 -m pytest` nos 15 módulos de sessão/ensino/ciclo lexical (**262 passed**, exit 0).
- Capturas `docs/layout-v1/after/` (14 PNGs) regeneradas incluindo o `FocusFrame`, o `FeedbackSheet` e o `SessionSummary` reais em `/learn/vocabulary`.
