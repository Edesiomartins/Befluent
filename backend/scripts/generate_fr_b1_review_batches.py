"""Gera lotes FR B1 para revisão humana.

Não usa o banco de produção. A sessão é SQLite em memória. O resultado
vai para backend/scripts/out/fr_b1_review_batches.json.

A chave de IA do projeto está em modo mock e não é usada. Os rascunhos
saem da fatia curada, com quality_status review_required. Nenhum item
é gravado como approved.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models import Base, ContentSource, ContentUnit, Language, LearningObjective
from app.services.activity_pool import generate_incremental_batches
from app.services.fr_b1_slice import activities

OUT = Path(__file__).resolve().parent / "out" / "fr_b1_review_batches.json"


def ai_block_reason() -> str | None:
    settings = get_settings()
    if settings.ai_mock_mode or not settings.openrouter_api_key:
        return (
            "Geração por modelo bloqueada: ai_mock_mode está ativo ou não há "
            "chave OpenRouter utilizável. O lote abaixo é a fatia curada local, "
            "não texto de um modelo."
        )
    return None


def _memory_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()


def _objective(db, language, skill: str, unit_id: str) -> LearningObjective:
    objective = LearningObjective(
        language_id=language.id,
        level="B1",
        code=f"FR-B1-{skill}"[:40],
        title="Fatia FR B1",
        can_do="Opinar e pedir informação em francês B1",
        skill_focus=skill,
        is_active=True,
        pedagogy_json={"activity_pool": []},
    )
    db.add(objective)
    db.flush()
    source = ContentSource(
        title="Fatia curada FR B1",
        language_id=language.id,
        review_status="APPROVED",
        usage_policy="OPEN_LICENSE",
    )
    db.add(source)
    db.flush()
    unit = ContentUnit(
        id=unit_id,
        source_id=source.id,
        language_id=language.id,
        cefr_level="B1",
        skill=skill,
        mode="guided",
        title=f"FR B1 {skill}",
        validation_status="APPROVED",
    )
    db.add(unit)
    db.flush()
    return objective


def _drafts(skill: str, objective_id: str, unit_id: str) -> list[dict]:
    drafts = []
    for activity in activities():
        if activity.get("skill") != skill:
            continue
        item = dict(activity)
        item["learning_objective_id"] = objective_id
        item["content_unit_id"] = unit_id
        item["quality_status"] = "generated"
        item["provenance"] = {"source": "curated_fr_b1_slice"}
        drafts.append(item)
    return drafts


def main() -> dict:
    block = ai_block_reason()
    db = _memory_session()
    language = Language(
        code="fr",
        name_pt="Francês",
        native_name="Français",
        description="",
        strategy_summary="",
    )
    db.add(language)
    db.flush()
    skills = []
    for activity in activities():
        if activity["skill"] not in skills:
            skills.append(activity["skill"])
    results = []
    accepted_items = []
    rejected = []
    for skill in skills:
        unit_id = f"unit-{skill}"
        objective = _objective(db, language, skill, unit_id)
        drafts = _drafts(skill, objective.id, unit_id)

        def generate_batch(objective, existing, batch_size, drafts=drafts):
            return drafts[:batch_size]

        batch_results = generate_incremental_batches(
            db,
            objective_id=objective.id,
            generate_batch=generate_batch,
            batch_count=1,
            batch_size=max(len(drafts), 1),
            required_quality="review_required",
        )
        for result in batch_results:
            for item in result["accepted"]:
                if item.get("quality_status") == "approved":
                    raise RuntimeError("Item aprovado não pode entrar no lote de revisão.")
                accepted_items.append(item)
            rejected.extend(result["rejected"])
        results.append({"skill": skill, "objective_id": objective.id, "drafts": len(drafts)})
    report = {
        "ai_generation": "blocked" if block else "available",
        "ai_block_reason": block,
        "target_language": "fr",
        "native_language": "pt-BR",
        "cefr_level": "B1",
        "database": "sqlite-memory",
        "generated": len(accepted_items) + len(rejected),
        "accepted_for_review": len(accepted_items),
        "rejected": len(rejected),
        "rejection_reasons": dict(Counter(item["reason"] for item in rejected)),
        "skills": results,
        "accepted": accepted_items,
        "rejected_items": rejected,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    db.close()
    return report


if __name__ == "__main__":
    written = main()
    print(
        f"gerados={written['generated']} aceitos_para_revisao={written['accepted_for_review']} "
        f"rejeitados={written['rejected']} motivos={written['rejection_reasons']}"
    )
    print(f"arquivo={OUT}")
    if written["ai_block_reason"]:
        print(written["ai_block_reason"])
