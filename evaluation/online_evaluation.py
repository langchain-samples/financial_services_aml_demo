"""Online evaluation for AML agent traces.

This script monitors LangSmith traces in real-time and evaluates whether
transactions are being correctly triaged. It can:

1. Monitor traces from production traffic
2. Evaluate triage decisions automatically
3. Flag cases for human review
4. Add problematic cases to annotation queues
5. Track accuracy metrics over time

Use this for:
- Production monitoring
- Real-time quality assurance
- Automated alerting on accuracy drops
- Continuous human-in-the-loop feedback
"""

import os
import sys
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langsmith import Client
from langsmith.run_helpers import traceable
from dotenv import load_dotenv

from evaluation.llm_judge_evaluator import aml_llm_judge
from evaluation.aml_evaluator import evaluate_transaction_flagging

# Load environment variables
load_dotenv()

# Configuration
PROJECT_NAME = os.getenv("LANGCHAIN_PROJECT", "financial_services_deep_agent_demo")
ANNOTATION_QUEUE_NAME = "aml-production-review-queue"
EVALUATION_INTERVAL_SECONDS = 60  # Check for new traces every minute
ACCURACY_ALERT_THRESHOLD = 0.80  # Alert if accuracy drops below 80%


class OnlineEvaluator:
    """Monitors and evaluates AML agent traces in real-time."""

    def __init__(
        self,
        project_name: str = PROJECT_NAME,
        lookback_minutes: int = 60,
        enable_llm_judge: bool = True,
        enable_annotation_queue: bool = True,
    ):
        """
        Initialize online evaluator.

        Args:
            project_name: LangSmith project to monitor
            lookback_minutes: How far back to look for traces
            enable_llm_judge: Whether to use LLM judge for evaluation
            enable_annotation_queue: Whether to add cases to annotation queue
        """
        self.client = Client()
        self.project_name = project_name
        self.lookback_minutes = lookback_minutes
        self.enable_llm_judge = enable_llm_judge
        self.enable_annotation_queue = enable_annotation_queue
        self.annotation_queue_id = None
        self.evaluated_run_ids = set()  # Track already evaluated runs

        if self.enable_annotation_queue:
            self.annotation_queue_id = self._get_or_create_annotation_queue()

    def _get_or_create_annotation_queue(self) -> Optional[str]:
        """Get existing annotation queue or create a new one."""
        print(f"\n{'='*70}")
        print(f"Setting up Annotation Queue: {ANNOTATION_QUEUE_NAME}")
        print(f"{'='*70}\n")

        # Try to find existing queue
        try:
            queues = list(self.client.list_annotation_queues())
            for queue in queues:
                if queue.name == ANNOTATION_QUEUE_NAME:
                    print(f"✓ Found existing queue: {queue.id}")
                    return str(queue.id)
        except Exception as e:
            print(f"Note: Could not list queues: {e}")

        # Create new queue
        try:
            queue = self.client.create_annotation_queue(
                name=ANNOTATION_QUEUE_NAME,
                description="Production AML cases that need human review",
            )
            print(f"✓ Created new queue: {queue.id}")
            return str(queue.id)
        except Exception as e:
            print(f"Error creating queue: {e}")
            print("Continuing without annotation queue...")
            return None

    def _get_recent_traces(self) -> List[Any]:
        """Fetch recent traces from LangSmith."""
        cutoff_time = datetime.now() - timedelta(minutes=self.lookback_minutes)

        try:
            # Get runs from the project
            runs = self.client.list_runs(
                project_name=self.project_name,
                start_time=cutoff_time,
                execution_order=1,  # Only get root runs
                error=False,  # Only successful runs
            )

            # Filter out already evaluated runs
            new_runs = [
                run for run in runs
                if str(run.id) not in self.evaluated_run_ids
            ]

            return new_runs
        except Exception as e:
            print(f"Error fetching traces: {e}")
            return []

    def _extract_transaction_data(self, run: Any) -> Optional[Dict[str, Any]]:
        """Extract transaction data from a trace."""
        try:
            # Get inputs and outputs from the run
            inputs = run.inputs if hasattr(run, 'inputs') else {}
            outputs = run.outputs if hasattr(run, 'outputs') else {}

            # Try to extract transaction from inputs
            transaction = inputs.get("transaction")
            if not transaction:
                # Maybe it's nested differently
                transaction = inputs.get("input", {}).get("transaction")

            if not transaction:
                return None

            return {
                "run_id": str(run.id),
                "transaction": transaction,
                "customer_history": inputs.get("customer_history", []),
                "outputs": outputs,
                "run": run,
            }
        except Exception as e:
            print(f"Error extracting transaction data: {e}")
            return None

    def _evaluate_triage_decision(
        self,
        transaction_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Evaluate if the triage decision was correct.

        Args:
            transaction_data: Transaction details and outputs

        Returns:
            Evaluation results with recommendation for human review
        """
        outputs = transaction_data["outputs"]
        alert = outputs.get("alert")

        # For online evaluation, we don't always have ground truth
        # So we use heuristics and LLM judge to assess quality

        evaluation_result = None
        needs_review = False
        review_reason = None
        confidence_score = None

        # Use LLM judge if enabled
        if self.enable_llm_judge:
            try:
                # Create mock Run and Example for evaluator
                Run = type('Run', (), {
                    'outputs': outputs,
                })()

                # For online eval, we don't have ground truth
                # So we create a minimal example for LLM judge to assess
                Example = type('Example', (), {
                    'inputs': {
                        'transaction': transaction_data['transaction'],
                        'customer_history': transaction_data.get('customer_history', []),
                    },
                    'outputs': {},  # No ground truth
                })()

                evaluation_result = aml_llm_judge(Run, Example)
                confidence_score = evaluation_result.get("score", 0.5)

            except Exception as e:
                print(f"Error in LLM judge evaluation: {e}")
                confidence_score = 0.5  # Default to uncertain

        # Determine if needs human review
        needs_review, review_reason = self._should_review_online(
            transaction_data,
            outputs,
            confidence_score,
        )

        return {
            "run_id": transaction_data["run_id"],
            "transaction_id": transaction_data["transaction"].get("transaction_id", "unknown"),
            "outputs": outputs,
            "evaluation": evaluation_result,
            "confidence_score": confidence_score,
            "needs_review": needs_review,
            "review_reason": review_reason,
            "timestamp": datetime.now().isoformat(),
        }

    def _should_review_online(
        self,
        transaction_data: Dict[str, Any],
        outputs: Dict[str, Any],
        confidence_score: Optional[float],
    ) -> tuple[bool, Optional[str]]:
        """
        Determine if a production case needs human review.

        Criteria for online evaluation (no ground truth):
        1. Low confidence from LLM judge (< 0.7)
        2. High-value transactions (> $100k)
        3. Edge cases near risk threshold
        4. Sanctions-related flags (always review)
        5. Unusual patterns flagged by agent
        """
        transaction = transaction_data["transaction"]
        alert = outputs.get("alert")

        # Criterion 1: Low confidence from LLM judge
        if confidence_score is not None and confidence_score < 0.7:
            return True, f"LOW_CONFIDENCE: LLM judge score {confidence_score:.2%}"

        # Criterion 2: High-value transactions - extra scrutiny
        amount = transaction.get("amount", 0)
        if amount > 100000:
            if alert:
                return True, f"HIGH_VALUE_FLAGGED: ${amount:,.2f} flagged for review"
            elif amount > 500000:
                return True, f"VERY_HIGH_VALUE: ${amount:,.2f} (flagged or not, review needed)"

        # Criterion 3: Edge cases near risk threshold
        if alert:
            risk_score = alert.get("risk_score", 0)
            if 38 <= risk_score <= 42:  # Near 40 threshold
                return True, f"EDGE_CASE: Risk score {risk_score} near threshold"

            # Criterion 4: Sanctions-related - ALWAYS review
            indicators = alert.get("indicators", [])
            if any("sanction" in ind.lower() for ind in indicators):
                return True, "SANCTIONS: Sanctions-related alert (CRITICAL)"

            # Criterion 5: Critical severity
            severity = alert.get("severity", "")
            if severity == "CRITICAL":
                return True, f"CRITICAL_SEVERITY: Severity level is CRITICAL"

        # Criterion 6: Multiple risk indicators
        if alert:
            indicators = alert.get("indicators", [])
            if len(indicators) >= 3:
                return True, f"MULTIPLE_INDICATORS: {len(indicators)} risk factors"

        return False, None

    def _add_to_annotation_queue(self, evaluation: Dict[str, Any]):
        """Add a run to annotation queue for human review."""
        if not self.annotation_queue_id:
            return

        try:
            run_id = evaluation["run_id"]

            # Add feedback to the run indicating it needs review
            self.client.create_feedback(
                run_id=run_id,
                key="needs_review",
                score=1.0,
                comment=f"Flagged for review: {evaluation['review_reason']}",
                source_info={
                    "review_reason": evaluation["review_reason"],
                    "confidence_score": evaluation.get("confidence_score"),
                    "timestamp": evaluation["timestamp"],
                }
            )

            # Note: Actual queue addition depends on LangSmith SDK version
            # The feedback above makes it filterable in the UI

            print(f"  ✓ Flagged for review: {evaluation['transaction_id']}")

        except Exception as e:
            print(f"  Error adding to queue: {e}")

    def evaluate_recent_traces(self) -> Dict[str, Any]:
        """
        Evaluate recent traces and return summary statistics.

        Returns:
            Summary with accuracy metrics and cases needing review
        """
        print(f"\n{'='*70}")
        print(f"Online Evaluation - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")
        print(f"Project: {self.project_name}")
        print(f"Lookback: {self.lookback_minutes} minutes")

        # Fetch recent traces
        runs = self._get_recent_traces()

        if not runs:
            print("No new traces to evaluate")
            return {
                "evaluated": 0,
                "needs_review": 0,
                "timestamp": datetime.now().isoformat(),
            }

        print(f"Found {len(runs)} new traces to evaluate\n")

        results = []
        needs_review_count = 0

        for run in runs:
            # Extract transaction data
            transaction_data = self._extract_transaction_data(run)
            if not transaction_data:
                continue

            transaction_id = transaction_data["transaction"].get("transaction_id", "unknown")
            print(f"Evaluating: {transaction_id}")

            # Evaluate triage decision
            evaluation = self._evaluate_triage_decision(transaction_data)
            results.append(evaluation)

            # Mark as evaluated
            self.evaluated_run_ids.add(evaluation["run_id"])

            # Handle cases needing review
            if evaluation["needs_review"]:
                needs_review_count += 1
                print(f"  ⚠️  NEEDS REVIEW: {evaluation['review_reason']}")

                if self.enable_annotation_queue:
                    self._add_to_annotation_queue(evaluation)
            else:
                conf = evaluation.get("confidence_score")
                if conf is not None:
                    print(f"  ✓ Confidence: {conf:.2%}")
                else:
                    print(f"  ✓ Passed basic checks")

        # Calculate summary
        summary = self._calculate_summary(results)
        self._print_summary(summary)

        # Check if accuracy alert needed
        if summary.get("avg_confidence") and summary["avg_confidence"] < ACCURACY_ALERT_THRESHOLD:
            self._send_accuracy_alert(summary)

        return summary

    def _calculate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics from evaluation results."""
        total = len(results)
        needs_review = sum(1 for r in results if r["needs_review"])

        # Calculate average confidence
        confidence_scores = [
            r["confidence_score"] for r in results
            if r.get("confidence_score") is not None
        ]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else None

        # Count review reasons
        review_reasons = {}
        for r in results:
            if r["needs_review"]:
                reason = r["review_reason"].split(":")[0]  # Get category
                review_reasons[reason] = review_reasons.get(reason, 0) + 1

        return {
            "total_evaluated": total,
            "needs_review": needs_review,
            "review_rate": needs_review / total if total > 0 else 0,
            "avg_confidence": avg_confidence,
            "review_reasons": review_reasons,
            "timestamp": datetime.now().isoformat(),
        }

    def _print_summary(self, summary: Dict[str, Any]):
        """Print evaluation summary."""
        print(f"\n{'='*70}")
        print(f"Summary")
        print(f"{'='*70}\n")
        print(f"  Total Evaluated: {summary['total_evaluated']}")

        if summary['avg_confidence'] is not None:
            print(f"  Average Confidence: {summary['avg_confidence']:.2%}")

        print(f"  Needs Human Review: {summary['needs_review']} ({summary['review_rate']:.1%})")

        if summary['review_reasons']:
            print(f"\n  Review Breakdown:")
            for reason, count in summary['review_reasons'].items():
                print(f"    {reason}: {count}")

        print()

    def _send_accuracy_alert(self, summary: Dict[str, Any]):
        """Send alert when accuracy drops below threshold."""
        print(f"\n{'='*70}")
        print(f"⚠️  ACCURACY ALERT")
        print(f"{'='*70}\n")
        print(f"Average confidence: {summary['avg_confidence']:.2%}")
        print(f"Threshold: {ACCURACY_ALERT_THRESHOLD:.2%}")
        print(f"Review rate: {summary['review_rate']:.1%}")
        print(f"\nAction required: Investigate recent changes to the system")
        print()

    def run_continuous_monitoring(self, interval_seconds: int = EVALUATION_INTERVAL_SECONDS):
        """
        Run continuous monitoring loop.

        Args:
            interval_seconds: How often to check for new traces
        """
        print(f"\n{'='*70}")
        print("STARTING CONTINUOUS ONLINE EVALUATION")
        print(f"{'='*70}\n")
        print(f"Project: {self.project_name}")
        print(f"Interval: {interval_seconds} seconds")
        print(f"LLM Judge: {'Enabled' if self.enable_llm_judge else 'Disabled'}")
        print(f"Annotation Queue: {'Enabled' if self.enable_annotation_queue else 'Disabled'}")
        print(f"\nPress Ctrl+C to stop\n")

        try:
            while True:
                # Evaluate recent traces
                summary = self.evaluate_recent_traces()

                # Wait for next interval
                print(f"Sleeping for {interval_seconds} seconds...")
                print(f"{'='*70}\n")
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            print("\n\nStopping online evaluation...")
            print(f"Total runs evaluated: {len(self.evaluated_run_ids)}")
            print()


def main():
    """Main entry point for online evaluation."""
    import argparse

    parser = argparse.ArgumentParser(description="Online evaluation for AML agent traces")
    parser.add_argument(
        "--mode",
        choices=["once", "continuous"],
        default="once",
        help="Run once or continuously monitor"
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=60,
        help="How many minutes to look back for traces (default: 60)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=EVALUATION_INTERVAL_SECONDS,
        help="Interval in seconds for continuous monitoring (default: 60)"
    )
    parser.add_argument(
        "--no-llm-judge",
        action="store_true",
        help="Disable LLM judge evaluation"
    )
    parser.add_argument(
        "--no-queue",
        action="store_true",
        help="Disable annotation queue"
    )

    args = parser.parse_args()

    # Initialize evaluator
    evaluator = OnlineEvaluator(
        project_name=PROJECT_NAME,
        lookback_minutes=args.lookback,
        enable_llm_judge=not args.no_llm_judge,
        enable_annotation_queue=not args.no_queue,
    )

    # Run evaluation
    if args.mode == "once":
        summary = evaluator.evaluate_recent_traces()

        print(f"{'='*70}")
        print("Next Steps:")
        print(f"{'='*70}\n")
        print("1. Review flagged cases in LangSmith")
        print("2. Check annotation queue for cases needing human review")
        print("3. Set up continuous monitoring with --mode continuous")
        print("4. Configure alerting for accuracy drops")
        print()

    else:  # continuous
        evaluator.run_continuous_monitoring(interval_seconds=args.interval)


if __name__ == "__main__":
    main()
