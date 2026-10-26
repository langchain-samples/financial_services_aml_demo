"""Example usage of the AML evaluator with LangSmith.

This script demonstrates how to use the evaluator with LangSmith's
native evaluation features for more advanced workflows.
"""

import asyncio
import os
from datetime import datetime

from langsmith import Client
from langsmith.evaluation import evaluate

from evaluation.aml_evaluator import evaluate_transaction_flagging
from evaluation.test_dataset import get_test_dataset
from agents.aml_agent import AMLAgent, Transaction


# Initialize AML agent
aml_agent = AMLAgent(llm_model="gpt-4o-mini", temperature=0.0)


def predict_function(inputs: dict) -> dict:
    """
    Wrapper function that runs the AML agent on inputs.

    This function is passed to LangSmith's evaluate() for automated testing.

    Args:
        inputs: Dictionary with transaction and customer_history

    Returns:
        Dictionary with agent outputs
    """
    transaction_data = inputs["transaction"]
    customer_history = inputs.get("customer_history", [])

    try:
        # Convert to Transaction objects
        transaction = Transaction(**transaction_data)

        # Convert history with defaults for missing fields
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

        # Set customer history in agent
        if customer_history:
            aml_agent.transaction_history[transaction.customer_id] = history_objects

        # Run analysis
        pattern = aml_agent.analyze_transaction_pattern(transaction, history_objects)
        sanctions_check = aml_agent.check_sanctions(transaction)
        anomalies = aml_agent.detect_anomalies(transaction, pattern, sanctions_check)
        alert = aml_agent.generate_alert(transaction, pattern, sanctions_check, anomalies)

        return {
            "alert": alert.model_dump() if alert else None,
            "pattern": pattern.model_dump() if pattern else None,
            "sanctions_check": sanctions_check.model_dump() if sanctions_check else None,
            "anomalies": anomalies.model_dump() if anomalies else None,
        }
    except Exception as e:
        return {
            "error": str(e),
            "alert": None,
        }


def sync_predict_function(inputs: dict) -> dict:
    """Synchronous wrapper for LangSmith evaluate."""
    return predict_function(inputs)


async def example_single_evaluation():
    """
    Example: Evaluate a single transaction manually.
    """
    print("\n" + "="*60)
    print("Example 1: Single Transaction Evaluation")
    print("="*60 + "\n")

    # Create a test transaction
    test_transaction_data = {
        "transaction_id": "TEST-001",
        "customer_id": "CUST-001",
        "amount": 50000.0,
        "currency": "USD",
        "transaction_type": "transfer",
        "origin": "United States",
        "destination": "Iran",
        "timestamp": datetime.now().isoformat(),
        "description": "Wire transfer",
    }

    # Run the agent
    print("Running AML agent on test transaction...")
    result = predict_function({"transaction": test_transaction_data, "customer_history": []})

    print(f"\nAgent Output:")
    print(f"  Alert Generated: {result.get('alert') is not None}")
    if result.get('alert'):
        alert = result['alert']
        print(f"  Severity: {alert.get('severity')}")
        print(f"  Risk Score: {alert.get('risk_score')}")
        print(f"  Indicators: {', '.join(alert.get('indicators', []))}")
        print(f"  Recommended Action: {alert.get('recommended_action')}")

    # Create expected output for evaluation
    expected = {
        "should_flag": True,
        "expected_severity": "CRITICAL",
        "expected_indicators": ["SANCTIONS_MATCH"],
        "min_risk_score": 70,
        "max_risk_score": 100,
    }

    # Mock example and run objects for evaluation
    Example = type('Example', (), {'outputs': expected})()
    Run = type('Run', (), {'outputs': result})()

    # Evaluate
    evaluation_result = evaluate_transaction_flagging(Run, Example)

    print(f"\nEvaluation Results:")
    print(f"  Overall Score: {evaluation_result['score']:.2%}")
    print(f"  Feedback:")
    for line in evaluation_result['comment'].split('\n'):
        print(f"    {line}")


async def example_batch_evaluation():
    """
    Example: Evaluate multiple transactions from test dataset.
    """
    print("\n" + "="*60)
    print("Example 2: Batch Evaluation")
    print("="*60 + "\n")

    # Get test dataset
    test_cases = get_test_dataset()[:5]  # Just first 5 for demo

    print(f"Evaluating {len(test_cases)} test cases...\n")

    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"[{i}/{len(test_cases)}] {test_case['metadata']['description']}")

        # Run agent
        output = predict_function(test_case['inputs'])

        # Mock objects
        Example = type('Example', (), {'outputs': test_case['outputs']})()
        Run = type('Run', (), {'outputs': output})()

        # Evaluate
        evaluation = evaluate_transaction_flagging(Run, Example)
        results.append(evaluation)

        print(f"  Score: {evaluation['score']:.2%}")

    # Calculate aggregate metrics
    avg_score = sum(r['score'] for r in results) / len(results)
    print(f"\nAggregate Results:")
    print(f"  Average Score: {avg_score:.2%}")
    print(f"  Cases Passed (>80%): {sum(1 for r in results if r['score'] >= 0.8)}/{len(results)}")


async def example_langsmith_native_evaluation():
    """
    Example: Use LangSmith's native evaluate() function.

    This is the recommended approach for production use.
    """
    print("\n" + "="*60)
    print("Example 3: LangSmith Native Evaluation")
    print("="*60 + "\n")

    # Initialize client
    client = Client()

    # Dataset name
    dataset_name = "aml-transaction-flagging-tests"

    print(f"Running evaluation on dataset: {dataset_name}\n")
    print("Note: This requires the dataset to be created in LangSmith.")
    print("Run 'python -m evaluation.run_evaluation' first to create it.\n")

    try:
        # Run LangSmith's built-in evaluate function
        # This will:
        # 1. Load the dataset from LangSmith
        # 2. Run the predict_function on each example
        # 3. Apply the evaluator to each result
        # 4. Log everything to LangSmith for visualization
        evaluation_results = evaluate(
            sync_predict_function,
            data=dataset_name,
            evaluators=[evaluate_transaction_flagging],
            experiment_prefix="aml-eval",
            description="AML transaction flagging accuracy evaluation",
            max_concurrency=5,
        )

        print("\n✓ Evaluation complete!")
        print(f"View results in LangSmith: https://smith.langchain.com/")

        return evaluation_results

    except Exception as e:
        print(f"\n✗ Evaluation failed: {e}")
        print("\nMake sure:")
        print("  1. LANGCHAIN_API_KEY is set")
        print("  2. Dataset exists (run 'python -m evaluation.run_evaluation' first)")
        return None


def example_custom_metrics():
    """
    Example: Calculate custom metrics from evaluation results.
    """
    print("\n" + "="*60)
    print("Example 4: Custom Metrics")
    print("="*60 + "\n")

    # Simulated evaluation results
    mock_results = [
        {'score': 1.0, 'scores': {'flag_correctness': 1.0, 'severity_accuracy': 1.0}},
        {'score': 0.85, 'scores': {'flag_correctness': 1.0, 'severity_accuracy': 0.67}},
        {'score': 0.0, 'scores': {'flag_correctness': 0.0, 'severity_accuracy': 0.0}},
        {'score': 1.0, 'scores': {'flag_correctness': 1.0, 'severity_accuracy': 1.0}},
        {'score': 0.92, 'scores': {'flag_correctness': 1.0, 'severity_accuracy': 0.83}},
    ]

    # Calculate metrics
    avg_score = sum(r['score'] for r in mock_results) / len(mock_results)
    perfect_scores = sum(1 for r in mock_results if r['score'] == 1.0)
    failed_scores = sum(1 for r in mock_results if r['score'] < 0.5)

    avg_flag_correctness = sum(
        r['scores']['flag_correctness'] for r in mock_results
    ) / len(mock_results)

    print(f"Custom Metrics:")
    print(f"  Average Score: {avg_score:.2%}")
    print(f"  Perfect Scores: {perfect_scores}/{len(mock_results)}")
    print(f"  Failed Cases: {failed_scores}/{len(mock_results)}")
    print(f"  Flag Correctness: {avg_flag_correctness:.2%}")

    # Identify areas for improvement
    print(f"\nAreas for Improvement:")
    for i, result in enumerate(mock_results, 1):
        if result['score'] < 0.8:
            print(f"  Case {i}: Score {result['score']:.2%}")
            if result['scores']['flag_correctness'] < 1.0:
                print(f"    - Incorrect flagging decision")
            if result['scores']['severity_accuracy'] < 0.8:
                print(f"    - Severity level needs adjustment")


async def main():
    """Run all examples."""
    print("\n" + "="*70)
    print(" "*15 + "AML EVALUATOR USAGE EXAMPLES")
    print("="*70)

    # Example 1: Single evaluation
    await example_single_evaluation()

    # Example 2: Batch evaluation
    await example_batch_evaluation()

    # Example 3: LangSmith native (requires dataset setup)
    # Uncomment to run:
    # await example_langsmith_native_evaluation()

    # Example 4: Custom metrics
    example_custom_metrics()

    print("\n" + "="*70)
    print("Examples complete!")
    print("="*70 + "\n")

    print("Next Steps:")
    print("  1. Run full evaluation: python -m evaluation.run_evaluation")
    print("  2. View results in LangSmith: https://smith.langchain.com/")
    print("  3. Integrate into CI/CD pipeline for continuous testing")
    print()


if __name__ == "__main__":
    asyncio.run(main())
