# Design: Reformulação Visual Híbrida de Alta Precisão (BeFluent)

**Data:** 2026-10-24
**Direção escolhida:** Opção B + C — SaaS de alta precisão (estilo Linear / Raycast / Stripe) com arquitetura **Híbrida** (Shell lateral e superfícies de comando/missão em slate-navy profundo `#0B1220`, área central de leitura/exercícios em superfície clara cirúrgica de alto contraste).

## 1. Objetivo
Elevar a apresentação visual de todo o webapp BeFluent para um padrão de produto SaaS profissional, substituindo a aparência de cartões genéricos por uma arquitetura de superfícies em camadas, bordas hairline (`1px`), tipografia técnica com números tabulares (`tabular-nums`) e contraste intencional entre áreas de comando (escuras) e áreas de leitura/estudo (claras), preservando 100% dos contratos pedagógicos e testes de acessibilidade.

## 2. Sistema de Tokens (`frontend/app/globals.css`)
- **Camada Command Dark (Shell & Hero de Missão):**
  - `--command-bg`: `#0b1220`
  - `--command-surface`: `#111c33`
  - `--command-elevated`: `#172542`
  - `--command-border`: `rgba(255, 255, 255, 0.08)`
  - `--command-text`: `#f8fafc`
  - `--command-muted`: `#94a3b8`
- **Camada Studio Light (Canvas & Exercícios):**
  - `--background`: `#f3f6fb`
  - `--surface`: `#ffffff`
  - `--surface-soft`: `#eef2f8`
  - `--surface-elevated`: `#e7edf6`
  - `--text-primary`: `#0f172a`
  - `--text-secondary`: `#475569`
  - `--border`: `#dce3ee`
  - `--border-strong`: `#cbd5e1`
- **Acentos Semânticos (Preservados com Contraste AA >= 4.5:1):**
  - `--primary`: `#2563eb` (`--primary-hover`: `#1d4ed8`)
  - `--success`: `#15803d`
  - `--danger`: `#dc2626`
  - `--streak`: `#9a3412` (`--warning`: `var(--streak)`)
  - `--language-accent`: dinâmico por idioma-alvo (`en`, `es-ES`, `fr`, `it`, `de`, `ja`, `zh-CN`, `la`)
- **Classes Utilitárias Estruturais:**
  - `.panel`: superfície clara com borda hairline `1px solid var(--border)` e sombra multicamada sutil (`0 1px 2px rgba(15, 23, 42, 0.04), 0 6px 16px -4px rgba(15, 23, 42, 0.04)`).
  - `.command-panel`: superfície escura (`#0b1220` → `#111c33`) com borda interna `rgba(255, 255, 255, 0.09)` e brilho radial discreto.
  - `.tech-badge`: cápsula técnica compacta com borda hairline e números tabulares.

## 3. Componentes e Telas Alvo
1. **Shell Híbrido (`components/shell.tsx`, `components/logo.tsx`):**
   - Sidebar desktop em `#0B1220` (`w-64`), logo em variante clara, links com indicador lateral luminoso quando ativos e rodapé de conta estruturado.
   - Header superior com barra translúcida (`backdrop-blur`), seletor de idioma em formato *command pill* e atalho de perfil/admin.
   - Barra inferior mobile (`MobileNav`) com superfície translúcida, borda superior definida e indicador ativo preciso.
2. **Primitivos de UI (`components/ui.tsx`):**
   - `Button`, `Input`, `PasswordInput`, `Toggle`, `EmptyState` e `ErrorState` com acabamento de precisão, sombras sutis em botões primários/secundários e foco nítido.
3. **Dashboard (`components/dashboard/*`):**
   - `HomeFocus`: cartão principal da Missão de Hoje em `.command-panel` escuro de alto destaque com CTA «Continuar a missão de hoje»; cartões laterais de Sequência e Meta Diária com tipografia tabular de painel analítico e barra de links secundários estruturada.
   - `StudyDetails` e `PracticeDetails`: painéis organizados com divisórias hairline e cabeçalhos técnicos.
4. **Cronograma e Jornada do Dia (`app/(app)/cronograma/page.tsx`, `app/(app)/cronograma/dia/[id]/page.tsx`, `components/journey-trail.tsx`):**
   - Cabeçalho executivo de progresso do plano, cartão de retomada rápida e `JourneyTrail` estilizado como pipeline vertical.
   - Na Jornada do Dia: cabeçalho da missão em `.command-panel` escuro com barra de progresso integrada, coluna lateral de sequência do dia estilo *stepper* técnico e área de atividade limpa.
5. **Sessão em Foco, Feedback e Atividades (`components/focus-session.tsx`, `components/feedback-sheet.tsx`, `components/activities/*`):**
   - `FocusFrame` com barra superior precisa, área central enquadrada e barra inferior fixa com acabamento elevado.
   - `FeedbackSheet` mantendo `bg-success/10` e `bg-danger/10` com superfície sólida subjacente, hierarquia clara e botões de ação rápida.
6. **Praticar, Progresso, Landing e Auth (`app/(app)/learn/page.tsx`, `components/mode-card.tsx`, `app/(app)/progress/page.tsx`, `app/page.tsx`, `app/(auth)/*`):**
   - `ModeCard` com estética de cartão técnico interativo.
   - `ProgressPage` com faixa de métricas estilo cockpit analítico.
   - Landing e Auth alinhados ao tema híbrido escuro/claro.

## 4. Invariantes e Testes
- Todos os textos, rótulos acessíveis (`aria-label`, `role`, `aria-current`, `aria-live`) e fluxos testados pela suíte Vitest (396 testes em 51 arquivos) permanecem intactos.
- Zero erros no `npm run typecheck` e `npm run lint` (mantendo no máximo os 5 warnings pré-existentes).
