"""Contrato de papéis: alvo, apoio e feedback, sem descartar o texto."""

from app.services.content_seed import _payload_for
from app.services.language_detection import target_field_status
from app.services.language_roles import apply_language_roles, separate_embedded_translation
from app.services.learner_context import LearnerContext
from app.services.lesson_bank import BAND_INTERMEDIATE
from app.services.lesson_envelope import apply_lesson_envelope
from app.services.teaching_slice import _language_roles

MIXED = "Praticar opinion, raison et concession em uma situação realista."
SPAN = "opinion, raison et concession"
GRAMMAR = "Use o imparfait para descrever hábitos ou situações no passado."
ENGLISH = "The student reads a short story about a long trip and then answers the questions."
GERMAN = "Ich bin mit diesem Plan nicht einverstanden, weil er zu viel kostet."


def _finding(payload, field):
    return next(row for row in payload["language_role_findings"] if row["field"] == field)


def test_mixed_objective_is_split_and_the_original_stays():
    payload = {
        "objective": MIXED,
        "situation": "Vous n'êtes pas d'accord avec un collègue et vous expliquez pourquoi, poliment.",
    }
    findings = apply_language_roles(payload, target_language="fr", native_language="pt-BR")
    assert payload["objective_target"] == SPAN
    assert "raison" not in payload["objective"]
    assert payload["objective"].startswith("Praticar")
    assert payload["language_role_originals"]["objective"] == MIXED
    row = _finding(payload, "objective")
    assert row["role"] == "native"
    assert row["action"] == "repaired"
    assert row["reason"] == "mixed_target_span"
    assert "opinion" not in row["reason"]
    assert findings == payload["language_role_findings"]


def test_curated_seed_keeps_french_focus_out_of_the_portuguese_objective():
    payload = _payload_for("conversation", "fr", BAND_INTERMEDIATE, "B1")
    assert payload["objective"] == "Praticar opinião, motivo e ressalva em uma situação realista."
    assert payload["objective_target"] == SPAN
    assert payload["objective_native"] == payload["objective"]
    assert "raison" not in payload["objective"]
    assert payload["situation_native"]


def test_envelope_repairs_a_stored_mixed_objective_before_save():
    context = LearnerContext(
        "fr", "Francês", "Français", "B1", "Intermediário", "desc",
        "placement_test", True, native_language="pt-BR",
    )
    payload = apply_lesson_envelope(
        {
            "title": "Conversação · B1",
            "objective": MIXED,
            "situation": "Vous n'êtes pas d'accord avec un collègue et vous expliquez pourquoi, poliment.",
        },
        context=context,
        mode="conversation",
        provider="curated_library",
    )
    assert payload["objective_target"] == SPAN
    assert payload["language_role_originals"]["objective"] == MIXED
    assert _finding(payload, "objective")["role"] == "native"


def test_portuguese_grammar_with_a_french_term_is_not_rewritten():
    payload = {"explanation": GRAMMAR}
    assert apply_language_roles(payload, target_language="fr", native_language="pt-BR") == []
    assert payload["explanation"] == GRAMMAR
    assert "language_role_status" not in payload


def test_target_prompt_in_another_language_is_blocked_and_kept():
    payload = {"type": "reading", "prompt": ENGLISH, "activity_id": "read-en"}
    apply_language_roles(payload, target_language="fr", native_language="pt-BR")
    row = _finding(payload, "prompt")
    assert row["role"] == "target"
    assert row["action"] == "blocked"
    assert row["detected_language"] == "en"
    assert payload["prompt"] == ENGLISH
    assert payload["activity_id"] == "read-en"
    assert payload["language_role_status"] == "blocked"


def test_feedback_in_a_third_language_is_marked_and_kept():
    payload = {"why_correct": GERMAN, "is_correct": True}
    apply_language_roles(payload, target_language="fr", native_language="pt-BR")
    row = _finding(payload, "why_correct")
    assert row["role"] == "feedback"
    assert row["action"] == "review_required"
    assert payload["why_correct"] == GERMAN
    assert payload["is_correct"] is True


def test_support_translation_stays_beside_the_target_term():
    payload = {
        "type": "presentation",
        "term": "la gare",
        "translation": "a estação",
        "example": "Je vais à la gare.",
        "example_translation": "Eu vou à estação.",
        "usage_note": "Use com o verbo aller.",
    }
    assert apply_language_roles(payload, target_language="fr", native_language="pt-BR") == []
    assert payload["term"] == "la gare"
    assert payload["translation"] == "a estação"


def test_exercise_prompt_and_native_instruction_stay_apart():
    payload = {
        "exercises": [{
            "prompt": "Je pense que ce plan est utile, mais il coute trop cher aujourd hui.",
            "prompt_native": "Diga se concorda e dê um motivo.",
            "answer": "oui",
        }],
    }
    assert apply_language_roles(payload, target_language="fr", native_language="pt-BR") == []
    assert payload["exercises"][0]["answer"] == "oui"
    assert "prompt_native" not in payload["exercises"][0] or payload["exercises"][0]["prompt_native"].startswith("Diga")


def test_conversation_reply_and_translation_keep_their_roles():
    payload = {
        "reply": "Je pense que ce plan est utile, mais il coute trop cher aujourd hui.",
        "reply_translation": "Acho que este plano é útil, mas custa caro demais.",
    }
    assert apply_language_roles(payload, target_language="fr", native_language="pt-BR") == []
    assert payload["reply"].startswith("Je pense")
    assert payload["reply_translation"].startswith("Acho")


def test_legacy_retry_payload_keeps_its_identity_when_the_objective_is_mixed():
    payload = {
        "activity_id": "legacy-1",
        "type": "choice",
        "objective": MIXED,
        "prompt": "Je pense que ce plan est utile, mais il coute trop cher aujourd hui.",
        "prompt_pt": "Escolha a frase que expressa a opinião.",
        "answer": "oui",
        "options": ["oui", "non"],
    }
    apply_language_roles(payload, target_language="fr", native_language="pt-BR")
    assert payload["activity_id"] == "legacy-1"
    assert payload["answer"] == "oui"
    assert payload["options"] == ["oui", "non"]
    assert payload["objective_target"] == SPAN
    assert payload["prompt_pt"].startswith("Escolha")
    assert _finding(payload, "objective")["action"] == "repaired"


def test_vocabulary_cycle_return_records_feedback_without_changing_the_activity_id():
    activity = {
        "activity_id": "vocab-1",
        "type": "presentation",
        "target_language": "fr",
        "native_language": "pt-BR",
        "term": "la gare",
        "translation": "a estação",
        "objective": MIXED,
    }
    feedback = {"why_correct": GERMAN, "is_correct": False}
    findings, assessed = _language_roles(activity, feedback)
    assert activity["activity_id"] == "vocab-1"
    assert activity["objective_target"] == SPAN
    assert assessed["why_correct"] == GERMAN
    assert assessed is not feedback
    roles = {(row["field"], row["role"], row["action"]) for row in findings}
    assert ("objective", "native", "repaired") in roles
    assert ("why_correct", "feedback", "review_required") in roles


def test_embedded_translation_leaves_the_reply():
    reply = separate_embedded_translation("Je vais à la gare. (Vou à estação.)", "Vou à estação.")
    assert reply == "Je vais à la gare."


def test_english_suggestion_is_visible_inside_the_list():
    payload = {
        "reply": "Je voudrais un billet pour Lyon, s'il vous plaît.",
        "suggestions": [
            "The student should buy a ticket and then ask for the platform number.",
        ],
    }
    apply_language_roles(payload, target_language="fr", native_language="pt-BR")
    assert payload["language_role_status"] == "blocked"
    assert payload["language_role_findings"][0]["field"] == "suggestions[0]"


def test_short_target_phrase_is_not_blocked():
    payload = {"reply": "Bonjour"}
    assert apply_language_roles(payload, target_language="fr", native_language="pt-BR") == []


ENGLISH = "The student reads a short story about a long trip and then answers the questions."
FRENCH = "Je voudrais un billet pour Lyon, s'il vous plaît, et ensuite le quai."
FRENCH_SUPPORT = "L'élève lit une histoire courte sur un long voyage et répond ensuite aux questions posées."


def test_english_support_is_refused_and_kept():
    payload = {"reply": FRENCH, "reply_translation": ENGLISH}
    apply_language_roles(payload, target_language="fr", native_language="pt-BR")
    assert payload["language_role_status"] == "blocked"
    assert payload["reply_translation"] == ENGLISH
    assert payload["reply"] == FRENCH


def test_french_support_is_allowed_when_native_is_french():
    payload = {"reply": ENGLISH, "reply_translation": FRENCH_SUPPORT}
    assert apply_language_roles(payload, target_language="en", native_language="fr") == []


def test_missing_native_does_not_promote_portuguese():
    payload = {
        "prompt": FRENCH,
        "prompt_pt": "Escolha a frase que expressa a opinião do aluno.",
    }
    apply_language_roles(payload, target_language="fr", native_language=None)
    assert "prompt_native" not in payload


def test_student_quote_in_another_language_does_not_block_the_reply():
    payload = {
        "reply": FRENCH,
        "corrections": [{
            "original": ENGLISH,
            "corrected": "Je voudrais un billet.",
            "explanation": "O verbo pedido aqui é o condicional de polidez.",
        }],
    }
    assert apply_language_roles(payload, target_language="fr", native_language="pt-BR") == []
    assert payload["corrections"][0]["original"] == ENGLISH


def test_invalid_reply_is_retried_once_and_then_stopped():
    from app.services.language_roles import checked_conversation_turn

    class Once:
        def __init__(self):
            self.calls = 0

        def conversation_turn(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                return {"reply": ENGLISH}
            return {"reply": FRENCH}

    provider = Once()
    result, _findings = checked_conversation_turn(
        provider, "bonjour", None, [], target_language="fr", native_language="pt-BR", turn_index=0,
    )
    assert provider.calls == 2
    assert result["reply"] == FRENCH

    class Always:
        def __init__(self):
            self.calls = 0

        def conversation_turn(self, *_args, **_kwargs):
            self.calls += 1
            return {"reply": ENGLISH}

    stuck = Always()
    rejected, _findings = checked_conversation_turn(
        stuck, "bonjour", None, [], target_language="fr", native_language="pt-BR", turn_index=0,
    )
    assert stuck.calls == 2
    assert rejected["language_role_status"] == "blocked"


def test_tutor_accepts_native_explanation_and_refuses_a_third_language():
    from app.services.language_roles import checked_tutor_turn

    class Native:
        def tutor_chat_turn(self, *_args, **_kwargs):
            return {"reply": "O condicional de polidez em francês usa je voudrais diante de um pedido."}

    accepted, rejected = checked_tutor_turn(
        Native(), "como peço?", None, [], target_language="fr", native_language="pt-BR",
    )
    assert rejected is False
    assert accepted["reply"].startswith("O condicional")

    class English:
        def __init__(self):
            self.calls = 0

        def tutor_chat_turn(self, *_args, **_kwargs):
            self.calls += 1
            return {"reply": ENGLISH}

    provider = English()
    _result, rejected = checked_tutor_turn(
        provider, "como peço?", None, [], target_language="fr", native_language="pt-BR",
    )
    assert rejected is True
    assert provider.calls == 2


def test_short_latin_and_isolated_term_are_not_blocked():
    assert apply_language_roles(
        {"reply": "Ave Maria"}, target_language="la", native_language="pt-BR",
    ) == []
    assert apply_language_roles(
        {"term": "駅"}, target_language="ja", native_language="pt-BR",
    ) == []


def test_japanese_sentence_without_spaces_is_measured():
    sentence = "今日は天気がいいので公園を散歩します"
    assert target_field_status({"prompt_target": sentence}, "ja") is None
    english = "The student reads a short story about a long trip and then answers the questions."
    assert target_field_status({"prompt_target": english}, "ja") == "language_invalid"
