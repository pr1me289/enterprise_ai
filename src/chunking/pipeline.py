"""Convenience entrypoint for chunk artifact generation."""

from __future__ import annotations

from pathlib import Path

from preprocessing import load_sources

from .artifacts import DEFAULT_CHUNK_ARTIFACT_DIR, chunk_and_write_sources


def build_chunk_artifacts_from_paths(
    paths: list[str | Path],
    output_dir: str | Path = DEFAULT_CHUNK_ARTIFACT_DIR,
) -> list[Path]:
    sources = load_sources(paths)
    return chunk_and_write_sources(sources, output_dir=output_dir)
