"""Cronograma estruturado de estudo.

Substitui `learning_plans` como motor de planejamento (aquele continua
funcionando, marcado como deprecated). Regras de propriedade: todo acesso
resolve currículo → perfil linguístico → usuário; um id de outro usuário
responde 404, nunca 403 — 403 confirmaria que o recurso existe.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.helpers import user_language
from app.core.curriculum import (
    BLOCK_LESSON_MODE,
    BlockStatus,
    CurriculumStatus,
    DayStatus,
    block_skill_label,
)
from app.core.database import get_db
from app.core.deps import current_user
from app.core.errors import APIError
from app.core.levels import level_payload
from app.models import (
    Curriculum,
    CurriculumBlock,
    CurriculumDay,
    CurriculumWeek,
    User,
    UserLanguage,
)
from app.services.curriculum_generator import generate_curriculum
from app.services.progression import (
    OVERDUE_THRESHOLD,
    RESCHEDULE_STRATEGIES,
    build_block_lesson,
    complete_block,
    overdue_days,
    reschedule,
    start_checkpoint,
)

router = APIRouter(prefix="/curriculum", tags=["curriculum"])


class CurriculumCreate(BaseModel):
    language_code: str
    duration_days: int


class BlockCompleteIn(BaseModel):
    score: float | None = Field(default=None, ge=0, le=1)


class RescheduleIn(BaseModel):
    strategy: str


def _today() -> date:
    return date.today()


def _owned_curriculum(db: Session, curriculum_id: str, user: User) -> Curriculum:
    curriculum = db.scalar(
        select(Curriculum)
        .join(UserLanguage, UserLanguage.id == Curriculum.user_language_id)
        .where(Curriculum.id == curriculum_id, UserLanguage.user_id == user.id)
    )
    if not curriculum:
        raise APIError(404, "curriculum_not_found", "Cronograma não encontrado.")
    return curriculum


def _owned_block(db: Session, block_id: str, user: User) -> tuple[CurriculumBlock, CurriculumDay, Curriculum]:
    row = db.execute(
        select(CurriculumBlock, CurriculumDay, Curriculum)
        .join(CurriculumDay, CurriculumDay.id == CurriculumBlock.day_id)
        .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
        .join(Curriculum, Curriculum.id == CurriculumWeek.curriculum_id)
        .join(UserLanguage, UserLanguage.id == Curriculum.user_language_id)
        .where(CurriculumBlock.id == block_id, UserLanguage.user_id == user.id)
    ).first()
    if not row:
        raise APIError(404, "curriculum_block_not_found", "Bloco de estudo não encontrado.")
    return row[0], row[1], row[2]


def _active_curriculum(db: Session, user: User, language_code: str) -> Curriculum:
    ul = user_language(db, user.id, language_code)
    curriculum = db.scalar(
        select(Curriculum)
        .where(
            Curriculum.user_language_id == ul.id,
            Curriculum.status == CurriculumStatus.ACTIVE,
        )
        .order_by(Curriculum.created_at.desc())
    )
    if not curriculum:
        raise APIError(
            404,
            "curriculum_not_found",
            "Nenhum cronograma ativo para este idioma.",
        )
    return curriculum


# ------------------------------------------------------------------ payloads


def _block_payload(block: CurriculumBlock) -> dict:
    return {
        "id": block.id,
        "skill": block.skill,
        "skill_label": block_skill_label(block.skill),
        "mode": BLOCK_LESSON_MODE.get(block.skill),
        "position": block.position,
        "estimated_minutes": block.estimated_minutes,
        "cefr_level": block.cefr_level,
        "topic": block.topic,
        "lesson_ref": block.lesson_ref,
        "status": block.status,
        "score": block.score,
    }


def _blocks_of(db: Session, day_ids: list[str]) -> dict[str, list[CurriculumBlock]]:
    if not day_ids:
        return {}
    grouped: dict[str, list[CurriculumBlock]] = {}
    for block in db.scalars(
        select(CurriculumBlock)
        .where(CurriculumBlock.day_id.in_(day_ids))
        .order_by(CurriculumBlock.position)
    ):
        grouped.setdefault(block.day_id, []).append(block)
    return grouped


def _day_payload(day: CurriculumDay, blocks: list[CurriculumBlock]) -> dict:
    done = [block for block in blocks if block.status == BlockStatus.COMPLETED]
    return {
        "id": day.id,
        "day_number": day.day_number,
        "scheduled_date": day.scheduled_date.isoformat(),
        "status": day.status,
        "completed_at": day.completed_at.isoformat() if day.completed_at else None,
        "total_minutes": sum(block.estimated_minutes for block in blocks),
        "blocks_total": len(blocks),
        "blocks_completed": len(done),
        "blocks": [_block_payload(block) for block in blocks],
    }


def _week_payload(week: CurriculumWeek, days: list[dict] | None = None) -> dict:
    payload = {
        "id": week.id,
        "week_number": week.week_number,
        "theme": week.theme,
        "cefr_focus": week.cefr_focus,
        "is_checkpoint": week.is_checkpoint,
    }
    if days is not None:
        payload["days"] = days
    return payload


def _progress_summary(db: Session, curriculum: Curriculum) -> dict:
    days = list(
        db.scalars(
            select(CurriculumDay)
            .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
            .where(CurriculumWeek.curriculum_id == curriculum.id)
            .order_by(CurriculumDay.day_number)
        )
    )
    total = len(days)
    completed = sum(1 for day in days if day.status == DayStatus.COMPLETED)
    today = _today()
    late = [day for day in days if day.scheduled_date < today and day.status not in {DayStatus.COMPLETED, DayStatus.SKIPPED}]
    current = next(
        (day for day in days if day.status != DayStatus.COMPLETED),
        days[-1] if days else None,
    )

    next_checkpoint = db.scalar(
        select(CurriculumWeek)
        .where(
            CurriculumWeek.curriculum_id == curriculum.id,
            CurriculumWeek.is_checkpoint.is_(True),
        )
        .order_by(CurriculumWeek.week_number)
        .offset(0)
        .limit(1)
    )
    if current is not None:
        current_week = db.get(CurriculumWeek, current.week_id)
        if current_week is not None:
            next_checkpoint = db.scalar(
                select(CurriculumWeek)
                .where(
                    CurriculumWeek.curriculum_id == curriculum.id,
                    CurriculumWeek.is_checkpoint.is_(True),
                    CurriculumWeek.week_number >= current_week.week_number,
                )
                .order_by(CurriculumWeek.week_number)
                .limit(1)
            )

    return {
        "days_total": total,
        "days_completed": completed,
        "percent_complete": round(completed / total * 100, 1) if total else 0.0,
        "current_day_number": current.day_number if current else None,
        "overdue_days": len(late),
        "needs_reschedule": len(late) >= OVERDUE_THRESHOLD,
        "next_checkpoint_week": next_checkpoint.week_number if next_checkpoint else None,
    }


def _curriculum_payload(db: Session, curriculum: Curriculum, *, with_progress: bool = True) -> dict:
    payload = {
        "id": curriculum.id,
        "duration_days": curriculum.duration_days,
        "start_date": curriculum.start_date.isoformat(),
        "entry_level": curriculum.entry_level,
        "target_level": curriculum.target_level,
        "entry": level_payload(curriculum.entry_level),
        "target": level_payload(curriculum.target_level),
        "status": curriculum.status,
        "generated_from": curriculum.generated_from,
        "weeks_total": db.scalar(
            select(func.count(CurriculumWeek.id)).where(
                CurriculumWeek.curriculum_id == curriculum.id
            )
        )
        or 0,
        "disclaimer": (
            "Cronograma estimado a partir do teste de nivelamento. "
            "Não é garantia de atingir o nível-meta no prazo."
        ),
    }
    if with_progress:
        payload["progress"] = _progress_summary(db, curriculum)
    return payload


# ----------------------------------------------------------------- endpoints


@router.post("")
def create(
    data: CurriculumCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Gera e ativa o cronograma. Regenerar arquiva o anterior."""
    ul = user_language(db, user.id, data.language_code)
    curriculum = generate_curriculum(db, ul.id, data.duration_days)
    db.commit()
    return _curriculum_payload(db, curriculum)


@router.get("/active")
def active(
    language_code: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    curriculum = _active_curriculum(db, user, language_code)
    payload = _curriculum_payload(db, curriculum)
    payload["weeks"] = [
        _week_payload(week)
        for week in db.scalars(
            select(CurriculumWeek)
            .where(CurriculumWeek.curriculum_id == curriculum.id)
            .order_by(CurriculumWeek.week_number)
        )
    ]
    return payload


@router.get("/day/today")
def today(
    language_code: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Dia corrente com seus blocos, mais os dias vencidos ainda em aberto.

    "Dia corrente" é o primeiro dia não concluído, não a data de hoje: quem
    parou uma semana retoma de onde ficou em vez de perder o conteúdo.
    """
    curriculum = _active_curriculum(db, user, language_code)
    days = list(
        db.scalars(
            select(CurriculumDay)
            .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
            .where(CurriculumWeek.curriculum_id == curriculum.id)
            .order_by(CurriculumDay.day_number)
        )
    )
    current = next((day for day in days if day.status != DayStatus.COMPLETED), None)
    late = overdue_days(days, reference=_today())

    blocks = _blocks_of(db, [current.id]) if current else {}
    week = db.get(CurriculumWeek, current.week_id) if current else None

    return {
        "curriculum": _curriculum_payload(db, curriculum),
        "week": _week_payload(week) if week else None,
        "day": _day_payload(current, blocks.get(current.id, [])) if current else None,
        "overdue_days": [
            {
                "id": day.id,
                "day_number": day.day_number,
                "scheduled_date": day.scheduled_date.isoformat(),
            }
            for day in late
        ],
    }


@router.get("/{curriculum_id}/week/{week_number}")
def week_detail(
    curriculum_id: str,
    week_number: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    curriculum = _owned_curriculum(db, curriculum_id, user)
    week = db.scalar(
        select(CurriculumWeek).where(
            CurriculumWeek.curriculum_id == curriculum.id,
            CurriculumWeek.week_number == week_number,
        )
    )
    if not week:
        raise APIError(404, "curriculum_week_not_found", "Semana não encontrada.")

    days = list(
        db.scalars(
            select(CurriculumDay)
            .where(CurriculumDay.week_id == week.id)
            .order_by(CurriculumDay.day_number)
        )
    )
    blocks = _blocks_of(db, [day.id for day in days])
    return _week_payload(week, [_day_payload(day, blocks.get(day.id, [])) for day in days])


@router.get("/day/{day_id}")
def day_detail(
    day_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    row = db.execute(
        select(CurriculumDay, CurriculumWeek, Curriculum)
        .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
        .join(Curriculum, Curriculum.id == CurriculumWeek.curriculum_id)
        .join(UserLanguage, UserLanguage.id == Curriculum.user_language_id)
        .where(CurriculumDay.id == day_id, UserLanguage.user_id == user.id)
    ).first()
    if not row:
        raise APIError(404, "curriculum_day_not_found", "Dia de estudo não encontrado.")
    day, week, curriculum = row
    blocks = _blocks_of(db, [day.id])
    return {
        "curriculum": _curriculum_payload(db, curriculum, with_progress=False),
        "week": _week_payload(week),
        "day": _day_payload(day, blocks.get(day.id, [])),
    }


@router.post("/block/{block_id}/start")
def start_block(
    block_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Gera (ou recupera) a lição do bloco e vincula em `lesson_ref`."""
    block, day, _ = _owned_block(db, block_id, user)
    payload = build_block_lesson(db, user=user, block=block, day=day)

    if day.status == DayStatus.PENDING:
        day.status = DayStatus.IN_PROGRESS
    db.commit()

    return {"block": _block_payload(block), "lesson": payload}


@router.post("/block/{block_id}/complete")
def finish_block(
    block_id: str,
    data: BlockCompleteIn | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Marca o bloco; concluir o último bloco fecha o dia."""
    block, day, curriculum = _owned_block(db, block_id, user)
    result = complete_block(db, block=block, day=day, score=data.score if data else None)
    db.commit()
    return {
        "block": _block_payload(block),
        "day": {
            "id": day.id,
            "status": day.status,
            "completed_at": day.completed_at.isoformat() if day.completed_at else None,
        },
        "day_completed": result["day_completed"],
        "progress": _progress_summary(db, curriculum),
    }


@router.post("/{curriculum_id}/checkpoint/{week_number}/start")
def start_week_checkpoint(
    curriculum_id: str,
    week_number: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Abre a mini-avaliação da semana e devolve o id do teste.

    O teste é respondido pelas rotas já existentes de `/placement-tests`
    (`/next-item`, `/answers`, `/writing`, `/complete`) — o cronograma não
    duplica a entrega de itens nem a correção.
    """
    curriculum = _owned_curriculum(db, curriculum_id, user)
    week = db.scalar(
        select(CurriculumWeek).where(
            CurriculumWeek.curriculum_id == curriculum.id,
            CurriculumWeek.week_number == week_number,
        )
    )
    if not week:
        raise APIError(404, "curriculum_week_not_found", "Semana não encontrada.")

    test = start_checkpoint(db, user=user, curriculum=curriculum, week=week)
    db.commit()
    return {
        "placement_test_id": test.id,
        "week_number": week.week_number,
        "cefr_focus": week.cefr_focus,
        "status": test.status,
        "answer_flow": "/api/v1/placement-tests",
        "notice": (
            "Mini-avaliação curta do cronograma. O resultado ajusta seu plano, "
            "mas não substitui o teste de nivelamento completo."
        ),
    }


@router.post("/{curriculum_id}/reschedule")
def reschedule_curriculum(
    curriculum_id: str,
    data: RescheduleIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Recupera atraso: `compress` redistribui o essencial, `extend` adia tudo."""
    curriculum = _owned_curriculum(db, curriculum_id, user)
    if data.strategy not in RESCHEDULE_STRATEGIES:
        raise APIError(
            422,
            "invalid_strategy",
            "Estratégia deve ser 'compress' (comprimir) ou 'extend' (estender).",
        )
    result = reschedule(db, curriculum, strategy=data.strategy, reference=_today())
    curriculum.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "curriculum": _curriculum_payload(db, curriculum),
        "strategy": data.strategy,
        **result,
    }
