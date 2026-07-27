# Telas — Fluentia

Documentos relacionados: [user-flows.md](user-flows.md), [design-system.md](design-system.md), [accessibility.md](accessibility.md).

## Princípios de tela

- Interface em português, adulta e acadêmica.
- Uma finalidade clara por tela.
- Sem sobrecarga de métricas ou botões.
- Estados obrigatórios: carregamento, vazio e erro.

---

## Login

- **Objetivo:** autenticar o usuário autorizado.
- **Informações:** formulário de credenciais; mensagem de erro se houver.
- **Ações:** entrar.
- **Carregamento:** botão desabilitado + indicador.
- **Vazio:** não se aplica.
- **Erro:** credenciais inválidas ou falha de servidor, com mensagem clara.
- **Celular:** formulário em coluna única, teclado adequado.
- **Conclusão:** sessão criada e redirecionamento correto.

## Onboarding

- **Objetivo:** apresentar o Fluentia e coletar preferências iniciais.
- **Informações:** propósito do app; próximos passos.
- **Ações:** continuar; escolher idioma inicial.
- **Carregamento:** transição entre passos.
- **Vazio:** não se aplica.
- **Erro:** falha ao salvar preferências.
- **Celular:** passos curtos, um por viewport quando possível.
- **Conclusão:** onboarding marcado como concluído.

## Seleção de idioma

- **Objetivo:** escolher o idioma de estudo ativo.
- **Informações:** inglês, espanhol da Espanha, francês, japonês, mandarim; status (novo / em andamento).
- **Ações:** selecionar idioma; iniciar diagnóstico se necessário.
- **Carregamento:** lista em skeleton.
- **Vazio:** se catálogo falhar, mensagem + retry.
- **Erro:** falha ao ativar idioma.
- **Celular:** lista empilhada, alvos de toque amplos.
- **Conclusão:** idioma ativo definido.

## Dashboard

- **Objetivo:** mostrar o próximo passo e resumo útil.
- **Informações:** idioma ativo; próxima atividade; sessão recente; alertas de revisão.
- **Ações:** continuar estudo; trocar idioma; abrir progresso; configurações.
- **Carregamento:** placeholders do resumo.
- **Vazio:** “Nenhuma sessão ainda” + CTA para começar.
- **Erro:** falha ao carregar resumo.
- **Celular:** hierarquia vertical; CTA principal no topo.
- **Conclusão:** usuário entende o que fazer a seguir.

## Diagnóstico

- **Objetivo:** estimar nível e dificuldades iniciais.
- **Informações:** progresso do diagnóstico; pergunta/atividade atual; instruções.
- **Ações:** responder; pular se permitido; concluir.
- **Carregamento:** entre itens e ao gerar resultado.
- **Vazio:** não se aplica após início.
- **Erro:** falha de IA/API com retry.
- **Celular:** uma atividade por vez.
- **Conclusão:** perfil inicial gerado e plano oferecido.

## Plano de estudo

- **Objetivo:** exibir a sequência recomendada.
- **Informações:** itens do plano; status; foco do idioma.
- **Ações:** iniciar item; voltar ao dashboard.
- **Carregamento:** skeleton da lista.
- **Vazio:** “Plano ainda não gerado” + gerar.
- **Erro:** falha ao carregar/gerar plano.
- **Celular:** lista simples sem cartões excessivos.
- **Conclusão:** plano legível e acionável.

## Aprender

- **Objetivo:** hub de atividades do idioma ativo.
- **Informações:** categorias (aula, conversação, vocabulário, etc.).
- **Ações:** abrir atividade; voltar.
- **Carregamento:** skeleton.
- **Vazio:** se módulo indisponível na fase atual, indicar “em breve” sem inventar dados.
- **Erro:** falha ao listar.
- **Celular:** navegação clara.
- **Conclusão:** usuário chega à atividade desejada.

## Conversação

- **Objetivo:** praticar diálogo por texto e/ou voz.
- **Informações:** histórico; tema; correções; controles de voz quando disponíveis.
- **Ações:** enviar texto; gravar; reproduzir; encerrar.
- **Carregamento:** indicador enquanto a IA responde.
- **Vazio:** prompt inicial do tema.
- **Erro:** IA/áudio/conexão com fallback textual quando possível.
- **Celular:** área de mensagem fixa na parte inferior; controles de áudio acessíveis.
- **Conclusão:** mensagens salvas e feedback exibido.

## Aula guiada

- **Objetivo:** conduzir uma lição estruturada.
- **Informações:** objetivo; conteúdo; exercícios; progresso da aula.
- **Ações:** avançar; responder; concluir aula.
- **Carregamento:** ao carregar e ao corrigir.
- **Vazio:** não se aplica.
- **Erro:** falha ao carregar conteúdo ou corrigir.
- **Celular:** seções empilhadas.
- **Conclusão:** aula marcada como concluída.

## Pronúncia

- **Objetivo:** praticar fala com feedback.
- **Informações:** alvo; áudio modelo; resultado da tentativa; dicas.
- **Ações:** ouvir; gravar; repetir; próximo.
- **Carregamento:** durante envio/processamento.
- **Vazio:** sem itens → mensagem + voltar.
- **Erro:** microfone/STT; oferecer retry e texto.
- **Celular:** botão de gravação proeminente.
- **Conclusão:** tentativa registrada; feedback compreensível.
- **Nota:** avaliação fonética precisa depende de provedor (decisão pendente).

## Compreensão auditiva

- **Objetivo:** praticar escuta e compreensão.
- **Informações:** player; questões; feedback.
- **Ações:** play/pause/repetir/velocidade; responder.
- **Carregamento:** áudio e correção.
- **Vazio:** sem atividade disponível.
- **Erro:** falha de TTS/áudio.
- **Celular:** controles grandes; texto legível.
- **Conclusão:** respostas registradas e feedback mostrado.

## Vocabulário

- **Objetivo:** estudar e reforçar itens lexicais.
- **Informações:** item; significado; exemplo; áudio se houver.
- **Ações:** revelar; marcar dificuldade; ouvir.
- **Carregamento:** lote.
- **Vazio:** nada para revisar.
- **Erro:** falha ao carregar/salvar.
- **Celular:** cartão em tela cheia simples.
- **Conclusão:** progresso do lote atualizado.

## Revisão

- **Objetivo:** revisar erros e itens agendados.
- **Informações:** fila do dia; tipo (erro/vocabulário/gramática).
- **Ações:** revisar; adiar se permitido; concluir.
- **Carregamento:** fila.
- **Vazio:** “Nada pendente hoje”.
- **Erro:** falha ao atualizar agendamento.
- **Celular:** fluxo linear.
- **Conclusão:** itens atualizados.

## Leitura

- **Objetivo:** praticar leitura com compreensão.
- **Informações:** texto; glossário sob demanda; questões.
- **Ações:** marcar dificuldade; responder; pedir explicação.
- **Carregamento:** texto e correção.
- **Vazio:** sem texto.
- **Erro:** falha de geração/carregamento.
- **Celular:** tipografia confortável; largura adequada.
- **Conclusão:** atividade registrada.

## Escrita

- **Objetivo:** produzir texto com correção explicativa.
- **Informações:** prompt; área de escrita; correções.
- **Ações:** enviar; revisar; salvar.
- **Carregamento:** durante correção por IA.
- **Vazio:** prompt sem rascunho.
- **Erro:** timeout/IA inválida com retry.
- **Celular:** textarea ampla; teclado não cobrir ações críticas.
- **Conclusão:** submissão e feedback persistidos.

## Relatório da sessão

- **Objetivo:** sintetizar o que foi feito e o próximo passo.
- **Informações:** atividades; erros; destaques; recomendação.
- **Ações:** revisar erros; voltar ao dashboard.
- **Carregamento:** geração do relatório.
- **Vazio:** sessão sem atividades → mensagem honesta.
- **Erro:** falha na geração; mostrar resumo mínimo local se possível.
- **Celular:** seções curtas.
- **Conclusão:** relatório compreensível exibido.

## Progresso

- **Objetivo:** acompanhar evolução sem falsa precisão.
- **Informações:** histórico; habilidades; vocabulário; erros.
- **Ações:** filtrar por idioma; abrir sessão passada.
- **Carregamento:** gráficos/listas em skeleton.
- **Vazio:** sem dados ainda.
- **Erro:** falha ao carregar métricas.
- **Celular:** listas e resumos, evitar dashboard lotado.
- **Conclusão:** dados corretos e legíveis.

## Configurações

- **Objetivo:** ajustar preferências.
- **Informações:** idioma padrão; áudio; preferências de estudo.
- **Ações:** salvar; cancelar.
- **Carregamento:** ao salvar.
- **Vazio:** não se aplica.
- **Erro:** falha ao persistir.
- **Celular:** formulário empilhado.
- **Conclusão:** preferências refletidas nas próximas sessões.

## Página de erro

- **Objetivo:** informar falha inesperada sem jargão.
- **Informações:** mensagem amigável; código opcional de referência.
- **Ações:** tentar novamente; ir ao dashboard; sair.
- **Carregamento:** não se aplica.
- **Vazio:** não se aplica.
- **Erro:** é a própria tela.
- **Celular:** CTA claros.
- **Conclusão:** usuário sabe o que fazer.

## Página não encontrada

- **Objetivo:** indicar rota inexistente.
- **Informações:** mensagem “página não encontrada”.
- **Ações:** voltar ao dashboard.
- **Carregamento:** não se aplica.
- **Vazio:** não se aplica.
- **Erro:** não se aplica.
- **Celular:** layout simples.
- **Conclusão:** retorno seguro à área principal.
