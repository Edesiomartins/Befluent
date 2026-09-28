"""E-mail diário da missão do dia.

Por que existe: nada trazia o aluno de volta ao BeFluent. O app esperava que a
pessoa lembrasse. Este módulo monta e envia um e-mail por dia com a jornada
corrente do cronograma e um link direto para ela.

O que o e-mail **não** traz, por decisão: contagem de revisão vencida,
percentual de progresso, nível e sequência de dias. O objetivo é ser um
convite, não um boletim de cobrança.

Quem dispara é uma tarefa agendada no Coolify chamando
`POST /api/v1/daily-email/dispatch`. Não há agendador dentro do processo:
dois workers agendando o mesmo horário mandariam dois e-mails.
"""

from __future__ import annotations

import html
import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.curriculum import CurriculumStatus, DayStatus, block_skill_label
from app.models import (
    Curriculum,
    CurriculumBlock,
    CurriculumDay,
    CurriculumWeek,
    User,
    UserLanguage,
)
from app.services.email import EmailSendError, send_email
from app.services.language_progress import record_product_event

logger = logging.getLogger(__name__)

#: Tipo de evento que marca "o e-mail de hoje já saiu para este perfil".
DAILY_EMAIL_SENT = "daily_email_sent"

#: Dias já encerrados não são missão. Mesma definição de `/curriculum/day/today`:
#: a jornada corrente é a primeira ainda aberta na progressão, não a data civil.
_CLOSED_DAY_STATUSES = (DayStatus.COMPLETED, DayStatus.SKIPPED)


@dataclass(frozen=True)
class DailyMission:
    """A jornada corrente, no mínimo necessário para montar o e-mail."""

    day_id: str
    day_number: int
    theme: str
    block_labels: tuple[str, ...]


def build_daily_mission(db: Session, *, user_language_id: str) -> DailyMission | None:
    """Jornada corrente do perfil, ou `None` quando não há o que enviar.

    `None` cobre os três casos em que um e-mail seria ruído: perfil sem
    cronograma ativo, cronograma inteiro concluído e dia sem blocos.
    """
    curriculum = db.scalar(
        select(Curriculum)
        .where(
            Curriculum.user_language_id == user_language_id,
            Curriculum.status == CurriculumStatus.ACTIVE,
        )
        .order_by(Curriculum.created_at.desc())
    )
    if curriculum is None:
        return None

    day = db.scalar(
        select(CurriculumDay)
        .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
        .where(
            CurriculumWeek.curriculum_id == curriculum.id,
            CurriculumDay.status.notin_(_CLOSED_DAY_STATUSES),
        )
        .order_by(CurriculumDay.day_number)
    )
    if day is None:
        return None

    week = db.get(CurriculumWeek, day.week_id)
    blocks = list(
        db.scalars(
            select(CurriculumBlock)
            .where(CurriculumBlock.day_id == day.id)
            .order_by(CurriculumBlock.position)
        )
    )
    if not blocks:
        return None

    return DailyMission(
        day_id=day.id,
        day_number=day.day_number,
        theme=week.theme if week else "",
        block_labels=tuple(block_skill_label(block.skill) for block in blocks),
    )


def daily_email_subject(mission: DailyMission) -> str:
    theme = mission.theme.strip()
    middle = f" — {theme}" if theme else ""
    return f"Dia {mission.day_number}{middle} | BeFluent"


def daily_email_html(*, name: str, mission: DailyMission, day_url: str) -> str:
    """Corpo do e-mail.

    Tudo que vem do banco passa por `html.escape`: tema e rótulo de bloco são
    dados, não marcação.
    """
    theme = html.escape(mission.theme.strip())
    blocks = "".join(
        f'<li style="margin: 0 0 6px;">{html.escape(label)}</li>'
        for label in mission.block_labels
    )
    return f"""
<div style="font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px 24px; color: #1a1a2e;">
  <p style="font-size: 13px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; color: #2563eb; margin: 0 0 20px;">BeFluent</p>
  <h1 style="font-size: 20px; font-weight: 600; margin: 0 0 16px;">Dia {mission.day_number}{f" — {theme}" if theme else ""}</h1>
  <p style="font-size: 15px; line-height: 1.6; margin: 0 0 16px;">Olá, {html.escape(name)}.</p>
  <p style="font-size: 15px; line-height: 1.6; margin: 0 0 12px;">A jornada de hoje tem estes blocos:</p>
  <ul style="font-size: 15px; line-height: 1.6; margin: 0 0 24px; padding-left: 20px;">{blocks}</ul>
  <p style="margin: 0 0 24px;">
    <a href="{day_url}" style="display: inline-block; background: #2563eb; color: #ffffff; text-decoration: none; font-size: 15px; font-weight: 600; padding: 12px 24px; border-radius: 8px;">
      Abrir a jornada de hoje
    </a>
  </p>
  <p style="font-size: 13px; line-height: 1.6; color: #6b7280; margin: 0;">
    Se o botão não funcionar, copie e cole este link no navegador:<br />
    <a href="{day_url}" style="color: #2563eb; word-break: break-all;">{day_url}</a>
  </p>
</div>
""".strip()


def dispatch_daily_emails(db: Session, *, today: date | None = None) -> dict:
    """Envia o e-mail do dia para cada perfil ativo. Um por perfil, por dia.

    A ordem é reivindicar → enviar → confirmar. Reivindicar depois do envio
    abriria janela para dois e-mails iguais; reivindicar antes, desfazendo em
    caso de falha, erra para o lado de mandar uma vez ou nenhuma.
    """
    reference = today or datetime.now(timezone.utc).date()
    dedupe_key = f"daily-email:{reference.isoformat()}"
    settings = get_settings()
    base_url = settings.frontend_origin.rstrip("/")
    result = {"sent": 0, "skipped": 0, "failed": 0, "date": reference.isoformat()}

    rows = db.execute(
        select(UserLanguage, User)
        .join(User, User.id == UserLanguage.user_id)
        .where(
            UserLanguage.is_active.is_(True),
            UserLanguage.onboarding_completed.is_(True),
        )
        .order_by(UserLanguage.id)
    ).all()

    for profile, user in rows:
        if not user.email:
            result["skipped"] += 1
            continue
        mission = build_daily_mission(db, user_language_id=profile.id)
        if mission is None:
            result["skipped"] += 1
            continue

        savepoint = db.begin_nested()
        claimed = record_product_event(
            db,
            user_language_id=profile.id,
            event_type=DAILY_EMAIL_SENT,
            dedupe_key=dedupe_key,
            payload={"day_id": mission.day_id, "day_number": mission.day_number},
        )
        if not claimed:
            savepoint.rollback()
            result["skipped"] += 1
            continue

        try:
            send_email(
                to=user.email,
                subject=daily_email_subject(mission),
                html=daily_email_html(
                    name=user.name,
                    mission=mission,
                    day_url=f"{base_url}/cronograma/dia/{mission.day_id}",
                ),
            )
        except EmailSendError:
            # Desfaz a reivindicação: falha de provedor não consome o dia.
            savepoint.rollback()
            result["failed"] += 1
            logger.warning("E-mail diário falhou para o perfil %s.", profile.id)
            continue

        savepoint.commit()
        result["sent"] += 1

    return result
