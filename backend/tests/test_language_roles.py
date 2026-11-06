"""Contrato de papéis: alvo, apoio e feedback, sem descartar o texto."""

from app.services.content_seed import _payload_for
from app.services.language_roles import apply_language_roles
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
