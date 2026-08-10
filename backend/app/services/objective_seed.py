"""Seed do vertical slice Teaching Engine V2 — EN-A1-CAN-001.

Conteúdo A1 simples, sem vocabulário avançado. Idempotente.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.teaching import EvidenceType
from app.models import Language, LearningObjective

EN_A1_CAN_001 = {
    "code": "EN-A1-CAN-001",
    "level": "A1",
    "title": "Apresentar-se com informações pessoais básicas",
    "can_do": (
        "O aluno consegue apresentar-se e trocar informações pessoais básicas "
        "(nome, origem, cidade, profissão e gostos simples)."
    ),
    "description": (
        "Vertical slice do Teaching Engine V2. Foco em produção controlada e "
        "transferência, não em tradução palavra a palavra."
    ),
    "skill_focus": "conversation",
    "target_vocabulary": [
        "name",
        "from",
        "live",
        "work",
        "like",
        "professor",
        "student",
    ],
    "target_expressions": [
        "My name is Ana.",
        "I'm from Brazil.",
        "I live in Goiânia.",
        "I work as a professor.",
        "I like coffee.",
    ],
    "target_patterns": [
        {
            "canonical": "My name is Ana.",
            "accepted": ["My name is Ana.", "My name's Ana.", "I am Ana.", "I'm Ana."],
            "required_features": ["name"],
        },
        {
            "canonical": "I'm from Brazil.",
            "accepted": ["I'm from Brazil.", "I am from Brazil."],
            "required_features": ["from"],
        },
        {
            "canonical": "I live in Goiânia.",
            "accepted": ["I live in Goiânia.", "I live in Goiania.", "I live in Goiânia"],
            "required_features": ["live", "in"],
        },
        {
            "canonical": "I work as a professor.",
            "accepted": [
                "I work as a professor.",
                "I'm a professor.",
                "I am a professor.",
            ],
            "required_features": ["professor"],
            "required_patterns": [r"\b(i('m| am)|i work as)\b"],
            "evaluation_mode": "structural",
            "minimum_structure": "clause",
        },
        {
            "canonical": "I like coffee.",
            "accepted": ["I like coffee.", "I like coffee"],
            "required_features": ["like"],
        },
    ],
    "pronunciation_focus": ["name", "live", "work"],
    "pedagogy": {
        "activation": {
            "title_pt": "Apresentar-se",
            "can_do": (
                "O aluno consegue apresentar-se informando nome, origem, "
                "profissão e interesses básicos."
            ),
            "support_pt": (
                "Nesta atividade você vai ouvir, notar o padrão e praticar "
                "frases simples para se apresentar."
            ),
        },
        "noticing": {
            "prompt_pt": "Note: My name is… / I'm from… / I live in… / I work as… / I like…",
            "examples": [
                "My name is Ana.",
                "I'm from Brazil.",
                "I live in Goiânia.",
                "I work as a professor.",
                "I like coffee.",
            ],
        },
        "guided_prompt": {
            "prompt": "Tell me about yourself.",
            "prompt_pt": "Apresente-se em 2–4 frases simples.",
            "scaffold_pt": "My name is… I'm from… I live in… I work as… I like…",
            "required_features": ["name", "from", "live", "like"],
            "evaluation_mode": "guided",
            "minimum_structure": "clause",
        },
        "transfer_prompts": [
            {
                "prompt": "Where does your brother live?",
                "prompt_pt": "Onde mora o seu irmão?",
                "scaffold_pt": "He lives in…",
                "expected_features": ["live", "in"],
                "required_patterns": [r"\blives?\b"],
                "evaluation_mode": "transfer",
                "minimum_structure": "clause",
                "accepted_variants": [
                    "He lives in Goiânia.",
                    "He lives in Goiania.",
                    "My brother lives in Goiânia.",
                ],
            }
        ],
        "frequency_note": (
            "Vocabulário A1 de alta utilidade comunicativa (apresentação). "
            "Evitar itens avançados neste objetivo."
        ),
    },
    "mastery_policy": {
        "min_evidence_count": 2,
        "required_evidence_types": [
            EvidenceType.CORRECT_RESPONSE,
            EvidenceType.TRANSFER,
        ],
        "require_transfer_success": True,
        "block_on_unresolved_severity": "critical",
    },
}


def ensure_en_a1_can_001(db: Session) -> LearningObjective:
    language = db.scalar(select(Language).where(Language.code == "en"))
    if language is None:
        raise RuntimeError("Idioma 'en' não encontrado — rode seed_languages antes.")

    existing = db.scalar(
        select(LearningObjective).where(
            LearningObjective.language_id == language.id,
            LearningObjective.code == EN_A1_CAN_001["code"],
        )
    )
    data = EN_A1_CAN_001
    if existing is None:
        objective = LearningObjective(
            language_id=language.id,
            level=data["level"],
            code=data["code"],
            title=data["title"],
            can_do=data["can_do"],
            description=data["description"],
            skill_focus=data["skill_focus"],
            prerequisites_json=[],
            target_vocabulary_json=data["target_vocabulary"],
            target_expressions_json=data["target_expressions"],
            target_patterns_json=data["target_patterns"],
            pronunciation_focus_json=data["pronunciation_focus"],
            pedagogy_json=data["pedagogy"],
            mastery_policy_json=data["mastery_policy"],
            version=1,
            is_active=True,
        )
        db.add(objective)
        db.flush()
        return objective

    existing.title = data["title"]
    existing.can_do = data["can_do"]
    existing.description = data["description"]
    existing.skill_focus = data["skill_focus"]
    existing.target_vocabulary_json = data["target_vocabulary"]
    existing.target_expressions_json = data["target_expressions"]
    existing.target_patterns_json = data["target_patterns"]
    existing.pronunciation_focus_json = data["pronunciation_focus"]
    existing.pedagogy_json = data["pedagogy"]
    existing.mastery_policy_json = data["mastery_policy"]
    existing.is_active = True
    db.flush()
    return existing


def _theme_slug(theme: str) -> str:
    """Slug estável e curto para códigos de objetivo por tema."""
    import re
    import unicodedata

    normalized = unicodedata.normalize("NFKD", theme)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").upper()
    return (slug or "THEME")[:24]


def ensure_theme_objective(
    db: Session,
    *,
    language_code: str,
    level: str,
    theme: str,
) -> LearningObjective | None:
    """Objetivo leve por tema/nível — ancora `CurriculumBlock.objective_id`.

    Não substitui o vertical slice EN-A1-CAN-001; só liga o cronograma a um
    can-do observável por semana. Retorna None se o idioma não existir.
    """
    language = db.scalar(select(Language).where(Language.code == language_code))
    if language is None or not theme.strip():
        return None

    code = f"{language_code.upper().replace('-', '')}-{level}-TH-{_theme_slug(theme)}"[:40]
    existing = db.scalar(
        select(LearningObjective).where(
            LearningObjective.language_id == language.id,
            LearningObjective.code == code,
        )
    )
    title = f"{theme} · {level}"
    can_do = (
        f"O aluno consegue usar vocabulário e estruturas de {level} "
        f"para tratar o tema «{theme}» com clareza e coerência."
    )
    if existing is None:
        objective = LearningObjective(
            language_id=language.id,
            level=level,
            code=code,
            title=title,
            can_do=can_do,
            description=(
                "Objetivo gerado a partir do tema semanal do cronograma. "
                "Ancora pedagógica leve; pedagogia detalhada fica no Teaching Engine."
            ),
            skill_focus="vocabulary",
            prerequisites_json=[],
            target_vocabulary_json=[],
            target_expressions_json=[],
            target_patterns_json=[],
            pronunciation_focus_json=[],
            pedagogy_json={"theme": theme, "source": "curriculum_theme"},
            mastery_policy_json={},
            version=1,
            is_active=True,
        )
        db.add(objective)
        db.flush()
        return objective

    existing.title = title
    existing.can_do = can_do
    existing.skill_focus = "vocabulary"
    existing.pedagogy_json = {"theme": theme, "source": "curriculum_theme"}
    existing.is_active = True
    db.flush()
    return existing


def seed_teaching_objectives(db: Session) -> int:
    ensure_en_a1_can_001(db)
    from app.services.objective_seed_b2_week1 import ensure_en_b2_week1_objectives

    b2 = ensure_en_b2_week1_objectives(db)
    db.commit()
    return 1 + len(b2)
