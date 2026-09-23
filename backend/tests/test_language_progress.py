"""Progresso por idioma, marcos derivados e transições que não se repetem."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.levels import CEFRLevel
from app.core.teaching import EvidenceType, MasteryState
from app.models import (
    Language,
    LearningAttempt,
    LearningEvidence,
    LearningObjective,
    LearningProgressEvent,
    StudySession,
    User,
    UserLanguage,
    UserObjectiveProgress,
    VocabularyExample,
    VocabularyItem,
)
from app.services.activity_generator import generate_vocabulary_activities
from app.services.language_access import user_can_access_language
from app.services.language_progress import (
    CEFR_AUTO_PROMOTION_ENABLED,
    CEFR_LEVEL_ADVANCED,
    LESSON_COMPLETED,
    MILESTONE_ADVANCED,
    adjacent_cefr,
    detect_progress_transition,
    evaluate_language_progress,
    evaluate_skill_progress,
    milestone_index_for_mean,
    observe_language_progress,
    record_product_event,
)
from app.services.language_progress import ProgressView
from app.services.lexical_policy import lexical_mastery_policy, required_evidence_types
from app.services.session_progress import select_short_batch, session_progress_from_activities


def _profile(db_session, code: str, *, level: str | None = "A1") -> UserLanguage:
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db_session.scalar(select(Language).where(Language.code == code))
    profile = UserLanguage(
        user_id=user.id,
        language_id=language.id,
        is_active=code == "en",
        current_level=level,
        level_source="placement_test",
    )
    db_session.add(profile)
    db_session.commit()
    return profile


def _demonstrated(db_session, profile, *, skill: str, level: str, state: str):
    language = db_session.get(Language, profile.language_id)
    objective = LearningObjective(
        language_id=language.id,
        level=level,
        code=f"{language.code}-{level}-{uuid.uuid4().hex[:8]}",
        title="Objetivo",
        can_do="Demonstra a habilidade.",
        skill_focus=skill,
    )
    db_session.add(objective)
    db_session.flush()
    attempt_time = datetime.now(timezone.utc)
    attempt = LearningAttempt(
        user_language_id=profile.id,
        objective_id=objective.id,
        activity_type="practice",
        result="correct",
        evaluated_at=attempt_time,
        created_at=attempt_time,
    )
    db_session.add(attempt)
    db_session.flush()
    db_session.add(
        LearningEvidence(
            user_language_id=profile.id,
            objective_id=objective.id,
            attempt_id=attempt.id,
            evidence_type="correct_response",
            created_at=attempt_time,
        )
    )
    db_session.add(
        UserObjectiveProgress(
            user_language_id=profile.id,
            objective_id=objective.id,
            state=state,
            started_at=attempt_time,
        )
    )
    db_session.commit()
    return objective


def test_progresso_fica_separado_por_idioma(db_session):
    english = _profile(db_session, "en", level="A1")
    german = _profile(db_session, "de", level="A2")
    _demonstrated(db_session, english, skill="reading", level="A1", state=MasteryState.MASTERED)
    _demonstrated(db_session, german, skill="listening", level="A2", state=MasteryState.LEARNING)

    english_skills = evaluate_skill_progress(db_session, english.id)
    german_skills = evaluate_skill_progress(db_session, german.id)

    assert [item["skill"] for item in english_skills] == ["reading"]
    assert english_skills[0]["percent"] == 100
    assert [item["skill"] for item in german_skills] == ["listening"]
    assert german_skills[0]["percent"] == 25
    assert evaluate_language_progress(db_session, english)["cefr"]["current"] == "A1"
    assert evaluate_language_progress(db_session, german)["cefr"]["current"] == "A2"


def test_skill_progress_omite_habilidade_sem_evidencia(db_session):
    profile = _profile(db_session, "en")
    _demonstrated(
        db_session, profile, skill="vocabulary_grammar", level="A1", state=MasteryState.PRACTICING
    )

    skills = evaluate_skill_progress(db_session, profile.id)

    assert skills == [
        {
            "skill": "vocabulary_grammar",
            "label": "Vocabulário e gramática",
            "percent": 50,
            "sample_size": 1,
        }
    ]
    assert all(item["skill"] != "speaking" for item in skills)


def test_sessoes_nao_alteram_cefr(db_session):
    profile = _profile(db_session, "en", level="A1")
    for _ in range(12):
        db_session.add(
            StudySession(
                user_language_id=profile.id,
                status="completed",
                started_at=datetime.now(timezone.utc) - timedelta(minutes=20),
                ended_at=datetime.now(timezone.utc),
            )
        )
    db_session.commit()

    result = evaluate_language_progress(db_session, profile)
    db_session.refresh(profile)

    assert profile.current_level == "A1"
    assert result["cefr"]["current"] == "A1"
    assert result["cefr"]["progress_to_next_percent"] is None
    assert result["auto_promotion_enabled"] is False


def test_cefr_nao_pula_nivel_intermediario():
    assert adjacent_cefr("A1") == "A2"
    assert adjacent_cefr("A2") == "B1"
    assert adjacent_cefr(CEFRLevel.C2) is None
    skipped = detect_progress_transition(
        ProgressView("A1", "A1-5", 5),
        ProgressView("B1", "B1-1", 1),
    )
    assert skipped == []


def test_marco_sai_das_faixas_reais_de_dominio():
    assert milestone_index_for_mean(25) == 1
    assert milestone_index_for_mean(35) == 2
    assert milestone_index_for_mean(50) == 3
    assert milestone_index_for_mean(70) == 4
    assert milestone_index_for_mean(100) == 5


def test_marco_e_cefr_disparam_uma_vez_e_dashboard_nao_repete(db_session):
    profile = _profile(db_session, "en", level="A1")
    objective = _demonstrated(
        db_session, profile, skill="reading", level="A1", state=MasteryState.LEARNING
    )

    first = observe_language_progress(db_session, profile.id)
    second = observe_language_progress(db_session, profile.id)
    assert first["celebrations"] == []
    assert second["celebrations"] == []
    assert first["milestone"]["code"] == "A1-1"

    progress = db_session.scalar(
        select(UserObjectiveProgress).where(UserObjectiveProgress.objective_id == objective.id)
    )
    progress.state = MasteryState.MASTERED
    db_session.commit()

    advanced = observe_language_progress(db_session, profile.id)
    repeated = observe_language_progress(db_session, profile.id)

    assert [item["event_type"] for item in advanced["celebrations"]] == [MILESTONE_ADVANCED]
    assert advanced["celebrations"][0]["payload"]["to_code"] == "A1-5"
    assert repeated["celebrations"] == []
    assert repeated["latest_achievement"]["title"] == "Você avançou para A1-5."
    assert (
        db_session.scalar(
            select(func.count(LearningProgressEvent.id)).where(
                LearningProgressEvent.user_language_id == profile.id,
                LearningProgressEvent.event_type == MILESTONE_ADVANCED,
            )
        )
        == 1
    )

    profile.current_level = "A2"
    db_session.commit()
    level_up = observe_language_progress(db_session, profile.id)
    again = observe_language_progress(db_session, profile.id)
    assert [item["event_type"] for item in level_up["celebrations"]] == [CEFR_LEVEL_ADVANCED]
    assert again["celebrations"] == []
    assert (
        db_session.scalar(
            select(func.count(LearningProgressEvent.id)).where(
                LearningProgressEvent.event_type == CEFR_LEVEL_ADVANCED,
                LearningProgressEvent.user_language_id == profile.id,
            )
        )
        == 1
    )


def test_promocao_automatica_permanece_desligada(db_session):
    profile = _profile(db_session, "en", level="A1")
    _demonstrated(db_session, profile, skill="reading", level="A1", state=MasteryState.MASTERED)
    _demonstrated(db_session, profile, skill="listening", level="A1", state=MasteryState.MASTERED)

    result = evaluate_language_progress(db_session, profile)
    db_session.refresh(profile)

    assert CEFR_AUTO_PROMOTION_ENABLED is False
    assert result["auto_promotion_enabled"] is False
    assert profile.current_level == "A1"
    assert result["cefr"]["next"] == "A2"


def test_politica_lexical_e_centralizada():
    policy = lexical_mastery_policy()
    assert policy["required_evidence_types"] == [
        EvidenceType.RECOGNITION,
        EvidenceType.REVERSE_RECOGNITION,
        EvidenceType.LISTENING_RECOGNITION,
        EvidenceType.LEXICAL_PRODUCTION,
    ]
    assert policy["evidence_strength"][EvidenceType.LEXICAL_PRODUCTION] == "strong"
    assert policy["evidence_strength"][EvidenceType.RECOGNITION] == "moderate"
    assert required_evidence_types() == frozenset(policy["required_evidence_types"])


def test_entitlement_desligado_nao_bloqueia_e_progresso_nao_usa_assinatura(db_session):
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    assert get_settings().language_entitlements_enabled is False
    assert user_can_access_language(db_session, user.id, "ja") is True
    profile = _profile(db_session, "fr", level="A2")
    result = evaluate_language_progress(db_session, profile)
    assert "subscription" not in result
    assert result["cefr"]["current"] == "A2"


def test_conclusao_de_licao_nao_duplica_evento(client, auth, db_session):
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    profile = UserLanguage(
        user_id=user.id,
        language_id=language.id,
        is_active=True,
        onboarding_completed=True,
        current_level="A2",
    )
    db_session.add(profile)
    db_session.commit()

    generated = client.post(
        "/api/v1/lessons/generate",
        json={"language_code": "en", "mode": "guided", "persist": True},
        headers=auth,
    )
    assert generated.status_code == 200
    lesson_id = generated.json()["lesson_id"]
    assert client.post(f"/api/v1/lessons/{lesson_id}/complete", headers=auth).status_code == 200
    assert client.post(f"/api/v1/lessons/{lesson_id}/complete", headers=auth).status_code == 409
    assert (
        db_session.scalar(
            select(func.count(LearningProgressEvent.id)).where(
                LearningProgressEvent.event_type == LESSON_COMPLETED,
                LearningProgressEvent.dedupe_key == lesson_id,
            )
        )
        == 1
    )
    assert record_product_event(
        db_session,
        user_language_id=profile.id,
        event_type=LESSON_COMPLETED,
        dedupe_key=lesson_id,
        payload={},
    ) is False


def test_progresso_da_sessao_curta_usa_atividades_reais():
    activities = [{"type": "presentation"}, {"type": "recognition"}, {"type": "lexical_production"}]
    progress = session_progress_from_activities(activities, 1)
    assert progress["completed"] == 1
    assert progress["total"] == 3
    assert progress["percent"] == 33
    assert progress["current_label"] == "Reconhecimento"
    assert progress["next_label"] == "Produção"

    batch, nxt = select_short_batch(["a", "b", "c", "d"], previous_offset=0)
    assert batch == ["a", "b", "c"]
    assert nxt == 3
    batch, nxt = select_short_batch(["a", "b", "c", "d"], previous_offset=3)
    assert batch == ["d"]
    assert nxt == 4


def test_audio_da_palavra_permanece_separado_do_audio_da_frase():
    apple = VocabularyItem(id="item-1", user_language_id="ul", term="apple", translation_pt="maçã")
    water = VocabularyItem(id="item-2", user_language_id="ul", term="water", translation_pt="água")
    example = VocabularyExample(
        vocabulary_item_id=apple.id,
        example_text="I eat an apple.",
        translation_pt="Eu como uma maçã.",
    )
    activities = generate_vocabulary_activities(
        [apple, water],
        examples_by_item={apple.id: [example]},
    )
    presentation = next(
        activity
        for activity in activities
        if activity["type"] == "presentation" and activity.get("term") == "apple"
    )
    targets = presentation["audio_targets"]
    assert targets[0]["audio_target_type"] == "vocabulary_item"
    assert targets[0]["audio_text"] == "apple"
    assert targets[1]["audio_target_type"] == "example_sentence"
    assert targets[1]["audio_text"] == "I eat an apple."
    listening = next(
        activity
        for activity in activities
        if activity["type"] == "listening_recognition" and activity.get("vocabulary_item_id") == apple.id
    )
    assert listening["audio_text"] == "apple"
    assert all(target["audio_target_type"] != "example_sentence" for target in listening["audio_targets"])
