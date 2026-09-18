"""Conteúdo mock/banco para latim eclesiástico (`la`).

Foco: leitura, morfologia, liturgia/Vulgata e composição escrita.
Fala/escuta existem no banco (compatibilidade de skills), mas a estratégia
pedagógica trata-as como secundárias.
"""

from __future__ import annotations

from typing import Any

BAND_BEGINNER = "beginner"
BAND_ELEMENTARY = "elementary"
BAND_INTERMEDIATE = "intermediate"
BAND_UPPER = "upper"

VOCABULARY: dict[str, dict[str, list[dict[str, str]]]] = {
    "la": {
        BAND_BEGINNER: [
            {
                "term": "Dominus",
                "translation": "Senhor",
                "example": "Dominus vobiscum.",
                "example_translation": "O Senhor esteja convosco.",
                "usage_note": "Vocativo/nominativo frequente na liturgia.",
            },
            {
                "term": "amen",
                "translation": "assim seja / amém",
                "example": "Amen, amen dico vobis.",
                "example_translation": "Em verdade, em verdade vos digo.",
                "usage_note": "Hebraísmo preservado na Vulgata e na Missa.",
            },
            {
                "term": "pax",
                "translation": "paz",
                "example": "Pax vobis.",
                "example_translation": "A paz esteja convosco.",
                "usage_note": "Substantivo feminino da 3ª declinação.",
            },
            {
                "term": "gratia",
                "translation": "graça",
                "example": "Ave, gratia plena.",
                "example_translation": "Ave, cheia de graça.",
                "usage_note": "1ª declinação; ablativo 'gratia' = 'por graça'.",
            },
            {
                "term": "oratio",
                "translation": "oração / discurso",
                "example": "Oremus. Oratio.",
                "example_translation": "Oremos. Oração.",
                "usage_note": "Na Missa introduz a coleta.",
            },
            {
                "term": "credo",
                "translation": "creio",
                "example": "Credo in unum Deum.",
                "example_translation": "Creio em um só Deus.",
                "usage_note": "1ª pessoa; dá nome ao Credo.",
            },
        ],
        BAND_ELEMENTARY: [
            {
                "term": "misericordia",
                "translation": "misericórdia",
                "example": "Kyrie, eleison — Domine, miserere.",
                "example_translation": "Senhor, tende piedade.",
                "usage_note": "Tema central dos salmos penitenciais.",
            },
            {
                "term": "verbum",
                "translation": "palavra / Verbo",
                "example": "In principio erat Verbum.",
                "example_translation": "No princípio era o Verbo.",
                "usage_note": "Jo 1,1 — neutro da 2ª declinação.",
            },
            {
                "term": "lux",
                "translation": "luz",
                "example": "Ego sum lux mundi.",
                "example_translation": "Eu sou a luz do mundo.",
                "usage_note": "3ª declinação; genitivo 'lucis'.",
            },
            {
                "term": "fides",
                "translation": "fé",
                "example": "Fides tua te salvum fecit.",
                "example_translation": "A tua fé te salvou.",
                "usage_note": "5ª declinação (rara, mas frequente).",
            },
            {
                "term": "caro",
                "translation": "carne",
                "example": "Et Verbum caro factum est.",
                "example_translation": "E o Verbo se fez carne.",
                "usage_note": "3ª declinação; genitivo 'carnis'.",
            },
            {
                "term": "saeculum",
                "translation": "século / era / mundo",
                "example": "Per omnia saecula saeculorum.",
                "example_translation": "Por todos os séculos dos séculos.",
                "usage_note": "Fórmula doxológica litúrgica.",
            },
        ],
        BAND_INTERMEDIATE: [
            {
                "term": "testamentum",
                "translation": "aliança / testamento",
                "example": "Hic est enim calix Novi Testamenti.",
                "example_translation": "Este é o cálice do Novo Testamento.",
                "usage_note": "Vocabulário eucarístico e bíblico.",
            },
            {
                "term": "iustitia",
                "translation": "justiça",
                "example": "Beati qui esuriunt et sitiunt iustitiam.",
                "example_translation": "Bem-aventurados os que têm fome e sede de justiça.",
                "usage_note": "Ortografia eclesiástica: iustitia (não justitia clássica moderna).",
            },
            {
                "term": "regnum",
                "translation": "reino",
                "example": "Adveniat regnum tuum.",
                "example_translation": "Venha o vosso reino.",
                "usage_note": "Do Pai-Nosso litúrgico.",
            },
            {
                "term": "voluntas",
                "translation": "vontade",
                "example": "Fiat voluntas tua.",
                "example_translation": "Seja feita a vossa vontade.",
                "usage_note": "3ª declinação; ablativo 'voluntate'.",
            },
            {
                "term": "peccatum",
                "translation": "pecado",
                "example": "Dimitte nobis debita nostra.",
                "example_translation": "Perdoai-nos as nossas dívidas/ofensas.",
                "usage_note": "Par paralelo: peccatum / delictum / debitum.",
            },
            {
                "term": "spiritu",
                "translation": "espírito (ablativo)",
                "example": "In Spiritu Sancto.",
                "example_translation": "No Espírito Santo.",
                "usage_note": "Ablativo de 'spiritus' (4ª declinação).",
            },
        ],
        BAND_UPPER: [
            {
                "term": "hypostasis",
                "translation": "hipóstase / pessoa (teologia)",
                "example": "Tres Personae, una Substantia.",
                "example_translation": "Três Pessoas, uma Substância.",
                "usage_note": "Vocabulário teológico latino medieval/eclesiástico.",
            },
            {
                "term": "incarnatio",
                "translation": "encarnação",
                "example": "Et incarnatus est de Spiritu Sancto.",
                "example_translation": "E encarnou pelo Espírito Santo.",
                "usage_note": "Do Credo niceno-constantinopolitano.",
            },
            {
                "term": "transsubstantiatio",
                "translation": "transubstanciação",
                "example": "Terminus scholasticus de Eucharistia.",
                "example_translation": "Termo escolástico sobre a Eucaristia.",
                "usage_note": "Latim teológico tardio; útil em textos conciliares.",
            },
            {
                "term": "aedificatio",
                "translation": "edificação (espiritual)",
                "example": "Omnia ad aedificationem fiant.",
                "example_translation": "Tudo se faça para edificação.",
                "usage_note": "1 Cor — uso paulino na Vulgata.",
            },
            {
                "term": "praedestinatio",
                "translation": "predestinação",
                "example": "Disputatio de praedestinatione apud Patres.",
                "example_translation": "Disputa sobre a predestinação entre os Padres.",
                "usage_note": "Registro patrístico/escolástico.",
            },
            {
                "term": "communicatio idiomatum",
                "translation": "comunicação dos idiomas (Cristologia)",
                "example": "Communicatio idiomatum in Christo.",
                "example_translation": "Comunicação das propriedades em Cristo.",
                "usage_note": "Expressão técnica da teologia latina.",
            },
        ],
    }
}

READING_TEXTS: dict[str, dict[str, dict[str, object]]] = {
    "la": {
        BAND_BEGINNER: {
            "title": "Dominus vobiscum",
            "text": (
                "Sacerdos dicit: Dominus vobiscum. "
                "Populus respondet: Et cum spiritu tuo. "
                "Deinde dicitur: Oremus."
            ),
            "note": "Diálogo litúrgico curto, presente e vocabulário da Missa.",
        },
        BAND_ELEMENTARY: {
            "title": "Pater noster (excerptum)",
            "text": (
                "Pater noster, qui es in caelis, sanctificetur nomen tuum. "
                "Adveniat regnum tuum. Fiat voluntas tua, sicut in caelo et in terra. "
                "Panem nostrum cotidianum da nobis hodie."
            ),
            "note": "Texto litúrgico canônico; subjuntivos de desejo.",
        },
        BAND_INTERMEDIATE: {
            "title": "In principio (Ioannes 1)",
            "text": (
                "In principio erat Verbum, et Verbum erat apud Deum, et Deus erat Verbum. "
                "Hoc erat in principio apud Deum. Omnia per ipsum facta sunt. "
                "Et Verbum caro factum est, et habitavit in nobis."
            ),
            "note": "Vulgata joânica; perfeito e estruturas teológicas.",
        },
        BAND_UPPER: {
            "title": "De fide et ratione (excerptum scholasticum)",
            "text": (
                "Fides non destruit rationem, sed eam perficit. "
                "Ea quae naturaliter cognosci possunt non contradicunt his quae per "
                "revelationem traduntur. Unde theologia utitur et auctoritate et "
                "argumentatione, dummodo ordo servetur: prius credere, deinde intelligere."
            ),
            "note": "Prosa escolástica; orações subordinadas e abstração.",
        },
    }
}

LISTENING_SCRIPTS: dict[str, dict[str, dict[str, object]]] = {
    "la": {
        BAND_BEGINNER: {
            "transcript": "Dominus vobiscum. Et cum spiritu tuo. Oremus.",
            "speaking_rate": "lenta, com pausas litúrgicas",
            "note": "Respostas da Missa — escuta secundária no latim eclesiástico.",
        },
        BAND_ELEMENTARY: {
            "transcript": (
                "Gloria in excelsis Deo. Et in terra pax hominibus bonae voluntatis."
            ),
            "speaking_rate": "moderada, estilo coral",
            "note": "Glória — ritmo eclesiástico (c = /tʃ/ diante de e/i).",
        },
        BAND_INTERMEDIATE: {
            "transcript": (
                "Ave Maria, gratia plena, Dominus tecum. Benedicta tu in mulieribus, "
                "et benedictus fructus ventris tui, Iesus."
            ),
            "speaking_rate": "natural de oração",
            "note": "Ave Maria — vocabulário mariano.",
        },
        BAND_UPPER: {
            "transcript": (
                "Credo in unum Deum, Patrem omnipotentem, factorem caeli et terrae, "
                "visibilium omnium et invisibilium. Et in unum Dominum Iesum Christum."
            ),
            "speaking_rate": "contínua, proclamação",
            "note": "Início do Credo — densidade sintática.",
        },
    }
}

WRITING_SCRIPT_HINTS: dict[str, list[str]] = {
    "la": [
        "Use latim eclesiástico (ortografia com ae/oe quando clássico exigir, mas pronúncia eclesiástica)",
        "Prefira vocabulário litúrgico/bíblico da Vulgata quando o tema for religioso",
        "Indique caso e função quando a ambiguidade impedir a compreensão",
    ]
}

GRAMMAR_EXAMPLES: dict[str, dict[str, list[dict[str, str]]]] = {
    "la": {
        BAND_BEGINNER: [
            {"sentence": "Quid est nomen tuum?", "translation": "Qual é o seu nome?"},
            {"sentence": "Dominus vobiscum.", "translation": "O Senhor esteja convosco."},
            {"sentence": "Deo gratias.", "translation": "Graças a Deus."},
        ],
        BAND_ELEMENTARY: [
            {"sentence": "Heri oravi usque ad vesperam.", "translation": "Ontem orei até a tarde."},
            {"sentence": "Saepe in ecclesia oro.", "translation": "Muitas vezes oro na igreja."},
            {"sentence": "Vocavit et deinde discessit.", "translation": "Chamou e depois partiu."},
        ],
        BAND_INTERMEDIATE: [
            {"sentence": "Romae ter fui.", "translation": "Estive em Roma três vezes."},
            {"sentence": "Anno Domini MMXIX Romam veni.", "translation": "No ano do Senhor 2019 vim a Roma."},
            {"sentence": "Ab mense Martio hic laboro.", "translation": "Desde março trabalho aqui."},
        ],
        BAND_UPPER: [
            {"sentence": "Hoc fortasse moram explicet.", "translation": "Isso talvez explique o atraso."},
            {"sentence": "Si scivissemus, exspectavissemus.", "translation": "Se soubéssemos, teríamos esperado."},
            {"sentence": "Haec, ut argumentor, melior optio est.", "translation": "Esta, argumento eu, é a melhor opção."},
        ],
    }
}

GRAMMAR_EXERCISES: dict[str, dict[str, list[dict]]] = {
    "la": {
        BAND_BEGINNER: [
            {
                "prompt": "____ vobiscum.",
                "options": ["Dominus", "Domine", "Domini"],
                "answer": "Dominus",
                "rationale": "Na saudação litúrgica usa-se nominativo 'Dominus'.",
                "option_rationales": {
                    "Dominus": "Nominativo: sujeito da frase litúrgica.",
                    "Domine": "Vocativo — usado em 'Domine, miserere', não aqui.",
                    "Domini": "Genitivo — 'do Senhor'.",
                },
            }
        ],
        BAND_ELEMENTARY: [
            {
                "prompt": "In principio erat ____.",
                "options": ["Verbum", "Verbi", "Verbo"],
                "answer": "Verbum",
                "rationale": "Jo 1,1: nominativo/acusativo neutro 'Verbum' como sujeito.",
                "option_rationales": {
                    "Verbum": "Forma correta do sujeito em Jo 1,1.",
                    "Verbi": "Genitivo — 'do Verbo'.",
                    "Verbo": "Dativo/ablativo — não cabe aqui.",
                },
            }
        ],
        BAND_INTERMEDIATE: [
            {
                "prompt": "Et Verbum ____ factum est.",
                "options": ["caro", "carnis", "carnem"],
                "answer": "caro",
                "rationale": "Predicativo: 'caro factum est' — nominativo.",
                "option_rationales": {
                    "caro": "Nominativo predicativo com 'factum est'.",
                    "carnis": "Genitivo.",
                    "carnem": "Acusativo — exigiria outro verbo transitivo.",
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
                    "scivissemus": "Perfeito/mais-que-perfeito do subjuntivo na prótase irreal.",
                    "scivimus": "Perfeito do indicativo — fato, não hipótese irreal.",
                    "sciebamus": "Imperfeito do indicativo — hábito/estado, não contrafactual.",
                },
            }
        ],
    }
}

PRONUNCIATION_FOCUS: dict[str, list[dict[str, str]]] = {
    "la": [
        {
            "sound": "c + e/i/ae/oe → /tʃ/ (eclesiástico)",
            "why_hard": "No clássico escolar muitas vezes se ensina /k/; na Igreja soa como italiano.",
            "how_to_produce": "Como 'tché': caelum ≈ 'ché-lum'; Cecilia ≈ 'Che-chí-li-a'.",
        },
        {
            "sound": "g + e/i → /dʒ/",
            "why_hard": "Difere da leitura 'restituída' clássica.",
            "how_to_produce": "Como 'dj': Regina ≈ 'Re-dji-na'; angelus ≈ 'án-dje-lus'.",
        },
        {
            "sound": "v = /v/ (não /w/)",
            "why_hard": "A restituta clássica usa /w/; a eclesiástica usa /v/.",
            "how_to_produce": "Como o 'v' do português: Verbum, vita, vobis.",
        },
    ]
}


def register(into: dict[str, Any]) -> None:
    """Mescla o conteúdo de `la` nos dicionários do lesson_bank principal."""
    into["VOCABULARY"].update(VOCABULARY)
    into["READING_TEXTS"].update(READING_TEXTS)
    into["LISTENING_SCRIPTS"].update(LISTENING_SCRIPTS)
    into["WRITING_SCRIPT_HINTS"].update(WRITING_SCRIPT_HINTS)
    into["GRAMMAR_EXAMPLES"].update(GRAMMAR_EXAMPLES)
    into["GRAMMAR_EXERCISES"].update(GRAMMAR_EXERCISES)
    into["PRONUNCIATION_FOCUS"].update(PRONUNCIATION_FOCUS)
