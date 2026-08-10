"""Auditoria programática do currículo 90 jornadas B2 — somente diagnóstico.

Não toca banco de produção. Gera currículo em SQLite em memória e simula o
conteúdo mock/lesson_bank que o aluno veria com IA em mock (estado atual).

Uso (a partir de backend/):
  python scripts/audit_curriculum_b2_90.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.curriculum import BlockSkill, block_phase  # noqa: E402
from app.core.levels import CEFRLevel, LevelSource  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import (  # noqa: E402
    Base,
    CurriculumBlock,
    CurriculumDay,
    CurriculumWeek,
    Language,
    LearningObjective,
    User,
    UserLanguage,
    UserPreference,
)
from app.services import lesson_bank  # noqa: E402
from app.services.curriculum_generator import (  # noqa: E402
    generate_curriculum,
    level_stages,
    week_levels,
)
from app.services.objective_seed import seed_teaching_objectives  # noqa: E402
from app.services.seed import seed_languages  # noqa: E402

START = date(2026, 8, 3)
REPORT_PATH = ROOT.parent / "docs" / "audits" / "curriculum-b2-90-jornadas-auditoria.md"


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()
    seed_languages(db)
    seed_teaching_objectives(db)
    user = User(
        email="audit-b2@befluent.local",
        name="Audit B2",
        password_hash=hash_password("audit-only"),
    )
    db.add(user)
    db.flush()
    db.add(UserPreference(user_id=user.id))
    language = db.scalar(select(Language).where(Language.code == "en"))
    # Placement B2 em todas as competências (caso do usuário).
    profile = UserLanguage(
        user_id=user.id,
        language_id=language.id,
        is_active=True,
        diagnostic_completed=True,
        current_level=CEFRLevel.B2,
        level_source=LevelSource.PLACEMENT_TEST,
        vocabulary_grammar_level=CEFRLevel.B2,
        reading_level=CEFRLevel.B2,
        listening_level=CEFRLevel.B2,
        writing_level=CEFRLevel.B2,
        speaking_level=CEFRLevel.B2,
    )
    db.add(profile)
    db.commit()
    return db, profile


def _vocab_selection_for_day(
    day_number: int,
    level: str = CEFRLevel.B2,
    *,
    week_theme: str | None = None,
    recycled_items: list[dict] | None = None,
    exposed_items: list[dict] | None = None,
) -> dict:
    """Espelha `ai._vocabulary` via `select_daily_vocabulary` (histórico curricular)."""
    from app.services.vocabulary_selection import select_daily_vocabulary

    band = lesson_bank.band_for(level)
    return select_daily_vocabulary(
        "en",
        band,
        day_number=day_number,
        week_theme=week_theme,
        recycled_items=recycled_items,
        exposed_items=exposed_items,
    )


def _vocab_for_day(
    day_number: int,
    level: str = CEFRLevel.B2,
    *,
    week_theme: str | None = None,
    recycled_items: list[dict] | None = None,
    exposed_items: list[dict] | None = None,
) -> list[dict]:
    return list(
        _vocab_selection_for_day(
            day_number,
            level,
            week_theme=week_theme,
            recycled_items=recycled_items,
            exposed_items=exposed_items,
        )["new_items"]
    )


def _fingerprint(payload: dict) -> str:
    """Assinatura estável do conteúdo lexical (ignora metadados de envelope)."""
    items = payload.get("items") or []
    terms = sorted(
        str(i.get("term", "")).casefold()
        for i in items
        if isinstance(i, dict) and i.get("term")
    )
    return "|".join(terms)


def main() -> int:
    db, profile = _session()
    curriculum = generate_curriculum(
        db, profile.id, 90, start_date=START, generated_from="placement"
    )
    db.commit()

    days = list(
        db.scalars(
            select(CurriculumDay)
            .join(CurriculumWeek)
            .where(CurriculumWeek.curriculum_id == curriculum.id)
            .order_by(CurriculumDay.day_number)
        )
    )
    weeks = {
        w.id: w
        for w in db.scalars(
            select(CurriculumWeek).where(CurriculumWeek.curriculum_id == curriculum.id)
        )
    }
    blocks_by_day: dict[str, list[CurriculumBlock]] = defaultdict(list)
    for block in db.scalars(select(CurriculumBlock).order_by(CurriculumBlock.position)):
        blocks_by_day[block.day_id].append(block)

    # --- Estrutura por jornada ---
    journey_rows = []
    all_terms_flat: list[str] = []
    term_day_map: dict[str, list[int]] = defaultdict(list)
    fingerprints: list[str] = []
    fingerprint_days: dict[str, list[int]] = defaultdict(list)
    consecutive_overlap: list[tuple[int, int, float, set[str]]] = []
    week_term_sets: dict[int, set[str]] = defaultdict(set)
    objective_linked = 0
    total_blocks = 0
    phase_ok_days = 0
    theme_by_day: dict[int, str] = {}

    prev_terms: set[str] | None = None
    prev_day_n = None
    week_recycled: dict[int, list[dict]] = defaultdict(list)
    curriculum_exposed: list[dict] = []
    first_exposures = 0
    revisits_total = 0
    new_as_exposed_violations = 0
    term_exposure_days: dict[str, list[int]] = defaultdict(list)
    week1_objective_blocks = 0
    week1_blocks = 0
    week1_can_dos: list[str] = []

    for day in days:
        week = weeks[day.week_id]
        blocks = sorted(blocks_by_day[day.id], key=lambda b: b.position)
        total_blocks += len(blocks)
        for b in blocks:
            if b.objective_id:
                objective_linked += 1
            if week.week_number == 1:
                week1_blocks += 1
                if b.objective_id:
                    week1_objective_blocks += 1

        phases = [block_phase(b.skill) for b in blocks]
        # Activate→…→Consolidate: ordem não-decrescente nas fases conhecidas
        order = ["activate", "structure", "input", "output", "consolidate"]
        idx = [order.index(p) for p in phases if p in order]
        if idx == sorted(idx) and len(idx) >= 3:
            phase_ok_days += 1

        selection = _vocab_selection_for_day(
            day.day_number,
            week.cefr_focus,
            week_theme=week.theme,
            recycled_items=week_recycled[week.week_number],
            exposed_items=curriculum_exposed,
        )
        vocab = list(selection["new_items"])
        revisited = list(selection["revisited_items"])
        first_exposures += len(vocab)
        revisits_total += len(revisited)
        new_as_exposed_violations += len(selection.get("new_as_exposed_violations") or [])
        week_recycled[week.week_number].extend(vocab)
        curriculum_exposed.extend(vocab)
        terms = [v["term"] for v in vocab]
        if week.week_number == 1:
            obj_ids = {b.objective_id for b in blocks if b.objective_id}
            for oid in obj_ids:
                obj = db.get(LearningObjective, oid)
                if obj and obj.code not in week1_can_dos:
                    week1_can_dos.append(obj.code)
        term_set = set(terms)
        fp = "|".join(t.casefold() for t in terms)
        fingerprints.append(fp)
        fingerprint_days[fp].append(day.day_number)
        theme_by_day[day.day_number] = week.theme

        for t in terms:
            key = t.casefold()
            all_terms_flat.append(key)
            term_day_map[key].append(day.day_number)
            term_exposure_days[key].append(day.day_number)
        for item in revisited:
            key = str(item.get("term") or "").casefold()
            if key:
                term_exposure_days[key].append(day.day_number)
        week_term_sets[week.week_number].update(t.casefold() for t in terms)

        if prev_terms is not None and prev_day_n is not None:
            overlap = prev_terms & term_set
            union = prev_terms | term_set
            ratio = len(overlap) / len(union) if union else 0.0
            consecutive_overlap.append((prev_day_n, day.day_number, ratio, overlap))

        prev_terms = set(terms)
        prev_day_n = day.day_number

        journey_rows.append(
            {
                "day": day.day_number,
                "week": week.week_number,
                "theme": week.theme,
                "cefr": week.cefr_focus,
                "checkpoint": week.is_checkpoint,
                "skills": [b.skill for b in blocks],
                "topics": [b.topic for b in blocks],
                "phases": phases,
                "objective_ids": [b.objective_id for b in blocks],
                "vocab_terms": terms,
                "vocab_count": len(terms),
                "can_do": None,  # não existe no CurriculumDay
            }
        )

    unique_terms = set(all_terms_flat)
    term_counts = Counter(all_terms_flat)
    max_term, max_count = term_counts.most_common(1)[0]
    identical_fp = {fp: ds for fp, ds in fingerprint_days.items() if len(ds) > 1}

    # Dia 1 × Dia 2
    d1 = journey_rows[0]
    d2 = journey_rows[1]
    t1 = set(d1["vocab_terms"])
    t2 = set(d2["vocab_terms"])
    shared = t1 & t2
    new_d2 = t2 - t1
    only_d1 = t1 - t2

    bank_upper = [i["term"] for i in lesson_bank.vocabulary("en", "upper")]
    stages = level_stages(CEFRLevel.B2, curriculum.target_level, 13)
    wlevels = week_levels(CEFRLevel.B2, curriculum.target_level, 13)

    # Diversidade de atividade: mesmo termo em skill diferente vs mesmo card
    # No mock, vocabulary devolve a lista inteira todo dia — "mesmo exercício".
    same_exercise_days = len(identical_fp.get("|".join(t.casefold() for t in sorted(bank_upper)), []))
    # Com rotação, fingerprints diferem mas o MULTISET de termos é idêntico.
    multiset_same = sum(
        1
        for row in journey_rows
        if Counter(t.casefold() for t in row["vocab_terms"])
        == Counter(t.casefold() for t in bank_upper)
    )

    # Temas únicos vs dias
    themes = [r["theme"] for r in journey_rows]
    unique_themes = len(set(themes))
    days_per_theme = Counter(themes)

    # Classificação
    avg_consec = (
        sum(r for _, _, r, _ in consecutive_overlap) / len(consecutive_overlap)
        if consecutive_overlap
        else 0
    )
    te_ratio = objective_linked / total_blocks if total_blocks else 0

    n_unique = len(unique_terms)
    # Reconsultar objetivos após geração (temas B2 criam LearningObjective sob demanda).
    objectives = list(db.scalars(select(LearningObjective)))
    if te_ratio < 0.05 and avg_consec >= 0.8:
        classification = "D"
    elif avg_consec >= 0.5:
        classification = "B"
    elif unique_themes < 5 or n_unique < 20:
        classification = "C"
    else:
        classification = "A"

    labels = {
        "A": "Progressão adequada",
        "B": "Progressão adequada, mas repetição excessiva",
        "C": "Progressão insuficiente entre jornadas",
        "D": "Currículo ainda baseado principalmente em templates/tema, sem objetivos pedagógicos suficientemente granulares",
    }

    # --- Report ---
    lines: list[str] = []
    lines.append("# Auditoria — Currículo 90 jornadas · entrada B2 (EN)")
    lines.append("")
    lines.append("**Modo:** diagnóstico somente (SQLite em memória). Sem alteração em produção.")
    lines.append(f"**Gerado em:** script `backend/scripts/audit_curriculum_b2_90.py`")
    lines.append(f"**Premissa:** placement B2 em todas as competências; duração 90; idioma `en`.")
    lines.append(f"**Conteúdo lexical simulado:** `MockAIProvider` + `lesson_bank` (estado atual sem OpenRouter ativo).")
    lines.append("")
    lines.append(f"## Classificação: **{classification}** — {labels[classification]}")
    lines.append("")
    lines.append("## 0. Resumo executivo")
    lines.append("")
    lines.append(f"- Jornadas: **{len(days)}** | Semanas: **{len(weeks)}** | Blocos: **{total_blocks}**")
    lines.append(f"- Entry → target: **{curriculum.entry_level} → {curriculum.target_level}**")
    lines.append(f"- Estágios de nível: {[(s.level, s.weeks) for s in stages]}")
    lines.append(f"- Temas únicos nas 90 jornadas: **{unique_themes}** (tema semanal compartilhado por ~7 dias)")
    lines.append(f"- Itens léxicos no banco UPPER (B2): **{len(bank_upper)}** — com tags de tema")
    lines.append(f"- Itens únicos observados na simulação mock: **{len(unique_terms)}**")
    lines.append(f"- Ocorrências totais de termos (soma dias×itens): **{len(all_terms_flat)}**")
    lines.append(f"- Sobreposição média Dia N ∩ Dia N+1 (Jaccard): **{avg_consec:.0%}**")
    lines.append(f"- Primeiras exposições (soma `items` novos): **{first_exposures}**")
    lines.append(f"- Revisitações spirais (soma `revisited_items`): **{revisits_total}**")
    avg_exp = (
        sum(len(v) for v in term_exposure_days.values()) / len(term_exposure_days)
        if term_exposure_days
        else 0
    )
    lines.append(f"- Média de exposições por termo (new+revisited): **{avg_exp:.2f}**")
    lines.append(
        f"- Violações new←já-exposto: **{new_as_exposed_violations}**"
    )
    lines.append(
        f"- Semana 1 blocos com `objective_id`: **{week1_objective_blocks}/{week1_blocks}**"
    )
    lines.append(f"- Semana 1 Can-Dos: **{week1_can_dos}**")
    lines.append(f"- Blocos com `objective_id` (Teaching Engine): **{objective_linked}/{total_blocks}** ({te_ratio:.1%})")
    obj_codes = [o.code for o in objectives][:12]
    lines.append(
        f"- Objetivos LearningObjective no banco: **{len(objectives)}** "
        f"({obj_codes}{'…' if len(objectives) > 12 else ''})"
    )
    lines.append(f"- Dias com sequência de fases Activate→…→Consolidate coerente: **{phase_ok_days}/{len(days)}**")
    lines.append("")
    lines.append("### Separação A / B / C (não misturar)")
    lines.append("")
    lines.append("| Tipo | O que é neste currículo |")
    lines.append("|---|---|")
    lines.append(
        "| **A. Conteúdo novo** | `select_daily_vocabulary` devolve ~5 itens novos/dia "
        "do pool temático da semana (`items` + `content_roles.items=new`). |"
    )
    lines.append(
        "| **B. Carryover / spiral** | **Dentro do dia:** `lesson_thread`. "
        "**Entre dias:** `revisited_items` (spiral). |"
    )
    lines.append(
        "| **C. SRS temporal** | Bloco `review` consome `ReviewItem` com "
        "`next_review_at <= agora`. Independente do tema semanal. |"
    )
    lines.append("")

    lines.append("## 1. Mapa das 90 jornadas (resumo por semana)")
    lines.append("")
    by_week: dict[int, list] = defaultdict(list)
    for row in journey_rows:
        by_week[row["week"]].append(row)

    for wn in sorted(by_week):
        rows = by_week[wn]
        w = weeks[next(d.week_id for d in days if d.day_number == rows[0]["day"])]
        lines.append(
            f"### Semana {wn} · {w.theme} · CEFR {w.cefr_focus}"
            + (" · **CHECKPOINT**" if w.is_checkpoint else "")
        )
        lines.append("")
        lines.append("| Dia | Blocos (skills) | Vocab simulado (mock) |")
        lines.append("|---|---|---|")
        for r in rows:
            skills = " → ".join(r["skills"])
            vocab = ", ".join(r["vocab_terms"][:4])
            if len(r["vocab_terms"]) > 4:
                vocab += ", …"
            lines.append(f"| {r['day']} | {skills} | {vocab} |")
        lines.append("")

    lines.append("## 2. Progressão pedagógica")
    lines.append("")
    lines.append("### Cada dia tem objetivo específico?")
    lines.append("")
    lines.append(
        "**Não.** `CurriculumDay` não possui can-do/objetivo próprio. "
        "Só herda o **tema semanal** (`CurriculumWeek.theme`) e cada bloco tem "
        "`topic` = ângulo do skill + tema (ex.: “Argumentar e refutar — vocabulário essencial”)."
    )
    lines.append("")
    lines.append("### Vários dias usam o mesmo tema semanal?")
    lines.append("")
    lines.append(
        f"**Sim.** Em média **{90/unique_themes:.1f}** jornadas por tema. "
        f"Distribuição: {dict(days_per_theme.most_common())}."
    )
    lines.append("")
    lines.append("### Dia N ensina algo novo vs Dia N-1?")
    lines.append("")
    lines.append(
        f"No léxico mock B2: overlap médio consecutivo **{avg_consec:.0%}**. "
        f"Com banco de {len(bank_upper)} itens e `_rotate` por `day_number`, "
        "o Dia N quase sempre contém **o mesmo conjunto** que o Dia N-1, "
        "apenas reordenado. Isso **não** é spiral pedagógico deliberado com itens novos — "
        "é limitação do `lesson_bank` UPPER."
    )
    lines.append("")
    high_overlap = [x for x in consecutive_overlap if x[2] >= 0.99]
    lines.append(
        f"- Pares consecutivos com overlap ≥ 99%: **{len(high_overlap)}** / {len(consecutive_overlap)}"
    )
    lines.append("")
    lines.append("### Progressão Activate → Structure → Comprehension → Production → Consolidation?")
    lines.append("")
    lines.append(
        f"**Sim na estrutura de blocos** ({phase_ok_days}/{len(days)} dias com fases em ordem). "
        "Gerado por `day_block_skills`: vocabulary → grammar → (pronunciation?) → "
        "listening|reading → conversation|writing → review. Domingos: reading → review."
    )
    lines.append("")
    lines.append("### Semanas: começo, desenvolvimento, checkpoint?")
    lines.append("")
    lines.append(
        "- Checkpoint: semanas **pares** (`is_checkpoint_week`). "
        "Não há conteúdo diferente nos dias 1–6 vs 7 além do flag; "
        "o checkpoint é mini-placement, não uma jornada especial de síntese."
    )
    lines.append(
        f"- Temas B2 ciclam: {themes_for_preview()}."
    )
    lines.append(
        "- Com entrada=B2 e target=B2, **todas as 13 semanas ficam em B2** "
        f"(week_levels amostra: {wlevels[:5]}…)."
    )
    lines.append("")
    lines.append("### Complexidade progressiva dos objetivos?")
    lines.append("")
    lines.append(
        "**Parcial e só no eixo temático.** Temas B2 mudam "
        "(Argumentar → Negociação → Ciência…). "
        "O **léxico e exercícios mock** não sobem de complexidade: mesma banda UPPER, "
        "mesmos 6 itens, mesmos templates de grammar/reading/listening por banda."
    )
    lines.append("")

    lines.append("## 3. Auditoria de repetição")
    lines.append("")
    lines.append("| Métrica | Valor |")
    lines.append("|---|---|")
    lines.append(f"| Itens (ocorrências) | {len(all_terms_flat)} |")
    lines.append(f"| Itens únicos | {len(unique_terms)} |")
    lines.append(f"| Itens repetidos (≥2 dias) | {sum(1 for t,c in term_counts.items() if c>=2)} |")
    lines.append(f"| Máx. aparições de um item | **{max_count}×** (`{max_term}`) |")
    lines.append(f"| Fingerprints lexicais idênticos (mesma ordem) | {sum(len(v) for v in identical_fp.values())} dias em grupos |")
    lines.append(f"| Dias cujo **conjunto** = banco UPPER inteiro | **{multiset_same}/90** |")
    lines.append(f"| `lesson_ref` / content unit IDs no currículo gerado | **0** (lição só nasce no `/block/start`) |")
    lines.append(f"| `objective_id` preenchido | **{objective_linked}** |")
    lines.append("")
    lines.append("### Top itens por frequência (aparência em jornadas)")
    lines.append("")
    lines.append("| Termo | Dias em que aparece (simulação vocab) |")
    lines.append("|---|---|")
    for term, count in term_counts.most_common(12):
        lines.append(f"| {term} | {count} |")
    lines.append("")
    lines.append("### Repetição na mesma semana")
    lines.append("")
    for wn in sorted(week_term_sets)[:4]:
        lines.append(
            f"- Semana {wn}: {len(week_term_sets[wn])} termos únicos "
            f"(banco UPPER tem {len(bank_upper)}) → "
            + ("**cobertura = 100% do banco toda semana**" if len(week_term_sets[wn]) >= len(bank_upper) else "parcial")
        )
    lines.append("- … (padrão se repete nas demais semanas B2)")
    lines.append("")

    lines.append("## 4. Dia 1 × Dia 2 (investigação específica)")
    lines.append("")
    lines.append("| | Dia 1 | Dia 2 |")
    lines.append("|---|---|---|")
    lines.append(f"| Tema/semana | {d1['theme']} (sem. {d1['week']}) | {d2['theme']} (sem. {d2['week']}) |")
    lines.append(f"| Can-do / LearningObjective | *nenhum* | *nenhum* |")
    lines.append(f"| Topic vocab | `{d1['topics'][0]}` | `{d2['topics'][0]}` |")
    lines.append(f"| Skills | {' → '.join(d1['skills'])} | {' → '.join(d2['skills'])} |")
    lines.append(f"| Vocabulário mock | {', '.join(d1['vocab_terms'])} | {', '.join(d2['vocab_terms'])} |")
    lines.append("")
    lines.append(f"- **Itens só no Dia 1:** {sorted(only_d1) or '∅'}")
    lines.append(f"- **Itens novos no Dia 2:** {sorted(new_d2) or '∅ (nenhum) — rotação da mesma lista'}")
    lines.append(f"- **Itens repetidos Dia1∩Dia2:** {sorted(shared)}")
    lines.append("")
    lines.append("### Por que reaparecem `to bring about`, `for the time being`, etc.?")
    lines.append("")
    lines.append("1. Placement B2 → `lesson_bank.band_for('B2')` = **`upper`**.")
    lines.append(
        f"2. `lesson_bank.vocabulary('en','upper')` contém **exatamente {len(bank_upper)} itens fixos**:"
    )
    for t in bank_upper:
        lines.append(f"   - `{t}`")
    lines.append(
        "3. `_vocabulary` em `ai.py` chama `_rotate(lista, day_number)` e devolve **a lista inteira** "
        "(não um subconjunto novo por dia)."
    )
    lines.append(
        "4. Dia 1: offset `(1-1)%6=0` → ordem original. "
        "Dia 2: offset `1` → mesma lista deslocada em 1 posição."
    )
    lines.append(
        "5. Portanto **todas** essas expressões reaparecem no Dia 2 (e em praticamente todos os 90 dias)."
    )
    lines.append(
        "6. **`to back up`:** **não está** no banco UPPER atual. "
        "Se o usuário viu essa expressão, veio de **conteúdo curado** (`content_repository` / "
        "`seed_starter_content`) ou de outro modo — não do `lesson_bank` UPPER listado acima."
    )
    lines.append("")
    lines.append("### “CONTINUA DE: BLOCOS ANTERIORES”")
    lines.append("")
    lines.append(
        "- **Origem UI:** `ThreadBanner` em `frontend/.../cronograma/dia/[id]/page.tsx`, "
        "texto fixo quando `thread.sources` existe."
    )
    lines.append(
        "- **Origem dados:** `lesson_thread.day_thread` / carryover em `learner_context` + "
        "`progression.build_block_lesson` → envelope com `thread.carried_terms`."
    )
    lines.append(
        "- **Algoritmo:** ao abrir um bloco **depois** do vocabulário no **mesmo dia**, "
        "o sistema extrai termos da lição anterior e força reuso "
        "(`_target_items` / `apply_to_terms` / `target_expressions`). "
        "Isso é **carryover intradía (tipo B)**, não SRS (tipo C) e não “conteúdo novo” (tipo A)."
    )
    lines.append(
        "- No Dia 2, expressões **novas** no bloco de vocabulário vêm de "
        "`select_daily_vocabulary` (tipo A). Retomadas da semana entram em "
        "`revisited_items` (tipo B). O banner “Continua de…” continua sendo "
        "apenas carryover **intradía**."
    )
    lines.append("")

    lines.append("## 5. Diversidade de atividades")
    lines.append("")
    lines.append(
        "A sequência de **skills** muda o tipo de bloco (vocab → grammar → input → output → review), "
        "o que em tese é a progressão apresentação → estrutura → compreensão → produção → consolidação."
    )
    lines.append("")
    lines.append(
        f"Dias cujo multiset lexical ainda replica o banco UPPER inteiro: "
        f"**{multiset_same}/90** (meta pós-correção: 0)."
    )
    lines.append("")

    lines.append("## 6. Teaching Engine V2")
    lines.append("")
    lines.append(
        f"- LearningObjectives no banco: **{len(objectives)}** "
        f"(inclui stubs por tema B2 + slice EN-A1-CAN-001 se seedado)"
    )
    lines.append(f"- Blocos do currículo com `objective_id`: **{objective_linked}/{total_blocks}**")
    lines.append(
        "- Ligação leve: blocos `vocabulary` em B2+ recebem `objective_id` do "
        "objetivo temático da semana. O fluxo completo TE V2 "
        "(atividades → evidência → mastery) no path do cronograma ainda é parcial."
    )
    lines.append("")

    lines.append("## 7. Padrões anormais (destaque automático)")
    lines.append("")
    if len(bank_upper) < 30:
        lines.append("1. Banco UPPER ainda pequeno (<30 itens).")
    else:
        lines.append(f"1. Banco UPPER expandido: **{len(bank_upper)}** itens (ok).")
    lines.append(f"2. Sobreposição média Dia N/N+1: **{avg_consec:.0%}**.")
    lines.append(f"3. Blocos com `objective_id`: **{objective_linked}/{total_blocks}**.")
    lines.append(
        "4. Semana 1 B2 piloto: Can-Do distinto por jornada "
        f"({len(week1_can_dos)} objetivos). Demais semanas: âncora temática leve."
    )
    lines.append("5. Checkpoint = semana par + mini-teste; Dia 7 do piloto também tem transfer Can-Do.")
    lines.append("6. Entry B2→B2: sem escada CEFR no plano de 90 dias (esperado).")
    lines.append("")

    lines.append("## 8. Correções aplicadas (lexical + piloto TE)")
    lines.append("")
    lines.append("1. New/revisited por histórico curricular (`exposed_items`), não só semana.")
    lines.append("2. Banco UPPER + seleção diária + papéis explícitos no payload.")
    lines.append("3. Piloto Semana 1 B2: EN-B2-CAN-001…007 com pedagogia/mastery real.")
    lines.append("4. Blocos pedagógicos da Semana 1 compartilham o Can-Do do dia; review sem objective.")
    lines.append("5. Endpoints `/curriculum/block/{id}/teaching/*` para attempt/evidence/retry.")
    lines.append("6. Carryover intradía (B) e SRS (C) mantidos separados.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Fim da auditoria. Nenhuma alteração aplicada ao banco de produção nem aos dados do usuário.*")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    intervals = []
    for days_list in term_exposure_days.values():
        ordered = sorted(days_list)
        for i in range(1, len(ordered)):
            intervals.append(ordered[i] - ordered[i - 1])
    top_terms = sorted(
        ((k, len(v)) for k, v in term_exposure_days.items()),
        key=lambda x: (-x[1], x[0]),
    )[:10]

    # JSON machine-readable sidecar
    sidecar = REPORT_PATH.with_suffix(".json")
    sidecar.write_text(
        json.dumps(
            {
                "classification": classification,
                "label": labels[classification],
                "days": len(days),
                "unique_terms": len(unique_terms),
                "term_occurrences": len(all_terms_flat),
                "avg_consecutive_jaccard": avg_consec,
                "objective_linked_blocks": objective_linked,
                "total_blocks": total_blocks,
                "week1_objective_blocks": week1_objective_blocks,
                "week1_blocks": week1_blocks,
                "week1_can_dos": week1_can_dos,
                "first_exposures": first_exposures,
                "revisits_total": revisits_total,
                "avg_exposures_per_term": avg_exp,
                "new_as_exposed_violations": new_as_exposed_violations,
                "top_repeated_terms": top_terms,
                "mean_repeat_interval_days": (
                    sum(intervals) / len(intervals) if intervals else None
                ),
                "bank_upper": bank_upper,
                "day1_terms": d1["vocab_terms"],
                "day2_terms": d2["vocab_terms"],
                "day1_day2_shared": sorted(shared),
                "day2_new": sorted(new_d2),
                "max_term": max_term,
                "max_count": max_count,
                "multiset_same_as_full_bank_days": multiset_same,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Relatório: {REPORT_PATH}")
    print(f"JSON:      {sidecar}")
    print(f"Classificação: {classification} — {labels[classification]}")
    print(f"Overlap medio Dia N vs N+1: {avg_consec:.0%}")
    print(f"TE objective_id: {objective_linked}/{total_blocks}")
    print(f"Dia1 e Dia2 compartilhados: {sorted(shared)}")
    print(f"Novos Dia2: {sorted(new_d2) or 'nenhum'}")
    return 0


def themes_for_preview() -> str:
    from app.services.curriculum_bank import themes_for

    themes = themes_for("en", CEFRLevel.B2)
    return " → ".join(themes[:5]) + (" → …" if len(themes) > 5 else "")


if __name__ == "__main__":
    raise SystemExit(main())
