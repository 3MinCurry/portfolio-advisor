#!/usr/bin/env python3
"""
Build Chroma index for a subset of tickers (cheap local eval).

Default: GE, HD, GOOGL, SHW — the 4 companies in evaluation/tests.json.

Usage:
    cd backend/sec_rag
    uv sync --extra chroma
    uv run ingest_chroma_subset.py
    uv run ingest_chroma_subset.py --tickers AAPL NVDA
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT.parents[2] / ".env", override=True)
sys.path.insert(0, str(ROOT))

from implementation.ingest import (  # noqa: E402
    KNOWLEDGE_BASE_PATH,
    chunk_filing,
    embed_chunks,
    write_to_chroma,
)
from tqdm import tqdm  # noqa: E402

DEFAULT_TICKERS = {"GE", "HD", "GOOGL", "SHW"}


def chunk_tickers(tickers: set[str]) -> list[dict]:
    files = sorted(
        fp for fp in KNOWLEDGE_BASE_PATH.rglob("*.md") if fp.parent.name in tickers
    )
    if not files:
        raise FileNotFoundError(f"No filings found for tickers: {sorted(tickers)}")

    print(f"Chunking {len(files)} filings for {sorted(tickers)}...")
    chunks: list[dict] = []
    for fp in tqdm(files, desc="Chunking"):
        try:
            chunks.extend(chunk_filing(fp))
        except Exception as exc:
            print(f"  Failed {fp}: {exc}", file=sys.stderr)
    print(f"Produced {len(chunks)} chunks.")
    return chunks


def main() -> None:
    import os

    if not os.getenv("OPENAI_API_KEY"):
        print("Error: set OPENAI_API_KEY in the project root .env", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="+", default=None, help="Ticker symbols to ingest")
    parser.add_argument(
        "--eval-full",
        action="store_true",
        help="Ingest all 27 tickers needed for evaluation/tests_full.json (150 Q)",
    )
    args = parser.parse_args()

    if args.eval_full:
        from evaluation.test import eval_tickers_from_full

        tickers = eval_tickers_from_full()
        print(f"Eval-full mode: ingesting {len(tickers)} tickers for 150-question eval")
    elif args.tickers:
        tickers = {t.upper() for t in args.tickers}
    else:
        tickers = DEFAULT_TICKERS

    chunks = chunk_tickers(tickers)
    vectors = embed_chunks(chunks)
    write_to_chroma(chunks, vectors)
    print("Subset ingestion complete.")


if __name__ == "__main__":
    main()
