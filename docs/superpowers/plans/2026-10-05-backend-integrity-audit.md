# Auditoria de integridade do backend

**Objetivo:** corrigir falhas reproduzidas de sessão, evidência e isolamento de retry.
**Escopo:** backend e documentação; sem frontend, migration, commit, merge, push ou deploy.
**Execução:** nesta sessão, em etapas pequenas com teste antes de cada correção.

- [x] Reproduzir e corrigir conclusão de Conversation abandonada ou com StudySession incompatível; testar repetição e rollback.
- [x] Reproduzir e corrigir bypass por `__ack__` e evidência de compreensão em atividades passivas; preservar exposição lexical.
- [x] Reproduzir e corrigir retry de remediação alheia ao fluxo; serializar retry usando o lock existente.
- [x] Reproduzir e corrigir cursor de transferência e fechamento sem domínio; manter mastery baseado na política existente.
- [x] Verificar orçamento 36/12, entitlements e STT/TTS; registrar limitações sem mudar provedores.
- [x] Executar suíte backend, revisar diff e registrar resultado no Segundo Cérebro.

Resultado: 1.454 testes passaram, zero falhas, 34 warnings existentes do Alembic.
Relatório: `docs/backend-audit-2026-10-05.md`. Registro no Segundo Cérebro
atualizado pela ponte protegida e verificado por releitura.

Revisão: reenviar respostas; estado abandonado; retry entre usuários; falha de commit; atividade passiva sem produção.
