"""
Fetch 10-K filings from SEC EDGAR using edgartools.

Downloads the last N years of 10-Ks for each ticker in sp500_tickers.py,
parses them into structured TenK objects, extracts the standard 10-K Items
(Business, Risk Factors, MD&A, Financial Statements, etc.), and writes one
Markdown file per filing to knowledge-base/<sector>/<TICKER>/<YEAR>.md.

The file layout matches `knowledge-base/<sector>/<TICKER>/<YEAR>.md` so ingest.py
and answer.py can consume a consistent directory structure.

Usage:
    python -m implementation.fetch_filings

Or with options:
    python -m implementation.fetch_filings --years 5 --max-companies 100
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm

from .sp500_tickers import get_tickers

load_dotenv(override=True)

KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "knowledge-base"


# Standard 10-K Items we care about. These are the sections that contain the
# most useful information for Q&A. Skipping exhibits, signatures, etc.
TENK_SECTIONS = [
    ("Item 1", "1_Business"),
    ("Item 1A", "1A_RiskFactors"),
    ("Item 1B", "1B_UnresolvedStaffComments"),
    ("Item 2", "2_Properties"),
    ("Item 3", "3_LegalProceedings"),
    ("Item 5", "5_MarketForRegistrants"),
    ("Item 6", "6_SelectedFinancialData"),
    ("Item 7", "7_MDA"),
    ("Item 7A", "7A_QuantitativeQualitativeMarketRisk"),
    ("Item 8", "8_FinancialStatements"),
    ("Item 9", "9_DisagreementsWithAccountants"),
    ("Item 9A", "9A_ControlsAndProcedures"),
]


def setup_edgar_identity() -> None:
    """
    SEC requires a User-Agent with your name and email.
    Set EDGAR_IDENTITY in .env as: "Your Name your.email@example.com"
    """
    identity = os.getenv("EDGAR_IDENTITY")
    if not identity:
        raise RuntimeError(
            "EDGAR_IDENTITY is not set. Add to the project root .env:\n"
            '  EDGAR_IDENTITY="Your Name your.email@example.com"\n'
            "The SEC requires this for all programmatic access to EDGAR."
        )
    from edgar import set_identity
    set_identity(identity)


def extract_filing_to_markdown(filing) -> str | None:
    """
    Parse a 10-K filing into Markdown. Tries the structured TenK object first
    (gives us nice per-Item sections); falls back to filing.markdown() if the
    structured parse fails — common for older or oddly-formatted filings.

    Returns Markdown string or None if extraction fails entirely.
    """
    try:
        tenk = filing.obj()  # Returns a TenK data object

        parts = []
        for item_key, section_name in TENK_SECTIONS:
            try:
                # edgartools exposes items via the [item_key] subscript on TenK
                content = tenk[item_key]
                if content and len(str(content).strip()) > 100:
                    parts.append(f"## {section_name}\n\n{content}\n")
            except (KeyError, AttributeError, Exception):
                # Some filings just don't have every item. Skip silently.
                continue

        if parts:
            return "\n".join(parts)
    except Exception as e:
        print(f"  TenK structured parse failed: {e}. Falling back to markdown.")

    # Fallback: raw markdown of the whole filing
    try:
        return filing.markdown()
    except Exception as e:
        print(f"  Markdown fallback also failed: {e}")
        return None


def fetch_company_filings(ticker: str, company_name: str, sector: str, years: int) -> int:
    """
    Fetch the last `years` 10-K filings for one company and write each to disk.
    Returns the number of filings successfully written.
    """
    from edgar import Company

    out_dir = KNOWLEDGE_BASE_PATH / sector / ticker
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        company = Company(ticker)
    except Exception as e:
        print(f"  Could not resolve ticker {ticker}: {e}")
        return 0

    try:
        filings = company.get_filings(form="10-K").head(years)
    except Exception as e:
        print(f"  Could not list filings for {ticker}: {e}")
        return 0

    written = 0
    for filing in filings:
        try:
            # filing.filing_date is a datetime.date
            year = filing.filing_date.year
        except Exception:
            year = "unknown"

        out_path = out_dir / f"{year}_10-K.md"
        if out_path.exists() and out_path.stat().st_size > 1000:
            # Already have it. Skip to keep re-runs cheap.
            written += 1
            continue

        content = extract_filing_to_markdown(filing)
        if not content:
            continue

        # Front-matter header so the ingestion step has rich metadata
        try:
            accession = filing.accession_number
        except Exception:
            accession = "unknown"
        try:
            filed = filing.filing_date.isoformat()
        except Exception:
            filed = "unknown"

        header = (
            f"# {company_name} ({ticker}) — 10-K Annual Report ({year})\n\n"
            f"- Ticker: {ticker}\n"
            f"- Company: {company_name}\n"
            f"- Sector: {sector}\n"
            f"- Filing year: {year}\n"
            f"- Filing date: {filed}\n"
            f"- Accession number: {accession}\n\n"
            "---\n\n"
        )

        out_path.write_text(header + content, encoding="utf-8")
        written += 1

        # Be polite to SEC servers — they ask for <= 10 req/sec.
        # edgartools rate-limits internally, but a small sleep doesn't hurt.
        time.sleep(0.1)

    return written


def main():
    parser = argparse.ArgumentParser(description="Fetch SEC 10-K filings.")
    parser.add_argument("--years", type=int, default=5, help="Years of 10-Ks per company.")
    parser.add_argument(
        "--max-companies",
        type=int,
        default=None,
        help="Limit number of companies (useful for testing).",
    )
    args = parser.parse_args()

    setup_edgar_identity()

    tickers = get_tickers()
    if args.max_companies:
        tickers = tickers[: args.max_companies]

    print(f"Fetching up to {args.years} years of 10-Ks for {len(tickers)} companies.")
    print(f"Writing to: {KNOWLEDGE_BASE_PATH}\n")

    total_filings = 0
    failed = []
    for ticker, company_name, sector in tqdm(tickers, desc="Companies"):
        try:
            count = fetch_company_filings(ticker, company_name, sector, args.years)
            total_filings += count
            if count == 0:
                failed.append(ticker)
        except Exception as e:
            print(f"\n{ticker}: unexpected error: {e}")
            failed.append(ticker)

    print(f"\nDone. Wrote {total_filings} filings across {len(tickers) - len(failed)} companies.")
    if failed:
        print(f"Failed ({len(failed)}): {', '.join(failed)}")


if __name__ == "__main__":
    main()
