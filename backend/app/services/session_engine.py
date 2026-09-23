"""Session Engine V2.

Planeja uma sessão por orçamento de exercícios. Não reescreve o Teaching
Engine: o plano vira a lista de atividades que a flow já percorre.

Uma palavra não completa presentation, recognition, listening e production
na mesma sessão. Revisão vencida ocupa vaga dentro do orçamento; o que
não cabe fica para outra sessão.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.teaching import ActivityType, EvidenceType, MemorySubjectType
from app.models import LearningEvidence, MemorySchedule, VocabularyExample, VocabularyItem
from app.services.activity_generator import generate_vocabulary_activities
from app.services.lexical_policy import next_review_modality
from app.services.session_budget import (
    AREA_LABELS,
    AREA_ORDER,
    MAXIMUM_SESSION_EXERCISES,
    MAX_CONSECUTIVE_SAME_MODALITY,
    PHASE_RANK,
    SESSION_ACTIVITY_BUDGET,
    TARGET_SESSION_EXERCISES,
)

_LATER_MODALITIES = frozenset(
    {
        ActivityType.LISTENING_RECOGNITION,
        ActivityType.LEXICAL_PRODUCTION,
    }
)
_OPENING_MODALITIES = (
    ActivityType.PRESENTATION,
    ActivityType.RECOGNITION,
)

_AREA_BY_TYPE: dict[str, str] = {
    ActivityType.PRESENTATION: "vocabulary",
    ActivityType.RECOGNITION: "vocabulary",
    ActivityType.REVERSE_RECOGNITION: "vocabulary",
    ActivityType.REVIEW: "vocabulary",
    ActivityType.LISTENING_RECOGNITION: "listening",
    ActivityType.LISTEN: "listening",
    ActivityType.FILL_GAP: "grammar",
    ActivityType.WORD_ORDER: "grammar",
    ActivityType.MULTIPLE_CHOICE: "grammar",
    ActivityType.LEXICAL_PRODUCTION: "production",
    ActivityType.GUIDED_PRODUCTION: "production",
    ActivityType.FREE_PRODUCTION: "production",
    ActivityType.CONVERSATION_PROMPT: "conversation",
    ActivityType.TRANSFER_QUESTION: "conversation",
}


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def activity_area(activity_type: str) -> str | None:
    return _AREA_BY_TYPE.get(activity_type)


def plan_session(candidates: list[dict]) -> dict:
    """Seleciona e ordena exercícios. Não completa o alvo com atividade vazia."""
    selected: list[dict] = []
    counts = {area: 0 for area in AREA_ORDER}
    chosen: dict[str, set[str]] = {}
    ranked = [
        candidate
        for _, candidate in sorted(
            enumerate(candidates),
            key=lambda pair: (pair[1].get("priority", 1), pair[0]),
        )
    ]
    overflow = [candidate for candidate in ranked if candidate.get("overflow")]
    pool = [candidate for candidate in ranked if not candidate.get("overflow")]
    while sum(counts.values()) < TARGET_SESSION_EXERCISES:
        progressed = False
        for area in AREA_ORDER:
            if counts[area] >= SESSION_ACTIVITY_BUDGET[area]:
                continue
            choice = _next_in_area(area, pool, selected, chosen)
            if choice is None:
                continue
            pool.remove(choice)
            _take(choice, counts, chosen, selected)
            progressed = True
        if not progressed:
            break

    for candidate in overflow:
        if len(selected) >= MAXIMUM_SESSION_EXERCISES:
            break
        item_key = candidate.get("item_key")
        modality = str(candidate.get("modality") or "")
        if item_key and modality in chosen.get(str(item_key), set()):
            continue
        _take(candidate, counts, chosen, selected)

    ordered = _order_by_phase(selected)
    activities = []
    for index, candidate in enumerate(ordered):
        activity = dict(candidate["activity"])
        activity["session_area"] = candidate["area"]
        activity["index"] = index
        activities.append(activity)
    return {
        "activities": activities,
        "counts": {area: counts[area] for area in AREA_ORDER if counts[area]},
        "total": len(activities),
        "target_total": TARGET_SESSION_EXERCISES,
        "maximum_total": MAXIMUM_SESSION_EXERCISES,
    }


def _next_in_area(
    area: str,
    pool: list[dict],
    selected: list[dict],
    chosen: dict[str, set[str]],
) -> dict | None:
    options = [candidate for candidate in pool if candidate.get("area") == area and _item_ok(candidate, chosen)]
    if not options:
        return None
    recent = [
        str(item.get("modality"))
        for item in selected
        if item.get("area") == area
    ][-MAX_CONSECUTIVE_SAME_MODALITY:]
    if len(recent) == MAX_CONSECUTIVE_SAME_MODALITY and len(set(recent)) == 1:
        for candidate in options:
            if str(candidate.get("modality")) != recent[0]:
                return candidate
    return options[0]


def _item_ok(candidate: dict, chosen: dict[str, set[str]]) -> bool:
    item_key = candidate.get("item_key")
    modality = str(candidate.get("modality") or "")
    if not item_key:
        return True
    owned = chosen.get(str(item_key), set())
    if modality in owned or len(owned) >= 2:
        return False
    if modality in _LATER_MODALITIES and owned:
        return False
    if owned & _LATER_MODALITIES:
        return False
    return True


def _take(
    candidate: dict,
    counts: dict[str, int],
    chosen: dict[str, set[str]],
    selected: list[dict],
) -> None:
    area = candidate["area"]
    counts[area] = counts.get(area, 0) + 1
    item_key = candidate.get("item_key")
    if item_key:
        chosen.setdefault(str(item_key), set()).add(str(candidate.get("modality") or ""))
    selected.append(candidate)


def _order_by_phase(selected: list[dict]) -> list[dict]:
    buckets: dict[int, list[dict]] = {}
    for candidate in selected:
        rank = PHASE_RANK.get(str(candidate.get("phase_hint") or "practicing"), PHASE_RANK["practicing"])
        buckets.setdefault(rank, []).append(candidate)
    ordered: list[dict] = []
    for rank in sorted(buckets):
        ordered.extend(_spread_modalities(buckets[rank]))
    return ordered


def _spread_modalities(phase_items: list[dict]) -> list[dict]:
    remaining = list(phase_items)
    ordered: list[dict] = []
    while remaining:
        tail = [str(item.get("modality")) for item in ordered[-MAX_CONSECUTIVE_SAME_MODALITY:]]
        pick = 0
        if (
            len(tail) == MAX_CONSECUTIVE_SAME_MODALITY
            and len(set(tail)) == 1
        ):
            for index, item in enumerate(remaining):
                if str(item.get("modality")) != tail[0]:
                    pick = index
                    break
        ordered.append(remaining.pop(pick))
    return ordered


def _candidate(
    activity: dict,
    *,
    priority: int,
    item_key: str | None = None,
    overflow: bool = False,
    modality: str | None = None,
    area: str | None = None,
) -> dict:
    activity_type = str(activity.get("type") or "")
    return {
        "area": area or activity_area(activity_type),
        "modality": modality or activity_type,
        "phase_hint": activity.get("phase_hint") or "practicing",
        "priority": priority,
        "item_key": item_key,
        "overflow": overflow,
        "activity": activity,
    }


def modalities_for_item(
    evaluated_types: set[str],
    *,
    available_types: set[str],
    last_incorrect_type: str | None = None,
) -> list[str]:
    """No máximo a abertura (apresentação + reconhecimento) ou uma evidência posterior."""
    required_seen = evaluated_types & set(
        (
            EvidenceType.RECOGNITION,
            EvidenceType.REVERSE_RECOGNITION,
            EvidenceType.LISTENING_RECOGNITION,
            EvidenceType.LEXICAL_PRODUCTION,
        )
    )
    if EvidenceType.EXPOSURE not in evaluated_types and not required_seen:
        opening = [item for item in _OPENING_MODALITIES if item in available_types]
        return opening
    nxt = next_review_modality(required_seen, last_incorrect_type)
    if nxt in available_types:
        return [nxt]
    return []


def lexical_candidates_for_items(
    items: list[VocabularyItem],
    *,
    examples_by_item: dict[str, list[VocabularyExample]],
    memory_by_item: dict[str, MemorySchedule],
    evaluated_by_item: dict[str, set[str]],
    lesson_item_ids: set[str],
    last_incorrect_by_item: dict[str, str] | None = None,
    now: datetime | None = None,
) -> list[dict]:
    current = _aware(now or datetime.now(timezone.utc))
    last_incorrect_by_item = last_incorrect_by_item or {}
    generated = generate_vocabulary_activities(
        items,
        examples_by_item=examples_by_item,
        memory_by_item=memory_by_item,
        now=current,
    )
    by_item: dict[str, dict[str, dict]] = {}
    for activity in generated:
        item_id = activity.get("vocabulary_item_id")
        if not item_id:
            continue
        by_item.setdefault(item_id, {})[activity["type"]] = activity

    candidates: list[dict] = []
    for item in items:
        available = by_item.get(item.id) or {}
        steps = modalities_for_item(
            evaluated_by_item.get(item.id, set()),
            available_types=set(available),
            last_incorrect_type=last_incorrect_by_item.get(item.id),
        )
        schedule = memory_by_item.get(item.id)
        due = schedule is not None and _aware(schedule.due_at) <= current
        in_lesson = item.id in lesson_item_ids
        priority = 0 if in_lesson else (1 if due else 2)
        for step in steps:
            candidates.append(
                _candidate(available[step], priority=priority, item_key=item.id)
            )
    return candidates


def supporting_candidates(
    *,
    language_code: str,
    level: str | None,
) -> list[dict]:
    """Gramática, escuta e conversação que já existem no banco de lições.

    Não duplica exercício para completar o número. Se o banco não tiver
    a área, a sessão simplesmente fica mais curta.
    """
    from app.services.lesson_bank import (
        band_for,
        conversation_situation,
        grammar_examples,
        grammar_exercises,
        listening_script,
    )

    band = band_for(level or "A1")
    candidates: list[dict] = []
    examples = grammar_examples(language_code, band)
    sentences = [item.get("sentence") for item in examples if item.get("sentence")]
    if sentences:
        candidates.append(
            _candidate(
                {
                    "type": ActivityType.RECOGNITION,
                    "phase_hint": "noticing",
                    "prompt_pt": "Observe o padrão destas frases.",
                    "examples": sentences[:3],
                    "ai_required": False,
                },
                priority=1,
                item_key=f"grammar-notice-{band}",
                modality="noticing",
                area="grammar",
            )
        )
    for exercise in grammar_exercises(language_code, band):
        prompt = exercise.get("prompt")
        answer = exercise.get("answer")
        options = exercise.get("options") or []
        if not prompt or not answer or len(options) < 2:
            continue
        candidates.append(
            _candidate(
                {
                    "type": ActivityType.MULTIPLE_CHOICE,
                    "phase_hint": "noticing",
                    "prompt_pt": "Por que esta forma?",
                    "prompt": prompt,
                    "options": list(options),
                    "canonical_answer": answer,
                    "accepted_variants": [answer],
                    "correct_explanation": exercise.get("rationale"),
                    "option_rationales": exercise.get("option_rationales") or {},
                    "ai_required": False,
                },
                priority=1,
                item_key=f"grammar:{prompt}",
                area="grammar",
            )
        )
    script = listening_script(language_code, band)
    transcript = script.get("transcript") if isinstance(script, dict) else None
    if isinstance(transcript, str) and transcript.strip():
        candidates.append(
            _candidate(
                {
                    "type": ActivityType.LISTEN,
                    "phase_hint": "practicing",
                    "prompt_pt": "Ouça o modelo. Não responda ainda.",
                    "models": [transcript],
                    "show_text": True,
                    "ai_required": False,
                },
                priority=1,
                item_key=f"listening-script-{band}",
                area="listening",
            )
        )
    situation = conversation_situation(language_code, band)
    text = situation.get("situation") if isinstance(situation, dict) else None
    if isinstance(text, str) and text.strip():
        candidates.append(
            _candidate(
                {
                    "type": ActivityType.CONVERSATION_PROMPT,
                    "phase_hint": "producing",
                    "prompt_pt": text,
                    "prompt": situation.get("focus") or text,
                    "ai_required": False,
                },
                priority=1,
                item_key=f"conversation-{band}",
                area="conversation",
            )
        )
    return [item for item in candidates if item.get("area")]


def area_summary(activities: list[dict], cursor: int) -> list[dict]:
    totals: dict[str, int] = {}
    done: dict[str, int] = {}
    for index, activity in enumerate(activities):
        if not isinstance(activity, dict):
            continue
        area = activity.get("session_area")
        if not isinstance(area, str) or area not in AREA_LABELS:
            continue
        totals[area] = totals.get(area, 0) + 1
        if index < cursor:
            done[area] = done.get(area, 0) + 1
    return [
        {
            "key": area,
            "label": AREA_LABELS[area],
            "completed": done.get(area, 0),
            "total": totals[area],
        }
        for area in AREA_ORDER
        if area in totals
    ]


def load_session_candidates(
    db: Session,
    *,
    user_language_id: str,
    lesson_items: list[VocabularyItem],
    language_code: str,
    level: str | None,
) -> list[dict]:
    lesson_ids = {item.id for item in lesson_items}
    now = datetime.now(timezone.utc)
    due_ids = list(
        db.scalars(
            select(MemorySchedule.subject_key)
            .where(
                MemorySchedule.user_language_id == user_language_id,
                MemorySchedule.subject_type == MemorySubjectType.VOCABULARY,
                MemorySchedule.due_at <= now,
            )
            .order_by(MemorySchedule.due_at.asc())
            .limit(TARGET_SESSION_EXERCISES)
        )
    )
    extra_ids = [item_id for item_id in due_ids if item_id not in lesson_ids]
    extra_items = []
    if extra_ids:
        extra_items = list(
            db.scalars(
                select(VocabularyItem).where(
                    VocabularyItem.id.in_(extra_ids),
                    VocabularyItem.user_language_id == user_language_id,
                )
            )
        )
    items = list(lesson_items) + extra_items
    item_ids = [item.id for item in items]
    examples_by_item: dict[str, list[VocabularyExample]] = {item_id: [] for item_id in item_ids}
    if item_ids:
        for example in db.scalars(
            select(VocabularyExample)
            .where(VocabularyExample.vocabulary_item_id.in_(item_ids))
            .order_by(VocabularyExample.id.asc())
        ):
            examples_by_item.setdefault(example.vocabulary_item_id, []).append(example)
    schedules = list(
        db.scalars(
            select(MemorySchedule).where(
                MemorySchedule.user_language_id == user_language_id,
                MemorySchedule.subject_type == MemorySubjectType.VOCABULARY,
                MemorySchedule.subject_key.in_(item_ids),
            )
        )
    ) if item_ids else []
    memory_by_item = {schedule.subject_key: schedule for schedule in schedules}
    evaluated: dict[str, set[str]] = {item_id: set() for item_id in item_ids}
    if item_ids:
        for item_id, evidence_type in db.execute(
            select(LearningEvidence.vocabulary_item_id, LearningEvidence.evidence_type).where(
                LearningEvidence.user_language_id == user_language_id,
                LearningEvidence.vocabulary_item_id.in_(item_ids),
            )
        ):
            if item_id:
                evaluated.setdefault(item_id, set()).add(evidence_type)
    lexical = lexical_candidates_for_items(
        items,
        examples_by_item=examples_by_item,
        memory_by_item=memory_by_item,
        evaluated_by_item=evaluated,
        lesson_item_ids=lesson_ids,
        now=now,
    )
    if not lexical:
        return []
    return lexical + supporting_candidates(language_code=language_code, level=level)
