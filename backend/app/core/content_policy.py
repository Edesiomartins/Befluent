"""Políticas da Biblioteca Pedagógica (não é aconselhamento jurídico)."""

from __future__ import annotations

from enum import StrEnum


class UsagePolicy(StrEnum):
    OPEN_LICENSE = "OPEN_LICENSE"
    PUBLIC_DOMAIN = "PUBLIC_DOMAIN"
    SHORT_QUOTE_ONLY = "SHORT_QUOTE_ONLY"
    CONCEPTS_ONLY = "CONCEPTS_ONLY"
    BLOCKED = "BLOCKED"
    UNREVIEWED = "UNREVIEWED"


class OriginType(StrEnum):
    ORIGINAL = "ORIGINAL"
    CONCEPT_DERIVED = "CONCEPT_DERIVED"
    SHORT_EXCERPT = "SHORT_EXCERPT"
    OPEN_LICENSE_DERIVED = "OPEN_LICENSE_DERIVED"


class ValidationStatus(StrEnum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    BLOCKED = "BLOCKED"


class SimilarityVerdict(StrEnum):
    APPROVED = "APPROVED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    BLOCKED = "BLOCKED"


#: PDFs conhecidos sem camada textual útil — exigem OCR (fora do escopo).
OCR_REQUIRED_FILENAMES = frozenset(
    {
        "3Textos-en-portugués.pdf",
        "Espan_ol_avanzado_1.pdf",
        "Exercícios de cores em chinês.pdf",
        "Os numeros em chinês 0-5.pdf",
        "Os numeros em chinês 5-10.pdf",
        "Planilha de escrita chinesa- Natureza.pdf",
        "课本扫描Miolo-Livro-Aprende-Chinês-Comigo-pt.-1.pdf",
    }
)
