"""E-mail diário da missão do dia.

O e-mail é o gatilho de volta ao app. As regras que os testes travam:
uma vez por dia, nunca dois; falha de envio não consome o dia; perfil sem
cronograma é pulado em silêncio, sem e-mail dizendo "não há nada"; e a rota
de disparo não existe sem chave configurada.
"""

from datetime import date

import pytest
from sqlalchemy import select

from app.models import (
    CurriculumDay,
    CurriculumWeek,
    Language,
    LearningProgressEvent,
    User,
    UserLanguage,
)
from app.services.curriculum_generator import generate_curriculum
from app.services.daily_email import DAILY_EMAIL_SENT, dispatch_daily_emails
from app.core.curriculum import DayStatus


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


@pytest.fixture
def sent(monkeypatch):
    """Captura os envios em vez de chamar o Resend."""
    calls: list[dict] = []

    def fake_send(*, to: str, subject: str, html: str) -> None:
        calls.append({"to": to, "subject": subject, "html": html})

    monkeypatch.setattr("app.services.daily_email.send_email", fake_send)
    return calls


def test_envia_a_missao_do_dia_aberto_com_link(db_session, sent):
    profile = _profile(db_session)
    generate_curriculum(db_session, profile.id, 90)
    db_session.commit()

    result = dispatch_daily_emails(db_session, today=date(2026, 9, 25))

    assert result["sent"] == 1
    assert len(sent) == 1
    assert "/cronograma/dia/" in sent[0]["html"]
    assert "BeFluent" in sent[0]["subject"]


def test_nao_envia_duas_vezes_no_mesmo_dia(db_session, sent):
    profile = _profile(db_session)
    generate_curriculum(db_session, profile.id, 90)
    db_session.commit()

    first = dispatch_daily_emails(db_session, today=date(2026, 9, 25))
    second = dispatch_daily_emails(db_session, today=date(2026, 9, 25))

    assert first["sent"] == 1
    assert second["sent"] == 0
    assert second["skipped"] == 1
    assert len(sent) == 1


def test_falha_de_envio_libera_nova_tentativa_no_mesmo_dia(db_session, monkeypatch):
    from app.services.email import EmailSendError

    profile = _profile(db_session)
    generate_curriculum(db_session, profile.id, 90)
    db_session.commit()

    def explode(**_kwargs):
        raise EmailSendError("Resend fora do ar")

    monkeypatch.setattr("app.services.daily_email.send_email", explode)
    failed = dispatch_daily_emails(db_session, today=date(2026, 9, 25))

    assert failed["failed"] == 1
    assert failed["sent"] == 0
    # A reivindicação foi desfeita: nenhum evento sobrou marcando o dia.
    assert (
        db_session.scalar(
            select(LearningProgressEvent.id).where(
                LearningProgressEvent.event_type == DAILY_EMAIL_SENT
            )
        )
        is None
    )

    calls: list[dict] = []
    monkeypatch.setattr(
        "app.services.daily_email.send_email",
        lambda **kwargs: calls.append(kwargs),
    )
    retried = dispatch_daily_emails(db_session, today=date(2026, 9, 25))

    assert retried["sent"] == 1
    assert len(calls) == 1


def test_perfil_sem_cronograma_e_pulado_sem_email(db_session, sent):
    _profile(db_session)
    db_session.commit()

    result = dispatch_daily_emails(db_session, today=date(2026, 9, 25))

    assert result["sent"] == 0
    assert result["skipped"] == 1
    assert sent == []


def test_cronograma_todo_concluido_nao_gera_email(db_session, sent):
    profile = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90)
    for day in db_session.scalars(
        select(CurriculumDay)
        .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
        .where(CurriculumWeek.curriculum_id == curriculum.id)
    ):
        day.status = DayStatus.COMPLETED
    db_session.commit()

    result = dispatch_daily_emails(db_session, today=date(2026, 9, 25))

    assert result["sent"] == 0
    assert sent == []


def test_tema_do_dia_vai_escapado_no_html(db_session, sent):
    profile = _profile(db_session)
    curriculum = generate_curriculum(db_session, profile.id, 90)
    week = db_session.scalar(
        select(CurriculumWeek)
        .where(CurriculumWeek.curriculum_id == curriculum.id)
        .order_by(CurriculumWeek.week_number)
    )
    week.theme = "Rotina <script>alert(1)</script>"
    db_session.commit()

    dispatch_daily_emails(db_session, today=date(2026, 9, 25))

    assert "<script>" not in sent[0]["html"]
    assert "&lt;script&gt;" in sent[0]["html"]


def test_rota_sem_chave_configurada_responde_503(client, monkeypatch):
    from app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.delenv("DAILY_EMAIL_KEY", raising=False)
    response = client.post("/api/v1/daily-email/dispatch")
    get_settings.cache_clear()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "dispatch_not_configured"


def test_rota_com_chave_errada_responde_401(client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("DAILY_EMAIL_KEY", "chave-certa")
    get_settings.cache_clear()
    response = client.post(
        "/api/v1/daily-email/dispatch", headers={"X-Dispatch-Key": "chave-errada"}
    )
    get_settings.cache_clear()

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "dispatch_key_invalid"


def test_rota_com_chave_certa_dispara(client, db_session, monkeypatch, sent):
    from app.core.config import get_settings

    profile = _profile(db_session)
    generate_curriculum(db_session, profile.id, 90)
    db_session.commit()

    monkeypatch.setenv("DAILY_EMAIL_KEY", "chave-certa")
    get_settings.cache_clear()
    response = client.post(
        "/api/v1/daily-email/dispatch", headers={"X-Dispatch-Key": "chave-certa"}
    )
    get_settings.cache_clear()

    assert response.status_code == 200
    assert response.json()["sent"] == 1
