"""Série narrativa do inglês: "Bell & Sons".

Por que existe: o cronograma tinha tema e sequência, mas nenhum motivo para
voltar amanhã além da disciplina. No produto de referência (Gymglish / Le Monde
Langues) o que sustenta o hábito é a história — elenco fixo, episódios curtos,
situações comuns com humor seco.

Regras deste módulo:

- **Só `en`.** Os outros idiomas não têm série; a ausência é declarada
  (`episode_for` devolve `None`), nunca preenchida com cena genérica.
- **Determinístico.** Mesmo tema e mesmo dia dão a mesma cena. Nada de sorteio:
  a pessoa que reabre a jornada precisa reencontrar a cena de onde parou.
- **Adulto, não infantil.** Segue a direção visual decidida em
  `docs/design-system.md`: humor seco, situação real, sem mascote.
- **Sem IA.** Conteúdo curado em código, revisável. Cena não é gerada na hora.

Cada fala carrega tradução para português, porque a cena é insumo de
compreensão, não avaliação: o aluno pode conferir sem sair da tela.
"""

from __future__ import annotations

from typing import Any

#: Elenco recorrente. Poucos personagens, reconhecíveis por função e voz.
CAST: tuple[dict[str, str], ...] = (
    {
        "name": "Nora",
        "role": "Gerente da livraria Bell & Sons, em Bristol. Direta, listas para tudo.",
    },
    {
        "name": "Theo",
        "role": "Barista do café da livraria. Escreve um romance que ninguém leu.",
    },
    {
        "name": "Priya",
        "role": "Jornalista freelancer. Trabalha nas mesas do fundo e ouve tudo.",
    },
    {
        "name": "Mr. Okafor",
        "role": "Dono do prédio. Fala pouco e cobra em dia.",
    },
)

#: Episódios por tema do currículo. A chave é o tema exatamente como o
#: `curriculum_bank` o escreve — se o tema mudar de nome lá, a cena desaparece
#: em vez de casar com o tema errado.
_EPISODES: dict[str, tuple[dict[str, Any], ...]] = {
    "Apresentações e rotina": (
        {
            "title": "First morning",
            "setting": "Segunda-feira, 7h40. Theo abre o café e encontra alguém já sentado.",
            "expressions": ("I'm", "Nice to meet you", "every morning"),
            "lines": (
                {
                    "speaker": "Theo",
                    "text": "Good morning. We open at eight.",
                    "translation_pt": "Bom dia. A gente abre às oito.",
                },
                {
                    "speaker": "Priya",
                    "text": "I know. I'm Priya. I work here every morning.",
                    "translation_pt": "Eu sei. Sou a Priya. Trabalho aqui todas as manhãs.",
                },
                {
                    "speaker": "Theo",
                    "text": "You work here? I'm Theo. I make the coffee.",
                    "translation_pt": "Você trabalha aqui? Sou o Theo. Eu faço o café.",
                },
                {
                    "speaker": "Priya",
                    "text": "Then we are colleagues. Nice to meet you, Theo.",
                    "translation_pt": "Então somos colegas. Prazer, Theo.",
                },
            ),
        },
        {
            "title": "Nora's list",
            "setting": "8h05. Nora chega com um caderno e um plano para o dia inteiro.",
            "expressions": ("I start", "at nine", "What time"),
            "lines": (
                {
                    "speaker": "Nora",
                    "text": "I start at seven. You start at eight. Priya starts at dawn, apparently.",
                    "translation_pt": "Eu começo às sete. Você começa às oito. A Priya começa ao amanhecer, aparentemente.",
                },
                {
                    "speaker": "Priya",
                    "text": "What time do you finish?",
                    "translation_pt": "A que horas você termina?",
                },
                {
                    "speaker": "Nora",
                    "text": "I never finish. I close the shop at nine.",
                    "translation_pt": "Eu nunca termino. Eu fecho a loja às nove.",
                },
            ),
        },
        {
            "title": "The rent is due",
            "setting": "Fim da tarde. Mr. Okafor aparece na porta, como toda primeira semana.",
            "expressions": ("every month", "on Friday", "I'm afraid"),
            "lines": (
                {
                    "speaker": "Mr. Okafor",
                    "text": "Good evening. It's the first week of the month.",
                    "translation_pt": "Boa noite. É a primeira semana do mês.",
                },
                {
                    "speaker": "Nora",
                    "text": "I'm afraid I know. You say that every month.",
                    "translation_pt": "Infelizmente eu sei. Você diz isso todo mês.",
                },
                {
                    "speaker": "Mr. Okafor",
                    "text": "And every month you pay on Friday.",
                    "translation_pt": "E todo mês você paga na sexta.",
                },
            ),
        },
    ),
    "Família e pessoas próximas": (
        {
            "title": "My sister's books",
            "setting": "Uma caixa de livros chega sem remetente claro.",
            "expressions": ("my sister", "her husband", "they live"),
            "lines": (
                {
                    "speaker": "Nora",
                    "text": "This box is from my sister. She lives in Leeds.",
                    "translation_pt": "Esta caixa é da minha irmã. Ela mora em Leeds.",
                },
                {
                    "speaker": "Theo",
                    "text": "Does her husband read all of this?",
                    "translation_pt": "O marido dela lê tudo isso?",
                },
                {
                    "speaker": "Nora",
                    "text": "No. They buy books and send them to me.",
                    "translation_pt": "Não. Eles compram livros e mandam para mim.",
                },
            ),
        },
        {
            "title": "Theo's mother calls",
            "setting": "O telefone de Theo vibra pela quarta vez.",
            "expressions": ("my mother", "she asks", "not yet"),
            "lines": (
                {
                    "speaker": "Theo",
                    "text": "It's my mother. She asks about the novel every week.",
                    "translation_pt": "É minha mãe. Ela pergunta do romance toda semana.",
                },
                {
                    "speaker": "Priya",
                    "text": "And what do you say?",
                    "translation_pt": "E o que você diz?",
                },
                {
                    "speaker": "Theo",
                    "text": "I say: not yet, Mum. Not yet.",
                    "translation_pt": "Eu digo: ainda não, mãe. Ainda não.",
                },
            ),
        },
    ),
    "Comida e restaurante": (
        {
            "title": "Two soups, one spoon",
            "setting": "Meio-dia. O café só tem duas opções e uma delas acabou.",
            "expressions": ("I'd like", "Is there any", "We're out of"),
            "lines": (
                {
                    "speaker": "Priya",
                    "text": "I'd like the tomato soup, please.",
                    "translation_pt": "Eu queria a sopa de tomate, por favor.",
                },
                {
                    "speaker": "Theo",
                    "text": "We're out of tomato. There's onion soup.",
                    "translation_pt": "A de tomate acabou. Tem sopa de cebola.",
                },
                {
                    "speaker": "Priya",
                    "text": "Is there any bread?",
                    "translation_pt": "Tem pão?",
                },
                {
                    "speaker": "Theo",
                    "text": "There's one slice. It's yours.",
                    "translation_pt": "Tem uma fatia. É sua.",
                },
            ),
        },
    ),
    "Casa e moradia": (
        {
            "title": "The flat above the shop",
            "setting": "Mr. Okafor mostra o apartamento de cima, que tem um defeito por ambiente.",
            "expressions": ("There's a", "on the second floor", "It doesn't work"),
            "lines": (
                {
                    "speaker": "Mr. Okafor",
                    "text": "There's a flat on the second floor. Two rooms.",
                    "translation_pt": "Tem um apartamento no segundo andar. Dois quartos.",
                },
                {
                    "speaker": "Theo",
                    "text": "And the heating?",
                    "translation_pt": "E o aquecimento?",
                },
                {
                    "speaker": "Mr. Okafor",
                    "text": "It exists. It doesn't work.",
                    "translation_pt": "Ele existe. Ele não funciona.",
                },
            ),
        },
    ),
    "Direções e transporte": (
        {
            "title": "Turn left at the bakery",
            "setting": "Uma entrega se perdeu três ruas antes.",
            "expressions": ("Turn left", "go straight", "next to"),
            "lines": (
                {
                    "speaker": "Nora",
                    "text": "Go straight, then turn left at the bakery.",
                    "translation_pt": "Siga em frente e vire à esquerda na padaria.",
                },
                {
                    "speaker": "Priya",
                    "text": "The bakery next to the station?",
                    "translation_pt": "A padaria ao lado da estação?",
                },
                {
                    "speaker": "Nora",
                    "text": "No. The bakery next to the other bakery.",
                    "translation_pt": "Não. A padaria ao lado da outra padaria.",
                },
            ),
        },
    ),
    "Compras e dinheiro": (
        {
            "title": "Cash only, again",
            "setting": "A máquina de cartão escolheu justo a hora do movimento.",
            "expressions": ("How much", "It costs", "Can I pay"),
            "lines": (
                {
                    "speaker": "Priya",
                    "text": "How much is the second-hand one?",
                    "translation_pt": "Quanto custa o de segunda mão?",
                },
                {
                    "speaker": "Nora",
                    "text": "It costs four pounds. The new one costs twelve.",
                    "translation_pt": "Custa quatro libras. O novo custa doze.",
                },
                {
                    "speaker": "Priya",
                    "text": "Can I pay by card?",
                    "translation_pt": "Posso pagar com cartão?",
                },
                {
                    "speaker": "Nora",
                    "text": "The machine is thinking about it. Cash is faster.",
                    "translation_pt": "A máquina está pensando. Dinheiro é mais rápido.",
                },
            ),
        },
    ),
}

#: Idioma único da série. Uma série por idioma exige elenco e revisão próprios;
#: não se reaproveita cena traduzida — seria conteúdo inglês com rótulo errado.
SERIES_LANGUAGE = "en"
SERIES_TITLE = "Bell & Sons"


def covered_themes() -> tuple[str, ...]:
    """Temas que já têm episódio. O resto do currículo segue sem cena."""
    return tuple(_EPISODES)


def episode_for(theme: str, *, day_number: int) -> dict[str, Any] | None:
    """Cena do tema para aquele dia, ou `None` se o tema não tem série.

    A escolha é determinística: o dia entra pelo resto da divisão sobre os
    episódios do tema. Dias seguintes do mesmo tema avançam na sequência e
    reabrir a mesma jornada devolve sempre a mesma cena.
    """
    episodes = _EPISODES.get(theme)
    if not episodes:
        return None
    index = max(day_number - 1, 0) % len(episodes)
    episode = episodes[index]
    return {
        "series": SERIES_TITLE,
        "title": episode["title"],
        "setting": episode["setting"],
        "expressions": list(episode["expressions"]),
        "lines": [dict(line) for line in episode["lines"]],
        "cast": [dict(member) for member in CAST],
        "episode_index": index + 1,
        "episodes_in_theme": len(episodes),
    }


def episode_for_language(
    language_code: str, theme: str | None, *, day_number: int
) -> dict[str, Any] | None:
    """Cena da jornada. Fora de `en`, ou sem tema, não há série."""
    if language_code != SERIES_LANGUAGE or not theme:
        return None
    return episode_for(theme, day_number=day_number)
