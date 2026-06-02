"""Local chunk relevance test (no AWS required)."""

from pathlib import Path

from chunking import chunk_filing
from paths import KNOWLEDGE_BASE

CASES = [
    (
        "AAPL",
        Path("technology/AAPL/2024_10-K.md"),
        "Apple iPhone manufacturing supply chain China risk factors",
        ["iphone", "china"],
    ),
    (
        "NVDA",
        Path("technology/NVDA/2024_10-K.md"),
        "NVIDIA GPU data center artificial intelligence revenue",
        ["gpu", "data center", "artificial intelligence"],
    ),
    (
        "AAPL",
        Path("technology/AAPL/2024_10-K.md"),
        "Apple geographic segments Americas Europe Greater China",
        ["greater china", "americas"],
    ),
]


def main() -> None:
    print("=" * 70)
    print("LOCAL CHUNK RELEVANCE TEST (chunking quality, no embeddings)")
    print("=" * 70)

    passed = 0
    for expected, rel, query, keywords in CASES:
        chunks = chunk_filing(KNOWLEDGE_BASE / rel)
        q = query.lower()
        scored = []
        for chunk in chunks:
            text = chunk["text"].lower()
            q_words = [w for w in q.split() if len(w) > 3]
            overlap = sum(1 for w in q_words if w in text)
            kw_hits = sum(1 for k in keywords if k in text)
            scored.append((overlap + kw_hits * 2, chunk))

        scored.sort(key=lambda x: -x[0])
        top_score, top = scored[0]
        meta = top["metadata"]
        preview = top["text"][:200].replace("\n", " ")
        ok = meta["ticker"] == expected and any(k in top["text"].lower() for k in keywords)
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1

        print(f"\n{status} | {query[:55]}...")
        print(
            f"  top chunk: {meta['ticker']} {meta['filing_year']} "
            f"item={meta['item']} score={top_score}"
        )
        print(f"  preview: {preview}...")

    print("\n" + "=" * 70)
    print(f"Score: {passed}/{len(CASES)} — chunking preserves retrievable content")
    print("=" * 70)


if __name__ == "__main__":
    main()
