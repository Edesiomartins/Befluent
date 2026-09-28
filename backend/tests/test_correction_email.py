"""E-mail de correção — o segundo e-mail do dia.

Vai atrás das sessões encerradas e manda a correção que o boletim já gravou.
As regras que os testes travam: uma correção por sessão, nunca duas; sessão sem
resposta corrigível não gera e-mail; falha de envio não consome a sessão;
sessão fechada fora da janela de varredura não é reenviada anos depois; e a
rota de disparo não existe sem chave configurada.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import LearningProgressEvent, TeachingFlowSession
from app.services.correction_email import (
    CORRECTION_EMAIL_SENT,
    build_correction,
    dispatch_correction_emails,
)

# Reaproveita o roteiro que conduz uma sessão lexical do início ao fim.
from tests.test_lesson_report import _answer_everything, _lesson, _profile


@pytest.fixture
def sent(monkeypatch):
    calls: list[dict] = []

    def fake_send(*, to: str, subject: str, html: str) -> None:
        calls.append({"to": to, "subject": subject, "html": html})

    monkeypatch.setattr("app.services.correction_email.send_email", fake_send)
    return calls


def _finished_session(client, auth, db, *, mode: str = "wrong") -> TeachingFlowSession:
    """Leva uma sessão até o fim e devolve a linha já encerrada."""
    profile = _profile(db)
    lesson = _lesson(db, profile)
    _answer_everything(client, auth, db, lesson.id, mode=mode)
    db.rollback()
    session = db.scalar(
        select(TeachingFlowSession)
        .where(TeachingFlowSession.lesson_id == lesson.id)
        .order_by(TeachingFlowSession.updated_at.desc())
    )
    assert session is not None
    assert session.status == "closed", "o roteiro deveria ter encerrado a sessão"
    return session


def test_sessao_encerrada_recebe_a_correcao_com_o_certo_e_o_porque(client, auth, db_session, sent):
    _finished_session(client, auth, db_session)

    result = dispatch_correction_emails(db_session)

    assert result["sent"] == 1
    assert len(sent) == 1
    assert "Correção" in sent[0]["subject"]
    assert "/boletim/" in sent[0]["html"]


def test_nao_envia_duas_correcoes_da_mesma_sessao(client, auth, db_session, sent):
    _finished_session(client, auth, db_session)

    first = dispatch_correction_emails(db_session)
    second = dispatch_correction_emails(db_session)

    assert first["sent"] == 1
    assert second["sent"] == 0
    assert second["skipped"] == 1
    assert len(sent) == 1


def test_falha_de_envio_libera_nova_tentativa(client, auth, db_session, monkeypatch):
    from app.services.email import EmailSendError

    _finished_session(client, auth, db_session)

    def explode(**_kwargs):
        raise EmailSendError("Resend fora do ar")

    monkeypatch.setattr("app.services.correction_email.send_email", explode)
    failed = dispatch_correction_emails(db_session)

    assert failed["failed"] == 1
    assert failed["sent"] == 0
    assert (
        db_session.scalar(
            select(LearningProgressEvent.id).where(
                LearningProgressEvent.event_type == CORRECTION_EMAIL_SENT
            )
        )
        is None
    )

    calls: list[dict] = []
    monkeypatch.setattr(
        "app.services.correction_email.send_email",
        lambda **kwargs: calls.append(kwargs),
    )
    retried = dispatch_correction_emails(db_session)

    assert retried["sent"] == 1
    assert len(calls) == 1


def test_sessao_fechada_fora_da_janela_nao_e_varrida(client, auth, db_session, sent):
    session = _finished_session(client, auth, db_session)
    session.closed_at = datetime.now(timezone.utc) - timedelta(days=3)
    db_session.commit()

    result = dispatch_correction_emails(db_session, within_hours=24)

    assert result["sent"] == 0
    assert sent == []


def test_sessao_sem_resposta_corrigivel_nao_gera_email(client, auth, db_session, sent, monkeypatch):
    """Sessão encerrada cujo boletim está vazio não vira e-mail de correção."""
    session = _finished_session(client, auth, db_session)
    from app.models import LearningAttempt

    for attempt in db_session.scalars(
        select(LearningAttempt).where(LearningAttempt.lesson_id == session.lesson_id)
    ):
        attempt.report_json = None
    db_session.commit()

    result = dispatch_correction_emails(db_session)

    assert result["sent"] == 0
    assert result["skipped"] == 1
    assert sent == []


def test_rota_sem_chave_configurada_responde_503(client, monkeypatch):
    from app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.delenv("DAILY_EMAIL_KEY", raising=False)
    response = client.post("/api/v1/correction-email/dispatch")
    get_settings.cache_clear()

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "dispatch_not_configured"


def test_rota_com_chave_errada_responde_401(client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("DAILY_EMAIL_KEY", "chave-certa")
    get_settings.cache_clear()
    response = client.post(
        "/api/v1/correction-email/dispatch", headers={"X-Dispatch-Key": "errada"}
    )
    get_settings.cache_clear()

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "dispatch_key_invalid"


def test_rota_com_chave_certa_dispara(client, auth, db_session, monkeypatch, sent):
    from app.core.config import get_settings

    _finished_session(client, auth, db_session)
    db_session.commit()

    monkeypatch.setenv("DAILY_EMAIL_KEY", "chave-certa")
    get_settings.cache_clear()
    response = client.post(
        "/api/v1/correction-email/dispatch", headers={"X-Dispatch-Key": "chave-certa"}
    )
    get_settings.cache_clear()

    assert response.status_code == 200
    assert response.json()["sent"] == 1


def test_segunda_sessao_na_mesma_licao_so_manda_o_que_e_novo(client, auth, db_session, sent):
    """O boletim é da lição inteira; a correção é da sessão.

    Sem recorte, a correção da segunda sessão repetiria os itens da primeira.
    A segunda sessão tem seu próprio conjunto de exercícios (é revisão dos itens
    já cadastrados), então o teste não compara contagens: verifica que nenhuma
    resposta anterior ao início da segunda sessão entrou, e que o boletim da
    lição é de fato maior do que a correção enviada.
    """
    from app.models import Lesson
    from app.services.lesson_report import lesson_report

    first = _finished_session(client, auth, db_session)
    dispatch_correction_emails(db_session)
    db_session.commit()

    _answer_everything(client, auth, db_session, first.lesson_id, mode="wrong")
    db_session.rollback()
    second = db_session.scalar(
        select(TeachingFlowSession)
        .where(
            TeachingFlowSession.lesson_id == first.lesson_id,
            TeachingFlowSession.id != first.id,
        )
        .order_by(TeachingFlowSession.updated_at.desc())
    )
    assert second is not None, "a segunda sessão deveria existir"

    correction = build_correction(db_session, second)
    assert correction is not None

    started_at = second.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    for entry in correction.entries:
        answered = datetime.fromisoformat(entry["answered_at"])
        if answered.tzinfo is None:
            answered = answered.replace(tzinfo=timezone.utc)
        assert answered >= started_at, (
            f"entrada de {answered} é anterior ao início da sessão ({started_at})"
        )

    lesson = db_session.get(Lesson, first.lesson_id)
    boletim_inteiro = lesson_report(db_session, lesson)["summary"]["total"]
    assert boletim_inteiro > correction.total, (
        "o boletim da lição deveria ter mais entradas que a correção da segunda "
        "sessão — se forem iguais, o recorte não cortou nada"
    )
