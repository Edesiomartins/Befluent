"""Speech Coach V1 — feedback pedagógico de inteligibilidade a partir do STT.

Usa `speech_intelligibility` (LCS). NÃO produz pronunciation score nem análise
fonética. Falhas técnicas (STT vazio, silêncio) NÃO viram LearningError.
"""

from __future__ import annotations

from typing import Any

from app.services.speech_intelligibility import (
    assess_intelligibility,
    normalize_speech_text,
)

#: Cobertura mínima para considerar a frase compreensível (repetição).
GOOD_COVERAGE = 0.85
#: Tentativas com problema antes de oferecer “continuar”.
MAX_REPAIR_ATTEMPTS = 3


def build_alignment_sequence(
    target_tokens: list[str], recognized_tokens: list[str]
) -> list[dict[str, str]]:
    """Sequência alinhada com papéis: match | miss | extra (para UI acessível)."""
    from app.services.speech_intelligibility import _lcs_table

    table = _lcs_table(target_tokens, recognized_tokens)
    i, j = len(target_tokens), len(recognized_tokens)
    ops: list[dict[str, str]] = []
    while i > 0 and j > 0:
        if target_tokens[i - 1] == recognized_tokens[j - 1]:
            ops.append({"role": "match", "token": target_tokens[i - 1]})
            i -= 1
            j -= 1
        elif table[i - 1][j] >= table[i][j - 1]:
            ops.append({"role": "miss", "token": target_tokens[i - 1]})
            i -= 1
        else:
            ops.append({"role": "extra", "token": recognized_tokens[j - 1]})
            j -= 1
    while i > 0:
        ops.append({"role": "miss", "token": target_tokens[i - 1]})
        i -= 1
    while j > 0:
        ops.append({"role": "extra", "token": recognized_tokens[j - 1]})
        j -= 1
    ops.reverse()
    return ops


def build_practice_chunk(
    target_tokens: list[str], missed_tokens: list[str]
) -> str | None:
    """Trecho curto (2–5 palavras) em torno do primeiro missed — não só a palavra."""
    if not target_tokens or not missed_tokens:
        return None
    focus = missed_tokens[0]
    try:
        idx = target_tokens.index(focus)
    except ValueError:
        idx = 0
    # Preferir 2–5 tokens com contexto.
    start = max(0, idx - 1)
    end = min(len(target_tokens), idx + 3)
    if end - start < 2:
        start = max(0, end - 2)
    if end - start > 5:
        end = start + 5
    chunk = " ".join(target_tokens[start:end])
    return chunk or None


def _priority_points(
    *,
    missed: list[str],
    extra: list[str],
    success: bool,
) -> list[dict[str, str]]:
    """No máximo 2 pontos prioritários — sem lista técnica enorme."""
    if success:
        return [
            {
                "kind": "good",
                "label_pt": "A frase foi compreensível.",
                "token": "",
            }
        ]
    points: list[dict[str, str]] = []
    for token in missed[:2]:
        points.append(
            {
                "kind": "missed",
                "label_pt": (
                    f"Não consegui identificar «{token}» com clareza na sua fala."
                ),
                "token": token,
            }
        )
        if len(points) >= 2:
            return points
    for token in extra[: 2 - len(points)]:
        points.append(
            {
                "kind": "extra",
                "label_pt": (
                    f"A transcrição identificou também «{token}». "
                    "Ouça novamente e compare."
                ),
                "token": token,
            }
        )
    if not points:
        points.append(
            {
                "kind": "needs_practice",
                "label_pt": "Vamos praticar este trecho novamente.",
                "token": "",
            }
        )
    return points[:2]


def _repair_plan(
    *,
    attempt_number: int,
    success: bool,
    practice_chunk: str | None,
    same_problem: bool,
) -> dict[str, Any]:
    if success:
        return {
            "action": "success",
            "label_pt": "Bom trabalho. Você pode seguir ou praticar a frase de novo.",
            "level": 0,
            "allow_continue": True,
            "practice_chunk": None,
        }
    level = min(max(attempt_number, 1), MAX_REPAIR_ATTEMPTS + 1)
    if attempt_number >= MAX_REPAIR_ATTEMPTS:
        return {
            "action": "continue",
            "label_pt": (
                "Você já praticou várias vezes. Pode continuar — "
                "voltaremos a este trecho na revisão quando fizer sentido."
            ),
            "level": level,
            "allow_continue": True,
            "practice_chunk": practice_chunk,
        }
    if attempt_number == 1:
        return {
            "action": "retry_full",
            "label_pt": "Ouça a frase de novo e tente a frase completa.",
            "level": 1,
            "allow_continue": False,
            "practice_chunk": None,
        }
    if attempt_number == 2 or same_problem:
        return {
            "action": "practice_chunk",
            "label_pt": (
                "Vamos isolar um trecho curto. Ouça o trecho e repita só essa parte."
            ),
            "level": 2,
            "allow_continue": False,
            "practice_chunk": practice_chunk,
        }
    return {
        "action": "contrast_model",
        "label_pt": (
            "Compare com o modelo: ouça a frase inteira com atenção e tente de novo."
        ),
        "level": 3,
        "allow_continue": False,
        "practice_chunk": practice_chunk,
    }


def coach_from_transcript(
    *,
    target_text: str,
    transcript: str | None,
    provider: str | None = None,
    attempt_number: int = 1,
    previous_missed: list[str] | None = None,
    mode: str = "repetition",
) -> dict[str, Any]:
    """Avalia uma tentativa de fala para o Speech Coach.

    `mode=repetition` é mais estrito (shadowing). Produção aberta fica para
    outro evaluator — não misturar com “falou a frase literal”.
    """
    raw = (transcript or "").strip()
    if not raw:
        return {
            "status": "technical_issue",
            "is_phonetic_score": False,
            "pedagogical_error": False,
            "success": False,
            "transcript": raw,
            "normalized_target": normalize_speech_text(target_text),
            "normalized_transcript": "",
            "provider": provider,
            "intelligibility": None,
            "alignment_sequence": [],
            "feedback": {
                "summary_pt": (
                    "Não recebi uma transcrição utilizável. "
                    "Pode ter sido silêncio, áudio curto ou falha do reconhecimento — "
                    "isso não conta como erro seu. Tente gravar de novo."
                ),
                "points": [],
                "metric_name": "speech_correspondence",
                "metric_label_pt": "Correspondência da fala (tokens reconhecidos)",
                "coverage": None,
            },
            "repair": {
                "action": "retry_record",
                "label_pt": "Grave novamente quando estiver pronto.",
                "level": 0,
                "allow_continue": True,
                "practice_chunk": None,
            },
            "practice_chunk": None,
            "attempt_number": attempt_number,
        }

    assessment = assess_intelligibility(
        target_text=target_text,
        transcript=raw,
        provider=provider,
    )
    intel = assessment["intelligibility"]
    target_tokens = list(intel["target_tokens"])
    recognized = list(intel["recognized_tokens"])
    missed = list(intel["missed_tokens"])
    extra = list(intel["extra_tokens"])
    coverage = float(intel["coverage"])
    sequence = build_alignment_sequence(target_tokens, recognized)

    if mode == "repetition":
        success = len(missed) == 0 and coverage >= GOOD_COVERAGE
    else:
        # Modo mais permissivo (produção guiada futura): cobertura alta basta.
        success = coverage >= GOOD_COVERAGE and len(missed) <= 1

    practice_chunk = None if success else build_practice_chunk(target_tokens, missed)
    prev = set(previous_missed or [])
    same_problem = bool(prev and prev.intersection(missed))

    points = _priority_points(missed=missed, extra=extra, success=success)
    if success:
        summary = "A frase foi compreensível."
        status = "good"
    elif len(missed) > 1 and len(extra) > 0:
        summary = (
            "Alguns trechos não ficaram claros na transcrição. "
            "Vamos focar no mais importante."
        )
        status = "needs_practice"
    elif missed:
        summary = f"Não consegui identificar «{missed[0]}» com clareza na sua fala."
        status = "needs_practice"
    else:
        summary = "A transcrição trouxe palavras a mais. Ouça e compare com o modelo."
        status = "needs_practice"

    repair = _repair_plan(
        attempt_number=attempt_number,
        success=success,
        practice_chunk=practice_chunk,
        same_problem=same_problem,
    )

    return {
        "status": status,
        "is_phonetic_score": False,
        "pedagogical_error": status == "needs_practice",
        "success": success,
        "transcript": raw,
        "normalized_target": normalize_speech_text(target_text),
        "normalized_transcript": assessment["normalized_transcript"],
        "provider": provider,
        "intelligibility": {
            **intel,
            #: Explicitamente NÃO é pronunciation score.
            "is_pronunciation_score": False,
        },
        "alignment_sequence": sequence,
        "feedback": {
            "summary_pt": summary,
            "points": points,
            "metric_name": intel["metric_name"],
            "metric_label_pt": intel["metric_label_pt"],
            "coverage": coverage,
        },
        "repair": repair,
        "practice_chunk": practice_chunk,
        "attempt_number": attempt_number,
        "target_text": target_text,
    }


def maybe_record_spoken_evidence(
    db: Any,
    *,
    user_language_id: str,
    objective_id: str | None,
    coach_result: dict[str, Any],
) -> dict[str, Any] | None:
    """Se houver LearningObjective e sucesso, registra evidência leve — sem mastery."""
    if not objective_id or not coach_result.get("success"):
        return None
    if coach_result.get("status") == "technical_issue":
        return None
    from app.core.teaching import AttemptResult, EvidenceType
    from app.services import teaching_engine

    attempt = teaching_engine.record_attempt(
        db,
        user_language_id=user_language_id,
        objective_id=objective_id,
        activity_type="speech_repetition",
        student_response=coach_result.get("transcript"),
    )
    # Evidência de inteligibilidade — evaluate_mastery pode rodar, mas uma
    # única SPOKEN_INTELLIGIBILITY não satisfaz a policy sozinha.
    teaching_engine.evaluate_attempt(
        db,
        attempt,
        result=AttemptResult.CORRECT,
        score=float((coach_result.get("feedback") or {}).get("coverage") or 0),
        provider=str(coach_result.get("provider") or "stt"),
        evidence_type=EvidenceType.SPOKEN_INTELLIGIBILITY,
        is_transfer=False,
    )
    return {
        "attempt_id": attempt.id,
        "evidence_type": EvidenceType.SPOKEN_INTELLIGIBILITY,
    }
