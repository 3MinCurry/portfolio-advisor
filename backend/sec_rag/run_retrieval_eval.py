#!/usr/bin/env python3
"""
Run retrieval accuracy eval locally (MRR, nDCG, keyword coverage).

Requires Chroma index at backend/sec_rag/preprocessed_db (run ingest_chroma_subset.py first).

Usage:
    cd backend/sec_rag
    uv sync --extra chroma
    uv run run_retrieval_eval.py
    uv run run_retrieval_eval.py --limit 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT.parents[1] / ".env", override=True)
sys.path.insert(0, str(ROOT))

from paths import chroma_db_path  # noqa: E402
from evaluation.eval import evaluate_retrieval  # noqa: E402
from evaluation.test import load_tests, load_tests_full  # noqa: E402


def main() -> None:
    import os

    db = chroma_db_path()
    if not db.exists():
        print("Error: Chroma DB not found. Run: uv run ingest_chroma_subset.py", file=sys.stderr)
        sys.exit(1)
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: set OPENAI_API_KEY in the project root .env", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Only run first N tests")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Use evaluation/tests_full.json (150 questions, 27 tickers)",
    )
    args = parser.parse_args()

    tests = load_tests_full() if args.full else load_tests()
    if args.limit:
        tests = tests[: args.limit]

    print("=" * 70)
    print(f"Retrieval eval — {len(tests)} questions (Chroma: {db})")
    print("=" * 70)

    total_mrr = total_ndcg = total_cov = 0.0
    for i, test in enumerate(tests, 1):
        result = evaluate_retrieval(test)
        total_mrr += result.mrr
        total_ndcg += result.ndcg
        total_cov += result.keyword_coverage
        print(
            f"\n[{i}/{len(tests)}] {test.question[:65]}..."
            f"\n  MRR={result.mrr:.3f}  nDCG={result.ndcg:.3f}  "
            f"coverage={result.keyword_coverage:.0f}% "
            f"({result.keywords_found}/{result.total_keywords} keywords)"
        )

    n = len(tests)
    print("\n" + "=" * 70)
    print(f"Average MRR:      {total_mrr / n:.3f}")
    print(f"Average nDCG:     {total_ndcg / n:.3f}")
    print(f"Average coverage: {total_cov / n:.1f}%")
    print("=" * 70)


if __name__ == "__main__":
    main()
