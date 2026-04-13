"""Mock indexed retrieval over stored chunk artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from chunking.models import Chunk


TOKEN_RE = re.compile(r"[a-z0-9_]+")


def _tokenize(value: str) -> set[str]:
    return set(TOKEN_RE.findall(value.lower()))


class MockHybridIndexedBackend:
    """Simple term-overlap search over chunk JSON artifacts."""

    def __init__(self, *, chunk_dir: str | Path) -> None:
        self.chunk_dir = Path(chunk_dir)
        self._chunks_by_source = self._load_chunks()

    def query(
        self,
        *,
        source_id: str,
        search_terms: tuple[str, ...],
        metadata_filter: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        scored_hits: list[tuple[float, Chunk]] = []
        query_text = " ".join(search_terms)
        query_tokens = _tokenize(query_text)
        for chunk in self._chunks_by_source.get(source_id, []):
            if not self._matches_metadata(chunk, metadata_filter or {}):
                continue
            score = self._score_chunk(chunk, query_tokens, search_terms)
            if score <= 0:
                continue
            scored_hits.append((score, chunk))

        scored_hits.sort(key=lambda item: item[0], reverse=True)
        results: list[dict[str, Any]] = []
        for rank, (score, chunk) in enumerate(scored_hits[:top_k], start=1):
            results.append(
                {
                    **chunk.to_dict(),
                    "retrieval_score": round(score, 4),
                    "rerank_score": round(score / max(rank, 1), 4),
                }
            )
        return results

    def _load_chunks(self) -> dict[str, list[Chunk]]:
        chunks_by_source: dict[str, list[Chunk]] = {}
        for path in sorted(self.chunk_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, list) or not payload:
                continue
            source_id = payload[0]["source_id"]
            chunks_by_source[source_id] = [Chunk.from_dict(item) for item in payload]
        return chunks_by_source

    def _matches_metadata(self, chunk: Chunk, metadata_filter: dict[str, Any]) -> bool:
        for key, value in metadata_filter.items():
            if getattr(chunk, key, None) != value:
                return False
        return True

    def _score_chunk(self, chunk: Chunk, query_tokens: set[str], search_terms: tuple[str, ...]) -> float:
        text_tokens = _tokenize(chunk.text)
        overlap = len(query_tokens & text_tokens)
        if not overlap:
            return 0.0
        exact_bonus = 0.0
        chunk_text = chunk.text.lower()
        for term in search_terms:
            normalized = term.lower()
            if normalized in chunk_text:
                exact_bonus += 0.5
        return float(overlap) + exact_bonus
