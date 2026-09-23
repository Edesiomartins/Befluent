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
from app.services.session_budget import MILESTONE_UPPER_BOUNDS

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
SESSION_STARTED = "session_started"
SESSION_RESUMED = "session_resumed"
SESSION_COMPLETED = "session_completed"

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
    """Marco do progresso efetivo. 80–100 continua no estágio 5 e não promove CEFR."""
    for index, bound in enumerate(MILESTONE_UPPER_BOUNDS, start=1):
        if mean < bound:
            return index
    return 5


def official_curriculum_total(language_code: str, level: str, skill: str) -> int | None:
    """Denominador de cobertura. Ausente de propósito.

    Não existe catálogo fechado de objetivos para idioma + CEFR + skill.
    `LearningObjective` hoje guarda um can-do A1, a semana piloto B2 e
    âncoras de tema. Contar essas linhas inventaria o total.
    """
    del language_code, level, skill
    return None


def skill_metrics(*, mastery_percents: list[int], total_objectives: int | None) -> dict:
    """Separa domínio do que já foi visto e progresso efetivo do currículo.

    Objetivo sem evidência entra como 0 no progresso efetivo. Sem total
    oficial, cobertura e progresso efetivo ficam ausentes — não viram 100%.
    """
    evidenced = len(mastery_percents)
    mastered = sum(1 for value in mastery_percents if value >= 100)
    mastery_seen = round(sum(mastery_percents) / evidenced) if evidenced else None
    if not total_objectives:
        return {
            "total_objectives": total_objectives,
            "evidenced_objectives": evidenced,
            "mastered_objectives": mastered,
            "coverage_percent": None,
            "mastery_seen_percent": mastery_seen if total_objectives != 0 else mastery_seen,
            "effective_progress_percent": None,
        }
    return {
        "total_objectives": total_objectives,
        "evidenced_objectives": evidenced,
        "mastered_objectives": mastered,
        "coverage_percent": round(100 * evidenced / total_objectives),
        "mastery_seen_percent": mastery_seen if evidenced else 0,
        "effective_progress_percent": round(sum(mastery_percents) / total_objectives),
    }


def effective_level_progress(skills: list[dict]) -> float | None:
    """Média das skills que têm catálogo. Uma skill com muitos objetivos não pesa mais."""
    known = [
        item["effective_progress_percent"]
        for item in skills
        if item.get("total_objectives") and item.get("effective_progress_percent") is not None
    ]
    if not known:
        return None
    return sum(known) / len(known)


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
    """Habilidades do CEFR atual. A barra principal é o progresso efetivo, se houver total."""
    profile = db.get(UserLanguage, user_language_id)
    level = normalize_level(profile.current_level if profile else None)
    language_code = ""
    if profile is not None:
        from app.models import Language

        language = db.get(Language, profile.language_id)
        language_code = language.code if language else ""
    grouped: dict[str, list[int]] = {}
    if level is not None:
        for objective, percent in _demonstrated_rows(db, user_language_id):
            if normalize_level(objective.level) != level:
                continue
            grouped.setdefault(objective.skill_focus, []).append(percent)
    skills = []
    for skill, values in sorted(grouped.items()):
        metrics = skill_metrics(
            mastery_percents=values,
            total_objectives=official_curriculum_total(language_code, level or "", skill),
        )
        skills.append(
            {
                "skill": skill,
                "label": skill_display_label(skill),
                "percent": metrics["effective_progress_percent"],
                "sample_size": len(values),
                **metrics,
            }
        )
    return skills


def _milestone_for_level(level: str | None, skills: list[dict]) -> dict | None:
    progress = effective_level_progress(skills)
    if level is None or progress is None:
        return None
    index = milestone_index_for_mean(progress)
    code = milestone_code(level, index)
    next_index = index + 1 if index < 5 else None
    return {
        "code": code,
        "index": index,
        "level": level,
        "sample_size": len(skills),
        "basis": "effective_level_progress",
        "effective_percent": round(progress),
        "next_code": milestone_code(level, next_index) if next_index else None,
        "next_hint": _NEXT_MILESTONE_HINT.get(index),
    }


def evaluate_language_progress(db: Session, user_language) -> dict:
    """Estado atual. Não grava CEFR e não promove faixa."""
    level = normalize_level(user_language.current_level if user_language else None)
    skills = evaluate_skill_progress(db, user_language.id) if user_language else []
    milestone = _milestone_for_level(level, skills)
    developed = sorted(
        skills,
        key=lambda item: (
            item.get("effective_progress_percent")
            if item.get("effective_progress_percent") is not None
            else item.get("mastery_seen_percent") or 0
        ),
        reverse=True,
    )[:3]
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
