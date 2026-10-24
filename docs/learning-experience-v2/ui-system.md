# Sistema de interface — Learning Experience V2

A interface permanece em português. Cada família de interação tem um componente. O teste de diversidade recusa uma tela que resolva tipos diferentes com a mesma interação, e recusa tipo oficial caindo no fallback genérico.

## Famílias na tela

| Família | O que o aluno faz |
|---|---|
| presentation, audio_model | lê ou ouve e continua |
| choice, audio_choice | escolhe uma alternativa com o teclado de setas |
| inline_gap | escreve na lacuna da frase |
| tap_order | monta a frase tocando os tokens; Backspace desfaz |
| pair_match | liga um item da esquerda e outro da direita, sem revelar o par |
| recall, guided_input, open_input | escreve a resposta |
| speech_repeat, speech_shadow, speech_retell | ouve e grava |
| dialogue, transfer | responde no contexto da missão |
| dictation | ouve e escreve; o transcript fica oculto quando `show_text` não é verdadeiro |

Matching continua com Continuar, porque o servidor ainda avalia esse tipo como leitura.

## Shell, dia e resumo

O shell mostra a fase pedagógica (Aquecimento, Descoberta, Observe, Prática, Produção, Avaliação, Revisão, Nova tentativa, Desafio, Concluído) e devolve o foco para a atividade depois de enviar, tentar de novo ou restaurar.

O dia mostra «Ao terminar, você será capaz de…» a partir do objetivo. Dia sem blocos diz «Este dia ainda não tem atividades.» e não conta como missão concluída. A barra de progresso só aparece quando há blocos.

O resumo repete o estado de domínio enviado pelo servidor. `mastered` é «Dominado». Outro estado não é promovido.

## Teclado, foco e axe

Escolha usa rádio com setas e um único item na ordem de tabulação. Ordem e pares movem o foco entre botões irmãos com setas. O feedback recebe foco quando muda. Os alvos de toque do caminho do dia têm 44px, e o movimento respeita `prefers-reduced-motion`.

`vitest-axe` olha as famílias, o shell e o resumo. O matcher `toHaveNoViolations` desta versão não registra no Vitest; o teste compara `violations` com uma lista vazia. Contraste de cor fica de fora no jsdom, porque o Tailwind não calcula cor ali. Isso não certifica WCAG no navegador.

## Sessão no navegador

`frontend/e2e/fr-b1-session.spec.ts` sobe a API em SQLite (`127.0.0.1:8011`) e o Next em `127.0.0.1:3011`, com `NEXT_PUBLIC_API_URL` apontando para essa API. Não entra no `npm test`. O comando é `npm run test:e2e`.
