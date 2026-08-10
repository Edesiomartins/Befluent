"""Fio condutor entre os blocos: o que um bloco entrega ao próximo.

Problema que este módulo resolve: o cronograma já tinha sequência de **fases**
(ativar → estruturar → compreender → produzir → consolidar), mas não tinha
sequência de **conteúdo**. O bloco de vocabulário introduzia seis palavras e o
bloco de conversação, logo em seguida, montava um diálogo sem nenhuma delas.
Cinco lições soltas debaixo do mesmo rótulo de tema não formam um dia de estudo.

Aqui cada lição já aberta é lida de volta e o que ela introduziu (léxico,
padrões, expressões) vira o material obrigatório do bloco seguinte. É isso que
faz a palavra do bloco 1 reaparecer na frase do bloco 3 e na fila de revisão do
bloco 5 — e, via SRS, nos dias seguintes.

LIMITAÇÃO DECLARADA: a extração é sintática. Ela lê as chaves do contrato de
saída por modo (`app/prompts/library.py::MODE_OUTPUT_CONTRACT`). Se o provedor
devolver um payload fora do contrato, o fio daquele bloco sai vazio — e o bloco
seguinte declara "sem material anterior" em vez de fingir continuidade.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.curriculum import BlockStatus, block_skill_label
from app.models import (
    CurriculumBlock,
    CurriculumDay,
    Lesson,
    ReviewItem,
    VocabularyItem,
)

#: Tetos do fio. Mais do que isso deixa de ser reforço e vira lista: um bloco de
#: 12 minutos não reusa 30 palavras.
MAX_THREAD_TERMS = 8
MAX_THREAD_PATTERNS = 4


@dataclass(frozen=True)
class ThreadTerm:
    """Item de léxico que atravessa os blocos.

    `translation` vazia é permitida (uma expressão-alvo de conversação nem sempre
    volta traduzida), mas só itens com tradução viram carta de revisão — um card
    sem resposta não é revisão, é adivinhação.
    """

    term: str
    translation: str = ""
    example: str = ""
    example_translation: str = ""

    @property
    def reviewable(self) -> bool:
        return bool(self.term and self.translation)

    def to_payload(self) -> dict:
        return {
            "term": self.term,
            "translation": self.translation,
            "example": self.example,
            "example_translation": self.example_translation,
        }


@dataclass(frozen=True)
class LessonThread:
    """Material acumulado que o próximo bloco precisa reaproveitar."""

    terms: tuple[ThreadTerm, ...] = ()
    patterns: tuple[str, ...] = ()
    #: Rótulos dos blocos de origem, na ordem em que foram estudados.
    sources: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.terms or self.patterns)

    @property
    def term_labels(self) -> list[str]:
        return [item.term for item in self.terms]

    def to_payload(self) -> dict:
        return {
            "terms": [item.to_payload() for item in self.terms],
            "patterns": list(self.patterns),
            "sources": list(self.sources),
        }


EMPTY_THREAD = LessonThread()


# --------------------------------------------------------------------- extração


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _terms_from_items(payload: dict) -> list[ThreadTerm]:
    """Léxico dos modos que devolvem `items` no contrato (vocabulário)."""
    terms: list[ThreadTerm] = []
    for item in payload.get("items") or []:
        if not isinstance(item, dict):
            continue
        term = _text(item.get("term"))
        if not term:
            continue
        terms.append(
            ThreadTerm(
                term=term,
                translation=_text(item.get("translation")),
                example=_text(item.get("example")),
                example_translation=_text(item.get("example_translation")),
            )
        )
    return terms


def _terms_from_glossary(payload: dict) -> list[ThreadTerm]:
    terms: list[ThreadTerm] = []
    for entry in payload.get("glossary") or []:
        if not isinstance(entry, dict):
            continue
        term = _text(entry.get("term"))
        if term:
            terms.append(ThreadTerm(term=term, translation=_text(entry.get("translation"))))
    return terms


def _terms_from_expressions(payload: dict, key: str) -> list[ThreadTerm]:
    """Expressões-alvo (conversação) e expressões úteis (escrita).

    Vêm sem tradução no contrato: entram no fio para serem reusadas, mas não
    viram carta de revisão.
    """
    return [
        ThreadTerm(term=_text(value))
        for value in payload.get(key) or []
        if _text(value)
    ]


def extract(mode: str, payload: dict) -> LessonThread:
    """Material que uma lição já entregue passa adiante."""
    if not isinstance(payload, dict):
        return EMPTY_THREAD

    terms: list[ThreadTerm] = []
    patterns: list[str] = []

    if mode == "vocabulary":
        terms = _terms_from_items(payload)
    elif mode == "grammar":
        patterns = [_text(value) for value in payload.get("patterns") or [] if _text(value)]
    elif mode == "reading":
        terms = _terms_from_glossary(payload)
    elif mode == "conversation":
        terms = _terms_from_expressions(payload, "target_expressions")
    elif mode == "writing":
        terms = _terms_from_expressions(payload, "useful_expressions")

    return LessonThread(terms=tuple(terms), patterns=tuple(patterns[:MAX_THREAD_PATTERNS]))


def merge(threads: list[LessonThread]) -> LessonThread:
    """Junta fios preservando a ordem de entrada e removendo repetição.

    A primeira ocorrência de um termo ganha: ela vem do bloco que o introduziu,
    e é a que traz tradução e exemplo. Quem repete depois costuma trazer só o
    rótulo.
    """
    seen: dict[str, ThreadTerm] = {}
    patterns: list[str] = []
    sources: list[str] = []

    for thread in threads:
        for term in thread.terms:
            key = term.term.casefold()
            current = seen.get(key)
            if current is None:
                seen[key] = term
            elif not current.translation and term.translation:
                seen[key] = term
        for pattern in thread.patterns:
            if pattern not in patterns:
                patterns.append(pattern)
        for source in thread.sources:
            if source not in sources:
                sources.append(source)

    return LessonThread(
        terms=tuple(list(seen.values())[:MAX_THREAD_TERMS]),
        patterns=tuple(patterns[:MAX_THREAD_PATTERNS]),
        sources=tuple(sources),
    )


# ----------------------------------------------------------------- fio do dia


def _lesson_payload(db: Session, block: CurriculumBlock) -> dict:
    if not block.lesson_ref:
        return {}
    lesson = db.get(Lesson, block.lesson_ref)
    return dict(lesson.content_json or {}) if lesson else {}


def _thread_of_block(db: Session, block: CurriculumBlock) -> LessonThread:
    payload = _lesson_payload(db, block)
    if not payload:
        return EMPTY_THREAD
    mode = str(payload.get("mode") or block.skill)
    thread = extract(mode, payload)
    if not thread:
        return EMPTY_THREAD
    return LessonThread(
        terms=thread.terms,
        patterns=thread.patterns,
        sources=(block_skill_label(block.skill),),
    )


def day_thread(db: Session, day: CurriculumDay, *, before_position: int) -> LessonThread:
    """O que os blocos anteriores **deste dia** já introduziram.

    Só blocos já abertos entram: um bloco sem `lesson_ref` ainda não mostrou
    nada ao aluno, e prometer reuso de conteúdo inexistente seria pior do que
    não prometer nada.
    """
    blocks = db.scalars(
        select(CurriculumBlock)
        .where(
            CurriculumBlock.day_id == day.id,
            CurriculumBlock.position < before_position,
        )
        .order_by(CurriculumBlock.position)
    )
    return merge([_thread_of_block(db, block) for block in blocks])


def week_thread(db: Session, day: CurriculumDay, *, limit_days: int = 2) -> LessonThread:
    """Léxico dos dias anteriores da mesma semana — o reforço em espiral.

    Sem isso a semana também seria uma pilha de dias independentes: o tema se
    repetiria no rótulo e o conteúdo recomeçaria do zero toda manhã.
    """
    previous = list(
        db.scalars(
            select(CurriculumDay)
            .where(
                CurriculumDay.week_id == day.week_id,
                CurriculumDay.day_number < day.day_number,
            )
            .order_by(CurriculumDay.day_number.desc())
            .limit(limit_days)
        )
    )
    threads: list[LessonThread] = []
    for earlier in reversed(previous):
        blocks = db.scalars(
            select(CurriculumBlock)
            .where(
                CurriculumBlock.day_id == earlier.id,
                CurriculumBlock.status == BlockStatus.COMPLETED,
            )
            .order_by(CurriculumBlock.position)
        )
        threads.extend(_thread_of_block(db, block) for block in blocks)
    return merge(threads)


def curriculum_exposed_terms(db: Session, day: CurriculumDay) -> LessonThread:
    """Léxico já **exposto ao aluno** em jornadas anteriores deste currículo.

    Definição adotada (preferência produto): termo que apareceu em `items` (ou
    outro campo extraível) de uma lição com `lesson_ref` em um dia anterior —
    ou seja, o aluno já abriu aquele conteúdo. Não usa a fila SRS para decidir
    novidade curricular.

    Usado para classificar `items` (primeira exposição) vs `revisited_items`
    (já visto). O spiral da semana (`week_thread`) continua sendo a fonte
    preferida para *quais* revisitados mostrar; este histórico impede que um
    termo já visto volte a ser marcado como novo.
    """
    from app.models import CurriculumWeek

    week = db.get(CurriculumWeek, day.week_id)
    if week is None:
        return EMPTY_THREAD

    previous_days = list(
        db.scalars(
            select(CurriculumDay)
            .join(CurriculumWeek, CurriculumWeek.id == CurriculumDay.week_id)
            .where(
                CurriculumWeek.curriculum_id == week.curriculum_id,
                CurriculumDay.day_number < day.day_number,
            )
            .order_by(CurriculumDay.day_number)
        )
    )
    threads: list[LessonThread] = []
    for earlier in previous_days:
        blocks = db.scalars(
            select(CurriculumBlock)
            .where(
                CurriculumBlock.day_id == earlier.id,
                CurriculumBlock.lesson_ref.is_not(None),
            )
            .order_by(CurriculumBlock.position)
        )
        for block in blocks:
            # Preferir só o léxico de vocabulário (`items`) para exposição A.
            payload = _lesson_payload(db, block)
            mode = str(payload.get("mode") or block.skill)
            if mode == "vocabulary" or block.skill == "vocabulary":
                thread = extract("vocabulary", payload)
            else:
                continue
            if thread:
                threads.append(
                    LessonThread(
                        terms=thread.terms,
                        patterns=(),
                        sources=(block_skill_label(block.skill),),
                    )
                )
    # Sem teto MAX_THREAD_TERMS aqui: histórico precisa ser completo para a regra
    # "nunca de novo como new". Merge local sem truncar.
    seen: dict[str, ThreadTerm] = {}
    sources: list[str] = []
    for thread in threads:
        for term in thread.terms:
            key = term.term.casefold()
            current = seen.get(key)
            if current is None:
                seen[key] = term
            elif not current.translation and term.translation:
                seen[key] = term
        for source in thread.sources:
            if source not in sources:
                sources.append(source)
    return LessonThread(terms=tuple(seen.values()), patterns=(), sources=tuple(sources))


# --------------------------------------------------------------- fio → memória


def enroll(db: Session, *, user_language_id: str, thread: LessonThread) -> int:
    """Coloca o léxico do dia na fila real de revisão espaçada.

    Aqui fecha o ciclo do cronograma. Antes disso, `ReviewItem` só nascia quando
    o aluno salvava uma palavra à mão em `/vocabulary` — então o bloco de
    consolidação abria vazio quase todo dia, e "consolidar" era um rótulo sem
    lastro. O que o aluno estudou hoje passa a voltar amanhã.

    Idempotente por termo: reabrir ou refazer um bloco não duplica a carta.
    Devolve quantos itens novos entraram na fila.
    """
    reviewable = [term for term in thread.terms if term.reviewable]
    if not reviewable:
        return 0

    existing = {
        row.casefold()
        for row in db.scalars(
            select(VocabularyItem.term).where(
                VocabularyItem.user_language_id == user_language_id,
                VocabularyItem.term.in_([term.term for term in reviewable]),
            )
        )
    }

    created = 0
    for term in reviewable:
        if term.term.casefold() in existing:
            continue
        item = VocabularyItem(
            user_language_id=user_language_id,
            term=term.term[:200],
            translation_pt=term.translation[:300],
            notes=term.example or None,
        )
        db.add(item)
        db.flush()
        db.add(
            ReviewItem(
                user_language_id=user_language_id,
                item_type="vocabulary",
                reference_id=item.id,
                payload_json={
                    "term": item.term,
                    "translation_pt": item.translation_pt,
                    "example": term.example,
                    "source": "curriculum",
                },
            )
        )
        existing.add(term.term.casefold())
        created += 1

    if created:
        db.flush()
    return created
