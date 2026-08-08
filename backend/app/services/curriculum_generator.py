"""Gerador do cronograma estruturado a partir do teste de nivelamento.

O que este módulo resolve: até aqui o resultado do nivelamento calibrava cada
lição isoladamente (`learner_context`), mas não existia sequência. O aluno via
"vocabulário B1" no dia 3 e "vocabulário B1" no dia 40, sem progressão nem
prazo. Aqui os níveis por competência gravados em `UserLanguage` viram um
cronograma com data por dia, tema por semana e meta declarada.

LIMITAÇÃO DECLARADA: a distribuição de semanas por nível e os pesos por
competência são heurísticas explícitas, não um modelo validado de aquisição.
Um cronograma de 90 dias não garante B1 — ele organiza o estudo necessário
para tentar. `docs/learning-engine.md` mantém a regra: não prometer fluência
em prazo fixo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.curriculum import (
    ALLOWED_DURATIONS,
    BLOCK_ASSESSED_SKILL,
    INPUT_BLOCKS,
    OUTPUT_BLOCKS,
    BlockSkill,
    BlockStatus,
    CurriculumStatus,
    DayStatus,
    GeneratedFrom,
)
from app.core.errors import APIError
from app.core.levels import LEVEL_INDEX, CEFRLevel, level_at, normalize_level
from app.models import (
    Curriculum,
    CurriculumBlock,
    CurriculumDay,
    CurriculumWeek,
    Language,
    UserLanguage,
)
from app.services.curriculum_bank import block_topic, weekly_theme
from app.services.learner_context import SKILL_COLUMNS

#: Teto do cronograma. C1/C2 não têm banco de itens validado (ver
#: `levels.TESTABLE_LEVELS`): prometer C1 em 180 dias seria promessa sem lastro.
MAX_TARGET_LEVEL = CEFRLevel.B2

#: Ganho esperado no plano curto, em subníveis CEFR.
SHORT_PLAN_GAIN = 2

#: Minutos base por bloco, antes dos pesos adaptativos. Soma ≈ 59 min no dia
#: cheio, dentro da faixa de 45–60 min prevista para o dia de estudo.
BASE_MINUTES: dict[str, int] = {
    BlockSkill.VOCABULARY: 10,
    BlockSkill.GRAMMAR: 10,
    BlockSkill.LISTENING: 12,
    BlockSkill.READING: 12,
    BlockSkill.CONVERSATION: 12,
    BlockSkill.WRITING: 12,
    BlockSkill.PRONUNCIATION: 5,
    BlockSkill.REVIEW: 10,
}

#: Multiplicador por posição da competência em relação à mediana do aluno.
#: Abaixo da mediana = lacuna, recebe mais tempo. Acima = manutenção.
WEIGHT_BEHIND = 1.5
WEIGHT_ON_LEVEL = 1.0
WEIGHT_AHEAD = 0.7

MIN_BLOCK_MINUTES = 5

#: Idiomas em que a pronúncia é diária, não 3x por semana. Japonês depende de
#: duração vocálica e mora; mandarim, de tom — em ambos o erro fonético muda o
#: significado, não só o sotaque (`docs/language-strategies.md`).
DAILY_PRONUNCIATION_LANGUAGES = frozenset({"ja", "zh-CN"})

#: Dias da semana (0=segunda) com bloco de pronúncia nos demais idiomas.
PRONUNCIATION_WEEKDAYS = frozenset({0, 2, 4})

#: Transparência lexical com o português faz o aluno superestimar a
#: compreensão: ele lê bem e não entende a fala. Compensado com escuta extra.
LISTENING_BONUS_LANGUAGES = frozenset({"fr", "es-ES"})
LISTENING_BONUS_MINUTES = 3

SUNDAY = 6

#: Domingo é dia leve: só revisão e leitura. Um cronograma sem folga é
#: abandonado na terceira semana.
#: Domingo leve: input curto e só então consolidação (revisão nunca vem antes).
LIGHT_DAY_BLOCKS: tuple[str, ...] = (BlockSkill.READING, BlockSkill.REVIEW)

DAYS_PER_WEEK = 7


@dataclass(frozen=True)
class LevelStage:
    """Trecho do cronograma em um nível CEFR."""

    level: str
    weeks: int


# --------------------------------------------------------------------- níveis


def assessed_skill_levels(profile: UserLanguage) -> dict[str, str]:
    """Níveis por competência efetivamente gravados pelo nivelamento."""
    levels: dict[str, str] = {}
    for skill, column in SKILL_COLUMNS.items():
        value = normalize_level(getattr(profile, column, None))
        if value:
            levels[skill] = value
    return levels


def hydrate_skill_levels(profile: UserLanguage, level: str) -> bool:
    """Preenche competências vazias a partir de um nível CEFR único.

    Usado no onboarding (iniciante / autodeclarado): sem colunas por skill o
    gerador recusa o cronograma. Só preenche o que estiver vazio — nunca
    sobrescreve um resultado de teste.
    """
    cefr = normalize_level(level)
    if not cefr:
        return False
    changed = False
    for column in SKILL_COLUMNS.values():
        if not normalize_level(getattr(profile, column, None)):
            setattr(profile, column, cefr)
            changed = True
    if changed and not profile.current_level:
        profile.current_level = cefr
    return changed


def active_curriculum(db: Session, user_language_id: str) -> Curriculum | None:
    return db.scalar(
        select(Curriculum)
        .where(
            Curriculum.user_language_id == user_language_id,
            Curriculum.status == CurriculumStatus.ACTIVE,
        )
        .order_by(Curriculum.created_at.desc())
    )


def ensure_active_curriculum(
    db: Session,
    user_language_id: str,
    *,
    duration_days: int = 90,
    generated_from: str = GeneratedFrom.MANUAL,
) -> Curriculum:
    """Devolve o cronograma ativo ou gera um novo (idempotente)."""
    existing = active_curriculum(db, user_language_id)
    if existing is not None:
        return existing

    profile = db.get(UserLanguage, user_language_id)
    if profile is None:
        raise APIError(404, "language_not_configured", "Idioma não configurado para o usuário.")

    if not assessed_skill_levels(profile):
        fallback = normalize_level(profile.current_level) or normalize_level(profile.level_estimate)
        if fallback:
            hydrate_skill_levels(profile, fallback)
        db.flush()

    return generate_curriculum(
        db,
        user_language_id,
        duration_days,
        generated_from=generated_from,
    )


def median_level(skill_levels: dict[str, str]) -> str:
    """Mediana dos níveis por competência.

    Com número par de competências usa a **menor** das duas centrais. Superestimar
    o ponto de entrada custa mais do que subestimar: o aluno trava numa faixa que
    não sustenta e abandona; começar um degrau abaixo só custa alguns dias.
    """
    indexes = sorted(LEVEL_INDEX[level] for level in skill_levels.values())
    if not indexes:
        raise ValueError("skill_levels vazio")
    middle = (len(indexes) - 1) // 2
    return level_at(indexes[middle])


def target_level_for(entry_level: str, duration_days: int) -> str:
    """Meta do cronograma: B2 no plano longo, +2 subníveis no curto, teto B2."""
    entry_index = LEVEL_INDEX[entry_level]
    ceiling = LEVEL_INDEX[MAX_TARGET_LEVEL]

    if duration_days >= 180:
        target_index = ceiling
    else:
        target_index = min(entry_index + SHORT_PLAN_GAIN, ceiling)

    # Aluno já no teto ou acima: o cronograma vira consolidação no nível atual.
    return level_at(max(target_index, entry_index))


def level_stages(entry_level: str, target_level: str, total_weeks: int) -> list[LevelStage]:
    """Distribui as semanas entre os níveis do caminho entrada→meta.

    Proporcional à distância: entrada A2 e meta B2 percorre A2, B1 e B2 em
    partes iguais; entrada igual à meta concentra tudo num nível só.
    """
    start = LEVEL_INDEX[entry_level]
    end = LEVEL_INDEX[target_level]
    path = [level_at(index) for index in range(start, end + 1)]

    if len(path) == 1:
        return [LevelStage(path[0], total_weeks)]

    base, extra = divmod(total_weeks, len(path))
    stages: list[LevelStage] = []
    for position, level in enumerate(path):
        # As semanas que sobram vão para os níveis finais: consolidar a meta
        # exige mais tempo do que atravessar o nível de entrada já dominado.
        weeks = base + (1 if position >= len(path) - extra else 0)
        stages.append(LevelStage(level, weeks))
    return stages


def week_levels(entry_level: str, target_level: str, total_weeks: int) -> list[str]:
    """Nível CEFR de cada semana, na ordem (índice 0 = semana 1)."""
    levels: list[str] = []
    for stage in level_stages(entry_level, target_level, total_weeks):
        levels.extend([stage.level] * stage.weeks)
    # Arredondamentos podem deixar sobra ou falta de uma semana.
    while len(levels) < total_weeks:
        levels.append(target_level)
    return levels[:total_weeks]


# ---------------------------------------------------------------- pesos e dia


def weight_for(block_skill: str, skill_levels: dict[str, str], entry_level: str) -> float:
    """Multiplicador de tempo do bloco conforme a lacuna daquela competência."""
    assessed = BLOCK_ASSESSED_SKILL.get(block_skill)
    level = skill_levels.get(assessed) if assessed else None
    if not level:
        return WEIGHT_ON_LEVEL

    difference = LEVEL_INDEX[level] - LEVEL_INDEX[entry_level]
    if difference < 0:
        return WEIGHT_BEHIND
    if difference > 0:
        return WEIGHT_AHEAD
    return WEIGHT_ON_LEVEL


def block_minutes(
    block_skill: str,
    skill_levels: dict[str, str],
    entry_level: str,
    language_code: str,
) -> int:
    minutes = BASE_MINUTES[block_skill] * weight_for(block_skill, skill_levels, entry_level)
    if block_skill == BlockSkill.LISTENING and language_code in LISTENING_BONUS_LANGUAGES:
        minutes += LISTENING_BONUS_MINUTES
    return max(MIN_BLOCK_MINUTES, int(round(minutes)))


def _lagging(candidates: tuple[str, ...], skill_levels: dict[str, str], entry_level: str) -> str | None:
    """Qual dos dois blocos do par está atrasado, se apenas um estiver.

    Com os dois no mesmo patamar não há motivo para quebrar a alternância.
    """
    behind = [
        skill
        for skill in candidates
        if weight_for(skill, skill_levels, entry_level) == WEIGHT_BEHIND
    ]
    return behind[0] if len(behind) == 1 else None


def choose_from_pair(
    candidates: tuple[str, ...],
    day_number: int,
    skill_levels: dict[str, str],
    entry_level: str,
) -> str:
    """Escolhe o bloco de entrada (ou de saída) do dia.

    Padrão: alternância simples. Quando uma das duas competências está abaixo
    da mediana, ela ocupa 2 de cada 3 dias — é assim que "peso adaptativo" vira
    número de blocos, e não só minutos.
    """
    lagging = _lagging(candidates, skill_levels, entry_level)
    if lagging is None:
        # day_number é 1-based: dia 1 deve pegar o primeiro candidato do par
        # (conversation/listening), não o segundo (off-by-one clássico).
        return candidates[(day_number - 1) % len(candidates)]

    other = next(skill for skill in candidates if skill != lagging)
    return other if day_number % 3 == 2 else lagging


def has_pronunciation(language_code: str, weekday: int) -> bool:
    if language_code in DAILY_PRONUNCIATION_LANGUAGES:
        return True
    return weekday in PRONUNCIATION_WEEKDAYS


def day_block_skills(
    *,
    language_code: str,
    day_number: int,
    weekday: int,
    skill_levels: dict[str, str],
    entry_level: str,
) -> list[str]:
    """Sequência de blocos do dia, na ordem em que serão estudados."""
    if weekday == SUNDAY:
        return list(LIGHT_DAY_BLOCKS)

    blocks: list[str] = [BlockSkill.VOCABULARY, BlockSkill.GRAMMAR]
    if has_pronunciation(language_code, weekday):
        blocks.append(BlockSkill.PRONUNCIATION)
    blocks.append(choose_from_pair(INPUT_BLOCKS, day_number, skill_levels, entry_level))
    blocks.append(choose_from_pair(OUTPUT_BLOCKS, day_number, skill_levels, entry_level))
    # A revisão fecha o dia: recuperar o que foi visto agora é o que fixa.
    blocks.append(BlockSkill.REVIEW)
    return blocks


def total_weeks_for(duration_days: int) -> int:
    return math.ceil(duration_days / DAYS_PER_WEEK)


def is_checkpoint_week(week_number: int) -> bool:
    """Semanas pares levam mini-avaliação das quatro competências."""
    return week_number % 2 == 0


# ------------------------------------------------------------------- geração


def build_blocks_for_day(
    db: Session,
    *,
    day: CurriculumDay,
    language_code: str,
    cefr_level: str,
    theme: str,
    week_number: int,
    weekday: int,
    skill_levels: dict[str, str],
    entry_level: str,
) -> list[CurriculumBlock]:
    skills = day_block_skills(
        language_code=language_code,
        day_number=day.day_number,
        weekday=weekday,
        skill_levels=skill_levels,
        entry_level=entry_level,
    )
    blocks: list[CurriculumBlock] = []
    for position, skill in enumerate(skills, start=1):
        block = CurriculumBlock(
            day_id=day.id,
            skill=skill,
            position=position,
            estimated_minutes=block_minutes(skill, skill_levels, entry_level, language_code),
            cefr_level=cefr_level,
            topic=block_topic(language_code, skill, theme, week_number),
            status=BlockStatus.PENDING,
        )
        db.add(block)
        blocks.append(block)
    return blocks


def generate_curriculum(
    db: Session,
    user_language_id: str,
    duration_days: int,
    *,
    start_date: date | None = None,
    generated_from: str = GeneratedFrom.PLACEMENT,
) -> Curriculum:
    """Gera e ativa um cronograma para o perfil linguístico informado.

    Um currículo ativo anterior é arquivado como `regenerated` — nunca apagado:
    o histórico do que o aluno já concluiu não pode sumir porque ele pediu um
    plano novo.
    """
    if duration_days not in ALLOWED_DURATIONS:
        raise APIError(
            422,
            "invalid_duration",
            "A duração do cronograma deve ser de 90 ou 180 dias.",
        )

    profile = db.get(UserLanguage, user_language_id)
    if not profile:
        raise APIError(404, "language_not_configured", "Idioma não configurado para o usuário.")

    language = db.get(Language, profile.language_id)
    if not language:
        raise APIError(404, "language_not_found", "Idioma não encontrado.")

    skill_levels = assessed_skill_levels(profile)
    if not skill_levels:
        raise APIError(
            409,
            "placement_required",
            "Faça o teste de nivelamento antes de gerar o cronograma: "
            "sem níveis por competência não há como definir o ponto de entrada.",
        )

    entry_level = median_level(skill_levels)
    target_level = target_level_for(entry_level, duration_days)
    first_day = start_date or date.today()

    for previous in db.scalars(
        select(Curriculum).where(
            Curriculum.user_language_id == user_language_id,
            Curriculum.status.in_([CurriculumStatus.ACTIVE, CurriculumStatus.PAUSED]),
        )
    ):
        previous.status = CurriculumStatus.REGENERATED

    curriculum = Curriculum(
        user_language_id=user_language_id,
        duration_days=duration_days,
        start_date=first_day,
        entry_level=entry_level,
        target_level=target_level,
        status=CurriculumStatus.ACTIVE,
        generated_from=generated_from,
    )
    db.add(curriculum)
    db.flush()

    total_weeks = total_weeks_for(duration_days)
    levels = week_levels(entry_level, target_level, total_weeks)
    # Quantas semanas já foram gastas em cada nível, para não repetir o tema.
    seen_per_level: dict[str, int] = {}
    day_number = 0

    for index, cefr_level in enumerate(levels):
        week_number = index + 1
        theme_index = seen_per_level.get(cefr_level, 0)
        seen_per_level[cefr_level] = theme_index + 1
        theme = weekly_theme(language.code, cefr_level, theme_index)

        week = CurriculumWeek(
            curriculum_id=curriculum.id,
            week_number=week_number,
            theme=theme,
            cefr_focus=cefr_level,
            is_checkpoint=is_checkpoint_week(week_number),
        )
        db.add(week)
        db.flush()

        for _ in range(DAYS_PER_WEEK):
            day_number += 1
            if day_number > duration_days:
                break
            scheduled = first_day + timedelta(days=day_number - 1)
            day = CurriculumDay(
                week_id=week.id,
                day_number=day_number,
                scheduled_date=scheduled,
                status=DayStatus.PENDING,
            )
            db.add(day)
            db.flush()
            build_blocks_for_day(
                db,
                day=day,
                language_code=language.code,
                cefr_level=cefr_level,
                theme=theme,
                week_number=week_number,
                weekday=scheduled.weekday(),
                skill_levels=skill_levels,
                entry_level=entry_level,
            )

    db.flush()
    return curriculum
