"""Fatia curada de francês B1 com apoio em pt-BR.

Não é cota nem preenchimento até 200. Cada item tem estímulo próprio.
O banco estático maior continua em lesson_bank; esta lista só cobre
interações que a sessão de apoio ainda não montava.
"""

from __future__ import annotations

_LEVEL = "B1"
_TARGET = "fr"
_NATIVE = "pt-BR"
_SOURCE = "curated_fr_b1_slice"


def _base(**fields) -> dict:
    item = {
        "target_language": _TARGET,
        "native_language": _NATIVE,
        "cefr_level": _LEVEL,
        "quality_status": "approved",
        "review_status": "approved",
        "content_source": _SOURCE,
        "ai_required": False,
        "support_visibility": "spot",
        "difficulty": "unknown",
        "topic": "opinion",
    }
    item.update(fields)
    return item


def activities() -> list[dict]:
    return [
        _base(
            activity_id="fr-b1-presentation-pourtant",
            type="presentation",
            skill="vocabulary",
            phase_hint="input",
            term="pourtant",
            translation="contudo",
            prompt="pourtant",
            prompt_native="Veja como marcar contraste.",
            example_sentence="L'idée est simple, pourtant elle change la discussion.",
            example_translation_pt="A ideia é simples, contudo ela muda a discussão.",
        ),
        _base(
            activity_id="fr-b1-listen-train",
            type="listening_recognition",
            skill="listening",
            phase_hint="practicing",
            audio_text="Le train de huit heures part du quai numéro deux.",
            show_text=False,
            prompt_native="Qual opção corresponde ao áudio?",
            prompt="Écoutez et choisissez.",
            options=[
                "Le train part à huit heures.",
                "Le train arrive à minuit.",
                "Le quai est fermé.",
            ],
            canonical_answer="Le train part à huit heures.",
        ),
        _base(
            activity_id="fr-b1-reading-opinion",
            type="multiple_choice",
            skill="reading",
            phase_hint="noticing",
            prompt="« Je pense que ce plan est utile, mais il coûte trop cher. » Que fait la personne ?",
            prompt_native="O que a pessoa faz nessa frase?",
            options=[
                "Elle donne un avis et une réserve.",
                "Elle demande l'addition.",
                "Elle se présente.",
            ],
            canonical_answer="Elle donne un avis et une réserve.",
        ),
        _base(
            activity_id="fr-b1-gap-utile",
            type="fill_gap",
            skill="grammar",
            phase_hint="practicing",
            prompt="Je pense que cette idée est ___.",
            prompt_native="Complete com a palavra que falta.",
            canonical_answer="utile",
            accepted_variants=["utile"],
        ),
        _base(
            activity_id="fr-b1-order-disagree",
            type="word_order",
            skill="grammar",
            phase_hint="practicing",
            prompt_native="Toque as palavras na ordem da frase.",
            prompt="Je ne suis pas d'accord.",
            tokens=["Je", "ne", "suis", "pas", "d'accord"],
            canonical_answer="Je ne suis pas d'accord.",
            accepted_variants=["Je ne suis pas d'accord."],
        ),
        _base(
            activity_id="fr-b1-match-courtesy",
            type="matching",
            skill="vocabulary",
            phase_hint="practicing",
            prompt_native="Relacione cada expressão ao sentido.",
            prompt="Reliez chaque expression à son sens.",
            pairs=[
                {"term": "je suis d'accord", "hint_pt": "eu concordo"},
                {"term": "je ne suis pas d'accord", "hint_pt": "eu não concordo"},
                {"term": "à mon avis", "hint_pt": "na minha opinião"},
            ],
        ),
        _base(
            activity_id="fr-b1-guided-train",
            type="guided_production",
            skill="production",
            phase_hint="producing",
            prompt="Dites que vous préférez le train.",
            prompt_native="Diga que você prefere o trem.",
            scaffold_pt="Je préfère…",
            canonical_answer="Je préfère le train.",
            accepted_variants=["Je préfère le train."],
        ),
        _base(
            activity_id="fr-b1-repeat-agree",
            type="repeat",
            skill="speaking",
            phase_hint="producing",
            prompt="Je suis d'accord.",
            prompt_native="Repita a frase.",
            models=["Je suis d'accord."],
            canonical_answer="Je suis d'accord.",
            accepted_variants=["Je suis d'accord."],
            response_modes=["typing", "speech"],
        ),
        _base(
            activity_id="fr-b1-transfer-station",
            type="transfer_question",
            skill="conversation",
            phase_hint="transfer_check",
            prompt="Vous avez demandé des informations à l'hôtel. Maintenant, demandez à un agent en gare où se trouve le bon quai.",
            prompt_native="Você praticou pedir informação. Agora pergunte na estação onde fica a plataforma certa.",
            canonical_answer="Où se trouve le bon quai ?",
            accepted_variants=["Où se trouve le bon quai ?", "Où est le bon quai ?"],
        ),
        _base(
            activity_id="fr-b1-dictation-agree",
            type="dictation",
            skill="listening",
            phase_hint="practicing",
            audio_text="Je suis d'accord avec cette idée.",
            show_text=False,
            prompt="Écrivez ce que vous entendez.",
            instruction_native="Escreva o que ouviu.",
            prompt_native="Escreva o que ouviu.",
            canonical_answer="Je suis d'accord avec cette idée.",
            accepted_variants=["Je suis d'accord avec cette idée."],
            compare="normalized_text",
            response_mode="typing",
        ),
    ]


def count() -> int:
    return len(activities())
