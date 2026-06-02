"""
RAG answer pipeline for SEC 10-K filings.

This is the consolidated version that combines everything we validated
in the v3 smoke test (37.5% accuracy on FinanceBench, vs. ~19% baseline).

Pipeline (per question):
    1. EXTRACT ENTITIES — pull tickers/years from the question via LLM.
    2. BUILD METADATA FILTER — Chroma `where` clause from extracted entities.
       Fiscal-year aware: a question about "FY2022" matches filings where
       filing_year is 2022 OR 2023 (since FY2022 reports get filed in 2023).
    3. REWRITE QUERY — LLM call to produce a sharper search query.
    4. RETRIEVE — 4 Chroma queries:
         - filtered original
         - filtered rewritten
         - unfiltered original
         - unfiltered rewritten
       Merged and deduped. The filtered passes give precision; the
       unfiltered passes are a safety net if entity extraction missed.
    5. RERANK — LLM re-orders the merged top-N for relevance.
    6. ANSWER — LLM answers using the top-K reranked chunks as context.

Public interface (unchanged from your earlier projects):
    answer_question(question: str, history: list[dict] = []) -> (answer, chunks)

That's what app.py and evaluator.py both call.

Debug logging:
    Set DEBUG_RETRIEVAL=1 in your environment (or in .env) to see what's
    happening at each stage:
        DEBUG_RETRIEVAL=1 python app.py
    Useful when retrieval is misbehaving — shows entities extracted, the
    rewritten query, and the number of chunks returned at each stage.
"""

from __future__ import annotations

import os
from pathlib import Path

from chromadb import PersistentClient
from dotenv import load_dotenv
from litellm import completion
from openai import OpenAI
from pydantic import BaseModel, Field
from tenacity import retry, wait_exponential

load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=True)

# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------

# All LLM calls go through OpenAI for now. If you later add Groq access,
# swap the four pipeline models to "groq/openai/gpt-oss-120b" or similar.
ANSWER_MODEL = "openai/gpt-4.1"     
RERANK_MODEL = "openai/gpt-4.1"      
REWRITE_MODEL = "openai/gpt-4.1-mini" 
ENTITY_MODEL = "openai/gpt-4.1-mini"   

EMBEDDING_MODEL = "text-embedding-3-large"

DB_NAME = str(Path(__file__).parent.parent / "preprocessed_db")
COLLECTION_NAME = "docs"

# Pull deep (20 candidates), then rerank to top 10.
RETRIEVAL_K = 20
FINAL_K = 10

DEBUG = os.getenv("DEBUG_RETRIEVAL", "").lower() in ("1", "true", "yes")


# ----------------------------------------------------------------------
# Globals — initialized lazily so importing this module doesn't fail if
# the DB doesn't exist yet.
# ----------------------------------------------------------------------

_openai: OpenAI | None = None
_collection = None
wait = wait_exponential(multiplier=1, min=10, max=240)


def _get_openai() -> OpenAI:
    global _openai
    if _openai is None:
        _openai = OpenAI()
    return _openai


def _get_collection():
    global _collection
    if _collection is None:
        chroma = PersistentClient(path=DB_NAME)
        _collection = chroma.get_or_create_collection(COLLECTION_NAME)
    return _collection


def _dbg(msg: str) -> None:
    if DEBUG:
        print(f"[retrieval] {msg}")


# ----------------------------------------------------------------------
# Data models
# ----------------------------------------------------------------------


class Result(BaseModel):
    page_content: str
    metadata: dict


class ExtractedEntities(BaseModel):
    """What the question is asking about, structurally."""

    tickers: list[str] = Field(
        default_factory=list,
        description=(
            "Stock ticker symbols mentioned or clearly implied (e.g. AAPL, MSFT). "
            "Empty list if the question is generic across companies."
        ),
    )
    fiscal_years: list[int] = Field(
        default_factory=list,
        description=(
            "Fiscal years mentioned (e.g. [2022], [2022, 2023]). "
            "Empty list if no year is specified."
        ),
    )


class RankOrder(BaseModel):
    order: list[int] = Field(
        description="The order of relevance of chunks, from most to least relevant, by chunk id."
    )


# ----------------------------------------------------------------------
# Prompts
# ----------------------------------------------------------------------


ENTITY_PROMPT = """Extract structured filters from this question about SEC 10-K filings.
Return ONLY the JSON object.

Rules for tickers:
- Extract a ticker only when the company is unambiguously named.
- "Apple" or "AAPL" -> AAPL
- "Microsoft" or "MSFT" -> MSFT
- "Amazon" or "AMZN" -> AMZN
- "JPMorgan", "JPMorgan Chase", "JPM" -> JPM
- "Johnson & Johnson", "JnJ", "J&J", "JNJ" -> JNJ
- "Google", "Alphabet" -> GOOGL
- "Meta", "Facebook" -> META
- "Tesla" -> TSLA
- "NVIDIA", "Nvidia" -> NVDA
- "General Electric", "GE" -> GE
- "Home Depot" -> HD
- "Sherwin-Williams", "Sherwin Williams" -> SHW
- Generic questions ("Which companies report the most...") -> []

Rules for fiscal_years:
- Only years explicitly mentioned.
- "FY2022", "fiscal 2022", "in 2022", "2022 annual report" -> [2022]
- "between 2021 and 2023" -> [2021, 2022, 2023]
- "last year", "recently" -> []

Question: {question}"""


REWRITE_PROMPT = """You will search a knowledge base of SEC 10-K filings to answer the user's question.

Conversation history so far:
{history}

User's current question:
{question}

Respond ONLY with a short, refined search query (a few words) most likely to surface
relevant content. Use precise financial vocabulary (GAAP terms where applicable).
Focus on entity names and key concepts. Do NOT use quotes."""


RERANK_SYSTEM_PROMPT = """You are a document re-ranker for a financial Q&A system over SEC 10-K filings.
You are given a question and a list of retrieved chunks. The chunks are roughly
ordered by relevance but you can improve on that.
Rank ALL the provided chunks from most to least relevant to the question.
Reply only with the JSON list of ranked chunk ids, nothing else."""


SYSTEM_PROMPT = """You are a knowledgeable financial analyst answering questions about publicly traded
US companies based on their SEC 10-K annual report filings.

The context below contains extracts from relevant 10-K filings. USE the numbers
and facts in the context. If the question asks for a ratio or comparison and the
inputs are present in the context, compute it. Cite the company and fiscal year
when stating figures. If something is genuinely not in the context, say so plainly.

Your answer will be evaluated for accuracy, relevance, and completeness, so make
sure it answers the question fully and only the question.

Context:
{context}"""


# ----------------------------------------------------------------------
# Pipeline steps
# ----------------------------------------------------------------------


@retry(wait=wait)
def extract_entities(question: str) -> ExtractedEntities:
    """
    Pull tickers and fiscal years out of the question so we can metadata-filter
    before doing semantic search. Returns empty ExtractedEntities on failure —
    we never want this step to break the whole pipeline.
    """
    try:
        response = completion(
            model=ENTITY_MODEL,
            messages=[{"role": "user", "content": ENTITY_PROMPT.format(question=question)}],
            response_format=ExtractedEntities,
        )
        return ExtractedEntities.model_validate_json(response.choices[0].message.content)
    except Exception as e:
        _dbg(f"extract_entities failed: {e}")
        return ExtractedEntities()


def build_where_clause(entities: ExtractedEntities) -> dict | None:
    """
    Translate extracted entities into a Chroma `where` filter.

    Fiscal-year handling: a FY2022 question can be answered by EITHER the
    filing made in 2022 (covering FY2021) OR the filing made in 2023
    (covering FY2022). So we include both possibilities.
    """
    clauses = []
    if entities.tickers:
        clauses.append({"ticker": {"$in": entities.tickers}})
    if entities.fiscal_years:
        # A FY2022 question matches filings where filing_year ∈ {2022, 2023}.
        years_inclusive = sorted(set(entities.fiscal_years + [y + 1 for y in entities.fiscal_years]))
        clauses.append({"filing_year": {"$in": years_inclusive}})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


@retry(wait=wait)
def rewrite_query(question: str, history: list[dict] | None = None) -> str:
    """Rewrite the user's question into a sharper search query."""
    history = history or []
    try:
        response = completion(
            model=REWRITE_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": REWRITE_PROMPT.format(history=history, question=question),
                }
            ],
        )
        return response.choices[0].message.content.strip().strip('"').strip("'")
    except Exception as e:
        _dbg(f"rewrite_query failed: {e}")
        return question


def _embed(text: str) -> list[float]:
    """Embed a single string with text-embedding-3-large."""
    openai = _get_openai()
    return openai.embeddings.create(model=EMBEDDING_MODEL, input=[text]).data[0].embedding


def _query_chroma(query_vector: list[float], where: dict | None, k: int) -> list[Result]:
    """Run one Chroma query, optionally with a metadata filter."""
    collection = _get_collection()
    kwargs = {"query_embeddings": [query_vector], "n_results": k}
    if where:
        kwargs["where"] = where
    results = collection.query(**kwargs)

    chunks = []
    if not results["documents"] or not results["documents"][0]:
        return chunks
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append(Result(page_content=doc, metadata=meta))
    return chunks


def merge_chunks(*chunk_lists: list[Result]) -> list[Result]:
    """Merge multiple chunk lists, deduping by page_content."""
    seen = set()
    merged = []
    for chunks in chunk_lists:
        for chunk in chunks:
            if chunk.page_content not in seen:
                seen.add(chunk.page_content)
                merged.append(chunk)
    return merged


def fetch_context_unranked(original_question: str, history: list[dict] | None = None) -> list[Result]:
    """
    Retrieve candidate chunks using:
      - the original question
      - a rewritten query
      - optional metadata filter from extracted entities
    Returns a deduped union (typically 20-80 candidates).
    """
    entities = extract_entities(original_question)
    where = build_where_clause(entities)
    _dbg(f"entities: tickers={entities.tickers} fiscal_years={entities.fiscal_years}")
    _dbg(f"where:    {where}")

    rewritten = rewrite_query(original_question, history)
    _dbg(f"rewritten: '{rewritten}'")

    qvec = _embed(original_question)
    rvec = _embed(rewritten)

    filtered_a = _query_chroma(qvec, where, RETRIEVAL_K) if where else []
    filtered_b = _query_chroma(rvec, where, RETRIEVAL_K) if where else []
    unfiltered_a = _query_chroma(qvec, None, RETRIEVAL_K)
    unfiltered_b = _query_chroma(rvec, None, RETRIEVAL_K)

    _dbg(
        f"retrieved: filtered={len(filtered_a)}+{len(filtered_b)} "
        f"unfiltered={len(unfiltered_a)}+{len(unfiltered_b)}"
    )

    merged = merge_chunks(filtered_a, filtered_b, unfiltered_a, unfiltered_b)
    _dbg(f"merged unique: {len(merged)} chunks")
    return merged


@retry(wait=wait)
def rerank(question: str, chunks: list[Result]) -> list[Result]:
    """
    LLM-based rerank. Falls back to the original order if anything goes wrong —
    we never want the reranker to break the pipeline.
    """
    if not chunks:
        return []

    user_prompt = (
        f"Question:\n\n{question}\n\n"
        "Order ALL chunks below by relevance, most relevant first. Include every id.\n\n"
        "Chunks:\n\n"
    )
    for i, chunk in enumerate(chunks):
        user_prompt += f"# CHUNK ID {i + 1}\n{chunk.page_content}\n\n"
    user_prompt += "Reply only with the list of ranked chunk ids."

    try:
        response = completion(
            model=RERANK_MODEL,
            messages=[
                {"role": "system", "content": RERANK_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format=RankOrder,
        )
        order = RankOrder.model_validate_json(response.choices[0].message.content).order
    except Exception as e:
        _dbg(f"rerank failed: {e} — using original order")
        return chunks

    # Defensive: ignore out-of-range ids if the LLM hallucinates.
    valid = [i for i in order if 1 <= i <= len(chunks)]
    seen = set()
    ranked = []
    for i in valid:
        if i not in seen:
            seen.add(i)
            ranked.append(chunks[i - 1])
    # Append any chunks the reranker missed, so we never lose information.
    for i, chunk in enumerate(chunks):
        if (i + 1) not in seen:
            ranked.append(chunk)
    return ranked


def fetch_context(question: str, history: list[dict] | None = None) -> list[Result]:
    """The full retrieve+rerank loop. Returns the top FINAL_K chunks."""
    candidates = fetch_context_unranked(question, history)
    ranked = rerank(question, candidates)
    _dbg(f"final top-{FINAL_K}: {len(ranked[:FINAL_K])} chunks")
    return ranked[:FINAL_K]


# ----------------------------------------------------------------------
# Final answer step
# ----------------------------------------------------------------------


def make_rag_messages(
    question: str, history: list[dict], chunks: list[Result]
) -> list[dict]:
    """Assemble the system + history + question messages with context."""
    context = "\n\n".join(
        (
            f"Extract from {chunk.metadata.get('source', 'unknown')} "
            f"({chunk.metadata.get('ticker', '?')} "
            f"{chunk.metadata.get('filing_year', '?')} 10-K "
            f"— {chunk.metadata.get('item', '?')}):\n"
            f"{chunk.page_content}"
        )
        for chunk in chunks
    )
    system_prompt = SYSTEM_PROMPT.format(context=context)
    return (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": question}]
    )


# @retry(wait=wait)
def answer_question(question: str, history: list[dict] | None = None) -> tuple[str, list[Result]]:
    """
    Answer a question using RAG.

    Returns:
        (answer_text, retrieved_chunks)

    Signature is unchanged from your earlier project, so app.py and
    evaluator.py both work without modification.
    """
    history = history or []
    chunks = fetch_context(question, history)
    messages = make_rag_messages(question, history, chunks)
    response = completion(model=ANSWER_MODEL, messages=messages)
    return response.choices[0].message.content, chunks