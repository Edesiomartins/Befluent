# Estratégia de Testes — Fluentia

Relacionados: [roadmap.md](roadmap.md), [acceptance-criteria.md](acceptance-criteria.md), [deployment-coolify.md](deployment-coolify.md), [error-handling.md](error-handling.md).

## Princípio

Nenhuma fase avança sem testes locais da entrega da fase. Deploy só após critérios mínimos.

## Camadas

### Testes unitários

- Regras do domínio (nível, SRS helpers, validação de schema de IA).
- Funções puras de formatação e parsing.
- **Mínimo:** cobrir regras críticas de auth hash, validação Pydantic e parsers de saída de IA.

### Testes de integração

- Backend + PostgreSQL de teste.
- Fluxos: login, criar sessão, salvar tentativa.
- **Mínimo:** 1 fluxo feliz + 1 falha de validação por módulo entregue.

### Testes de API

- Contratos de [api-specification.md](api-specification.md).
- Status codes e formato de erro.
- **Mínimo:** health, auth, endpoint principal da fase.

### Testes de componentes

- Componentes React de UI crítica (login, player de áudio, correção).
- Estados loading/empty/error.
- **Mínimo:** componentes das telas entregues na fase.

### Testes end-to-end

- Fluxos: login → dashboard → iniciar atividade.
- **Mínimo:** 1 E2E feliz por fase a partir da Fase 1.

### Responsividade

- Verificar layouts principais em larguras de celular, tablet e desktop.
- **Mínimo:** checklist manual ou snapshot em breakpoints definidos.

### Acessibilidade

- Teclado, foco, labels, contraste básico.
- **Mínimo:** login e navegação principal sem armadilha de foco.

### Áudio

- Permissão negada → fallback.
- Upload inválido → 400/413.
- STT/TTS mockados em teste.
- **Mínimo:** não quebrar fluxo textual se áudio falhar.

### Falha de serviços externos

- OpenRouter timeout / 5xx / JSON inválido.
- STT/TTS down.
- **Mínimo:** mensagem amigável + retry onde previsto.

### Autenticação

- Cookie setado; rota protegida bloqueia anônimo; logout.
- **Mínimo:** suite auth verde antes de qualquer feature autenticada.

### Migração

- Alembic upgrade/downgrade em banco limpo.
- **Mínimo:** upgrade from zero passa.

### Ambiente local

- Compose sobe DB; app inicia; `/health` ok.
- **Mínimo:** README/runbook local executável (quando existir código).

### Antes do deploy

Checklist:

1. Testes da fase passando.
2. Variáveis de ambiente revisadas (sem secrets no git).
3. Migrações revisadas.
4. Smoke script local.

### Smoke tests após deploy

- `/health`
- Login
- Carregar dashboard
- Uma ação de escrita simples (quando existir)

## Critérios mínimos por etapa do roadmap

| Fase | Mínimo de teste |
|---|---|
| 0 | Revisão documental / consistência |
| 1 | unit+API auth/health + migração |
| 2 | integração onboarding/diagnóstico |
| 3 | API conversa/aula + mock IA |
| 4 | áudio com mocks + fallback |
| 5 | SRS/vocab/grammar integração |
| 6 | relatórios/leitura/escrita |
| 7 | E2E amplo + segurança + a11y + smoke prod |

## O que não fazer

- Inventar resultados de testes.
- Deploy sem falhas conhecidas críticas abertas.
- Testar só o caminho feliz.
