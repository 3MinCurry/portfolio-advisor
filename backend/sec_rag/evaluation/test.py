import json
from pathlib import Path
from pydantic import BaseModel, Field

TEST_FILE = str(Path(__file__).parent / "tests.json")
TEST_FILE_FULL = str(Path(__file__).parent / "tests_full.json")


class TestQuestion(BaseModel):
    """A test question with expected keywords and reference answer."""

    question: str = Field(description="The question to ask the RAG system")
    keywords: list[str] = Field(description="Keywords that must appear in retrieved context")
    reference_answer: str = Field(description="The reference answer for this question")
    category: str = Field(description="Question category (e.g., direct_fact, spanning, temporal)")


def load_tests(test_file: str | None = None) -> list[TestQuestion]:
    """Load test questions from JSON file (default: tests.json, 20 questions)."""
    path = test_file or TEST_FILE
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [TestQuestion(**item) for item in data]


def load_tests_full() -> list[TestQuestion]:
    """Load full eval set (150 questions, 27 tickers)."""
    return load_tests(TEST_FILE_FULL)


def eval_tickers_from_full() -> set[str]:
    """Tickers referenced in tests_full.json."""
    from implementation.sp500_tickers import allowed_tickers

    sp500 = allowed_tickers()
    tickers: set[str] = set()
    for test in load_tests_full():
        for kw in test.keywords:
            if kw in sp500:
                tickers.add(kw)
    return tickers