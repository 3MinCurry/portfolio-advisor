#!/usr/bin/env python3
"""Remove non-SEC demo folders and tickers outside the S&P 500 sample list."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from implementation.sp500_tickers import allowed_sectors, allowed_tickers  # noqa: E402

KNOWLEDGE_BASE = ROOT / "knowledge-base"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prune demo folders and non-S&P 500 tickers from knowledge-base"
    )
    parser.add_argument("--dry-run", action="store_true", help="List removals without deleting")
    args = parser.parse_args()

    allowed = allowed_tickers()
    sectors = allowed_sectors()
    removed: list[str] = []

    for top_dir in sorted(KNOWLEDGE_BASE.iterdir()):
        if not top_dir.is_dir():
            continue

        if top_dir.name not in sectors:
            removed.append(str(top_dir.relative_to(KNOWLEDGE_BASE)))
            if not args.dry_run:
                shutil.rmtree(top_dir)
            continue

        for ticker_dir in sorted(top_dir.iterdir()):
            if not ticker_dir.is_dir():
                continue
            if ticker_dir.name not in allowed:
                removed.append(str(ticker_dir.relative_to(KNOWLEDGE_BASE)))
                if not args.dry_run:
                    shutil.rmtree(ticker_dir)

    ten_k_count = sum(1 for _ in KNOWLEDGE_BASE.rglob("*_10-K.md"))
    print(f"S&P 500 universe: {len(allowed)} tickers across {len(sectors)} sectors")
    print(f"Removed paths: {len(removed)}")
    for path in removed:
        print(f"  - {path}")
    if not removed:
        print("Knowledge base already clean (SEC 10-K only, S&P 500 tickers).")
    print(f"Remaining 10-K filings: {ten_k_count}")


if __name__ == "__main__":
    main()
