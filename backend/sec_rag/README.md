# SEC 10-K RAG

Self-contained RAG module for Alex: SEC filing knowledge base, retrieval pipeline, eval metrics, and AWS ingest. Integrated with the **Reporter** agent for portfolio analysis.

## Folder layout

```
backend/sec_rag/
├── README.md
├── pyproject.toml            # dependencies (uv)
├── knowledge-base/           # SEC 10-K filings for 104 S&P 500 sample tickers
├── implementation/
│   ├── sp500_tickers.py      # canonical list of 104 S&P 500 tickers
│   ├── ingest.py             # chunk + embed → Chroma
│   ├── answer.py             # entity filter, rewrite, rerank, answer
│   └── fetch_filings.py      # download new 10-Ks from SEC (S&P 500 only)
├── prune_knowledge_base.py   # remove demo folders + non-S&P 500 tickers
├── evaluation/               # retrieval & answer metrics
│   ├── tests.json            # 20-question eval set (GE, HD, GOOGL, SHW)
│   └── eval.py               # MRR, nDCG, LLM-judge scoring
├── preprocessed_db/          # local Chroma index (gitignored, created by ingest)
├── app.py                    # Gradio chat UI (optional)
│
├── ingest_chroma_subset.py   # local: Chroma index (eval tickers)
├── ingest_s3vectors_subset.py  # cloud: S3 Vectors index (same tickers)
├── ingest_chroma.py          # full Chroma ingest (all filings)
├── ingest_s3vectors.py       # full S3 ingest (all filings)
├── run_retrieval_eval.py     # metrics: local Chroma path
├── run_retrieval_eval_s3.py  # metrics: cloud S3 Vectors path
├── test_local_chunks.py      # chunking sanity check
├── retrieval.py              # used by Reporter (Chroma or S3)
├── chunking.py               # shared chunking for S3 ingest
└── paths.py                  # path constants
```

## Local vs cloud

| | **Local (development)** | **Cloud (production)** |
|---|---|---|
| **Ingest** | `ingest_chroma_subset.py` | `ingest_s3vectors_subset.py` |
| **Storage** | `preprocessed_db/` (Chroma) | S3 Vectors (`VECTOR_BUCKET`) |
| **Embeddings** | OpenAI | SageMaker |
| **Retrieval** | Advanced (filter, rewrite, rerank) | Semantic top-K (Reporter Lambda) |
| **Eval** | `run_retrieval_eval.py` | `run_retrieval_eval_s3.py` |

```powershell
# Local
cd backend\sec_rag
uv sync --extra chroma
uv run ingest_chroma_subset.py
uv run run_retrieval_eval.py

# Cloud (same 20-question eval set)
uv sync
uv run ingest_s3vectors_subset.py
uv run run_retrieval_eval_s3.py
```

On AWS, agents use S3 Vectors automatically (`SEC_RAG_MODE=auto` skips local Chroma when the index is absent).

## Quick start (local)

```powershell
cd backend\sec_rag
uv sync --extra chroma
```

Add `OPENAI_API_KEY` to the project root `.env`, then:

```powershell
# Build embeddings (GE, HD, GOOGL, SHW — ~15–30 min)
uv run ingest_chroma_subset.py

# Run retrieval metrics
uv run test_retrieval_benchmark.py
# or: uv run run_retrieval_eval.py

# Optional: interactive Q&A
uv pip install gradio
uv run app.py
```

## Evaluation

| Script | Path | Output |
|--------|------|--------|
| `test_retrieval_benchmark.py` | Chroma or S3, 20 or 150 questions | MRR, nDCG, coverage + per-category breakdown |
| `run_retrieval_eval.py` | Local Chroma | MRR, nDCG, coverage (20 Q) |
| `run_retrieval_eval_s3.py` | S3 Vectors | Same metrics on cloud index |
| `python -m evaluation.eval 0` | Per-question retrieval + answer scores /5 |
| `evaluation/evaluator.py` | Gradio dashboard for retrieval + answer eval |

## AWS path (production)

Local Chroma is for development and evaluation only. Production uses:

```
ingest_s3vectors.py  →  SageMaker embeddings  →  S3 Vectors  →  Reporter Lambda
```

Requires `VECTOR_BUCKET` and `SAGEMAKER_ENDPOINT` in `.env`.

```powershell
uv run ingest_s3vectors.py --limit-files 20 --max-chunks 200
```

Set `SEC_RAG_MODE=s3` to force S3 retrieval (skip Chroma).

## Alex integration

The **Reporter** agent calls `sec_rag.retrieval.fetch_insights_for_holdings()`:

1. SEC 10-K context (Chroma locally, or S3 Vectors in production)
2. General market research from S3 Vectors (Researcher-ingested web content)

The **Researcher** agent browses the web and **writes** to S3 Vectors — it does not read from this module.

## Environment

From the project root `.env`:

```env
OPENAI_API_KEY=sk-...          # required for local Chroma ingest + eval
SEC_RAG_MODE=auto              # auto | chroma | s3
VECTOR_BUCKET=...              # AWS path only
SAGEMAKER_ENDPOINT=...         # AWS path only
```
