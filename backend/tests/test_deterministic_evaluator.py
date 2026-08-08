"""Contrato do avaliador determinístico — lexical vs estrutural."""

from app.services import deterministic_evaluator as ev


def test_substring_false_positive_professor_alone_structural():
    result = ev.evaluate_response(
        student_response="professor",
        activity={
            "type": "guided_production",
            "evaluation_mode": "structural",
            "minimum_structure": "clause",
            "canonical_answer": "I work as a professor.",
            "accepted_variants": ["I'm a professor.", "I am a professor."],
            "required_features": ["professor"],
            "required_patterns": [r"\b(i('m| am)|i work as)\b"],
        },
    )
    assert result["result"] == "incorrect"


def test_accepted_variant_im_a_professor():
    result = ev.evaluate_response(
        student_response="I'm a professor.",
        canonical_answer="I work as a professor.",
        accepted_variants=["I'm a professor.", "I am a professor."],
        activity={"type": "guided_production", "evaluation_mode": "structural"},
    )
    assert result["result"] == "correct"
    assert result["matched_variant"] == "i'm a professor"


def test_accepted_variant_i_work_as():
    result = ev.evaluate_response(
        student_response="I work as a professor.",
        activity={
            "type": "transfer_question",
            "canonical_answer": "I work as a professor.",
            "accepted_variants": ["I'm a professor."],
        },
    )
    assert result["result"] == "correct"


def test_contraction_and_punctuation_and_casing():
    result = ev.evaluate_response(
        student_response="  I’M   a   PROFESSOR!!!  ",
        accepted_variants=["I'm a professor.", "I am a professor."],
        activity={"evaluation_mode": "structural"},
    )
    assert result["result"] == "correct"


def test_whitespace_normalization():
    result = ev.evaluate_response(
        student_response="I   am    a   professor.",
        accepted_variants=["I am a professor."],
    )
    assert result["result"] == "correct"


def test_incomplete_structural_answer():
    result = ev.evaluate_response(
        student_response="I am",
        activity={
            "type": "guided_production",
            "required_features": ["professor"],
            "required_patterns": [r"\bprofessor\b"],
            "minimum_structure": "clause",
        },
    )
    assert result["result"] == "incorrect"


def test_structurally_correct_with_patterns():
    result = ev.evaluate_response(
        student_response="I am a professor",
        activity={
            "type": "guided_production",
            "required_features": ["professor"],
            "required_patterns": [r"\b(i('m| am)|i work as)\b"],
            "minimum_structure": "clause",
        },
    )
    assert result["result"] == "correct"


def test_lexical_fill_gap_accepts_single_token():
    result = ev.evaluate_response(
        student_response="Ana",
        activity={
            "type": "fill_gap",
            "canonical_answer": "Ana",
            "accepted_variants": ["ana"],
        },
    )
    assert result["result"] == "correct"


def test_lexical_required_feature_still_token_boundary():
    """Sem modo estrutural, feature lexical pode passar — mas com fronteira."""
    result = ev.evaluate_response(
        student_response="professor",
        required_features=["professor"],
        activity={"type": "fill_gap", "evaluation_mode": "lexical"},
    )
    assert result["result"] == "correct"
