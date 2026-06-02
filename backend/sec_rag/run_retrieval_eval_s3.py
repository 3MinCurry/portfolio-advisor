#!/usr/bin/env python3
"""
Retrieval eval on AWS S3 Vectors (production path) — same MRR / nDCG / coverage as local eval.

Requires:
  - SageMaker embedding endpoint (terraform/2_sagemaker)
  - VECTOR_BUCKET with sec_10k chunks (run ingest_s3vectors_subset.py first)

Usage:
    cd backend/sec_rag
    uv run ingest_s3vectors_subset.py
    uv run run_retrieval_eval_s3.py
    uv run run_retrieval_eval_s3.py --limit 5
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import boto3
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT.parents[2] / ".env", override=True)
sys.path.insert(0, str(ROOT))

from evaluation.retrieval_metrics import RetrievedDoc, evaluate_retrieval_docs  # noqa: E402
from evaluation.test import load_tests  # noqa: E402
from implementation.sp500_tickers import allowed_tickers  # noqa: E402

INDEX_NAME = "financial-research"
TOP_K = 10


def _embed_query(text: str) -> list[float]:
    region = os.getenv("DEFAULT_AWS_REGION", "us-east-1")
    endpoint = os.getenv("SAGEMAKER_ENDPOINT", "alex-embedding-endpoint")
    client = boto3.client("sagemaker-runtime", region_name=region)
    response = client.invoke_endpoint(
        EndpointName=endpoint,
        ContentType="application/json",
        Body=json.dumps({"inputs": text}),
    )
    result = json.loads(response["Body"].read().decode())
    if isinstance(result, list) and result:
        if isinstance(result[0], list):
            return result[0][0] if isinstance(result[0][0], list) else result[0]
        return result[0]
    return result


def fetch_context_s3(question: str, k: int = TOP_K) -> list[RetrievedDoc]:
    """Semantic search on S3 Vectors — matches Reporter Lambda production path."""
    bucket = os.getenv("VECTOR_BUCKET")
    if not bucket:
        sts = boto3.client("sts")
        bucket = f"alex-vectors-{sts.get_caller_identity()['Account']}"

    region = os.getenv("DEFAULT_AWS_REGION", "us-east-1")
    s3v = boto3.client("s3vectors", region_name=region)

    embedding = _embed_query(question)
    response = s3v.query_vectors(
        vectorBucketName=bucket,
        indexName=INDEX_NAME,
        queryVector={"float32": embedding},
        topK=k,
        returnMetadata=True,
    )

    docs: list[RetrievedDoc] = []
    seen: set[str] = set()
    for vector in response.get("vectors", []):
        metadata = vector.get("metadata", {})
        if metadata.get("source_type") != "sec_10k":
            continue
        text = metadata.get("text", "")
        if not text or text in seen:
            continue
        seen.add(text)
        docs.append(RetrievedDoc(page_content=text, metadata=metadata))
    return docs


def _primary_ticker(test) -> str | None:
    sp500 = allowed_tickers()
    for kw in test.keywords:
        if kw in sp500:
            return kw
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if not os.getenv("VECTOR_BUCKET"):
        print("Error: set VECTOR_BUCKET in .env", file=sys.stderr)
        sys.exit(1)

    tests = load_tests()
    if args.limit:
        tests = tests[: args.limit]

    bucket = os.getenv("VECTOR_BUCKET")
    print("=" * 70)
    print(f"S3 Vectors retrieval eval — {len(tests)} questions")
    print(f"Bucket: {bucket}  Index: {INDEX_NAME}  (sec_10k only)")
    print("=" * 70)

    total_mrr = total_ndcg = total_cov = 0.0
    for i, test in enumerate(tests, 1):
        docs = fetch_context_s3(test.question, k=TOP_K)
        result = evaluate_retrieval_docs(test, docs, k=TOP_K)
        total_mrr += result.mrr
        total_ndcg += result.ndcg
        total_cov += result.keyword_coverage
        ticker = _primary_ticker(test) or "?"
        print(
            f"\n[{i}/{len(tests)}] ({ticker}) {test.question[:55]}..."
            f"\n  chunks={len(docs)}  MRR={result.mrr:.3f}  nDCG={result.ndcg:.3f}  "
            f"coverage={result.keyword_coverage:.0f}% "
            f"({result.keywords_found}/{result.total_keywords})"
        )

    n = len(tests)
    print("\n" + "=" * 70)
    print(f"Cloud average MRR:      {total_mrr / n:.3f}")
    print(f"Cloud average nDCG:     {total_ndcg / n:.3f}")
    print(f"Cloud average coverage: {total_cov / n:.1f}%")
    print("=" * 70)


if __name__ == "__main__":
    main()
