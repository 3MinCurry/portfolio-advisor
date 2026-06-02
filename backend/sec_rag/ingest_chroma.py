#!/usr/bin/env python3
"""
Build local Chroma index for advanced SEC RAG (rewrite + rerank).

Usage:
    cd backend/sec_rag
    uv sync --extra chroma
    uv run ingest_chroma.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env", override=True)

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from implementation.ingest import main  # noqa: E402

if __name__ == "__main__":
    main()
