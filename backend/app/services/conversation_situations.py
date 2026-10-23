"""Situações de conversa por idioma-alvo.

O cenário principal está no idioma estudado. O texto em português é apoio
para pt-BR e não substitui o cenário.
"""

from __future__ import annotations

_BANDS = ("beginner", "elementary", "intermediate", "upper")


def _pack(rows: dict[str, tuple[str, str, str, str, str, str]]) -> dict[str, dict[str, str]]:
    packed = {}
    for band, (title, scenario, focus, title_pt, scenario_pt, focus_pt) in rows.items():
        packed[band] = {
            "title_target": title,
            "scenario_target": scenario,
            "focus_target": focus,
            "title_pt": title_pt,
            "scenario_pt": scenario_pt,
            "focus_pt": focus_pt,
        }
    return packed


SITUATIONS: dict[str, dict[str, dict[str, str]]] = {
    "en": _pack({
        "beginner": (
            "Introduce yourself",
            "You meet someone for the first time and introduce yourself.",
            "greetings and personal information",
            "Apresentar-se",
            "Você cumprimenta alguém que acabou de conhecer.",
            "cumprimentos e informação pessoal",
        ),
        "elementary": (
            "Order a meal",
            "You order food in a restaurant and ask for the bill.",
            "orders, preferences and the bill",
            "Pedir uma refeição",
            "Você pede comida em um restaurante e pergunta a conta.",
            "pedidos, preferências e conta",
        ),
        "intermediate": (
            "Tell a trip",
            "You tell a colleague about a recent trip.",
            "narrative and details",
            "Contar uma viagem",
            "Você conta a um colega uma viagem recente.",
            "narrativa e detalhes",
        ),
        "upper": (
            "Disagree politely",
            "You disagree politely in a work meeting and give a reason.",
            "opinion, reason and concession",
            "Discordar com educação",
            "Você discorda com educação numa reunião e dá um motivo.",
            "opinião, motivo e ressalva",
        ),
    }),
    "fr": _pack({
        "beginner": (
            "Se présenter",
            "Vous rencontrez quelqu'un pour la première fois et vous vous présentez.",
            "salutations et informations personnelles",
            "Apresentar-se",
            "Você cumprimenta alguém que acabou de conhecer.",
            "cumprimentos e informação pessoal",
        ),
        "elementary": (
            "Commander un repas",
            "Vous commandez un plat au restaurant et vous demandez l'addition.",
            "commandes, préférences et addition",
            "Pedir uma refeição",
            "Você pede comida em um restaurante e pergunta a conta.",
            "pedidos, preferências e conta",
        ),
        "intermediate": (
            "Défendre une opinion simple",
            "Vous n'êtes pas d'accord avec un collègue et vous expliquez pourquoi, poliment.",
            "opinion, raison et concession",
            "Defender uma opinião simples",
            "Você discorda de um colega e explica o motivo, com educação.",
            "opinião, motivo e ressalva",
        ),
        "upper": (
            "Nuancer un désaccord",
            "Dans une réunion, vous défendez votre avis et vous reconnaissez un argument contraire.",
            "argumentation et concession",
            "Matizar um desacordo",
            "Numa reunião, você defende seu ponto e reconhece um argumento contrário.",
            "argumentação e ressalva",
        ),
    }),
    "es-ES": _pack({
        "beginner": (
            "Presentarse",
            "Acabas de conocer a alguien y te presentas.",
            "saludos e información personal",
            "Apresentar-se",
            "Você cumprimenta alguém que acabou de conhecer.",
            "cumprimentos e informação pessoal",
        ),
        "elementary": (
            "Pedir la comida",
            "Pides la comida en un restaurante y preguntas por la cuenta.",
            "pedidos, preferencias y cuenta",
            "Pedir uma refeição",
            "Você pede comida em um restaurante e pergunta a conta.",
            "pedidos, preferências e conta",
        ),
        "intermediate": (
            "Contar un viaje",
            "Le cuentas a un compañero un viaje reciente.",
            "narración y detalles",
            "Contar uma viagem",
            "Você conta a um colega uma viagem recente.",
            "narrativa e detalhes",
        ),
        "upper": (
            "Discrepar con educación",
            "En una reunión discrepas con educación y das un motivo.",
            "opinión, motivo y concesión",
            "Discordar com educação",
            "Você discorda com educação numa reunião e dá um motivo.",
            "opinião, motivo e ressalva",
        ),
    }),
    "it": _pack({
        "beginner": (
            "Presentarsi",
            "Incontri qualcuno per la prima volta e ti presenti.",
            "saluti e informazioni personali",
            "Apresentar-se",
            "Você cumprimenta alguém que acabou de conhecer.",
            "cumprimentos e informação pessoal",
        ),
        "elementary": (
            "Ordinare al ristorante",
            "Ordini un piatto al ristorante e chiedi il conto.",
            "ordini, preferenze e conto",
            "Pedir uma refeição",
            "Você pede comida em um restaurante e pergunta a conta.",
            "pedidos, preferências e conta",
        ),
        "intermediate": (
            "Raccontare un viaggio",
            "Racconti a un collega un viaggio recente.",
            "narrazione e dettagli",
            "Contar uma viagem",
            "Você conta a um colega uma viagem recente.",
            "narrativa e detalhes",
        ),
        "upper": (
            "Dissentire con educazione",
            "In una riunione non sei d'accordo e spieghi il motivo, con educazione.",
            "opinione, motivo e concessione",
            "Discordar com educação",
            "Você discorda com educação numa reunião e dá um motivo.",
            "opinião, motivo e ressalva",
        ),
    }),
    "de": _pack({
        "beginner": (
            "Sich vorstellen",
            "Du lernst jemanden gerade kennen und stellst dich vor.",
            "Grüße und persönliche Angaben",
            "Apresentar-se",
            "Você cumprimenta alguém que acabou de conhecer.",
            "cumprimentos e informação pessoal",
        ),
        "elementary": (
            "Essen bestellen",
            "Du bestellst ein Gericht im Restaurant und fragst nach der Rechnung.",
            "Bestellung, Vorlieben und Rechnung",
            "Pedir uma refeição",
            "Você pede comida em um restaurante e pergunta a conta.",
            "pedidos, preferências e conta",
        ),
        "intermediate": (
            "Eine Reise erzählen",
            "Du erzählst einem Kollegen von einer kurzen Reise.",
            "Erzählung und Details",
            "Contar uma viagem",
            "Você conta a um colega uma viagem recente.",
            "narrativa e detalhes",
        ),
        "upper": (
            "Höflich widersprechen",
            "In einer Besprechung widersprichst du höflich und nennst einen Grund.",
            "Meinung, Grund und Einschränkung",
            "Discordar com educação",
            "Você discorda com educação numa reunião e dá um motivo.",
            "opinião, motivo e ressalva",
        ),
    }),
    "ja": _pack({
        "beginner": (
            "自己紹介",
            "初めて会った人に名前を言います。",
            "あいさつと個人情報",
            "Apresentar-se",
            "Você cumprimenta alguém que acabou de conhecer.",
            "cumprimentos e informação pessoal",
        ),
        "elementary": (
            "注文する",
            "レストランで料理を注文し、会計を尋ねます。",
            "注文、希望、会計",
            "Pedir uma refeição",
            "Você pede comida em um restaurante e pergunta a conta.",
            "pedidos, preferências e conta",
        ),
        "intermediate": (
            "旅行を話す",
            "同僚に最近の旅行について話します。",
            "物語と細部",
            "Contar uma viagem",
            "Você conta a um colega uma viagem recente.",
            "narrativa e detalhes",
        ),
        "upper": (
            "丁寧に反対する",
            "会議で丁寧に反対し、理由を述べます。",
            "意見、理由、譲歩",
            "Discordar com educação",
            "Você discorda com educação numa reunião e dá um motivo.",
            "opinião, motivo e ressalva",
        ),
    }),
    "zh-CN": _pack({
        "beginner": (
            "自我介绍",
            "你向刚认识的人介绍自己。",
            "问候和个人信息",
            "Apresentar-se",
            "Você cumprimenta alguém que acabou de conhecer.",
            "cumprimentos e informação pessoal",
        ),
        "elementary": (
            "点餐",
            "你在餐厅点餐，并询问账单。",
            "点餐、偏好和账单",
            "Pedir uma refeição",
            "Você pede comida em um restaurante e pergunta a conta.",
            "pedidos, preferências e conta",
        ),
        "intermediate": (
            "讲一次旅行",
            "你跟同事讲一次最近的旅行。",
            "叙述和细节",
            "Contar uma viagem",
            "Você conta a um colega uma viagem recente.",
            "narrativa e detalhes",
        ),
        "upper": (
            "礼貌地反对",
            "你在会议上礼貌地表示不同意见，并说明理由。",
            "观点、理由和让步",
            "Discordar com educação",
            "Você discorda com educação numa reunião e dá um motivo.",
            "opinião, motivo e ressalva",
        ),
    }),
    "la": _pack({
        "beginner": (
            "Te ipsum praesentare",
            "Salutas hominem quem modo nosti et nomen tuum dicis.",
            "salutationes et indicia personalia",
            "Apresentar-se",
            "Você cumprimenta alguém que acabou de conhecer.",
            "cumprimentos e informação pessoal",
        ),
        "elementary": (
            "Cibum rogare",
            "In popina cibum rogas et de pretio interrogas.",
            "petitiones, voluntates et pretium",
            "Pedir uma refeição",
            "Você pede comida em um restaurante e pergunta a conta.",
            "pedidos, preferências e conta",
        ),
        "intermediate": (
            "Iter narrare",
            "Socio iter recens narras.",
            "narratio et singula",
            "Contar uma viagem",
            "Você conta a um colega uma viagem recente.",
            "narrativa e detalhes",
        ),
        "upper": (
            "Urbane dissentire",
            "In colloquio sententiam aliter dicis et causam affers, urbane.",
            "sententia, causa et concessio",
            "Discordar com educação",
            "Você discorda com educação numa reunião e dá um motivo.",
            "opinião, motivo e ressalva",
        ),
    }),
}


def situation_for(language_code: str, band: str, native_language: str | None = "pt-BR") -> dict[str, str | None]:
    if language_code not in SITUATIONS:
        raise ValueError(f"Conteúdo indisponível para o idioma {language_code}")
    if band not in _BANDS:
        raise ValueError(f"Faixa indisponível: {band}")
    row = SITUATIONS[language_code][band]
    # Apoio estático só para português. Outra língua nativa não recebe esse texto.
    portuguese = native_language in {"pt", "pt-BR", "pt-PT"}
    support_scenario = row["scenario_pt"] if portuguese else None
    support_focus = row["focus_pt"] if portuguese else None
    support_title = row["title_pt"] if portuguese else None
    return {
        "target_language": language_code,
        "native_language": native_language,
        "situation": row["scenario_target"],
        "focus": row["focus_target"],
        "title_target": row["title_target"],
        "title_native": support_title,
        "scenario_target": row["scenario_target"],
        "scenario_native": support_scenario,
        "focus_target": row["focus_target"],
        "focus_native": support_focus,
        "instruction_target": row["scenario_target"],
        "instruction_native": support_scenario,
    }
