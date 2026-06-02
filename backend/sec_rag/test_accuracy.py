#!/usr/bin/env python3
"""
Accuracy smoke test for SEC RAG integration.

Ingests 2 filings (AAPL + NVDA 2024), runs targeted queries, checks ticker relevance.

Usage:
    cd backend/sec_rag
    uv run test_accuracy.py
    uv run test_accuracy.py --skip-ingest   # if already ingested
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import boto3
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env", override=True)

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

from chunking import chunk_filing

INDEX_NAME = "financial-research"
TEST_FILINGS = [
    Path("technology/AAPL/2024_10-K.md"),
    Path("technology/NVDA/2024_10-K.md"),
]

# Query -> expected ticker + keywords that should appear in top results
TEST_CASES = [
    {
        "query": "Apple iPhone manufacturing supply chain China risk factors",
        "expected_ticker": "AAPL",
        "keywords": ["iphone", "china", "apple"],
    },
    {
        "query": "NVIDIA GPU data center artificial intelligence revenue growth",
        "expected_ticker": "NVDA",
        "keywords": ["nvidia", "gpu", "data center"],
    },
    {
        "query": "What are Apple's reportable geographic segments Americas Europe Greater China",
        "expected_ticker": "AAPL",
        "keywords": ["greater china", "americas", "segment"],
    },
]


def get_embedding(client, endpoint: str, text: str) -> list[float]:
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


def ingest_test_filings(max_chunks_per_filing: int = 40) -> int:
    from paths import KNOWLEDGE_BASE

    bucket = os.getenv("VECTOR_BUCKET")
    endpoint = os.getenv("SAGEMAKER_ENDPOINT", "alex-embedding-endpoint")
    region = os.getenv("DEFAULT_AWS_REGION", "us-east-1")

    if not bucket:
        print("Error: VECTOR_BUCKET not set", file=sys.stderr)
        sys.exit(1)

    sm = boto3.client("sagemaker-runtime", region_name=region)
    s3v = boto3.client("s3vectors", region_name=region)

    total = 0
    for rel in TEST_FILINGS:
        path = KNOWLEDGE_BASE / rel
        if not path.exists():
            print(f"Missing filing: {path}", file=sys.stderr)
            continue

        chunks = chunk_filing(path)[:max_chunks_per_filing]
        print(f"Ingesting {len(chunks)} chunks from {rel}...")
        for chunk in chunks:
            meta = {
                **chunk["metadata"],
                "text": chunk["text"],
                "timestamp": datetime.now(UTC).isoformat(),
                "source_type": "sec_10k",
                "test_batch": "sec_rag_accuracy",
            }
            embedding = get_embedding(sm, endpoint, chunk["text"])
            s3v.put_vectors(
                vectorBucketName=bucket,
                indexName=INDEX_NAME,
                vectors=[
                    {
                        "key": str(uuid.uuid4()),
                        "data": {"float32": embedding},
                        "metadata": meta,
                    }
                ],
            )
            total += 1
    print(f"Ingested {total} test chunks.\n")
    return total


def search(query: str, top_k: int = 3) -> list[dict]:
    bucket = os.getenv("VECTOR_BUCKET")
    endpoint = os.getenv("SAGEMAKER_ENDPOINT", "alex-embedding-endpoint")
    region = os.getenv("DEFAULT_AWS_REGION", "us-east-1")

    sm = boto3.client("sagemaker-runtime", region_name=region)
    s3v = boto3.client("s3vectors", region_name=region)

    embedding = get_embedding(sm, endpoint, query)
    response = s3v.query_vectors(
        vectorBucketName=bucket,
        indexName=INDEX_NAME,
        queryVector={"float32": embedding},
        topK=top_k,
        returnDistance=True,
        returnMetadata=True,
    )
    return response.get("vectors", [])


def run_tests() -> int:
    passed = 0
    print("=" * 70)
    print("SEC RAG accuracy test (S3 Vectors + SageMaker embeddings)")
    print("=" * 70)

    for i, case in enumerate(TEST_CASES, 1):
        print(f"\nTest {i}: {case['query'][:60]}...")
        vectors = search(case["query"], top_k=3)

        if not vectors:
            print("  FAIL — no results")
            continue

        top = vectors[0]
        meta = top.get("metadata", {})
        ticker = meta.get("ticker", "")
        text = meta.get("text", "").lower()
        distance = top.get("distance", 1.0)
        score = 1 - distance

        ticker_ok = ticker == case["expected_ticker"]
        keyword_hits = sum(1 for kw in case["keywords"] if kw in text)
        keywords_ok = keyword_hits >= 1

        print(f"  Top result: {ticker} | similarity ~{score:.3f}")
        print(f"  Preview: {meta.get('text', '')[:180].replace(chr(10), ' ')}...")

        if ticker_ok and keywords_ok:
            print(f"  PASS — correct ticker + {keyword_hits}/{len(case['keywords'])} keywords")
            passed += 1
        elif ticker_ok:
            print(f"  PARTIAL — correct ticker but weak keyword match ({keyword_hits})")
            passed += 0.5
        else:
            print(f"  FAIL — expected {case['expected_ticker']}, got {ticker or 'unknown'}")

    print("\n" + "=" * 70)
    print(f"Score: {passed}/{len(TEST_CASES)} tests passed")
    print("=" * 70)

    # Also test integrated retrieval module
    print("\nIntegrated retrieval (fetch_insights_for_holdings):")
    os.environ["SEC_RAG_MODE"] = "s3"
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from sec_rag.retrieval import fetch_insights_for_holdings

    result = fetch_insights_for_holdings(["AAPL", "NVDA"])
    print(result[:800] + ("..." if len(result) > 800 else ""))

    return int(passed)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-ingest", action="store_true")
    parser.add_argument("--max-chunks", type=int, default=40)
    args = parser.parse_args()

    if not args.skip_ingest:
        ingest_test_filings(max_chunks_per_filing=args.max_chunks)

    score = run_tests()
    sys.exit(0 if score >= 2 else 1)


if __name__ == "__main__":
    main()
