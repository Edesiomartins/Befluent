"""Conteúdo mock/banco para italiano (`it`).

Mesma regra dos idiomas de alfabeto latino falados (inglês, francês, espanhol):
conversação, escuta, vocabulário, gramática aplicada, pronúncia e leitura.
Não segue a trilha de escrita do japonês/mandarim nem a de leitura do latim.

LIMITAÇÃO: banco de desenvolvimento, sem revisão de falante nativo.
"""

from __future__ import annotations

from typing import Any

BAND_BEGINNER = "beginner"
BAND_ELEMENTARY = "elementary"
BAND_INTERMEDIATE = "intermediate"
BAND_UPPER = "upper"


def _q(prompt: str, answer: str, options: list[tuple[str, str]], rationale: str) -> dict:
    return {
        "prompt": prompt,
        "options": [text for text, _why in options],
        "answer": answer,
        "rationale": rationale,
        "option_rationales": {text: why for text, why in options},
    }


def _v(term: str, translation: str, example: str, example_translation: str, usage_note: str) -> dict[str, str]:
    return {
        "term": term,
        "translation": translation,
        "example": example,
        "example_translation": example_translation,
        "usage_note": usage_note,
    }


VOCABULARY: dict[str, dict[str, list[dict[str, str]]]] = {
    "it": {
        BAND_BEGINNER: [
            _v("buongiorno", "bom dia", "Buongiorno, come sta?", "Bom dia, como vai?", "Use até o início da tarde; depois, buonasera."),
            _v("mi chiamo", "eu me chamo", "Mi chiamo Ana.", "Eu me chamo Ana.", "Apresentação mais comum do que 'il mio nome è'."),
            _v("grazie", "obrigado(a)", "Grazie per l'aiuto.", "Obrigado pela ajuda.", "Não muda com o gênero de quem fala."),
            _v("non capisco", "eu não entendo", "Scusi, non capisco.", "Desculpe, eu não entendo.", "Peça repetição sem travar a conversa."),
            _v("quanto costa", "quanto custa", "Quanto costa questo?", "Quanto custa isto?", "Base de qualquer compra."),
            _v("acqua", "água", "Un bicchiere d'acqua, per favore.", "Um copo de água, por favor.", "Substantivo feminino: l'acqua."),
        ],
        BAND_ELEMENTARY: [
            _v("cercare", "procurar", "Cerco la stazione.", "Procuro a estação.", "Sem preposição extra: cercare + objeto."),
            _v("di solito", "normalmente", "Di solito lavoro da casa.", "Normalmente trabalho de casa.", "Marca hábito atual."),
            _v("essere in ritardo", "estar atrasado", "Scusa, sono in ritardo.", "Desculpa, estou atrasado.", "Expressão fixa com essere."),
            _v("appena", "assim que", "Chiamami appena arrivi.", "Me liga assim que você chegar.", "Conector de tempo imediato."),
            _v("invece di", "em vez de", "Prendiamo il bus invece del taxi.", "Vamos de ônibus em vez do táxi.", "Di + artigo se o que segue é substantivo."),
            _v("abituarsi", "acostumar-se", "Mi sto abituando al clima.", "Estou me acostumando com o clima.", "Verbo pronominal: mi abituo."),
        ],
        BAND_INTERMEDIATE: [
            _v("rendersi conto", "dar-se conta", "Mi sono reso conto del problema.", "Eu me dei conta do problema.", "Passato prossimo com essere."),
            _v("fare fronte a", "lidar com", "Dobbiamo fare fronte al ritardo.", "Precisamos lidar com o atraso.", "Registro um pouco formal."),
            _v("per quanto riguarda", "no que diz respeito a", "Per quanto riguarda il budget, è chiuso.", "Quanto ao orçamento, está fechado.", "Abre um tópico em reunião."),
            _v("non vedo l'ora", "mal posso esperar", "Non vedo l'ora del viaggio.", "Mal posso esperar pela viagem.", "Expectativa positiva."),
            _v("mettere in evidenza", "destacar", "Ha messo in evidenza un dettaglio.", "Ele destacou um detalhe.", "Útil em argumentação."),
            _v("a quanto pare", "ao que parece", "A quanto pare, la riunione resta.", "Ao que parece, a reunião continua.", "Ressalva: informação não confirmada."),
        ],
        BAND_UPPER: [
            _v("sostenere che", "sustentar que", "Molti esperti sostengono che la riforma sia urgente.", "Muitos especialistas sustentam que a reforma é urgente.", "Introduz posição; o que segue pode ir ao subjuntivo."),
            _v("al contrario", "pelo contrário", "Al contrario, i dati suggeriscono l'opposto.", "Pelo contrário, os dados sugerem o oposto.", "Contraste forte."),
            _v("ammettere che", "admitir que", "Ammetto che la prima bozza era debole.", "Admito que o primeiro rascunho era fraco.", "Concede um ponto sem abandonar a tese."),
            _v("un compromesso", "um meio-termo", "Le parti hanno trovato un compromesso.", "As partes encontraram um meio-termo.", "Negociação."),
            _v("verificare", "verificar", "Verifica la data prima di condividere.", "Verifique a data antes de compartilhar.", "Ação concreta contra informação fraca."),
            _v("un trade-off", "um trade-off", "C'è un trade-off tra privacy e comodità.", "Há um trade-off entre privacidade e conveniência.", "Dilema típico em discussão."),
        ],
    }
}

READING_TEXTS: dict[str, dict[str, dict[str, object]]] = {
    "it": {
        BAND_BEGINNER: {
            "title": "Una mattina normale",
            "text": (
                "Ana si alza alle sette. Fa colazione con la famiglia. "
                "Poi va al lavoro in autobus. Il viaggio dura trenta minuti. "
                "Ad Ana piace leggere in autobus."
            ),
            "note": "Frases curtas, presente e rotina.",
        },
        BAND_ELEMENTARY: {
            "title": "Trasferirsi in un'altra città",
            "text": (
                "L'anno scorso Pietro si è trasferito in un'altra città per lavoro. "
                "All'inizio è stato difficile: non conosceva nessuno e gli mancavano "
                "gli amici. Piano piano ha fatto nuove amicizie nel quartiere. Oggi "
                "dice che il trasferimento è stata una buona decisione."
            ),
            "note": "Passato prossimo, conectores e causa.",
        },
        BAND_INTERMEDIATE: {
            "title": "Come il lavoro flessibile ha cambiato le routine",
            "text": (
                "Per molti professionisti il lavoro flessibile ha cambiato più del "
                "luogo in cui si svolgono i compiti. Ha cambiato anche il modo di "
                "organizzare l'attenzione, di parlare con i colleghi e di separare "
                "il lavoro dalla vita personale. Alcuni apprezzano l'autonomia; "
                "altri sentono la mancanza delle conversazioni spontanee in ufficio."
            ),
            "note": "Texto expositivo, contraste de pontos de vista.",
        },
        BAND_UPPER: {
            "title": "Automazione e valore del lavoro umano",
            "text": (
                "Il dibattito sull'automazione oscilla tra due estremi poco "
                "plausibili: la scomparsa generale dei lavori e la creazione "
                "spontanea di lavori migliori. I dati disponibili indicano uno "
                "scenario meno drammatico e più scomodo — la ricomposizione "
                "disuguale dei compiti dentro le professioni già esistenti."
            ),
            "note": "Argumentação com nuance e ressalva.",
        },
    }
}

LISTENING_SCRIPTS: dict[str, dict[str, dict[str, object]]] = {
    "it": {
        BAND_BEGINNER: {
            "transcript": "Buongiorno. Mi chiamo Carlo. Sono un insegnante. Piacere.",
            "speaking_rate": "lenta, com pausas entre as frases",
            "note": "Apresentação pessoal simples.",
        },
        BAND_ELEMENTARY: {
            "transcript": (
                "Attenzione, passeggeri. Il volo 482 per Madrid è in ritardo di "
                "trenta minuti. L'imbarco inizierà al gate sedici."
            ),
            "speaking_rate": "moderada, típica de anúncio público",
            "note": "Anúncio funcional com números.",
        },
        BAND_INTERMEDIATE: {
            "transcript": (
                "Allora, per la riunione di domani: l'ho anticipata perché la sala "
                "era libera solo la mattina. L'ho detto al team per messaggio, ma "
                "se qualcuno non può, la spostiamo senza problema."
            ),
            "speaking_rate": "natural, com hesitações",
            "note": "Fala espontânea de trabalho.",
        },
        BAND_UPPER: {
            "transcript": (
                "Quello che mi ha colpito nel rapporto non è stato il numero in sé, "
                "ma il modo in cui è stato presentato. Quando aggreghi tutto in un "
                "unico indicatore, nascondi proprio la variazione che conta."
            ),
            "speaking_rate": "rápida, natural, com encadeamento",
            "note": "Opinião analítica em velocidade real.",
        },
    }
}

WRITING_SCRIPT_HINTS: dict[str, list[str]] = {
    "it": ["Gênero e concordância", "Artigos e acentuação"],
}

GRAMMAR_EXAMPLES: dict[str, dict[str, list[dict[str, str]]]] = {
    "it": {
        BAND_BEGINNER: [
            {"sentence": "Come ti chiami?", "translation": "Como você se chama?"},
            {"sentence": "Di dove sei?", "translation": "De onde você é?"},
            {"sentence": "Che lavoro fai?", "translation": "O que você faz?"},
        ],
        BAND_ELEMENTARY: [
            {"sentence": "Ieri ho lavorato fino a tardi.", "translation": "Ontem trabalhei até tarde."},
            {"sentence": "Di solito lavoro da casa.", "translation": "Normalmente trabalho de casa."},
            {"sentence": "Ha chiamato e poi è uscito.", "translation": "Ligou e depois saiu."},
        ],
        BAND_INTERMEDIATE: [
            {"sentence": "Sono stato a Parigi tre volte.", "translation": "Já estive em Paris três vezes."},
            {"sentence": "Ci sono andato nel 2019.", "translation": "Fui lá em 2019."},
            {"sentence": "Lavoro qui da marzo.", "translation": "Trabalho aqui desde março."},
        ],
        BAND_UPPER: [
            {"sentence": "Questo potrebbe spiegare il ritardo.", "translation": "Isso poderia explicar o atraso."},
            {"sentence": "Se lo avessimo saputo, avremmo aspettato.", "translation": "Se soubéssemos, teríamos esperado."},
            {"sentence": "È, probabilmente, la scelta più sicura.", "translation": "É, provavelmente, a escolha mais segura."},
        ],
    }
}

GRAMMAR_EXERCISES: dict[str, dict[str, list[dict]]] = {
    "it": {
        BAND_BEGINNER: [
            _q(
                "Come ti ____?",
                "chiami",
                [
                    ("chiami", "'Come ti chiami?' pergunta o nome, com 'tu'."),
                    ("chiamo", "'Chiamo' é a resposta de quem fala."),
                    ("chiama", "'Chiama' é terceira pessoa."),
                ],
                "Pergunta de identidade no presente.",
            ),
            _q(
                "Di ____ sei?",
                "dove",
                [
                    ("dove", "'Di dove sei?' pergunta a origem."),
                    ("che", "'Che' não forma a pergunta de origem."),
                    ("chi", "'Chi' pergunta a pessoa."),
                ],
                "Pergunta de origem.",
            ),
            _q(
                "Che lavoro ____?",
                "fai",
                [
                    ("fai", "'Che lavoro fai?' pergunta a ocupação a 'tu'."),
                    ("faccio", "'Faccio' seria a resposta."),
                    ("fa", "'Fa' é terceira pessoa."),
                ],
                "Pergunta de rotina.",
            ),
            _q(
                "Io ____ Ana.",
                "sono",
                [
                    ("sono", "'Io' pede 'sono'."),
                    ("sei", "'Sei' combina com tu."),
                    ("è", "'È' combina com lui/lei."),
                ],
                "Identidade: io sono.",
            ),
        ],
        BAND_ELEMENTARY: [
            _q(
                "Ieri ____ fino a tardi.",
                "ho lavorato",
                [
                    ("ho lavorato", "'Ieri' fecha o tempo: passato prossimo."),
                    ("lavoro", "Presente não combina com 'ieri'."),
                    ("lavorerò", "Futuro aponta para depois, não para ontem."),
                ],
                "Marcador fechado pede passato prossimo.",
            ),
            _q(
                "Di solito ____ da casa.",
                "lavoro",
                [
                    ("lavoro", "'Di solito' marca hábito atual."),
                    ("ho lavorato", "Passato prossimo encerraria o hábito."),
                    ("lavoravo", "Imperfetto descreve hábito passado."),
                ],
                "Hábito que continua válido fica no presente.",
            ),
            _q(
                "Ha chiamato e poi ____.",
                "è uscito",
                [
                    ("è uscito", "Sequência no passado: os dois no passato prossimo."),
                    ("esce", "Presente quebra a sequência."),
                    ("uscirà", "Futuro não fecha o segundo fato."),
                ],
                "Sequência de fatos no passado.",
            ),
            _q(
                "Ieri sera ____ a casa tardi.",
                "sono tornato",
                [
                    ("sono tornato", "'Tornare' forma o passato prossimo com essere."),
                    ("ho tornato", "'Tornare' não usa avere neste sentido."),
                    ("torno", "Presente não combina com 'ieri sera'."),
                ],
                "Verbo de movimento: ausiliare essere.",
            ),
        ],
        BAND_INTERMEDIATE: [
            _q(
                "____ a Parigi tre volte.",
                "Sono stato",
                [
                    ("Sono stato", "Sem data fechada: experiência acumulada."),
                    ("Stavo", "Imperfetto descreve fundo ou hábito, não a contagem."),
                    ("Starò", "Futuro não descreve as três visitas."),
                ],
                "Experiência, sem momento fechado.",
            ),
            _q(
                "Ci ____ nel 2019.",
                "sono andato",
                [
                    ("sono andato", "'Nel 2019' fecha o tempo."),
                    ("vado", "Presente não combina com o ano fechado."),
                    ("andrò", "Futuro aponta para depois de 2019."),
                ],
                "Marcador fechado pede passato prossimo.",
            ),
            _q(
                "Lavoro qui ____ marzo.",
                "da",
                [
                    ("da", "'Da' + presente: a ação continua desde março."),
                    ("per", "'Per' mediria uma duração já medida, não o início."),
                    ("fra", "'Fra' aponta para o futuro ('daqui a')."),
                ],
                "Ação iniciada no passado e ainda em curso.",
            ),
            _q(
                "Quando ero piccolo, ____ spesso al mare.",
                "andavo",
                [
                    ("andavo", "Hábito no passado: imperfetto."),
                    ("sono andato", "Passato prossimo marca um evento pontual, não 'spesso'."),
                    ("andrò", "Futuro não descreve a infância."),
                ],
                "Hábito passado pede imperfetto.",
            ),
        ],
        BAND_UPPER: [
            _q(
                "Questo ____ spiegare il ritardo.",
                "potrebbe",
                [
                    ("potrebbe", "Condicional de possibilidade."),
                    ("deve di", "Construção inválida."),
                    ("può a", "'Può' não leva 'a' aqui."),
                ],
                "Modalização de possibilidade.",
            ),
            _q(
                "Se lo ____, avremmo aspettato.",
                "avessimo saputo",
                [
                    ("avessimo saputo", "Contrafactual do passado: congiuntivo trapassato."),
                    ("sappiamo", "Presente não forma a hipótese."),
                    ("avremmo", "'Avremmo' fica no resultado, não depois de se."),
                ],
                "Hipótese contrafactual sobre o passado.",
            ),
            _q(
                "È, ____, la scelta più sicura.",
                "probabilmente",
                [
                    ("probabilmente", "Ressalva: provável, não absoluto."),
                    ("probabile", "Adjetivo; a frase pede advérbio."),
                    ("probabilità", "Substantivo não cabe neste encaixe."),
                ],
                "Ressalva que preserva o argumento.",
            ),
            _q(
                "Ammetto che la prima bozza ____ debole.",
                "fosse",
                [
                    ("fosse", "Depois de 'ammettere che', o juízo vai ao congiuntivo."),
                    ("è", "Indicativo aqui soa categórico demais para a concessão."),
                    ("sarà", "Futuro não descreve o rascunho já escrito."),
                ],
                "Concessão modalizada, não afirmação bruta.",
            ),
        ],
    }
}

PRONUNCIATION_FOCUS: dict[str, list[dict[str, str]]] = {
    "it": [
        {
            "sound": "consoantes duplas",
            "why_hard": "Em português a dobra quase não muda a palavra; em italiano muda o sentido.",
            "how_to_produce": "Segure a consoante: 'pala' (pá) × 'palla' (bola).",
        },
        {
            "sound": "e/o abertos × fechados",
            "why_hard": "O português não distingue esses pares como o italiano padrão.",
            "how_to_produce": "Compare 'pesca' (pêssego, e fechado) e 'pesca' (pesca, e aberto) isoladamente.",
        },
        {
            "sound": "gli e gn",
            "why_hard": "Não há equivalente estável; 'gli' vira 'li' e 'gn' vira 'nh' frouxo.",
            "how_to_produce": "'Gli' como o 'lh' de 'filho'; 'gn' como o 'nh' de 'ninho', com a língua no palato.",
        },
    ]
}


def register(into: dict[str, Any]) -> None:
    into["VOCABULARY"].update(VOCABULARY)
    into["READING_TEXTS"].update(READING_TEXTS)
    into["LISTENING_SCRIPTS"].update(LISTENING_SCRIPTS)
    into["WRITING_SCRIPT_HINTS"].update(WRITING_SCRIPT_HINTS)
    into["GRAMMAR_EXAMPLES"].update(GRAMMAR_EXAMPLES)
    into["GRAMMAR_EXERCISES"].update(GRAMMAR_EXERCISES)
    into["PRONUNCIATION_FOCUS"].update(PRONUNCIATION_FOCUS)
