# BeFluent — Diagnóstico Pareto e progresso por domínio

## Objetivo

Fazer o nivelamento orientar as primeiras práticas e fazer a aba Progresso
representar domínio demonstrado, não volume de atividades concluídas.

## Escopo aprovado

1. Seleção adaptativa independente por habilidade objetiva: vocabulário e
   gramática, leitura e escuta.
2. Evidência mínima antes de estimar uma habilidade.
3. Escrita heurística exibida como amostra, sem participar do nível geral.
4. Três prioridades acionáveis derivadas de lacunas observadas.
5. Semana inicial de calibração antes de o currículo consolidar a trajetória.
6. Nova aba Progresso com domínio geral, habilidades e caminho CEFR.

## Princípios de produto

- Concluir uma atividade não é demonstrar domínio.
- Um erro preserva a evidência anterior, mas não aumenta o domínio e deve abrir
  remediação ou revisão quando houver objetivo identificado.
- O produto não exibirá uma precisão que os dados não sustentam.
- Fala e escrita sem avaliação confiável aparecem como não avaliadas, sem
  contaminar a métrica geral.

## Diagnóstico

### Estado adaptativo por habilidade

O teste manterá uma faixa, streaks e contagens por habilidade objetiva. A
seleção alterna habilidades ainda sem evidência suficiente, mas apenas os
acertos/erros da própria habilidade promovem ou rebaixam sua faixa. A ordem
continua variada para não ficar previsível.

### Evidência mínima

Uma habilidade só recebe faixa estimada se tiver pelo menos quatro itens
objetivos respondidos e pelo menos dois na faixa que sustenta a estimativa.
Quando faltar cobertura, o resultado será `em_calibracao`, não um nível
inventado. O nível geral considera somente habilidades com evidência válida e
reduz a confiança quando houver cobertura incompleta.

O banco inicial não tem itens suficientes para satisfazer essa regra em todas
as combinações. A implementação deve expor essa limitação com honestidade e
servir itens disponíveis sem promover artificialmente a habilidade. A expansão
do banco será uma entrega seguinte, com itens revisados.

### Escrita e fala

Enquanto a escrita usar a heurística atual, seu resultado será registrado como
amostra e feedback preliminar, mas não terá peso no nível geral, nas barras de
domínio ou no plano. Fala seguirá como não avaliada até que exista avaliação
real.

### Prioridades e calibração

O resultado derivará no máximo três prioridades ordenadas por: habilidade sem
evidência, habilidade abaixo do geral e padrões de erro identificáveis. Cada
prioridade terá texto curto e um destino para prática/revisão quando houver
objetivo existente.

O currículo gerado pelo nivelamento terá uma fase inicial de uma semana de
calibração. Nela, as habilidades sem evidência ou abaixo do geral recebem maior
peso. Ao final, um checkpoint usa as tentativas reais para confirmar ou ajustar
o caminho restante; não há mudança automática de CEFR sem evidência suficiente.

## Progresso por domínio

### Fonte de verdade

Não será criada uma pontuação paralela. A agregação usará registros já
persistidos pelo Teaching Engine:

- `UserObjectiveProgress.state`;
- `LearningEvidence`;
- `LearningAttempt`;
- `LearningError` aberto/resolvido;
- eventos de revisão em `MemoryReviewEvent`/`MemorySchedule`.

Atividades legadas sem objetivo continuarão visíveis como atividade concluída,
mas não aumentam a métrica de domínio. Isso impede que o gráfico premie apenas
presença.

### Cálculo v1

Para cada objetivo, o estado é convertido em contribuição transparente:

| Estado | Contribuição |
|---|---:|
| não iniciado | 0 |
| aprendendo | 25 |
| praticando | 50 |
| precisa de revisão/remediação | 35 |
| retomando tentativa | 45 |
| dominado | 100 |

Erro aberto impede que o objetivo suba para `dominado`; remediação resolvida e
evidência posterior permitem a recuperação. Os números são faixas de interface,
não uma alegação psicométrica. O agregado geral é a média ponderada dos
objetivos ativos; agregados por habilidade usam apenas objetivos daquela
habilidade. Se não houver objetivos suficientes, a interface mostra `Dados em
calibração` em vez de percentual enganoso.

O gráfico temporal é calculado por snapshots diários da agregação, reconstruídos
a partir dos eventos existentes na primeira versão. Não será gravada uma tabela
de snapshots agora; isso mantém a solução reversível. Se a consulta se tornar
cara, uma projeção materializada poderá ser introduzida depois.

### Caminho CEFR

O cartão CEFR exibirá:

- faixa atual estimada e sua confiança;
- próxima faixa possível;
- percentual de domínio atual como evidência de preparação, nunca como garantia
  de promoção;
- competências não avaliadas ou ainda em calibração.

Não haverá previsão de prazo para subir de faixa. O percentual é associado a
domínio dos objetivos do nível atual, não a uma conversão automática para CEFR.

## API

Expandir `GET /api/v1/progress` com um bloco `mastery`:

```json
{
  "mastery": {
    "status": "ready | calibrating | unavailable",
    "overall_percent": 54,
    "by_skill": [{"skill": "listening", "percent": 35, "objective_count": 4}],
    "timeline": [{"date": "2026-09-17", "overall_percent": 54}],
    "cefr": {"current": "A2", "next": "B1", "readiness_percent": 54},
    "priorities": [{"skill": "listening", "label": "Compreensão auditiva", "reason": "...", "href": "..."}]
  }
}
```

O endpoint mantém os campos atuais para não quebrar o frontend existente.

## Interface

Uma aba/rota autenticada `Progresso` conterá:

1. cartão de domínio geral e estado de calibração;
2. gráfico de linha semanal de domínio;
3. cartão do caminho CEFR;
4. barras por habilidade;
5. três prioridades Pareto com ação de estudo;
6. mensagem explícita quando uma atividade concluída ainda não gerou domínio.

O gráfico será feito com componentes já disponíveis ou SVG acessível simples;
uma dependência nova só será adicionada se a biblioteca atual não cobrir a
interação necessária.

## Erros e estados vazios

- Sem idioma ativo: orientar a configurar um idioma.
- Sem objetivos/evidências: explicar que o domínio será calibrado nas primeiras
  práticas e não renderizar gráfico artificial.
- Falha da API: usar o componente de erro existente com nova tentativa.
- Dados parciais: mostrar o que existe e rotular o restante como calibração.

## Testes

- testes unitários para cálculo de domínio, erro aberto, erro resolvido,
  agregação por habilidade e timeline;
- testes de API para contrato, autenticação e estado vazio;
- testes do motor de placement para independência entre habilidades, evidência
  mínima e escrita fora do peso;
- testes de frontend para dados prontos, calibração, erro e navegação das
  prioridades.

## Fora do escopo desta entrega

- novo provedor/modelo de IA;
- STT ou avaliação de pronúncia;
- classificação CEFR C1/C2;
- expansão e validação pedagógica completa do banco de itens;
- FSRS.
