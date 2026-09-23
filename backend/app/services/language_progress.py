"""Progresso de idioma: habilidades, marcos e transições.

Três medidas separadas:

- sessão: `session_progress` (posição nas atividades);
- habilidade: média do domínio demonstrado por `skill_focus` real;
- idioma: CEFR gravado no perfil e marco derivado dentro dessa faixa.

CEFR não sobe aqui. A média de objetivos não distingue desempenho no
próximo nível, e repetir atividade fácil não é evidência de faixa nova.
`CEFR_AUTO_PROMOTION_ENABLED` permanece falso até existir evidência
sustentada nas competências do nível seguinte.

O marco é derivado, não gravado como fonte de verdade. O que se persiste
é a transição (evento) e o último estado observado, para o dashboard não
celebrar de novo um nível que o aluno já tinha.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.curriculum import block_skill_label
from app.core.levels import LEVEL_INDEX, LEVEL_ORDER, SKILL_LABELS, normalize_level
from app.models import (
    LearningEvidence,
    LearningError,
    LearningObjective,
    LearningProgressEvent,
    LearningProgressSnapshot,
    UserLanguage,
    UserObjectiveProgress,
)
from app.services.progress import mastery_percent_for_state

CEFR_AUTO_PROMOTION_ENABLED = False
PROMOTION_BLOCK_REASON = "insufficient_cross_skill_evidence"

ACTIVITY_COMPLETED = "activity_completed"
LESSON_STARTED = "lesson_started"
LESSON_COMPLETED = "lesson_completed"
MILESTONE_ADVANCED = "milestone_advanced"
CEFR_LEVEL_ADVANCED = "cefr_level_advanced"
VOCABULARY_REVIEWED = "vocabulary_reviewed"
CONVERSATION_STARTED = "conversation_started"
CONVERSATION_COMPLETED = "conversation_completed"
LEARNING_CONTEXT_USED = "learning_context_used"

#: Limites entre os percentuais reais de `mastery_percent_for_state`
#: (25 learning, 35 revisão/remediação, 45 retry, 50 practicing, 100 mastered).
#: Fatias iguais de 20 pontos deixariam o marco 1 inalcançável.
_MILESTONE_UPPER_BOUNDS = (30, 43, 56, 85)

_NEXT_MILESTONE_HINT = {
    1: "O próximo marco aparece quando os objetivos deste nível passarem do contato inicial.",
    2: "O próximo marco aparece quando a revisão em aberto deste nível der lugar à prática.",
    3: "O próximo marco aparece quando mais objetivos deste nível passarem da prática controlada.",
    4: "O próximo marco aparece quando a maior parte dos objetivos deste nível estiver dominada.",
}


@dataclass(frozen=True)
class ProgressView:
    cefr_level: str | None
    milestone_code: str | None
    milestone_index: int | None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def skill_display_label(skill: str) -> str:
    if skill in SKILL_LABELS:
        return SKILL_LABELS[skill]
    return block_skill_label(skill)


def adjacent_cefr(level: str | None) -> str | None:
    """Próxima faixa da escala oficial. Nunca pula um nível."""
    normalized = normalize_level(level)
    if normalized is None:
        return None
    index = LEVEL_INDEX[normalized]
    if index >= len(LEVEL_ORDER) - 1:
        return None
    return LEVEL_ORDER[index + 1]


def milestone_index_for_mean(mean: float) -> int:
    for index, bound in enumerate(_MILESTONE_UPPER_BOUNDS, start=1):
        if mean < bound:
            return index
    return 5


def milestone_code(level: str, index: int) -> str:
    return f"{level}-{index}"


def detect_progress_transition(
    previous: ProgressView | None, current: ProgressView
) -> list[dict]:
    """Só transições novas. Estado já observado não gera celebração."""
    if previous is None:
        return []
    events: list[dict] = []
    if (
        previous.cefr_level
        and current.cefr_level
        and previous.cefr_level != current.cefr_level
    ):
        previous_index = LEVEL_INDEX.get(previous.cefr_level)
        current_index = LEVEL_INDEX.get(current.cefr_level)
        if (
            previous_index is not None
            and current_index is not None
            and current_index == previous_index + 1
        ):
            events.append(
                {
                    "event_type": CEFR_LEVEL_ADVANCED,
                    "dedupe_key": f"cefr:{current.cefr_level}",
                    "payload": {
                        "from_level": previous.cefr_level,
                        "to_level": current.cefr_level,
                        "title": f"Você alcançou o nível {current.cefr_level}.",
                    },
                }
            )
    if (
        previous.cefr_level
        and previous.cefr_level == current.cefr_level
        and previous.milestone_index is not None
        and current.milestone_index is not None
        and current.milestone_code is not None
        and current.milestone_index > previous.milestone_index
    ):
        events.append(
            {
                "event_type": MILESTONE_ADVANCED,
                "dedupe_key": f"milestone:{current.milestone_code}",
                "payload": {
                    "from_code": previous.milestone_code,
                    "to_code": current.milestone_code,
                    "level": current.cefr_level,
                    "title": f"Você avançou para {current.milestone_code}.",
                },
            }
        )
    return events


def _demonstrated_rows(db: Session, user_language_id: str):
    rows = list(
        db.execute(
            select(UserObjectiveProgress, LearningObjective)
            .join(LearningObjective, LearningObjective.id == UserObjectiveProgress.objective_id)
            .where(
                UserObjectiveProgress.user_language_id == user_language_id,
                LearningObjective.is_active.is_(True),
            )
        )
    )
    evidenced = set(
        db.scalars(
            select(LearningEvidence.objective_id).where(
                LearningEvidence.user_language_id == user_language_id,
                LearningEvidence.objective_id.is_not(None),
            )
        )
    )
    open_errors = set(
        db.scalars(
            select(LearningError.objective_id).where(
                LearningError.user_language_id == user_language_id,
                LearningError.resolved.is_(False),
                LearningError.objective_id.is_not(None),
            )
        )
    )
    demonstrated = []
    for progress, objective in rows:
        if objective.id not in evidenced:
            continue
        percent = mastery_percent_for_state(
            progress.state, has_open_error=objective.id in open_errors
        )
        demonstrated.append((objective, percent))
    return demonstrated


def evaluate_skill_progress(db: Session, user_language_id: str) -> list[dict]:
    """Percentuais só de habilidades com evidência. Sem skill, o item some."""
    grouped: dict[str, list[int]] = {}
    for objective, percent in _demonstrated_rows(db, user_language_id):
        grouped.setdefault(objective.skill_focus, []).append(percent)
    return [
        {
            "skill": skill,
            "label": skill_display_label(skill),
            "percent": round(sum(values) / len(values)),
            "sample_size": len(values),
        }
        for skill, values in sorted(grouped.items())
    ]


def _milestone_for_level(rows: list[tuple], level: str | None) -> dict | None:
    if level is None:
        return None
    percents = [
        percent
        for objective, percent in rows
        if normalize_level(objective.level) == level
    ]
    if not percents:
        return None
    mean = sum(percents) / len(percents)
    index = milestone_index_for_mean(mean)
    code = milestone_code(level, index)
    next_index = index + 1 if index < 5 else None
    return {
        "code": code,
        "index": index,
        "level": level,
        "sample_size": len(percents),
        "basis": "objectives_at_current_level_with_evidence",
        "next_code": milestone_code(level, next_index) if next_index else None,
        "next_hint": _NEXT_MILESTONE_HINT.get(index),
    }


def evaluate_language_progress(db: Session, user_language) -> dict:
    """Estado atual. Não grava CEFR e não promove faixa."""
    level = normalize_level(user_language.current_level if user_language else None)
    rows = _demonstrated_rows(db, user_language.id) if user_language else []
    skills = evaluate_skill_progress(db, user_language.id) if user_language else []
    milestone = _milestone_for_level(rows, level)
    developed = sorted(skills, key=lambda item: item["percent"], reverse=True)[:3]
    return {
        "auto_promotion_enabled": CEFR_AUTO_PROMOTION_ENABLED,
        "promotion_block_reason": None
        if CEFR_AUTO_PROMOTION_ENABLED
        else PROMOTION_BLOCK_REASON,
        "cefr": {
            "current": level,
            "next": adjacent_cefr(level),
            "source": user_language.level_source if user_language else None,
            "progress_to_next_percent": None,
        },
        "milestone": milestone,
        "skills": skills,
        "strongest_skills": developed,
        "next_milestone": (
            {
                "code": milestone["next_code"],
                "hint": milestone["next_hint"],
            }
            if milestone and milestone["next_code"]
            else None
        ),
    }


def record_product_event(
    db: Session,
    *,
    user_language_id: str,
    event_type: str,
    dedupe_key: str,
    payload: dict | None = None,
) -> bool:
    """Grava a transição uma vez. Reabrir a tela não cria outro evento."""
    existing = db.scalar(
        select(LearningProgressEvent.id).where(
            LearningProgressEvent.user_language_id == user_language_id,
            LearningProgressEvent.event_type == event_type,
            LearningProgressEvent.dedupe_key == dedupe_key,
        )
    )
    if existing:
        return False
    try:
        with db.begin_nested():
            db.add(
                LearningProgressEvent(
                    user_language_id=user_language_id,
                    event_type=event_type,
                    dedupe_key=dedupe_key,
                    payload_json=dict(payload or {}),
                )
            )
            db.flush()
        return True
    except IntegrityError:
        return False


def _latest_achievement(db: Session, user_language_id: str) -> dict | None:
    event = db.scalar(
        select(LearningProgressEvent)
        .where(
            LearningProgressEvent.user_language_id == user_language_id,
            LearningProgressEvent.event_type.in_(
                (MILESTONE_ADVANCED, CEFR_LEVEL_ADVANCED)
            ),
        )
        .order_by(LearningProgressEvent.created_at.desc(), LearningProgressEvent.id.desc())
    )
    if event is None:
        return None
    payload = dict(event.payload_json or {})
    return {
        "event_type": event.event_type,
        "title": payload.get("title"),
        "payload": payload,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def observe_language_progress(db: Session, user_language_id: str) -> dict:
    """Compara com o último estado visto. A primeira leitura só estabelece a base."""
    profile = db.get(UserLanguage, user_language_id)
    if profile is None:
        return {
            "auto_promotion_enabled": CEFR_AUTO_PROMOTION_ENABLED,
            "promotion_block_reason": PROMOTION_BLOCK_REASON,
            "cefr": {
                "current": None,
                "next": None,
                "source": None,
                "progress_to_next_percent": None,
            },
            "milestone": None,
            "skills": [],
            "strongest_skills": [],
            "next_milestone": None,
            "celebrations": [],
            "latest_achievement": None,
        }

    state = evaluate_language_progress(db, profile)
    milestone = state["milestone"]
    current = ProgressView(
        cefr_level=state["cefr"]["current"],
        milestone_code=milestone["code"] if milestone else None,
        milestone_index=milestone["index"] if milestone else None,
    )
    snapshot = db.scalar(
        select(LearningProgressSnapshot).where(
            LearningProgressSnapshot.user_language_id == user_language_id
        )
    )
    celebrations: list[dict] = []
    if snapshot is None:
        db.add(
            LearningProgressSnapshot(
                user_language_id=user_language_id,
                cefr_level=current.cefr_level,
                milestone_code=current.milestone_code,
                milestone_index=current.milestone_index,
                observed_at=_now(),
            )
        )
        db.flush()
    else:
        previous = ProgressView(
            cefr_level=snapshot.cefr_level,
            milestone_code=snapshot.milestone_code,
            milestone_index=snapshot.milestone_index,
        )
        for event in detect_progress_transition(previous, current):
            created = record_product_event(
                db,
                user_language_id=user_language_id,
                event_type=event["event_type"],
                dedupe_key=event["dedupe_key"],
                payload=event["payload"],
            )
            if created:
                celebrations.append(
                    {"event_type": event["event_type"], "payload": event["payload"]}
                )
        snapshot.cefr_level = current.cefr_level
        snapshot.milestone_code = current.milestone_code
        snapshot.milestone_index = current.milestone_index
        snapshot.observed_at = _now()
        db.flush()

    return {
        **state,
        "celebrations": celebrations,
        "latest_achievement": _latest_achievement(db, user_language_id),
    }
