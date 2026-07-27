# Requisitos do Produto — BeFluent

## Visão resumida

O BeFluent é um webapp pessoal e privado para aprendizado de inglês, espanhol da Espanha, francês, japonês e mandarim, com apoio de inteligência artificial, prática guiada, voz e acompanhamento de progresso.

A interface permanece em português. O sistema é desenvolvido localmente e publicado depois em VPS própria via Coolify.

Documentos relacionados: [vision.md](vision.md), [stack.md](stack.md), [language-strategies.md](language-strategies.md).

## Problema que o BeFluent resolve

Ferramentas genéricas de idiomas costumam:

- ensinar todos os idiomas da mesma forma;
- priorizar jogos e gamificação em vez de comunicação real;
- oferecer pouco acompanhamento personalizado de erros;
- misturar variantes linguísticas sem aviso (ex.: espanhol);
- não adaptar o estudo ao desempenho real do aluno.

O BeFluent concentra, em um único ambiente privado, estudo estruturado, conversação, revisão e progresso, com estratégia própria por idioma.

## Usuário principal

- Proprietário do projeto.
- Uso pessoal.
- Sem cadastro público nesta fase.
- Apenas um usuário autorizado inicialmente.

## Objetivos

1. Desenvolver conversação nos idiomas alvo.
2. Melhorar compreensão auditiva e pronúncia.
3. Ampliar vocabulário e reforçar gramática.
4. Praticar leitura e escrita.
5. Registrar erros recorrentes e gerar revisões úteis.
6. Acompanhar progresso de forma compreensível.
7. Adaptar o estudo ao desempenho, sem excesso de exercícios.

## Escopo inicial

Esta documentação planeja o produto completo. **Nem todas as funcionalidades serão implementadas ao mesmo tempo.** A ordem de entrega está em [roadmap.md](roadmap.md).

Escopo documental desta etapa:

- requisitos, fluxos, telas, arquitetura, dados, API, IA, áudio, pedagogia, segurança, testes e deploy.

Fora desta etapa:

- código de frontend/backend;
- banco real;
- integrações reais;
- instalação de dependências.

## Funcionalidades principais (planejadas)

| Funcionalidade | Descrição resumida | Prioridade relativa |
|---|---|---|
| Login privado | Acesso autenticado de um único usuário | Alta |
| Dashboard | Visão do próximo passo e resumo de estudo | Alta |
| Seleção de idioma | Escolher e ativar um dos cinco idiomas | Alta |
| Diagnóstico inicial | Avaliar nível e dificuldades iniciais | Alta |
| Plano de estudo | Sequência de atividades recomendadas | Alta |
| Aula guiada | Lição estruturada com explicação e prática | Alta |
| Conversação por texto | Diálogo escrito com correção e explicação | Alta |
| Conversação por voz | Diálogo falado com STT/TTS | Média-Alta |
| Compreensão auditiva | Escuta + compreensão | Média |
| Pronúncia | Prática e feedback de fala | Média |
| Vocabulário | Aprendizado e reforço de itens lexicais | Alta |
| Gramática | Tópicos e prática aplicada | Média |
| Leitura | Textos com compreensão | Média |
| Escrita | Produção escrita com correção | Média |
| Repetição espaçada | Revisões programadas | Alta |
| Revisão de erros | Foco em erros recorrentes | Alta |
| Relatório de sessão | Síntese do que foi feito e aprendido | Alta |
| Acompanhamento de progresso | Métricas e histórico legíveis | Alta |
| Configurações | Preferências do usuário | Alta |

## Funcionalidades futuras

- Inglês médico como módulo separado.
- Avaliação de pronúncia fonética mais precisa (provedor pendente).
- Múltiplos usuários autorizados (ainda fora do escopo inicial).
- Redis para filas/cache, somente se houver necessidade real.
- Exportação avançada de dados de estudo.
- Internacionalização da interface (hoje fixa em português).

## Explicitamente fora do escopo

- Cadastro público.
- Assinatura, pagamento ou monetização.
- Marketplace de conteúdo.
- Rede social ou ranking público.
- Gamificação infantil (medalhas excessivas, mascotes, etc.).
- Equivalências rígidas e automáticas entre escalas (CEFR/JLPT/HSK).
- Armazenamento permanente de áudio sem necessidade.
- Exposição de chaves de API no frontend.

## Requisitos funcionais

| ID | Requisito |
|---|---|
| RF-01 | O sistema deve autenticar um único usuário autorizado. |
| RF-02 | A interface deve estar em português. |
| RF-03 | O usuário deve poder selecionar entre inglês, espanhol da Espanha, francês, japonês e mandarim. |
| RF-04 | Cada idioma deve seguir estratégia pedagógica própria. |
| RF-05 | O sistema deve oferecer diagnóstico inicial por idioma. |
| RF-06 | O sistema deve gerar e atualizar um plano de estudo. |
| RF-07 | O sistema deve permitir sessões de estudo com atividades guiadas. |
| RF-08 | O sistema deve permitir conversação textual com feedback. |
| RF-09 | O sistema deve permitir conversação por voz quando STT/TTS estiverem disponíveis. |
| RF-10 | O sistema deve registrar tentativas, erros e progresso. |
| RF-11 | O sistema deve recomendar a próxima atividade com base no desempenho. |
| RF-12 | O sistema deve gerar relatório ao encerrar uma sessão. |
| RF-13 | O sistema deve oferecer revisão espaçada e revisão de erros. |
| RF-14 | Em falha de IA, áudio ou conexão, o usuário deve receber mensagem clara e opção de retry quando fizer sentido. |
| RF-15 | Configurações devem permitir preferências básicas (idioma ativo, velocidade de áudio, etc.). |

## Requisitos não funcionais

| ID | Requisito |
|---|---|
| RNF-01 | Stack: Next.js, TypeScript, FastAPI, PostgreSQL, OpenRouter, Docker, Coolify. |
| RNF-02 | Aplicação privada, HTTPS em produção. |
| RNF-03 | Segredos apenas em variáveis de ambiente. |
| RNF-04 | Sessão com cookie HTTP-only. |
| RNF-05 | Interface responsiva (computador, tablet, celular). |
| RNF-06 | Experiência adulta, limpa e acadêmica. |
| RNF-07 | Redis não é dependência obrigatória na primeira versão. |
| RNF-08 | Áudios temporários devem ser excluídos quando não forem mais necessários. |
| RNF-09 | Testes locais obrigatórios antes de qualquer deploy. |
| RNF-10 | Funcionalidade só é concluída se atender o critério de qualidade em [vision.md](vision.md). |

## Indicadores úteis de progresso

- Sessões concluídas por idioma.
- Tempo de estudo efetivo.
- Itens de vocabulário em domínio / em revisão.
- Erros recorrentes resolvidos vs. ativos.
- Taxa de conclusão de atividades recomendadas.
- Evolução em habilidades (conversação, escuta, leitura, escrita, gramática, pronúncia) sem falsa precisão.

## Riscos principais

| Risco | Impacto | Mitigação |
|---|---|---|
| Escopo amplo demais | Atraso | Entrega por fases ([roadmap.md](roadmap.md)) |
| Dependência de provedores externos (IA/áudio) | Falhas de sessão | Fallback, timeout, mensagens claras |
| Falsa precisão de nível | Desmotivação / estudo inadequado | Escalas como referência, não equivalência rígida |
| Custo de tokens/áudio | Orçamento | Limites, resumos, controle de uso |
| Complexidade pedagógica por idioma | Qualidade desigual | Estratégias por idioma e fases de conteúdo |
| Armazenamento indevido de áudio | Privacidade | Minimização e exclusão |

## Critérios gerais de sucesso

1. O usuário consegue autenticar, escolher idioma e iniciar estudo sem fricção.
2. Cada sessão gera feedback útil e um relatório compreensível.
3. O sistema recomenda a próxima atividade com base em dados reais.
4. Falhas de IA/áudio não travam a aplicação sem explicação.
5. Nenhum segredo é exposto no frontend.
6. Deploy no Coolify ocorre somente após testes locais bem-sucedidos.
