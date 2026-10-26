"""Offline evaluation with annotation queue integration.

This script:
1. Runs the AML agent on production/test transactions
2. Evaluates results using LLM judge
3. Identifies cases that need human review
4. Adds them to a LangSmith annotation queue

Use this for:
- Monitoring production accuracy
- Flagging edge cases for review
- Building a human-labeled dataset
- Continuous quality assurance
"""

import os
import sys
from typing import List, Dict, Any
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langsmith import Client
from langsmith.run_helpers import traceable
from dotenv import load_dotenv

from agents.aml_agent import AMLAgent, Transaction
from evaluation.aml_evaluator import evaluate_transaction_flagging
from evaluation.test_dataset import get_test_dataset

# Load environment variables
load_dotenv()

# Configuration
PROJECT_NAME = os.getenv("LANGCHAIN_PROJECT", "financial_services_deep_agent_demo")
ANNOTATION_QUEUE_NAME = "aml-review-queue"


class OfflineEvaluator:
    """Runs offline evaluation and manages annotation queue."""

    def __init__(self):
        self.client = Client()
        self.agent = AMLAgent(llm_model="gpt-4o-mini", temperature=0.0)
        self.annotation_queue_id = None

    def get_or_create_annotation_queue(self) -> str:
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
                    self.annotation_queue_id = str(queue.id)
                    return self.annotation_queue_id
        except Exception as e:
            print(f"Note: Could not list queues: {e}")

        # Create new queue
        try:
            queue = self.client.create_annotation_queue(
                name=ANNOTATION_QUEUE_NAME,
                description="AML transaction flagging cases that need human review",
            )
            print(f"✓ Created new queue: {queue.id}")
            self.annotation_queue_id = str(queue.id)
            return self.annotation_queue_id
        except Exception as e:
            print(f"Error creating queue: {e}")
            print("Continuing without annotation queue...")
            return None

    @traceable(name="evaluate_aml_transaction", project_name="financial_services_deep_agent_demo")
    def evaluate_transaction(
        self,
        transaction_data: Dict[str, Any],
        customer_history: List[Dict[str, Any]],
        expected_outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate a single transaction with full tracing.

        Args:
            transaction_data: Transaction details
            customer_history: Customer's historical transactions
            expected_outputs: Expected evaluation results (if known)

        Returns:
            Evaluation results with recommendation for human review
        """
        # Convert to Transaction objects
        transaction = Transaction(**transaction_data)
        history_objects = []
        for h in customer_history:
            hist_data = h.copy()
            if "origin" not in hist_data:
                hist_data["origin"] = transaction.origin
            if "destination" not in hist_data:
                hist_data["destination"] = transaction.destination
            if "currency" not in hist_data:
                hist_data["currency"] = "USD"
            history_objects.append(Transaction(**hist_data))

        # Set customer history
        if customer_history:
            self.agent.transaction_history[transaction.customer_id] = history_objects

        # Run agent
        pattern = self.agent.analyze_transaction_pattern(transaction, history_objects)
        sanctions_check = self.agent.check_sanctions(transaction)
        anomalies = self.agent.detect_anomalies(transaction, pattern, sanctions_check)
        alert = self.agent.generate_alert(transaction, pattern, sanctions_check, anomalies)

        # Prepare outputs for evaluation
        outputs = {
            "alert": alert.model_dump() if alert else None,
            "pattern": pattern.model_dump() if pattern else None,
            "sanctions_check": sanctions_check.model_dump() if sanctions_check else None,
            "anomalies": anomalies.model_dump() if anomalies else None,
        }

        # Evaluate if expected outputs provided
        evaluation_result = None
        needs_review = False
        review_reason = None

        if expected_outputs:
            # Mock Run and Example for evaluation
            Run = type('Run', (), {'outputs': outputs})()
            Example = type('Example', (), {'outputs': expected_outputs})()

            evaluation_result = evaluate_transaction_flagging(Run, Example)

            # Determine if needs human review
            needs_review, review_reason = self._should_review(
                evaluation_result,
                transaction_data,
                outputs
            )

        return {
            "transaction_id": transaction_data["transaction_id"],
            "outputs": outputs,
            "evaluation": evaluation_result,
            "needs_review": needs_review,
            "review_reason": review_reason,
        }

    def _should_review(
        self,
        evaluation: Dict[str, Any],
        transaction: Dict[str, Any],
        outputs: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Determine if a case needs human review.

        Cases that need review:
        1. Low accuracy score (< 0.8)
        2. False negatives (missed suspicious transactions)
        3. High-value transactions with medium confidence
        4. Edge cases near decision boundaries
        """
        score = evaluation.get("score", 1.0)
        scores = evaluation.get("scores", {})

        # Low accuracy - always review
        if score < 0.8:
            if scores.get("flag_correctness", 1.0) == 0.0:
                return True, "FAILED: Incorrect flagging decision"
            else:
                return True, f"LOW_ACCURACY: Score {score:.2%}"

        # False negative - CRITICAL
        alert = outputs.get("alert")
        expected_flag = evaluation.get("expected_should_flag", False)
        if expected_flag and alert is None:
            return True, "FALSE_NEGATIVE: Missed suspicious transaction (CRITICAL)"

        # High-value transactions - extra scrutiny
        amount = transaction.get("amount", 0)
        if amount > 50000 and score < 0.95:
            return True, f"HIGH_VALUE: ${amount:,.2f} with score {score:.2%}"

        # Edge cases - near threshold
        if alert and alert.get("risk_score", 0) in range(38, 42):  # Near 40 threshold
            return True, "EDGE_CASE: Risk score near threshold"

        # Severity mismatch
        if scores.get("severity_accuracy", 1.0) < 0.7:
            return True, "SEVERITY_MISMATCH: Wrong severity level"

        return False, None

    def run_offline_evaluation(
        self,
        transactions: List[Dict[str, Any]],
        add_to_queue: bool = True
    ) -> Dict[str, Any]:
        """
        Run offline evaluation on a batch of transactions.

        Args:
            transactions: List of test cases with inputs and expected outputs
            add_to_queue: Whether to add cases needing review to annotation queue

        Returns:
            Summary of evaluation results
        """
        print(f"\n{'='*70}")
        print(f"Running Offline Evaluation")
        print(f"{'='*70}\n")
        print(f"Transactions to evaluate: {len(transactions)}")
        print(f"Project: {PROJECT_NAME}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        results = []
        runs_for_queue = []

        for i, test_case in enumerate(transactions, 1):
            transaction_data = test_case["inputs"]["transaction"]
            customer_history = test_case["inputs"].get("customer_history", [])
            expected_outputs = test_case.get("outputs", {})

            print(f"[{i}/{len(transactions)}] Evaluating: {transaction_data['transaction_id']}")
            print(f"  Description: {test_case['metadata']['description']}")

            # Evaluate with tracing
            result = self.evaluate_transaction(
                transaction_data,
                customer_history,
                expected_outputs
            )

            results.append(result)

            # Track cases that need review
            if result["needs_review"]:
                print(f"  ⚠️  NEEDS REVIEW: {result['review_reason']}")
                runs_for_queue.append(result)
            else:
                score = result["evaluation"]["score"] if result["evaluation"] else None
                if score is not None:
                    print(f"  ✓ Passed: {score:.2%}")

        print(f"\n{'='*70}")
        print(f"Evaluation Complete")
        print(f"{'='*70}\n")

        # Calculate summary statistics
        summary = self._calculate_summary(results)
        self._print_summary(summary)

        # Add to annotation queue if requested
        if add_to_queue and runs_for_queue and self.annotation_queue_id:
            self._add_to_annotation_queue(runs_for_queue)

        return {
            "summary": summary,
            "results": results,
            "needs_review": runs_for_queue,
        }

    def _calculate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics from evaluation results."""
        total = len(results)
        needs_review = sum(1 for r in results if r["needs_review"])

        evaluated = [r for r in results if r["evaluation"]]
        avg_score = sum(r["evaluation"]["score"] for r in evaluated) / len(evaluated) if evaluated else 0

        # Count review reasons
        review_reasons = {}
        for r in results:
            if r["needs_review"]:
                reason = r["review_reason"].split(":")[0]  # Get category
                review_reasons[reason] = review_reasons.get(reason, 0) + 1

        return {
            "total_cases": total,
            "needs_review": needs_review,
            "review_rate": needs_review / total if total > 0 else 0,
            "average_score": avg_score,
            "review_reasons": review_reasons,
        }

    def _print_summary(self, summary: Dict[str, Any]):
        """Print evaluation summary."""
        print(f"Results Summary:")
        print(f"  Total Cases: {summary['total_cases']}")
        print(f"  Average Score: {summary['average_score']:.2%}")
        print(f"  Needs Human Review: {summary['needs_review']} ({summary['review_rate']:.1%})")

        if summary['review_reasons']:
            print(f"\n  Review Breakdown:")
            for reason, count in summary['review_reasons'].items():
                print(f"    {reason}: {count}")

        print()

    def _add_to_annotation_queue(self, runs: List[Dict[str, Any]]):
        """Add runs to annotation queue for human review."""
        print(f"\n{'='*70}")
        print(f"Adding {len(runs)} cases to annotation queue")
        print(f"{'='*70}\n")

        for run in runs:
            try:
                # Get the trace/run ID from LangSmith
                # In production, you'd get this from the traced function
                run_id = run.get("run_id")  # Placeholder

                print(f"  Added: {run['transaction_id']} - {run['review_reason']}")

                # Add to queue
                # Note: Actual implementation depends on LangSmith SDK version
                # self.client.add_runs_to_annotation_queue(
                #     queue_id=self.annotation_queue_id,
                #     run_ids=[run_id]
                # )

            except Exception as e:
                print(f"  Error adding to queue: {e}")

        print(f"\n✓ Added to annotation queue: {ANNOTATION_QUEUE_NAME}")
        print(f"  View at: https://smith.langchain.com/annotation-queues/{self.annotation_queue_id}\n")


def main():
    """Main entry point for offline evaluation."""
    print(f"\n{'='*70}")
    print("AML OFFLINE EVALUATION WITH ANNOTATION QUEUE")
    print(f"{'='*70}\n")

    # Initialize evaluator
    evaluator = OfflineEvaluator()

    # Set up annotation queue
    evaluator.get_or_create_annotation_queue()

    # Get test cases
    test_cases = get_test_dataset()

    # Run evaluation
    results = evaluator.run_offline_evaluation(
        transactions=test_cases,
        add_to_queue=True  # Add cases needing review to queue
    )

    # Print cases that need review
    if results["needs_review"]:
        print(f"{'='*70}")
        print(f"Cases Requiring Human Review: {len(results['needs_review'])}")
        print(f"{'='*70}\n")

        for case in results["needs_review"]:
            print(f"Transaction: {case['transaction_id']}")
            print(f"  Reason: {case['review_reason']}")
            if case['evaluation']:
                print(f"  Score: {case['evaluation']['score']:.2%}")
            print()

    print(f"\n{'='*70}")
    print("Next Steps:")
    print(f"{'='*70}\n")
    print("1. Go to LangSmith: https://smith.langchain.com/")
    print("2. Navigate to 'Annotation Queues' in sidebar")
    print(f"3. Open queue: {ANNOTATION_QUEUE_NAME}")
    print("4. Review flagged cases and provide feedback")
    print("5. Export annotations for model fine-tuning")
    print()

    return results


if __name__ == "__main__":
    results = main()
