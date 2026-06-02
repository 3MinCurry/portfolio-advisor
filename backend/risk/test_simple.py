#!/usr/bin/env python3
"""Simple test for Risk Management agent."""

import json
from dotenv import load_dotenv

load_dotenv(override=True)

from src import Database
from src.schemas import JobCreate
from lambda_handler import lambda_handler


def test_risk():
    db = Database()
    job_create = JobCreate(
        clerk_user_id="test_user_001",
        job_type="portfolio_analysis",
        request_payload={"test": True},
    )
    job_id = db.jobs.create(job_create.model_dump())
    print(f"Created test job: {job_id}")

    test_event = {
        "job_id": job_id,
        "portfolio_data": {
            "accounts": [
                {
                    "name": "Brokerage",
                    "type": "investment",
                    "cash_balance": 5000,
                    "positions": [
                        {
                            "symbol": "SPY",
                            "quantity": 100,
                            "instrument": {
                                "name": "SPDR S&P 500 ETF",
                                "current_price": 450,
                                "allocation_asset_class": {"equity": 100},
                                "allocation_sectors": {"Technology": 30, "Financials": 15},
                                "allocation_regions": {"North America": 100},
                            },
                        },
                        {
                            "symbol": "QQQ",
                            "quantity": 50,
                            "instrument": {
                                "name": "Invesco QQQ",
                                "current_price": 380,
                                "allocation_asset_class": {"equity": 100},
                                "allocation_sectors": {"Technology": 50},
                                "allocation_regions": {"North America": 100},
                            },
                        },
                    ],
                }
            ]
        },
    }

    print("Testing Risk Agent...")
    print("=" * 60)

    result = lambda_handler(test_event, None)
    print(f"Status Code: {result['statusCode']}")

    if result["statusCode"] == 200:
        body = json.loads(result["body"])
        print(f"Success: {body.get('success', False)}")
        print(f"Risk level: {body.get('risk_level', 'N/A')}")

        job = db.jobs.find_by_id(job_id)
        if job and job.get("risk_payload"):
            payload = job["risk_payload"]
            print("Risk data saved to database")
            print(f"Payload keys: {list(payload.keys())}")
            metrics = payload.get("metrics", {})
            if metrics:
                print(f"Metrics risk_level: {metrics.get('risk_level')}")
                print(f"Top holding: {metrics.get('top_holding_symbol')} ({metrics.get('top_holding_pct')}%)")
            analysis = payload.get("analysis", "")
            if isinstance(analysis, str) and analysis:
                print(f"Analysis length: {len(analysis)} characters")
                print(analysis[:400])
        else:
            print("No risk data found in database")
    else:
        print(f"Error: {result['body']}")

    db.jobs.delete(job_id)
    print(f"Deleted test job: {job_id}")
    print("=" * 60)


if __name__ == "__main__":
    test_risk()
