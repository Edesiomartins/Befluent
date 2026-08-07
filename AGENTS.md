# BeFluent — Regras do Projeto

- O projeto se chama **BeFluent** (antes: Fluentia).
- O BeFluent é um webapp para aprendizado de inglês, espanhol da Espanha, francês, japonês e mandarim.
- A interface deve permanecer em português.
- Cadastro público e múltiplos usuários estão autorizados.
- O projeto está **publicado em produção no Coolify**: `befluent.medquesthub.com.br` (frontend) e `api-befluent.medquesthub.com.br` (backend).
- BeFluent é independente do MedQuestHub AI (auth, banco e sessões próprios).
- Não alterar tecnologias sem autorização.
- Não apagar arquivos existentes sem autorização.
- Não executar comandos destrutivos.
- Sempre trabalhar em pequenas etapas.
- Sempre testar antes de avançar.
- Sempre explicar erros de forma simples.
- Não esconder falhas.
- Não inventar credenciais, chaves ou resultados de testes.

## Fase atual — pós-deploy, evolução de funcionalidades

Já implementado (referência, não precisa reautorizar):

- Frontend (Next.js/React), backend (FastAPI), PostgreSQL, Docker, testes automatizados (pytest/vitest).
- Fluxos de currículo/cronograma, placement tests, dashboard, progresso, SRS simples, banco de lições, avaliação de escrita heurística.
- Deploy em produção no Coolify (ordem obrigatória: backend antes do frontend — `NEXT_PUBLIC_API_URL` é lida em build time; ver `backend/README.md`).
- Integrações modulares de IA/STT/TTS, hoje rodando em **modo mock** (a chave OpenRouter configurada não está ativa/compatível — não é decisão de produto, é pendência técnica).

Continua autorizado:

- Adicionar dependências da stack oficial.
- Evoluir frontend/backend/testes e fazer deploys de atualização no Coolify (seguindo a ordem backend → frontend e confirmando com o usuário antes de cada deploy, como qualquer ação que afeta produção).
- Manter FSRS como decisão pendente; usar agendador SRS **simples e substituível**.

Continua **não autorizado** sem confirmação explícita:

- Trocar o modo mock de IA por um provedor/modelo definitivo, ou escolher modelo/provedor silenciosamente.
- Integrar login ao MedQuestHub AI.
- Renomear infraestrutura legada `fluentia-*` (serviços, volume `fluentia_pg_data`) por causa da marca — quebraria volumes existentes em produção.

Codes de idioma autorizados: `en`, `es-ES`, `fr`, `ja`, `zh-CN`.
