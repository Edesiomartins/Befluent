# Vocabulary Learning Cycle V2 e entitlements por idioma

Data: 2026-09-23  
Status: aprovado

## Objetivo

Evoluir o módulo de vocabulário para um ciclo pedagógico com apresentação,
reconhecimento, reconhecimento reverso, escuta, produção e revisão, reutilizando
o Teaching Engine V2 e a memória existentes. Em paralelo, criar a fundação de
autorização por idioma para a futura regra “uma assinatura = um idioma”, sem
implementar cobrança nem bloquear usuários atuais.

## Diagnóstico

- O componente `Vocabulary` atual é um deck de apresentação. Ao avançar, salva
  um `VocabularyItem` e um `ReviewItem`, mas não registra evidências variadas.
- O áudio do termo e o áudio da frase já estão separados no frontend.
- `VocabularyExample` existe, mas não participa de forma consistente do fluxo.
- `LearningAttempt` e `LearningEvidence` pertencem somente a objetivos; não
  identificam o item lexical praticado.
- O Teaching Engine já contém as fases e os mecanismos de tentativa, evidência,
  erro, remediação e retry necessários.
- `MemorySchedule` já é a fonte de verdade V2 para repetição espaçada;
  `ReviewItem` é a projeção compatível com a fila legada.
- `UserLanguage` representa perfil pedagógico e idioma ativo, não direito de
  acesso.
- Não existem modelos de assinatura, entitlement, pagamento ou role
  administrativa.

## Decisões

### 1. Um único Teaching Engine

Não será criado um motor paralelo de vocabulário. O fluxo lexical será uma
especialização do Teaching Engine:

- `TeachingFlowSession` poderá referenciar uma `Lesson`;
- tentativas e evidências poderão referenciar opcionalmente um
  `VocabularyItem`;
- progresso de objetivo continuará em `UserObjectiveProgress`;
- progresso lexical será materializado no `MemorySchedule` do item;
- o clique em concluir continuará sem significar domínio.

Objetivos existentes e seus históricos permanecerão inalterados. Os vínculos
novos serão opcionais e retrocompatíveis.

### 2. Identidade e conteúdo lexical

`VocabularyItem` é a identidade persistente do termo por usuário/idioma.
`VocabularyExample` guarda frase, tradução e referência de áudio quando houver.
Ao iniciar um ciclo persistido, os itens da lição são matriculados de forma
idempotente e recebem identificadores usados pelas atividades.

Conteúdo antigo sem frase, metadados ou campos do ciclo continua renderizando.
Nenhuma explicação gramatical será inferida por comparação de strings.

### 3. Sequência pedagógica

O conjunto progride pelas fases:

- `ACTIVATING`/`INPUT`: apresentação do termo, tradução, áudio do termo, frase,
  tradução da frase e áudio da frase;
- `NOTICING`/`PRACTICING`: recognition e reverse recognition;
- `PRACTICING`: listening recognition;
- `PRODUCING`: recuperação por digitação ou fala;
- `NEEDS_REVIEW`: itens fracos retornam pelo agendamento da memória.

O gerador lexical é determinístico. Distratores vêm do próprio conjunto e
nunca são inventados pelo frontend.

### 4. Contrato de áudio

Toda atividade auditiva declara o alvo:

- `vocabulary_item`: o texto sintetizado é o termo/expressão;
- `example_sentence`: o texto sintetizado é a frase.

A apresentação expõe controles separados. Listening recognition usa
`vocabulary_item` por padrão e não revela a resposta antes da tentativa. O
frontend apenas reproduz o `audio_text` associado ao alvo declarado.

Piper, fallback do navegador, preparação de latim, cache e seleção de idioma
não serão alterados.

### 5. Evidência e domínio lexical

Serão suportadas evidências de:

- exposição;
- reconhecimento;
- reconhecimento reverso;
- escuta;
- produção lexical.

Uma exposição ou um único acerto não marca domínio. O estado lexical considera
variedade de evidências corretas, produção e histórico da memória. Evidência de
retry após revelação tem peso corretivo, não equivale a recuperação independente.

Tentativas erradas registram o erro e reduzem/agendam a memória. O mesmo
exercício não é repetido imediatamente; o item volta depois, por vencimento ou
em outro contexto/modalidade.

### 6. Produção oral

Atividades que permitem fala reutilizam `Recorder` e o endpoint STT existentes.
Somente a transcrição é enviada ao Teaching Engine. Não haverá armazenamento de
áudio bruto nem segundo pipeline de reconhecimento.

### 7. Entitlement por idioma

Será criada a entidade `LanguageEntitlement`, independente de billing:

- `user_id`;
- `language_id`;
- `source`: `legacy`, `admin`, `trial`, `promotion` ou, futuramente,
  `subscription`;
- `status`;
- `starts_at`;
- `expires_at`;
- `cancelled_at`;
- `metadata_json`;
- timestamps.

Múltiplas concessões e múltiplos idiomas por usuário são permitidos. Uma
assinatura financeira futura ficará associada a exatamente um idioma e
criará/revogará uma concessão `source=subscription`.

Não será criado `users.language_id`, gateway financeiro, preço, checkout,
webhook ou tela de compra.

### 8. Autorização central

O serviço `user_can_access_language(db, user_id, language_code)` será a única
regra de decisão. Helpers/dependencies do backend e a ativação de idioma o
utilizarão. O frontend nunca será a autoridade.

Concessões `admin`, `trial` e `promotion` são acessos explícitos sem pagamento;
não dependem de allow-list de e-mail nem exigem criar uma role artificial.

### 9. Transição segura

A configuração `LANGUAGE_ENTITLEMENTS_ENABLED` terá default `false`.

- flag desligada: comportamento atual permanece aberto;
- migration: todos os `UserLanguage` existentes recebem entitlement `legacy`;
- novas ativações com a flag desligada criam entitlement `legacy`
  idempotentemente;
- flag ligada futuramente: somente concessão vigente permite ativar/estudar o
  idioma.

Assim, a criação da fundação não bloqueia ninguém e a ativação futura da regra
não remove silenciosamente o acesso já existente.

### 10. Frontend

Os payloads do catálogo/perfil de idiomas expõem um estado de acesso reutilizável:

- `available`;
- `entitled`;
- `locked`.

Com a flag desligada, todos os idiomas ativos no catálogo são `available`.
Componentes compartilhados poderão exibir ou bloquear ações futuramente, mas
esta entrega não mostrará preço nem converterá idiomas atuais em pagos.

## Migrations

A alteração é exclusivamente aditiva:

- tabela e índices de `language_entitlements`;
- vínculos opcionais de lição/item lexical no Teaching Engine;
- metadado opcional necessário em exemplos, se o contrato persistido exigir;
- backfill de entitlements `legacy`.

Nenhuma tabela ou histórico existente será removido.

## Testes de aceitação

1. Termo e frase mantêm textos e alvos de áudio distintos.
2. Recognition correto cria evidência lexical.
3. Reverse recognition é avaliado e cria evidência própria.
4. Listening não revela a resposta e usa o áudio do item lexical.
5. Produção digitada ou transcrita cria evidência de produção.
6. Erro agenda retorno posterior, sem retry idêntico imediato.
7. Item dominado não é selecionado excessivamente.
8. Conteúdo antigo sem campos novos continua utilizável.
9. Flag de entitlement desligada preserva todo o acesso atual.
10. Serviço central permite concessão vigente e nega ausência/expiração quando
    a flag está ligada.
11. Concessões administrativas/de teste não dependem de pagamento.
12. Ativação e endpoints protegidos consultam a autorização do backend.

## Fora de escopo

- cobrança, checkout, preços, Asaas, Stripe e webhooks;
- deploy, push ou alteração de secrets/variáveis de produção;
- mudanças em Piper, TTS, STT ou Speech Coach;
- reescrita do Teaching Engine;
- troca do algoritmo SRS simples;
- inferência morfológica no frontend.
