# Design System — BeFluent

Documentos relacionados: [screens.md](screens.md), [accessibility.md](accessibility.md), [vision.md](vision.md).

## Direção visual

Identidade **adulta, limpa, moderna e acadêmica**.

- Sem aparência infantil.
- Sem excesso de gradientes.
- Sem excesso de cartões.
- Boa leitura e hierarquia clara.
- Responsiva para computador, tablet e celular.
- Textos da interface em português.

A paleta oficial BeFluent (azul e branco) está implementada nos tokens CSS do frontend.

## Princípios

1. Uma composição por seção; cada tela com um trabalho claro.
2. Tipografia legível; contraste adequado.
3. Espaçamento generoso, sem densificar métricas.
4. Feedback de estado sempre explícito (carregando, vazio, erro, sucesso).
5. Controles de áudio e correções linguísticas com padrões consistentes.

## Tokens semânticos

| Token | Valor | Uso |
|---|---|---|
| `background` / `surface-soft` | `#F5F9FF` | Fundo da página |
| `surface` | `#FFFFFF` | Superfície de conteúdo |
| `text-primary` | `#172033` | Texto principal |
| `text-secondary` | `#64748B` | Texto de apoio |
| `border` | `#DCE6F2` | Separadores |
| `primary` | `#2563EB` | Ação principal |
| `primary-hover` | `#1D4ED8` | Hover |
| `primary-strong` / `primary-deep` | `#0F2A5F` / `#0B1F44` | Painéis de destaque |
| `primary-soft` | `#DBEAFE` | Fundo suave |
| `success` | `#16A34A` | Sucesso |
| `warning` | `#D97706` | Atenção |
| `danger` | `#DC2626` | Erro |

Tipografia: Inter via `next/font`.

## Tipografia

- Hierarquia: título de página → subtítulo → corpo → meta.
- Evitar tipografia decorativa excessiva.
- Corpo com boa legibilidade em telas longas (leitura/escrita).
- Tamanhos relativos (rem) para permitir ajuste futuro.

## Espaçamento

- Escala consistente (ex.: 4/8 base — decisão de valores exatos pendente).
- Margens laterais generosas no mobile.
- Evitar “paredes” de elementos sem respiro.

## Bordas e sombras

- Bordas sutis; preferir separação por espaço/tipografia.
- Sombras mínimas; sem múltiplas camadas.
- Raio de borda moderado e consistente; evitar “pills” em tudo.

## Ícones

- Estilo linear/simples, tamanho consistente.
- Sempre acompanhados de rótulo quando a ação não for óbvia.
- Ícones de áudio (play, pause, microfone) padronizados.

## Botões

- Primário: uma ação principal por contexto.
- Secundário e terciário (texto) para ações de menor prioridade.
- Estado desabilitado visível.
- Loading no próprio botão quando a ação estiver em andamento.

## Formulários

- Labels sempre visíveis.
- Mensagens de erro próximas ao campo.
- Inputs com foco visível.
- Evitar placeholder como único rótulo.

## Cartões

- Usar com parcimônia.
- Preferidos quando agrupam interação (ex.: item de revisão).
- Não transformar o dashboard em mosaico de cartões.

## Modais

- Usar só para confirmações ou interrupções necessárias.
- Foco preso no modal; retorno de foco ao fechar.
- Escopo claro: título, corpo, ações.

## Alertas

- Sucesso, aviso, erro e info alinhados aos tokens.
- Mensagens curtas e acionáveis.
- Não usar alertas como decoração.

## Estados de foco

- Anel/contorno visível para teclado.
- Nunca remover outline sem substituto acessível.

## Estados desabilitados

- Reduzir contraste do controle, manter legibilidade mínima.
- Explicar por que está desabilitado quando não for óbvio.

## Feedback de carregamento

- Skeleton ou spinner contextual.
- Evitar tela totalmente em branco.
- Não inventar dados enquanto carrega.

## Padrões para áudio

- Controles: reproduzir, pausar, repetir, velocidade, gravar, parar.
- Indicar claramente estado “gravando” e “processando”.
- Em falha de microfone/serviço, oferecer fallback textual.
- Não depender só de cor para status (gravando/erro).

## Padrões para correções linguísticas

- Separar claramente: resposta do tutor × correção × explicação.
- Destacar o trecho corrigido sem poluir o texto.
- Tom respeitoso e útil (alinhado a [vision.md](vision.md)).
- Explicações em português quando o nível do usuário ainda precisar.

## Responsividade

- Mobile-first pragmático: coluna única, CTAs acessíveis.
- Tablet: aproveitar largura sem criar painéis concorrentes.
- Desktop: conteúdo principal legível; evitar sidebars densas.

## O que não fazer

- Tema infantil ou “app de criança”.
- Gradientes pesados como identidade.
- Excesso de badges, chips e cartões.
- Dashboard sobrecarregado de estatísticas.
- Paleta definitiva inventada sem validação visual.
