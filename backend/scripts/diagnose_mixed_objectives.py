"""Diagnóstico somente leitura: objetivos mistos já gravados e inventário.

Não corrige lição, não promove conteúdo e não chama modelo. Sem --database-url
o relatório usa só o catálogo estático do código. Com URL, lê um sqlite local
ou um PostgreSQL cujo nome termina em _test. A transação é desfeita.

Uso, a partir de backend/:
    python scripts/diagnose_mixed_objectives.py
    python scripts/diagnose_mixed_objectives.py --database-url sqlite:///./tmp/copia.db
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select
from sqlalchemy.engine import Connection, make_url

from app.models import ContentUnit, Language, Lesson, User, UserLanguage
from app.services import lesson_bank as bank
from app.services.language_roles import apply_language_roles
from app.services.placement_seed import load_fixture
from app.services.seed import LANGUAGES


def static_inventory() -> list[dict]:
    """Conta o catálogo versionado. Não é o banco aprovado de produção."""
    rows = []
    for code, name_pt, *_rest in LANGUAGES:
        if code not in bank.SUPPORTED_LANGUAGES:
            continue
        vocabulary = bank.VOCABULARY.get(code, {})
        rows.append(
            {
                "language": code,
                "name_pt": name_pt,
                "vocabulary": sum(len(items) for items in vocabulary.values()),
                "reading": len(bank.READING_TEXTS.get(code, {})),
                "listening": len(bank.LISTENING_SCRIPTS.get(code, {})),
                "placement_items": len(load_fixture(code).get("items") or []),
            }
        )
    return rows


def _snippet(text: object, *, limit: int = 120) -> str:
    raw = str(text or "").replace("\n", " ").strip()
    if len(raw) <= limit:
        return raw
    return raw[: limit - 1].rstrip() + "…"


def _mixed_objective(text: object, target_language: str | None, native_language: str | None) -> dict | None:
    if not isinstance(text, str) or len(text.split()) < 4:
        return None
    payload = {"objective": text}
    findings = apply_language_roles(
        payload,
        target_language=target_language,
        native_language=native_language,
    )
    finding = next(
        (
            item
            for item in findings
            if item.get("field") == "objective" and item.get("reason") == "mixed_target_span"
        ),
        None,
    )
    if finding is None:
        return None
    return {
        "finding": finding,
        "proposal": {
            "objective_native": payload.get("objective"),
            "objective_target": payload.get("objective_target"),
            "strategy": (
                "split_mixed_target_span"
                if isinstance(payload.get("objective_target"), str) and payload.get("objective_target")
                else "manual_review_required"
            ),
        },
    }


def _json_object(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def scan_lessons(conn: Connection) -> dict:
    """Lista objetivos com trecho no idioma-alvo dentro da frase de apoio."""
    lessons, owners, languages, users = (
        Lesson.__table__,
        UserLanguage.__table__,
        Language.__table__,
        User.__table__,
    )
    rows = conn.execute(
        select(
            lessons.c.id,
            lessons.c.status,
            lessons.c.objective,
            lessons.c.content_json,
            languages.c.code.label("target_language"),
            users.c.native_language,
        )
        .join(owners, owners.c.id == lessons.c.user_language_id)
        .join(languages, languages.c.id == owners.c.language_id)
        .join(users, users.c.id == owners.c.user_id)
        .order_by(lessons.c.id)
    ).mappings()
    mixed = []
    per_language: Counter[str] = Counter()
    per_field: Counter[str] = Counter()
    per_status: Counter[str] = Counter()
    examples = []
    checked = 0
    for row in rows:
        checked += 1
        content = _json_object(row["content_json"])
        fields = {"objective": row["objective"]}
        if isinstance(content.get("objective"), str):
            fields["content_json.objective"] = content["objective"]
        for field, text in fields.items():
            result = _mixed_objective(text, row["target_language"], row["native_language"])
            if result is None:
                continue
            finding = result["finding"]
            proposal = result["proposal"]
            record = {
                "lesson_id": row["id"],
                "status": row["status"],
                "field": field,
                "target_language": row["target_language"],
                "native_language": row["native_language"],
                "action": finding.get("action"),
                "reason": finding.get("reason"),
                "detected_language": finding.get("detected_language"),
                "proposal": proposal,
            }
            mixed.append(record)
            lang = row["target_language"] or "unknown"
            per_language[lang] += 1
            per_field[field] += 1
            per_status[str(row["status"])] += 1
            if len(examples) < 12:
                examples.append(
                    {
                        "lesson_id": row["id"],
                        "language": lang,
                        "status": row["status"],
                        "field": field,
                        "objective_preview": _snippet(text),
                        "proposed_native_preview": _snippet(proposal.get("objective_native")),
                        "proposed_target_preview": _snippet(proposal.get("objective_target")),
                    }
                )
    return {
        "checked": checked,
        "mixed_count": len(mixed),
        "mixed_by_language": dict(sorted(per_language.items())),
        "mixed_by_field": dict(sorted(per_field.items())),
        "mixed_by_status": dict(sorted(per_status.items())),
        "examples": examples,
        "proposed_repair": {
            "mode": "diagnostic_only",
            "writes": 0,
            "sql_or_script_run": False,
            "steps": [
                "Filtrar lessons ativas por language/status usando mixed_by_language.",
                "Em cada linha, separar objective em objective_native e objective_target com strategy split_mixed_target_span.",
                "Revisar manualmente casos sem objective_target antes de qualquer update.",
                "Executar correção em transação com rollback ensaiado e auditoria por lesson_id.",
            ],
            "counts_by_language": dict(sorted(per_language.items())),
        },
        "mixed": mixed,
    }


def scan_content_units(conn: Connection) -> list[dict]:
    units, languages = ContentUnit.__table__, Language.__table__
    rows = conn.execute(
        select(
            languages.c.code.label("language"),
            units.c.cefr_level,
            units.c.skill,
            units.c.mode,
            units.c.validation_status,
            func.count().label("count"),
        )
        .join(languages, languages.c.id == units.c.language_id)
        .group_by(
            languages.c.code,
            units.c.cefr_level,
            units.c.skill,
            units.c.mode,
            units.c.validation_status,
        )
        .order_by(languages.c.code, units.c.cefr_level, units.c.skill, units.c.mode)
    ).mappings()
    return [dict(row) for row in rows]


def assert_safe_database_url(url: str) -> None:
    parsed = make_url(url)
    backend = parsed.get_backend_name()
    if backend == "sqlite":
        return
    if backend != "postgresql" or not (parsed.database or "").endswith("_test"):
        raise ValueError(
            "Este diagnóstico só abre sqlite ou um PostgreSQL cujo nome termina em _test."
        )


def diagnose(conn: Connection | None = None, *, database_url: str | None = None) -> dict:
    """Monta o relatório. Não grava. `writes` permanece 0."""
    report = {
        "mode": "dry_run",
        "writes": 0,
        "production": False,
        "static_inventory": static_inventory(),
        "database_inventory": None,
        "historical_lessons": None,
    }
    if database_url:
        assert_safe_database_url(database_url)
        from sqlalchemy import create_engine

        engine = create_engine(database_url)
        try:
            with engine.connect() as opened:
                transaction = opened.begin()
                try:
                    if opened.dialect.name == "postgresql":
                        opened.exec_driver_sql("SET TRANSACTION READ ONLY")
                    report["database_inventory"] = scan_content_units(opened)
                    report["historical_lessons"] = scan_lessons(opened)
                finally:
                    transaction.rollback()
        finally:
            engine.dispose()
        return report
    if conn is not None:
        report["database_inventory"] = scan_content_units(conn)
        report["historical_lessons"] = scan_lessons(conn)
    return report


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description="Diagnóstico somente leitura de objetivos mistos e do inventário.")
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args(argv)
    report = diagnose(database_url=args.database_url)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return report


if __name__ == "__main__":
    main()
