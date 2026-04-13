"""Shared text parsing and normalization helpers."""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


WHITESPACE_RE = re.compile(r"[ \t]+")
MULTI_BLANK_RE = re.compile(r"\n{3,}")
SEPARATOR_LINE_RE = re.compile(r"(?m)^(?:---+|\*\*\*+|___+)\s*$")
INLINE_SECTION_RE = re.compile(
    r"(?m)^(?:#{1,6}\s+)?(?:\*\*)?(?P<section_id>(?:§\s*)?\d+(?:\.\d+)*)(?:[.)])?(?:\*\*)?\s+(?P<heading>[^\n]+?)\s*$",
)

XML_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def normalize_text(text: str) -> str:
    """Trim noisy whitespace while preserving paragraph boundaries."""

    cleaned_lines = [WHITESPACE_RE.sub(" ", line).strip() for line in text.replace("\r", "").split("\n")]
    cleaned = "\n".join(cleaned_lines)
    cleaned = MULTI_BLANK_RE.sub("\n\n", cleaned)
    return cleaned.strip()


def flatten_json_to_text(value: Any, prefix: str = "") -> str:
    """Flatten nested JSON into stable line-oriented text."""

    lines: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else key
            lines.append(flatten_json_to_text(item, next_prefix))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            next_prefix = f"{prefix}[{index}]"
            lines.append(flatten_json_to_text(item, next_prefix))
    else:
        lines.append(f"{prefix}: {value}")
    return "\n".join(line for line in lines if line).strip()


def stable_json_text(value: Any) -> str:
    """Serialize JSON-like data to text for provenance and debugging."""

    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True)


def split_policy_sections(raw_text: str) -> list[tuple[str, str, str, int]]:
    """Split a policy document into section-boundary units."""

    all_matches = list(INLINE_SECTION_RE.finditer(raw_text))
    # Only split at top-level section boundaries (no subsection dots)
    matches = [
        m for m in all_matches
        if "." not in normalize_section_id(m.group("section_id"))
    ]
    if not matches:
        text = normalize_text(raw_text)
        if not text:
            return []
        return [("document", "Document", text, 0)]

    sections: list[tuple[str, str, str, int]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw_text)
        section_id = normalize_section_id(match.group("section_id"))
        heading = normalize_text(match.group("heading"))
        body_start = match.end()
        body_text = _clean_policy_chunk_text(raw_text[body_start:end])
        if not body_text and not _heading_is_substantive(heading):
            continue
        full_text = _clean_policy_chunk_text(f"{section_id} {heading}\n{body_text}".strip())
        sections.append((section_id, heading, full_text, section_level(section_id)))
    return sections


def normalize_section_id(section_id: str) -> str:
    return section_id.replace("§", "").replace(" ", "")


def section_level(section_id: str) -> int:
    if section_id == "document":
        return 0
    return section_id.count(".") + 1


def read_docx_text(path: Path) -> str:
    """Extract text from a DOCX file without external dependencies."""

    with zipfile.ZipFile(path) as archive:
        xml_bytes = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml_bytes)
    paragraphs: list[str] = []
    for paragraph in root.findall(".//main:p", XML_NS):
        text_fragments = [node.text or "" for node in paragraph.findall(".//main:t", XML_NS)]
        if text_fragments:
            paragraphs.append("".join(text_fragments))
    return normalize_text("\n".join(paragraphs))


def xlsx_to_rows(path: Path) -> list[dict[str, str]]:
    """Read the first worksheet from an XLSX file using stdlib only."""

    with zipfile.ZipFile(path) as archive:
        shared_strings = _read_shared_strings(archive)
        worksheet_path = _first_worksheet_path(archive)
        sheet_root = ElementTree.fromstring(archive.read(worksheet_path))

    rows: list[list[str]] = []
    for row_node in sheet_root.findall(".//main:sheetData/main:row", XML_NS):
        row_values: dict[int, str] = {}
        for cell in row_node.findall("main:c", XML_NS):
            cell_ref = cell.attrib.get("r", "")
            column_index = _column_index(cell_ref)
            row_values[column_index] = _read_cell_value(cell, shared_strings)
        if row_values:
            last_index = max(row_values)
            rows.append([row_values.get(index, "") for index in range(last_index + 1)])

    if not rows:
        return []

    header_row_index = max(
        range(len(rows)),
        key=lambda index: sum(1 for value in rows[index] if value.strip()),
    )
    header = [value.strip() for value in rows[header_row_index]]
    header_width = sum(1 for value in header if value)
    normalized_rows: list[dict[str, str]] = []
    for row in rows[header_row_index + 1 :]:
        non_empty_count = sum(1 for value in row if value.strip())
        if non_empty_count == 0:
            continue
        if header_width > 1 and non_empty_count == 1:
            continue
        padded = row + [""] * (len(header) - len(row))
        normalized_rows.append({header[index]: padded[index] for index in range(len(header)) if header[index]})
    return normalized_rows


def parse_markdown_table(text: str) -> list[dict[str, str]]:
    """Parse a single markdown table into row dictionaries."""

    table_lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    if len(table_lines) < 2:
        return []

    header = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    separator = [cell.strip() for cell in table_lines[1].strip("|").split("|")]
    if not all(set(cell) <= {"-", ":"} for cell in separator):
        return []

    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        values = [cell.strip() for cell in line.strip("|").split("|")]
        padded = values + [""] * (len(header) - len(values))
        rows.append({header[index]: padded[index] for index in range(len(header))})
    return rows


def _clean_policy_chunk_text(text: str) -> str:
    without_separators = SEPARATOR_LINE_RE.sub("", text)
    return normalize_text(without_separators)


def _heading_is_substantive(heading: str) -> bool:
    words = heading.split()
    if len(words) >= 5:
        return True
    return any(token.lower() in {"must", "shall", "required", "requires", "prohibited"} for token in words)


def _read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    strings: list[str] = []
    for item in root.findall("main:si", XML_NS):
        parts = [node.text or "" for node in item.findall(".//main:t", XML_NS)]
        strings.append("".join(parts))
    return strings


def _first_worksheet_path(archive: zipfile.ZipFile) -> str:
    workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    relationship_targets = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in relationships.findall("pkgrel:Relationship", XML_NS)
    }
    first_sheet = workbook.find("main:sheets/main:sheet", XML_NS)
    if first_sheet is None:
        raise ValueError(f"No worksheet found in {archive.filename}")
    rel_id = first_sheet.attrib[f"{{{XML_NS['rel']}}}id"]
    target = relationship_targets[rel_id]
    if target.startswith("/"):
        return target.lstrip("/")
    if target.startswith("xl/"):
        return target
    return f"xl/{target}"


def _column_index(cell_ref: str) -> int:
    letters = "".join(character for character in cell_ref if character.isalpha())
    index = 0
    for character in letters:
        index = index * 26 + (ord(character.upper()) - ord("A") + 1)
    return max(index - 1, 0)


def _read_cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//main:t", XML_NS))

    value_node = cell.find("main:v", XML_NS)
    if value_node is None or value_node.text is None:
        return ""

    value = value_node.text
    if cell_type == "s":
        return shared_strings[int(value)]
    if cell_type == "b":
        return "TRUE" if value == "1" else "FALSE"
    return value
