"""Paths for SEC 10-K RAG — single self-contained module root."""

from pathlib import Path

SEC_RAG_ROOT = Path(__file__).resolve().parent

KNOWLEDGE_BASE = SEC_RAG_ROOT / "knowledge-base"
CHROMA_DB = SEC_RAG_ROOT / "preprocessed_db"
IMPLEMENTATION = SEC_RAG_ROOT / "implementation"
EVALUATION = SEC_RAG_ROOT / "evaluation"


def chroma_db_path() -> Path:
    return CHROMA_DB


# SageMaker all-MiniLM-L6-v2 max is 512 tokens. Dense SEC prose can exceed that
# below typical chunk sizes — truncate embedding input only, not stored metadata.
# 800 chars stays safely under 512 tokens for legal/financial text (~3-4 chars/token).
MINILM_MAX_EMBED_CHARS = 800


def text_for_embedding(text: str, max_chars: int = MINILM_MAX_EMBED_CHARS) -> str:
    """Return text safe for MiniLM embedding; full chunk text stays in metadata."""
    return text if len(text) <= max_chars else text[:max_chars]
