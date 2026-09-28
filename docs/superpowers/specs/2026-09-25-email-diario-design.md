# Design — E-mail diário da missão do dia

Data: 2026-09-25 · Item 2 do programa de adesão (ver `docs/decisions.md`, D-022 e vizinhança).

## Problema

Nada traz o aluno de volta ao BeFluent. O app espera que a pessoa lembre. O
produto de referência (Le Monde Langues / Gymglish) empurra a lição por e-mail
todo dia, e é isso que sustenta o hábito.

O serviço de e-mail já existe (`app/services/email.py`, Resend) e só é usado
para recuperação de senha. Não há agendador no backend.

## Decisões de escopo (confirmadas pelo proprietário)

1. **Disparo:** tarefa agendada no Coolify chamando um endpoint autenticado por
   chave. Sem APScheduler, sem dependência nova, sem risco de envio duplicado
   por múltiplos workers.
2. **Conteúdo:** só a missão do dia e o link. **Sem** contagem de revisão
   vencida, **sem** segundo e-mail de correção (depende do item 3), **sem**
   percentual, nível ou sequência de dias.

## Contrato

```
POST /api/v1/daily-email/dispatch
Header: X-Dispatch-Key: <DAILY_EMAIL_KEY>
→ 200 {"sent": n, "skipped": n, "failed": n, "date": "2026-09-25"}
→ 401 dispatch_key_invalid   (chave ausente ou errada)
→ 503 dispatch_not_configured (DAILY_EMAIL_KEY vazio no ambiente)
```

A rota **não** usa cookie de sessão: o cron não tem sessão. Ela também não
aceita `?key=` na URL — chave em query string vaza em log de acesso.

Sem `DAILY_EMAIL_KEY` configurado a rota responde 503 e não envia nada. Nunca
existe disparo aberto: a falta de configuração fecha a porta, não a abre.

## Fluxo

Para cada `UserLanguage` ativo com onboarding concluído, do usuário dono:

1. Achar o currículo ativo e o **primeiro dia ainda aberto** (mesma definição
   de `/curriculum/day/today`: progressão, não data civil).
2. Sem currículo ativo ou sem dia aberto → `skipped`. Nada de e-mail dizendo
   "você não tem nada" — isso é ruído, não gatilho.
3. **Reivindicar o envio do dia** com `record_product_event`
   (`event_type="daily_email_sent"`, `dedupe_key="daily-email:<AAAA-MM-DD>"`).
   Se já existe, `skipped` — rodar o cron duas vezes não manda dois e-mails.
4. Enviar. Assunto: `Dia <n> — <tema> | BeFluent`. Corpo: tema do dia, os
   rótulos dos blocos na ordem, e um botão para `/cronograma/dia/<id>`.
5. Falha de envio (`EmailSendError`) → **desfaz a reivindicação** (rollback do
   savepoint) e conta em `failed`, para a próxima execução tentar de novo.
   Um erro de e-mail nunca consome o envio do dia.

## Por que a reivindicação vem antes do envio

Reivindicar depois abriria janela para dois e-mails iguais se o disparo rodasse
duas vezes próximo. Reivindicar antes, com desfazimento em falha, erra para o
lado de "manda uma vez ou nenhuma", nunca "manda duas".

## Arquivos

- `app/core/config.py` — `daily_email_key` (env `DAILY_EMAIL_KEY`).
- `app/services/daily_email.py` — `build_daily_mission`, `daily_email_html`,
  `dispatch_daily_emails`. Sem FastAPI aqui: função pura de DB, testável.
- `app/api/daily_email.py` — a rota e a checagem de chave.
- `app/main.py` — registro do router.
- `app/services/language_progress.py` — constante `DAILY_EMAIL_SENT`.
- `docs/deployment-coolify.md` — como criar a tarefa agendada.

## Testes

- Monta a missão do dia aberto, não o da data civil.
- Segundo disparo no mesmo dia não reenvia.
- Falha de envio libera o dia para nova tentativa.
- Perfil sem currículo ativo é pulado sem erro.
- Chave errada → 401; chave ausente no ambiente → 503; chave certa → 200.
- O HTML escapa o tema (conteúdo vindo do banco não entra cru no corpo).

## Limites declarados

- Fuso: o dia usado é a data do servidor (UTC), igual ao resto do currículo.
  Horário do e-mail é o horário do cron no Coolify — não há preferência de
  horário por usuário nesta etapa.
- Sem descadastro por link. O app é privado, de um dono; desligar = remover a
  tarefa no Coolify ou limpar `DAILY_EMAIL_KEY`. Isso está declarado aqui
  porque é uma limitação real, não um esquecimento.
