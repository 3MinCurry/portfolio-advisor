"""Retrieve SEC 10-K context for portfolio holdings."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env", override=True)

logger = logging.getLogger(__name__)


def _chroma_available() -> bool:
    try:
        try:
            from sec_rag.paths import IMPLEMENTATION, chroma_db_path
        except ImportError:
            from .paths import IMPLEMENTATION, chroma_db_path

        return chroma_db_path().exists() and (IMPLEMENTATION / "answer.py").exists()
    except Exception:
        return False


def _fetch_from_chroma(symbols: list[str]) -> str | None:
    """Use advanced local RAG (entity filter + rewrite + rerank) when Chroma DB exists."""
    if not _chroma_available():
        return None

    try:
        root = Path(__file__).resolve().parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))

        try:
            from .implementation.answer import fetch_context
        except ImportError:
            from implementation.answer import fetch_context  # type: ignore

        tickers = " ".join(symbols[:5])
        question = (
            f"Key business risks, competitive position, and recent financial themes "
            f"for {tickers} from SEC 10-K filings"
        )
        chunks = fetch_context(question)
        if not chunks:
            return None

        lines = []
        for chunk in chunks[:8]:
            meta = chunk.metadata
            header = (
                f"{meta.get('ticker', '?')} {meta.get('filing_year', '?')} 10-K "
                f"({meta.get('item', 'section')})"
            )
            preview = chunk.page_content[:400].replace("\n", " ")
            lines.append(f"- {header}: {preview}...")

        return "SEC 10-K context (advanced retrieval):\n" + "\n".join(lines)
    except Exception as exc:
        logger.warning("SEC RAG Chroma retrieval failed: %s", exc)
        return None


def _embed_query(text: str) -> list[float]:
    import boto3

    try:
        from sec_rag.paths import text_for_embedding
    except ImportError:
        from .paths import text_for_embedding

    region = os.getenv("DEFAULT_AWS_REGION", "us-east-1")
    endpoint = os.getenv("SAGEMAKER_ENDPOINT", "alex-embedding-endpoint")
    client = boto3.client("sagemaker-runtime", region_name=region)
    response = client.invoke_endpoint(
        EndpointName=endpoint,
        ContentType="application/json",
        Body=json.dumps({"inputs": text_for_embedding(text)}),
    )
    result = json.loads(response["Body"].read().decode())
    if isinstance(result, list) and result:
        if isinstance(result[0], list):
            return result[0][0] if isinstance(result[0][0], list) else result[0]
        return result[0]
    return result


def _fetch_from_s3_vectors(symbols: list[str]) -> str | None:
    """Search Alex S3 Vectors for 10-K chunks (works on Lambda after ingest)."""
    try:
        import boto3

        bucket = os.getenv("VECTOR_BUCKET")
        if not bucket:
            sts = boto3.client("sts")
            bucket = f"alex-vectors-{sts.get_caller_identity()['Account']}"

        region = os.getenv("DEFAULT_AWS_REGION", "us-east-1")
        s3v = boto3.client("s3vectors", region_name=region)

        lines: list[str] = []
        seen: set[str] = set()

        for symbol in symbols[:5]:
            query = f"{symbol} 10-K risk factors business overview financial performance"
            embedding = _embed_query(query)
            response = s3v.query_vectors(
                vectorBucketName=bucket,
                indexName="financial-research",
                queryVector={"float32": embedding},
                topK=3,
                returnMetadata=True,
            )

            for vector in response.get("vectors", []):
                metadata = vector.get("metadata", {})
                if metadata.get("source_type") != "sec_10k":
                    continue
                text = metadata.get("text", "")
                if not text or text in seen:
                    continue
                seen.add(text)

                ticker = metadata.get("ticker", symbol)
                year = metadata.get("filing_year", "")
                item = metadata.get("item", "")
                preview = text[:350].replace("\n", " ")
                lines.append(f"- {ticker} {year} ({item}): {preview}...")

        if not lines:
            return None
        return "SEC 10-K context (vector search):\n" + "\n".join(lines[:10])
    except Exception as exc:
        logger.warning("SEC RAG S3 retrieval failed: %s", exc)
        return None


def fetch_insights_for_holdings(symbols: list[str]) -> str:
    """
    Retrieve filing context for portfolio tickers.
    Prefers local Chroma (advanced RAG) when available; otherwise S3 Vectors.
    """
    if not symbols:
        return "No symbols provided for SEC filing lookup."

    mode = os.getenv("SEC_RAG_MODE", "auto").lower()
    chroma_result = None
    s3_result = None

    if mode in ("auto", "chroma"):
        chroma_result = _fetch_from_chroma(symbols)
    if mode in ("auto", "s3") and not chroma_result:
        s3_result = _fetch_from_s3_vectors(symbols)

    if chroma_result:
        return chroma_result
    if s3_result:
        return s3_result

    return (
        "SEC filing context unavailable — run sec_rag ingest (Chroma or S3 Vectors) "
        "or ingest market research via the standard pipeline."
    )
