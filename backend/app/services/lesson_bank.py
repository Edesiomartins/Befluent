"""Conteúdo de lição usado quando não há provedor de IA configurado.

Por que existe: `AI_MOCK_MODE=true` é o padrão do projeto e o estado atual da
produção. Sem este módulo, o modo mock devolveria a mesma frase para todo mundo
e o teste de nivelamento continuaria sem efeito prático — que é exatamente o
problema que esta integração resolve. Aqui o conteúdo varia por faixa de nível.

Cobertura: todas as combinações idioma × habilidade × faixa devolvem conteúdo —
`coverage_report()` verifica isso e um teste falha se abrir uma lacuna. Sem essa
garantia, um bloco do cronograma em japonês abriria vazio no modo mock, que é o
modo padrão do projeto.

LIMITAÇÃO DECLARADA: banco inicial de desenvolvimento, escrito para validar o
fluxo técnico de ponta a ponta. Não passou por validação pedagógica nem por
revisão de falante nativo. A faixa UPPER (B2) do inglês foi expandida com
etiquetas de tema semanal para permitir subconjuntos diários (ver
`vocabulary_selection.py`); ainda não substitui material didático certificado.
Com uma chave OpenRouter configurada, `ai.py` gera conteúdo por prompt e este
banco passa a ser apenas fallback.
"""

from __future__ import annotations

from app.core.levels import LEVEL_INDEX, CEFRLevel


def _vocab_item(
    term: str,
    translation: str,
    example: str,
    example_translation: str,
    usage_note: str,
    themes: list[str] | None = None,
) -> dict:
    item = {
        "term": term,
        "translation": translation,
        "example": example,
        "example_translation": example_translation,
        "usage_note": usage_note,
    }
    if themes:
        item["themes"] = list(themes)
    return item

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
            # Argumentar e refutar
            _vocab_item("to bring about", "provocar, ocasionar", "The policy brought about significant change.", "A política provocou mudanças significativas.", "Registro formal, comum em textos analíticos.", ["Argumentar e refutar", "Sociedade e políticas públicas"]),
            _vocab_item("to call into question", "colocar em xeque", "The report calls into question the official figures.", "O relatório coloca as cifras oficiais em xeque.", "Útil para refutar com evidência.", ["Argumentar e refutar"]),
            _vocab_item("to hold that", "sustentar que", "Many experts hold that the reform is overdue.", "Muitos especialistas sustentam que a reforma está atrasada.", "Introduz posição argumentativa.", ["Argumentar e refutar", "Apresentar e defender uma ideia"]),
            _vocab_item("on the contrary", "pelo contrário", "On the contrary, the data suggest the opposite.", "Pelo contrário, os dados sugerem o oposto.", "Contraste forte em debate.", ["Argumentar e refutar"]),
            _vocab_item("to concede that", "admitir que", "I concede that the first draft was weak.", "Admito que o primeiro rascunho era fraco.", "Concede um ponto sem abandonar a tese.", ["Argumentar e refutar"]),
            _vocab_item("a compelling argument", "um argumento convincente", "She made a compelling argument for transparency.", "Ela apresentou um argumento convincente a favor da transparência.", "Avalia força retórica.", ["Argumentar e refutar", "Apresentar e defender uma ideia"]),
            _vocab_item("to rebut", "refutar", "He rebutted the claim with three case studies.", "Ele refutou a alegação com três estudos de caso.", "Mais formal que 'disagree'.", ["Argumentar e refutar"]),
            _vocab_item("for the sake of argument", "para fins de discussão", "For the sake of argument, assume costs stay flat.", "Para fins de discussão, assume que os custos ficam estáveis.", "Hipotético em debate.", ["Argumentar e refutar"]),
            # Negociação e mercado de trabalho
            _vocab_item("to bargain for", "negociar / contar com", "We didn't bargain for such a long delay.", "Não contávamos com um atraso tão longo.", "Dois sentidos: barganhar ou esperar.", ["Negociação e mercado de trabalho"]),
            _vocab_item("leverage", "alavancagem; influência", "They used market data as leverage in talks.", "Usaram dados de mercado como alavancagem nas conversas.", "Comum em negócios.", ["Negociação e mercado de trabalho"]),
            _vocab_item("to meet halfway", "chegar a um meio-termo", "Both sides agreed to meet halfway on the fee.", "Os dois lados concordaram em um meio-termo na taxa.", "Negociação cooperativa.", ["Negociação e mercado de trabalho"]),
            _vocab_item("a sticking point", "ponto de atrito", "Remote work remains a sticking point.", "O trabalho remoto continua sendo um ponto de atrito.", "Obstáculo em acordo.", ["Negociação e mercado de trabalho"]),
            _vocab_item("to turn down", "recusar", "She turned down the offer after reviewing the contract.", "Ela recusou a oferta após revisar o contrato.", "Recusa consciente.", ["Negociação e mercado de trabalho"]),
            _vocab_item("to back up", "apoiar; fazer backup", "Can you back up that claim with figures?", "Você pode apoiar essa alegação com números?", "Em debate = sustentar com prova.", ["Negociação e mercado de trabalho", "Argumentar e refutar"]),
            _vocab_item("in good faith", "de boa-fé", "They negotiated in good faith for weeks.", "Eles negociaram de boa-fé por semanas.", "Registro jurídico/negociável.", ["Negociação e mercado de trabalho"]),
            _vocab_item("to settle for", "aceitar (menos do que queria)", "We may have to settle for a smaller raise.", "Talvez tenhamos de aceitar um aumento menor.", "Compromisso.", ["Negociação e mercado de trabalho"]),
            # Ciência, dados e evidência
            _vocab_item("to account for", "explicar, corresponder a", "This accounts for most of the delay.", "Isso explica a maior parte do atraso.", "Justificar ou representar proporção.", ["Ciência, dados e evidência", "Argumentar e refutar"]),
            _vocab_item("to bear out", "confirmar (dados)", "The trial results bear out the hypothesis.", "Os resultados do ensaio confirmam a hipótese.", "Evidência apoia tese.", ["Ciência, dados e evidência"]),
            _vocab_item("a confounding factor", "fator de confusão", "Age was a confounding factor in the study.", "A idade foi um fator de confusão no estudo.", "Vocabulário de pesquisa.", ["Ciência, dados e evidência"]),
            _vocab_item("to extrapolate", "extrapolar", "We shouldn't extrapolate from such a small sample.", "Não devemos extrapolar a partir de uma amostra tão pequena.", "Cuidado metodológico.", ["Ciência, dados e evidência"]),
            _vocab_item("peer-reviewed", "revisado por pares", "Only peer-reviewed sources were cited.", "Só foram citadas fontes revisadas por pares.", "Credibilidade acadêmica.", ["Ciência, dados e evidência", "Mídia, fontes e desinformação"]),
            _vocab_item("statistically significant", "estatisticamente significativo", "The difference was statistically significant.", "A diferença foi estatisticamente significativa.", "Não confundir com 'importante'.", ["Ciência, dados e evidência"]),
            _vocab_item("to control for", "controlar (variável)", "The model controls for income and education.", "O modelo controla renda e educação.", "Método quantitativo.", ["Ciência, dados e evidência"]),
            _vocab_item("an outlier", "ponto fora da curva", "One outlier skewed the average.", "Um outlier distorceu a média.", "Análise de dados.", ["Ciência, dados e evidência"]),
            # Mídia, fontes e desinformação
            _vocab_item("to fact-check", "checar fatos", "Journalists fact-checked the viral post.", "Jornalistas checaram os fatos do post viral.", "Hábito midiático.", ["Mídia, fontes e desinformação"]),
            _vocab_item("clickbait", "isca de cliques", "The headline was pure clickbait.", "A manchete era pura isca de cliques.", "Crítica de mídia.", ["Mídia, fontes e desinformação"]),
            _vocab_item("to go viral", "viralizar", "The clip went viral within hours.", "O clipe viralizou em poucas horas.", "Dinâmica de redes.", ["Mídia, fontes e desinformação"]),
            _vocab_item("a primary source", "fonte primária", "Always prefer a primary source when possible.", "Prefira sempre uma fonte primária quando possível.", "Letramento informacional.", ["Mídia, fontes e desinformação", "Ciência, dados e evidência"]),
            _vocab_item("to take with a grain of salt", "receber com ceticismo", "Take anonymous tips with a grain of salt.", "Receba denúncias anônimas com ceticismo.", "Idiomático e útil.", ["Mídia, fontes e desinformação"]),
            _vocab_item("echo chamber", "bolha de eco", "Social feeds can become an echo chamber.", "Os feeds podem virar uma bolha de eco.", "Crítica de polarização.", ["Mídia, fontes e desinformação", "Mudanças sociais e gerações"]),
            _vocab_item("to verify", "verificar", "Verify the date before sharing.", "Verifique a data antes de compartilhar.", "Ação concreta anti-desinformação.", ["Mídia, fontes e desinformação"]),
            _vocab_item("biased coverage", "cobertura enviesada", "The channel was accused of biased coverage.", "O canal foi acusado de cobertura enviesada.", "Avaliação crítica.", ["Mídia, fontes e desinformação"]),
            # Sociedade e políticas públicas
            _vocab_item("notwithstanding", "apesar de", "Notwithstanding the risks, they moved forward.", "Apesar dos riscos, eles seguiram em frente.", "Formal; em fala prefira 'despite'.", ["Sociedade e políticas públicas", "Argumentar e refutar"]),
            _vocab_item("public interest", "interesse público", "The inquiry was held in the public interest.", "A investigação foi feita no interesse público.", "Discurso cívico.", ["Sociedade e políticas públicas"]),
            _vocab_item("to roll out", "implementar gradualmente", "The city will roll out the new fare system.", "A cidade implementará gradualmente o novo sistema de tarifas.", "Políticas e produtos.", ["Sociedade e políticas públicas", "Economia pessoal e global"]),
            _vocab_item("a safety net", "rede de proteção", "Unemployment benefits are a basic safety net.", "O seguro-desemprego é uma rede de proteção básica.", "Política social.", ["Sociedade e políticas públicas"]),
            _vocab_item("to crack down on", "reprimir com rigor", "Authorities cracked down on tax evasion.", "As autoridades reprimiram a evasão fiscal.", "Ação estatal.", ["Sociedade e políticas públicas"]),
            _vocab_item("grassroots", "de base (movimento)", "It started as a grassroots campaign.", "Começou como uma campanha de base.", "Mobilização social.", ["Sociedade e políticas públicas", "Mudanças sociais e gerações"]),
            _vocab_item("to phase out", "eliminar gradualmente", "They plan to phase out single-use plastics.", "Planejam eliminar gradualmente os plásticos de uso único.", "Transição de política.", ["Sociedade e políticas públicas"]),
            _vocab_item("red tape", "burocracia", "Small firms struggle with red tape.", "Pequenas empresas sofrem com a burocracia.", "Crítica administrativa.", ["Sociedade e políticas públicas", "Negociação e mercado de trabalho"]),
            # Ética e dilemas
            _vocab_item("to be inclined to", "tender a", "I'm inclined to agree with that view.", "Tendo a concordar com essa visão.", "Suaviza opinião.", ["Ética e dilemas", "Argumentar e refutar"]),
            _vocab_item("a trade-off", "trade-off, troca", "There is a trade-off between privacy and convenience.", "Há um trade-off entre privacidade e conveniência.", "Dilema típico.", ["Ética e dilemas", "Ciência, dados e evidência"]),
            _vocab_item("to draw the line", "estabelecer um limite", "Where do we draw the line on surveillance?", "Onde estabelecemos o limite da vigilância?", "Limite ético.", ["Ética e dilemas"]),
            _vocab_item("unintended consequences", "consequências não intencionais", "The ban had unintended consequences.", "A proibição teve consequências não intencionais.", "Análise ética de política.", ["Ética e dilemas", "Sociedade e políticas públicas"]),
            _vocab_item("to turn a blind eye", "fazer vista grossa", "Managers turned a blind eye to the risk.", "Gestores fizeram vista grossa ao risco.", "Omissão ética.", ["Ética e dilemas"]),
            _vocab_item("informed consent", "consentimento informado", "Patients must give informed consent.", "Pacientes devem dar consentimento informado.", "Ética profissional.", ["Ética e dilemas"]),
            _vocab_item("to outweigh", "superar (em peso/importância)", "The benefits outweigh the costs.", "Os benefícios superam os custos.", "Balanço moral/prático.", ["Ética e dilemas", "Argumentar e refutar"]),
            _vocab_item("a slippery slope", "ladeira escorregadia", "Critics warn of a slippery slope.", "Críticos alertam para uma ladeira escorregadia.", "Argumento clássico.", ["Ética e dilemas", "Argumentar e refutar"]),
            # Economia pessoal e global
            _vocab_item("for the time being", "por ora", "For the time being, we'll keep the current process.", "Por ora, manteremos o processo atual.", "Decisão provisória.", ["Economia pessoal e global", "Negociação e mercado de trabalho"]),
            _vocab_item("to hedge against", "proteger-se contra", "Investors hedge against currency swings.", "Investidores se protegem contra oscilações cambiais.", "Finanças.", ["Economia pessoal e global"]),
            _vocab_item("purchasing power", "poder de compra", "Inflation erodes purchasing power.", "A inflação corrói o poder de compra.", "Macro/pessoal.", ["Economia pessoal e global"]),
            _vocab_item("to break even", "empatar custos/receita", "The shop hopes to break even this year.", "A loja espera empatar custos e receita este ano.", "Negócios.", ["Economia pessoal e global"]),
            _vocab_item("a downturn", "queda, retração", "The downturn hit small exporters hardest.", "A retração atingiu mais os pequenos exportadores.", "Ciclo econômico.", ["Economia pessoal e global"]),
            _vocab_item("to cut back on", "reduzir (gastos)", "Households cut back on dining out.", "As famílias reduziram refeições fora.", "Economia pessoal.", ["Economia pessoal e global"]),
            _vocab_item("supply chain", "cadeia de suprimentos", "Storms disrupted the supply chain.", "Tempestades atrapalharam a cadeia de suprimentos.", "Economia global.", ["Economia pessoal e global"]),
            _vocab_item("to write off", "dar como prejuízo; descartar", "The bank wrote off the bad loan.", "O banco deu o empréstimo ruim como prejuízo.", "Contábil/metafórico.", ["Economia pessoal e global"]),
            # Arte, crítica e interpretação
            _vocab_item("by and large", "de modo geral", "By and large, the results were positive.", "De modo geral, os resultados foram positivos.", "Generaliza com exceções.", ["Arte, crítica e interpretação", "Argumentar e refutar"]),
            _vocab_item("to convey", "transmitir (ideia/emoção)", "The film conveys quiet grief.", "O filme transmite um luto silencioso.", "Crítica cultural.", ["Arte, crítica e interpretação"]),
            _vocab_item("a nuanced reading", "leitura nuançada", "She offers a nuanced reading of the novel.", "Ela oferece uma leitura nuançada do romance.", "Interpretação.", ["Arte, crítica e interpretação"]),
            _vocab_item("to fall flat", "fracassar / não funcionar", "The joke fell flat with the audience.", "A piada não funcionou com a plateia.", "Recepção.", ["Arte, crítica e interpretação"]),
            _vocab_item("to resonate with", "fazer sentido / ecoar em", "The speech resonated with younger voters.", "O discurso ecoou nos eleitores mais jovens.", "Impacto.", ["Arte, crítica e interpretação", "Mudanças sociais e gerações"]),
            _vocab_item("derivative", "derivativo, pouco original", "Critics called the plot derivative.", "Críticos chamaram o enredo de pouco original.", "Juízo estético.", ["Arte, crítica e interpretação"]),
            _vocab_item("to shed light on", "lançar luz sobre", "The essay sheds light on colonial memory.", "O ensaio lança luz sobre a memória colonial.", "Análise.", ["Arte, crítica e interpretação", "Ciência, dados e evidência"]),
            _vocab_item("understated", "discreto, contido", "The performance was powerful yet understated.", "A atuação foi poderosa e ainda assim contida.", "Estilo.", ["Arte, crítica e interpretação"]),
            # Mudanças sociais e gerações
            _vocab_item("a generational shift", "mudança geracional", "Remote work marks a generational shift.", "O trabalho remoto marca uma mudança geracional.", "Sociedade.", ["Mudanças sociais e gerações"]),
            _vocab_item("to come of age", "atingir a maioridade; amadurecer", "The movement came of age online.", "O movimento amadureceu online.", "Metáfora social.", ["Mudanças sociais e gerações"]),
            _vocab_item("out of touch", "desconectado (da realidade)", "The ad felt out of touch with Gen Z.", "O anúncio parecia desconectado da Gen Z.", "Crítica geracional.", ["Mudanças sociais e gerações", "Mídia, fontes e desinformação"]),
            _vocab_item("to bridge the gap", "estreitar a lacuna", "Mentoring can bridge the gap between cohorts.", "Mentoria pode estreitar a lacuna entre coortes.", "Inclusão.", ["Mudanças sociais e gerações"]),
            _vocab_item("social mobility", "mobilidade social", "Education still shapes social mobility.", "A educação ainda molda a mobilidade social.", "Tema estrutural.", ["Mudanças sociais e gerações", "Sociedade e políticas públicas"]),
            _vocab_item("to push back against", "resistir a", "Workers pushed back against longer hours.", "Trabalhadores resistiram a jornadas maiores.", "Agência coletiva.", ["Mudanças sociais e gerações", "Negociação e mercado de trabalho"]),
            _vocab_item("the status quo", "o status quo", "Few want to defend the status quo.", "Poucos querem defender o status quo.", "Mudança vs permanência.", ["Mudanças sociais e gerações", "Ética e dilemas"]),
            _vocab_item("to catch on", "pegar (moda/ideia)", "The habit caught on among students.", "O hábito pegou entre estudantes.", "Difusão cultural.", ["Mudanças sociais e gerações"]),
            # Apresentar e defender uma ideia
            _vocab_item("to put forward", "apresentar (proposta)", "She put forward a clearer framework.", "Ela apresentou um quadro mais claro.", "Proposta formal.", ["Apresentar e defender uma ideia"]),
            _vocab_item("to spell out", "deixar explícito", "Please spell out the assumptions.", "Por favor, deixe as premissas explícitas.", "Clareza.", ["Apresentar e defender uma ideia"]),
            _vocab_item("to stand by", "manter (posição)", "I stand by my earlier conclusion.", "Mantenho minha conclusão anterior.", "Defesa.", ["Apresentar e defender uma ideia", "Argumentar e refutar"]),
            _vocab_item("a working hypothesis", "hipótese de trabalho", "Treat this as a working hypothesis.", "Trate isto como hipótese de trabalho.", "Provisório e científico.", ["Apresentar e defender uma ideia", "Ciência, dados e evidência"]),
            _vocab_item("to boil down to", "resumir-se a", "The dispute boils down to funding.", "A disputa se resume a financiamento.", "Síntese.", ["Apresentar e defender uma ideia"]),
            _vocab_item("in a nutshell", "em síntese", "In a nutshell, we need clearer rules.", "Em síntese, precisamos de regras mais claras.", "Fechamento oral.", ["Apresentar e defender uma ideia"]),
            _vocab_item("to flesh out", "detalhar, desenvolver", "Can you flesh out the second point?", "Você pode detalhar o segundo ponto?", "Desenvolvimento de ideia.", ["Apresentar e defender uma ideia"]),
            _vocab_item("the crux of the matter", "o cerne da questão", "The crux of the matter is trust.", "O cerne da questão é a confiança.", "Foco argumentativo.", ["Apresentar e defender uma ideia", "Argumentar e refutar"]),
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

#: Textos de leitura POR IDIOMA. Antes eram só por faixa e vinham em português —
#: uma "leitura em inglês" servia um texto em português, o que não treina
#: leitura nenhuma. Cada célula idioma×faixa tem texto no idioma-alvo.
READING_TEXTS: dict[str, dict[str, dict[str, object]]] = {
    "en": {
        BAND_BEGINNER: {
            "title": "An ordinary morning",
            "text": (
                "Ana wakes up at seven o'clock. She has breakfast with her family. "
                "Then she goes to work by bus. The trip takes thirty minutes. "
                "Ana likes to read on the bus."
            ),
            "note": "Frases curtas, vocabulário de rotina.",
        },
        BAND_ELEMENTARY: {
            "title": "Moving to a new city",
            "text": (
                "Last year, Pedro moved to another city because of his job. At first it "
                "was hard: he did not know anyone and he missed his friends. Little by "
                "little, he made new friends in the neighbourhood. Today he says the "
                "move was a good decision, despite the difficult beginning."
            ),
            "note": "Passado simples, conectores, causa e consequência.",
        },
        BAND_INTERMEDIATE: {
            "title": "How flexible work changed daily routines",
            "text": (
                "For many professionals, flexible work changed more than the place "
                "where tasks are done. It also changed how people organise their "
                "attention, talk to colleagues and separate work from personal life. "
                "Some value the autonomy; others miss the spontaneous conversations of "
                "the office. Research suggests that the most effective arrangements "
                "depend less on a fixed model and more on clear expectations."
            ),
            "note": "Texto expositivo, contraste de pontos de vista.",
        },
        BAND_UPPER: {
            "title": "Automation and the value of human work",
            "text": (
                "The debate about automation tends to swing between two equally "
                "unlikely extremes: the widespread disappearance of jobs and the "
                "spontaneous creation of better ones. The available evidence points to "
                "a less dramatic and more uncomfortable scenario — the uneven "
                "recomposition of tasks within existing occupations. Not every role is "
                "replaced; many are hollowed out from the inside, losing precisely the "
                "activities that gave autonomy to the people doing them."
            ),
            "note": "Argumentação densa, nuance e ressalva.",
        },
    },
    "es-ES": {
        BAND_BEGINNER: {
            "title": "Una mañana normal",
            "text": (
                "Ana se levanta a las siete. Desayuna con su familia. Después va al "
                "trabajo en autobús. El trayecto dura treinta minutos. A Ana le gusta "
                "leer durante el viaje."
            ),
            "note": "Frases curtas, presente e rotina.",
        },
        BAND_ELEMENTARY: {
            "title": "Mudarse de ciudad",
            "text": (
                "El año pasado, Pedro se mudó a otra ciudad por el trabajo. Al "
                "principio fue difícil: no conocía a nadie y echaba de menos a sus "
                "amigos. Poco a poco hizo nuevas amistades en el barrio. Hoy dice que "
                "la mudanza fue una buena decisión."
            ),
            "note": "Indefinido × imperfecto, conectores simples.",
        },
        BAND_INTERMEDIATE: {
            "title": "Cómo el trabajo flexible cambió las rutinas",
            "text": (
                "Para muchos profesionales, el trabajo flexible cambió más que el "
                "lugar donde se hacen las tareas. También cambió la forma de organizar "
                "la atención, de hablar con los compañeros y de separar el trabajo de "
                "la vida personal. Algunos valoran la autonomía; otros echan de menos "
                "las conversaciones espontáneas de la oficina. Los estudios sugieren "
                "que los acuerdos más eficaces dependen menos de un modelo fijo y más "
                "de expectativas claras."
            ),
            "note": "Texto expositivo peninsular.",
        },
        BAND_UPPER: {
            "title": "La automatización y el valor del trabajo humano",
            "text": (
                "El debate sobre la automatización suele oscilar entre dos extremos "
                "igualmente improbables: la desaparición generalizada del empleo y la "
                "creación espontánea de ocupaciones mejores. La evidencia disponible "
                "apunta a un escenario menos dramático y más incómodo: la "
                "recomposición desigual de las tareas dentro de las profesiones "
                "existentes. No toda función se sustituye; muchas se vacían por dentro "
                "y pierden justamente las actividades que daban autonomía a quien las "
                "ejercía."
            ),
            "note": "Argumentação com ressalva, registro formal.",
        },
    },
    "fr": {
        BAND_BEGINNER: {
            "title": "Une matinée ordinaire",
            "text": (
                "Ana se lève à sept heures. Elle prend le petit-déjeuner avec sa "
                "famille. Ensuite, elle va au travail en bus. Le trajet dure trente "
                "minutes. Ana aime lire pendant le voyage."
            ),
            "note": "Presente, rotina, frases curtas.",
        },
        BAND_ELEMENTARY: {
            "title": "Déménager dans une autre ville",
            "text": (
                "L'année dernière, Pedro a déménagé dans une autre ville pour son "
                "travail. Au début, c'était difficile : il ne connaissait personne et "
                "ses amis lui manquaient. Peu à peu, il s'est fait de nouveaux amis "
                "dans le quartier. Aujourd'hui, il dit que ce déménagement était une "
                "bonne décision."
            ),
            "note": "Passé composé × imparfait.",
        },
        BAND_INTERMEDIATE: {
            "title": "Comment le travail flexible a changé les routines",
            "text": (
                "Pour beaucoup de professionnels, le travail flexible a changé plus "
                "que le lieu où les tâches sont faites. Il a aussi changé la façon "
                "dont les gens organisent leur attention, parlent à leurs collègues et "
                "séparent le travail de la vie personnelle. Certains apprécient "
                "l'autonomie ; d'autres regrettent les conversations spontanées du "
                "bureau. Les études suggèrent que les arrangements les plus efficaces "
                "dépendent moins d'un modèle fixe que d'attentes claires."
            ),
            "note": "Texto expositivo, contraste de posições.",
        },
        BAND_UPPER: {
            "title": "L'automatisation et la valeur du travail humain",
            "text": (
                "Le débat sur l'automatisation oscille souvent entre deux extrêmes "
                "également improbables : la disparition généralisée de l'emploi et la "
                "création spontanée de meilleurs métiers. Les données disponibles "
                "indiquent un scénario moins dramatique et plus inconfortable : la "
                "recomposition inégale des tâches à l'intérieur des professions "
                "existantes. Toutes les fonctions ne sont pas remplacées ; beaucoup se "
                "vident de l'intérieur et perdent précisément les activités qui "
                "donnaient de l'autonomie à ceux qui les exerçaient."
            ),
            "note": "Registro formal, concessão e nuance.",
        },
    },
    "ja": {
        BAND_BEGINNER: {
            "title": "ふつうの朝（あさ）",
            "text": (
                "アナさんは七時（しちじ）に起（お）きます。家族（かぞく）と朝（あさ）ごはんを食（た）べます。"
                "それからバスで会社（かいしゃ）に行（い）きます。バスは三十分（さんじゅっぷん）かかります。"
                "アナさんはバスの中（なか）で本（ほん）を読（よ）みます。"
            ),
            "note": "Frases curtas com furigana; leitura desde o início.",
        },
        BAND_ELEMENTARY: {
            "title": "引（ひ）っ越（こ）し",
            "text": (
                "去年（きょねん）、ペドロさんは仕事（しごと）のために別（べつ）の町（まち）に引（ひ）っ越（こ）しました。"
                "最初（さいしょ）は大変（たいへん）でした。知（し）っている人（ひと）がいなくて、"
                "友達（ともだち）に会（あ）いたかったからです。少（すこ）しずつ近所（きんじょ）で"
                "新（あたら）しい友達（ともだち）ができました。今（いま）は、引（ひ）っ越（こ）して"
                "よかったと言（い）っています。"
            ),
            "note": "Passado em ました, conectores simples.",
        },
        BAND_INTERMEDIATE: {
            "title": "柔軟（じゅうなん）な働（はたら）き方（かた）",
            "text": (
                "多（おお）くの働（はたら）く人（ひと）にとって、柔軟（じゅうなん）な働（はたら）き方（かた）は"
                "場所（ばしょ）だけを変（か）えたのではありません。集中（しゅうちゅう）の仕方（しかた）や、"
                "同僚（どうりょう）との話（はな）し方（かた）、仕事（しごと）と私生活（しせいかつ）の"
                "区別（くべつ）も変（か）わりました。自由（じゆう）を歓迎（かんげい）する人（ひと）もいれば、"
                "職場（しょくば）の自然（しぜん）な会話（かいわ）が恋（こい）しい人（ひと）もいます。"
            ),
            "note": "Texto expositivo com kanji de uso frequente.",
        },
        BAND_UPPER: {
            "title": "自動化（じどうか）と人間（にんげん）の仕事（しごと）",
            "text": (
                "自動化（じどうか）をめぐる議論（ぎろん）は、極端（きょくたん）な二（ふた）つの"
                "見方（みかた）の間（あいだ）で揺（ゆ）れがちです。仕事（しごと）が広（ひろ）く"
                "消（き）えるという見方（みかた）と、より良（よ）い職業（しょくぎょう）が"
                "自然（しぜん）に生（う）まれるという見方（みかた）です。実際（じっさい）のデータが"
                "示（しめ）すのは、もっと地味（じみ）で厄介（やっかい）な状況（じょうきょう）、"
                "つまり既存（きそん）の職業（しょくぎょう）の中（なか）で業務（ぎょうむ）が"
                "不均等（ふきんとう）に組（く）み替（か）えられることです。"
            ),
            "note": "Registro escrito, estruturas de concessão.",
        },
    },
    "zh-CN": {
        BAND_BEGINNER: {
            "title": "普通的早晨",
            "text": (
                "安娜七点起床。她和家人一起吃早饭。然后她坐公交车去上班。"
                "路上要三十分钟。安娜喜欢在车上看书。"
            ),
            "note": "Pinyin: Ānnà qī diǎn qǐchuáng… Frases curtas, hanzi de alta frequência.",
        },
        BAND_ELEMENTARY: {
            "title": "搬到另一个城市",
            "text": (
                "去年，彼得因为工作搬到了另一个城市。刚开始很难：他谁也不认识，"
                "也很想念朋友。慢慢地，他在小区里交了新朋友。"
                "现在他说，搬家是一个好决定。"
            ),
            "note": "Partícula 了 e marcadores de tempo.",
        },
        BAND_INTERMEDIATE: {
            "title": "灵活办公如何改变日常",
            "text": (
                "对很多职场人来说，灵活办公改变的不只是工作的地点。"
                "它也改变了人们安排注意力、跟同事沟通以及区分工作与生活的方式。"
                "有人喜欢这种自主，也有人怀念办公室里自然发生的对话。"
                "研究表明，最有效的安排更多取决于清晰的预期，而不是固定的模式。"
            ),
            "note": "Texto expositivo, conectores de contraste.",
        },
        BAND_UPPER: {
            "title": "自动化与人的劳动价值",
            "text": (
                "关于自动化的讨论常常在两个同样不太可能的极端之间摇摆："
                "工作大规模消失，或者更好的职业自动出现。"
                "现有证据指向一个不那么戏剧化、却更令人不安的情形："
                "现有职业内部的任务被不均衡地重新组合。"
                "并非每个岗位都会被取代；许多岗位是从内部被掏空的，"
                "失去的恰恰是让从业者拥有自主性的那些活动。"
            ),
            "note": "Registro formal escrito, expressões de quatro caracteres.",
        },
    },
}

#: Roteiros de escuta POR IDIOMA, mesma razão dos textos de leitura.
LISTENING_SCRIPTS: dict[str, dict[str, dict[str, object]]] = {
    "en": {
        BAND_BEGINNER: {
            "transcript": "Good morning. My name is Carlos. I am a teacher. Nice to meet you.",
            "speaking_rate": "lenta, com pausas entre as frases",
            "note": "Apresentação pessoal simples.",
        },
        BAND_ELEMENTARY: {
            "transcript": (
                "Attention, passengers. Flight 482 to Madrid is delayed by thirty "
                "minutes. Boarding will begin at gate sixteen."
            ),
            "speaking_rate": "moderada, típica de anúncio público",
            "note": "Anúncio funcional com números.",
        },
        BAND_INTERMEDIATE: {
            "transcript": (
                "So, about tomorrow's meeting — I moved it earlier because the room "
                "was only free in the morning. I told the team by message, but if "
                "anyone can't make it, we can reschedule, no problem."
            ),
            "speaking_rate": "natural, com hesitações",
            "note": "Fala espontânea de trabalho.",
        },
        BAND_UPPER: {
            "transcript": (
                "What struck me in the report wasn't the number itself, but the way it "
                "was presented. When you aggregate everything into a single indicator, "
                "you hide exactly the variation that matters — and then the discussion "
                "becomes about the average, not about who falls outside it."
            ),
            "speaking_rate": "rápida, natural, com encadeamento",
            "note": "Opinião analítica em velocidade real.",
        },
    },
    "es-ES": {
        BAND_BEGINNER: {
            "transcript": "Buenos días. Me llamo Carlos. Soy profesor. Encantado.",
            "speaking_rate": "lenta, com pausas entre as frases",
            "note": "Apresentação pessoal simples.",
        },
        BAND_ELEMENTARY: {
            "transcript": (
                "Atención, pasajeros. El vuelo 482 con destino a Madrid lleva treinta "
                "minutos de retraso. El embarque comenzará en la puerta dieciséis."
            ),
            "speaking_rate": "moderada, típica de anúncio público",
            "note": "Anúncio funcional com números.",
        },
        BAND_INTERMEDIATE: {
            "transcript": (
                "Bueno, sobre la reunión de mañana: la he adelantado porque la sala "
                "solo estaba libre por la mañana. Se lo he dicho al equipo por "
                "mensaje, pero si alguien no puede, la cambiamos sin problema."
            ),
            "speaking_rate": "natural, com hesitações",
            "note": "Fala espontânea de trabalho (variante peninsular).",
        },
        BAND_UPPER: {
            "transcript": (
                "Lo que más me llamó la atención del informe no fue el número en sí, "
                "sino cómo se presentó. Cuando lo agregas todo en un único indicador, "
                "escondes justamente la variación que importa, y entonces la discusión "
                "pasa a ser sobre la media y no sobre quien queda fuera de ella."
            ),
            "speaking_rate": "rápida, natural, com encadeamento",
            "note": "Opinião analítica em velocidade real.",
        },
    },
    "fr": {
        BAND_BEGINNER: {
            "transcript": "Bonjour. Je m'appelle Carlos. Je suis professeur. Enchanté.",
            "speaking_rate": "lenta, com pausas entre as frases",
            "note": "Apresentação pessoal simples.",
        },
        BAND_ELEMENTARY: {
            "transcript": (
                "Attention, mesdames et messieurs. Le vol 482 à destination de Madrid "
                "a trente minutes de retard. L'embarquement se fera porte seize."
            ),
            "speaking_rate": "moderada, típica de anúncio público",
            "note": "Anúncio funcional com números.",
        },
        BAND_INTERMEDIATE: {
            "transcript": (
                "Alors, pour la réunion de demain : je l'ai avancée parce que la salle "
                "n'était libre que le matin. J'ai prévenu l'équipe par message, mais "
                "si quelqu'un ne peut pas, on la déplace sans problème."
            ),
            "speaking_rate": "natural, com liaison e hesitações",
            "note": "Fala espontânea de trabalho.",
        },
        BAND_UPPER: {
            "transcript": (
                "Ce qui m'a le plus frappé dans le rapport, ce n'est pas le chiffre "
                "lui-même, mais la façon dont il a été présenté. Quand on agrège tout "
                "dans un seul indicateur, on cache justement la variation qui compte — "
                "et la discussion porte alors sur la moyenne, pas sur ceux qui en sortent."
            ),
            "speaking_rate": "rápida, natural, com encadeamento",
            "note": "Opinião analítica em velocidade real.",
        },
    },
    "ja": {
        BAND_BEGINNER: {
            "transcript": "おはようございます。カルロスです。教師（きょうし）です。よろしくお願（ねが）いします。",
            "speaking_rate": "lenta, com pausas entre as frases",
            "note": "Apresentação pessoal em forma polida.",
        },
        BAND_ELEMENTARY: {
            "transcript": (
                "ご案内（あんない）します。マドリード行（ゆ）き四八二便（びん）は、"
                "三十分（さんじゅっぷん）遅（おく）れています。"
                "十六番（じゅうろくばん）ゲートからご搭乗（とうじょう）ください。"
            ),
            "speaking_rate": "moderada, típica de anúncio público",
            "note": "Anúncio funcional com números e keigo.",
        },
        BAND_INTERMEDIATE: {
            "transcript": (
                "あの、明日（あした）の会議（かいぎ）ですが、部屋（へや）が午前中（ごぜんちゅう）しか"
                "空（あ）いていなかったので、時間（じかん）を早（はや）めました。"
                "メッセージでチームに伝（つた）えましたが、都合（つごう）が悪（わる）い人（ひと）がいたら、"
                "日程（にってい）を変（か）えても大丈夫（だいじょうぶ）です。"
            ),
            "speaking_rate": "natural, com hesitações",
            "note": "Fala espontânea de trabalho.",
        },
        BAND_UPPER: {
            "transcript": (
                "報告書（ほうこくしょ）で気（き）になったのは、数字（すうじ）そのものより、"
                "その見（み）せ方（かた）でした。すべてを一（ひと）つの指標（しひょう）にまとめると、"
                "いちばん重要（じゅうよう）なばらつきが隠（かく）れてしまいます。そうすると、"
                "議論（ぎろん）は平均（へいきん）の話（はなし）になってしまいます。"
            ),
            "speaking_rate": "rápida, natural, com encadeamento",
            "note": "Opinião analítica em velocidade real.",
        },
    },
    "zh-CN": {
        BAND_BEGINNER: {
            "transcript": "早上好。我叫卡洛斯。我是老师。很高兴认识你。",
            "speaking_rate": "lenta, com tons bem marcados",
            "note": "Pinyin: Zǎoshang hǎo. Wǒ jiào Kǎluòsī…",
        },
        BAND_ELEMENTARY: {
            "transcript": (
                "各位旅客请注意。飞往马德里的482次航班晚点三十分钟，"
                "将在十六号登机口开始登机。"
            ),
            "speaking_rate": "moderada, típica de anúncio público",
            "note": "Anúncio funcional com números.",
        },
        BAND_INTERMEDIATE: {
            "transcript": (
                "关于明天的会议啊，我把时间提前了，因为会议室只有上午空着。"
                "我已经发消息告诉大家了，如果谁来不了，我们再改时间也没问题。"
            ),
            "speaking_rate": "natural, com partículas de fala",
            "note": "Fala espontânea de trabalho.",
        },
        BAND_UPPER: {
            "transcript": (
                "这份报告里最让我在意的，不是数字本身，而是它的呈现方式。"
                "当你把所有东西都汇总成一个指标时，恰恰把最值得关注的差异藏了起来——"
                "于是讨论变成了关于平均值，而不是关于那些落在平均值之外的人。"
            ),
            "speaking_rate": "rápida, natural, com encadeamento",
            "note": "Opinião analítica em velocidade real.",
        },
    },
}

#: Exigências de escrita acrescentadas à rubrica da tarefa, por idioma.
#: É o que impede uma tarefa de escrita em japonês de ser cumprida em romaji.
WRITING_SCRIPT_HINTS: dict[str, list[str]] = {
    "en": [],
    "es-ES": ["Vocabulário peninsular", "Acentuação correta"],
    "fr": ["Gênero e concordância", "Acentos e cedilha"],
    "ja": ["Escreva em kana", "Kanji apenas com furigana", "Romaji não conta como resposta"],
    "zh-CN": ["Escreva em hanzi", "Inclua o pinyin com marcação de tom"],
}

#: Exemplos de gramática por idioma e faixa, alinhados a `GRAMMAR_FOCUS`.
#: Antes existia só para inglês (em `ai.py`), então uma lição de gramática em
#: japonês saía sem um único exemplo.
GRAMMAR_EXAMPLES: dict[str, dict[str, list[dict[str, str]]]] = {
    "en": {
        BAND_BEGINNER: [
            {"sentence": "What is your name?", "translation": "Qual é o seu nome?"},
            {"sentence": "Where are you from?", "translation": "De onde você é?"},
            {"sentence": "What do you do?", "translation": "O que você faz?"},
        ],
        BAND_ELEMENTARY: [
            {"sentence": "I worked late yesterday.", "translation": "Eu trabalhei até tarde ontem."},
            {"sentence": "I usually work from home.", "translation": "Eu normalmente trabalho de casa."},
            {"sentence": "She called, then she left.", "translation": "Ela ligou, depois saiu."},
        ],
        BAND_INTERMEDIATE: [
            {"sentence": "I have been to Paris three times.", "translation": "Já estive em Paris três vezes."},
            {"sentence": "I went to Paris in 2019.", "translation": "Fui a Paris em 2019."},
            {"sentence": "I have been working here since March.", "translation": "Trabalho aqui desde março."},
        ],
        BAND_UPPER: [
            {"sentence": "That might explain the delay.", "translation": "Isso talvez explique o atraso."},
            {"sentence": "If we had known, we would have waited.", "translation": "Se soubéssemos, teríamos esperado."},
            {"sentence": "It is arguably the better option.", "translation": "É, discutivelmente, a melhor opção."},
        ],
    },
    "es-ES": {
        BAND_BEGINNER: [
            {"sentence": "¿Cómo te llamas?", "translation": "Qual é o seu nome?"},
            {"sentence": "¿De dónde eres?", "translation": "De onde você é?"},
            {"sentence": "¿A qué te dedicas?", "translation": "O que você faz?"},
        ],
        BAND_ELEMENTARY: [
            {"sentence": "Ayer trabajé hasta tarde.", "translation": "Ontem trabalhei até tarde."},
            {"sentence": "Normalmente trabajo desde casa.", "translation": "Normalmente trabalho de casa."},
            {"sentence": "Llamó y luego se fue.", "translation": "Ligou e depois foi embora."},
        ],
        BAND_INTERMEDIATE: [
            {"sentence": "He estado en París tres veces.", "translation": "Já estive em Paris três vezes."},
            {"sentence": "Fui a París en 2019.", "translation": "Fui a Paris em 2019."},
            {"sentence": "Trabajo aquí desde marzo.", "translation": "Trabalho aqui desde março."},
        ],
        BAND_UPPER: [
            {"sentence": "Eso podría explicar el retraso.", "translation": "Isso poderia explicar o atraso."},
            {"sentence": "Si lo hubiéramos sabido, habríamos esperado.", "translation": "Se soubéssemos, teríamos esperado."},
            {"sentence": "Es, sin duda, la mejor opción.", "translation": "É, sem dúvida, a melhor opção."},
        ],
    },
    "fr": {
        BAND_BEGINNER: [
            {"sentence": "Comment vous appelez-vous ?", "translation": "Como você se chama?"},
            {"sentence": "D'où venez-vous ?", "translation": "De onde você é?"},
            {"sentence": "Que faites-vous ?", "translation": "O que você faz?"},
        ],
        BAND_ELEMENTARY: [
            {"sentence": "Hier, j'ai travaillé tard.", "translation": "Ontem trabalhei até tarde."},
            {"sentence": "D'habitude, je travaille chez moi.", "translation": "Normalmente trabalho em casa."},
            {"sentence": "Elle a appelé, puis elle est partie.", "translation": "Ela ligou, depois saiu."},
        ],
        BAND_INTERMEDIATE: [
            {"sentence": "Quand j'étais petit, je jouais au football.", "translation": "Quando eu era pequeno, eu jogava futebol."},
            {"sentence": "Hier, j'ai joué au football.", "translation": "Ontem joguei futebol."},
            {"sentence": "Je travaille ici depuis mars.", "translation": "Trabalho aqui desde março."},
        ],
        BAND_UPPER: [
            {"sentence": "Cela pourrait expliquer le retard.", "translation": "Isso poderia explicar o atraso."},
            {"sentence": "Si nous avions su, nous aurions attendu.", "translation": "Se soubéssemos, teríamos esperado."},
            {"sentence": "C'est sans doute la meilleure option.", "translation": "É, sem dúvida, a melhor opção."},
        ],
    },
    "ja": {
        BAND_BEGINNER: [
            {"sentence": "お名前（なまえ）は何（なん）ですか。", "translation": "Qual é o seu nome?"},
            {"sentence": "どこから来（き）ましたか。", "translation": "De onde você veio?"},
            {"sentence": "お仕事（しごと）は何（なん）ですか。", "translation": "O que você faz?"},
        ],
        BAND_ELEMENTARY: [
            {"sentence": "昨日（きのう）遅（おそ）くまで働（はたら）きました。", "translation": "Ontem trabalhei até tarde."},
            {"sentence": "いつも家（いえ）で働（はたら）きます。", "translation": "Sempre trabalho em casa."},
            {"sentence": "電話（でんわ）して、それから帰（かえ）りました。", "translation": "Ligou e depois foi embora."},
        ],
        BAND_INTERMEDIATE: [
            {"sentence": "パリに行（い）ったことがあります。", "translation": "Já estive em Paris."},
            {"sentence": "二〇一九年（にせんじゅうくねん）にパリに行（い）きました。", "translation": "Fui a Paris em 2019."},
            {"sentence": "三月（さんがつ）からここで働（はたら）いています。", "translation": "Trabalho aqui desde março."},
        ],
        BAND_UPPER: [
            {"sentence": "それが遅（おく）れの理由（りゆう）かもしれません。", "translation": "Isso talvez explique o atraso."},
            {"sentence": "知（し）っていたら、待（ま）っていたでしょう。", "translation": "Se soubéssemos, teríamos esperado."},
            {"sentence": "おそらく、そちらのほうが良（よ）い選択（せんたく）です。", "translation": "Provavelmente essa é a melhor opção."},
        ],
    },
    "zh-CN": {
        BAND_BEGINNER: [
            {"sentence": "你叫什么名字？", "translation": "Qual é o seu nome? (Nǐ jiào shénme míngzi?)"},
            {"sentence": "你是哪里人？", "translation": "De onde você é? (Nǐ shì nǎlǐ rén?)"},
            {"sentence": "你做什么工作？", "translation": "O que você faz? (Nǐ zuò shénme gōngzuò?)"},
        ],
        BAND_ELEMENTARY: [
            {"sentence": "昨天我工作到很晚。", "translation": "Ontem trabalhei até tarde. (Zuótiān wǒ gōngzuò dào hěn wǎn.)"},
            {"sentence": "我平时在家工作。", "translation": "Normalmente trabalho em casa. (Wǒ píngshí zài jiā gōngzuò.)"},
            {"sentence": "她打了电话，然后就走了。", "translation": "Ela ligou e depois foi embora. (Tā dǎle diànhuà, ránhòu jiù zǒule.)"},
        ],
        BAND_INTERMEDIATE: [
            {"sentence": "我去过巴黎三次。", "translation": "Já estive em Paris três vezes. (Wǒ qùguo Bālí sān cì.)"},
            {"sentence": "我2019年去了巴黎。", "translation": "Fui a Paris em 2019. (Wǒ 2019 nián qùle Bālí.)"},
            {"sentence": "我从三月起在这里工作。", "translation": "Trabalho aqui desde março. (Wǒ cóng sānyuè qǐ zài zhèlǐ gōngzuò.)"},
        ],
        BAND_UPPER: [
            {"sentence": "这也许可以解释延误。", "translation": "Isso talvez explique o atraso. (Zhè yěxǔ kěyǐ jiěshì yánwù.)"},
            {"sentence": "要是我们早知道，就会等了。", "translation": "Se soubéssemos, teríamos esperado. (Yàoshi wǒmen zǎo zhīdào, jiù huì děngle.)"},
            {"sentence": "总的来说，这是更好的选择。", "translation": "De modo geral, é a melhor opção. (Zǒng de láishuō…)"},
        ],
    },
}

#: Um exercício por idioma e faixa. Cada um traz a razão da resposta: marcar
#: certo/errado sem explicar não ensina a montar a frase sozinho.
GRAMMAR_EXERCISES: dict[str, dict[str, list[dict]]] = {
    "en": {
        BAND_BEGINNER: [
            {
                "prompt": "____ is your name?",
                "options": ["What", "Where", "Who"],
                "answer": "What",
                "rationale": "'What' pergunta pela informação pedida (o nome).",
                "option_rationales": {
                    "What": "'What' pergunta pela informação pedida (o nome).",
                    "Where": "'Where' pergunta por lugar, não por nome.",
                    "Who": "'Who' pergunta por pessoa/identidade, não pelo nome em si neste padrão.",
                },
            }
        ],
        BAND_ELEMENTARY: [
            {
                "prompt": "I ____ late yesterday.",
                "options": ["worked", "work", "am working"],
                "answer": "worked",
                "rationale": "'Yesterday' fecha o tempo, então o passado simples é obrigatório.",
                "option_rationales": {
                    "worked": "Passado simples: combina com 'yesterday'.",
                    "work": "Presente simples não combina com um tempo passado fechado.",
                    "am working": "Presente contínuo descreve agora, não ontem.",
                },
            }
        ],
        BAND_INTERMEDIATE: [
            {
                "prompt": "I ____ to Paris three times.",
                "options": ["have been", "went", "was going"],
                "answer": "have been",
                "rationale": "Não há momento passado fechado: o que importa é a experiência acumulada.",
                "option_rationales": {
                    "have been": "Present perfect: experiência até agora, sem data fechada.",
                    "went": "Passado simples pede um momento específico (ex.: last year).",
                    "was going": "Passado contínuo descreve ação em progresso, não contagem de visitas.",
                },
            }
        ],
        BAND_UPPER: [
            {
                "prompt": "If we ____ earlier, we would have caught the train.",
                "options": ["had left", "left", "have left"],
                "answer": "had left",
                "rationale": "Hipótese contrafactual sobre o passado exige o mais-que-perfeito.",
                "option_rationales": {
                    "had left": "3ª condicional: if + past perfect + would have.",
                    "left": "Passado simples aqui formaria uma condicional de outro tipo, não contrafactual passado.",
                    "have left": "Present perfect não entra na estrutura contrafactual do passado.",
                },
            }
        ],
    },
    "es-ES": {
        BAND_BEGINNER: [
            {
                "prompt": "¿____ te llamas?",
                "options": ["Cómo", "Dónde", "Quién"],
                "answer": "Cómo",
                "rationale": "'Cómo' pergunta o nome; 'Dónde' pergunta lugar.",
                "option_rationales": {
                    "Cómo": "En '¿Cómo te llamas?' pergunta o nome.",
                    "Dónde": "Pergunta lugar, não o nome.",
                    "Quién": "Pergunta identidade de pessoa, não o padrão de nome.",
                },
            }
        ],
        BAND_ELEMENTARY: [
            {
                "prompt": "Ayer ____ hasta tarde.",
                "options": ["trabajé", "trabajo", "estoy trabajando"],
                "answer": "trabajé",
                "rationale": "'Ayer' fecha o tempo: pretérito indefinido.",
                "option_rationales": {
                    "trabajé": "Pretérito indefinido com marcador 'ayer'.",
                    "trabajo": "Presente não combina com 'ayer'.",
                    "estoy trabajando": "Estar + gerundio descreve agora, não ontem.",
                },
            }
        ],
        BAND_INTERMEDIATE: [
            {
                "prompt": "____ en París tres veces.",
                "options": ["He estado", "Estuve", "Estaba"],
                "answer": "He estado",
                "rationale": "Sem marcador fechado, o pretérito perfecto marca experiência acumulada (uso peninsular).",
                "option_rationales": {
                    "He estado": "Pretérito perfecto: experiência até o presente (peninsular).",
                    "Estuve": "Indefinido sugere um episódio pontual/fechado.",
                    "Estaba": "Imperfecto descreve hábito ou pano de fundo, não contagem de visitas.",
                },
            }
        ],
        BAND_UPPER: [
            {
                "prompt": "Si lo ____ antes, habríamos cogido el tren.",
                "options": ["hubiéramos sabido", "supimos", "sabíamos"],
                "answer": "hubiéramos sabido",
                "rationale": "Hipótese contrafactual do passado pede pluscuamperfecto de subjuntivo.",
                "option_rationales": {
                    "hubiéramos sabido": "Si + pluscuamperfecto de subjuntivo + condicional compuesto.",
                    "supimos": "Pretérito indefinido não forma a condicional contrafactual do passado.",
                    "sabíamos": "Imperfecto descreve estado, não a hipótese 'se tivéssemos sabido'.",
                },
            }
        ],
    },
    "fr": {
        BAND_BEGINNER: [
            {
                "prompt": "____ vous appelez-vous ?",
                "options": ["Comment", "Où", "Qui"],
                "answer": "Comment",
                "rationale": "'Comment' pergunta o nome; 'Où' pergunta lugar.",
                "option_rationales": {
                    "Comment": "Em 'Comment vous appelez-vous ?' pergunta o nome.",
                    "Où": "Pergunta lugar, não o nome.",
                    "Qui": "Pergunta identidade, não o padrão de nome.",
                },
            }
        ],
        BAND_ELEMENTARY: [
            {
                "prompt": "Hier, j'____ tard.",
                "options": ["ai travaillé", "travaille", "travaillerai"],
                "answer": "ai travaillé",
                "rationale": "'Hier' fecha o tempo: passé composé.",
                "option_rationales": {
                    "ai travaillé": "Passé composé com 'hier'.",
                    "travaille": "Présent não combina com 'hier'.",
                    "travaillerai": "Futur aponta para depois, não para ontem.",
                },
            }
        ],
        BAND_INTERMEDIATE: [
            {
                "prompt": "Quand j'étais enfant, je ____ souvent à la plage.",
                "options": ["allais", "suis allé", "irai"],
                "answer": "allais",
                "rationale": "Hábito no passado pede imparfait; uma ação pontual pediria passé composé.",
                "option_rationales": {
                    "allais": "Imparfait: hábito repetido no passado.",
                    "suis allé": "Passé composé marca um evento pontual, não 'souvent'.",
                    "irai": "Futur não descreve infância passada.",
                },
            }
        ],
        BAND_UPPER: [
            {
                "prompt": "Si nous ____ plus tôt, nous aurions eu le train.",
                "options": ["étions partis", "sommes partis", "partions"],
                "answer": "étions partis",
                "rationale": "Contrafactual do passado: plus-que-parfait na condição, conditionnel passé no resultado.",
                "option_rationales": {
                    "étions partis": "Si + plus-que-parfait para hipótese passada irreal.",
                    "sommes partis": "Passé composé não forma essa condicional irreal.",
                    "partions": "Imparfait sozinho não basta para o contrafactual com 'aurions eu'.",
                },
            }
        ],
    },
    "ja": {
        BAND_BEGINNER: [
            {
                "prompt": "お名前（なまえ）は____ですか。",
                "options": ["何（なん）", "どこ", "だれ"],
                "answer": "何（なん）",
                "rationale": "「何」pergunta pela coisa; 「どこ」pergunta lugar.",
                "option_rationales": {
                    "何（なん）": "「お名前は何ですか」é o padrão para perguntar o nome.",
                    "どこ": "Pergunta lugar, não o nome.",
                    "だれ": "Pergunta 'quem', não o padrão de nome.",
                },
            }
        ],
        BAND_ELEMENTARY: [
            {
                "prompt": "昨日（きのう）遅（おそ）くまで____。",
                "options": ["働（はたら）きました", "働（はたら）きます", "働（はたら）いています"],
                "answer": "働（はたら）きました",
                "rationale": "「昨日」fecha o tempo: a forma passada ました é obrigatória.",
                "option_rationales": {
                    "働（はたら）きました": "Forma passada com 「昨日」.",
                    "働（はたら）きます": "Não-passado não combina com 「昨日」.",
                    "働（はたら）いています": "Progressivo descreve agora, não ontem.",
                },
            }
        ],
        BAND_INTERMEDIATE: [
            {
                "prompt": "パリに行（い）った____があります。",
                "options": ["こと", "もの", "ところ"],
                "answer": "こと",
                "rationale": "「〜たことがある」é a estrutura fixa de experiência acumulada.",
                "option_rationales": {
                    "こと": "「たことがある」marca experiência.",
                    "もの": "Não forma a expressão de experiência.",
                    "ところ": "「ところ」marca momento/lugar relativo, não experiência.",
                },
            }
        ],
        BAND_UPPER: [
            {
                "prompt": "明日（あした）は雨（あめ）が降（ふ）る____。",
                "options": ["かもしれません", "ましょう", "てください"],
                "answer": "かもしれません",
                "rationale": "「かもしれない」marca possibilidade; grau de certeza menor que 「でしょう」.",
                "option_rationales": {
                    "かもしれません": "Possibilidade / incerteza sobre o futuro.",
                    "ましょう": "Convite ('vamos…'), não previsão.",
                    "てください": "Pedido cortês, não hipótese sobre o tempo.",
                },
            }
        ],
    },
    "zh-CN": {
        BAND_BEGINNER: [
            {
                "prompt": "你叫____名字？",
                "options": ["什么", "哪里", "谁"],
                "answer": "什么",
                "rationale": "「什么」pergunta pela coisa; 「哪里」pergunta lugar.",
                "option_rationales": {
                    "什么": "「你叫什么名字？」é o padrão para o nome.",
                    "哪里": "Pergunta lugar, não o nome.",
                    "谁": "Pergunta 'quem', não este padrão de nome.",
                },
            }
        ],
        BAND_ELEMENTARY: [
            {
                "prompt": "昨天我____到很晚。",
                "options": ["工作了", "工作", "在工作"],
                "answer": "工作了",
                "rationale": "「了」marca ação concluída; com 「昨天」o tempo já está fechado.",
                "option_rationales": {
                    "工作了": "「了」+ 「昨天」marca ação concluída.",
                    "工作": "Sem 「了」fica genérico/presente, não o evento de ontem.",
                    "在工作": "Progressivo descreve agora, não ontem.",
                },
            }
        ],
        BAND_INTERMEDIATE: [
            {
                "prompt": "我去____巴黎三次。",
                "options": ["过", "了", "着"],
                "answer": "过",
                "rationale": "「过」marca experiência acumulada; 「了」marcaria um fato pontual.",
                "option_rationales": {
                    "过": "「过」= experiência (já ter ido).",
                    "了": "Marca mudança/conclusão pontual, não contagem de experiência.",
                    "着": "Marca estado durativo, não experiência.",
                },
            }
        ],
        BAND_UPPER: [
            {
                "prompt": "要是我们早知道，____会等。",
                "options": ["就", "才", "还"],
                "answer": "就",
                "rationale": "「要是…就…」é o par condicional padrão do mandarim.",
                "option_rationales": {
                    "就": "Par 「要是…就…」para condição → resultado.",
                    "才": "「才」marca 'só então/apenas', não este par condicional.",
                    "还": "「还」marca 'ainda/também', não a condição.",
                },
            }
        ],
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


# ---------------------------------------------------------------------------
# Acessores com fallback explícito
# ---------------------------------------------------------------------------

#: Idiomas suportados. Vale como contrato: nenhuma célula
#: idioma × habilidade × faixa pode voltar vazia para nenhum deles.
SUPPORTED_LANGUAGES: tuple[str, ...] = ("en", "es-ES", "fr", "ja", "zh-CN")

#: Idioma usado quando um código desconhecido chega até aqui. Só protege contra
#: dado inesperado — para os cinco idiomas oficiais o fallback nunca dispara.
FALLBACK_LANGUAGE = "en"


def _by_language(table: dict, language_code: str) -> dict:
    return table.get(language_code) or table[FALLBACK_LANGUAGE]


def vocabulary(language_code: str, band: str) -> list[dict[str, str]]:
    table = _by_language(VOCABULARY, language_code)
    return list(table.get(band) or table[BAND_ELEMENTARY])


def reading_text(language_code: str, band: str) -> dict[str, object]:
    table = _by_language(READING_TEXTS, language_code)
    return dict(table.get(band) or table[BAND_ELEMENTARY])


def listening_script(language_code: str, band: str) -> dict[str, object]:
    table = _by_language(LISTENING_SCRIPTS, language_code)
    return dict(table.get(band) or table[BAND_ELEMENTARY])


def grammar_examples(language_code: str, band: str) -> list[dict[str, str]]:
    table = _by_language(GRAMMAR_EXAMPLES, language_code)
    return list(table.get(band) or table[BAND_ELEMENTARY])


def grammar_exercises(language_code: str, band: str) -> list[dict]:
    table = _by_language(GRAMMAR_EXERCISES, language_code)
    return list(table.get(band) or table[BAND_ELEMENTARY])


def pronunciation_focus(language_code: str) -> list[dict[str, str]]:
    return list(PRONUNCIATION_FOCUS.get(language_code) or PRONUNCIATION_FOCUS[FALLBACK_LANGUAGE])


def writing_task(language_code: str, band: str) -> dict[str, object]:
    """Tarefa de escrita da faixa, com as exigências de escrita do idioma.

    O enunciado é o mesmo entre idiomas (o que se pede escrever não muda); o
    que muda é a rubrica — em japonês e mandarim o sistema de escrita faz parte
    do que está sendo avaliado.
    """
    task = dict(WRITING_TASKS[band])
    hints = list(task["rubric_hints"])  # type: ignore[arg-type]
    hints.extend(WRITING_SCRIPT_HINTS.get(language_code, []))
    task["rubric_hints"] = hints
    return task


def conversation_situation(language_code: str, band: str) -> dict[str, str]:
    return dict(CONVERSATION_SITUATIONS[band])


def grammar_focus(language_code: str, band: str) -> dict[str, object]:
    return dict(GRAMMAR_FOCUS[band])


#: Habilidade → acessor. Usado pelo relatório de cobertura.
SKILL_ACCESSORS = {
    "vocabulary": vocabulary,
    "grammar": grammar_examples,
    "grammar_exercises": grammar_exercises,
    "reading": reading_text,
    "listening": listening_script,
    "writing": writing_task,
    "conversation": conversation_situation,
    "review": vocabulary,
}

ALL_BANDS: tuple[str, ...] = (
    BAND_BEGINNER,
    BAND_ELEMENTARY,
    BAND_INTERMEDIATE,
    BAND_UPPER,
)


def coverage_report() -> list[str]:
    """Células vazias no formato `idioma/habilidade/faixa`.

    Existe para virar teste: com `AI_MOCK_MODE=true` (o padrão do projeto), uma
    célula vazia aqui é um bloco do cronograma que abre sem conteúdo nenhum.
    """
    gaps: list[str] = []
    for language_code in SUPPORTED_LANGUAGES:
        for skill, accessor in SKILL_ACCESSORS.items():
            for band in ALL_BANDS:
                if not accessor(language_code, band):
                    gaps.append(f"{language_code}/{skill}/{band}")
        if not pronunciation_focus(language_code):
            gaps.append(f"{language_code}/pronunciation/-")
    return gaps
