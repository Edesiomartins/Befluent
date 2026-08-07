"""Ponte entre o teste de nivelamento e as lições.

O teste de nivelamento grava em `UserLanguage` o nível CEFR geral, os níveis por
competência e a confiança da estimativa. Antes deste módulo esses dados só eram
lidos pelo dashboard: as lições eram estáticas e iguais para todos os alunos.

`LearnerContext` reúne esses dados com as preferências do onboarding (objetivo,
minutos por dia, competências prioritárias) e os transforma no bloco `# CONTEXT`
dos prompts em `app/prompts/library.py`. É esse bloco que faz uma lição de
vocabulário para PRE_A1 sair diferente de uma para B2.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.levels import (
    LEVEL_DETAILS,
    LEVEL_INDEX,
    LEVEL_ORDER,
    SKILL_LABELS,
    CEFRLevel,
    LevelSource,
    Skill,
    level_at,
    normalize_level,
)
from app.models import Language, User, UserLanguage, UserPreference

#: Nível assumido quando o aluno ainda não tem avaliação nem nível declarado.
#: A2 é o mesmo ponto de partida do teste adaptativo — a faixa que menos
#: desperdiça itens quando não se sabe nada sobre o aluno.
DEFAULT_LEVEL = CEFRLevel.A2

#: Regras de escrita/fonologia que o modelo precisa seguir por idioma. Sem
#: isso, uma lição de japonês volta em romaji e uma de mandarim sem tom marcado
#: — as duas coisas que `docs/language-strategies.md` proíbe.
SCRIPT_RULES: dict[str, str] = {
    "ja": (
        "Regra de escrita: escreva em japonês real (kana e kanji), com furigana "
        "em hiragana entre parênteses logo após cada palavra com kanji. Use romaji "
        "apenas como apoio adicional, nunca como forma principal."
    ),
    "zh-CN": (
        "Regra de escrita: escreva em caracteres simplificados (hanzi) e forneça "
        "sempre o pinyin com marcação de tom (ā á ǎ à) junto de cada item. "
        "Explique diferenças de significado causadas pelo tom quando forem relevantes."
    ),
    "es-ES": (
        "Variante: espanhol da Espanha. Use vocabulário peninsular e a forma "
        "vosotros quando couber; sinalize regionalismos."
    ),
}

SKILL_COLUMNS: dict[str, str] = {
    Skill.VOCABULARY_GRAMMAR: "vocabulary_grammar_level",
    Skill.READING: "reading_level",
    Skill.LISTENING: "listening_level",
    Skill.WRITING: "writing_level",
    Skill.SPEAKING: "speaking_level",
}


@dataclass
class LearnerContext:
    """Retrato do aluno em um idioma, no momento da geração da lição."""

    language_code: str
    language_name_pt: str
    language_native_name: str

    level: str
    level_name_pt: str
    level_description: str
    level_source: str
    level_is_estimated: bool

    skill_levels: dict[str, str | None] = field(default_factory=dict)
    weakest_skills: list[str] = field(default_factory=list)
    confidence_score: float | None = None

    goal: str | None = None
    minutes_per_day: int | None = None
    priority_skills: list[str] = field(default_factory=list)
    recommendations: list = field(default_factory=list)

    #: Preenchidos quando a lição vem de um bloco do cronograma. Sem eles o
    #: modelo geraria "vocabulário B1" genérico em toda semana do plano.
    topic: str | None = None
    curriculum_week_theme: str | None = None

    @property
    def level_index(self) -> int:
        return LEVEL_INDEX[self.level]

    def level_for_skill(self, skill: str | None) -> str:
        """Nível a usar numa lição que treina `skill`.

        Uma lição deve calibrar pela competência que ela treina, não pelo nível
        geral: quem lê em B2 mas escreve em A2 precisa de leitura B2 e escrita
        A2. Sem avaliação daquela competência, cai no nível geral.
        """
        if not skill:
            return self.level
        return self.skill_levels.get(skill) or self.level

    def next_level(self) -> str:
        return level_at(self.level_index + 1)

    def to_prompt_context(self, skill: str | None = None) -> str:
        """Bloco `# CONTEXT` dos prompts do documento, preenchido com dados reais."""
        target = self.level_for_skill(skill)
        lines = [
            "Idioma-alvo: "
            f"{self.language_name_pt} ({self.language_native_name}, código {self.language_code})",
            "Idioma nativo do aluno: português do Brasil",
            f"Nível CEFR do aluno: {target} — {LEVEL_DETAILS[target]['name_pt']}",
            f"Descrição do nível: {LEVEL_DETAILS[target]['short_description']}",
        ]

        if self.level_is_estimated:
            confidence = (
                f" (confiança da estimativa: {self.confidence_score:.0f}/100)"
                if self.confidence_score is not None
                else ""
            )
            lines.append(f"Origem do nível: teste de nivelamento{confidence}")
        else:
            lines.append("Origem do nível: informado pelo próprio aluno, ainda não testado")

        assessed = [
            f"{SKILL_LABELS[code]}: {value}"
            for code, value in self.skill_levels.items()
            if value
        ]
        if assessed:
            lines.append("Níveis por competência: " + "; ".join(assessed))

        if self.weakest_skills:
            labels = ", ".join(SKILL_LABELS[code] for code in self.weakest_skills)
            lines.append(f"Competências mais fracas (priorizar): {labels}")

        if self.goal:
            lines.append(f"Objetivo do aluno: {self.goal}")
        if self.minutes_per_day:
            lines.append(f"Tempo disponível por dia: {self.minutes_per_day} minutos")
        if self.priority_skills:
            lines.append(
                "Competências que o aluno escolheu priorizar: "
                + ", ".join(self.priority_skills)
            )

        if self.curriculum_week_theme:
            lines.append(f"Tema da semana no cronograma: {self.curriculum_week_theme}")
        if self.topic:
            lines.append(
                f"Tópico obrigatório desta atividade: {self.topic}. "
                "A atividade precisa tratar deste tópico, não de um tema genérico."
            )

        script_rule = SCRIPT_RULES.get(self.language_code)
        if script_rule:
            lines.append(script_rule)

        return "\n".join(lines)


def _weakest_skills(skill_levels: dict[str, str | None]) -> list[str]:
    """Competências avaliadas no menor nível. Vazio se nada foi avaliado."""
    assessed = {code: value for code, value in skill_levels.items() if value}
    if not assessed:
        return []
    lowest = min(LEVEL_INDEX[value] for value in assessed.values())
    return [code for code, value in assessed.items() if LEVEL_INDEX[value] == lowest]


def build_context(db: Session, user: User, language_code: str) -> LearnerContext:
    """Monta o contexto do aluno para um idioma.

    Levanta `LookupError` se o idioma não existe. Se o usuário ainda não tem
    perfil naquele idioma, devolve um contexto no nível padrão — gerar uma lição
    não deve exigir onboarding concluído.
    """
    language = db.scalar(select(Language).where(Language.code == language_code))
    if not language:
        raise LookupError(language_code)

    profile = db.scalar(
        select(UserLanguage).where(
            UserLanguage.user_id == user.id,
            UserLanguage.language_id == language.id,
        )
    )
    preference = db.scalar(select(UserPreference).where(UserPreference.user_id == user.id))
    ui_prefs = dict(preference.ui_prefs_json or {}) if preference else {}

    skill_levels: dict[str, str | None] = {code: None for code in SKILL_COLUMNS}
    level = DEFAULT_LEVEL
    level_source = LevelSource.PENDING
    confidence = None

    if profile:
        # `current_level` é CEFR; `level_estimate` pode guardar rótulo legado.
        level = (
            normalize_level(profile.current_level)
            or normalize_level(profile.level_estimate)
            or DEFAULT_LEVEL
        )
        level_source = profile.level_source or LevelSource.PENDING
        confidence = profile.confidence_score
        for code, column in SKILL_COLUMNS.items():
            skill_levels[code] = normalize_level(getattr(profile, column, None))

    return LearnerContext(
        language_code=language.code,
        language_name_pt=language.name_pt,
        language_native_name=language.native_name,
        level=level,
        level_name_pt=LEVEL_DETAILS[level]["name_pt"],
        level_description=LEVEL_DETAILS[level]["short_description"],
        level_source=level_source,
        level_is_estimated=level_source == LevelSource.PLACEMENT_TEST,
        skill_levels=skill_levels,
        weakest_skills=_weakest_skills(skill_levels),
        confidence_score=confidence,
        goal=ui_prefs.get("primary_goal"),
        minutes_per_day=ui_prefs.get("minutes_per_day"),
        priority_skills=list(ui_prefs.get("skills") or []),
        recommendations=list(profile.recommendations_json or []) if profile else [],
    )


def for_curriculum_block(
    context: LearnerContext,
    *,
    assessed_skill: str,
    cefr_level: str,
    topic: str | None,
    week_theme: str | None = None,
) -> LearnerContext:
    """Contexto calibrado para um bloco do cronograma.

    O nível do bloco vem do cronograma, não do perfil: depois de uma promoção
    por checkpoint, o plano avança antes de o perfil ser reavaliado por inteiro.
    Usar o nível do perfil aqui congelaria o aluno na faixa antiga.
    """
    return replace(
        context,
        skill_levels={**context.skill_levels, assessed_skill: cefr_level},
        topic=topic,
        curriculum_week_theme=week_theme,
    )


def recommended_modes(context: LearnerContext, limit: int = 3) -> list[str]:
    """Modos de estudo que atacam as competências mais fracas do teste.

    Sem avaliação, devolve uma sequência neutra em vez de fingir personalização.
    """
    from app.prompts.library import MODE_SKILL

    if not context.weakest_skills:
        return ["guided", "vocabulary", "conversation"][:limit]

    priority = [
        mode
        for mode, skill in MODE_SKILL.items()
        if skill in context.weakest_skills and mode != "voice"
    ]
    return priority[:limit] or ["guided"]
