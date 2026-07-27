# Registro de Decisões — Fluentia

Formato: ID | decisão | status | motivo | data | impacto.

Datas no registro inicial: **2026-07-27**.

Relacionados: [stack.md](stack.md), [architecture.md](architecture.md), [roadmap.md](roadmap.md).

## Decisões confirmadas

| ID | Decisão | Status | Motivo | Data | Impacto |
|---|---|---|---|---|---|
| D-001 | Nome do produto: Fluentia | Confirmada | Identidade do projeto | 2026-07-27 | Branding e docs |
| D-002 | Webapp pessoal | Confirmada | Uso do proprietário | 2026-07-27 | Escopo e UX |
| D-003 | Cinco idiomas iniciais: inglês, espanhol da Espanha, francês, japonês, mandarim | Confirmada | Objetivos de aprendizado | 2026-07-27 | Conteúdo e dados |
| D-004 | Interface em português | Confirmada | Usabilidade do dono | 2026-07-27 | UI/copy |
| D-005 | Frontend Next.js + TypeScript + App Router + Tailwind | Confirmada | Stack oficial | 2026-07-27 | Arquitetura FE |
| D-006 | Backend Python + FastAPI + SQLAlchemy + Alembic + Pydantic | Confirmada | Stack oficial | 2026-07-27 | Arquitetura BE |
| D-007 | PostgreSQL | Confirmada | Fonte da verdade | 2026-07-27 | Persistência |
| D-008 | OpenRouter para LLM (principal + fallback) | Confirmada | Abstração de modelos | 2026-07-27 | IA |
| D-009 | Docker + Docker Compose | Confirmada | Reprodutibilidade | 2026-07-27 | Dev/Deploy |
| D-010 | Publicação via Coolify em VPS própria | Confirmada | Hospedagem escolhida | 2026-07-27 | Ops |
| D-011 | Cadastro público e múltiplos usuários autorizados | Confirmada | Autorização do proprietário em 2026-07-27 (substitui restrição de usuário único) | 2026-07-27 | Auth |
| D-012 | Endpoint POST /api/v1/auth/register + tela de cadastro | Confirmada | Permitir que outras pessoas usem o Fluentia | 2026-07-27 | Auth |
| D-013 | Sessão com cookie HTTP-only | Confirmada | Segurança de sessão | 2026-07-27 | Auth FE/BE |
| D-014 | Desenvolvimento e testes locais antes do deploy | Confirmada | Qualidade | 2026-07-27 | Processo |
| D-015 | Redis não obrigatório inicialmente | Confirmada | Evitar complexidade precoce | 2026-07-27 | Infra |
| D-016 | STT/TTS com arquitetura modular; provedor após testes | Confirmada | Flexibilidade | 2026-07-27 | Áudio |
| D-017 | Estratégias pedagógicas distintas por idioma | Confirmada | Qualidade de ensino | 2026-07-27 | Motor/prompts |
| D-018 | Codes de idioma: en, es-ES, fr, ja, zh-CN | Confirmada | Autorização explícita do proprietário | 2026-07-27 | API/DB |
| D-019 | SRS da 1ª versão: agendador simples substituível (não FSRS) | Confirmada | P-010 permanece pendente para algoritmo final | 2026-07-27 | Reviews |

## Decisões pendentes

| ID | Decisão | Status | Motivo de estar pendente | Data | Impacto |
|---|---|---|---|---|---|
| P-001 | Modelo principal no OpenRouter | Pendente | Requer testes de qualidade/custo | 2026-07-27 | IA |
| P-002 | Modelo de fallback | Pendente | Depende do principal | 2026-07-27 | Resiliência |
| P-003 | Limites de tokens por tarefa | Pendente | Medir uso real | 2026-07-27 | Custo/UX |
| P-004 | Temperatura por tarefa | Pendente | Calibrar criatividade vs precisão | 2026-07-27 | Qualidade |
| P-005 | Provedor STT | Pendente | Testes de acurácia/idioma | 2026-07-27 | Voz |
| P-006 | Provedor TTS | Pendente | Qualidade e variantes (ex.: es-ES) | 2026-07-27 | Voz |
| P-007 | Serviço de avaliação de pronúncia | Pendente | STT ≠ fonética precisa | 2026-07-27 | Pronúncia |
| P-008 | Paleta definitiva / tokens de cor | Pendente | Validação visual | 2026-07-27 | Design |
| P-009 | Biblioteca de componentes UI | Pendente | Alinhar a design system | 2026-07-27 | FE |
| P-010 | Estratégia final de repetição espaçada (FSRS = recomendação técnica provisória; SM-2 = alternativa válida) | Pendente | Algoritmo final ainda não confirmado; 1ª versão usa scheduler simples (D-019) | 2026-07-27 | Reviews |
| P-011 | Armazenamento externo de arquivos | Pendente | Preferência por minimizar | 2026-07-27 | Infra/privacidade |
| P-012 | Política final de retenção de dados/logs/áudio | Pendente | Fechar prazos operacionais | 2026-07-27 | Privacidade |
| P-013 | Mecanismo CSRF detalhado | Pendente | Fechar com desenho de sessão | 2026-07-27 | Segurança |
| P-014 | Timeouts/limiares de alerta | Pendente | Dados de operação | 2026-07-27 | Observabilidade |

## Notas de alinhamento

- **P-010 / D-019:** FSRS não está confirmado. A primeira versão usa agendador simples isolado e substituível.
- **D-018 (ex-P-015):** codes confirmados: `en`, `es-ES`, `fr`, `ja`, `zh-CN`.

## Como atualizar este registro

1. Não sobrescrever histórico: altere status e acrescente nota/data.
2. Toda mudança estrutural de stack exige autorização e nova linha.
3. Introduzir Redis só com necessidade real e novo ID confirmado.
