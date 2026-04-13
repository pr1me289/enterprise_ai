"""Convenience entrypoint for chunk artifact generation."""

from __future__ import annotations

from pathlib import Path

from preprocessing import load_scenario_sources, load_sources

from .artifacts import (
    DEFAULT_CHUNK_ARTIFACT_DIR,
    chunk_and_write_sources,
    scenario_chunk_artifact_dir,
)


def build_chunk_artifacts_from_paths(
    paths: list[str | Path],
    output_dir: str | Path = DEFAULT_CHUNK_ARTIFACT_DIR,
) -> list[Path]:
    sources = load_sources(paths)
    return chunk_and_write_sources(sources, output_dir=output_dir)


def build_scenario_chunk_artifacts(
    scenario_name: str,
    *,
    output_dir: str | Path | None = None,
    repo_root: str | Path | None = None,
) -> list[Path]:
    sources = load_scenario_sources(scenario_name, repo_root=repo_root)
    return chunk_and_write_sources(
        sources,
        output_dir=output_dir or scenario_chunk_artifact_dir(scenario_name),
    )
