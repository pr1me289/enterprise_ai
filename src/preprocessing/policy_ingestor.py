"""Ingest policy documents into normalized source objects."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .models import NormalizedSource, PolicySection
from .source_contract import SourceContract
from .text_utils import normalize_text, read_docx_text, split_policy_sections


def ingest_policy(path: str | Path, contract: SourceContract) -> NormalizedSource:
    source_path = Path(path)
    raw_text = _read_policy_text(source_path)
    detected_version = _detect_version_from_name(source_path.name)

    sections = [
        PolicySection(
            section_id=section_id,
            heading=heading,
            text=text,
            order=index,
            level=level,
        )
        for index, (section_id, heading, text, level) in enumerate(split_policy_sections(raw_text), start=1)
    ]

    return NormalizedSource(
        source_id=contract.source_id,
        source_type=contract.source_type,
        source_name=contract.source_name,
        version=contract.version,
        document_date=contract.document_date,
        freshness_status=contract.freshness_status,
        authority_tier=contract.authority_tier,
        retrieval_lane=contract.retrieval_lane,
        allowed_agents=contract.allowed_agents,
        is_primary_citable=contract.is_primary_citable,
        manifest_status=contract.manifest_status,
        owner_role=contract.owner_role,
        source_path=source_path,
        raw_text=normalize_text(raw_text),
        sections=sections,
        document_id=contract.source_id,
        detected_version=detected_version,
        warnings=[],
    )


def _read_policy_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        return normalize_text(path.read_text(encoding="utf-8"))
    if suffix == ".docx":
        return read_docx_text(path)
    if suffix == ".pdf":
        return _extract_pdf_text(path)
    raise ValueError(f"Unsupported policy format: {path.suffix}")


def _extract_pdf_text(path: Path) -> str:
    pdftotext_path = shutil.which("pdftotext")
    if pdftotext_path:
        result = subprocess.run(
            [pdftotext_path, "-layout", str(path), "-"],
            check=True,
            capture_output=True,
            text=True,
        )
        return normalize_text(result.stdout)

    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "PDF ingestion requires either the `pdftotext` command or the `pypdf` package."
        ) from exc

    reader = PdfReader(str(path))
    text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    return normalize_text(text)


def _detect_version_from_name(filename: str) -> str | None:
    stem = Path(filename).stem
    for token in stem.replace("-", "_").split("_"):
        if token.lower().startswith("v") and any(character.isdigit() for character in token):
            return token.lower().lstrip("v")
    return None
