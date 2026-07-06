"""Retrieval backends for benchmark eval (Chroma local vs S3 Vectors cloud)."""

from __future__ import annotations

import json
import os

import boto3

from evaluation.retrieval_metrics import RetrievedDoc

INDEX_NAME = "financial-research"
TOP_K = 10


def fetch_chroma_docs(question: str, k: int = TOP_K) -> list[RetrievedDoc]:
    from implementation.answer import fetch_context

    chunks = fetch_context(question)
    return [
        RetrievedDoc(page_content=chunk.page_content, metadata=chunk.metadata)
        for chunk in chunks[:k]
    ]


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


def fetch_s3_docs(question: str, k: int = TOP_K) -> list[RetrievedDoc]:
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
