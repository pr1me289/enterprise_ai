"""Chunk artifact writing for canonical intermediate JSON outputs."""

from __future__ import annotations

import json
from pathlib import Path

from preprocessing import NormalizedSource

from .chunker import chunk_source
from .models import Chunk


DEFAULT_CHUNK_ARTIFACT_DIR = Path("data/processed/chunks")


def write_chunk_artifacts(
    source_chunks: dict[str, list[Chunk]],
    output_dir: str | Path = DEFAULT_CHUNK_ARTIFACT_DIR,
) -> list[Path]:
    artifact_dir = Path(output_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    written_paths: list[Path] = []
    for source_id, chunks in source_chunks.items():
        if not chunks:
            continue
        artifact_path = artifact_dir / f"{source_id}.json"
        artifact_path.write_text(
            json.dumps([chunk.to_dict() for chunk in chunks], indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        written_paths.append(artifact_path)
    return written_paths


def chunk_and_write_sources(
    sources: list[NormalizedSource],
    output_dir: str | Path = DEFAULT_CHUNK_ARTIFACT_DIR,
) -> list[Path]:
    source_chunks = {source.source_id: chunk_source(source) for source in sources}
    return write_chunk_artifacts(source_chunks, output_dir=output_dir)
