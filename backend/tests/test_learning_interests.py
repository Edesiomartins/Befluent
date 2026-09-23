"""Interesse troca o contexto da frase e não apaga domínio."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.levels import LevelSource
from app.core.teaching import MasteryState
from app.models import (
    Language,
    LearningAttempt,
    LearningEvidence,
    LearningGoal,
    LearningObjective,
    User,
    UserLanguage,
    UserObjectiveProgress,
)
from app.services.learning_interests import (
    apply_interest_context,
    personalize_conversation_item,
)
from app.services.learner_context import LearnerContext, build_context
from app.core.levels import CEFRLevel, LevelSource as Source
from app.services.ai import MockAIProvider


def _items():
    return [
        {
            "term": "how much",
            "translation": "quanto",
            "example": "How much is this?",
            "example_translation": "Quanto custa isto?",
        },
        {
            "term": "thank you",
            "translation": "obrigado",
            "example": "Thank you for your help.",
            "example_translation": "Obrigado pela ajuda.",
        },
    ]


def test_sem_interesse_mantem_conteudo_geral():
    result = apply_interest_context(_items(), language_code="en", interests=[])
    assert [item["term"] for item in result] == ["how much", "thank you"]
    assert result[0]["example"] == "How much is this?"
    assert result[0]["learning_context"] == "general"


def test_interesse_personaliza_so_quando_ha_variante_e_nao_remove_o_resto():
    result = apply_interest_context(_items(), language_code="en", interests=["Viajar"])
    assert [item["term"] for item in result] == ["how much", "thank you"]
    assert result[0]["translation"] == "quanto"
    assert result[0]["example"] == "How much is the train ticket?"
    assert result[0]["learning_context"] == "travel"
    assert result[1]["example"] == "Thank you for your help."
    assert result[1]["learning_context"] == "general"


def test_fallback_quando_nao_existe_variante():
    result = apply_interest_context(
        [{"term": "thank you", "translation": "obrigado", "example": "Thank you."}],
        language_code="en",
        interests=["Consumir cultura"],
    )
    assert result[0]["example"] == "Thank you."
    assert result[0]["learning_context"] == "general"


def test_conversa_usa_interesse_e_cai_no_geral(db_session):
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    travel = build_context(db_session, user, "en")
    travel.interests = ["Viajar"]
    travel.recent_terms = ["how much"]
    chosen = personalize_conversation_item(
        _items(),
        language_code="en",
        interests=travel.interests,
        recent_terms=travel.recent_terms,
        turn=0,
    )
    assert chosen["example"] == "How much is the train ticket?"

    general = personalize_conversation_item(
        _items(),
        language_code="en",
        interests=[],
        recent_terms=["how much"],
        turn=0,
    )
    assert general["example"] == "How much is this?"

    context = LearnerContext(
        language_code="en",
        language_name_pt="Inglês",
        language_native_name="English",
        level=CEFRLevel.A1,
        level_name_pt="A1",
        level_description="desc",
        level_source=Source.SELF_DECLARED,
        level_is_estimated=False,
        interests=["Viajar"],
        recent_terms=["how much"],
    )
    turn = MockAIProvider().conversation_turn("oi", context, [])
    assert "train ticket" in turn["reply"]
    empty = LearnerContext(
        language_code="en",
        language_name_pt="Inglês",
        language_native_name="English",
        level=CEFRLevel.A1,
        level_name_pt="A1",
        level_description="desc",
        level_source=Source.SELF_DECLARED,
        level_is_estimated=False,
    )
    fallback = MockAIProvider().conversation_turn("oi", empty, [])
    assert fallback["reply"]
    assert "train ticket" not in fallback["reply"]


def test_trocar_interesse_nao_apaga_dominio_nem_cefr(client, auth, db_session):
    user = db_session.scalar(select(User).where(User.email == "admin@befluent.local"))
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    profile = UserLanguage(
        user_id=user.id,
        language_id=language.id,
        is_active=True,
        onboarding_completed=True,
        current_level="A2",
        level_source=LevelSource.PLACEMENT_TEST,
    )
    db_session.add(profile)
    db_session.flush()
    objective = LearningObjective(
        language_id=language.id,
        level="A2",
        code=f"EN-A2-{uuid.uuid4().hex[:6]}",
        title="Leitura",
        can_do="Lê um aviso.",
        skill_focus="reading",
    )
    db_session.add(objective)
    db_session.flush()
    attempt = LearningAttempt(
        user_language_id=profile.id,
        objective_id=objective.id,
        activity_type="practice",
        result="correct",
    )
    db_session.add(attempt)
    db_session.flush()
    db_session.add(
        LearningEvidence(
            user_language_id=profile.id,
            objective_id=objective.id,
            attempt_id=attempt.id,
            evidence_type="correct_response",
        )
    )
    db_session.add(
        UserObjectiveProgress(
            user_language_id=profile.id,
            objective_id=objective.id,
            state=MasteryState.MASTERED,
            started_at=datetime.now(timezone.utc),
        )
    )
    db_session.add(
        LearningGoal(
            user_language_id=profile.id,
            goal_type="personal",
            description="Viajar",
            priority=1,
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/onboarding/complete",
        json={
            "language_code": "en",
            "level_choice": "self_declared",
            "cefr_level": "A2",
            "goal": "Trabalho e carreira",
            "minutes_per_day": 15,
        },
        headers=auth,
    )
    assert response.status_code == 200
    db_session.expire_all()
    saved = db_session.get(UserLanguage, profile.id)
    progress = db_session.scalar(
        select(UserObjectiveProgress).where(
            UserObjectiveProgress.user_language_id == profile.id,
            UserObjectiveProgress.objective_id == objective.id,
        )
    )
    goals = list(
        db_session.scalars(
            select(LearningGoal.description).where(
                LearningGoal.user_language_id == profile.id,
                LearningGoal.goal_type == "personal",
            )
        )
    )
    assert saved.current_level == "A2"
    assert progress.state == MasteryState.MASTERED
    assert goals == ["Trabalho e carreira"]
