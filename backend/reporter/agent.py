"""
Report Writer Agent - generates portfolio analysis narratives.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from agents import function_tool, RunContextWrapper
from agents.extensions.models.litellm_model import LitellmModel

logger = logging.getLogger()


@dataclass
class ReporterContext:
    """Context for the Reporter agent"""

    job_id: str
    portfolio_data: Dict[str, Any]
    user_data: Dict[str, Any]
    db: Optional[Any] = None  # Database connection (optional for testing)


def calculate_portfolio_metrics(portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate basic portfolio metrics."""
    metrics = {
        "total_value": 0,
        "cash_balance": 0,
        "num_accounts": len(portfolio_data.get("accounts", [])),
        "num_positions": 0,
        "unique_symbols": set(),
    }

    for account in portfolio_data.get("accounts", []):
        metrics["cash_balance"] += float(account.get("cash_balance", 0))
        positions = account.get("positions", [])
        metrics["num_positions"] += len(positions)

        for position in positions:
            symbol = position.get("symbol")
            if symbol:
                metrics["unique_symbols"].add(symbol)

            # Calculate value if we have price
            instrument = position.get("instrument", {})
            if instrument.get("current_price"):
                value = float(position.get("quantity", 0)) * float(instrument["current_price"])
                metrics["total_value"] += value

    metrics["total_value"] += metrics["cash_balance"]
    metrics["unique_symbols"] = len(metrics["unique_symbols"])

    return metrics


def format_portfolio_for_analysis(portfolio_data: Dict[str, Any], user_data: Dict[str, Any]) -> str:
    """Format portfolio data for agent analysis."""
    metrics = calculate_portfolio_metrics(portfolio_data)

    lines = [
        f"Portfolio Overview:",
        f"- {metrics['num_accounts']} accounts",
        f"- {metrics['num_positions']} total positions",
        f"- {metrics['unique_symbols']} unique holdings",
        f"- ${metrics['cash_balance']:,.2f} in cash",
        f"- ${metrics['total_value']:,.2f} total value" if metrics["total_value"] > 0 else "",
        "",
        "Account Details:",
    ]

    for account in portfolio_data.get("accounts", []):
        name = account.get("name", "Unknown")
        cash = float(account.get("cash_balance", 0))
        lines.append(f"\n{name} (${cash:,.2f} cash):")

        for position in account.get("positions", []):
            symbol = position.get("symbol")
            quantity = float(position.get("quantity", 0))
            instrument = position.get("instrument", {})
            name = instrument.get("name", "")

            # Include allocation info if available
            allocations = []
            if instrument.get("asset_class"):
                allocations.append(f"Asset: {instrument['asset_class']}")
            if instrument.get("regions"):
                regions = ", ".join(
                    [f"{r['name']} {r['percentage']}%" for r in instrument["regions"][:2]]
                )
                allocations.append(f"Regions: {regions}")

            alloc_str = f" ({', '.join(allocations)})" if allocations else ""
            lines.append(f"  - {symbol}: {quantity:,.2f} shares{alloc_str}")

    # Add user context
    lines.extend(
        [
            "",
            "User Profile:",
            f"- Years to retirement: {user_data.get('years_until_retirement', 'Not specified')}",
            f"- Target retirement income: ${user_data.get('target_retirement_income', 0):,.0f}/year",
        ]
    )

    return "\n".join(lines)


# update_report tool removed - report is now saved directly in lambda_handler


def _fetch_sec_insights(symbols: List[str]) -> Optional[str]:
    """SEC 10-K context via backend/sec_rag (Chroma locally, S3 Vectors on Lambda)."""
    try:
        try:
            from sec_rag.retrieval import fetch_insights_for_holdings
        except ImportError:
            import sys
            from pathlib import Path

            backend_dir = Path(__file__).resolve().parent
            if backend_dir.name == "reporter":
                backend_dir = backend_dir.parent
            sys.path.insert(0, str(backend_dir))
            from sec_rag.retrieval import fetch_insights_for_holdings

        result = fetch_insights_for_holdings(symbols)
        if result and "unavailable" not in result.lower():
            return result
    except Exception as exc:
        logger.warning("Reporter: SEC RAG retrieval failed: %s", exc)
    return None


def _fetch_general_market_insights(symbols: List[str]) -> Optional[str]:
    """General market research from S3 Vectors (web ingest, news, etc.)."""
    import boto3

    bucket = os.getenv("VECTOR_BUCKET")
    if not bucket:
        sts = boto3.client("sts")
        bucket = f"alex-vectors-{sts.get_caller_identity()['Account']}"

    sagemaker_region = os.getenv("DEFAULT_AWS_REGION", "us-east-1")
    sagemaker = boto3.client("sagemaker-runtime", region_name=sagemaker_region)
    endpoint_name = os.getenv("SAGEMAKER_ENDPOINT", "alex-embedding-endpoint")
    query = f"market analysis {' '.join(symbols[:5])}" if symbols else "market outlook"

    response = sagemaker.invoke_endpoint(
        EndpointName=endpoint_name,
        ContentType="application/json",
        Body=json.dumps({"inputs": query}),
    )

    result = json.loads(response["Body"].read().decode())
    if isinstance(result, list) and result:
        embedding = result[0][0] if isinstance(result[0], list) else result[0]
    else:
        embedding = result

    s3v = boto3.client("s3vectors", region_name=sagemaker_region)
    response = s3v.query_vectors(
        vectorBucketName=bucket,
        indexName="financial-research",
        queryVector={"float32": embedding},
        topK=3,
        returnMetadata=True,
    )

    insights = []
    for vector in response.get("vectors", []):
        metadata = vector.get("metadata", {})
        if metadata.get("source_type") == "sec_10k":
            continue
        text = metadata.get("text", "")[:200]
        if text:
            company = metadata.get("company_name", metadata.get("company", ""))
            prefix = f"{company}: " if company else "- "
            insights.append(f"{prefix}{text}...")

    if insights:
        return "Market research:\n" + "\n".join(insights)
    return None


@function_tool
async def get_market_insights(
    wrapper: RunContextWrapper[ReporterContext], symbols: List[str]
) -> str:
    """
    Retrieve market insights: SEC 10-K filings plus general vector research.

    Args:
        wrapper: Context wrapper with job_id and database
        symbols: List of symbols to get insights for

    Returns:
        Relevant market context and insights
    """
    try:
        parts: List[str] = []

        sec = _fetch_sec_insights(symbols)
        if sec:
            parts.append(sec)

        general = _fetch_general_market_insights(symbols)
        if general:
            parts.append(general)

        if parts:
            return "\n\n".join(parts)
        return "Market insights unavailable - proceeding with standard analysis."

    except Exception as e:
        logger.warning(f"Reporter: Could not retrieve market insights: {e}")
        return "Market insights unavailable - proceeding with standard analysis."


def create_agent(job_id: str, portfolio_data: Dict[str, Any], user_data: Dict[str, Any], db=None):
    """Create the reporter agent with tools and context."""

    # Get model configuration
    model_id = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
    # Set region for LiteLLM Bedrock calls
    bedrock_region = os.getenv("BEDROCK_REGION", "us-west-2")
    logger.info(f"DEBUG: BEDROCK_REGION from env = {bedrock_region}")
    os.environ["AWS_REGION_NAME"] = bedrock_region
    logger.info(f"DEBUG: Set AWS_REGION_NAME to {bedrock_region}")

    model = LitellmModel(model=f"bedrock/{model_id}")

    # Create context
    context = ReporterContext(
        job_id=job_id, portfolio_data=portfolio_data, user_data=user_data, db=db
    )

    # Tools - only get_market_insights now, report saved in lambda_handler
    tools = [get_market_insights]

    # Format portfolio for analysis
    portfolio_summary = format_portfolio_for_analysis(portfolio_data, user_data)

    # Create task
    task = f"""Analyze this investment portfolio and write a comprehensive report.

{portfolio_summary}

Your task:
1. First, get market insights for the top holdings using get_market_insights()
2. Analyze the portfolio's current state, strengths, and weaknesses
3. Generate a detailed, professional analysis report in markdown format

The report should include:
- Executive Summary
- Portfolio Composition Analysis
- Risk Assessment
- Diversification Analysis
- Retirement Readiness (based on user goals)
- Recommendations
- Market Context (from insights)

Provide your complete analysis as the final output in clear markdown format.
Make the report informative yet accessible to a retail investor."""

    return model, tools, task, context
