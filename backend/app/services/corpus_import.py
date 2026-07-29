"""Importação de itens a partir de corpus de frases licenciado (Tatoeba).

Fonte alvo: Tatoeba (https://tatoeba.org), pares de frases contribuídos por
voluntários, licença CC-BY 2.0 FR. O download é feito pelo usuário; este módulo
lê o arquivo local. Nada é buscado na rede aqui.

Formato esperado (export "Sentence pairs" do Tatoeba, TSV):

    id_alvo <TAB> frase_no_idioma_alvo <TAB> id_pt <TAB> frase_em_portugues

DUAS LIMITAÇÕES QUE IMPORTAM:

1. A calibragem de nível é heurística. Deriva de comprimento da frase, número de
   palavras e tamanho médio das palavras — não de análise linguística nem de
   lista de frequência. Uma frase curta com vocabulário raro será subestimada.
   Por isso todo item entra como `pending_review` e não é servido ao aluno.

2. O Tatoeba é colaborativo e não revisado por especialistas. Há frases com erro,
   tradução imprecisa e registro inadequado. É matéria-prima boa e barata, não
   material didático pronto.

Para elevar a qualidade da calibragem, passe uma lista de frequência em
`frequency_ranks` (ex.: FrequencyWords/OpenSubtitles). Sem ela, o importador
avisa que está usando só o proxy de comprimento.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.levels import CEFRLevel, ItemType, ReviewStatus, Skill
from app.models import PlacementItem

TATOEBA_SOURCE = "tatoeba"
TATOEBA_LICENSE = "CC-BY-2.0-FR"
TATOEBA_ATTRIBUTION = (
    "Frases de tatoeba.org, licenciadas sob CC-BY 2.0 FR. "
    "Contribuições de voluntários do projeto Tatoeba."
)

#: Faixas de comprimento (em palavras) por nível. Proxy declaradamente grosseiro:
#: frase longa não é necessariamente difícil, e curta não é necessariamente fácil.
LENGTH_BANDS: list[tuple[int, str]] = [
    (4, CEFRLevel.PRE_A1),
    (7, CEFRLevel.A1),
    (11, CEFRLevel.A2),
    (17, CEFRLevel.B1),
    (999, CEFRLevel.B2),
]

#: Frases fora desta faixa são descartadas: muito curtas não ensinam, muito
#: longas viram parágrafo e não caem bem como item de vocabulário.
MIN_WORDS = 2
MAX_WORDS = 25
MAX_CHARS = 300


@dataclass
class ImportStats:
    read: int = 0
    imported: int = 0
    skipped_duplicate: int = 0
    skipped_too_short: int = 0
    skipped_too_long: int = 0
    skipped_malformed: int = 0
    by_level: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "read": self.read,
            "imported": self.imported,
            "skipped_duplicate": self.skipped_duplicate,
            "skipped_too_short": self.skipped_too_short,
            "skipped_too_long": self.skipped_too_long,
            "skipped_malformed": self.skipped_malformed,
            "by_level": dict(sorted(self.by_level.items())),
        }


@dataclass
class SentencePair:
    target_id: str
    target_text: str
    translation_id: str
    translation_text: str


def _word_count(text: str) -> int:
    return len([token for token in re.split(r"\s+", text.strip()) if token])


def _is_cjk(language_code: str) -> bool:
    """Japonês e mandarim não separam palavras por espaço."""
    return language_code in {"ja", "zh-CN", "zh-TW"}


def _unit_count(text: str, language_code: str) -> int:
    """Unidades de comprimento: palavras em línguas com espaço, caracteres em CJK."""
    if _is_cjk(language_code):
        return sum(
            1
            for char in text
            if not char.isspace() and unicodedata.category(char) not in {"Po", "Pf", "Pi"}
        )
    return _word_count(text)


def estimate_level(
    text: str,
    language_code: str,
    frequency_ranks: dict[str, int] | None = None,
) -> str:
    """Estima o nível CEFR de uma frase. HEURÍSTICA, não análise linguística.

    Sem `frequency_ranks`, usa apenas comprimento. Com a lista, uma frase que
    contenha palavra fora das mais frequentes é promovida uma faixa, porque
    vocabulário raro pesa mais que comprimento.
    """
    units = _unit_count(text, language_code)
    # Em CJK, o limiar de caracteres é maior que o de palavras.
    scale = 2 if _is_cjk(language_code) else 1

    level = CEFRLevel.B2
    for limit, band in LENGTH_BANDS:
        if units <= limit * scale:
            level = band
            break

    if frequency_ranks and not _is_cjk(language_code):
        words = [re.sub(r"[^\w']", "", w).casefold() for w in re.split(r"\s+", text)]
        words = [w for w in words if w]
        if words:
            worst = max(frequency_ranks.get(word, 100_000) for word in words)
            if worst > 20_000:
                level = _promote(level, 2)
            elif worst > 5_000:
                level = _promote(level, 1)
    return level


def _promote(level: str, steps: int) -> str:
    order = [
        CEFRLevel.PRE_A1,
        CEFRLevel.A1,
        CEFRLevel.A2,
        CEFRLevel.B1,
        CEFRLevel.B2,
    ]
    index = min(order.index(level) + steps, len(order) - 1)
    return order[index]


def read_pairs(path: Path, limit: int | None = None) -> tuple[list[SentencePair], int]:
    """Lê o TSV do Tatoeba. Retorna (pares válidos, linhas malformadas)."""
    pairs: list[SentencePair] = []
    malformed = 0
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t", quoting=csv.QUOTE_NONE)
        for row in reader:
            if len(row) < 4 or not row[1].strip() or not row[3].strip():
                malformed += 1
                continue
            pairs.append(
                SentencePair(
                    target_id=row[0].strip(),
                    target_text=row[1].strip(),
                    translation_id=row[2].strip(),
                    translation_text=row[3].strip(),
                )
            )
            if limit and len(pairs) >= limit:
                break
    return pairs, malformed


def build_item(
    pair: SentencePair,
    language_code: str,
    frequency_ranks: dict[str, int] | None = None,
) -> PlacementItem:
    """Monta um item de tradução (PT → idioma-alvo) a partir do par de frases."""
    level = estimate_level(pair.target_text, language_code, frequency_ranks)
    return PlacementItem(
        external_key=f"{TATOEBA_SOURCE}-{pair.target_id}",
        language_code=language_code,
        cefr_level=level,
        skill=Skill.VOCABULARY_GRAMMAR,
        item_type=ItemType.FILL_BLANK,
        prompt=f"Traduza: “{pair.translation_text}”",
        instructions="Escreva a frase no idioma que você está estudando.",
        correct_answer_json={"accepted": [pair.target_text]},
        explanation=None,
        difficulty=0.5,
        discrimination=1.0,
        is_active=True,
        version=1,
        source=TATOEBA_SOURCE,
        license=TATOEBA_LICENSE,
        attribution=TATOEBA_ATTRIBUTION,
        source_ref=f"sentence:{pair.target_id};translation:{pair.translation_id}",
        # Nunca aprovado na importação: a calibragem acima é um proxy.
        review_status=ReviewStatus.PENDING_REVIEW,
    )


def import_pairs(
    db: Session,
    path: Path,
    language_code: str,
    limit: int | None = None,
    frequency_ranks: dict[str, int] | None = None,
    dry_run: bool = False,
) -> ImportStats:
    """Importa pares do arquivo para `placement_items`.

    Idempotente por `external_key`: rodar duas vezes não duplica. Itens entram
    como `pending_review`, então nada chega ao aluno sem revisão.
    """
    pairs, malformed = read_pairs(path, limit)
    stats = ImportStats(read=len(pairs), skipped_malformed=malformed)

    existing = set(
        db.scalars(
            select(PlacementItem.external_key).where(
                PlacementItem.language_code == language_code,
                PlacementItem.source == TATOEBA_SOURCE,
            )
        )
    )

    for pair in pairs:
        units = _unit_count(pair.target_text, language_code)
        scale = 2 if _is_cjk(language_code) else 1
        if units < MIN_WORDS * scale:
            stats.skipped_too_short += 1
            continue
        if units > MAX_WORDS * scale or len(pair.target_text) > MAX_CHARS:
            stats.skipped_too_long += 1
            continue

        key = f"{TATOEBA_SOURCE}-{pair.target_id}"
        if key in existing:
            stats.skipped_duplicate += 1
            continue

        item = build_item(pair, language_code, frequency_ranks)
        existing.add(key)
        stats.imported += 1
        stats.by_level[item.cefr_level] = stats.by_level.get(item.cefr_level, 0) + 1
        if not dry_run:
            db.add(item)

    if not dry_run:
        db.commit()
    return stats


def load_frequency_ranks(path: Path, limit: int = 50_000) -> dict[str, int]:
    """Lê lista de frequência no formato `palavra contagem` (FrequencyWords).

    O valor guardado é a posição (1 = mais frequente), não a contagem.
    """
    ranks: dict[str, int] = {}
    with path.open(encoding="utf-8") as handle:
        for position, line in enumerate(handle, start=1):
            word = line.split(maxsplit=1)[0].strip().casefold() if line.strip() else ""
            if word and word not in ranks:
                ranks[word] = position
            if len(ranks) >= limit:
                break
    return ranks
