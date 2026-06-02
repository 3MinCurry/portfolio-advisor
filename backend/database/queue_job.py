#!/usr/bin/env python3
"""Send a pending job to SQS. Usage: uv run queue_job.py [job_id_prefix]"""
import json
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

import boto3
from src import Database

prefix = sys.argv[1] if len(sys.argv) > 1 else None
db = Database()

if prefix:
    row = db.client.query_one(
        f"SELECT id::text, clerk_user_id FROM jobs WHERE id::text LIKE '{prefix}%' ORDER BY created_at DESC LIMIT 1"
    )
else:
    row = db.client.query_one(
        "SELECT id::text, clerk_user_id FROM jobs WHERE status = 'pending' ORDER BY created_at DESC LIMIT 1"
    )

if not row:
    print("No matching job found")
    sys.exit(1)

job_id = row["id"]
uid = row["clerk_user_id"]
url = os.environ["SQS_QUEUE_URL"]
if not url:
    print("SQS_QUEUE_URL not set in .env")
    sys.exit(1)

sqs = boto3.client("sqs", region_name=os.environ.get("DEFAULT_AWS_REGION", "us-east-1"))
msg = json.dumps(
    {"job_id": job_id, "clerk_user_id": uid, "analysis_type": "portfolio", "options": {}}
)
r = sqs.send_message(QueueUrl=url, MessageBody=msg)
print(f"Queued {job_id} (user {uid})")
print(f"MessageId: {r['MessageId']}")
