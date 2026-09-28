"""Boletim da lição — a correção que sobrevive ao fim da sessão.

Antes disto, `build_answer_feedback` era calculado na hora da resposta, ia para
a tela e se perdia: `payload_json["last_answer_feedback"]` guarda só a última.
Aqui cada resposta com produção real deixa um snapshot em
`learning_attempts.report_json`, e o boletim é a leitura desses snapshots.

Duas regras que definem o módulo:

1. **Snapshot, não reconstrução.** O boletim mostra o que o aluno viu naquele
   momento. Tentativa sem snapshot (anterior à migration 0015) aparece com a
   ausência declarada, nunca com uma correção remontada depois.
2. **"Continuar" não é resposta.** Atividade expositiva não gera linha de
   boletim: não houve produção para corrigir.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LearningAttempt, Lesson, VocabularyItem

#: Campos de correção que o snapshot copia do feedback já calculado.
_FEEDBACK_FIELDS = ("why_selected", "why_correct", "remember")


def build_report_snapshot(
    *,
    activity: dict[str, Any],
    student_response: str,
    result: str,
    answer_feedback: dict[str, Any] | None,
    term: str | None = None,
) -> dict[str, Any]:
    """Monta a linha do boletim a partir do que existia na hora da correção."""
    prompt = (
        activity.get("prompt")
        or activity.get("question")
        or activity.get("instruction")
        or activity.get("text")
        or ""
    )
    snapshot: dict[str, Any] = {
        "activity_type": activity.get("type") or "practice",
        "prompt": str(prompt),
        "student_response": student_response,
        "correct_answer": activity.get("canonical_answer")
        or (activity.get("accepted_variants") or [None])[0]
        or "",
        "result": result,
        "term": term or "",
    }
    for field in _FEEDBACK_FIELDS:
        snapshot[field] = str((answer_feedback or {}).get(field) or "")
    return snapshot


def lesson_report(db: Session, lesson: Lesson) -> dict[str, Any]:
    """Boletim de uma lição: entradas em ordem de resposta, mais o resumo."""
    attempts = list(
        db.scalars(
            select(LearningAttempt)
            .where(LearningAttempt.lesson_id == lesson.id)
            .order_by(LearningAttempt.created_at, LearningAttempt.id)
        )
    )

    entries: list[dict[str, Any]] = []
    for attempt in attempts:
        snapshot = attempt.report_json
        if not snapshot:
            # Sem produção (atividade expositiva) ou tentativa antiga: fora do
            # boletim. O total do resumo conta entradas, não tentativas.
            continue
        entry = dict(snapshot)
        entry["id"] = attempt.id
        entry["attempt_number"] = attempt.attempt_number
        entry["answered_at"] = attempt.created_at.isoformat() if attempt.created_at else None
        entry["result"] = snapshot.get("result") or attempt.result
        if not entry.get("term") and attempt.vocabulary_item_id:
            item = db.get(VocabularyItem, attempt.vocabulary_item_id)
            entry["term"] = item.term if item else ""
        entries.append(entry)

    incorrect = sum(1 for entry in entries if entry["result"] == "incorrect")
    return {
        "lesson": {
            "id": lesson.id,
            "title": lesson.title,
            "objective": lesson.objective,
            "status": lesson.status,
        },
        "entries": entries,
        "summary": {
            "total": len(entries),
            "incorrect": incorrect,
            "correct": len(entries) - incorrect,
        },
        "disclaimer": (
            "O boletim mostra a correção como ela foi apresentada na hora da "
            "resposta. Tentativas sem correção registrada não aparecem."
        ),
    }
