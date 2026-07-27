# BeFluent — Regras do Projeto

- O projeto se chama **BeFluent** (antes: Fluentia).
- O BeFluent é um webapp para aprendizado de inglês, espanhol da Espanha, francês, japonês e mandarim.
- A interface deve permanecer em português.
- Cadastro público e múltiplos usuários estão autorizados nesta fase.
- O projeto será desenvolvido localmente e depois publicado no Coolify em `befluent.medquesthub.com.br`.
- BeFluent é independente do MedQuestHub AI (auth, banco e sessões próprios).
- Não alterar tecnologias sem autorização.
- Não apagar arquivos existentes sem autorização.
- Não executar comandos destrutivos.
- Sempre trabalhar em pequenas etapas.
- Sempre testar antes de avançar.
- Sempre explicar erros de forma simples.
- Não esconder falhas.
- Não inventar credenciais, chaves ou resultados de testes.

## Fase atual — identidade BeFluent + primeira versão

Autorizado:

- adicionar dependências da stack oficial;
- criar frontend, backend, PostgreSQL, Docker e testes;
- usar integrações modulares de IA, STT e TTS com **modo mock** quando não houver chaves;
- migrar marca Fluentia para BeFluent (cookie `befluent_session`, containers `befluent-*`);
- não fazer deploy no Coolify nesta etapa;
- não publicar na internet;
- não integrar login ao MedQuestHub AI;
- não escolher modelos/provedores definitivos silenciosamente;
- manter FSRS como decisão pendente; usar agendador SRS **simples e substituível**.

Codes de idioma autorizados: `en`, `es-ES`, `fr`, `ja`, `zh-CN`.
