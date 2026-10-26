"""Run a LangSmith Insights report over AML review decisions stored in SQLite.

Analyst decisions (approve / reject / escalate + justification) live in the
local review database, not in LangSmith. ``Client.generate_insights`` uploads
them as conversations to a new tracing project and clusters them, which shows
what kinds of alerts analysts overturn and why.

Usage:
    python -m insights.generate_review_insights --limit 500 --wait
"""

import argparse
import json
import os

from dotenv import load_dotenv
from langsmith import Client

from app.database import SessionLocal
from app.models_db import AMLReview

load_dotenv()

DEFAULT_INSTRUCTIONS = (
    "These are AML transaction alerts and the compliance analyst's decision on each. "
    "Which alert typologies are most often approved as false positives, which are "
    "escalated, and what reasons do analysts give? Highlight patterns that suggest "
    "the agent's severity or risk scoring should be recalibrated."
)


def review_to_chat_history(review: AMLReview) -> list[dict]:
    """Represent one review as an alert -> analyst-decision exchange."""
    alert = {
        "transaction_id": review.transaction_id,
        "amount": review.amount,
        "currency": review.currency,
        "origin": review.origin,
        "destination": review.destination,
        "transaction_type": review.transaction_type,
        "anomaly_types": json.loads(review.anomaly_types) if review.anomaly_types else [],
        "severity": review.severity,
        "risk_score": review.risk_score,
        "details": review.anomaly_details,
    }
    decision = {
        "status": review.status,
        "action": review.review_action,
        "justification": review.justification,
        "escalation_priority": review.escalation_priority,
    }
    return [
        {"role": "user", "content": f"AML alert raised by the agent:\n{json.dumps(alert, indent=2)}"},
        {"role": "assistant", "content": f"Analyst decision:\n{json.dumps(decision, indent=2)}"},
    ]


def load_chat_histories(limit: int, include_pending: bool) -> list[list[dict]]:
    """Read reviews from the database (read-only)."""
    with SessionLocal() as session:
        query = session.query(AMLReview)
        if not include_pending:
            query = query.filter(AMLReview.status != "pending")
        reviews = query.order_by(AMLReview.created_at.desc()).limit(limit).all()
        return [review_to_chat_history(r) for r in reviews]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, default=500, help="Max reviews to analyze (Insights samples up to 1,000)")
    parser.add_argument("--include-pending", action="store_true", help="Include reviews with no analyst decision yet")
    parser.add_argument("--name", default="AML analyst decisions", help="Report name")
    parser.add_argument("--instructions", default=DEFAULT_INSTRUCTIONS, help="What Insights should look for")
    parser.add_argument("--model", choices=["openai", "anthropic"], default="openai")
    parser.add_argument("--wait", action="store_true", help="Poll until the report finishes (up to 30 min)")
    args = parser.parse_args()

    chat_histories = load_chat_histories(args.limit, args.include_pending)
    if not chat_histories:
        raise SystemExit(
            "No reviews found. Generate some with "
            "`curl -X POST 'http://localhost:8000/load/transactions/anomalies?anomaly_type=sanctions'` "
            "and review them in the UI, or pass --include-pending."
        )
    print(f"Uploading {len(chat_histories)} reviews to LangSmith Insights...")

    client = Client()
    report = client.generate_insights(
        chat_histories=chat_histories,
        name=args.name,
        instructions=args.instructions,
        model=args.model,
        # Optional if the provider key is already stored as a workspace secret
        openai_api_key=os.getenv("OPENAI_API_KEY") if args.model == "openai" else None,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") if args.model == "anthropic" else None,
    )

    if args.wait:
        report = client.poll_insights(report=report, verbose=True)
    print(f"Insights report: {report.link}")


if __name__ == "__main__":
    main()
