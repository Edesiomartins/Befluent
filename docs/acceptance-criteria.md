# Critérios de Aceitação — Fluentia

Critérios observáveis e testáveis. Evitar “funcionar bem”, “bonito”, “rápido”, “usável” ou “UX simples” sem comportamento verificável.

Relacionados: [product-requirements.md](product-requirements.md), [roadmap.md](roadmap.md), [testing-strategy.md](testing-strategy.md), [screens.md](screens.md).

## Gerais

- Dado usuário não autenticado, ao acessar rota protegida, o sistema redireciona para login ou responde 401 e exibe caminho para login.
- Dado falha de API, a UI mostra mensagem em português e, se `retryable`, exibe controle “Tentar novamente”.
- Em toda tela de lista ou detalhe entregue, existem estados distintos de carregamento, vazio e erro.
- Nenhuma tela apresenta mais de uma ação primária no mesmo contexto visível.
- Nenhum arquivo de frontend contém chave de OpenRouter/STT/TTS.
- Textos da interface principal estão em português.
- O usuário consegue concluir o fluxo principal (login → dashboard → iniciar estudo) sem abrir Configurações.
- Critérios de desempenho (latência, throughput) só serão exigidos quando limiares forem definidos e registrados; **não inventar números** nesta etapa.

## Autenticação

- Login com credenciais válidas do usuário autorizado cria cookie HTTP-only e navega para dashboard ou onboarding.
- O navegador não armazena JWT (nem token de sessão) em `localStorage` ou `sessionStorage`.
- Login inválido não autentica e mostra erro sem detalhar internals.
- Logout invalida a sessão; chamada autenticada subsequente falha até novo login.
- Não existe fluxo de cadastro público.
- Formulário de login apresenta mensagem de validação quando campos obrigatórios estão vazios.

## Dashboard

- Exibe o idioma ativo **ou**, se nenhum estiver ativo, um CTA explícito para selecionar idioma.
- Exibe exatamente uma ação primária de continuidade de estudo (ex.: “Continuar” / “Iniciar”) **ou** estado vazio com texto explícito (“Nenhuma sessão ainda”) e CTA para começar.
- Em larguras móveis comuns (~360–430px), a ação primária do dashboard fica visível sem rolagem vertical inicial.
- Links para Progresso e Configurações estão presentes, com rótulo visível, e navegam para as rotas corretas.

## Idiomas

- Lista contém exatamente: Inglês, Espanhol da Espanha, Francês, Japonês, Mandarim.
- Ativar um idioma persiste `UserLanguage` e esse idioma aparece como ativo nas telas seguintes.
- Na UI e nos dados, o espanhol é identificado como espanhol da Espanha (não como variante latino-americana genérica).

## Diagnóstico

- Usuário inicia diagnóstico para idioma sem diagnóstico concluído.
- Ao concluir, o sistema persiste resultado com faixa estimada e limitações visíveis (sem equivalência rígida obrigatória CEFR/JLPT/HSK).
- Falha de IA mostra erro e permite retry sem perder respostas já confirmadas pelo servidor.
- Durante o diagnóstico, há estado de carregamento entre itens e estado de erro se a API falhar.

## Plano

- Após diagnóstico (ou sob demanda), o plano atual lista itens com status legível.
- Ao iniciar um item, o sistema registra o start no backend e navega para a atividade correspondente, ou exibe erro claro se a navegação não for possível.

## Aulas

- Abrir aula exibe objetivo e ao menos uma atividade.
- Submeter atividade retorna feedback persistido recuperável depois.
- Concluir aula altera o status persistido para concluída.
- Estados de carregamento e erro existem ao carregar e ao submeter.

## Conversação textual

- Usuário envia mensagem e recebe resposta do tutor persistida no histórico.
- Correções, quando houver, aparecem em bloco/região separada da resposta do tutor.
- Timeout ou resposta inválida de IA retorna erro com `retryable` verdadeiro (ou equivalente UI).

## Conversação por voz

- Com microfone permitido, o áudio enviado resulta em texto (STT) processado na conversa.
- Com microfone negado ou STT falho, a UI oferece alternativa textual e permite continuar a conversa por texto.
- Após o processamento, não permanece URL pública permanente do áudio enviado (limpeza verificável).

## Vocabulário

- É possível criar e listar itens por idioma.
- Após criação bem-sucedida, o item aparece na listagem sem recarregar a aplicação manualmente (ou após refresh explícito documentado).
- Campos de leitura/pinyin/caracteres, quando preenchidos, seguem as regras do idioma ativo.

## Revisão

- `GET /reviews/due` retorna apenas itens não suspensos com `next_review_at` menor ou igual ao momento da consulta.
- Após `POST /reviews/{id}/answer` com grade válida, o backend persiste novo `next_review_at` diferente do valor anterior **ou**, no caso de domínio/suspensão, remove o item da fila due; a regra exata depende do algoritmo autorizado em [decisions.md](decisions.md) (P-010).
- Se a fila estiver vazia, a UI mostra “Nada pendente hoje” (ou texto equivalente fixo).

## Gramática

- Lista tópicos do idioma ativo.
- Submeter prática retorna feedback e atualiza o progresso persistido do tópico.
- Estados vazio/erro existem se não houver tópicos ou se a API falhar.

## Escuta

- Atividade apresenta áudio (ou TTS) e questões.
- Sempre existe alternativa textual (script/transcrição) disponível conforme as regras pedagógicas da atividade (antes ou após tentativa, de forma explícita na UI).
- Submit grava resultado.
- Se TTS falhar, a UI mostra mensagem em português e mantém caminho textual.

## Pronúncia

- Tentativa com alvo + áudio gera feedback persistido.
- A UI indica explicitamente se o feedback é aproximado (baseado em transcrição) ou fonético especializado.
- Sem provedor fonético configurado, o sistema não afirma precisão fonética científica.

## Leitura

- Texto e questões são exibidos.
- Respostas submetidas são corrigidas e salvas com id recuperável.
- Existem estados de carregamento, vazio (sem texto) e erro.

## Escrita

- Submissão de texto retorna feedback com explicações.
- O registro fica recuperável por id.
- Formulário rejeita envio vazio com mensagem de validação.

## Progresso

- Resumo por idioma exibe apenas dados derivados de sessões/registros reais persistidos.
- Sem sessões, a UI mostra estado vazio explícito (não um gráfico vazio sem explicação).

## Segurança

- Rotas `/api/v1/*`, exceto login (e health fora do prefixo), exigem autenticação.
- Em produção, CORS não permite origem `*`.
- Upload acima do limite retorna 413 com mensagem em português.
- Logs de aplicação não contêm senha, token de sessão, JWT ou chave de API.
- JWT em `localStorage` está proibido.

## Acessibilidade

- Fluxo de login é concluível apenas com teclado (Tab/Enter), com foco visível.
- Controles de áudio possuem nome acessível (rótulo ou `aria-label`).
- Mensagens de erro de formulário estão associadas ao campo correspondente.

## Responsividade

- Telas login, dashboard e conversação não geram scroll horizontal do layout base em larguras ~360px, ~768px e ~1280px.
- Em mobile, a ação primária dessas telas permanece alcançável; se o teclado virtual cobrir o campo ativo, a ação de envio permanece acessível por scroll ou layout ajustado (verificação manual documentada).
- Nenhuma dessas telas exibe mais de uma ação primária simultânea.

## Deploy

- `GET /health` responde sucesso no ambiente publicado.
- HTTPS está ativo no domínio.
- Login com o usuário autorizado funciona no ambiente publicado.
- Checklist de [deployment-coolify.md](deployment-coolify.md) é cumprido antes de desligar serviço anterior (se houver).

## Critério transversal de conclusão de funcionalidade

Uma funcionalidade só é aceita se:

1. atende os critérios observáveis do módulo;
2. possui estados de carregamento, vazio e erro quando aplicável;
3. possui tratamento de erro definido em [error-handling.md](error-handling.md) / API;
4. foi testada conforme [testing-strategy.md](testing-strategy.md);
5. está documentada;
6. apresenta no máximo uma ação primária por contexto de tela;
7. não compromete autenticação, privacidade nem estabilidade (sem regressão de login, sem vazamento de segredos, sem quebra de `/health`).
