"""Paths for SEC 10-K RAG — single self-contained module root."""

from pathlib import Path

SEC_RAG_ROOT = Path(__file__).resolve().parent

KNOWLEDGE_BASE = SEC_RAG_ROOT / "knowledge-base"
CHROMA_DB = SEC_RAG_ROOT / "preprocessed_db"
IMPLEMENTATION = SEC_RAG_ROOT / "implementation"
EVALUATION = SEC_RAG_ROOT / "evaluation"


def chroma_db_path() -> Path:
    return CHROMA_DB
