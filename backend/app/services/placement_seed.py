"""Importação do banco de itens de nivelamento a partir de fixtures JSON.

O banco de itens NÃO é criado por migration: itens são conteúdo pedagógico
versionado, revisado e substituível, não estrutura de banco. Este seed é
idempotente e não destrutivo — itens removidos das fixtures são desativados
(`is_active = False`), nunca apagados, porque podem estar referenciados por
respostas de testes já realizados.

AVISO: banco inicial de desenvolvimento. Requer validação pedagógica antes de
uso definitivo.
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.levels import is_valid_level
from app.models import PlacementItem

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "placement_items"


def load_fixture(language_code: str) -> dict:
    path = DATA_DIR / f"{language_code}.json"
    if not path.exists():
        return {"version": 0, "language_code": language_code, "items": []}
    return json.loads(path.read_text(encoding="utf-8"))


def available_languages() -> list[str]:
    if not DATA_DIR.exists():
        return []
    return sorted(path.stem for path in DATA_DIR.glob("*.json"))


def _apply(item: PlacementItem, raw: dict, language_code: str, version: int) -> None:
    item.language_code = language_code
    item.cefr_level = raw["cefr_level"]
    item.skill = raw["skill"]
    item.item_type = raw["item_type"]
    item.prompt = raw["prompt"]
    item.instructions = raw.get("instructions")
    item.passage = raw.get("passage")
    item.options_json = raw.get("options", [])
    item.correct_answer_json = raw.get("correct_answer", {})
    item.explanation = raw.get("explanation")
    item.audio_url = raw.get("audio_url")
    item.audio_script = raw.get("audio_script")
    item.rubric_json = raw.get("rubric", {})
    item.difficulty = float(raw.get("difficulty", 0.5))
    item.discrimination = float(raw.get("discrimination", 1.0))
    item.is_active = True
    item.version = version


def seed_placement_items(db: Session, language_codes: list[str] | None = None) -> dict:
    """Insere/atualiza itens. Retorna contagem por idioma."""
    codes = language_codes or available_languages()
    summary: dict[str, int] = {}

    for code in codes:
        fixture = load_fixture(code)
        version = int(fixture.get("version", 1))
        raw_items = fixture.get("items", [])
        seen_keys: set[str] = set()

        for raw in raw_items:
            if not is_valid_level(raw.get("cefr_level")):
                raise ValueError(
                    f"Item {raw.get('external_key')} usa nível inválido: {raw.get('cefr_level')}"
                )
            key = raw["external_key"]
            seen_keys.add(key)

            existing = db.scalar(
                select(PlacementItem).where(
                    PlacementItem.language_code == code,
                    PlacementItem.external_key == key,
                )
            )
            if existing is None:
                existing = PlacementItem(external_key=key)
                db.add(existing)
            _apply(existing, raw, code, version)

        # Itens fora da fixture atual são desativados, nunca removidos.
        current = db.scalars(
            select(PlacementItem).where(PlacementItem.language_code == code)
        ).all()
        for item in current:
            if item.external_key not in seen_keys:
                item.is_active = False

        summary[code] = len(seen_keys)

    db.commit()
    return summary
