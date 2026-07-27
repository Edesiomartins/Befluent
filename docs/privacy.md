# Privacidade — BeFluent

Relacionados: [security.md](security.md), [database.md](database.md), [speech-architecture.md](speech-architecture.md), [observability.md](observability.md).

## Princípios

- Aplicação privada de uso pessoal.
- Minimização de dados.
- Transparência sobre envio a provedores externos (IA/áudio).
- Não armazenar áudio permanentemente sem necessidade.
- Política final de retenção = **decisão pendente** (registrar quando fechada).

## Tipos de dados coletados

| Categoria | Exemplos | Necessidade |
|---|---|---|
| Conta | email, hash de senha, nome | Autenticação |
| Preferências | idioma padrão, velocidade TTS | UX |
| Estudo | planos, sessões, exercícios | Pedagogia |
| Conversas | mensagens texto | Tutor |
| Textos | redações, respostas | Correção |
| Áudios | clips temporários | STT/pronúncia |
| Métricas | ProgressMetric | Progresso |
| Logs | request_id, erros técnicos | Operação |
| Auditoria | login, ações relevantes | Segurança |

## Dados de estudo

Incluem progresso, erros, vocabulário e avaliações. São sensíveis no sentido pessoal; acesso só do usuário autenticado (e operações de manutenção autorizadas na VPS).

## Conversas e textos

- Persistidos conforme necessidade pedagógica.
- Resumos preferíveis a históricos eternos detalhados.
- Podem ser enviados ao provedor de IA para gerar respostas — isso deve ser claro na documentação do produto.

## Áudios

- Capturados no navegador com permissão.
- Enviados ao backend e, se necessário, ao provedor STT/TTS.
- **Exclusão temporária padrão** após processamento.
- Avaliação de pronúncia não justifica arquivo eterno por padrão.

## Métricas

- Preferir agregados.
- Evitar granularidade que reconstrua conteúdo sensível desnecessariamente.

## Logs

- Sem conteúdo completo de conversa/áudio/senha.
- Retenção limitada (prazo final pendente).

## Retenção

Diretrizes provisórias (não finais):

- Conta e progresso: enquanto o uso continuar.
- Sessões/mensagens detalhadas: janela + resumos.
- Áudio: minutos/horas no máximo, preferência zero permanente.
- AuditLog: prazo curto/médio.
- Backups: prazo definido na operação.

**Decisão pendente:** prazos exatos e processo de purge.

## Exclusão

- Desativação de conta.
- Processo de exclusão/anonimização de dados pessoais sob pedido do proprietário.
- Cascata controlada conforme [database.md](database.md).

## Exportação

- Futuro: exportar progresso/vocabulário em formato legível.
- Não obrigatório na fundação; registrar como melhoria.

## Backups

- Necessários para recuperação.
- Protegidos como dados pessoais.
- Testar restauração periodicamente (procedimento operacional).

## Serviços externos

Podem processar:

- textos enviados à IA (OpenRouter/modelo);
- áudio enviado a STT/TTS (provedores pendentes).

Regras:

- enviar só o mínimo;
- não enviar senhas/chaves;
- preferir regiões/provedores aceitáveis quando a escolha for feita;
- documentar a escolha em [decisions.md](decisions.md).

## Minimização

Antes de persistir ou enviar, perguntar:

1. É necessário para a atividade atual?
2. Pode ser resumido?
3. Pode ser temporário?
4. Pode ficar só no cliente? (geralmente não para pedagogia server-side)

## Transparência

A documentação e, no futuro, uma página/seção de configurações/privacidade devem deixar claro que conteúdo de estudo pode ser processado por provedores externos de IA e áudio para prestar a funcionalidade.
