"""
Ingest 10-K filings into Chroma.

Design notes:

1. No LLM-based chunking. 10-Ks have predictable structure (Item 1, 1A, 7, ...).
   Sections are split deterministically by header, then recursively split when long
   (Risk Factors and MD&A are routinely 30k+ words).

2. Rich metadata on every chunk:
       ticker, company, sector, filing_year, item (e.g. "1A_RiskFactors"),
       source (path), chunk_index
   Metadata powers filtered retrieval in answer.py — e.g. a question about
   "Apple's 2024 risk factors" can filter ticker=AAPL and year=2024 before search.

3. Embeddings use OpenAI text-embedding-3-large, batched under API limits.

Usage:
    python -m implementation.ingest
"""

from __future__ import annotations

import re
from pathlib import Path

from chromadb import PersistentClient
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI
from tenacity import retry, wait_exponential
from tqdm import tqdm

load_dotenv(override=True)

DB_NAME = str(Path(__file__).parent.parent / "preprocessed_db")
KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "knowledge-base"
COLLECTION_NAME = "docs"
EMBEDDING_MODEL = "text-embedding-3-large"

# Section chunk size. 10-K Items vary wildly in length:
#   Item 1 Business: a few thousand to 30k+ words
#   Item 1A Risk Factors: routinely 20k–50k words
#   Item 7 MD&A: 10k–40k words
# We split anything longer than this into overlapping recursive chunks.
SECTION_CHUNK_SIZE = 1200
SECTION_CHUNK_OVERLAP = 200

# Embedding API limits
EMBEDDING_BATCH_SIZE = 100  # well under the 2048 limit; keeps requests snappy

openai = OpenAI()
wait = wait_exponential(multiplier=1, min=10, max=240)


# Matches "## 1A_RiskFactors", "## 7_MDA", etc. (written by fetch_filings.py)
SECTION_HEADER_RE = re.compile(r"^##\s+([\w-]+)\s*$", re.MULTILINE)


def parse_front_matter(text: str) -> tuple[dict, str]:
    """
    Pull the metadata header that fetch_filings.py wrote at the top of each
    file. Returns (metadata_dict, body_after_header).
    """
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
    """
    Split a 10-K body (one with ## section headers) into (section_name, text) pairs.
    If no headers are found (the markdown fallback case in fetch_filings),
    returns [("full_document", body)].
    """
    matches = list(SECTION_HEADER_RE.finditer(body))
    if not matches:
        return [("full_document", body.strip())]

    sections = []
    for i, m in enumerate(matches):
        section_name = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        section_text = body[start:end].strip()
        if section_text:
            sections.append((section_name, section_text))
    return sections


def chunk_filing(file_path: Path) -> list[dict]:
    """
    Read one filing and return a list of chunk dicts:
        {"text": str, "metadata": dict}
    """
    text = file_path.read_text(encoding="utf-8")
    front, body = parse_front_matter(text)

    # Filename pattern: knowledge-base/<sector>/<TICKER>/<YEAR>_10-K.md
    parts = file_path.parts
    sector = parts[-3]
    ticker = parts[-2]
    year_match = re.match(r"(\d{4})", file_path.stem)
    year = int(year_match.group(1)) if year_match else 0

    base_metadata = {
        "source": str(file_path.relative_to(KNOWLEDGE_BASE_PATH.parent)),
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
        # Skip trivial sections — common for "Item 1B Unresolved Staff Comments"
        if len(section_text) < 50:
            continue

        sub_chunks = splitter.split_text(section_text)
        for i, sub in enumerate(sub_chunks):
            # Prepend a context line so each chunk is self-describing.
            # This helps the embedding model and also gives the LLM useful
            # context when the chunk is later assembled into the prompt.
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


def chunk_all_filings() -> list[dict]:
    """Walk knowledge-base/ and chunk S&P 500 .md files only."""
    from .sp500_tickers import allowed_tickers

    allowed = allowed_tickers()
    files = sorted(
        fp
        for fp in KNOWLEDGE_BASE_PATH.rglob("*_10-K.md")
        if fp.parent.name in allowed
    )
    print(f"Found {len(files)} S&P 500 filings to chunk.")

    all_chunks = []
    for fp in tqdm(files, desc="Chunking"):
        try:
            all_chunks.extend(chunk_filing(fp))
        except Exception as e:
            print(f"  Failed to chunk {fp}: {e}")
    print(f"Produced {len(all_chunks)} chunks.")
    return all_chunks


@retry(wait=wait)
def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts with retry on rate limits."""
    response = openai.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [d.embedding for d in response.data]


def embed_chunks(chunks: list[dict]) -> list[list[float]]:
    """Embed all chunks in batches with a progress bar."""
    vectors = []
    for i in tqdm(range(0, len(chunks), EMBEDDING_BATCH_SIZE), desc="Embedding"):
        batch = chunks[i : i + EMBEDDING_BATCH_SIZE]
        texts = [c["text"] for c in batch]
        vectors.extend(embed_batch(texts))
    return vectors


def write_to_chroma(chunks: list[dict], vectors: list[list[float]]) -> None:
    """Write chunks + embeddings to Chroma, replacing any existing collection."""
    chroma = PersistentClient(path=DB_NAME)
    if COLLECTION_NAME in [c.name for c in chroma.list_collections()]:
        print("Deleting existing collection...")
        chroma.delete_collection(COLLECTION_NAME)

    collection = chroma.get_or_create_collection(COLLECTION_NAME)

    # Chroma writes ~5k records per .add() call comfortably. For ~500 filings
    # we expect ~50k-150k chunks, so we batch the writes too.
    WRITE_BATCH = 1000
    for i in tqdm(range(0, len(chunks), WRITE_BATCH), desc="Writing to Chroma"):
        batch = chunks[i : i + WRITE_BATCH]
        batch_vectors = vectors[i : i + WRITE_BATCH]
        ids = [str(i + j) for j in range(len(batch))]
        docs = [c["text"] for c in batch]
        metas = [c["metadata"] for c in batch]
        collection.add(ids=ids, embeddings=batch_vectors, documents=docs, metadatas=metas)

    print(f"Vector store contains {collection.count()} chunks.")


def main():
    chunks = chunk_all_filings()
    if not chunks:
        print("No chunks produced. Did you run fetch_filings.py first?")
        return
    vectors = embed_chunks(chunks)
    write_to_chroma(chunks, vectors)
    print("Ingestion complete.")


if __name__ == "__main__":
    main()
