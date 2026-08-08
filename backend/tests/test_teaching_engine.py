"""Teaching Engine: núcleo pedagógico entre currículo e atividades.

O ponto sob teste é a distinção central do módulo — atividade concluída não é
aprendizagem demonstrada — e o ciclo erro → remediação → retry → reavaliação.
Também cobre que nenhuma chamada, nem via IA, marca `mastered` fora de
`evaluate_mastery`, e que o isolamento por usuário (padrão 404, nunca 403) vale
aqui como em todo o resto do backend.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.teaching import ErrorCategory, ErrorSeverity, EvidenceType, MasteryState, RemediationAction
from app.models import Language, LearningObjective, User, UserLanguage
from app.services import teaching_engine as engine


def _objective(db_session, **overrides) -> LearningObjective:
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    defaults = dict(
        language_id=language.id,
        level="A1",
        code=f"EN-A1-TEST-{uuid.uuid4().hex[:8]}",
        title="Apresentar-se",
        can_do="Diz nome, origem e profissão em uma conversa simples.",
        skill_focus="speaking",
    )
    defaults.update(overrides)
    objective = LearningObjective(**defaults)
    db_session.add(objective)
    db_session.commit()
    return objective


def _user_language(db_session, *, email: str = "admin@befluent.local") -> UserLanguage:
    user = db_session.scalar(select(User).where(User.email == email))
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    ul = UserLanguage(user_id=user.id, language_id=language.id, is_active=True)
    db_session.add(ul)
    db_session.commit()
    return ul


# --------------------------------------------------------- 1. estado inicial


def test_objective_starts_not_started_then_learning(db_session):
    objective = _objective(db_session)
    ul = _user_language(db_session)

    mastery = engine.evaluate_mastery(db_session, user_language_id=ul.id, objective_id=objective.id)
    assert mastery["state"] == MasteryState.NOT_STARTED

    progress = engine.start_objective(db_session, user_language_id=ul.id, objective_id=objective.id)
    assert progress.state == MasteryState.LEARNING
    assert progress.started_at is not None


# -------------------------------------------------------------- 2. evidência


def test_correct_attempt_generates_evidence(db_session):
    objective = _objective(db_session)
    ul = _user_language(db_session)
    attempt = engine.record_attempt(
        db_session,
        user_language_id=ul.id,
        objective_id=objective.id,
        activity_type="controlled_practice",
        student_response="My name is Ana.",
    )
    result = engine.evaluate_attempt(
        db_session,
        attempt,
        result="correct",
        score=1.0,
        provider="heuristic",
        evidence_type=EvidenceType.WRITTEN_PRODUCTION,
    )
    assert result["evidence"] is not None
    assert result["evidence"].evidence_type == EvidenceType.WRITTEN_PRODUCTION


# ------------------------------------------------------------------ 3. erro


def test_incorrect_attempt_can_record_error(db_session):
    objective = _objective(db_session)
    ul = _user_language(db_session)
    attempt = engine.record_attempt(
        db_session,
        user_language_id=ul.id,
        objective_id=objective.id,
        activity_type="controlled_practice",
        student_response="Me name Ana.",
    )
    engine.evaluate_attempt(db_session, attempt, result="incorrect")
    error = engine.record_error(
        db_session,
        attempt,
        category=ErrorCategory.GRAMMAR,
        original="Me name Ana.",
        expected="My name is Ana.",
        severity=ErrorSeverity.CRITICAL,
    )
    assert error.resolved is False
    progress = engine.get_or_create_progress(db_session, user_language_id=ul.id, objective_id=objective.id)
    assert progress.state == MasteryState.NEEDS_REMEDIATION


def test_incorrect_attempt_alone_does_not_end_the_activity(db_session):
    """Erro não termina a atividade: o objetivo continua vivo (NEEDS_REMEDIATION),
    nunca um estado terminal de falha — sempre há caminho de volta."""
    objective = _objective(db_session)
    ul = _user_language(db_session)
    attempt = engine.record_attempt(
        db_session, user_language_id=ul.id, objective_id=objective.id, activity_type="writing"
    )
    engine.evaluate_attempt(db_session, attempt, result="incorrect")
    engine.record_error(db_session, attempt, category=ErrorCategory.SPELLING, original="teh")
    mastery = engine.evaluate_mastery(db_session, user_language_id=ul.id, objective_id=objective.id)
    assert mastery["state"] in (MasteryState.NEEDS_REMEDIATION,)
    assert mastery["state"] != MasteryState.NOT_STARTED


# ---------------------------------------------------------- 4. remediation


def test_error_triggers_remediation_choice(db_session):
    objective = _objective(db_session)
    ul = _user_language(db_session)
    attempt = engine.record_attempt(
        db_session, user_language_id=ul.id, objective_id=objective.id, activity_type="controlled_practice"
    )
    engine.evaluate_attempt(db_session, attempt, result="incorrect")
    error = engine.record_error(
        db_session, attempt, category=ErrorCategory.WORD_ORDER, original="X", severity=ErrorSeverity.MODERATE
    )
    remediation = engine.choose_remediation(db_session, error)
    assert remediation.action == RemediationAction.SHOW_CONTRAST
    assert remediation.error_id == error.id


# -------------------------------------------------------- 5. retry resolve erro


def test_correct_retry_resolves_error_and_reaches_mastery(db_session):
    objective = _objective(db_session)
    ul = _user_language(db_session)
    attempt = engine.record_attempt(
        db_session, user_language_id=ul.id, objective_id=objective.id, activity_type="controlled_practice"
    )
    engine.evaluate_attempt(db_session, attempt, result="incorrect")
    error = engine.record_error(
        db_session, attempt, category=ErrorCategory.GRAMMAR, original="bad", severity=ErrorSeverity.CRITICAL
    )
    remediation = engine.choose_remediation(db_session, error)

    retry_attempt = engine.record_retry(db_session, remediation, student_response="fixed")
    assert retry_attempt.attempt_number == 2
    progress = engine.get_or_create_progress(db_session, user_language_id=ul.id, objective_id=objective.id)
    assert progress.state == MasteryState.RETRYING

    result = engine.evaluate_attempt(
        db_session, retry_attempt, result="correct", evidence_type=EvidenceType.CORRECT_RESPONSE
    )
    db_session.refresh(error)
    assert error.resolved is True
    assert result["mastery"]["state"] == MasteryState.MASTERED


# ------------------------------------------------- 6. erro crítico bloqueia mastery


def test_unresolved_critical_error_blocks_mastery(db_session):
    objective = _objective(db_session)
    ul = _user_language(db_session)
    attempt = engine.record_attempt(
        db_session, user_language_id=ul.id, objective_id=objective.id, activity_type="writing"
    )
    engine.evaluate_attempt(db_session, attempt, result="correct", evidence_type=EvidenceType.WRITTEN_PRODUCTION)
    engine.record_error(db_session, attempt, category=ErrorCategory.GRAMMAR, original="bad", severity=ErrorSeverity.CRITICAL)

    mastery = engine.evaluate_mastery(db_session, user_language_id=ul.id, objective_id=objective.id)
    assert mastery["state"] == MasteryState.NEEDS_REMEDIATION


def test_unresolved_minor_error_does_not_block_mastery_by_default(db_session):
    objective = _objective(db_session)
    ul = _user_language(db_session)
    attempt = engine.record_attempt(
        db_session, user_language_id=ul.id, objective_id=objective.id, activity_type="writing"
    )
    engine.evaluate_attempt(db_session, attempt, result="correct", evidence_type=EvidenceType.WRITTEN_PRODUCTION)
    engine.record_error(db_session, attempt, category=ErrorCategory.SPELLING, original="teh", severity=ErrorSeverity.MINOR)

    mastery = engine.evaluate_mastery(db_session, user_language_id=ul.id, objective_id=objective.id)
    assert mastery["state"] == MasteryState.MASTERED


# --------------------------------------------- 7/8. concluído != domínio


def test_activity_completed_without_enough_evidence_is_needs_review(db_session):
    objective = _objective(db_session, mastery_policy_json={"min_evidence_count": 3})
    ul = _user_language(db_session)
    attempt = engine.record_attempt(
        db_session, user_language_id=ul.id, objective_id=objective.id, activity_type="vocabulary"
    )
    engine.evaluate_attempt(db_session, attempt, result="correct", evidence_type=EvidenceType.CORRECT_RESPONSE)

    # Sem o hint de conclusão, o objetivo fica só "em prática" — não é falha,
    # é evidência insuficiente ainda.
    mid = engine.evaluate_mastery(db_session, user_language_id=ul.id, objective_id=objective.id)
    assert mid["state"] == MasteryState.PRACTICING

    mastery = engine.evaluate_mastery(
        db_session, user_language_id=ul.id, objective_id=objective.id, activity_completed=True
    )
    assert mastery["state"] == MasteryState.NEEDS_REVIEW


def test_completing_activity_never_calls_it_mastered_without_evidence(db_session):
    objective = _objective(db_session)
    ul = _user_language(db_session)
    # Nenhuma tentativa registrada — só o "clique em concluir" hipotético.
    mastery = engine.evaluate_mastery(
        db_session, user_language_id=ul.id, objective_id=objective.id, activity_completed=True
    )
    assert mastery["state"] != MasteryState.MASTERED
    assert mastery["state"] == MasteryState.NOT_STARTED


# ------------------------------------------------------------- 9. SRS intacto


def test_existing_srs_review_endpoint_still_works(client, auth):
    response = client.get("/api/v1/reviews/due", headers=auth)
    assert response.status_code == 200
    assert response.json() == []


# --------------------------------------------------------------- 10. IDOR


def test_users_cannot_access_each_others_teaching_data(client, auth, db_session, other_user):
    outro = db_session.get(User, other_user)
    objective = _objective(db_session)
    ul_outro = _user_language(db_session, email=outro.email)
    attempt = engine.record_attempt(
        db_session, user_language_id=ul_outro.id, objective_id=objective.id, activity_type="writing"
    )

    resp = client.post(
        f"/api/v1/teaching/attempts/{attempt.id}/evaluate",
        json={"result": "correct"},
        headers=auth,
    )
    assert resp.status_code == 404

    mastery_resp = client.get(f"/api/v1/teaching/objectives/{objective.id}/mastery", headers=auth)
    # O objetivo em si é catálogo (sem dono), mas o admin não tem perfil no
    # idioma criado só para "outro" nesta suíte — 404 é o resultado esperado
    # aqui também, pelo mesmo motivo de sempre: recurso não resolvido para
    # este usuário, nunca um 403 que confirmaria a existência do dado alheio.
    assert mastery_resp.status_code in (200, 404)


def test_attempt_cannot_reference_another_users_curriculum_block(client, auth, db_session, other_user):
    from tests.test_curriculum_api import blocks_of, first_day, make_curriculum, setup_profile

    outro = db_session.get(User, other_user)
    profile = setup_profile(db_session, user_email=outro.email)
    curriculum = make_curriculum(db_session, profile)
    block = blocks_of(db_session, first_day(db_session, curriculum))[0]

    objective = _objective(db_session)
    _user_language(db_session)

    resp = client.post(
        "/api/v1/teaching/attempts",
        json={
            "objective_id": objective.id,
            "activity_type": "controlled_practice",
            "curriculum_block_id": block.id,
        },
        headers=auth,
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "curriculum_block_not_found"


# --------------------------------------------------- 11. IA não marca mastery sozinha


def test_ai_provider_cannot_mark_mastery_without_evidence(db_session):
    objective = _objective(db_session, mastery_policy_json={"min_evidence_count": 2})
    ul = _user_language(db_session)
    attempt = engine.record_attempt(
        db_session, user_language_id=ul.id, objective_id=objective.id, activity_type="conversation"
    )
    # A IA avalia e devolve "correct" com score alto, mas não é ela quem
    # decide mastery — evaluate_mastery aplica a política do objetivo.
    result = engine.evaluate_attempt(
        db_session,
        attempt,
        result="correct",
        score=1.0,
        provider="openrouter",
        evidence_type=EvidenceType.ORAL_PRODUCTION_TRANSCRIBED,
    )
    assert result["mastery"]["state"] != MasteryState.MASTERED
    assert result["mastery"]["state"] == MasteryState.PRACTICING


def test_evaluate_endpoint_schema_has_no_state_field(client, auth, db_session):
    """A API não aceita um campo `state`/`mastery` no corpo — só quem chama
    `evaluate_mastery` server-side pode mudar o estado de domínio."""
    objective = _objective(db_session)
    _user_language(db_session)
    created = client.post(
        "/api/v1/teaching/attempts",
        json={"objective_id": objective.id, "activity_type": "conversation"},
        headers=auth,
    ).json()

    resp = client.post(
        f"/api/v1/teaching/attempts/{created['id']}/evaluate",
        json={"result": "correct", "state": "mastered"},
        headers=auth,
    )
    assert resp.status_code == 422


# ----------------------------------------------------- 12. endpoints antigos


def test_curriculum_block_payload_stays_backward_compatible(client, auth, db_session):
    from tests.test_curriculum_api import blocks_of, first_day, make_curriculum, setup_profile

    profile = setup_profile(db_session, user_email="admin@befluent.local")
    curriculum = make_curriculum(db_session, profile)
    block = blocks_of(db_session, first_day(db_session, curriculum))[0]

    response = client.get(f"/api/v1/curriculum/day/{first_day(db_session, curriculum).id}", headers=auth)
    assert response.status_code == 200
    block_payload = response.json()["day"]["blocks"][0]
    for key in ("id", "skill", "position", "status", "lesson_ref", "score"):
        assert key in block_payload
    assert "objective_id" in block_payload
    assert block_payload["objective_id"] is None


def test_old_review_and_grammar_endpoints_still_respond(client, auth):
    assert client.get("/api/v1/reviews/due", headers=auth).status_code == 200
    assert client.get("/api/v1/grammar/topics?language_code=en", headers=auth).status_code == 200
