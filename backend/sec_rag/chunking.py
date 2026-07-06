"""Chunk SEC 10-K markdown filings for vector ingestion."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paths import KNOWLEDGE_BASE

SECTION_HEADER_RE = re.compile(r"^##\s+([\w-]+)\s*$", re.MULTILINE)
SECTION_CHUNK_SIZE = 1200
SECTION_CHUNK_OVERLAP = 200


def parse_front_matter(text: str) -> tuple[dict, str]:
    metadata = {}
    lines = text.split("\n")
    body_start = 0

    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith("- ") and ":" in line:
            key, _, value = line[2:].partition(":")
            metadata[key.strip().lower().replace(" ", "_")] = value.strip()
        elif line == "---":
            body_start = i + 1
            break

    return metadata, "\n".join(lines[body_start:])


def split_into_sections(body: str) -> list[tuple[str, str]]:
    matches = list(SECTION_HEADER_RE.finditer(body))
    if not matches:
        return [("full_document", body.strip())]

    sections = []
    for i, match in enumerate(matches):
        section_name = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        section_text = body[start:end].strip()
        if section_text:
            sections.append((section_name, section_text))
    return sections


def chunk_filing(file_path: Path) -> list[dict]:
    text = file_path.read_text(encoding="utf-8")
    front, body = parse_front_matter(text)

    parts = file_path.parts
    sector = parts[-3]
    ticker = parts[-2]
    year_match = re.match(r"(\d{4})", file_path.stem)
    year = int(year_match.group(1)) if year_match else 0

    base_metadata = {
        "source": str(file_path.relative_to(KNOWLEDGE_BASE.parent)),
        "ticker": ticker,
        "company": front.get("company", ticker),
        "sector": sector,
        "filing_year": year,
        "doc_type": "10-K",
    }

    sections = split_into_sections(body)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=SECTION_CHUNK_SIZE,
        chunk_overlap=SECTION_CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    for section_name, section_text in sections:
        if len(section_text) < 50:
            continue

        for i, sub in enumerate(splitter.split_text(section_text)):
            contextual_text = (
                f"[{base_metadata['company']} ({ticker}) — {year} 10-K — "
                f"{section_name}]\n\n{sub}"
            )
            chunks.append(
                {
                    "text": contextual_text,
                    "metadata": {
                        **base_metadata,
                        "item": section_name,
                        "chunk_index": i,
                    },
                }
            )
    return chunks


def chunk_all_filings(limit_files: int | None = None) -> list[dict]:
    if not KNOWLEDGE_BASE.exists():
        raise FileNotFoundError(f"Knowledge base not found: {KNOWLEDGE_BASE}")

    from implementation.sp500_tickers import allowed_tickers

    allowed = allowed_tickers()
    files = sorted(
        fp
        for fp in KNOWLEDGE_BASE.rglob("*_10-K.md")
        if fp.parent.name in allowed
    )
    if limit_files:
        files = files[:limit_files]

    all_chunks: list[dict] = []
    for file_path in files:
        try:
            all_chunks.extend(chunk_filing(file_path))
        except Exception as exc:
            print(f"Failed to chunk {file_path}: {exc}", file=sys.stderr)
    return all_chunks
