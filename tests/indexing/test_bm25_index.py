from __future__ import annotations

from indexing.build_bm25_index import BM25Index, tokenize


def _make_record(
    chunk_id: str,
    text: str,
    *,
    source_id: str = "ISP-001",
    section_id: str = "12.2.1",
) -> dict:
    return {
        "chunk_id": chunk_id,
        "text": text,
        "metadata": {
            "chunk_id": chunk_id,
            "source_id": source_id,
            "source_type": "POLICY",
            "authority_tier": 1,
            "retrieval_lane": "INDEXED_HYBRID",
            "version": "4.2",
            "document_date": "2026-04-04",
            "freshness_status": "CURRENT",
            "allowed_agents": ["legal"],
            "is_primary_citable": True,
            "section_id": section_id,
            "text": text,
        },
    }


def test_tokenize_preserves_identifiers_and_acronyms() -> None:
    tokens = tokenize("ERP §12.2.1 DPA NDA SSO")

    assert "erp" in tokens
    assert "§12.2.1" in tokens
    assert "dpa" in tokens


def test_bm25_index_builds_and_filters_before_scoring(tmp_path) -> None:
    index = BM25Index(persist_directory=tmp_path)
    index.build(
        "idx_security_policy",
        [
            _make_record("chunk-a", "ERP integration requires review", section_id="12.2.1"),
            _make_record("chunk-b", "NDA execution is required before sharing data", section_id="12.1.4"),
            _make_record("chunk-c", "SSO login access is reviewed quarterly", section_id="6.2.1"),
        ],
    )

    hits = index.query(
        "idx_security_policy",
        "NDA",
        k=2,
        metadata_filter={"section_id": "99.9.9"},
        allowed_agent="legal",
    )

    assert hits == []
    hits = index.query("idx_security_policy", "NDA execution", k=2, allowed_agent="legal")
    assert hits[0]["chunk_id"] == "chunk-b"
