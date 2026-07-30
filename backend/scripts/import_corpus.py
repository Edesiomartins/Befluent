"""Importa pares de frases licenciados do Tatoeba para o banco de itens.

IMPORTANTE — escopo deste script:
- Tatoeba é um corpus de frases licenciadas, NÃO um importador de livros/PDFs.
- Todo item importado entra como ``pending_review`` e NÃO é servido ao aluno até revisão.
- Itens pendentes NÃO entram automaticamente em lições nem no teste de nivelamento.
- Para livros e PDFs, use ``python -m tools.content_ingestion`` (candidatos locais).

O download é seu: em https://tatoeba.org/downloads escolha "Sentence pairs",
idioma-alvo + Portuguese, e salve o TSV.

    # confere o que seria importado, sem gravar nada
    python scripts/import_corpus.py --file eng-por.tsv --language en --limit 500 --dry-run

    # importa de verdade
    python scripts/import_corpus.py --file eng-por.tsv --language en --limit 2000

    # com lista de frequência, a calibragem de nível melhora
    python scripts/import_corpus.py --file eng-por.tsv --language en \
        --frequency en_50k.txt --limit 2000

Todo item importado entra como `pending_review` e NÃO é servido ao aluno até ser
revisado. Isso é deliberado: a estimativa de nível é heurística.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import inspect  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import SessionLocal, engine  # noqa: E402
from app.services.corpus_import import (  # noqa: E402
    import_pairs,
    load_frequency_ranks,
)

SUPPORTED = {"en", "es-ES", "fr", "ja", "zh-CN"}

REQUIRED_COLUMNS = {"source", "license", "attribution", "source_ref", "review_status"}


def _safe_target() -> str:
    """Descreve o banco de destino sem expor usuário e senha."""
    url = engine.url
    if url.get_backend_name() == "sqlite":
        return f"sqlite: {url.database}"
    host = url.host or "?"
    return f"{url.get_backend_name()}: {host}/{url.database or '?'}"


def _check_schema() -> str | None:
    """Confirma que a migration de proveniência já rodou neste banco."""
    inspector = inspect(engine)
    if not inspector.has_table("placement_items"):
        return "A tabela placement_items não existe. Rode: alembic upgrade head"
    columns = {column["name"] for column in inspector.get_columns("placement_items")}
    missing = REQUIRED_COLUMNS - columns
    if missing:
        return (
            "Faltam colunas de proveniência em placement_items: "
            f"{', '.join(sorted(missing))}. Rode: alembic upgrade head"
        )
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, help="TSV de pares do Tatoeba")
    parser.add_argument("--language", required=True, help=f"Um de: {', '.join(sorted(SUPPORTED))}")
    parser.add_argument("--limit", type=int, default=None, help="Máximo de pares a ler")
    parser.add_argument("--frequency", default=None, help="Lista de frequência opcional")
    parser.add_argument("--dry-run", action="store_true", help="Não grava nada")
    args = parser.parse_args()

    if args.language not in SUPPORTED:
        print(f"Idioma não suportado: {args.language}", file=sys.stderr)
        return 2

    path = pathlib.Path(args.file)
    if not path.is_file():
        print(f"Arquivo não encontrado: {path}", file=sys.stderr)
        return 2

    # Deixa explícito o destino: importar dezenas de milhares de linhas no banco
    # errado é silencioso e caro de desfazer.
    print(f"Banco de destino: {_safe_target()}")
    problem = _check_schema()
    if problem:
        print(problem, file=sys.stderr)
        return 3

    ranks = None
    if args.frequency:
        frequency_path = pathlib.Path(args.frequency)
        if not frequency_path.is_file():
            print(f"Lista de frequência não encontrada: {frequency_path}", file=sys.stderr)
            return 2
        ranks = load_frequency_ranks(frequency_path)
        print(f"Lista de frequência: {len(ranks)} palavras")
    else:
        print(
            "AVISO: sem lista de frequência, o nível é estimado apenas por "
            "comprimento da frase — proxy grosseiro."
        )

    with SessionLocal() as db:
        stats = import_pairs(
            db,
            path,
            args.language,
            limit=args.limit,
            frequency_ranks=ranks,
            dry_run=args.dry_run,
        )

    print(json.dumps(stats.as_dict(), indent=2, ensure_ascii=False))
    if args.dry_run:
        print("\nDry-run: nada foi gravado.")
    else:
        print(
            f"\n{stats.imported} itens gravados como 'pending_review'. "
            "Eles não aparecem no teste até serem revisados e aprovados."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
