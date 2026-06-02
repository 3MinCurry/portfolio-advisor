#!/usr/bin/env python3
"""Quick check of recent job statuses. Run: cd backend/database && uv run check_jobs.py"""
from dotenv import load_dotenv
from pathlib import Path

_env = Path(__file__).resolve().parents[2] / ".env"
if not _env.exists():
    print(f"ERROR: .env not found at {_env}")
    raise SystemExit(1)

load_dotenv(_env, override=True)

from src import Database

db = Database()
rows = db.client.query(
    """
  SELECT id::text, status, created_at, started_at, completed_at,
         COALESCE(error_message, '') as err,
         (report_payload IS NOT NULL) as has_report,
         (charts_payload IS NOT NULL) as has_charts,
         (retirement_payload IS NOT NULL) as has_retirement,
         (risk_payload IS NOT NULL) as has_risk
  FROM jobs
  ORDER BY created_at DESC
  LIMIT 10
"""
)

if not rows:
    print("No jobs in database yet. Start an analysis from the app first.")
    raise SystemExit(0)

running = [r for r in rows if r["status"] == "running"]
pending = [r for r in rows if r["status"] == "pending"]
completed = [r for r in rows if r["status"] == "completed"]
failed = [r for r in rows if r["status"] == "failed"]

print("=" * 60)
print("JOB SUMMARY (last 10)")
print("=" * 60)
print(f"  Running now:     {len(running)}  (agent actively working)")
print(f"  Pending (stuck): {len(pending)}  (created but planner never started)")
print(f"  Completed:       {len([r for r in rows if r['status']=='completed'])}")
print(f"  Failed:          {len(failed)}")
print()

if running:
    print(">>> AGENTS CURRENTLY RUNNING:")
    for r in running:
        print(f"    {r['id'][:8]}... started {r['started_at']}")
else:
    print(">>> No agent is running right now.")

orphan_pending = [r for r in pending if r["started_at"] is None]
if orphan_pending:
    print()
    print(f">>> {len(orphan_pending)} orphaned pending job(s) (never reached SQS/planner):")
    print("    Fix: restart run_local.py, then start a NEW analysis.")
    print("    Old pending jobs will not auto-run.")

print()
print("RECENT JOBS:")
print("-" * 60)
for r in rows:
    jid = str(r["id"])[:8]
    flags = []
    if r["has_report"]:
        flags.append("report")
    if r["has_charts"]:
        flags.append("charts")
    if r["has_retirement"]:
        flags.append("retirement")
    if r["has_risk"]:
        flags.append("risk")
    extra = f" [{', '.join(flags)}]" if flags else ""
    err = f"  ERROR: {r['err'][:50]}" if r["err"] else ""
    print(
        f"  {r['status']:10} {jid}  {r['created_at']}{extra}{err}"
    )
print("=" * 60)
