"""Locked source-manifest configuration for orchestration runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from indexing.load_index_registry import load_index_registry

DEFAULT_MANIFEST_VERSION = "CC-001-v1.4"


@dataclass(frozen=True, slots=True)
class SourceManifest:
    manifest_version: str
    sources: dict[str, dict[str, Any]]


def build_source_manifest(manifest_version: str = DEFAULT_MANIFEST_VERSION) -> SourceManifest:
    registry = load_index_registry()
    return SourceManifest(
        manifest_version=manifest_version,
        sources=dict(registry["sources"]),
    )


DEFAULT_STAKEHOLDER_MAP: dict[str, Any] = {
    "stakeholder_map": {
        "IT Security": {"domain": "security", "contact": "K. Whitfield"},
        "Legal (General Counsel)": {"domain": "legal", "contact": "General Counsel"},
        "Procurement": {"domain": "procurement", "contact": "Procurement Manager"},
        "Procurement Director": {"domain": "procurement", "contact": "Procurement Director"},
        "Procurement / Legal": {"domain": "procurement", "contact": "Procurement + Legal"},
    },
    "approver_contacts": {
        "security": "K. Whitfield",
        "legal": "General Counsel",
        "procurement": "Procurement Director",
    },
    "escalation_owners": {
        "ERP integration tier unclassified": "IT Security",
        "GDPR Art. 28 DPA not yet executed": "Legal (General Counsel)",
        "NDA execution unconfirmed": "Procurement / Legal",
    },
}
