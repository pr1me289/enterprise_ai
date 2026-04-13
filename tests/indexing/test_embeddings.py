from __future__ import annotations

from chunking import Chunk
from indexing.embeddings import build_embeddings, should_embed


def _make_chunk(
    *,
    chunk_id: str,
    retrieval_lane: str = "INDEXED_HYBRID",
    source_id: str = "ISP-001",
    chunk_order: int = 1,
    text: str = "policy text",
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        source_id=source_id,
        source_name="IT Security Policy",
        source_type="POLICY_DOCUMENT",
        version="4.2",
        document_date="2026-04-04",
        freshness_status="CURRENT",
        authority_tier=1,
        retrieval_lane=retrieval_lane,
        allowed_agents=("it_security",),
        is_primary_citable=True,
        manifest_status="PROVISIONAL",
        chunk_type="SECTION",
        chunk_order=chunk_order,
        citation_label=f"{source_id} citation",
        text=text,
    )


def test_should_embed_only_allows_indexed_hybrid_chunks() -> None:
    assert should_embed(_make_chunk(chunk_id="ISP-001__section_1")) is True
    assert should_embed(
        _make_chunk(
            chunk_id="VQ-OC-001__field_vendor_name",
            retrieval_lane="DIRECT_STRUCTURED",
            source_id="VQ-OC-001",
        )
    ) is False


def test_build_embeddings_filters_non_eligible_chunks_and_sorts_deterministically() -> None:
    chunks = [
        _make_chunk(chunk_id="ISP-001__section_2", chunk_order=2, text="second"),
        _make_chunk(
            chunk_id="VQ-OC-001__field_vendor_name",
            retrieval_lane="DIRECT_STRUCTURED",
            source_id="VQ-OC-001",
            text="questionnaire",
        ),
        _make_chunk(chunk_id="ISP-001__section_1", chunk_order=1, text="first"),
    ]

    captured_texts: list[str] = []

    def fake_embed(texts: list[str]) -> list[list[float]]:
        captured_texts.extend(texts)
        return [[float(index), float(index) + 0.5] for index, _ in enumerate(texts, start=1)]

    records = build_embeddings(chunks, embed_texts=fake_embed)

    assert captured_texts == ["first", "second"]
    assert [record.chunk_id for record in records] == [
        "ISP-001__section_1",
        "ISP-001__section_2",
    ]
    assert records[0].embedding == [1.0, 1.5]
    assert records[1].embedding == [2.0, 2.5]


def test_build_embeddings_copies_current_chunk_metadata_without_new_fields() -> None:
    chunk = _make_chunk(chunk_id="SLK-001__thread_1", source_id="SLK-001", text="thread text")

    record = build_embeddings([chunk], embed_texts=lambda texts: [[0.1, 0.2]])[0]

    assert record.chunk_id == "SLK-001__thread_1"
    assert record.text == "thread text"
    assert record.document_date == "2026-04-04"
    assert record.freshness_status == "CURRENT"
    assert record.is_primary_citable is True
    assert record.manifest_status == "PROVISIONAL"
    assert record.allowed_agents == ("it_security",)
