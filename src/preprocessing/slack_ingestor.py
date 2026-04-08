"""Ingest Slack note exports while preserving thread boundaries."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .models import NormalizedSource, SlackMessage, SlackThread
from .source_contract import SourceContract
from .text_utils import normalize_text

THREAD_HEADING_RE = re.compile(r"^##\s+Thread\s+\d+\s+[-—]\s+(?P<title>.+)$", re.MULTILINE)
THREAD_ID_RE = re.compile(r"\*\*Thread ID:\*\*\s+(?P<thread_id>\S+)")
EXPORT_DATE_RE = re.compile(r"\*\*Export Date:\*\*\s+(?P<export_date>[^\n]+)")
MESSAGE_COUNT_RE = re.compile(r"\*\*Messages:\*\*\s+(?P<count>\d+)")


def ingest_slack_threads(path: str | Path, contract: SourceContract) -> NormalizedSource:
    source_path = Path(path)
    if source_path.suffix.lower() == ".json":
        data = json.loads(source_path.read_text(encoding="utf-8"))
        threads = _threads_from_json(data)
        document_id = str(data.get("document_id") or contract.source_id)
        detected_version = str(data.get("version") or "") or _detect_version_from_name(source_path.name)
        structured_data = data
    elif source_path.suffix.lower() in {".md", ".markdown"}:
        markdown = source_path.read_text(encoding="utf-8")
        threads = _threads_from_markdown(markdown)
        document_id = contract.source_id
        detected_version = _detect_version_from_name(source_path.name)
        structured_data = None
    else:
        raise ValueError(f"Unsupported slack export format: {source_path.suffix}")

    raw_text = "\n\n".join(thread.text for thread in threads)

    return NormalizedSource(
        source_id=contract.source_id,
        source_type=contract.source_type,
        source_name=contract.source_name,
        version=contract.version,
        authority_tier=contract.authority_tier,
        retrieval_lane=contract.retrieval_lane,
        allowed_agents=contract.allowed_agents,
        status=contract.status,
        owner_role=contract.owner_role,
        source_path=source_path,
        raw_text=normalize_text(raw_text),
        structured_data=structured_data,
        threads=threads,
        document_id=document_id,
        detected_version=detected_version,
        warnings=[],
    )


def _threads_from_json(data: dict) -> list[SlackThread]:
    threads: list[SlackThread] = []
    for index, thread in enumerate(data.get("threads", []), start=1):
        messages = [
            SlackMessage(
                timestamp=str(message.get("timestamp", "")),
                author=str(message.get("author", "")),
                text=normalize_text(str(message.get("text", ""))),
                order=message_index,
            )
            for message_index, message in enumerate(thread.get("messages", []), start=1)
        ]
        thread_text = normalize_text(
            "\n".join(
                [f"channel: {thread.get('channel', '')}"]
                + [f"{message.author} [{message.timestamp}]: {message.text}" for message in messages]
            )
        )
        threads.append(
            SlackThread(
                thread_id=str(thread.get("thread_id") or f"thread-{index:03d}"),
                channel=str(thread.get("channel") or ""),
                export_date=str(thread.get("export_date") or ""),
                message_count=int(thread.get("message_count") or len(messages)),
                messages=messages,
                text=thread_text,
                order=index,
            )
        )
    return threads


def _threads_from_markdown(markdown: str) -> list[SlackThread]:
    matches = list(THREAD_HEADING_RE.finditer(markdown))
    threads: list[SlackThread] = []
    for index, match in enumerate(matches, start=1):
        start = match.start()
        end = matches[index].start() if index < len(matches) else len(markdown)
        block = markdown[start:end]
        thread_id_match = THREAD_ID_RE.search(block)
        export_date_match = EXPORT_DATE_RE.search(block)
        message_count_match = MESSAGE_COUNT_RE.search(block)
        thread_text = normalize_text(block)
        threads.append(
            SlackThread(
                thread_id=thread_id_match.group("thread_id") if thread_id_match else f"thread-{index:03d}",
                channel=match.group("title"),
                export_date=export_date_match.group("export_date") if export_date_match else None,
                message_count=int(message_count_match.group("count")) if message_count_match else None,
                text=thread_text,
                order=index,
            )
        )
    return threads


def _detect_version_from_name(filename: str) -> str | None:
    stem = Path(filename).stem
    for token in stem.replace("-", "_").split("_"):
        if token.lower().startswith("v") and any(character.isdigit() for character in token):
            return token.lower().lstrip("v")
    return None
