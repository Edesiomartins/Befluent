"""Speech Coach V1 — inteligibilidade pedagógica (sem pronunciation score)."""

from __future__ import annotations

from sqlalchemy import select

from app.core.teaching import EvidenceType, MasteryState
from app.models import Language, LearningEvidence, User, UserLanguage, UserObjectiveProgress
from app.services import speech_coach
from app.services.objective_seed import ensure_en_a1_can_001
from app.services.speech_intelligibility import assess_intelligibility


TARGET = "I strongly disagree with that argument."


def test_target_equals_transcript_success():
    out = speech_coach.coach_from_transcript(
        target_text=TARGET,
        transcript="I strongly disagree with that argument.",
    )
    assert out["success"] is True
    assert out["is_phonetic_score"] is False
    assert out["status"] == "good"
    assert "compreensível" in out["feedback"]["summary_pt"].lower()
    assert out["feedback"]["metric_name"] == "speech_correspondence"
    assert "pronunciation" not in (out["feedback"]["metric_label_pt"] or "").lower()


def test_missed_word_feedback():
    out = speech_coach.coach_from_transcript(
        target_text=TARGET,
        transcript="I strongly disagree with argument.",
    )
    assert out["success"] is False
    assert "that" in out["intelligibility"]["missed_tokens"]
    assert any("that" in (p["label_pt"] or "") for p in out["feedback"]["points"])
    assert out["practice_chunk"]
    assert "that" in out["practice_chunk"]


def test_extra_word_feedback():
    out = speech_coach.coach_from_transcript(
        target_text="I disagree.",
        transcript="I really disagree.",
    )
    assert "really" in out["intelligibility"]["extra_tokens"]
    assert out["is_phonetic_score"] is False


def test_multiple_diffs_limit_points():
    out = speech_coach.coach_from_transcript(
        target_text="I strongly disagree with that argument today.",
        transcript="strongly agree argument now",
    )
    assert len(out["feedback"]["points"]) <= 2


def test_punctuation_case_not_false_error():
    out = speech_coach.coach_from_transcript(
        target_text="I strongly disagree with that argument!",
        transcript="i strongly disagree with that argument",
    )
    assert out["success"] is True


def test_empty_transcript_technical_not_pedagogical():
    out = speech_coach.coach_from_transcript(target_text=TARGET, transcript="")
    assert out["status"] == "technical_issue"
    assert out["pedagogical_error"] is False
    assert out["intelligibility"] is None
    assert out["repair"]["action"] == "retry_record"


def test_practice_chunk_is_short_context():
    chunk = speech_coach.build_practice_chunk(
        ["i", "strongly", "disagree", "with", "that", "argument"],
        ["that"],
    )
    assert chunk is not None
    tokens = chunk.split()
    assert 2 <= len(tokens) <= 5
    assert "that" in tokens


def test_repair_escalation_and_limit():
    first = speech_coach.coach_from_transcript(
        target_text=TARGET,
        transcript="I strongly disagree with argument.",
        attempt_number=1,
    )
    assert first["repair"]["action"] == "retry_full"

    second = speech_coach.coach_from_transcript(
        target_text=TARGET,
        transcript="I strongly disagree with argument.",
        attempt_number=2,
        previous_missed=["that"],
    )
    assert second["repair"]["action"] == "practice_chunk"
    assert second["practice_chunk"]

    limited = speech_coach.coach_from_transcript(
        target_text=TARGET,
        transcript="I strongly disagree with argument.",
        attempt_number=speech_coach.MAX_REPAIR_ATTEMPTS,
        previous_missed=["that"],
    )
    assert limited["repair"]["action"] == "continue"
    assert limited["repair"]["allow_continue"] is True


def test_alignment_sequence_roles():
    seq = speech_coach.build_alignment_sequence(
        ["i", "love", "cats"],
        ["i", "love", "dogs"],
    )
    roles = {item["role"] for item in seq}
    assert "match" in roles
    assert "miss" in roles or "extra" in roles


def test_api_speech_coach(client, auth):
    response = client.post(
        "/api/v1/teaching/speech-coach",
        headers=auth,
        json={
            "target_text": TARGET,
            "transcript": "I strongly disagree with that argument.",
            "attempt_number": 1,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["is_phonetic_score"] is False
    assert body["te_evidence"] is None


def test_stt_empty_via_api_not_learning_error(client, auth, db_session):
    response = client.post(
        "/api/v1/teaching/speech-coach",
        headers=auth,
        json={"target_text": TARGET, "transcript": "", "attempt_number": 1},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["pedagogical_error"] is False
    from app.models import LearningError

    assert db_session.scalars(select(LearningError)).first() is None


def test_evidence_does_not_auto_master(db_session):
    objective = ensure_en_a1_can_001(db_session)
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    ul = db_session.scalar(
        select(UserLanguage).where(
            UserLanguage.user_id == user.id,
            UserLanguage.language_id == language.id,
        )
    )
    if ul is None:
        ul = UserLanguage(
            user_id=user.id,
            language_id=language.id,
            is_active=True,
            onboarding_completed=True,
        )
        db_session.add(ul)
        db_session.flush()

    coach = speech_coach.coach_from_transcript(
        target_text="I live in Brazil.",
        transcript="I live in Brazil.",
    )
    evidence = speech_coach.maybe_record_spoken_evidence(
        db_session,
        user_language_id=ul.id,
        objective_id=objective.id,
        coach_result=coach,
    )
    db_session.commit()
    assert evidence is not None
    assert evidence["evidence_type"] == EvidenceType.SPOKEN_INTELLIGIBILITY
    rows = db_session.scalars(select(LearningEvidence)).all()
    assert any(r.evidence_type == EvidenceType.SPOKEN_INTELLIGIBILITY for r in rows)

    progress = db_session.scalar(
        select(UserObjectiveProgress).where(
            UserObjectiveProgress.user_language_id == ul.id,
            UserObjectiveProgress.objective_id == objective.id,
        )
    )
    assert progress is not None
    assert progress.state != MasteryState.MASTERED


def test_intelligibility_reused_not_phonetic():
    base = assess_intelligibility(target_text=TARGET, transcript=TARGET)
    assert base["is_phonetic_score"] is False
    coach = speech_coach.coach_from_transcript(target_text=TARGET, transcript=TARGET)
    assert coach["intelligibility"]["coverage"] == base["intelligibility"]["coverage"]
