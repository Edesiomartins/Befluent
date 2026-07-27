# Acessibilidade — BeFluent

Relacionados: [design-system.md](design-system.md), [screens.md](screens.md), [speech-architecture.md](speech-architecture.md).

## Objetivo

Tornar o BeFluent utilizável por teclado, leitores de tela e em diferentes condições sensoriais/motoras, sem abrir mão da interface adulta e limpa.

## Navegação por teclado

- Todas as ações principais acessíveis via teclado.
- Ordem de foco lógica.
- Atalhos futuros não devem quebrar Tab/Enter/Esc.
- Modais: foco preso; Esc fecha; retorno ao gatilho.

## Foco visível

- Indicador de foco sempre perceptível.
- Não remover outline sem substituto.

## Contraste

- Texto e controles com contraste adequado (meta WCAG AA como referência).
- Não depender só de cor para acerto/erro.

## Leitores de tela

- Landmarks e headings coerentes.
- Nomes acessíveis em botões de ícone (gravar, play, etc.).
- Atualizações importantes via live regions quando fizer sentido (ex.: “processando áudio”).

## Rótulos

- Labels em formulários.
- Erros associados ao campo (`aria-describedby` ou equivalente).

## Legendas e transcrições

- Conteúdo falado deve ter alternativa textual.
- TTS: texto visível junto.
- Atividades de escuta: após tentativa, revelar script conforme desenho pedagógico (sem sabotar o exercício cedo demais).

## Alternativas ao áudio

- Modo texto em conversação.
- Se microfone/STT falhar, continuar estudando.

## Controles de velocidade

- Velocidade de TTS ajustável.
- Controles claros de play/pause/stop.

## Tamanho de texto

- Tipografia relativa.
- Evitar truncar conteúdo crítico.
- Layout não quebra com zoom do navegador em níveis razoáveis.

## Redução de animações

- Respeitar preferência de reduzir movimento do sistema.
- Animações só se agregarem clareza; nunca essenciais à informação.

## Mensagens de erro acessíveis

- Texto legível, não só ícone/cor.
- Foco ou anúncio quando erro bloquear envio.

## Uso em celular

- Alvos de toque adequados.
- Controles de gravação fáceis de acionar.
- Evitar gestos sem alternativa.

## Internacionalização futura

- Interface hoje em português.
- Estruturar copy para possível i18n futura, sem implementar agora.
- Conteúdo pedagógico permanece multi-idioma por natureza.

## Critérios verificáveis (amostra)

- Login completo só com teclado.
- Botão de microfone tem nome acessível.
- Erro de formulário é anunciável/associado.
- Player de áudio operável por teclado.
- Contraste dos textos principais passa checagem básica.
