"""Temas comunicativos por nível CEFR e por idioma, consumidos pelo gerador.

O cronograma precisa de um eixo temático: sem ele, "semana 7" não significa
nada além de "sete semanas depois". Cada semana recebe um tema comunicativo
(o que o aluno consegue *fazer* ao final dela) e cada bloco do dia recebe um
tópico derivado desse tema.

LIMITAÇÃO DECLARADA: a progressão temática segue os descritores gerais do CEFR
e as prioridades de `docs/language-strategies.md`, mas não passou por validação
pedagógica formal. É um esqueleto coerente e auditável, não um currículo
certificado.

Os temas por idioma **precedem** os temas base: em japonês e mandarim as
primeiras semanas são de sistema de escrita e de tons, que não existem como
etapa nos idiomas de alfabeto latino.
"""

from __future__ import annotations

from app.core.curriculum import BlockSkill
from app.core.levels import LEVEL_ORDER, CEFRLevel

#: Temas base por nível. Ordem = progressão dentro do nível.
BASE_THEMES: dict[str, list[str]] = {
    CEFRLevel.PRE_A1: [
        "Sons e alfabeto do idioma",
        "Cumprimentos e cortesia",
        "Números, horas e datas",
        "Objetos do dia a dia e cores",
        "Pessoas da família",
        "Comida e bebida básicas",
        "Lugares da cidade",
        "Pedir ajuda e repetição",
    ],
    CEFRLevel.A1: [
        "Apresentações e rotina",
        "Família e pessoas próximas",
        "Comida e restaurante",
        "Casa e moradia",
        "Direções e transporte",
        "Compras e dinheiro",
        "Tempo e clima",
        "Trabalho e estudo",
        "Lazer e hobbies",
        "Corpo e saúde básica",
    ],
    CEFRLevel.A2: [
        "Rotina detalhada e frequência",
        "Passado e memórias",
        "Viagem e hospedagem",
        "Serviços e pequenos problemas",
        "Planos e futuro próximo",
        "Descrever pessoas e lugares",
        "Telefone, mensagens e recados",
        "Comparações e preferências",
        "Convites, festas e combinados",
        "Contar uma história curta",
    ],
    CEFRLevel.B1: [
        "Opinião e justificativa",
        "Trabalho e carreira",
        "Saúde e bem-estar",
        "Notícias e atualidades",
        "Educação e formação",
        "Tecnologia no dia a dia",
        "Meio ambiente e hábitos",
        "Cultura e entretenimento",
        "Relacionamentos e conflitos",
        "Resolver problemas e reclamar",
    ],
    CEFRLevel.B2: [
        "Argumentar e refutar",
        "Negociação e mercado de trabalho",
        "Ciência, dados e evidência",
        "Mídia, fontes e desinformação",
        "Sociedade e políticas públicas",
        "Ética e dilemas",
        "Economia pessoal e global",
        "Arte, crítica e interpretação",
        "Mudanças sociais e gerações",
        "Apresentar e defender uma ideia",
    ],
}

#: Temas que precedem os base, por idioma e nível. Vêm de
#: `docs/language-strategies.md`: japonês e mandarim exigem etapas de escrita e
#: de tom que não existem nos idiomas de alfabeto latino.
LANGUAGE_THEMES: dict[str, dict[str, list[str]]] = {
    "en": {
        CEFRLevel.A2: ["Sotaques e inglês falado real"],
        CEFRLevel.B1: ["Leitura acadêmica e científica"],
    },
    "es-ES": {
        CEFRLevel.A1: ["Vogais puras e ritmo do espanhol"],
        CEFRLevel.A2: ["Vosotros e registro na Espanha"],
        CEFRLevel.B1: ["Espanha × América Latina: o que muda"],
    },
    "fr": {
        CEFRLevel.PRE_A1: ["Sons do francês que não existem em português"],
        CEFRLevel.A1: ["Gênero gramatical e artigos", "Liaison e ritmo da fala"],
        CEFRLevel.A2: ["Conjugação: os tempos que você mais vai usar"],
    },
    "ja": {
        CEFRLevel.PRE_A1: [
            "Hiragana — leitura e escrita",
            "Katakana — leitura e escrita",
            "Partículas essenciais (は, を, に)",
        ],
        CEFRLevel.A1: ["Estrutura da frase japonesa (SOV)", "Primeiros kanji do cotidiano"],
        CEFRLevel.A2: ["Níveis de formalidade (です/ます × forma casual)"],
        CEFRLevel.B1: ["Kanji de textos jornalísticos"],
    },
    "zh-CN": {
        CEFRLevel.PRE_A1: [
            "Pinyin e os quatro tons",
            "Pares tonais e sílabas difíceis",
            "Primeiros hanzi e traços",
        ],
        CEFRLevel.A1: ["Classificadores (量词)", "Estrutura da frase e partícula 了"],
        CEFRLevel.A2: ["Hanzi compostos e radicais"],
        CEFRLevel.B1: ["Chengyu e expressões de quatro caracteres"],
    },
}


def themes_for(language_code: str, level: str) -> list[str]:
    """Temas do nível para o idioma: específicos primeiro, depois os base."""
    specific = LANGUAGE_THEMES.get(language_code, {}).get(level, [])
    base = BASE_THEMES.get(level, BASE_THEMES[CEFRLevel.A1])
    return [*specific, *base]


def weekly_theme(language_code: str, level: str, index: int) -> str:
    """Tema da `index`-ésima semana passada naquele nível (0-based).

    Dá a volta na lista quando o aluno passa mais semanas no nível do que há
    temas — repetir um tema com o nível já consolidado é melhor do que inventar
    um tema fora da progressão.
    """
    themes = themes_for(language_code, level)
    return themes[index % len(themes)]


# ---------------------------------------------------------------------------
# Tópico do bloco
# ---------------------------------------------------------------------------

#: Recorte de cada bloco dentro do tema da semana.
SKILL_ANGLES: dict[str, str] = {
    BlockSkill.VOCABULARY: "vocabulário essencial",
    BlockSkill.GRAMMAR: "estruturas-chave",
    BlockSkill.PRONUNCIATION: "sons e ritmo",
    BlockSkill.LISTENING: "escuta ativa",
    BlockSkill.READING: "leitura guiada",
    BlockSkill.CONVERSATION: "conversa aplicada",
    BlockSkill.WRITING: "produção escrita",
    BlockSkill.REVIEW: "revisão espaçada",
}

#: Progressão do sistema de escrita, por idioma e semana de estudo.
#: Japonês: kana nas duas primeiras semanas, kanji progressivo depois.
#: Mandarim: hanzi progressivo desde o início (o pinyin é apoio, não destino).
def script_focus(language_code: str, week_number: int) -> str | None:
    if language_code == "ja":
        if week_number <= 1:
            return "kana (hiragana)"
        if week_number == 2:
            return "kana (katakana)"
        return f"kanji — lote {min((week_number - 2), 24)}"
    if language_code == "zh-CN":
        return f"hanzi — lote {min(week_number, 26)}"
    return None


#: Foco fonético que abre o cronograma. Mandarim trabalha tons desde o dia 1
#: (`docs/language-strategies.md`: "não adiar o ensino dos tons").
PRONUNCIATION_OPENING: dict[str, str] = {
    "zh-CN": "tons (1º ao 4º) e neutro",
    "ja": "duração vocálica e mora",
    "fr": "vogais nasais e /y/",
    "es-ES": "/θ/ e vibrante múltiplo",
    "en": "/θ/, /ð/ e vogais curtas × longas",
}


def block_topic(
    language_code: str,
    skill: str,
    theme: str,
    week_number: int,
) -> str:
    """Tópico concreto do bloco, derivado do tema da semana.

    É o que vai para o prompt da IA e para a busca no banco de conteúdo: sem
    ele o bloco seria só "vocabulário", igual em toda semana do cronograma.
    """
    angle = SKILL_ANGLES.get(skill, skill)

    if skill == BlockSkill.WRITING:
        script = script_focus(language_code, week_number)
        if script:
            return f"{theme} — escrita com {script}"

    if skill == BlockSkill.PRONUNCIATION and week_number <= 2:
        opening = PRONUNCIATION_OPENING.get(language_code)
        if opening:
            return f"{theme} — {opening}"

    return f"{theme} — {angle}"


def coverage_report() -> dict[str, list[str]]:
    """Níveis sem tema por idioma. Usado por teste: uma célula vazia aqui vira
    uma semana sem tema no cronograma do aluno."""
    gaps: dict[str, list[str]] = {}
    for language_code in ("en", "es-ES", "fr", "ja", "zh-CN"):
        missing = [
            level
            for level in LEVEL_ORDER
            if level in BASE_THEMES and not themes_for(language_code, level)
        ]
        if missing:
            gaps[language_code] = missing
    return gaps
