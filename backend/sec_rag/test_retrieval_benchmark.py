#!/usr/bin/env python3
"""
Run retrieval benchmark: MRR, nDCG, keyword coverage.

Loads questions from evaluation/tests.json (20 Q) or tests_full.json (150 Q),
runs each through retrieval, and prints per-question + aggregate metrics.

Usage:
    cd backend/sec_rag
    uv sync --extra chroma

    # Local Chroma + OpenAI (full RAG pipeline: filter, rewrite, rerank)
    uv run test_retrieval_benchmark.py
    uv run test_retrieval_benchmark.py --full
    uv run test_retrieval_benchmark.py --full --limit 5

    # Cloud S3 Vectors + SageMaker embeddings (production path)
    uv run test_retrieval_benchmark.py --backend s3
    uv run test_retrieval_benchmark.py --backend s3 --full

    # Save summary JSON
    uv run test_retrieval_benchmark.py --full --json-out results.json

Prerequisites:
    Chroma:  OPENAI_API_KEY + ingest_chroma_subset.py [--eval-full]
    S3:      AWS creds, VECTOR_BUCKET, SageMaker endpoint + ingest_s3vectors_subset.py [--eval-full]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT.parents[1] / ".env", override=True)
sys.path.insert(0, str(ROOT))

from evaluation.retrieval_backends import TOP_K, fetch_chroma_docs, fetch_s3_docs  # noqa: E402
from evaluation.retrieval_metrics import evaluate_retrieval_docs  # noqa: E402
from evaluation.test import TestQuestion, load_tests, load_tests_full  # noqa: E402
from paths import chroma_db_path  # noqa: E402


def _check_prerequisites(backend: str) -> None:
    if backend == "chroma":
        if not chroma_db_path().exists():
            print(
                "Error: Chroma DB not found. Run:\n"
                "  uv run ingest_chroma_subset.py           # 20-question set\n"
                "  uv run ingest_chroma_subset.py --eval-full  # 150-question set",
                file=sys.stderr,
            )
            sys.exit(1)
        if not os.getenv("OPENAI_API_KEY"):
            print("Error: set OPENAI_API_KEY in .env", file=sys.stderr)
            sys.exit(1)
    else:
        if not os.getenv("VECTOR_BUCKET"):
            print("Error: set VECTOR_BUCKET in .env", file=sys.stderr)
            sys.exit(1)


def _fetch(backend: str, question: str, k: int):
    if backend == "chroma":
        return fetch_chroma_docs(question, k=k)
    return fetch_s3_docs(question, k=k)


def _run_benchmark(
    tests: list[TestQuestion],
    backend: str,
    k: int,
    verbose: bool,
) -> dict:
    fetch_docs = _fetch
    totals = {"mrr": 0.0, "ndcg": 0.0, "coverage": 0.0}
    by_category: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0, 0])
    per_question: list[dict] = []

    for i, test in enumerate(tests, 1):
        docs = fetch_docs(backend, test.question, k)
        result = evaluate_retrieval_docs(test, docs, k=k)
        totals["mrr"] += result.mrr
        totals["ndcg"] += result.ndcg
        totals["coverage"] += result.keyword_coverage

        cat_stats = by_category[test.category]
        cat_stats[0] += result.mrr
        cat_stats[1] += result.ndcg
        cat_stats[2] += result.keyword_coverage
        cat_stats[3] += 1

        row = {
            "index": i,
            "category": test.category,
            "question": test.question,
            "chunks": len(docs),
            "mrr": round(result.mrr, 4),
            "ndcg": round(result.ndcg, 4),
            "keyword_coverage": round(result.keyword_coverage, 1),
            "keywords_found": result.keywords_found,
            "total_keywords": result.total_keywords,
        }
        per_question.append(row)

        if verbose:
            print(
                f"\n[{i}/{len(tests)}] ({test.category}) {test.question[:60]}..."
                f"\n  chunks={len(docs)}  MRR={result.mrr:.3f}  nDCG={result.ndcg:.3f}  "
                f"coverage={result.keyword_coverage:.0f}% "
                f"({result.keywords_found}/{result.total_keywords} keywords)"
            )

    n = len(tests)
    summary = {
        "backend": backend,
        "questions": n,
        "top_k": k,
        "average_mrr": round(totals["mrr"] / n, 4),
        "average_ndcg": round(totals["ndcg"] / n, 4),
        "average_keyword_coverage": round(totals["coverage"] / n, 1),
        "by_category": {
            cat: {
                "count": int(stats[3]),
                "average_mrr": round(stats[0] / stats[3], 4),
                "average_ndcg": round(stats[1] / stats[3], 4),
                "average_keyword_coverage": round(stats[2] / stats[3], 1),
            }
            for cat, stats in sorted(by_category.items())
        },
        "per_question": per_question,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieval benchmark (MRR, nDCG, keyword coverage)")
    parser.add_argument(
        "--backend",
        choices=("chroma", "s3"),
        default="chroma",
        help="chroma = local OpenAI+Chroma; s3 = SageMaker+S3 Vectors (default: chroma)",
    )
    parser.add_argument("--full", action="store_true", help="Use tests_full.json (150 questions)")
    parser.add_argument("--limit", type=int, default=None, help="Only run first N questions")
    parser.add_argument("--top-k", type=int, default=TOP_K, help=f"Chunks to retrieve (default {TOP_K})")
    parser.add_argument("--quiet", action="store_true", help="Only print summary")
    parser.add_argument("--json-out", type=str, default=None, help="Write summary JSON to this path")
    args = parser.parse_args()

    _check_prerequisites(args.backend)

    tests = load_tests_full() if args.full else load_tests()
    if args.limit:
        tests = tests[: args.limit]

    backend_label = {
        "chroma": "Chroma + OpenAI (filter, rewrite, rerank)",
        "s3": "S3 Vectors + SageMaker embeddings",
    }[args.backend]

    print("=" * 70)
    print(f"Retrieval benchmark — {len(tests)} questions")
    print(f"Backend: {backend_label}")
    print(f"Top-K: {args.top_k}")
    print("=" * 70)

    summary = _run_benchmark(tests, args.backend, args.top_k, verbose=not args.quiet)

    print("\n" + "=" * 70)
    print(f"Average MRR:      {summary['average_mrr']:.3f}")
    print(f"Average nDCG:     {summary['average_ndcg']:.3f}")
    print(f"Average coverage: {summary['average_keyword_coverage']:.1f}%")
    print("-" * 70)
    print("By category:")
    for cat, stats in summary["by_category"].items():
        print(
            f"  {cat:14s}  n={stats['count']:3d}  "
            f"MRR={stats['average_mrr']:.3f}  nDCG={stats['average_ndcg']:.3f}  "
            f"coverage={stats['average_keyword_coverage']:.1f}%"
        )
    print("=" * 70)

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
