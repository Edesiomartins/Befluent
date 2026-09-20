"""Conteúdo mock/banco para latim clássico (`la-classical`).

Foco: República / início do Império, morfologia, prosa graduada e pronúncia
clássica reconstruída. Não reutiliza gabaritos fonéticos eclesiásticos.
"""

from __future__ import annotations

from typing import Any

BAND_BEGINNER = "beginner"
BAND_ELEMENTARY = "elementary"
BAND_INTERMEDIATE = "intermediate"
BAND_UPPER = "upper"

VOCABULARY: dict[str, dict[str, list[dict[str, str]]]] = {
    "la-classical": {
        BAND_BEGINNER: [
            {
                "term": "caelum",
                "translation": "céu",
                "example": "Caelum serenum est.",
                "example_translation": "O céu está sereno.",
                "usage_note": "Na pronúncia clássica reconstruída: c=/k/, ae=/ae̯/ → ≈ /ˈkae̯.lum/.",
                "themes": ["Alfabeto e pronúncia clássica"],
            },
            {
                "term": "via",
                "translation": "caminho / estrada",
                "example": "Via Appia longa est.",
                "example_translation": "A Via Ápia é longa.",
                "usage_note": "Na pronúncia clássica reconstruída: v ≈ /w/ → /ˈwi.a/.",
                "themes": ["Alfabeto e pronúncia clássica", "Roma e as vias"],
            },
            {
                "term": "rosa",
                "translation": "rosa",
                "example": "Rosa pulchra est.",
                "example_translation": "A rosa é bela.",
                "usage_note": "1ª declinação; nominativo singular em -a.",
                "themes": ["1ª declinação"],
            },
            {
                "term": "puella",
                "translation": "menina",
                "example": "Puella librum legit.",
                "example_translation": "A menina lê um livro.",
                "usage_note": "Nominativo sujeito; acusativo librum objeto.",
                "themes": ["Nominativo e acusativo"],
            },
            {
                "term": "amicus",
                "translation": "amigo",
                "example": "Amicus meus venit.",
                "example_translation": "Meu amigo vem.",
                "usage_note": "2ª declinação masculina em -us.",
                "themes": ["2ª declinação"],
            },
            {
                "term": "bellum",
                "translation": "guerra",
                "example": "Bellum longum fuit.",
                "example_translation": "A guerra foi longa.",
                "usage_note": "Neutro da 2ª declinação; nominativo = acusativo.",
                "themes": ["2ª declinação", "República Romana"],
            },
            {
                "term": "rex",
                "translation": "rei",
                "example": "Rex populum ducit.",
                "example_translation": "O rei conduz o povo.",
                "usage_note": "3ª declinação; genitivo regis.",
                "themes": ["3ª declinação"],
            },
            {
                "term": "urbs",
                "translation": "cidade",
                "example": "Roma urbs magna est.",
                "example_translation": "Roma é uma grande cidade.",
                "usage_note": "3ª declinação; genitivo urbis.",
                "themes": ["Roma e as vias"],
            },
            {
                "term": "vinum",
                "translation": "vinho",
                "example": "Vinum bibimus.",
                "example_translation": "Bebemos vinho.",
                "usage_note": "Na pronúncia clássica reconstruída: v ≈ /w/ → /ˈwi.num/.",
                "themes": ["Alfabeto e pronúncia clássica"],
            },
            {
                "term": "quattuor",
                "translation": "quatro",
                "example": "Quattuor libri sunt.",
                "example_translation": "Há quatro livros.",
                "usage_note": "Na pronúncia clássica reconstruída: qu = /kʷ/.",
                "themes": ["Alfabeto e pronúncia clássica"],
            },
            {
                "term": "Cicero",
                "translation": "Cícero",
                "example": "Cicero orator clarus est.",
                "example_translation": "Cícero é um orador célebre.",
                "usage_note": "Na pronúncia clássica reconstruída: /ˈki.ke.ro/ (c=/k/).",
                "themes": ["Alfabeto e pronúncia clássica", "Prosa clássica"],
            },
            {
                "term": "Caesar",
                "translation": "César",
                "example": "Caesar Galliam vicit.",
                "example_translation": "César venceu a Gália.",
                "usage_note": "Na pronúncia clássica reconstruída: /ˈkae̯.sar/ (não 'Chésar').",
                "themes": ["Alfabeto e pronúncia clássica", "República Romana"],
            },
        ],
        BAND_ELEMENTARY: [
            {
                "term": "senatus",
                "translation": "senado",
                "example": "Senatus consultum fecit.",
                "example_translation": "O senado fez um decreto.",
                "usage_note": "4ª declinação; instituição da República.",
                "themes": ["República Romana"],
            },
            {
                "term": "populus",
                "translation": "povo",
                "example": "Senatus populusque Romanus.",
                "example_translation": "O senado e o povo romano.",
                "usage_note": "Fórmula SPQR; -que = e.",
                "themes": ["República Romana"],
            },
            {
                "term": "virtus",
                "translation": "virtude / coragem",
                "example": "Virtus militum magna est.",
                "example_translation": "A coragem dos soldados é grande.",
                "usage_note": "3ª declinação; genitivo virtutis.",
                "themes": ["Vocabulário moral clássico"],
            },
            {
                "term": "gratia",
                "translation": "favor / agradecimento",
                "example": "Gratias tibi ago.",
                "example_translation": "Dou-te graças / obrigado.",
                "usage_note": "Na pronúncia clássica reconstruída: ti = /ti/ (não /tsi/).",
                "themes": ["Alfabeto e pronúncia clássica"],
            },
            {
                "term": "ratio",
                "translation": "razão / cálculo",
                "example": "Ratio clara est.",
                "example_translation": "A razão é clara.",
                "usage_note": "Na pronúncia clássica reconstruída: /ˈra.ti.o/.",
                "themes": ["Alfabeto e pronúncia clássica"],
            },
            {
                "term": "regina",
                "translation": "rainha",
                "example": "Regina in urbe habitat.",
                "example_translation": "A rainha mora na cidade.",
                "usage_note": "Na pronúncia clássica reconstruída: g=/g/ → /reˈgi.na/.",
                "themes": ["Alfabeto e pronúncia clássica"],
            },
        ],
        BAND_INTERMEDIATE: [
            {
                "term": "res publica",
                "translation": "república / coisa pública",
                "example": "Res publica in periculo est.",
                "example_translation": "A república está em perigo.",
                "usage_note": "Expressão política clássica (Cícero, Salústio).",
                "themes": ["República Romana", "Prosa clássica"],
            },
            {
                "term": "oratio",
                "translation": "discurso",
                "example": "Cicero orationem habuit.",
                "example_translation": "Cícero proferiu um discurso.",
                "usage_note": "Gênero central da prosa clássica.",
                "themes": ["Prosa clássica"],
            },
            {
                "term": "imperium",
                "translation": "poder de mando / império",
                "example": "Imperium populi Romani.",
                "example_translation": "O poder do povo romano.",
                "usage_note": "Conceito político e militar.",
                "themes": ["Início do Império"],
            },
            {
                "term": "philosophia",
                "translation": "filosofia",
                "example": "Philosophia vitae magistra.",
                "example_translation": "A filosofia é mestra da vida.",
                "usage_note": "Na pronúncia clássica reconstruída: ph ≈ /pʰ/.",
                "themes": ["Alfabeto e pronúncia clássica", "Prosa clássica"],
            },
            {
                "term": "angelus",
                "translation": "mensageiro / anjo",
                "example": "Angelus nuntium fert.",
                "example_translation": "O mensageiro traz a notícia.",
                "usage_note": "Na pronúncia clássica reconstruída: g=/g/ (não /dʒ/).",
                "themes": ["Alfabeto e pronúncia clássica"],
            },
            {
                "term": "sanctus",
                "translation": "sagrado / santo",
                "example": "Locus sanctus est.",
                "example_translation": "O lugar é sagrado.",
                "usage_note": "Na pronúncia clássica reconstruída: c=/k/.",
                "themes": ["Alfabeto e pronúncia clássica"],
            },
        ],
        BAND_UPPER: [
            {
                "term": "auctoritas",
                "translation": "autoridade / prestígio",
                "example": "Auctoritas senatus magna erat.",
                "example_translation": "A autoridade do senado era grande.",
                "usage_note": "Conceito político republicano.",
                "themes": ["República Romana"],
            },
            {
                "term": "dignitas",
                "translation": "dignidade / prestígio",
                "example": "Dignitatem suam defendit.",
                "example_translation": "Defendeu a própria dignidade.",
                "usage_note": "Tema recorrente em Cícero.",
                "themes": ["Prosa clássica"],
            },
            {
                "term": "libertas",
                "translation": "liberdade",
                "example": "Libertas populi Romani.",
                "example_translation": "A liberdade do povo romano.",
                "usage_note": "Ideal republicano.",
                "themes": ["República Romana"],
            },
            {
                "term": "ecclesia",
                "translation": "assembleia / reunião",
                "example": "Ecclesia populi convocata est.",
                "example_translation": "A assembleia do povo foi convocada.",
                "usage_note": "Na pronúncia clássica reconstruída: /ekˈkle.si.a/ (c=/k/). Sentido clássico ≠ litúrgico.",
                "themes": ["Alfabeto e pronúncia clássica"],
            },
            {
                "term": "credo",
                "translation": "creio / confio",
                "example": "Tibi credo.",
                "example_translation": "Confio em ti.",
                "usage_note": "Na pronúncia clássica reconstruída: /ˈkre.do/ (c=/k/).",
                "themes": ["Alfabeto e pronúncia clássica"],
            },
            {
                "term": "mos maiorum",
                "translation": "costume dos antepassados",
                "example": "Mos maiorum servandus est.",
                "example_translation": "O costume dos antepassados deve ser preservado.",
                "usage_note": "Norma social da República.",
                "themes": ["República Romana", "Prosa clássica"],
            },
        ],
    }
}

READING_TEXTS: dict[str, dict[str, dict[str, object]]] = {
    "la-classical": {
        BAND_BEGINNER: {
            "title": "In foro",
            "text": (
                "Marcus in foro ambulat. Amicum videt et salutat. "
                "Amicus respondet: Salve, Marce. Quid agis hodie?"
            ),
            "note": "Diálogo cotidiano em Roma; vocativo e presente.",
        },
        BAND_ELEMENTARY: {
            "title": "De via Appia",
            "text": (
                "Via Appia a Roma Capuam ducit. Multae carinae et milites "
                "per viam pergunt. Caelum serenum est; labor longus."
            ),
            "note": "Prosa pedagógica sobre a Via Ápia; acusativos de direção.",
        },
        BAND_INTERMEDIATE: {
            "title": "De re publica (excerptum pedagogicum)",
            "text": (
                "Res publica populi Romani legibus et auctoritate senatus nititur. "
                "Si cives virtutem et iustitiam colunt, urbs firma manet. "
                "Cicero saepe de libertate et dignitate disputavit."
            ),
            "note": "Prosa graduada inspirada em temas ciceronianos (domínio pedagógico).",
        },
        BAND_UPPER: {
            "title": "De bello et pace",
            "text": (
                "Bellum gerere facile est; pacem firmam servare difficile. "
                "Duces qui solum victoriam quaerunt saepe rem publicam perdunt. "
                "Sapientia et temperantia plus valent quam arma sola."
            ),
            "note": "Prosa argumentativa; subordinadas e abstração moral.",
        },
    }
}

LISTENING_SCRIPTS: dict[str, dict[str, dict[str, object]]] = {
    "la-classical": {
        BAND_BEGINNER: {
            "transcript": "Salve, amice. Quid agis? Bene ago, gratias.",
            "speaking_rate": "lenta, com pausas claras",
            "note": "Na pronúncia clássica reconstruída: v≈/w/, c=/k/. Áudio em modo de teste (speechSynthesis).",
        },
        BAND_ELEMENTARY: {
            "transcript": "Caesar in Gallia pugnat. Milites fortes sunt.",
            "speaking_rate": "moderada",
            "note": "Na pronúncia clássica reconstruída: Caesar ≈ /ˈkae̯.sar/ (não eclesiástico).",
        },
        BAND_INTERMEDIATE: {
            "transcript": (
                "Cicero orationem in foro habet. Cives attentē audiunt. "
                "Res publica in periculo esse videtur."
            ),
            "speaking_rate": "natural de prosa",
            "note": "Escuta de prosa política; c e g duros.",
        },
        BAND_UPPER: {
            "transcript": (
                "Libertas sine lege ruina est. Mos maiorum et auctoritas "
                "senatus rem publicam servant."
            ),
            "speaking_rate": "contínua, declamação",
            "note": "Densidade lexical republicana; validação auditiva humana pendente.",
        },
    }
}

WRITING_SCRIPT_HINTS: dict[str, list[str]] = {
    "la-classical": [
        "Use latim clássico (ortografia e vocabulário da prosa republicana/imperial inicial)",
        "Na pronúncia clássica reconstruída: c/g duros, v≈/w/; não misture regras eclesiásticas",
        "Indique caso e função quando a ambiguidade impedir a compreensão",
    ]
}

GRAMMAR_EXAMPLES: dict[str, dict[str, list[dict[str, str]]]] = {
    "la-classical": {
        BAND_BEGINNER: [
            {"sentence": "Quid est nomen tuum?", "translation": "Qual é o seu nome?"},
            {"sentence": "Puella rosam amat.", "translation": "A menina ama a rosa."},
            {"sentence": "Marcus amicum salutat.", "translation": "Marco saúda o amigo."},
        ],
        BAND_ELEMENTARY: [
            {"sentence": "Heri in foro fui.", "translation": "Ontem estive no fórum."},
            {"sentence": "Saepe libros lego.", "translation": "Muitas vezes leio livros."},
            {"sentence": "Milites urbem viderunt.", "translation": "Os soldados viram a cidade."},
        ],
        BAND_INTERMEDIATE: [
            {"sentence": "Romae ter fui.", "translation": "Estive em Roma três vezes."},
            {"sentence": "Caesar Galliam vicit.", "translation": "César venceu a Gália."},
            {"sentence": "Ab urbe condita multi anni fluxerunt.", "translation": "Desde a fundação da cidade passaram muitos anos."},
        ],
        BAND_UPPER: [
            {"sentence": "Si hoc scivissemus, melius egissemus.", "translation": "Se soubéssemos isto, teríamos agido melhor."},
            {"sentence": "Utinam pax firma sit.", "translation": "Oxalá a paz seja firme."},
            {"sentence": "Haec, ut opinor, melior via est.", "translation": "Esta, na minha opinião, é a melhor via."},
        ],
    }
}

GRAMMAR_EXERCISES: dict[str, dict[str, list[dict]]] = {
    "la-classical": {
        BAND_BEGINNER: [
            {
                "prompt": "Puella ____ amat.",
                "options": ["rosam", "rosae", "rosa"],
                "answer": "rosam",
                "rationale": "Objeto direto: acusativo singular da 1ª declinação.",
                "option_rationales": {
                    "rosam": "Acusativo singular — objeto de amat.",
                    "rosae": "Genitivo/dativo — não cabe como objeto direto.",
                    "rosa": "Nominativo/ablativo — não é o objeto aqui.",
                },
            }
        ],
        BAND_ELEMENTARY: [
            {
                "prompt": "Milites ____ viderunt.",
                "options": ["urbem", "urbis", "urbi"],
                "answer": "urbem",
                "rationale": "Acusativo objeto de viderunt.",
                "option_rationales": {
                    "urbem": "Acusativo singular da 3ª declinação.",
                    "urbis": "Genitivo — 'da cidade'.",
                    "urbi": "Dativo — 'à cidade'.",
                },
            }
        ],
        BAND_INTERMEDIATE: [
            {
                "prompt": "Na pronúncia clássica reconstruída, \"Caesar\" soa aproximadamente como:",
                "options": ["káe-sar", "ché-sar", "sé-sar"],
                "answer": "káe-sar",
                "rationale": "C = /k/ e ae = ditongo /ae̯/; não a leitura eclesiástica /tʃ/.",
                "option_rationales": {
                    "káe-sar": "Pronúncia clássica reconstruída.",
                    "ché-sar": "Aproximação eclesiástica — outra modalidade (`la`).",
                    "sé-sar": "Não corresponde à reconstrução adotada.",
                },
            }
        ],
        BAND_UPPER: [
            {
                "prompt": "Si hoc ____, melius egissemus.",
                "options": ["scivissemus", "scivimus", "sciebamus"],
                "answer": "scivissemus",
                "rationale": "Contrafactual passado: si + mais-que-perfeito do subjuntivo.",
                "option_rationales": {
                    "scivissemus": "Mais-que-perfeito do subjuntivo na prótase irreal.",
                    "scivimus": "Perfeito do indicativo — fato, não hipótese irreal.",
                    "sciebamus": "Imperfeito do indicativo — hábito/estado.",
                },
            }
        ],
    }
}

PRONUNCIATION_FOCUS: dict[str, list[dict[str, str]]] = {
    "la-classical": [
        {
            "sound": "c = /k/ em todas as posições",
            "why_hard": "A modalidade eclesiástica (`la`) usa /tʃ/ ante e/i/ae/oe.",
            "how_to_produce": "Como 'k': caelum ≈ /ˈkae̯.lum/; Cicero ≈ /ˈki.ke.ro/.",
        },
        {
            "sound": "g = /g/ em todas as posições",
            "why_hard": "No eclesiástico, g ante e/i vira /dʒ/.",
            "how_to_produce": "G duro: regina ≈ /reˈgi.na/; angelus ≈ /ˈan.ge.lus/.",
        },
        {
            "sound": "v consonantal ≈ /w/",
            "why_hard": "O eclesiástico usa /v/; o português sugere /v/.",
            "how_to_produce": "Como 'u' semivogal: via ≈ /ˈwi.a/; vinum ≈ /ˈwi.num/.",
        },
        {
            "sound": "ae = /ae̯/, oe = /oe̯/",
            "why_hard": "No eclesiástico ae/oe frequentemente monotongam para /e/.",
            "how_to_produce": "Ditongo claro: Caesar ≈ /ˈkae̯.sar/.",
        },
        {
            "sound": "ti + vogal sem palatalização eclesiástica",
            "why_hard": "No eclesiástico, ti+vogal pode soar /tsi/.",
            "how_to_produce": "gratia ≈ /ˈgra.ti.a/; ratio ≈ /ˈra.ti.o/.",
        },
    ]
}


def register(into: dict[str, Any]) -> None:
    """Mescla o conteúdo de `la-classical` nos dicionários do lesson_bank."""
    into["VOCABULARY"].update(VOCABULARY)
    into["READING_TEXTS"].update(READING_TEXTS)
    into["LISTENING_SCRIPTS"].update(LISTENING_SCRIPTS)
    into["WRITING_SCRIPT_HINTS"].update(WRITING_SCRIPT_HINTS)
    into["GRAMMAR_EXAMPLES"].update(GRAMMAR_EXAMPLES)
    into["GRAMMAR_EXERCISES"].update(GRAMMAR_EXERCISES)
    into["PRONUNCIATION_FOCUS"].update(PRONUNCIATION_FOCUS)
