"""Progresso imediato da sessão e formato de bloco curto.

Isto não é domínio nem CEFR. É a posição dentro das atividades já geradas.
O bloco curto limita quantos itens entram de uma vez; a Teaching Flow
continua dona da ordem, porque a máquina de fases só avança.
"""

from __future__ import annotations

from app.core.teaching import ActivityType

#: Itens novos por bloco. Três palavras nas cinco etapas do ciclo lexical
#: cabem numa sentada curta sem cronômetro.
SHORT_SESSION_ITEM_LIMIT = 3

SHORT_SESSION_PHASES: tuple[dict[str, str], ...] = (
    {"key": "review", "label_pt": "Revisão curta"},
    {"key": "input", "label_pt": "Vocabulário"},
    {"key": "noticing", "label_pt": "Observar o padrão"},
    {"key": "recognition", "label_pt": "Reconhecimento e escuta"},
    {"key": "production", "label_pt": "Produção"},
    {"key": "application", "label_pt": "Aplicação contextual"},
)

ACTIVITY_LABELS: dict[str, str] = {
    ActivityType.PRESENTATION: "Apresentação",
    ActivityType.RECOGNITION: "Reconhecimento",
    ActivityType.REVERSE_RECOGNITION: "Reconhecimento inverso",
    ActivityType.LISTENING_RECOGNITION: "Escuta",
    ActivityType.LEXICAL_PRODUCTION: "Produção",
    ActivityType.REVIEW: "Revisão",
    ActivityType.LISTEN: "Escuta do modelo",
    ActivityType.GUIDED_PRODUCTION: "Produção guiada",
    ActivityType.FREE_PRODUCTION: "Produção livre",
}


def activity_label(activity: dict | None) -> str | None:
    if not activity:
        return None
    activity_type = activity.get("type")
    if not isinstance(activity_type, str):
        return None
    return ACTIVITY_LABELS.get(activity_type, activity_type)


def session_progress_from_activities(activities: list, cursor: int) -> dict:
    total = len(activities)
    completed = min(max(cursor, 0), total)
    current = activities[cursor] if 0 <= cursor < total else None
    nxt = activities[cursor + 1] if 0 <= cursor + 1 < total else None
    percent = round(100 * completed / total) if total else 0
    return {
        "completed": completed,
        "total": total,
        "percent": percent,
        "current_label": activity_label(current if isinstance(current, dict) else None),
        "next_label": activity_label(nxt if isinstance(nxt, dict) else None),
        "short_session_phases": list(SHORT_SESSION_PHASES),
    }


def session_progress_from_flow(session) -> dict:
    activities = (session.payload_json or {}).get("activities") or []
    return session_progress_from_activities(activities, session.activity_cursor)


def select_short_batch(items: list, *, previous_offset: int) -> tuple[list, int]:
    """Próximo bloco curto. O restante fica para 'Continuar estudando'."""
    if not items:
        return [], 0
    offset = previous_offset if 0 <= previous_offset < len(items) else 0
    batch = items[offset : offset + SHORT_SESSION_ITEM_LIMIT]
    return batch, offset + len(batch)
