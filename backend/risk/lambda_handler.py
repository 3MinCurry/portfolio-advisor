"""
Risk Management Agent Lambda Handler
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any
from datetime import datetime

from agents import Agent, Runner, trace
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from litellm.exceptions import RateLimitError

try:
    from dotenv import load_dotenv

    load_dotenv(override=True)
except ImportError:
    pass

from src import Database

from templates import RISK_INSTRUCTIONS
from agent import create_agent
from observability import observe

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def load_portfolio_data(db: Database, job_id: str) -> Dict[str, Any]:
    """Load portfolio data for a job from the database."""
    job = db.jobs.find_by_id(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    user_id = job["clerk_user_id"]
    user = db.users.find_by_clerk_id(user_id)
    accounts = db.accounts.find_by_user(user_id)

    portfolio_data = {
        "user_id": user_id,
        "job_id": job_id,
        "years_until_retirement": user.get("years_until_retirement", 30) if user else 30,
        "accounts": [],
    }

    for account in accounts:
        account_data = {
            "id": account["id"],
            "name": account["account_name"],
            "type": account.get("account_type", "investment"),
            "cash_balance": float(account.get("cash_balance", 0)),
            "positions": [],
        }

        for position in db.positions.find_by_account(account["id"]):
            instrument = db.instruments.find_by_symbol(position["symbol"])
            if instrument:
                account_data["positions"].append(
                    {
                        "symbol": position["symbol"],
                        "quantity": float(position["quantity"]),
                        "instrument": instrument,
                    }
                )

        portfolio_data["accounts"].append(account_data)

    return portfolio_data


@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    before_sleep=lambda retry_state: logger.info(
        f"Risk: Rate limit hit, retrying in {retry_state.next_action.sleep} seconds..."
    ),
)
async def run_risk_agent(job_id: str, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run the risk management agent."""
    db = Database()
    model, tools, task, metrics = create_agent(job_id, portfolio_data, db)

    with trace("Risk Agent"):
        agent = Agent(
            name="Risk Manager",
            instructions=RISK_INSTRUCTIONS,
            model=model,
            tools=tools,
        )

        result = await Runner.run(agent, input=task, max_turns=10)

        risk_payload = {
            "analysis": result.final_output,
            "metrics": metrics,
            "generated_at": datetime.utcnow().isoformat(),
            "agent": "risk",
        }

        success = db.jobs.update_risk(job_id, risk_payload)

        return {
            "success": success,
            "message": "Risk analysis completed" if success else "Analysis completed but failed to save",
            "risk_level": metrics.get("risk_level"),
        }


def lambda_handler(event, context):
    """Lambda handler; expects job_id in event."""
    with observe():
        try:
            if isinstance(event, str):
                event = json.loads(event)

            job_id = event.get("job_id")
            if not job_id:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "job_id is required"}),
                }

            portfolio_data = event.get("portfolio_data")
            db = Database()

            if not portfolio_data:
                portfolio_data = load_portfolio_data(db, job_id)

            logger.info(f"Risk: Processing job {job_id}")
            result = asyncio.run(run_risk_agent(job_id, portfolio_data))

            return {"statusCode": 200, "body": json.dumps(result)}

        except Exception as e:
            logger.error(f"Error in risk agent: {e}", exc_info=True)
            return {
                "statusCode": 500,
                "body": json.dumps({"success": False, "error": str(e)}),
            }
