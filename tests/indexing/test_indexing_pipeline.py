from __future__ import annotations

from pathlib import Path

from indexing.pipeline import (
    build_and_persist_embeddings_from_chunk_paths,
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
) -> None:
    client = FakeClient()

    records = build_and_persist_embeddings_from_chunk_paths(
        [
            repo_root / "data/processed/chunks/ISP-001.json",
            repo_root / "data/processed/chunks/PVD-001.json",
        ],
        embed_texts=lambda texts: [[float(index)] for index, _ in enumerate(texts, start=1)],
        client=client,
    )

    assert records
    assert len(records) == 86
    assert client.collection.calls
    assert len(client.collection.calls[0]["ids"]) == 86
