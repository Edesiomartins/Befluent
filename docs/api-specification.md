# Especificação da API — BeFluent

Planejamento REST. **Sem implementação nesta etapa.**

Prefixo de negócio: `/api/v1`  
Health: `GET /health`

Autenticação padrão: sessão via cookie HTTP-only, salvo onde indicado.

Relacionados: [architecture.md](architecture.md), [security.md](security.md), [error-handling.md](error-handling.md).

## Convenções

- JSON request/response.
- Erros com código, mensagem amigável e `request_id` quando possível.
- Datas em ISO-8601.
- Idiomas: inglês, espanhol da Espanha, francês, japonês, mandarim.

Exemplo ilustrativo de erro:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Não foi possível validar os dados enviados.",
    "request_id": "exemplo-nao-real"
  }
}
```

---

## health

| Método | Caminho | Objetivo | Auth | Entrada | Resposta | Erros |
|---|---|---|---|---|---|---|
| GET | `/health` | Saúde do serviço | Não | — | status ok/degraded | 503 se crítico |

## auth

| Método | Caminho | Objetivo | Auth | Entrada | Resposta | Erros |
|---|---|---|---|---|---|---|
| POST | `/api/v1/auth/login` | Login | Não | credenciais | sessão (cookie) + perfil mínimo | 401, 429 futuro, 500 |
| POST | `/api/v1/auth/logout` | Logout | Sim | — | ok | 401 |
| GET | `/api/v1/auth/me` | Sessão atual | Sim | — | usuário | 401 |

## Fronteira entre profile e settings

Os módulos **não devem duplicar** as mesmas responsabilidades.

### `/profile` — identidade e visão da conta

Escopo:

- dados do usuário;
- nome;
- imagem (quando existir);
- idioma principal / idioma de estudo em destaque;
- resumo do progresso (visão agregada, sem substituir `/progress`);
- informações de conta;
- preferências pedagógicas de alto nível, quando fizer sentido (ex.: objetivo geral declarado).

Não deve expor nem persistir aqui: velocidade de voz, toggles de áudio, modo fino de correção, notificações ou opções técnicas de interface.

### `/settings` — configurações operacionais

Escopo:

- configurações operacionais;
- idioma da interface (hoje português; campo preparado para evolução);
- preferências de áudio;
- velocidade da voz;
- exibição de tradução;
- modo de correção;
- notificações futuras;
- opções de privacidade;
- configurações técnicas do usuário.

**Entidade principal:** `UserPreference` é a fonte persistente das configurações de `/settings`. Ver [database.md](database.md).

Preferências pedagógicas profundas por idioma (nível, plano, diagnóstico) ficam nos módulos de learning/assessment, não em settings.

## profile

| Método | Caminho | Objetivo | Auth | Entrada | Resposta | Erros |
|---|---|---|---|---|---|---|
| GET | `/api/v1/profile` | Obter dados de conta, nome, imagem, idioma principal e resumo de progresso | Sim | — | perfil | 401 |
| PATCH | `/api/v1/profile` | Atualizar nome, imagem e preferências pedagógicas de alto nível permitidas | Sim | campos de perfil | perfil | 400, 401 |

## languages

| Método | Caminho | Objetivo | Auth | Entrada | Resposta | Erros |
|---|---|---|---|---|---|---|
| GET | `/api/v1/languages` | Listar idiomas | Sim | — | lista | 401 |
| GET | `/api/v1/languages/mine` | Idiomas do usuário | Sim | — | lista com status | 401 |
| POST | `/api/v1/languages/{code}/activate` | Ativar idioma | Sim | — | UserLanguage | 404, 401 |

## onboarding

| Método | Caminho | Objetivo | Auth | Entrada | Resposta | Erros |
|---|---|---|---|---|---|---|
| GET | `/api/v1/onboarding/status` | Status do onboarding | Sim | — | flags | 401 |
| POST | `/api/v1/onboarding/complete` | Concluir onboarding | Sim | preferências iniciais | status | 400, 401 |

## assessments

| Método | Caminho | Objetivo | Auth | Entrada | Resposta | Erros |
|---|---|---|---|---|---|---|
| POST | `/api/v1/assessments/diagnostic` | Iniciar diagnóstico | Sim | language_code | assessment | 400, 401, 503 IA |
| GET | `/api/v1/assessments/{id}` | Obter avaliação | Sim | — | assessment | 404, 401 |
| POST | `/api/v1/assessments/{id}/answers` | Enviar respostas | Sim | answers | progresso | 400, 401 |
| POST | `/api/v1/assessments/{id}/complete` | Finalizar | Sim | — | resultado resumido | 400, 401, 503 |

## learning-plans

| Método | Caminho | Objetivo | Auth | Entrada | Resposta | Erros |
|---|---|---|---|---|---|---|
| GET | `/api/v1/learning-plans/current` | Plano atual | Sim | language_code | plan + items | 404, 401 |
| POST | `/api/v1/learning-plans/generate` | Gerar/atualizar plano | Sim | language_code | plan | 400, 401, 503 |
| POST | `/api/v1/learning-plans/items/{id}/start` | Iniciar item | Sim | — | item + deep link | 404, 401 |

## lessons

| Método | Caminho | Objetivo | Auth | Entrada | Resposta | Erros |
|---|---|---|---|---|---|---|
| POST | `/api/v1/lessons` | Criar/iniciar aula | Sim | language_code, topic? | lesson | 401, 503 |
| GET | `/api/v1/lessons/{id}` | Obter aula | Sim | — | lesson | 404, 401 |
| POST | `/api/v1/lessons/{id}/activities/{aid}/submit` | Enviar atividade | Sim | response | feedback | 400, 401, 503 |
| POST | `/api/v1/lessons/{id}/complete` | Concluir aula | Sim | — | summary | 400, 401 |

## study-sessions

| Método | Caminho | Objetivo | Auth | Entrada | Resposta | Erros |
|---|---|---|---|---|---|---|
| POST | `/api/v1/study-sessions` | Abrir sessão | Sim | language_code | session | 401 |
| GET | `/api/v1/study-sessions/{id}` | Detalhe | Sim | — | session | 404, 401 |
| POST | `/api/v1/study-sessions/{id}/end` | Encerrar | Sim | — | session | 400, 401 |
| GET | `/api/v1/study-sessions/{id}/report` | Relatório | Sim | — | report | 404, 401, 503 |

## conversations

| Método | Caminho | Objetivo | Auth | Entrada | Resposta | Erros |
|---|---|---|---|---|---|---|
| POST | `/api/v1/conversations` | Iniciar conversa | Sim | language_code, mode, topic? | conversation | 401, 503 |
| GET | `/api/v1/conversations/{id}` | Histórico | Sim | — | messages | 404, 401 |
| POST | `/api/v1/conversations/{id}/messages` | Enviar texto | Sim | content | assistant + corrections | 400, 401, 503 |
| POST | `/api/v1/conversations/{id}/end` | Encerrar | Sim | — | summary curto | 401 |

## speech

| Método | Caminho | Objetivo | Auth | Entrada | Resposta | Erros |
|---|---|---|---|---|---|---|
| POST | `/api/v1/speech/transcribe` | STT | Sim | áudio multipart | text | 400, 401, 413, 503 |
| POST | `/api/v1/speech/synthesize` | TTS | Sim | text, language, speed? | áudio/stream | 400, 401, 503 |
| POST | `/api/v1/speech/pronunciation` | Avaliar pronúncia | Sim | áudio + target | feedback | 400, 401, 503; provedor pendente |

## vocabulary

| Método | Caminho | Objetivo | Auth | Entrada | Resposta | Erros |
|---|---|---|---|---|---|---|
| GET | `/api/v1/vocabulary` | Listar | Sim | language_code, filtros | items | 401 |
| POST | `/api/v1/vocabulary` | Criar item | Sim | term payload | item | 400, 401 |
| PATCH | `/api/v1/vocabulary/{id}` | Atualizar | Sim | campos | item | 404, 401 |

## reviews

| Método | Caminho | Objetivo | Auth | Entrada | Resposta | Erros |
|---|---|---|---|---|---|---|
| GET | `/api/v1/reviews/due` | Itens devidos | Sim | language_code | queue | 401 |
| POST | `/api/v1/reviews/{id}/answer` | Registrar revisão | Sim | grade/result | next schedule | 400, 401 |

## grammar

| Método | Caminho | Objetivo | Auth | Entrada | Resposta | Erros |
|---|---|---|---|---|---|---|
| GET | `/api/v1/grammar/topics` | Tópicos | Sim | language_code | topics + progress | 401 |
| POST | `/api/v1/grammar/practice` | Prática | Sim | topic_id | exercise | 401, 503 |
| POST | `/api/v1/grammar/practice/{id}/submit` | Enviar | Sim | response | feedback | 400, 401 |

## listening

| Método | Caminho | Objetivo | Auth | Entrada | Resposta | Erros |
|---|---|---|---|---|---|---|
| POST | `/api/v1/listening/activities` | Gerar/iniciar | Sim | language_code | activity | 401, 503 |
| POST | `/api/v1/listening/activities/{id}/submit` | Responder | Sim | answers | result | 400, 401 |

## pronunciation

| Método | Caminho | Objetivo | Auth | Entrada | Resposta | Erros |
|---|---|---|---|---|---|---|
| POST | `/api/v1/pronunciation/attempts` | Nova tentativa | Sim | target + áudio | feedback | 400, 401, 503 |
| GET | `/api/v1/pronunciation/attempts` | Histórico resumido | Sim | language_code | list | 401 |

## writing

| Método | Caminho | Objetivo | Auth | Entrada | Resposta | Erros |
|---|---|---|---|---|---|---|
| POST | `/api/v1/writing/submissions` | Enviar texto | Sim | prompt/content | feedback | 400, 401, 503 |
| GET | `/api/v1/writing/submissions/{id}` | Detalhe | Sim | — | submission | 404, 401 |

## progress

| Método | Caminho | Objetivo | Auth | Entrada | Resposta | Erros |
|---|---|---|---|---|---|---|
| GET | `/api/v1/progress/summary` | Resumo | Sim | language_code | metrics | 401 |
| GET | `/api/v1/progress/sessions` | Histórico de sessões | Sim | language_code, page | list | 401 |

## settings

Persistência via `UserPreference`. Não repetir campos de `/profile` (nome, imagem, resumo de progresso).

| Método | Caminho | Objetivo | Auth | Entrada | Resposta | Erros |
|---|---|---|---|---|---|---|
| GET | `/api/v1/settings` | Obter configurações operacionais (áudio, voz, tradução, correção, privacidade, UI) | Sim | — | settings | 401 |
| PUT | `/api/v1/settings` | Atualizar configurações operacionais em `UserPreference` | Sim | settings | settings | 400, 401 |

## Observações

- Endpoints de IA/áudio podem retornar 503 com mensagem amigável e possibilidade de retry.
- Avaliação de pronúncia precisa depende de provedor (decisão pendente).
- Rate limiting detalhado é futuro, mas a API deve estar preparada para limites.
- Não há endpoints de cadastro público, pagamento ou multi-usuário aberto.
- `/profile` e `/settings` têm fronteiras distintas; conflitos de campo devem ser resolvidos em favor dessa separação.
