# Segurança — Fluentia

Relacionados: [privacy.md](privacy.md), [architecture.md](architecture.md), [api-specification.md](api-specification.md), [stack.md](stack.md).

## Postura geral

- Aplicação **privada**.
- **Apenas um usuário** autorizado inicialmente.
- **Sem cadastro público**.
- Segredos e credenciais ficam **apenas no backend** (variáveis de ambiente / secrets).
- Autenticação com **cookie HTTP-only**.
- O navegador **não deve armazenar JWT em `localStorage`** (nem em `sessionStorage`).

## Autenticação e sessão

- Login com credenciais verificadas no backend.
- Após login, a sessão é estabelecida por **cookie HTTP-only**.
- Em produção, o cookie deve ser **`Secure`**.
- O cookie deve usar **`SameSite` adequado** ao desenho anti-CSRF.
- Logout invalida a sessão no servidor e remove/expira o cookie.
- Credenciais e segredos nunca são enviados ao frontend além do necessário para a UX de login.

## Esclarecimento sobre tokens

| Conceito | O que é | Uso no Fluentia |
|---|---|---|
| Token de sessão **opaco** | Identificador aleatório sem significado para o cliente; o servidor resolve a sessão | Permitido **somente** dentro de cookie HTTP-only |
| **JWT** | Token assinado que pode carregar claims e ser decodificado no cliente | **Não** deve ser armazenado em `localStorage`/`sessionStorage`. Se algum dia for considerado, exige decisão explícita em [decisions.md](decisions.md) — **não é a estratégia atual** |
| Cookie **HTTP-only** | Cookie inacessível a JavaScript | Estratégia confirmada de sessão |
| `localStorage` | Armazenamento acessível a JS no navegador | **Proibido** para JWT e para token de sessão |

“Token opaco” **não** significa JWT exposto ao cliente. Significa um identificador de sessão que o JavaScript da página **não lê**.

## Cookie HTTP-only

- Inacessível a JavaScript.
- Reduz risco de roubo via XSS.
- Ainda exige prevenção de XSS e CSRF.

## Proteção CSRF

- CSRF **deve ser considerado** porque a autenticação usa cookie.
- Estratégia alinhada ao uso de cookies (ex.: `SameSite` + token CSRF em mutações, se necessário).
- Mecanismo detalhado = decisão pendente P-013 em [decisions.md](decisions.md), a fechar na Fase 1.

## Hash de senha

- Algoritmo moderno de hash (ex.: Argon2/bcrypt — escolha na implementação).
- Nunca armazenar senha em texto puro.
- Nunca logar senha.

## Rate limiting futuro

- Planejado para login e endpoints caros (IA/áudio).
- Não bloqueia a fundação; deve ser adicionado antes/durante endurecimento de segurança (Fase 7).

## Validação de entrada

- Pydantic no backend.
- Limites de tamanho de texto e upload.
- Sanitização/escape no frontend contra XSS.

## CORS

- Origens explicitamente permitidas (frontend).
- Sem `*` em produção com credenciais.

## Headers de segurança

Planejar (produção):

- HTTPS enforced;
- `Content-Security-Policy` adequada (ajuste fino pendente);
- `X-Content-Type-Options`, `Referrer-Policy`, `Frame-Options`/`CSP frame-ancestors`.

## Armazenamento de segredos

- Variáveis de ambiente / secrets do Coolify.
- Não commitar `.env`.
- Rotação possível sem rebuild de lógica.
- OpenRouter/STT/TTS e demais chaves apenas no backend.

## Proteção de endpoints

- Default: autenticado.
- Exceções: `GET /health`, login.
- Autorização: recurso pertence ao usuário da sessão.

## Upload de áudio

- Autenticado.
- Validar tipo e tamanho.
- Armazenamento temporário.
- Exclusão após uso.
- Sem execução de conteúdo enviado.

## Tamanho de arquivos

- Limite máximo no proxy e na aplicação.
- Erro 413 com mensagem clara.

## Logs

- Não armazenar senha, token de sessão, JWT, cookies, chaves de API, áudio ou prompts completos sensíveis.
- Ver [observability.md](observability.md).

## Backups

- PostgreSQL com backup periódico no ambiente de deploy.
- Backups protegidos e com retenção definida ([privacy.md](privacy.md) — política final pendente).

## Dependências

- Fixar versões.
- Atualizar patches de segurança.
- Evitar pacotes desnecessários (nesta etapa: nenhuma instalação).

## Atualização de segurança

- Processo: testar local → deploy Coolify → smoke test.
- Rollback preparado ([deployment-coolify.md](deployment-coolify.md)).

## Prompt injection

- Separar system prompt de dados do usuário.
- Validar saídas estruturadas.
- Não permitir que o modelo altere regras de auth ou exponha secrets.
- Detalhes em [ai-architecture.md](ai-architecture.md).

## Exposição de chaves

Checklist:

- [ ] Nenhuma `NEXT_PUBLIC_` com chave secreta.
- [ ] OpenRouter/STT/TTS só no backend.
- [ ] Nenhum JWT ou token de sessão em `localStorage`/`sessionStorage`.
- [ ] Respostas de erro sem vazar stack interna em produção.
- [ ] Repositório sem secrets commitados.
- [ ] Logs sem senha, token ou conteúdo sensível.

## Redis

- Não introduzir por “padrão de mercado”.
- Não é obrigatório.
- Se no futuro houver rate limit/fila distribuída, avaliar com necessidade real.
