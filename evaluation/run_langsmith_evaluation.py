"""Run AML evaluation using LangSmith's native evaluate() with LLM judge.

This script uses LangSmith's evaluation framework with an LLM-as-a-judge
evaluator. Results will appear in the LangSmith evaluations UI.
"""

import os
import sys
import asyncio
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langsmith import Client
from langsmith.evaluation import evaluate
from dotenv import load_dotenv

from evaluation.llm_judge_evaluator import aml_llm_judge
from evaluation.aml_evaluator import evaluate_transaction_flagging
from evaluation.test_dataset import get_test_dataset, get_dataset_summary
from agents.aml_agent import AMLAgent, Transaction


# Load environment variables
load_dotenv()

# Configuration
DATASET_NAME = "aml-transaction-flagging-tests"
PROJECT_NAME = os.getenv("LANGCHAIN_PROJECT", "financial_services_deep_agent_demo")


def create_dataset(client: Client) -> None:
    """
    Creates the test dataset in LangSmith.

    Args:
        client: LangSmith client
    """
    print(f"\n{'='*70}")
    print(f"Creating Dataset: {DATASET_NAME}")
    print(f"{'='*70}\n")

    # Get test cases
    test_cases = get_test_dataset()
    summary = get_dataset_summary()

    print(f"Dataset Summary:")
    print(f"  Total test cases: {summary['total_cases']}")
    print(f"  Categories: {summary['categories']}")
    print(f"  Expected positives: {summary['expected_positives']}")
    print(f"  Expected negatives: {summary['expected_negatives']}\n")

    # Check if dataset exists
    try:
        existing = client.read_dataset(dataset_name=DATASET_NAME)
        print(f"Dataset already exists: {existing.id}")
        print("Deleting existing dataset to recreate with latest test cases...\n")
        client.delete_dataset(dataset_id=existing.id)
    except Exception:
        pass

    # Create new dataset
    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description=(
            "Test dataset for evaluating AML transaction flagging accuracy. "
            f"Contains {summary['total_cases']} test cases covering sanctions, "
            "structuring, large amounts, high frequency, and normal transactions."
        ),
    )

    print(f"✓ Created dataset: {dataset.id}\n")
    print("Adding test cases...")

    # Add examples
    for i, test_case in enumerate(test_cases, 1):
        client.create_example(
            dataset_id=dataset.id,
            inputs=test_case["inputs"],
            outputs=test_case["outputs"],
            metadata=test_case["metadata"],
        )
        category = test_case['metadata']['category']
        desc = test_case['metadata']['description']
        print(f"  [{i:2d}/{len(test_cases)}] [{category:12s}] {desc}")

    print(f"\n✓ Dataset ready with {len(test_cases)} test cases\n")


# Initialize AML agent (create once, reuse for all predictions)
aml_agent = AMLAgent(llm_model="gpt-4o-mini", temperature=0.0)


def predict_async(inputs: dict) -> dict:
    """
    Prediction function for the AML agent.

    Args:
        inputs: Dictionary with transaction and customer_history

    Returns:
        Dictionary with agent outputs
    """
    transaction_data = inputs["transaction"]
    customer_history = inputs.get("customer_history", [])

    try:
        # Convert dict to Transaction object
        transaction = Transaction(**transaction_data)

        # Convert history to Transaction objects
        # Add defaults for missing fields in history
        history_objects = []
        for h in customer_history:
            hist_data = h.copy()
            # Add defaults if missing
            if "origin" not in hist_data:
                hist_data["origin"] = transaction.origin if "origin" in transaction_data else "Unknown"
            if "destination" not in hist_data:
                hist_data["destination"] = transaction.destination if "destination" in transaction_data else "Unknown"
            if "currency" not in hist_data:
                hist_data["currency"] = "USD"
            history_objects.append(Transaction(**hist_data))

        # Set customer history in agent
        if customer_history:
            aml_agent.transaction_history[transaction.customer_id] = history_objects

        # Run analysis
        pattern = aml_agent.analyze_transaction_pattern(transaction, history_objects)
        sanctions_check = aml_agent.check_sanctions(transaction)
        anomalies = aml_agent.detect_anomalies(transaction, pattern, sanctions_check)
        alert = aml_agent.generate_alert(transaction, pattern, sanctions_check, anomalies)

        # Convert to dict for output
        return {
            "alert": alert.model_dump() if alert else None,
            "pattern": pattern.model_dump() if pattern else None,
            "sanctions_check": sanctions_check.model_dump() if sanctions_check else None,
            "anomalies": anomalies.model_dump() if anomalies else None,
        }
    except Exception as e:
        print(f"Error in prediction: {e}")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "alert": None,
        }


def predict(inputs: dict) -> dict:
    """
    Prediction function for LangSmith evaluate().

    Args:
        inputs: Dictionary with transaction and customer_history

    Returns:
        Dictionary with agent outputs
    """
    return predict_async(inputs)


def run_evaluation_with_llm_judge():
    """
    Run evaluation using LangSmith's evaluate() with LLM judge.
    """
    print(f"\n{'='*70}")
    print("AML TRANSACTION FLAGGING EVALUATION")
    print("Using LLM-as-a-Judge Evaluator")
    print(f"{'='*70}\n")
    print(f"Project: {PROJECT_NAME}")
    print(f"Dataset: {DATASET_NAME}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Initialize client
    client = Client()

    # Create/update dataset
    create_dataset(client)

    print(f"{'='*70}")
    print("Running Evaluation")
    print(f"{'='*70}\n")

    print("Evaluator: LLM Judge (GPT-4o)")
    print("This will:")
    print("  1. Run AML agent on all test cases")
    print("  2. Use GPT-4o to evaluate each result")
    print("  3. Log all traces to LangSmith")
    print("  4. Generate evaluation report\n")

    experiment_name = f"aml-eval-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Run evaluation with LLM judge
    print(f"Starting experiment: {experiment_name}\n")

    results = evaluate(
        predict,
        data=DATASET_NAME,
        evaluators=[aml_llm_judge],
        experiment_prefix=experiment_name,
        description="AML transaction flagging evaluation using LLM-as-a-judge",
        max_concurrency=3,  # Limit concurrency to avoid rate limits
        client=client,
    )

    print(f"\n{'='*70}")
    print("Evaluation Complete!")
    print(f"{'='*70}\n")

    # Print summary
    print("View detailed results in LangSmith:")
    print(f"  https://smith.langchain.com/\n")

    print("The LangSmith UI will show:")
    print("  • Individual test case results with LLM judge feedback")
    print("  • Aggregate metrics and charts")
    print("  • Full traces for debugging")
    print("  • Component scores breakdown")
    print("  • Critical issues and recommendations\n")

    return results


def run_evaluation_with_both():
    """
    Run evaluation with both LLM judge and rule-based evaluators.
    """
    print(f"\n{'='*70}")
    print("AML TRANSACTION FLAGGING EVALUATION")
    print("Using Both LLM Judge and Rule-Based Evaluators")
    print(f"{'='*70}\n")
    print(f"Project: {PROJECT_NAME}")
    print(f"Dataset: {DATASET_NAME}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Initialize client
    client = Client()

    # Create/update dataset
    create_dataset(client)

    print(f"{'='*70}")
    print("Running Evaluation")
    print(f"{'='*70}\n")

    print("Evaluators:")
    print("  1. LLM Judge (GPT-4o) - Qualitative assessment")
    print("  2. Rule-Based - Quantitative metrics\n")

    experiment_name = f"aml-eval-dual-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    print(f"Starting experiment: {experiment_name}\n")

    # Run with both evaluators
    results = evaluate(
        predict,
        data=DATASET_NAME,
        evaluators=[
            aml_llm_judge,  # LLM-as-a-judge
            evaluate_transaction_flagging,  # Rule-based
        ],
        experiment_prefix=experiment_name,
        description="AML evaluation with both LLM judge and rule-based evaluators",
        max_concurrency=3,
        client=client,
    )

    print(f"\n{'='*70}")
    print("Evaluation Complete!")
    print(f"{'='*70}\n")

    print("View results in LangSmith UI:")
    print(f"  https://smith.langchain.com/\n")

    print("Compare both evaluators to see:")
    print("  • LLM judge provides nuanced qualitative feedback")
    print("  • Rule-based provides precise quantitative metrics")
    print("  • Insights from combining both approaches\n")

    return results


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run AML transaction flagging evaluation with LangSmith"
    )
    parser.add_argument(
        "--mode",
        choices=["llm", "both"],
        default="llm",
        help="Evaluation mode: 'llm' (LLM judge only) or 'both' (LLM + rule-based)",
    )

    args = parser.parse_args()

    # Check for API key
    if not os.getenv("LANGCHAIN_API_KEY"):
        print("Error: LANGCHAIN_API_KEY not found in environment")
        print("Set it with: export LANGCHAIN_API_KEY='your-api-key'")
        sys.exit(1)

    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in environment")
        print("Set it with: export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)

    try:
        if args.mode == "llm":
            results = run_evaluation_with_llm_judge()
        else:
            results = run_evaluation_with_both()

        print("✓ Evaluation successful\n")
        return 0

    except Exception as e:
        print(f"\n✗ Evaluation failed: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
