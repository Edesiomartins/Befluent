"""E-mail de correção — o segundo e-mail do dia.

O primeiro e-mail é o convite (`daily_email.py`): chega de manhã e traz a missão
do dia. Este é o outro lado do ciclo: depois que a sessão termina, manda a
correção — o que foi respondido, o certo e o porquê — para o erro ser entendido
no mesmo dia, sem depender de o aluno voltar à tela procurar.

Conteúdo: o boletim que `lesson_report` já grava em
`learning_attempts.report_json` no momento da resposta. Este módulo **não**
recalcula correção nenhuma; se o boletim está vazio, não há e-mail.

Gatilho: o fim da sessão é um evento interno (`teaching_flow` fecha a sessão e
grava `closed_at`), não um horário. Ainda assim o envio é feito por varredura
agendada, e não dentro da requisição do aluno, por dois motivos:

1. a resposta do último exercício não deve esperar o provedor de e-mail;
2. varredura repete a tentativa sozinha quando o provedor falha — envio dentro
   da requisição perderia a correção em silêncio.

A janela (`within_hours`) existe para a primeira execução não despejar o
histórico inteiro na caixa de entrada.
"""

from __future__ import annotations

import html
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Lesson, TeachingFlowSession, User, UserLanguage
from app.services.email import EmailSendError, send_email
from app.services.language_progress import record_product_event
from app.services.lesson_report import lesson_report

logger = logging.getLogger(__name__)

#: Marca "a correção desta sessão já saiu".
CORRECTION_EMAIL_SENT = "correction_email_sent"

#: Padrão da varredura. Um dia cobre com folga um cron de 15 minutos e ainda
#: absorve algumas horas de indisponibilidade do provedor.
DEFAULT_WINDOW_HOURS = 24

#: Teto de itens no corpo do e-mail. O resto fica no boletim, que é a página
#: completa — um e-mail de sessão longa não precisa ter 40 blocos.
MAX_EMAIL_ENTRIES = 12


def _as_utc(value: datetime) -> datetime:
    """SQLite devolve `DateTime(timezone=True)` sem `tzinfo`; trata como UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _answered_in_session(entry: dict, *, started_at: datetime) -> bool:
    """A entrada do boletim pertence a esta sessão?

    O boletim é da **lição**; a correção é da **sessão**. Sem este recorte, uma
    segunda sessão na mesma lição reenviaria os itens da primeira.

    Entrada sem data utilizável entra: esconder uma correção por causa de um
    carimbo ilegível seria pior do que repeti-la.
    """
    raw = entry.get("answered_at")
    if not raw:
        return True
    try:
        answered = datetime.fromisoformat(str(raw))
    except ValueError:
        return True
    return _as_utc(answered) >= _as_utc(started_at)


@dataclass(frozen=True)
class Correction:
    """O que o e-mail de uma sessão precisa, já resolvido."""

    lesson_id: str
    lesson_title: str
    entries: list[dict]
    total: int
    incorrect: int


def build_correction(db: Session, session: TeachingFlowSession) -> Correction | None:
    """Correção da sessão, ou `None` quando não há o que corrigir.

    Só as respostas **desta** sessão entram: o boletim é da lição e pode conter
    sessões anteriores da mesma lição.

    `None` cobre sessão sem lição associada e boletim vazio — o caso de uma
    sessão composta só de atividades expositivas, em que o aluno apertou
    "continuar" e não produziu resposta nenhuma.
    """
    if not session.lesson_id:
        return None
    lesson = db.get(Lesson, session.lesson_id)
    if lesson is None:
        return None
    report = lesson_report(db, lesson)
    entries = [
        entry
        for entry in report["entries"]
        if _answered_in_session(entry, started_at=session.started_at)
    ]
    if not entries:
        return None
    return Correction(
        lesson_id=lesson.id,
        lesson_title=lesson.title or "Sessão de estudo",
        entries=entries[:MAX_EMAIL_ENTRIES],
        total=len(entries),
        incorrect=sum(1 for entry in entries if entry.get("result") == "incorrect"),
    )


def correction_email_subject(correction: Correction) -> str:
    return f"Correção — {correction.lesson_title} | BeFluent"


def _entry_html(entry: dict) -> str:
    wrong = entry.get("result") == "incorrect"
    parts = [
        '<li style="margin: 0 0 20px;">',
        f'<p style="font-size: 12px; font-weight: 600; letter-spacing: .04em;'
        f' text-transform: uppercase; color: {"#b91c1c" if wrong else "#6b7280"}; margin: 0 0 6px;">'
        f'{"Para revisar" if wrong else "Correta"}</p>',
    ]
    if entry.get("prompt"):
        parts.append(
            f'<p style="font-size: 15px; line-height: 1.6; margin: 0 0 6px;">'
            f'{html.escape(str(entry["prompt"]))}</p>'
        )
    parts.append(
        f'<p style="font-size: 14px; line-height: 1.6; margin: 0; color: #6b7280;">'
        f'Sua resposta: <strong style="color: {"#b91c1c" if wrong else "#1a1a2e"};">'
        f'{html.escape(str(entry.get("student_response") or "—"))}</strong></p>'
    )
    if wrong and entry.get("correct_answer"):
        parts.append(
            f'<p style="font-size: 14px; line-height: 1.6; margin: 0; color: #6b7280;">'
            f'Resposta certa: <strong style="color: #1a1a2e;">'
            f'{html.escape(str(entry["correct_answer"]))}</strong></p>'
        )
    for field in ("why_selected", "why_correct", "remember"):
        value = entry.get(field)
        if value:
            parts.append(
                f'<p style="font-size: 14px; line-height: 1.6; margin: 6px 0 0; color: #6b7280;">'
                f"{html.escape(str(value))}</p>"
            )
    parts.append("</li>")
    return "".join(parts)


def correction_email_html(*, name: str, correction: Correction, report_url: str) -> str:
    """Corpo do e-mail. Tudo que vem do banco passa por `html.escape`."""
    omitted = correction.total - len(correction.entries)
    tail = (
        f'<p style="font-size: 13px; line-height: 1.6; color: #6b7280; margin: 0 0 24px;">'
        f"E mais {omitted} no boletim completo.</p>"
        if omitted > 0
        else ""
    )
    return f"""
<div style="font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px 24px; color: #1a1a2e;">
  <p style="font-size: 13px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; color: #2563eb; margin: 0 0 20px;">BeFluent</p>
  <h1 style="font-size: 20px; font-weight: 600; margin: 0 0 16px;">Correção da sessão</h1>
  <p style="font-size: 15px; line-height: 1.6; margin: 0 0 8px;">Olá, {html.escape(name)}.</p>
  <p style="font-size: 15px; line-height: 1.6; margin: 0 0 20px;">
    {html.escape(correction.lesson_title)} — {correction.total}
    {"resposta" if correction.total == 1 else "respostas"} com correção registrada,
    {correction.incorrect} para revisar.
  </p>
  <ol style="margin: 0 0 24px; padding-left: 20px;">{"".join(_entry_html(entry) for entry in correction.entries)}</ol>
  {tail}
  <p style="margin: 0 0 24px;">
    <a href="{report_url}" style="display: inline-block; background: #2563eb; color: #ffffff; text-decoration: none; font-size: 15px; font-weight: 600; padding: 12px 24px; border-radius: 8px;">
      Abrir o boletim completo
    </a>
  </p>
  <p style="font-size: 13px; line-height: 1.6; color: #6b7280; margin: 0;">
    Esta é a correção como foi apresentada no momento da resposta.
  </p>
</div>
""".strip()


def dispatch_correction_emails(
    db: Session,
    *,
    within_hours: int = DEFAULT_WINDOW_HOURS,
    now: datetime | None = None,
) -> dict:
    """Manda a correção das sessões encerradas na janela. Uma por sessão.

    Mesma ordem do e-mail diário: reivindicar → enviar → confirmar, desfazendo a
    reivindicação em falha de provedor. Ver `daily_email.dispatch_daily_emails`.
    """
    reference = now or datetime.now(timezone.utc)
    cutoff = reference - timedelta(hours=within_hours)
    base_url = get_settings().frontend_origin.rstrip("/")
    result = {"sent": 0, "skipped": 0, "failed": 0, "window_hours": within_hours}

    rows = db.execute(
        select(TeachingFlowSession, User)
        .join(UserLanguage, UserLanguage.id == TeachingFlowSession.user_language_id)
        .join(User, User.id == UserLanguage.user_id)
        .where(
            TeachingFlowSession.status == "closed",
            TeachingFlowSession.lesson_id.is_not(None),
            TeachingFlowSession.closed_at.is_not(None),
            TeachingFlowSession.closed_at >= cutoff,
        )
        .order_by(TeachingFlowSession.closed_at)
    ).all()

    for session, user in rows:
        if not user.email:
            result["skipped"] += 1
            continue
        correction = build_correction(db, session)
        if correction is None:
            result["skipped"] += 1
            continue

        savepoint = db.begin_nested()
        claimed = record_product_event(
            db,
            user_language_id=session.user_language_id,
            event_type=CORRECTION_EMAIL_SENT,
            dedupe_key=f"correction:{session.id}",
            payload={
                "lesson_id": correction.lesson_id,
                "entries": correction.total,
                "incorrect": correction.incorrect,
            },
        )
        if not claimed:
            savepoint.rollback()
            result["skipped"] += 1
            continue

        try:
            send_email(
                to=user.email,
                subject=correction_email_subject(correction),
                html=correction_email_html(
                    name=user.name,
                    correction=correction,
                    report_url=f"{base_url}/boletim/{correction.lesson_id}",
                ),
            )
        except EmailSendError:
            savepoint.rollback()
            result["failed"] += 1
            logger.warning("E-mail de correção falhou para a sessão %s.", session.id)
            continue

        savepoint.commit()
        result["sent"] += 1

    return result
