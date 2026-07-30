"""Ferramentas locais de ingestão de conteúdo pedagógico (PDFs → candidatos JSON)."""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORK_ROOT = ROOT / "content_work"
MANIFEST_ROOT = ROOT / "content_manifests"
CANDIDATES_ROOT = ROOT / "content_candidates"

for folder in (WORK_ROOT, MANIFEST_ROOT, CANDIDATES_ROOT):
    folder.mkdir(parents=True, exist_ok=True)


def _require_path(path: str | None, label: str) -> pathlib.Path:
    if not path:
        print(f"Informe {label}.", file=sys.stderr)
        raise SystemExit(2)
    resolved = pathlib.Path(path).expanduser().resolve()
    if not resolved.exists():
        print(f"Arquivo não encontrado: {resolved}", file=sys.stderr)
        raise SystemExit(2)
    return resolved


def cmd_inventory(args) -> int:
    target = _require_path(args.path, "--path")
    from app.core.content_policy import OCR_REQUIRED_FILENAMES

    if target.name in OCR_REQUIRED_FILENAMES:
        print(f"PDF exige OCR (fora do escopo): {target.name}")
        return 1
    try:
        import fitz  # pymupdf
    except ImportError:
        print("Instale pymupdf: pip install pymupdf", file=sys.stderr)
        return 1

    doc = fitz.open(target)
    manifest = {
        "filename": target.name,
        "page_count": doc.page_count,
        "file_hash": hashlib.sha256(target.read_bytes()).hexdigest(),
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "ocr_required": target.name in OCR_REQUIRED_FILENAMES,
    }
    out = MANIFEST_ROOT / f"{target.stem}.inventory.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Inventário salvo em {out}")
    return 0


def cmd_extract(args) -> int:
    target = _require_path(args.path, "--path")
    from app.core.content_policy import OCR_REQUIRED_FILENAMES

    if target.name in OCR_REQUIRED_FILENAMES:
        print(f"PDF exige OCR (fora do escopo): {target.name}", file=sys.stderr)
        return 1
    try:
        import fitz
    except ImportError:
        print("Instale pymupdf: pip install pymupdf", file=sys.stderr)
        return 1

    doc = fitz.open(target)
    pages = []
    for index in range(doc.page_count):
        text = doc.load_page(index).get_text("text").strip()
        pages.append({"page": index + 1, "chars": len(text), "preview": text[:240]})
    payload = {"filename": target.name, "pages": pages}
    out = WORK_ROOT / f"{target.stem}.extract.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Extração salva em {out}")
    return 0


def cmd_generate(args) -> int:
    extract_path = WORK_ROOT / f"{pathlib.Path(args.source).stem}.extract.json"
    if not extract_path.exists():
        print(f"Extração ausente: {extract_path}. Rode extract antes.", file=sys.stderr)
        return 2
    data = json.loads(extract_path.read_text(encoding="utf-8"))
    candidate = {
        "title": args.title or data.get("filename", "Unidade"),
        "language_code": args.language,
        "cefr_level": args.level,
        "skill": args.skill,
        "mode": args.mode,
        "validation_status": "PENDING_REVIEW",
        "payload": {"excerpt_pages": data.get("pages", [])[:3]},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    out = CANDIDATES_ROOT / f"{candidate['title'].replace(' ', '_')}.candidate.json"
    out.write_text(json.dumps(candidate, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Candidato PENDING_REVIEW: {out}")
    return 0


def cmd_validate(args) -> int:
    candidate_path = _require_path(args.path, "--path")
    data = json.loads(candidate_path.read_text(encoding="utf-8"))
    errors = []
    for field in ("language_code", "cefr_level", "skill", "mode", "validation_status"):
        if not data.get(field):
            errors.append(f"Campo ausente: {field}")
    if data.get("validation_status") != "PENDING_REVIEW":
        errors.append("Candidatos devem permanecer PENDING_REVIEW até revisão humana.")
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1
    print("Candidato válido (ainda não aprovado para lições).")
    return 0


def cmd_list_candidates(_args) -> int:
    files = sorted(CANDIDATES_ROOT.glob("*.json"))
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        print(f"{path.name}\t{data.get('validation_status')}\t{data.get('language_code')}")
    print(f"Total: {len(files)}")
    return 0


def cmd_approve(args) -> int:
    candidate_path = _require_path(args.path, "--path")
    data = json.loads(candidate_path.read_text(encoding="utf-8"))
    data["validation_status"] = "APPROVED"
    data["approved_at"] = datetime.now(timezone.utc).isoformat()
    approved_dir = ROOT / "content_manifests" / "approved"
    approved_dir.mkdir(parents=True, exist_ok=True)
    out = approved_dir / candidate_path.name
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Aprovado localmente (importe com import-approved): {out}")
    return 0


def cmd_reject(args) -> int:
    if not args.reason or not args.reason.strip():
        print("Rejeição exige --reason.", file=sys.stderr)
        return 2
    candidate_path = _require_path(args.path, "--path")
    data = json.loads(candidate_path.read_text(encoding="utf-8"))
    data["validation_status"] = "REJECTED"
    data["reject_reason"] = args.reason.strip()
    rejected_dir = ROOT / "content_rejected"
    rejected_dir.mkdir(parents=True, exist_ok=True)
    out = rejected_dir / candidate_path.name
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    candidate_path.unlink(missing_ok=True)
    print(f"Rejeitado: {out}")
    return 0


def cmd_import_approved(_args) -> int:
    approved_dir = ROOT / "content_manifests" / "approved"
    if not approved_dir.exists():
        print("Nenhum candidato aprovado local.", file=sys.stderr)
        return 1
    files = list(approved_dir.glob("*.json"))
    print(f"{len(files)} candidato(s) aprovado(s) prontos para importação manual ao banco.")
    print("Use o repositório de conteúdo / migration dedicada — não auto-importa para lições.")
    return 0


def cmd_report(_args) -> int:
    pending = len(list(CANDIDATES_ROOT.glob("*.json")))
    approved_dir = ROOT / "content_manifests" / "approved"
    approved = len(list(approved_dir.glob("*.json"))) if approved_dir.exists() else 0
    rejected_dir = ROOT / "content_rejected"
    rejected = len(list(rejected_dir.glob("*.json"))) if rejected_dir.exists() else 0
    print("Relatório content_ingestion")
    print(f"  pending_candidates: {pending}")
    print(f"  approved_local: {approved}")
    print(f"  rejected_local: {rejected}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingestão local de conteúdo pedagógico")
    sub = parser.add_subparsers(dest="command", required=True)

    p_inv = sub.add_parser("inventory")
    p_inv.add_argument("--path", required=True)

    p_ext = sub.add_parser("extract")
    p_ext.add_argument("--path", required=True)

    p_gen = sub.add_parser("generate")
    p_gen.add_argument("--source", required=True, help="Nome do PDF de origem")
    p_gen.add_argument("--language", default="en")
    p_gen.add_argument("--level", default="A2")
    p_gen.add_argument("--skill", default="reading")
    p_gen.add_argument("--mode", default="reading")
    p_gen.add_argument("--title")

    p_val = sub.add_parser("validate")
    p_val.add_argument("--path", required=True)

    sub.add_parser("list-candidates")

    p_app = sub.add_parser("approve")
    p_app.add_argument("--path", required=True)

    p_rej = sub.add_parser("reject")
    p_rej.add_argument("--path", required=True)
    p_rej.add_argument("--reason", required=True)

    sub.add_parser("import-approved")
    sub.add_parser("report")

    args = parser.parse_args(argv)
    handlers = {
        "inventory": cmd_inventory,
        "extract": cmd_extract,
        "generate": cmd_generate,
        "validate": cmd_validate,
        "list-candidates": cmd_list_candidates,
        "approve": cmd_approve,
        "reject": cmd_reject,
        "import-approved": cmd_import_approved,
        "report": cmd_report,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
