#!/usr/bin/env python3
"""Remove knowledge-base folders for tickers not in the S&P 500 sample list."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from implementation.sp500_tickers import allowed_tickers, get_tickers  # noqa: E402

KNOWLEDGE_BASE = ROOT / "knowledge-base"


def main() -> None:
    parser = argparse.ArgumentParser(description="Prune non-S&P 500 tickers from knowledge-base")
    parser.add_argument("--dry-run", action="store_true", help="List removals without deleting")
    args = parser.parse_args()

    allowed = allowed_tickers()
    removed: list[str] = []

    for sector_dir in sorted(KNOWLEDGE_BASE.iterdir()):
        if not sector_dir.is_dir():
            continue
        for ticker_dir in sorted(sector_dir.iterdir()):
            if not ticker_dir.is_dir():
                continue
            ticker = ticker_dir.name
            if ticker not in allowed:
                removed.append(str(ticker_dir.relative_to(KNOWLEDGE_BASE)))
                if not args.dry_run:
                    shutil.rmtree(ticker_dir)

    kept = sum(1 for _ in KNOWLEDGE_BASE.rglob("*.md"))
    print(f"S&P 500 universe: {len(allowed)} tickers")
    print(f"Removed folders: {len(removed)}")
    for path in removed:
        print(f"  - {path}")
    if not removed:
        print("Knowledge base already S&P 500 only.")
    print(f"Remaining filings: {kept} markdown files")


if __name__ == "__main__":
    main()
