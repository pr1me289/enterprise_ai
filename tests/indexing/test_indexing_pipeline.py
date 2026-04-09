from __future__ import annotations

from pathlib import Path

from indexing.pipeline import (
    build_and_persist_embeddings_from_chunk_paths,
    build_storage_indices,
    load_chunk_artifacts,
    load_chunk_artifacts_from_dir,
)


class FakeCollection:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def upsert(self, **kwargs: object) -> None:
        self.calls.append(kwargs)


class FakeClient:
    def __init__(self) -> None:
        self.collection = FakeCollection()

    def get_or_create_collection(self, *, name: str) -> FakeCollection:
        return self.collection


def test_load_chunk_artifacts_reads_existing_chunk_json(repo_root: Path) -> None:
    chunks = load_chunk_artifacts(
        [
            repo_root / "data/processed/chunks/ISP-001.json",
            repo_root / "data/processed/chunks/DPA-TM-001.json",
        ]
    )

    assert chunks
    assert chunks[0].source_id == "DPA-TM-001"
    assert any(chunk.source_id == "ISP-001" for chunk in chunks)
    assert all(isinstance(chunk.allowed_agents, tuple) for chunk in chunks)


def test_load_chunk_artifacts_from_dir_reads_all_current_chunk_artifacts(repo_root: Path) -> None:
    chunks = load_chunk_artifacts_from_dir(repo_root / "data/processed/chunks")

    assert chunks
    assert {chunk.source_id for chunk in chunks} == {
        "DPA-TM-001",
        "ISP-001",
        "PAM-001",
        "PVD-001",
        "SLK-001",
    }


def test_build_and_persist_embeddings_from_chunk_paths_builds_records_and_persists(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    client = FakeClient()

    records = build_and_persist_embeddings_from_chunk_paths(
        [
            repo_root / "data/processed/chunks/ISP-001.json",
            repo_root / "data/processed/chunks/PVD-001.json",
        ],
        registry_directory=tmp_path / "vector_registry",
        embed_texts=lambda texts: [[float(index)] for index, _ in enumerate(texts, start=1)],
        client=client,
    )

    assert records
    assert len(records) == 86
    assert client.collection.calls
    assert len(client.collection.calls[0]["ids"]) == 86


def test_build_storage_indices_writes_vector_bm25_and_structured_outputs(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    result = build_storage_indices(
        chunk_artifact_dir=repo_root / "data/processed/chunks",
        questionnaire_path=repo_root / "mock_documents/OptiChain_VSQ_001_v2_1.json",
        chroma_persist_directory=tmp_path / "chroma",
        vector_registry_directory=tmp_path / "vector_registry",
        bm25_persist_directory=tmp_path / "bm25",
        structured_store_directory=tmp_path / "structured",
        index_registry_path=tmp_path / "indexes/index_registry.json",
        embed_texts=lambda texts: [[float(index)] for index, _ in enumerate(texts, start=1)],
    )

    assert result["vector_counts"]["idx_security_policy"] == 82
    assert result["bm25_counts"]["idx_precedents"] == 4
    assert result["structured_store_path"].name == "vq_direct_access.json"
    assert result["index_registry_path"].name == "index_registry.json"
    assert (tmp_path / "bm25/idx_security_policy.pkl").exists()
    assert (tmp_path / "vector_registry/idx_slack_notes.json").exists()
