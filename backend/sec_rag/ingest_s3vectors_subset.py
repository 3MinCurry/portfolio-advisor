#!/usr/bin/env python3
"""
Ingest eval tickers into S3 Vectors (SageMaker embeddings) — cloud counterpart to ingest_chroma_subset.py.

Default: GE, HD, GOOGL, SHW (same 20 questions in evaluation/tests.json).

Usage:
    cd backend/sec_rag
    uv sync
    uv run ingest_s3vectors_subset.py --max-chunks 50    # smoke
    uv run ingest_s3vectors_subset.py                     # full eval subset
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
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT.parents[2] / ".env", override=True)
sys.path.insert(0, str(ROOT))

from ingest_chroma_subset import DEFAULT_TICKERS, chunk_tickers  # noqa: E402
from paths import text_for_embedding  # noqa: E402

INDEX_NAME = "financial-research"


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="+", default=None, help="Ticker symbols to ingest")
    parser.add_argument(
        "--eval-full",
        action="store_true",
        help="Ingest all 27 tickers needed for evaluation/tests_full.json (150 Q)",
    )
    parser.add_argument("--max-chunks", type=int, default=None)
    args = parser.parse_args()

    if args.eval_full:
        from evaluation.test import eval_tickers_from_full

        tickers = eval_tickers_from_full()
        print(f"Eval-full mode: ingesting {len(tickers)} tickers for 150-question eval")
    elif args.tickers:
        tickers = {t.upper() for t in args.tickers}
    else:
        tickers = DEFAULT_TICKERS

    bucket = os.getenv("VECTOR_BUCKET")
    endpoint = os.getenv("SAGEMAKER_ENDPOINT", "alex-embedding-endpoint")
    region = os.getenv("DEFAULT_AWS_REGION", "us-east-1")

    if not bucket:
        print("Error: set VECTOR_BUCKET in .env", file=sys.stderr)
        sys.exit(1)

    chunks = chunk_tickers(tickers)
    if args.max_chunks:
        chunks = chunks[: args.max_chunks]

    print(f"Ingesting {len(chunks)} chunks → s3://{bucket}/{INDEX_NAME} (source_type=sec_10k)")

    sm = boto3.client("sagemaker-runtime", region_name=region)
    s3v = boto3.client("s3vectors", region_name=region)

    for chunk in tqdm(chunks, desc="S3 Vectors ingest"):
        text = chunk["text"]
        meta = {
            **chunk["metadata"],
            "text": text,
            "timestamp": datetime.now(UTC).isoformat(),
            "source_type": "sec_10k",
        }
        embedding = get_embedding(sm, endpoint, text_for_embedding(text))
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

    print("Cloud ingest complete.")


if __name__ == "__main__":
    main()
