"""Boletim da lição: o que o aluno errou, o certo e o porquê — guardado.

Antes disto o feedback era gerado no momento da resposta e se perdia. As
regras que os testes travam: cada resposta deixa uma entrada permanente; a
entrada guarda o enunciado e a resposta certa, não só o acerto; acerto por
"continuar" (atividade expositiva) não entra no boletim; e o boletim é do dono
da lição, de mais ninguém.
"""

from sqlalchemy import select

from app.models import (
    Language,
    LearningAttempt,
    Lesson,
    TeachingFlowSession,
    User,
    UserLanguage,
)


def _profile(db, *, email: str = "admin@befluent.local") -> UserLanguage:
    user = db.scalar(select(User).where(User.email == email))
    language = db.scalar(select(Language).where(Language.code == "en"))
    profile = UserLanguage(
        user_id=user.id,
        language_id=language.id,
        is_active=True,
        onboarding_completed=True,
        diagnostic_completed=True,
        current_level="A2",
        level_source="placement_test",
        vocabulary_grammar_level="A2",
        reading_level="A2",
        listening_level="A2",
        writing_level="A2",
        speaking_level="A2",
    )
    db.add(profile)
    db.flush()
    return profile


def _lesson(db, profile: UserLanguage) -> Lesson:
    lesson = Lesson(
        user_language_id=profile.id,
        title="Vocabulário de viagem",
        objective="Usar palavras de viagem",
        status="active",
        content_json={
            "mode": "vocabulary",
            "language_code": "en",
            "items": [
                {
                    "term": "hello",
                    "translation": "olá",
                    "example": "Hello, Ana!",
                    "example_translation": "Olá, Ana!",
                },
                {"term": "goodbye", "translation": "tchau"},
            ],
        },
    )
    db.add(lesson)
    db.commit()
    return lesson


def _canonical_answer(db, lesson_id: str, cursor: int) -> str:
    """Gabarito da atividade atual, lido do banco.

    O cliente não recebe gabarito (é o ponto do `hide_answer_key`), então o
    teste consulta a sessão para poder errar — ou acertar — de propósito.
    """
    db.rollback()  # encerra a transação para ver o que o cliente já gravou
    flow = db.scalar(
        select(TeachingFlowSession)
        .where(TeachingFlowSession.lesson_id == lesson_id)
        .order_by(TeachingFlowSession.updated_at.desc())
    )
    activities = (flow.payload_json or {}).get("activities") or [] if flow else []
    activity = activities[cursor] if 0 <= cursor < len(activities) else {}
    return str(activity.get("canonical_answer") or "")


def _answer_everything(client, auth, db, lesson_id: str, *, mode: str) -> None:
    """Responde a sessão inteira. `mode`: "wrong" erra onde há alternativa."""
    session = client.post(
        f"/api/v1/lessons/{lesson_id}/vocabulary-cycle/start",
        headers=auth,
        json={"size": "short"},
    ).json()
    for _ in range(40):
        activity = session.get("current_activity")
        if not activity or session.get("flow", {}).get("status") != "active":
            break
        cursor = session["flow"]["activity_cursor"]
        options = activity.get("options") or []
        answer = ""
        if options:
            expected = _canonical_answer(db, lesson_id, cursor)
            if mode == "wrong":
                answer = next(
                    (option for option in options if option != expected), options[0]
                )
            else:
                answer = expected if expected in options else options[0]
        response = client.post(
            f"/api/v1/lessons/{lesson_id}/vocabulary-cycle/answer",
            headers=auth,
            json={"activity_index": cursor, "student_response": answer},
        )
        if response.status_code != 200:
            break
        session = response.json()


def test_resposta_produtiva_deixa_entrada_no_boletim(client, auth, db_session):
    profile = _profile(db_session)
    lesson = _lesson(db_session, profile)

    _answer_everything(client, auth, db_session, lesson.id, mode="wrong")

    report = client.get(f"/api/v1/lessons/{lesson.id}/report", headers=auth)
    assert report.status_code == 200
    body = report.json()
    assert body["lesson"]["id"] == lesson.id
    assert body["entries"], "o boletim não pode voltar vazio depois de respostas reais"
    first = body["entries"][0]
    assert first["prompt"], "a entrada precisa guardar o enunciado"
    assert "correct_answer" in first
    assert "result" in first


def test_boletim_guarda_o_porque_do_erro(client, auth, db_session):
    profile = _profile(db_session)
    lesson = _lesson(db_session, profile)

    _answer_everything(client, auth, db_session, lesson.id, mode="wrong")

    body = client.get(f"/api/v1/lessons/{lesson.id}/report", headers=auth).json()
    errors = [entry for entry in body["entries"] if entry["result"] == "incorrect"]
    assert errors, "o roteiro do teste erra de propósito; deveria haver erro"
    assert any(entry.get("why_correct") for entry in errors)
    assert body["summary"]["incorrect"] == len(errors)


def test_continuar_em_atividade_expositiva_nao_entra_no_boletim(client, auth, db_session):
    profile = _profile(db_session)
    lesson = _lesson(db_session, profile)

    _answer_everything(client, auth, db_session, lesson.id, mode="correct")

    body = client.get(f"/api/v1/lessons/{lesson.id}/report", headers=auth).json()
    prompts = [entry["activity_type"] for entry in body["entries"]]
    assert "presentation" not in prompts
    # A tentativa existe no banco (é histórico), mas não vira linha de boletim.
    assert db_session.scalar(
        select(LearningAttempt.id).where(LearningAttempt.lesson_id == lesson.id)
    )


def test_boletim_de_licao_de_outro_usuario_responde_404(client, auth, db_session, other_user):
    language = db_session.scalar(select(Language).where(Language.code == "en"))
    alien_profile = UserLanguage(
        user_id=other_user,
        language_id=language.id,
        is_active=True,
        onboarding_completed=True,
        current_level="A1",
    )
    db_session.add(alien_profile)
    db_session.flush()
    alien_lesson = Lesson(
        user_language_id=alien_profile.id,
        title="Lição de outra conta",
        objective="—",
        status="active",
        content_json={"mode": "vocabulary", "language_code": "en", "items": []},
    )
    db_session.add(alien_lesson)
    db_session.commit()

    response = client.get(f"/api/v1/lessons/{alien_lesson.id}/report", headers=auth)

    assert response.status_code == 404


def test_boletim_de_licao_sem_resposta_vem_vazio_sem_erro(client, auth, db_session):
    profile = _profile(db_session)
    lesson = _lesson(db_session, profile)

    response = client.get(f"/api/v1/lessons/{lesson.id}/report", headers=auth)

    assert response.status_code == 200
    assert response.json()["entries"] == []
    assert response.json()["summary"]["total"] == 0
