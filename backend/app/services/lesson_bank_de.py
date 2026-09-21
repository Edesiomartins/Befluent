"""Conteúdo mock/banco para alemão (`de`).

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
    "de": {
        BAND_BEGINNER: [
            _v("guten Morgen", "bom dia", "Guten Morgen! Wie geht es Ihnen?", "Bom dia! Como vai?", "Use de manhã; à tarde, guten Tag."),
            _v("ich heiße", "eu me chamo", "Ich heiße Ana.", "Eu me chamo Ana.", "Apresentação direta. Substantivos em alemão levam maiúscula."),
            _v("danke", "obrigado(a)", "Danke für Ihre Hilfe.", "Obrigado pela sua ajuda.", "Não muda com o gênero de quem fala."),
            _v("ich verstehe nicht", "eu não entendo", "Entschuldigung, ich verstehe nicht.", "Desculpe, eu não entendo.", "Peça repetição sem travar."),
            _v("wie viel kostet", "quanto custa", "Wie viel kostet das?", "Quanto custa isto?", "Base de qualquer compra."),
            _v("Wasser", "água", "Ein Glas Wasser, bitte.", "Um copo de água, por favor.", "Substantivo neutro: das Wasser. Maiúscula obrigatória."),
        ],
        BAND_ELEMENTARY: [
            _v("suchen", "procurar", "Ich suche den Bahnhof.", "Procuro a estação.", "O objeto vai no acusativo: den Bahnhof."),
            _v("normalerweise", "normalmente", "Normalerweise arbeite ich von zu Hause.", "Normalmente trabalho de casa.", "Marca hábito atual; o verbo fica em segundo lugar."),
            _v("zu spät kommen", "chegar atrasado", "Entschuldigung, ich komme zu spät.", "Desculpe, estou atrasado.", "Expressão de atraso no dia a dia."),
            _v("sobald", "assim que", "Ruf mich an, sobald du ankommst.", "Me liga assim que você chegar.", "Na oração com sobald o verbo vai ao fim."),
            _v("statt", "em vez de", "Nehmen wir den Bus statt eines Taxis.", "Vamos de ônibus em vez de um táxi.", "Statt pede genitivo no registro cuidado."),
            _v("sich gewöhnen an", "acostumar-se com", "Ich gewöhne mich an das Wetter.", "Estou me acostumando com o clima.", "Verbo reflexivo + an."),
        ],
        BAND_INTERMEDIATE: [
            _v("merken", "perceber", "Ich habe das Problem zu spät gemerkt.", "Percebi o problema tarde demais.", "Particípio gemerkt com haben."),
            _v("umgehen mit", "lidar com", "Wir müssen mit der Verspätung umgehen.", "Precisamos lidar com o atraso.", "A preposição mit pede dativo."),
            _v("was ... angeht", "no que diz respeito a", "Was das Budget angeht, ist es geschlossen.", "Quanto ao orçamento, está fechado.", "Abre um tópico em reunião."),
            _v("sich freuen auf", "aguardar com expectativa", "Ich freue mich auf die Reise.", "Estou ansioso pela viagem.", "Auf + acusativo para o que ainda vem."),
            _v("hinweisen auf", "apontar para", "Er hat auf ein wichtiges Detail hingewiesen.", "Ele apontou um detalhe importante.", "Útil em argumentação."),
            _v("soweit ich weiß", "até onde eu sei", "Soweit ich weiß, bleibt das Treffen.", "Até onde eu sei, a reunião continua.", "Ressalva: informação não confirmada."),
        ],
        BAND_UPPER: [
            _v("die Auffassung vertreten", "sustentar a posição", "Viele Fachleute vertreten die Auffassung, die Reform sei überfällig.", "Muitos especialistas sustentam que a reforma está atrasada.", "Introduz posição argumentativa."),
            _v("im Gegenteil", "pelo contrário", "Im Gegenteil, die Daten legen das Gegenteil nahe.", "Pelo contrário, os dados sugerem o oposto.", "Contraste forte."),
            _v("zugeben, dass", "admitir que", "Ich gebe zu, dass der erste Entwurf schwach war.", "Admito que o primeiro rascunho era fraco.", "Concede um ponto sem abandonar a tese."),
            _v("ein Kompromiss", "um meio-termo", "Beide Seiten fanden einen Kompromiss.", "Os dois lados encontraram um meio-termo.", "Negociação."),
            _v("überprüfen", "verificar", "Überprüfen Sie das Datum, bevor Sie es teilen.", "Verifique a data antes de compartilhar.", "Ação concreta contra informação fraca."),
            _v("ein Zielkonflikt", "um trade-off", "Es gibt einen Zielkonflikt zwischen Privatsphäre und Bequemlichkeit.", "Há um trade-off entre privacidade e conveniência.", "Dilema típico em discussão."),
        ],
    }
}

READING_TEXTS: dict[str, dict[str, dict[str, object]]] = {
    "de": {
        BAND_BEGINNER: {
            "title": "Ein normaler Morgen",
            "text": (
                "Ana steht um sieben Uhr auf. Sie frühstückt mit ihrer Familie. "
                "Dann fährt sie mit dem Bus zur Arbeit. Die Fahrt dauert dreißig "
                "Minuten. Ana liest gern im Bus."
            ),
            "note": "Frases curtas, presente e rotina. Verbo em segunda posição.",
        },
        BAND_ELEMENTARY: {
            "title": "Umzug in eine andere Stadt",
            "text": (
                "Letztes Jahr ist Peter wegen der Arbeit in eine andere Stadt "
                "gezogen. Am Anfang war es schwer: Er kannte niemanden und vermisste "
                "seine Freunde. Nach und nach fand er neue Freunde in der Nachbarschaft. "
                "Heute sagt er, der Umzug war eine gute Entscheidung."
            ),
            "note": "Perfekt e pretérito, conectores e causa.",
        },
        BAND_INTERMEDIATE: {
            "title": "Wie flexible Arbeit den Alltag verändert hat",
            "text": (
                "Für viele Berufstätige hat flexible Arbeit mehr verändert als nur "
                "den Ort der Aufgaben. Sie hat auch verändert, wie Menschen ihre "
                "Aufmerksamkeit organisieren, mit Kollegen sprechen und Arbeit vom "
                "Privatleben trennen. Manche schätzen die Autonomie; andere vermissen "
                "die spontanen Gespräche im Büro."
            ),
            "note": "Texto expositivo, contraste de pontos de vista.",
        },
        BAND_UPPER: {
            "title": "Automatisierung und der Wert menschlicher Arbeit",
            "text": (
                "Die Debatte über Automatisierung schwankt zwischen zwei wenig "
                "plausiblen Extremen: dem allgemeinen Verschwinden von Arbeitsplätzen "
                "und der spontanen Entstehung besserer Stellen. Die verfügbaren Daten "
                "zeigen ein weniger dramatisches und unbequemeres Szenario — die "
                "ungleiche Neuverteilung von Aufgaben in bestehenden Berufen."
            ),
            "note": "Argumentação com nuance e ressalva.",
        },
    }
}

LISTENING_SCRIPTS: dict[str, dict[str, dict[str, object]]] = {
    "de": {
        BAND_BEGINNER: {
            "transcript": "Guten Morgen. Ich heiße Karl. Ich bin Lehrer. Freut mich.",
            "speaking_rate": "lenta, com pausas entre as frases",
            "note": "Apresentação pessoal simples.",
        },
        BAND_ELEMENTARY: {
            "transcript": (
                "Achtung, Fahrgäste. Flug 482 nach Madrid hat dreißig Minuten "
                "Verspätung. Das Boarding beginnt an Gate sechzehn."
            ),
            "speaking_rate": "moderada, típica de anúncio público",
            "note": "Anúncio funcional com números.",
        },
        BAND_INTERMEDIATE: {
            "transcript": (
                "Also, zum Meeting morgen: Ich habe es vorverlegt, weil der Raum "
                "nur am Vormittag frei war. Ich habe dem Team per Nachricht Bescheid "
                "gesagt, aber wenn jemand nicht kann, verschieben wir es."
            ),
            "speaking_rate": "natural, com hesitações",
            "note": "Fala espontânea de trabalho.",
        },
        BAND_UPPER: {
            "transcript": (
                "Was mir im Bericht aufgefallen ist, war nicht die Zahl selbst, "
                "sondern die Art, wie sie präsentiert wurde. Wenn man alles in einen "
                "einzigen Indikator packt, versteckt man genau die Variation, die zählt."
            ),
            "speaking_rate": "rápida, natural, com encadeamento",
            "note": "Opinião analítica em velocidade real.",
        },
    }
}

WRITING_SCRIPT_HINTS: dict[str, list[str]] = {
    "de": ["Substantivos com maiúscula", "Artigos, gênero e caso"],
}

GRAMMAR_EXAMPLES: dict[str, dict[str, list[dict[str, str]]]] = {
    "de": {
        BAND_BEGINNER: [
            {"sentence": "Wie heißen Sie?", "translation": "Como você se chama?"},
            {"sentence": "Woher kommen Sie?", "translation": "De onde você é?"},
            {"sentence": "Was machen Sie beruflich?", "translation": "O que você faz?"},
        ],
        BAND_ELEMENTARY: [
            {"sentence": "Ich habe gestern lange gearbeitet.", "translation": "Ontem trabalhei até tarde."},
            {"sentence": "Normalerweise arbeite ich von zu Hause.", "translation": "Normalmente trabalho de casa."},
            {"sentence": "Er hat angerufen und ist dann gegangen.", "translation": "Ele ligou e depois foi embora."},
        ],
        BAND_INTERMEDIATE: [
            {"sentence": "Ich bin dreimal in Paris gewesen.", "translation": "Já estive em Paris três vezes."},
            {"sentence": "Ich bin 2019 hingefahren.", "translation": "Fui lá em 2019."},
            {"sentence": "Ich arbeite hier seit März.", "translation": "Trabalho aqui desde março."},
        ],
        BAND_UPPER: [
            {"sentence": "Das könnte die Verspätung erklären.", "translation": "Isso poderia explicar o atraso."},
            {"sentence": "Wenn wir es gewusst hätten, hätten wir gewartet.", "translation": "Se soubéssemos, teríamos esperado."},
            {"sentence": "Das ist wohl die sicherere Wahl.", "translation": "Essa é, provavelmente, a escolha mais segura."},
        ],
    }
}

GRAMMAR_EXERCISES: dict[str, dict[str, list[dict]]] = {
    "de": {
        BAND_BEGINNER: [
            _q(
                "Wie ____ Sie?",
                "heißen",
                [
                    ("heißen", "'Wie heißen Sie?' pergunta o nome."),
                    ("heiße", "'Heiße' combina com ich, não com Sie."),
                    ("heißt", "'Heißt' combina com er/sie, não com Sie formal."),
                ],
                "Pergunta de identidade.",
            ),
            _q(
                "____ kommen Sie?",
                "Woher",
                [
                    ("Woher", "'Woher kommen Sie?' pergunta a origem."),
                    ("Wohin", "'Wohin' pergunta o destino."),
                    ("Warum", "'Warum' pergunta a causa."),
                ],
                "Pergunta de origem.",
            ),
            _q(
                "Was ____ Sie beruflich?",
                "machen",
                [
                    ("machen", "'Was machen Sie beruflich?' pergunta a ocupação."),
                    ("macht", "'Macht' é terceira pessoa do singular."),
                    ("mache", "'Mache' combina com ich."),
                ],
                "Pergunta de rotina.",
            ),
            _q(
                "Ich ____ Ana.",
                "bin",
                [
                    ("bin", "'Ich' pede 'bin'."),
                    ("bist", "'Bist' combina com du."),
                    ("ist", "'Ist' combina com er/sie/es."),
                ],
                "Identidade: ich bin.",
            ),
        ],
        BAND_ELEMENTARY: [
            _q(
                "Ich habe gestern lange ____.",
                "gearbeitet",
                [
                    ("gearbeitet", "'Gestern' fecha o tempo: Perfekt com particípio no fim."),
                    ("arbeite", "Presente não fecha o fato de ontem."),
                    ("arbeiten", "Infinitivo não é o particípio do Perfekt."),
                ],
                "Marcador fechado pede Perfekt.",
            ),
            _q(
                "Normalerweise ____ ich von zu Hause.",
                "arbeite",
                [
                    ("arbeite", "'Normalerweise' marca hábito; o verbo fica em segundo lugar."),
                    ("gearbeitet", "Particípio não ocupa a segunda posição sozinho."),
                    ("arbeitete", "Pretérito encerraria o hábito atual."),
                ],
                "Hábito atual: presente, verbo em segunda posição.",
            ),
            _q(
                "Er hat angerufen und ist dann ____.",
                "gegangen",
                [
                    ("gegangen", "Sequência no passado: 'gehen' usa sein + gegangen."),
                    ("gehen", "Infinitivo não fecha o segundo fato."),
                    ("geht", "Presente quebra a sequência."),
                ],
                "Sequência de fatos no passado.",
            ),
            _q(
                "Der Bahnhof — ich suche ____.",
                "den Bahnhof",
                [
                    ("den Bahnhof", "Objeto direto masculino: acusativo 'den'."),
                    ("der Bahnhof", "Nominativo: serve de sujeito, não de objeto de suchen."),
                    ("dem Bahnhof", "Dativo não é o caso do objeto de suchen."),
                ],
                "Caso do objeto: acusativo masculino.",
            ),
        ],
        BAND_INTERMEDIATE: [
            _q(
                "Ich bin dreimal in Paris ____.",
                "gewesen",
                [
                    ("gewesen", "Sem data fechada: experiência com sein + gewesen."),
                    ("war", "'War' sozinho não conta as três vezes nesta estrutura."),
                    ("bin", "Presente não marca a experiência acumulada."),
                ],
                "Experiência acumulada, sem ano fechado.",
            ),
            _q(
                "Ich ____ 2019 hingefahren.",
                "bin",
                [
                    ("bin", "'2019' fecha o tempo; 'fahren' forma o Perfekt com sein."),
                    ("habe", "'Hinfahren' não usa haben."),
                    ("war", "'War' não é o auxiliar deste Perfekt."),
                ],
                "Marcador fechado pede Perfekt.",
            ),
            _q(
                "Ich arbeite hier ____ März.",
                "seit",
                [
                    ("seit", "'Seit' + presente: a ação continua desde março."),
                    ("vor", "'Vor' marca um ponto já passado e encerrado."),
                    ("für", "'Für' não marca o início de uma ação em curso."),
                ],
                "Ação iniciada no passado e ainda em curso.",
            ),
            _q(
                "Als ich klein war, ____ ich oft ans Meer.",
                "fuhr",
                [
                    ("fuhr", "Hábito no passado: pretérito."),
                    ("fahre", "Presente não descreve a infância."),
                    ("werde fahren", "Futuro não descreve o hábito passado."),
                ],
                "Hábito passado, não fato único de agora.",
            ),
        ],
        BAND_UPPER: [
            _q(
                "Das ____ die Verspätung erklären.",
                "könnte",
                [
                    ("könnte", "Konjunktiv II de possibilidade."),
                    ("muss zu", "'Müssen' não leva 'zu' antes do infinitivo."),
                    ("kann zu", "'Können' também não leva 'zu'."),
                ],
                "Modalização de possibilidade.",
            ),
            _q(
                "Wenn wir es gewusst ____, hätten wir gewartet.",
                "hätten",
                [
                    ("hätten", "Contrafactual do passado: hätte + particípio na condição."),
                    ("haben", "Indicativo presente não forma a hipótese irreal."),
                    ("würden", "'Würden' não substitui o auxiliar desta condição."),
                ],
                "Hipótese contrafactual sobre o passado.",
            ),
            _q(
                "Das ist ____ die sicherere Wahl.",
                "wohl",
                [
                    ("wohl", "Ressalva: provavelmente, não com certeza absoluta."),
                    ("wohl zu", "'Wohl' não leva 'zu' neste encaixe."),
                    ("sicherlich nicht", "Negação categórica, não a ressalva pedida."),
                ],
                "Ressalva que preserva o argumento.",
            ),
            _q(
                "Ich gebe zu, dass der Entwurf schwach ____.",
                "war",
                [
                    ("war", "O rascunho já existe no passado: pretérito na oração com dass."),
                    ("ist gewesen worden", "Construção inexistente para este juízo."),
                    ("sein", "Infinitivo não fecha a oração subordinada."),
                ],
                "Concessão sobre um fato já ocorrido; o verbo fica no fim.",
            ),
        ],
    }
}

PRONUNCIATION_FOCUS: dict[str, list[dict[str, str]]] = {
    "de": [
        {
            "sound": "ch (ich × ach)",
            "why_hard": "Não existe em português; costuma virar 'x' ou 'rr'.",
            "how_to_produce": "Depois de e/i, som suave no palato ('ich'). Depois de a/o/u, som mais atrás ('ach').",
        },
        {
            "sound": "umlauts ä, ö, ü",
            "why_hard": "O português não arredonda essas vogais do mesmo modo.",
            "how_to_produce": "Ä como 'e' aberto; ö e ü: diga 'e' ou 'i' e arredonde os lábios sem mover a língua.",
        },
        {
            "sound": "r uvular e ensurdecimento final",
            "why_hard": "O r brasileiro muda, e no fim da palavra 'Tag' soa como 'Tak'.",
            "how_to_produce": "R no fundo da boca. No fim da sílaba, b/d/g perdem a vibração: Tag ≈ 'tak'.",
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
