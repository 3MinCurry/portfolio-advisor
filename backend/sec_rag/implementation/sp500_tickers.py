"""
Curated list of ~100 S&P 500 tickers spread across GICS sectors.
Picked to give a good mix for the RAG demo without being huge.

The official S&P 500 list lives at:
https://en.wikipedia.org/wiki/List_of_S%26P_500_companies
or you can pull it programmatically with pandas.read_html(...).
"""

SP500_SAMPLE: list[tuple[str, str, str]] = [
    # (ticker, company name, GICS sector)
    # Technology
    ("AAPL", "Apple Inc.", "technology"),
    ("MSFT", "Microsoft Corporation", "technology"),
    ("NVDA", "NVIDIA Corporation", "technology"),
    ("ORCL", "Oracle Corporation", "technology"),
    ("CRM", "Salesforce Inc.", "technology"),
    ("ADBE", "Adobe Inc.", "technology"),
    ("AMD", "Advanced Micro Devices", "technology"),
    ("INTC", "Intel Corporation", "technology"),
    ("CSCO", "Cisco Systems", "technology"),
    ("IBM", "IBM Corporation", "technology"),
    ("QCOM", "Qualcomm Inc.", "technology"),
    ("TXN", "Texas Instruments", "technology"),
    ("AVGO", "Broadcom Inc.", "technology"),
    ("NOW", "ServiceNow Inc.", "technology"),
    ("INTU", "Intuit Inc.", "technology"),
    # Communication Services
    ("GOOGL", "Alphabet Inc.", "communication_services"),
    ("META", "Meta Platforms Inc.", "communication_services"),
    ("NFLX", "Netflix Inc.", "communication_services"),
    ("DIS", "Walt Disney Company", "communication_services"),
    ("CMCSA", "Comcast Corporation", "communication_services"),
    ("T", "AT&T Inc.", "communication_services"),
    ("VZ", "Verizon Communications", "communication_services"),
    # Consumer Discretionary
    ("AMZN", "Amazon.com Inc.", "consumer_discretionary"),
    ("TSLA", "Tesla Inc.", "consumer_discretionary"),
    ("HD", "Home Depot Inc.", "consumer_discretionary"),
    ("MCD", "McDonald's Corporation", "consumer_discretionary"),
    ("NKE", "Nike Inc.", "consumer_discretionary"),
    ("SBUX", "Starbucks Corporation", "consumer_discretionary"),
    ("LOW", "Lowe's Companies", "consumer_discretionary"),
    ("TJX", "TJX Companies", "consumer_discretionary"),
    ("BKNG", "Booking Holdings", "consumer_discretionary"),
    # Consumer Staples
    ("WMT", "Walmart Inc.", "consumer_staples"),
    ("PG", "Procter & Gamble", "consumer_staples"),
    ("KO", "Coca-Cola Company", "consumer_staples"),
    ("PEP", "PepsiCo Inc.", "consumer_staples"),
    ("COST", "Costco Wholesale", "consumer_staples"),
    ("PM", "Philip Morris International", "consumer_staples"),
    ("MDLZ", "Mondelez International", "consumer_staples"),
    ("CL", "Colgate-Palmolive", "consumer_staples"),
    # Financials
    ("JPM", "JPMorgan Chase & Co.", "financials"),
    ("BAC", "Bank of America", "financials"),
    ("WFC", "Wells Fargo & Company", "financials"),
    ("GS", "Goldman Sachs Group", "financials"),
    ("MS", "Morgan Stanley", "financials"),
    ("C", "Citigroup Inc.", "financials"),
    ("AXP", "American Express", "financials"),
    ("BLK", "BlackRock Inc.", "financials"),
    ("SCHW", "Charles Schwab", "financials"),
    ("V", "Visa Inc.", "financials"),
    ("MA", "Mastercard Inc.", "financials"),
    ("BRK-B", "Berkshire Hathaway", "financials"),
    # Healthcare
    ("JNJ", "Johnson & Johnson", "healthcare"),
    ("UNH", "UnitedHealth Group", "healthcare"),
    ("PFE", "Pfizer Inc.", "healthcare"),
    ("MRK", "Merck & Co.", "healthcare"),
    ("ABBV", "AbbVie Inc.", "healthcare"),
    ("LLY", "Eli Lilly and Company", "healthcare"),
    ("TMO", "Thermo Fisher Scientific", "healthcare"),
    ("ABT", "Abbott Laboratories", "healthcare"),
    ("DHR", "Danaher Corporation", "healthcare"),
    ("BMY", "Bristol-Myers Squibb", "healthcare"),
    ("AMGN", "Amgen Inc.", "healthcare"),
    ("CVS", "CVS Health", "healthcare"),
    # Industrials
    ("BA", "Boeing Company", "industrials"),
    ("CAT", "Caterpillar Inc.", "industrials"),
    ("GE", "General Electric", "industrials"),
    ("HON", "Honeywell International", "industrials"),
    ("UPS", "United Parcel Service", "industrials"),
    ("LMT", "Lockheed Martin", "industrials"),
    ("RTX", "RTX Corporation", "industrials"),
    ("DE", "Deere & Company", "industrials"),
    ("UNP", "Union Pacific", "industrials"),
    ("MMM", "3M Company", "industrials"),
    ("FDX", "FedEx Corporation", "industrials"),
    # Energy
    ("XOM", "Exxon Mobil", "energy"),
    ("CVX", "Chevron Corporation", "energy"),
    ("COP", "ConocoPhillips", "energy"),
    ("SLB", "Schlumberger Limited", "energy"),
    ("EOG", "EOG Resources", "energy"),
    ("PSX", "Phillips 66", "energy"),
    # Utilities
    ("NEE", "NextEra Energy", "utilities"),
    ("DUK", "Duke Energy", "utilities"),
    ("SO", "Southern Company", "utilities"),
    ("D", "Dominion Energy", "utilities"),
    # Materials
    ("LIN", "Linde plc", "materials"),
    ("APD", "Air Products and Chemicals", "materials"),
    ("SHW", "Sherwin-Williams", "materials"),
    ("ECL", "Ecolab Inc.", "materials"),
    ("FCX", "Freeport-McMoRan", "materials"),
    # Real Estate
    ("PLD", "Prologis Inc.", "real_estate"),
    ("AMT", "American Tower", "real_estate"),
    ("EQIX", "Equinix Inc.", "real_estate"),
    ("CCI", "Crown Castle Inc.", "real_estate"),
    ("PSA", "Public Storage", "real_estate"),
    # A few more to round out to 100
    ("ACN", "Accenture plc", "technology"),
    ("PYPL", "PayPal Holdings", "financials"),
    ("GM", "General Motors", "consumer_discretionary"),
    ("F", "Ford Motor Company", "consumer_discretionary"),
    ("KHC", "Kraft Heinz Company", "consumer_staples"),
    ("MO", "Altria Group", "consumer_staples"),
    ("GILD", "Gilead Sciences", "healthcare"),
    ("ISRG", "Intuitive Surgical", "healthcare"),
    ("ADP", "Automatic Data Processing", "industrials"),
    ("CSX", "CSX Corporation", "industrials"),
]


def get_tickers() -> list[tuple[str, str, str]]:
    """Returns list of (ticker, company_name, sector) tuples."""
    return SP500_SAMPLE


def allowed_tickers() -> set[str]:
    return {ticker for ticker, _, _ in SP500_SAMPLE}


def allowed_sectors() -> set[str]:
    return {sector for _, _, sector in SP500_SAMPLE}


def ticker_alias_rules() -> str:
    """Build ENTITY_PROMPT ticker mapping lines from the S&P 500 sample list."""
    lines: list[str] = []
    for ticker, name, _ in SP500_SAMPLE:
        short = (
            name.replace(" Inc.", "")
            .replace(" Corporation", "")
            .replace(" Company", "")
            .replace(" & Co.", "")
            .replace(" Group", "")
            .strip()
        )
        if short != name:
            lines.append(f'- "{name}", "{short}", or "{ticker}" -> {ticker}')
        else:
            lines.append(f'- "{name}" or "{ticker}" -> {ticker}')
    return "\n".join(lines)


def is_sp500_ticker(ticker: str) -> bool:
    return ticker.upper() in allowed_tickers()


if __name__ == "__main__":
    tickers = get_tickers()
    print(f"Total tickers: {len(tickers)}")
    from collections import Counter
    sectors = Counter(t[2] for t in tickers)
    for sector, count in sorted(sectors.items()):
        print(f"  {sector}: {count}")
