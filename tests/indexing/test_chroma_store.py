from __future__ import annotations

import json

from indexing.chroma_store import persist_embeddings
from indexing.models import EmbeddingRecord


class FakeCollection:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def upsert(self, **kwargs: object) -> None:
        self.calls.append(kwargs)


class FakeClient:
    def __init__(self) -> None:
        self.collection = FakeCollection()
        self.requested_name: str | None = None

    def get_or_create_collection(self, *, name: str) -> FakeCollection:
        self.requested_name = name
        return self.collection


def test_persist_embeddings_upserts_documents_embeddings_and_metadata(tmp_path) -> None:
    client = FakeClient()
    record = EmbeddingRecord(
        chunk_id="ISP-001__section_1",
        text="policy chunk",
        embedding=[0.1, 0.2],
        source_id="ISP-001",
        source_name="IT Security Policy",
        source_type="POLICY",
        version="4.2",
        document_date="2026-04-04",
        freshness_status="CURRENT",
        authority_tier=1,
        retrieval_lane="INDEXED_HYBRID",
        allowed_agents=("it_security", "legal"),
        is_primary_citable=True,
        manifest_status="PROVISIONAL",
        chunk_type="SECTION",
        citation_label="ISP-001 §1",
        section_id="1",
    )

    written = persist_embeddings(
        [record],
        collection_name="test_collection",
        client=client,
        registry_directory=tmp_path,
    )

    assert written == 1
    assert client.requested_name == "test_collection"
    call = client.collection.calls[0]
    assert call["ids"] == ["ISP-001__section_1"]
    assert call["documents"] == ["policy chunk"]
    assert call["embeddings"] == [[0.1, 0.2]]
    metadata = call["metadatas"][0]
    assert metadata["section_id"] == "1"
    assert metadata["freshness_status"] == "CURRENT"
    assert json.loads(metadata["allowed_agents"]) == ["it_security", "legal"]


def test_persist_embeddings_returns_zero_for_empty_input() -> None:
    assert persist_embeddings([], client=FakeClient(), registry_directory="/tmp") == 0
