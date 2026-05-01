from __future__ import annotations

import json
from pathlib import Path

from chunking.artifacts import write_chunk_artifacts
from chunking.chunker import chunk_source
from preprocessing import load_source

from indexing.pipeline import (
    build_and_persist_embeddings_from_chunk_paths,
    build_and_persist_embeddings_for_scenario,
    build_and_persist_embeddings_for_scenarios,
    build_storage_indices,
    build_storage_indices_for_scenario,
    build_storage_indices_for_scenarios,
    load_chunk_artifacts,
    load_chunk_artifacts_from_dir,
    load_chunk_artifacts_from_dirs,
    scenario_bm25_persist_directory,
    scenario_chroma_persist_directory,
    scenario_embedding_collection_name,
    scenario_index_registry_path,
    scenario_structured_store_directory,
    scenario_vector_registry_directory,
)


class FakeCollection:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[dict[str, object]] = []

    def upsert(self, **kwargs: object) -> None:
        self.calls.append(kwargs)


class FakeClient:
    def __init__(self) -> None:
        self.collections: dict[str, FakeCollection] = {}

    def get_or_create_collection(self, *, name: str) -> FakeCollection:
        if name not in self.collections:
            self.collections[name] = FakeCollection(name)
        return self.collections[name]


def test_load_chunk_artifacts_reads_existing_chunk_json(repo_root: Path) -> None:
    chunks = load_chunk_artifacts(
        [
            repo_root / "data/processed/scenario_1/chunks/ISP-001.json",
            repo_root / "data/processed/scenario_1/chunks/DPA-TM-001.json",
        ]
    )

    assert chunks
    assert chunks[0].source_id == "DPA-TM-001"
    assert any(chunk.source_id == "ISP-001" for chunk in chunks)
    assert all(isinstance(chunk.allowed_agents, tuple) for chunk in chunks)


def test_load_chunk_artifacts_from_dir_reads_all_current_chunk_artifacts(repo_root: Path) -> None:
    chunks = load_chunk_artifacts_from_dir(repo_root / "data/processed/scenario_1/chunks")

    assert chunks
    assert {chunk.source_id for chunk in chunks} == {
        "DPA-TM-001",
        "ISP-001",
        "PAM-001",
        "SHM-001",
        "SLK-001",
    }


def test_build_and_persist_embeddings_from_chunk_paths_builds_records_and_persists(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    client = FakeClient()

    records = build_and_persist_embeddings_from_chunk_paths(
        [
            repo_root / "data/processed/scenario_1/chunks/ISP-001.json",
            repo_root / "data/processed/scenario_1/chunks/SHM-001.json",
        ],
        registry_directory=tmp_path / "vector_registry",
        embed_texts=lambda texts: [[float(index)] for index, _ in enumerate(texts, start=1)],
        client=client,
    )

    assert records
    assert len(records) == 82
    collection = client.collections["enterprise_ai_chunks"]
    assert collection.calls
    assert len(collection.calls[0]["ids"]) == 82
    registry_payload = json.loads((tmp_path / "vector_registry/enterprise_ai_chunks.json").read_text(encoding="utf-8"))
    assert all(item["metadata"]["source_id"] == "ISP-001" for item in registry_payload)


def test_load_chunk_artifacts_from_dirs_reads_both_scenario_directories(repo_root: Path) -> None:
    chunks = load_chunk_artifacts_from_dirs(
        [
            repo_root / "data/processed/scenario_1/chunks",
            repo_root / "data/processed/scenario_2/chunks",
        ]
    )

    assert len(chunks) == 296
    assert sum(1 for chunk in chunks if chunk.source_id == "SHM-001") == 30


def test_build_and_persist_embeddings_for_scenario_uses_scenario_specific_outputs(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    client = FakeClient()

    records = build_and_persist_embeddings_for_scenario(
        "scenario_1",
        chunk_artifact_dir=repo_root / "data/processed/scenario_1/chunks",
        persist_directory=tmp_path / "scenario_1/chroma",
        registry_directory=tmp_path / "scenario_1/vector_registry",
        embed_texts=lambda texts: [[float(index)] for index, _ in enumerate(texts, start=1)],
        client=client,
    )

    assert len(records) == 133
    assert "enterprise_ai_chunks_scenario_1" in client.collections
    assert (tmp_path / "scenario_1/vector_registry/enterprise_ai_chunks_scenario_1.json").exists()


def test_build_and_persist_embeddings_for_scenarios_splits_collections_by_scenario(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    clients: dict[str, FakeClient] = {}

    def client_factory(scenario_name: str) -> FakeClient:
        client = FakeClient()
        clients[scenario_name] = client
        return client

    results = build_and_persist_embeddings_for_scenarios(
        ("scenario_1", "scenario_2"),
        chunk_artifact_dirs={
            "scenario_1": repo_root / "data/processed/scenario_1/chunks",
            "scenario_2": repo_root / "data/processed/scenario_2/chunks",
        },
        persist_directories={
            "scenario_1": tmp_path / "scenario_1/chroma",
            "scenario_2": tmp_path / "scenario_2/chroma",
        },
        registry_directories={
            "scenario_1": tmp_path / "scenario_1/vector_registry",
            "scenario_2": tmp_path / "scenario_2/vector_registry",
        },
        embed_texts=lambda texts: [[float(index)] for index, _ in enumerate(texts, start=1)],
        client_factory=client_factory,
    )

    assert len(results["scenario_1"]) == 133
    assert len(results["scenario_2"]) == 133
    assert "enterprise_ai_chunks_scenario_1" in clients["scenario_1"].collections
    assert "enterprise_ai_chunks_scenario_2" in clients["scenario_2"].collections


def test_scenario_embedding_output_helpers_are_stable() -> None:
    assert scenario_chroma_persist_directory("scenario_1") == Path("data/indexes/scenario_1/chroma")
    assert scenario_vector_registry_directory("scenario_2") == Path("data/indexes/scenario_2/vector_registry")
    assert scenario_embedding_collection_name("scenario_1") == "enterprise_ai_chunks_scenario_1"


def test_build_storage_indices_writes_vector_bm25_and_structured_outputs(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    chunk_artifact_dir = tmp_path / "chunks"
    chunk_artifact_dir.mkdir(parents=True, exist_ok=True)
    for artifact_name in ("ISP-001.json", "DPA-TM-001.json", "PAM-001.json", "SLK-001.json"):
        source_path = repo_root / "data/processed/scenario_1/chunks" / artifact_name
        (chunk_artifact_dir / artifact_name).write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

    precedent_source = load_source(repo_root / "mock_documents/Vendor_Precedent_Log_v1_1.json")
    write_chunk_artifacts(
        {precedent_source.source_id: chunk_source(precedent_source)},
        output_dir=chunk_artifact_dir,
    )

    result = build_storage_indices(
        chunk_artifact_dir=chunk_artifact_dir,
        questionnaire_path=repo_root / "mock_documents/OptiChain_VSQ_001_v2_1.json",
        stakeholder_map_path=repo_root / "scenarios_full_pipeline/scenario_1/source_mock_documents/Stakeholder_Map_PRQ_2024_0047.json",
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
    assert result["structured_store_paths"]["SHM-001"].name == "stakeholder_map_direct_access.json"
    assert result["index_registry_path"].name == "index_registry.json"
    assert (tmp_path / "bm25/idx_security_policy.pkl").exists()
    assert (tmp_path / "vector_registry/idx_slack_notes.json").exists()


def test_build_storage_indices_for_scenario_writes_scenario_specific_outputs(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    result = build_storage_indices_for_scenario(
        "scenario_1",
        repo_root=repo_root,
        chroma_persist_directory=tmp_path / "scenario_1/chroma",
        vector_registry_directory=tmp_path / "scenario_1/vector_registry",
        bm25_persist_directory=tmp_path / "scenario_1/bm25",
        structured_store_directory=tmp_path / "scenario_1/structured",
        index_registry_path=tmp_path / "scenario_1/index_registry.json",
        embed_texts=lambda texts: [[float(index)] for index, _ in enumerate(texts, start=1)],
    )

    assert result["vector_counts"] == {
        "idx_security_policy": 82,
        "idx_slack_notes": 4,
    }
    assert result["bm25_counts"] == result["vector_counts"]
    assert set(result["structured_store_paths"]) == {"VQ-OC-001", "SHM-001"}
    assert (tmp_path / "scenario_1/index_registry.json").exists()
    assert (tmp_path / "scenario_1/structured/stakeholder_map_direct_access.json").exists()


def test_build_storage_indices_for_scenarios_splits_storage_outputs_by_scenario(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    results = build_storage_indices_for_scenarios(
        ("scenario_1", "scenario_2"),
        repo_root=repo_root,
        chroma_persist_directories={
            "scenario_1": tmp_path / "scenario_1/chroma",
            "scenario_2": tmp_path / "scenario_2/chroma",
        },
        vector_registry_directories={
            "scenario_1": tmp_path / "scenario_1/vector_registry",
            "scenario_2": tmp_path / "scenario_2/vector_registry",
        },
        bm25_persist_directories={
            "scenario_1": tmp_path / "scenario_1/bm25",
            "scenario_2": tmp_path / "scenario_2/bm25",
        },
        structured_store_directories={
            "scenario_1": tmp_path / "scenario_1/structured",
            "scenario_2": tmp_path / "scenario_2/structured",
        },
        index_registry_paths={
            "scenario_1": tmp_path / "scenario_1/index_registry.json",
            "scenario_2": tmp_path / "scenario_2/index_registry.json",
        },
        embed_texts=lambda texts: [[float(index)] for index, _ in enumerate(texts, start=1)],
    )

    assert set(results) == {"scenario_1", "scenario_2"}
    assert set(results["scenario_1"]["structured_store_paths"]) == {"VQ-OC-001", "SHM-001"}
    assert results["scenario_1"]["vector_counts"]["idx_security_policy"] == 82
    assert results["scenario_2"]["vector_counts"]["idx_security_policy"] == 82


def test_scenario_storage_output_helpers_are_stable() -> None:
    assert scenario_bm25_persist_directory("scenario_1") == Path("data/bm25/scenario_1")
    assert scenario_chroma_persist_directory("scenario_2") == Path("data/indexes/scenario_2/chroma")
    assert scenario_structured_store_directory("scenario_1") == Path("data/structured/scenario_1")
    assert scenario_index_registry_path("scenario_2") == Path("data/indexes/scenario_2/index_registry.json")
