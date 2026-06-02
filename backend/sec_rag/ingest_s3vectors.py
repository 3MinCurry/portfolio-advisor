#!/usr/bin/env python3
"""
Chunk SEC 10-K filings and ingest into Alex S3 Vectors (SageMaker embeddings).

Usage:
    cd backend/sec_rag
    uv run ingest_s3vectors.py --limit-files 10 --max-chunks 50   # smoke test
    uv run ingest_s3vectors.py                                     # full ingest (slow)
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
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT.parents[2] / ".env", override=True)

from chunking import chunk_all_filings

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
    parser = argparse.ArgumentParser(description="Ingest SEC 10-K chunks into S3 Vectors")
    parser.add_argument("--limit-files", type=int, default=None, help="Limit number of filings")
    parser.add_argument("--max-chunks", type=int, default=None, help="Limit total chunks ingested")
    args = parser.parse_args()

    bucket = os.getenv("VECTOR_BUCKET")
    endpoint = os.getenv("SAGEMAKER_ENDPOINT", "alex-embedding-endpoint")
    region = os.getenv("DEFAULT_AWS_REGION", "us-east-1")

    if not bucket:
        print("Error: set VECTOR_BUCKET in .env", file=sys.stderr)
        sys.exit(1)

    print(f"Chunking filings from knowledge-base (limit_files={args.limit_files})...")
    chunks = chunk_all_filings(limit_files=args.limit_files)
    if args.max_chunks:
        chunks = chunks[: args.max_chunks]
    print(f"Ingesting {len(chunks)} chunks into {bucket}/{INDEX_NAME}")

    sm = boto3.client("sagemaker-runtime", region_name=region)
    s3v = boto3.client("s3vectors", region_name=region)

    for chunk in tqdm(chunks, desc="Ingesting"):
        text = chunk["text"]
        meta = {
            **chunk["metadata"],
            "text": text,
            "timestamp": datetime.now(UTC).isoformat(),
            "source_type": "sec_10k",
        }
        embedding = get_embedding(sm, endpoint, text)
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

    print("Done.")


if __name__ == "__main__":
    main()
