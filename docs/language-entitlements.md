# Entitlements por idioma

Relacionados: [architecture.md](architecture.md), [vocabulary-learning-cycle.md](vocabulary-learning-cycle.md).

## Objetivo

Preparar a regra futura **uma assinatura = um idioma** sem cobrança, checkout
ou bloqueio dos usuários atuais.

`UserLanguage` continua sendo perfil pedagógico (nível, onboarding, idioma
ativo). Direito de acesso mora em `LanguageEntitlement`.

```
User → LanguageEntitlement → Language
```

O mesmo usuário pode ter várias concessões e, no futuro, várias assinaturas.

## Contrato central

A única decisão de autorização é:

```
user_can_access_language(db, user_id, language_code)
```

Helpers, ativação (`/languages/activate`) e onboarding consultam esse
serviço. O frontend só apresenta estado (`available`, `entitled`, `locked`)
e nunca autoriza sozinho.

## Fontes

| `source` | Significado |
|---|---|
| `legacy` | acesso atual, criado no backfill e em novas ativações com a flag desligada |
| `admin` | concessão explícita da equipe, sem pagamento |
| `trial` | acesso de teste |
| `promotion` | acesso promocional |
| `subscription` | reservado; uma assinatura futura cria/revoga exatamente um grant |

Vigência: `status=active`, sem `cancelled_at`, `starts_at <= agora` e
`expires_at` nulo ou futuro.

## Transição segura

`LANGUAGE_ENTITLEMENTS_ENABLED` tem default `false`.

1. Flag desligada: todo idioma do catálogo ativo permanece acessível.
   Novas ativações criam grant `legacy` de forma idempotente.
2. Migration `0012` fez backfill `legacy` para todos os `UserLanguage`
   existentes.
3. Flag ligada no futuro: só grant vigente permite ativar/estudar o idioma.
   Usuários atuais não perdem acesso, porque já têm `legacy`.

Não ligar a flag em produção nesta entrega. Não criar `users.language_id`,
role improvisada, preço, Asaas, Stripe, webhook ou tela de compra.

## Como ligar a flag no futuro

1. Confirmar que a migration `0012` rodou e o backfill existe.
2. Conferir grants `legacy` dos usuários atuais.
3. Definir grants `admin`/`trial` explícitos quando necessário.
4. Só então setar `LANGUAGE_ENTITLEMENTS_ENABLED=true` no backend.
5. O frontend passará a receber `locked` para idiomas sem grant; a UI de
   compra ainda não existe e não deve ser improvisada neste passo.

## Risco do backfill legacy

`UserLanguage` não tem estado `deleted`, `disabled` ou `archived`.
`is_active` significa “idioma selecionado agora”, não “acesso válido”.
`onboarding_completed` pode ser falso.

A migration `0012` concedeu grant `legacy` ativo e sem expiração para **toda**
linha de `user_languages`, inclusive perfil incompleto. A migration histórica
não foi alterada. Com `LANGUAGE_ENTITLEMENTS_ENABLED=false` isso não bloqueia
nem libera ninguém além do comportamento atual. Antes de ligar a flag, revisar
se algum par usuário↔idioma foi criado sem intenção de acesso.
