# Língua nativa e política pedagógica

Pedido de implementação: anexo do usuário a29c78bf, 2026-10-05. Escopo autorizado: backend, migration local, contratos/testes/documentação; sem frontend/commit/push/deploy. Preservar alterações editoriais pré-existentes.

## Decisão

`User.native_language: str | None`, VARCHAR(32), nullable, sem default/backfill. É propriedade da pessoa; UserLanguage continua definindo alvo/CEFR e UserPreference configura interface/tempo. Não criar interface_language persistente. Interface permanece portuguesa; não confundir seus rótulos com explicações pedagógicas.

Códigos nativos reutilizam o mapa BCP47 existente + pt-BR como idioma de apoio, sem criar curso português ou reativar latim clássico. Testar igualdade entre catálogo alvo/seed e mapa. Sem inferência de navegador, localização ou nacionalidade.

## Contrato e fluxo

Cadastro preservado. Onboarding aceita native_language opcional; omissão preserva o valor atual, null explícito limpa. GET/PATCH profile e GET auth/me devolvem native_language e native_language_required. PATCH name torna-se opcional para permitir atualização apenas de idioma; campos omitidos não são apagados. Expor códigos aceitos no perfil/status sem endpoint novo.

Uma política central recebe alvo/nativo/CEFR e devolve princípios, idioma da explicação, disponibilidade de apoio e regra de terceira língua. Prompts recebem os três parâmetros; suporte/translations seguem idioma nativo, nunca português fixo. PRE_A1/A1 apoio frequente; A2 breve; B1 pontual e explicação alvo; B2 apenas útil; C1/C2 apenas solicitado/necessário. Sem percentuais.

## Conteúdo e compatibilidade

NULL não vira pt-BR nem en. Contas/perfil/onboarding/encerramento continuam disponíveis; conteúdo estático que depende de apoio exige escolha explícita (409 native_language_required). IA com nativo ausente recebe instrução de alvo apenas e metadata de escolha pendente.

Biblioteca/mock existentes têm apoio português. Usá-los apenas para native=pt-BR, identificados por provenance; outro nativo deve usar geração IA configurada com contexto correto. Sem IA/material compatível: erro recuperável native_support_unavailable; não mudar provedor/configuração e não traduzir corpus. Vocabulário/SRS legado com translation_pt exige cautela e não pode ser reaproveitado como apoio em outra língua sem provenance.

Envelope mantém campos antigos e adiciona target_language, native_language, native_language_required e language_policy; conteúdo principal, tradução, explicação e áudio ficam em campos existentes separados. Áudio mantém language_code=alvo. Cache/lessons/contextos anteriores não são reinterpretados após troca de nativo; rejeitar ou não reutilizar conteúdo incompatível, sem apagar dados.

Guard determinístico passa a considerar alvo+nativo, campos de explicação/apoio e frases inglesas reconhecíveis; inglês de apoio é válido se native=en, mas não substitui conteúdo principal alemão. Não certifica idioma universalmente. Política é propagada a conversa/tutor/avaliação escrita e chamadas de IA da Teaching Engine quando existirem; endpoints sem contexto nativo não recebem default universal.

## Causa conhecida e limites

“A lógica” = lesson.explanation (frontend somente leitura). Geração OpenRouter recebia contexto de português e validador verificava título/campos-alvo, não explicação. Isso permite inglês nesse campo; corrigir contexto+guard+entrega, não rótulo. Sem imagem/ID/texto exato e sem acesso a produção, origem persistida da ocorrência original permanece não confirmada.

## Validação

Testar persistência, omissão/null, me/perfil/onboarding, inválidos, legados, FR/PT, DE/EN, EN/PT, prompts/CEFR, guard de explicação, metadados/áudio, material estático incompatível, conteúdo/cache após mudança, migration de 0015→0016 com usuário existente e cadeia Alembic. Rodar testes focais e suíte completa sobre versão final. Não executar migration no banco local existente nem produção; usar SQLite temporário de teste.
