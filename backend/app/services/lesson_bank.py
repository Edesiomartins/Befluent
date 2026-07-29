"""Conteúdo de lição usado quando não há provedor de IA configurado.

Por que existe: `AI_MOCK_MODE=true` é o padrão do projeto e o estado atual da
produção. Sem este módulo, o modo mock devolveria a mesma frase para todo mundo
e o teste de nivelamento continuaria sem efeito prático — que é exatamente o
problema que esta integração resolve. Aqui o conteúdo varia por faixa de nível.

LIMITAÇÃO DECLARADA: banco inicial de desenvolvimento, escrito para validar o
fluxo técnico de ponta a ponta. Não passou por validação pedagógica e não tem
cobertura uniforme entre os cinco idiomas — inglês é o mais completo. Com uma
chave OpenRouter configurada, `ai.py` gera conteúdo real por prompt e este banco
passa a ser apenas fallback.
"""

from __future__ import annotations

from app.core.levels import LEVEL_INDEX, CEFRLevel

#: Faixas de conteúdo. Agrupar níveis vizinhos evita manter sete versões de cada
#: lição num banco que é declaradamente provisório.
BAND_BEGINNER = "beginner"      # PRE_A1, A1
BAND_ELEMENTARY = "elementary"  # A2
BAND_INTERMEDIATE = "intermediate"  # B1
BAND_UPPER = "upper"            # B2, C1, C2


def band_for(level: str) -> str:
    index = LEVEL_INDEX.get(level, LEVEL_INDEX[CEFRLevel.A2])
    if index <= LEVEL_INDEX[CEFRLevel.A1]:
        return BAND_BEGINNER
    if index == LEVEL_INDEX[CEFRLevel.A2]:
        return BAND_ELEMENTARY
    if index == LEVEL_INDEX[CEFRLevel.B1]:
        return BAND_INTERMEDIATE
    return BAND_UPPER


# ---------------------------------------------------------------------------
# Vocabulário — por idioma e faixa
# ---------------------------------------------------------------------------

VOCABULARY: dict[str, dict[str, list[dict[str, str]]]] = {
    "en": {
        BAND_BEGINNER: [
            {"term": "good morning", "translation": "bom dia", "example": "Good morning! How are you?", "example_translation": "Bom dia! Como você está?", "usage_note": "Use até por volta do meio-dia."},
            {"term": "my name is", "translation": "meu nome é", "example": "My name is Ana.", "example_translation": "Meu nome é Ana.", "usage_note": "Forma mais comum de se apresentar."},
            {"term": "thank you", "translation": "obrigado(a)", "example": "Thank you for your help.", "example_translation": "Obrigado pela sua ajuda.", "usage_note": "Não muda com o gênero de quem fala."},
            {"term": "I don't understand", "translation": "eu não entendo", "example": "Sorry, I don't understand.", "example_translation": "Desculpe, eu não entendo.", "usage_note": "Frase essencial: peça repetição sem travar."},
            {"term": "how much", "translation": "quanto (custa)", "example": "How much is this?", "example_translation": "Quanto custa isto?", "usage_note": "Base de qualquer compra."},
            {"term": "water", "translation": "água", "example": "Can I have some water, please?", "example_translation": "Pode me trazer água, por favor?", "usage_note": "Substantivo incontável: sem artigo 'a'."},
        ],
        BAND_ELEMENTARY: [
            {"term": "to look for", "translation": "procurar", "example": "I'm looking for the train station.", "example_translation": "Estou procurando a estação de trem.", "usage_note": "Sempre com 'for' — 'look' sozinho é 'olhar'."},
            {"term": "used to", "translation": "costumava", "example": "I used to live in Recife.", "example_translation": "Eu morava em Recife.", "usage_note": "Só para hábitos do passado que não valem mais."},
            {"term": "on my way", "translation": "a caminho", "example": "I'm on my way to the office.", "example_translation": "Estou a caminho do escritório.", "usage_note": "Muito frequente em mensagens do dia a dia."},
            {"term": "to get used to", "translation": "acostumar-se", "example": "I'm getting used to the weather.", "example_translation": "Estou me acostumando com o clima.", "usage_note": "Diferente de 'used to': aqui há adaptação em curso."},
            {"term": "as soon as", "translation": "assim que", "example": "Call me as soon as you arrive.", "example_translation": "Me ligue assim que você chegar.", "usage_note": "Conector de tempo muito usado."},
            {"term": "instead of", "translation": "em vez de", "example": "Let's take the bus instead of a taxi.", "example_translation": "Vamos de ônibus em vez de táxi.", "usage_note": "O verbo depois de 'of' vai para o gerúndio."},
        ],
        BAND_INTERMEDIATE: [
            {"term": "to figure out", "translation": "descobrir, entender", "example": "We need to figure out a better solution.", "example_translation": "Precisamos descobrir uma solução melhor.", "usage_note": "Chegar a uma resposta por reflexão ou tentativa."},
            {"term": "to come up with", "translation": "bolar, propor", "example": "She came up with a great idea.", "example_translation": "Ela bolou uma ótima ideia.", "usage_note": "Criar algo novo, geralmente sob pressão."},
            {"term": "to keep up with", "translation": "acompanhar o ritmo", "example": "It's hard to keep up with the news.", "example_translation": "É difícil acompanhar as notícias.", "usage_note": "Manter o mesmo passo de algo que avança."},
            {"term": "to look forward to", "translation": "aguardar com expectativa", "example": "I'm looking forward to the trip.", "example_translation": "Estou ansioso pela viagem.", "usage_note": "O 'to' aqui é preposição: o verbo seguinte vai no gerúndio."},
            {"term": "to point out", "translation": "apontar, destacar", "example": "He pointed out an important detail.", "example_translation": "Ele destacou um detalhe importante.", "usage_note": "Chamar atenção para algo que passou despercebido."},
            {"term": "as far as I know", "translation": "até onde eu sei", "example": "As far as I know, the meeting is still on.", "example_translation": "Até onde eu sei, a reunião continua de pé.", "usage_note": "Sinaliza informação não confirmada."},
        ],
        BAND_UPPER: [
            {"term": "to bring about", "translation": "provocar, ocasionar", "example": "The policy brought about significant change.", "example_translation": "A política provocou mudanças significativas.", "usage_note": "Registro formal, comum em textos analíticos."},
            {"term": "for the time being", "translation": "por ora, no momento", "example": "For the time being, we'll keep the current process.", "example_translation": "Por ora, manteremos o processo atual.", "usage_note": "Marca uma decisão explicitamente provisória."},
            {"term": "to account for", "translation": "explicar, corresponder a", "example": "This accounts for most of the delay.", "example_translation": "Isso explica a maior parte do atraso.", "usage_note": "Dois sentidos: justificar ou representar uma proporção."},
            {"term": "notwithstanding", "translation": "apesar de", "example": "Notwithstanding the risks, they moved forward.", "example_translation": "Apesar dos riscos, eles seguiram em frente.", "usage_note": "Bastante formal; em fala prefira 'despite'."},
            {"term": "to be inclined to", "translation": "tender a, inclinar-se a", "example": "I'm inclined to agree with that view.", "example_translation": "Tendo a concordar com essa visão.", "usage_note": "Suaviza uma opinião sem torná-la vaga."},
            {"term": "by and large", "translation": "de modo geral", "example": "By and large, the results were positive.", "example_translation": "De modo geral, os resultados foram positivos.", "usage_note": "Generaliza admitindo exceções."},
        ],
    },
    "es-ES": {
        BAND_BEGINNER: [
            {"term": "buenos días", "translation": "bom dia", "example": "¡Buenos días! ¿Cómo estás?", "example_translation": "Bom dia! Como você está?", "usage_note": "No plural em espanhol, diferente do português."},
            {"term": "me llamo", "translation": "meu nome é", "example": "Me llamo Ana.", "example_translation": "Meu nome é Ana.", "usage_note": "Literalmente 'eu me chamo'."},
            {"term": "gracias", "translation": "obrigado(a)", "example": "Gracias por tu ayuda.", "example_translation": "Obrigado pela sua ajuda.", "usage_note": "Invariável, não muda com gênero."},
            {"term": "no entiendo", "translation": "não entendo", "example": "Perdona, no entiendo.", "example_translation": "Desculpe, não entendo.", "usage_note": "Peça repetição sem travar a conversa."},
            {"term": "¿cuánto cuesta?", "translation": "quanto custa?", "example": "¿Cuánto cuesta esto?", "example_translation": "Quanto custa isto?", "usage_note": "Note o ponto de interrogação inicial."},
            {"term": "agua", "translation": "água", "example": "¿Me pones un vaso de agua, por favor?", "example_translation": "Me traz um copo de água, por favor?", "usage_note": "Feminina, mas leva 'el' no singular: 'el agua'."},
        ],
        BAND_ELEMENTARY: [
            {"term": "buscar", "translation": "procurar", "example": "Estoy buscando la estación.", "example_translation": "Estou procurando a estação.", "usage_note": "Sem preposição, diferente do inglês 'look for'."},
            {"term": "soler", "translation": "costumar", "example": "Suelo desayunar a las ocho.", "example_translation": "Costumo tomar café da manhã às oito.", "usage_note": "Verbo muito usado; não tem equivalente direto em inglês."},
            {"term": "en cuanto", "translation": "assim que", "example": "Llámame en cuanto llegues.", "example_translation": "Me ligue assim que você chegar.", "usage_note": "Exige subjuntivo quando fala do futuro."},
            {"term": "en vez de", "translation": "em vez de", "example": "Vamos en autobús en vez de en taxi.", "example_translation": "Vamos de ônibus em vez de táxi.", "usage_note": "Muito próximo do português."},
            {"term": "acostumbrarse a", "translation": "acostumar-se a", "example": "Me estoy acostumbrando al clima.", "example_translation": "Estou me acostumando ao clima.", "usage_note": "Sempre com a preposição 'a'."},
            {"term": "de camino", "translation": "a caminho", "example": "Estoy de camino a la oficina.", "example_translation": "Estou a caminho do escritório.", "usage_note": "Frequente em mensagens rápidas."},
        ],
        BAND_INTERMEDIATE: [
            {"term": "darse cuenta de", "translation": "perceber", "example": "Me di cuenta de que era tarde.", "example_translation": "Percebi que era tarde.", "usage_note": "Falso amigo: não é 'realizar'."},
            {"term": "llevar a cabo", "translation": "realizar, executar", "example": "Llevaron a cabo el proyecto.", "example_translation": "Executaram o projeto.", "usage_note": "Registro mais formal."},
            {"term": "echar de menos", "translation": "sentir falta", "example": "Echo de menos a mi familia.", "example_translation": "Sinto falta da minha família.", "usage_note": "Na Espanha; na América Latina, 'extrañar'."},
            {"term": "por lo visto", "translation": "pelo visto", "example": "Por lo visto, no vendrá.", "example_translation": "Pelo visto, ele não virá.", "usage_note": "Marca conclusão a partir de indício."},
            {"term": "hacer falta", "translation": "ser necessário", "example": "Hace falta más tiempo.", "example_translation": "É necessário mais tempo.", "usage_note": "Construção impessoal muito comum."},
            {"term": "a pesar de", "translation": "apesar de", "example": "A pesar del retraso, llegamos.", "example_translation": "Apesar do atraso, chegamos.", "usage_note": "Idêntico ao português na forma e no uso."},
        ],
        BAND_UPPER: [
            {"term": "no obstante", "translation": "não obstante, contudo", "example": "No obstante, la decisión se mantuvo.", "example_translation": "Contudo, a decisão foi mantida.", "usage_note": "Registro formal, típico de texto escrito."},
            {"term": "de hecho", "translation": "de fato", "example": "De hecho, los datos lo confirman.", "example_translation": "De fato, os dados confirmam.", "usage_note": "Reforça com evidência."},
            {"term": "en la medida en que", "translation": "na medida em que", "example": "En la medida en que crece, se complica.", "example_translation": "Na medida em que cresce, se complica.", "usage_note": "Conector argumentativo."},
            {"term": "dar por sentado", "translation": "dar como certo", "example": "No des por sentado su apoyo.", "example_translation": "Não dê o apoio dele como certo.", "usage_note": "Expressão idiomática frequente."},
            {"term": "a raíz de", "translation": "em decorrência de", "example": "A raíz de la crisis, cambió todo.", "example_translation": "Em decorrência da crise, tudo mudou.", "usage_note": "Introduz causa em registro formal."},
            {"term": "en términos generales", "translation": "de modo geral", "example": "En términos generales, funcionó.", "example_translation": "De modo geral, funcionou.", "usage_note": "Generaliza admitindo exceções."},
        ],
    },
    "fr": {
        BAND_BEGINNER: [
            {"term": "bonjour", "translation": "bom dia / olá", "example": "Bonjour ! Comment allez-vous ?", "example_translation": "Bom dia! Como vai?", "usage_note": "Serve o dia inteiro até o fim da tarde."},
            {"term": "je m'appelle", "translation": "meu nome é", "example": "Je m'appelle Ana.", "example_translation": "Meu nome é Ana.", "usage_note": "Literalmente 'eu me chamo'."},
            {"term": "merci", "translation": "obrigado(a)", "example": "Merci pour votre aide.", "example_translation": "Obrigado pela sua ajuda.", "usage_note": "Invariável."},
            {"term": "je ne comprends pas", "translation": "não entendo", "example": "Pardon, je ne comprends pas.", "example_translation": "Desculpe, não entendo.", "usage_note": "Negação com 'ne... pas' em volta do verbo."},
            {"term": "combien", "translation": "quanto", "example": "C'est combien ?", "example_translation": "Quanto custa?", "usage_note": "Forma coloquial e muito usada."},
            {"term": "de l'eau", "translation": "água", "example": "Je voudrais de l'eau, s'il vous plaît.", "example_translation": "Eu queria água, por favor.", "usage_note": "Artigo partitivo: 'de l'' antes de vogal."},
        ],
        BAND_ELEMENTARY: [
            {"term": "chercher", "translation": "procurar", "example": "Je cherche la gare.", "example_translation": "Procuro a estação.", "usage_note": "Sem preposição depois do verbo."},
            {"term": "avoir besoin de", "translation": "precisar de", "example": "J'ai besoin d'aide.", "example_translation": "Preciso de ajuda.", "usage_note": "Construção com 'avoir', não com 'être'."},
            {"term": "dès que", "translation": "assim que", "example": "Appelle-moi dès que tu arrives.", "example_translation": "Me ligue assim que chegar.", "usage_note": "Com futuro em francês, diferente do português."},
            {"term": "au lieu de", "translation": "em vez de", "example": "Prenons le bus au lieu du taxi.", "example_translation": "Vamos de ônibus em vez de táxi.", "usage_note": "Seguido de infinitivo ou substantivo."},
            {"term": "s'habituer à", "translation": "acostumar-se a", "example": "Je m'habitue au climat.", "example_translation": "Estou me acostumando ao clima.", "usage_note": "Verbo pronominal com 'à'."},
            {"term": "en route", "translation": "a caminho", "example": "Je suis en route.", "example_translation": "Estou a caminho.", "usage_note": "Muito usado em mensagens."},
        ],
        BAND_INTERMEDIATE: [
            {"term": "se rendre compte", "translation": "perceber", "example": "Je me suis rendu compte de l'erreur.", "example_translation": "Percebi o erro.", "usage_note": "Sempre pronominal."},
            {"term": "mettre en place", "translation": "implementar", "example": "Ils ont mis en place un nouveau système.", "example_translation": "Implementaram um novo sistema.", "usage_note": "Muito frequente no mundo do trabalho."},
            {"term": "avoir du mal à", "translation": "ter dificuldade em", "example": "J'ai du mal à suivre.", "example_translation": "Tenho dificuldade em acompanhar.", "usage_note": "Seguido de infinitivo."},
            {"term": "il s'agit de", "translation": "trata-se de", "example": "Il s'agit d'un point important.", "example_translation": "Trata-se de um ponto importante.", "usage_note": "Impessoal: só existe com 'il'."},
            {"term": "d'ailleurs", "translation": "aliás", "example": "D'ailleurs, il a raison.", "example_translation": "Aliás, ele tem razão.", "usage_note": "Adiciona informação lateral relevante."},
            {"term": "malgré", "translation": "apesar de", "example": "Malgré le retard, tout s'est bien passé.", "example_translation": "Apesar do atraso, correu tudo bem.", "usage_note": "Seguido direto de substantivo."},
        ],
        BAND_UPPER: [
            {"term": "néanmoins", "translation": "no entanto", "example": "Néanmoins, la décision reste valable.", "example_translation": "No entanto, a decisão continua válida.", "usage_note": "Registro formal."},
            {"term": "dans la mesure où", "translation": "na medida em que", "example": "Dans la mesure où c'est possible.", "example_translation": "Na medida em que for possível.", "usage_note": "Conector argumentativo."},
            {"term": "faire l'objet de", "translation": "ser objeto de", "example": "Le projet a fait l'objet d'un débat.", "example_translation": "O projeto foi objeto de debate.", "usage_note": "Típico de texto administrativo."},
            {"term": "au demeurant", "translation": "aliás, de resto", "example": "Au demeurant, le résultat est bon.", "example_translation": "De resto, o resultado é bom.", "usage_note": "Bastante literário."},
            {"term": "compte tenu de", "translation": "tendo em conta", "example": "Compte tenu des risques, on attend.", "example_translation": "Tendo em conta os riscos, esperamos.", "usage_note": "Introduz ponderação formal."},
            {"term": "dans l'ensemble", "translation": "de modo geral", "example": "Dans l'ensemble, c'est positif.", "example_translation": "De modo geral, é positivo.", "usage_note": "Generaliza admitindo exceções."},
        ],
    },
    "ja": {
        BAND_BEGINNER: [
            {"term": "おはようございます", "translation": "bom dia", "example": "おはようございます。", "example_translation": "Bom dia.", "usage_note": "Forma polida; entre amigos, 'おはよう'."},
            {"term": "私は…です", "translation": "eu sou / meu nome é", "example": "私はアナです。", "example_translation": "Eu sou a Ana.", "usage_note": "'は' aqui lê-se 'wa', não 'ha'."},
            {"term": "ありがとうございます", "translation": "obrigado(a)", "example": "ありがとうございます。", "example_translation": "Muito obrigado.", "usage_note": "Forma polida completa."},
            {"term": "わかりません", "translation": "não entendo", "example": "すみません、わかりません。", "example_translation": "Desculpe, não entendo.", "usage_note": "Negativo polido de 'わかる'."},
            {"term": "いくらですか", "translation": "quanto custa?", "example": "これはいくらですか。", "example_translation": "Quanto custa isto?", "usage_note": "'か' marca a pergunta."},
            {"term": "水", "translation": "água", "example": "水をください。", "example_translation": "Água, por favor.", "usage_note": "Leitura: みず (mizu)."},
        ],
        BAND_ELEMENTARY: [
            {"term": "探しています", "translation": "estou procurando", "example": "駅を探しています。", "example_translation": "Estou procurando a estação.", "usage_note": "Forma ています indica ação em curso."},
            {"term": "…たことがあります", "translation": "já fiz (experiência)", "example": "日本に行ったことがあります。", "example_translation": "Já fui ao Japão.", "usage_note": "Estrutura de experiência passada."},
            {"term": "…たら", "translation": "quando / se", "example": "着いたら電話してください。", "example_translation": "Me ligue quando chegar.", "usage_note": "Condicional muito usado no dia a dia."},
            {"term": "…の代わりに", "translation": "em vez de", "example": "タクシーの代わりにバスで行きます。", "example_translation": "Vou de ônibus em vez de táxi.", "usage_note": "Precedido de substantivo + の."},
            {"term": "慣れる", "translation": "acostumar-se", "example": "生活に慣れてきました。", "example_translation": "Fui me acostumando com a vida aqui.", "usage_note": "Partícula に marca o alvo."},
            {"term": "…に向かっています", "translation": "estou a caminho de", "example": "会社に向かっています。", "example_translation": "Estou a caminho da empresa.", "usage_note": "Registro um pouco formal."},
        ],
        BAND_INTERMEDIATE: [
            {"term": "気づく", "translation": "perceber, notar", "example": "間違いに気づきました。", "example_translation": "Percebi o erro.", "usage_note": "Partícula に antes do verbo."},
            {"term": "…によると", "translation": "segundo, de acordo com", "example": "天気予報によると、明日は雨です。", "example_translation": "Segundo a previsão, amanhã chove.", "usage_note": "Cita fonte de informação."},
            {"term": "…わけではない", "translation": "não é bem que", "example": "嫌いなわけではない。", "example_translation": "Não é bem que eu não goste.", "usage_note": "Nega uma conclusão presumida."},
            {"term": "…ようにする", "translation": "procurar fazer", "example": "毎日練習するようにしています。", "example_translation": "Procuro praticar todo dia.", "usage_note": "Esforço deliberado e contínuo."},
            {"term": "とはいえ", "translation": "ainda assim", "example": "とはいえ、簡単ではない。", "example_translation": "Ainda assim, não é fácil.", "usage_note": "Conector concessivo."},
            {"term": "…にもかかわらず", "translation": "apesar de", "example": "雨にもかかわらず、行きました。", "example_translation": "Apesar da chuva, fomos.", "usage_note": "Registro formal."},
        ],
        BAND_UPPER: [
            {"term": "…を踏まえて", "translation": "com base em", "example": "結果を踏まえて判断します。", "example_translation": "Decidiremos com base nos resultados.", "usage_note": "Muito usado em contexto profissional."},
            {"term": "…に他ならない", "translation": "nada mais é que", "example": "努力の結果に他ならない。", "example_translation": "Nada mais é que resultado de esforço.", "usage_note": "Ênfase de registro escrito."},
            {"term": "…をめぐって", "translation": "em torno de (questão)", "example": "その件をめぐって議論がある。", "example_translation": "Há debate em torno do assunto.", "usage_note": "Típico de jornalismo."},
            {"term": "…とはいうものの", "translation": "embora se diga que", "example": "便利とはいうものの、高い。", "example_translation": "Embora seja prático, é caro.", "usage_note": "Concessão mais enfática."},
            {"term": "概して", "translation": "de modo geral", "example": "概して良い結果でした。", "example_translation": "De modo geral, bons resultados.", "usage_note": "Registro formal escrito."},
            {"term": "…に基づいて", "translation": "com base em", "example": "データに基づいて判断する。", "example_translation": "Decidir com base nos dados.", "usage_note": "Frequente em relatórios."},
        ],
    },
    "zh-CN": {
        BAND_BEGINNER: [
            {"term": "早上好", "translation": "bom dia", "example": "早上好！", "example_translation": "Bom dia!", "usage_note": "Pinyin: zǎoshang hǎo."},
            {"term": "我叫", "translation": "meu nome é", "example": "我叫安娜。", "example_translation": "Meu nome é Ana.", "usage_note": "Pinyin: wǒ jiào."},
            {"term": "谢谢", "translation": "obrigado(a)", "example": "谢谢你的帮助。", "example_translation": "Obrigado pela sua ajuda.", "usage_note": "Pinyin: xièxie."},
            {"term": "我不懂", "translation": "não entendo", "example": "对不起，我不懂。", "example_translation": "Desculpe, não entendo.", "usage_note": "Pinyin: wǒ bù dǒng."},
            {"term": "多少钱", "translation": "quanto custa", "example": "这个多少钱？", "example_translation": "Quanto custa isto?", "usage_note": "Pinyin: duōshao qián."},
            {"term": "水", "translation": "água", "example": "请给我一杯水。", "example_translation": "Me dê um copo de água, por favor.", "usage_note": "Pinyin: qǐng gěi wǒ yì bēi shuǐ."},
        ],
        BAND_ELEMENTARY: [
            {"term": "找", "translation": "procurar", "example": "我在找车站。", "example_translation": "Estou procurando a estação.", "usage_note": "Pinyin: zhǎo. 在 marca ação em curso."},
            {"term": "以前", "translation": "antigamente", "example": "我以前住在里约。", "example_translation": "Eu morava no Rio.", "usage_note": "Pinyin: yǐqián."},
            {"term": "一…就…", "translation": "assim que", "example": "你一到就给我打电话。", "example_translation": "Me ligue assim que chegar.", "usage_note": "Estrutura correlativa muito usada."},
            {"term": "而不是", "translation": "em vez de", "example": "坐公交车而不是打车。", "example_translation": "De ônibus em vez de táxi.", "usage_note": "Pinyin: ér bùshì."},
            {"term": "习惯", "translation": "acostumar-se / hábito", "example": "我慢慢习惯了。", "example_translation": "Fui me acostumando.", "usage_note": "Serve como verbo e substantivo."},
            {"term": "在路上", "translation": "a caminho", "example": "我在路上。", "example_translation": "Estou a caminho.", "usage_note": "Pinyin: zài lùshang."},
        ],
        BAND_INTERMEDIATE: [
            {"term": "发现", "translation": "descobrir, perceber", "example": "我发现了一个问题。", "example_translation": "Descobri um problema.", "usage_note": "Pinyin: fāxiàn."},
            {"term": "根据", "translation": "de acordo com", "example": "根据天气预报，明天下雨。", "example_translation": "Segundo a previsão, amanhã chove.", "usage_note": "Pinyin: gēnjù."},
            {"term": "不但…而且…", "translation": "não só… mas também…", "example": "他不但会英语，而且会法语。", "example_translation": "Ele não só fala inglês, mas também francês.", "usage_note": "Par correlativo frequente."},
            {"term": "尽量", "translation": "na medida do possível", "example": "我尽量每天练习。", "example_translation": "Procuro praticar todo dia.", "usage_note": "Pinyin: jǐnliàng."},
            {"term": "其实", "translation": "na verdade", "example": "其实没那么难。", "example_translation": "Na verdade não é tão difícil.", "usage_note": "Corrige uma impressão anterior."},
            {"term": "尽管", "translation": "apesar de", "example": "尽管下雨，我们还是去了。", "example_translation": "Apesar da chuva, fomos.", "usage_note": "Costuma vir com 还是."},
        ],
        BAND_UPPER: [
            {"term": "然而", "translation": "no entanto", "example": "然而，结果并不理想。", "example_translation": "No entanto, o resultado não foi ideal.", "usage_note": "Registro escrito."},
            {"term": "基于", "translation": "com base em", "example": "基于以上分析。", "example_translation": "Com base na análise acima.", "usage_note": "Formal, típico de relatório."},
            {"term": "在某种程度上", "translation": "até certo ponto", "example": "在某种程度上是对的。", "example_translation": "Até certo ponto está correto.", "usage_note": "Modaliza uma afirmação."},
            {"term": "归根结底", "translation": "no fim das contas", "example": "归根结底还是时间问题。", "example_translation": "No fim das contas é questão de tempo.", "usage_note": "Expressão de quatro caracteres."},
            {"term": "鉴于", "translation": "tendo em vista", "example": "鉴于目前的情况。", "example_translation": "Tendo em vista a situação atual.", "usage_note": "Bastante formal."},
            {"term": "总的来说", "translation": "de modo geral", "example": "总的来说，很成功。", "example_translation": "De modo geral, foi um sucesso.", "usage_note": "Generaliza admitindo exceções."},
        ],
    },
}


# ---------------------------------------------------------------------------
# Conteúdo por faixa, independente de idioma (estruturas e temas)
# ---------------------------------------------------------------------------

GRAMMAR_FOCUS: dict[str, dict[str, object]] = {
    BAND_BEGINNER: {
        "title": "Perguntas simples no presente",
        "objective": "Fazer e responder perguntas básicas sobre você.",
        "explanation": (
            "Neste nível o essencial é montar perguntas curtas sobre identidade, "
            "origem e rotina. A lógica: identifique quem faz a ação, o que é feito "
            "e onde. Comece pelas perguntas que você mais vai ouvir sobre si mesmo."
        ),
        "patterns": [
            "Pergunta de identidade: quem é você / como se chama",
            "Pergunta de origem: de onde você é",
            "Pergunta de rotina: o que você faz",
        ],
    },
    BAND_ELEMENTARY: {
        "title": "Passado simples e rotina",
        "objective": "Contar o que você fez, usando o passado com clareza.",
        "explanation": (
            "A dificuldade em A2 não é a regra, é a escolha: falar de um momento "
            "encerrado (passado simples) ou de um hábito (presente). A pista está "
            "no marcador de tempo da frase."
        ),
        "patterns": [
            "Momento encerrado e explícito → passado simples",
            "Hábito que continua válido → presente",
            "Sequência de fatos → passado em todos os verbos",
        ],
    },
    BAND_INTERMEDIATE: {
        "title": "Experiência × tempo encerrado",
        "objective": "Escolher entre experiência acumulada e fato datado.",
        "explanation": (
            "A lógica é a relação com o presente. Se o que importa é a experiência "
            "acumulada até agora, use a forma de experiência. Se há um momento "
            "passado fechado e explícito, use o passado simples. Falantes de "
            "português tendem a usar só o passado simples, porque é o que o "
            "português faz."
        ),
        "patterns": [
            "Sem marcador temporal fechado → forma de experiência",
            "Com marcador fechado (ontem, em 2019) → passado simples",
            "Ação iniciada no passado e ainda em curso → forma continuada",
        ],
    },
    BAND_UPPER: {
        "title": "Modalização e hipótese",
        "objective": "Expressar grau de certeza, hipótese e ressalva.",
        "explanation": (
            "Em B2 e acima, a precisão vem de modalizar: distinguir o que é certo, "
            "provável, possível e contrafactual. É o que separa uma opinião "
            "defensável de uma afirmação categórica que você não sustenta."
        ),
        "patterns": [
            "Certeza alta × probabilidade × possibilidade remota",
            "Hipótese sobre o presente × hipótese sobre o passado",
            "Ressalva que preserva o argumento principal",
        ],
    },
}

WRITING_TASKS: dict[str, dict[str, object]] = {
    BAND_BEGINNER: {
        "prompt": "Escreva de 3 a 5 frases se apresentando: nome, de onde você é e o que você faz.",
        "min_words": 25,
        "max_words": 60,
        "rubric_hints": ["Frases completas", "Informação pessoal básica", "Clareza acima de variedade"],
    },
    BAND_ELEMENTARY: {
        "prompt": "Descreva sua rotina diária: o que você faz de manhã, à tarde e à noite.",
        "min_words": 60,
        "max_words": 110,
        "rubric_hints": ["Sequência temporal clara", "Verbos de rotina", "Conectores simples"],
    },
    BAND_INTERMEDIATE: {
        "prompt": "Conte uma experiência importante para você e explique por que ela marcou.",
        "min_words": 90,
        "max_words": 150,
        "rubric_hints": ["Narrativa com começo e fim", "Passado consistente", "Justificativa explícita"],
    },
    BAND_UPPER: {
        "prompt": "Defenda sua opinião sobre trabalho remoto, reconhecendo ao menos um contra-argumento.",
        "min_words": 130,
        "max_words": 220,
        "rubric_hints": ["Tese explícita", "Contra-argumento tratado", "Conectores argumentativos", "Registro coerente"],
    },
}

CONVERSATION_SITUATIONS: dict[str, dict[str, str]] = {
    BAND_BEGINNER: {"situation": "Apresentar-se a alguém que você acabou de conhecer", "focus": "cumprimentos e informação pessoal"},
    BAND_ELEMENTARY: {"situation": "Pedir comida em um restaurante", "focus": "pedidos, preferências e conta"},
    BAND_INTERMEDIATE: {"situation": "Contar sobre uma viagem recente a um colega", "focus": "narrativa e detalhes"},
    BAND_UPPER: {"situation": "Discordar educadamente em uma reunião de trabalho", "focus": "argumentação e ressalva"},
}

READING_TEXTS: dict[str, dict[str, object]] = {
    BAND_BEGINNER: {
        "title": "Uma manhã comum",
        "text": (
            "Ana acorda às sete horas. Ela toma café da manhã com a família. "
            "Depois ela vai para o trabalho de ônibus. O trajeto leva trinta minutos. "
            "Ana gosta de ler durante a viagem."
        ),
        "note": "Frases curtas, vocabulário de rotina.",
    },
    BAND_ELEMENTARY: {
        "title": "Mudança de cidade",
        "text": (
            "No ano passado, Pedro se mudou para outra cidade por causa do trabalho. "
            "No começo foi difícil: ele não conhecia ninguém e sentia falta dos amigos. "
            "Aos poucos, começou a fazer novas amizades no bairro. Hoje ele diz que "
            "a mudança foi uma boa decisão, mesmo com as dificuldades do início."
        ),
        "note": "Passado, conectores simples, causa e consequência.",
    },
    BAND_INTERMEDIATE: {
        "title": "Como o trabalho flexível mudou as rotinas",
        "text": (
            "Para muitos profissionais, o trabalho flexível mudou mais do que o lugar "
            "onde as tarefas são feitas. Ele também alterou a forma como as pessoas "
            "organizam a atenção, se comunicam com colegas e separam trabalho e vida "
            "pessoal. Alguns valorizam a autonomia; outros sentem falta das conversas "
            "espontâneas do escritório. Pesquisas sugerem que os arranjos mais eficazes "
            "dependem menos de um modelo fixo e mais de expectativas claras."
        ),
        "note": "Texto expositivo, contraste de pontos de vista.",
    },
    BAND_UPPER: {
        "title": "Automação e o valor do trabalho humano",
        "text": (
            "O debate sobre automação costuma oscilar entre dois extremos igualmente "
            "improváveis: o desaparecimento generalizado do emprego e a criação "
            "espontânea de ocupações melhores. A evidência disponível sugere um "
            "cenário menos dramático e mais incômodo — a recomposição desigual das "
            "tarefas dentro das profissões existentes. Nem toda função é substituída; "
            "muitas são esvaziadas por dentro, perdendo justamente as atividades que "
            "conferiam autonomia a quem as exercia."
        ),
        "note": "Argumentação densa, nuance e ressalva.",
    },
}

LISTENING_SCRIPTS: dict[str, dict[str, object]] = {
    BAND_BEGINNER: {
        "transcript": "Bom dia. Meu nome é Carlos. Eu sou professor. Muito prazer.",
        "speaking_rate": "lenta, com pausas entre as frases",
        "note": "Apresentação pessoal simples.",
    },
    BAND_ELEMENTARY: {
        "transcript": (
            "Atenção, passageiros. O voo 482 para Madri está atrasado em trinta "
            "minutos. O embarque começará no portão dezesseis."
        ),
        "speaking_rate": "moderada, típica de anúncio público",
        "note": "Anúncio funcional com números.",
    },
    BAND_INTERMEDIATE: {
        "transcript": (
            "Então, sobre a reunião de amanhã: eu adiantei o horário porque a sala "
            "só estava livre de manhã. Avisei o time por mensagem, mas se alguém não "
            "puder, a gente remarca sem problema."
        ),
        "speaking_rate": "natural, com hesitações",
        "note": "Fala espontânea de trabalho.",
    },
    BAND_UPPER: {
        "transcript": (
            "O que mais me chamou atenção no relatório não foi o número em si, mas a "
            "forma como ele foi apresentado. Quando você agrega tudo num único "
            "indicador, você esconde exatamente a variação que interessa — e aí a "
            "discussão vira sobre a média, não sobre quem está fora dela."
        ),
        "speaking_rate": "rápida, natural, com encadeamento",
        "note": "Opinião analítica em velocidade real.",
    },
}

PRONUNCIATION_FOCUS: dict[str, list[dict[str, str]]] = {
    "en": [
        {"sound": "th (/θ/ e /ð/)", "why_hard": "Não existe em português; costuma virar 't', 'd', 'f' ou 's'.", "how_to_produce": "Ponta da língua entre os dentes, sopro leve. Em 'the' há vibração; em 'think' não há."},
        {"sound": "/ɪ/ curto × /iː/ longo", "why_hard": "Português tem só um 'i'; 'ship' e 'sheep' viram a mesma palavra.", "how_to_produce": "Para /ɪ/, relaxe a língua e encurte. Para /iː/, estique os lábios e alongue."},
        {"sound": "/h/ inicial", "why_hard": "Em português o 'h' é mudo, então 'house' perde o sopro.", "how_to_produce": "Sopro audível antes da vogal, como quem embaça um vidro."},
    ],
    "es-ES": [
        {"sound": "/θ/ (c/z na Espanha)", "why_hard": "Falantes de português tendem a produzir 's'.", "how_to_produce": "Língua entre os dentes, como o 'th' de 'think'. 'Cinco' soa 'zinco'."},
        {"sound": "'rr' vibrante múltiplo", "why_hard": "O 'r' do português brasileiro costuma ser gutural.", "how_to_produce": "Ponta da língua vibrando atrás dos dentes superiores, sem usar a garganta."},
        {"sound": "vogais puras", "why_hard": "O português nasaliza e reduz vogais átonas; o espanhol não.", "how_to_produce": "Mantenha as cinco vogais abertas e estáveis, sem nasalizar."},
    ],
    "fr": [
        {"sound": "/y/ (u de 'tu')", "why_hard": "Não existe em português; vira 'u' comum.", "how_to_produce": "Diga 'i' e, sem mover a língua, arredonde os lábios."},
        {"sound": "vogais nasais", "why_hard": "Parecem as do português, mas os pontos são diferentes.", "how_to_produce": "Contraste 'an', 'on' e 'in' isoladamente antes de usar em palavras."},
        {"sound": "'r' uvular", "why_hard": "Diferente do 'r' brasileiro em posição inicial.", "how_to_produce": "Vibração no fundo da boca, próxima ao gargarejo leve."},
    ],
    "ja": [
        {"sound": "vogal longa × curta", "why_hard": "Muda o significado; o português não usa duração assim.", "how_to_produce": "Sustente a vogal por dois tempos: 'obasan' (tia) × 'obaasan' (avó)."},
        {"sound": "り (ri)", "why_hard": "Fica entre 'r' e 'l' e não corresponde a nenhum som do português.", "how_to_produce": "Toque rápido da ponta da língua no céu da boca, como o 'r' de 'caro'."},
        {"sound": "つ (tsu)", "why_hard": "O encontro 'ts' não inicia sílaba em português.", "how_to_produce": "Comece pelo 't' e solte imediatamente no 's', sem vogal no meio."},
    ],
    "zh-CN": [
        {"sound": "os quatro tons", "why_hard": "O português usa entonação para emoção, não para significado.", "how_to_produce": "Treine 'mā, má, mǎ, mà' isoladamente até distinguir de ouvido."},
        {"sound": "q, x, j", "why_hard": "Não têm equivalente direto; costumam virar 'tch', 'ch' e 'dj'.", "how_to_produce": "Língua baixa atrás dos dentes inferiores, som formado no palato duro."},
        {"sound": "zh, ch, sh, r retroflexos", "why_hard": "Exigem língua curvada para trás, movimento ausente no português.", "how_to_produce": "Ponta da língua enrolada em direção ao céu da boca."},
    ],
}
