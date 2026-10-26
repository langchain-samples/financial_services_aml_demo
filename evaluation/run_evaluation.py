"""Script to run AML transaction flagging evaluation using LangSmith.

This script:
1. Creates or updates a dataset in LangSmith
2. Runs the AML agent against the test dataset
3. Evaluates the results using custom evaluators
4. Generates a comprehensive evaluation report
"""

import os
import sys
from datetime import datetime
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langsmith import Client
from langsmith.schemas import Example, Run
from langchain_core.tracers.langchain import LangChainTracer

from evaluation.aml_evaluator import (
    evaluate_transaction_flagging,
    evaluate_false_positive_rate,
    evaluate_false_negative_rate,
    evaluate_severity_distribution,
)
from evaluation.test_dataset import get_test_dataset, get_dataset_summary

# Import AML agent
from agents.aml_agent import AMLAgent, Transaction


# Dataset name in LangSmith
DATASET_NAME = "aml-transaction-flagging-tests"
PROJECT_NAME = "financial_services_deep_agent_demo"


def create_or_update_dataset(client: Client) -> str:
    """
    Creates or updates the test dataset in LangSmith.

    Args:
        client: LangSmith client

    Returns:
        Dataset name
    """
    print(f"\n{'='*60}")
    print(f"Creating/Updating Dataset: {DATASET_NAME}")
    print(f"{'='*60}\n")

    # Get test cases
    test_cases = get_test_dataset()
    summary = get_dataset_summary()

    print(f"Total test cases: {summary['total_cases']}")
    print(f"Categories: {summary['categories']}")
    print(f"Expected positives: {summary['expected_positives']}")
    print(f"Expected negatives: {summary['expected_negatives']}\n")

    # Create dataset (will update if exists)
    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description=(
            "Test dataset for evaluating AML transaction flagging accuracy. "
            "Includes sanctions matches, structuring patterns, large amounts, "
            "high frequency, and normal transactions."
        ),
    )

    print(f"Dataset created/updated: {dataset.id}\n")

    # Add examples to dataset
    print("Adding test cases to dataset...")
    for i, test_case in enumerate(test_cases, 1):
        client.create_example(
            dataset_id=dataset.id,
            inputs=test_case["inputs"],
            outputs=test_case["outputs"],
            metadata=test_case["metadata"],
        )
        print(f"  [{i}/{len(test_cases)}] Added: {test_case['metadata']['description']}")

    print(f"\n✓ Dataset ready with {len(test_cases)} test cases\n")

    return DATASET_NAME


def run_aml_agent_on_example(example: Example, agent: AMLAgent) -> Dict[str, Any]:
    """
    Runs the AML agent on a single test example.

    Args:
        example: Test example with transaction data
        agent: AMLAgent instance

    Returns:
        Agent output dictionary
    """
    inputs = example.inputs
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
            agent.transaction_history[transaction.customer_id] = history_objects

        # Run the AML agent analysis
        pattern = agent.analyze_transaction_pattern(transaction, history_objects)
        sanctions_check = agent.check_sanctions(transaction)
        anomalies = agent.detect_anomalies(transaction, pattern, sanctions_check)
        alert = agent.generate_alert(transaction, pattern, sanctions_check, anomalies)

        return {
            "alert": alert.model_dump() if alert else None,
            "pattern": pattern.model_dump() if pattern else None,
            "sanctions_check": sanctions_check.model_dump() if sanctions_check else None,
            "anomalies": anomalies.model_dump() if anomalies else None,
        }
    except Exception as e:
        print(f"Error running agent on {transaction_data['transaction_id']}: {e}")
        return {
            "error": str(e),
            "alert": None,
        }


def print_evaluation_results(results: Dict[str, Any]):
    """
    Prints a formatted evaluation report.

    Args:
        results: Evaluation results dictionary
    """
    print(f"\n{'='*60}")
    print(f"EVALUATION RESULTS")
    print(f"{'='*60}\n")

    # Overall metrics
    print(f"Overall Accuracy: {results['overall_accuracy']:.2%}")
    print(f"Total Test Cases: {results['total_cases']}")
    print(f"\n{'-'*60}\n")

    # Classification metrics
    print("CLASSIFICATION METRICS:")
    print(f"  True Positives:  {results['true_positives']:3d}")
    print(f"  True Negatives:  {results['true_negatives']:3d}")
    print(f"  False Positives: {results['false_positives']:3d}")
    print(f"  False Negatives: {results['false_negatives']:3d}")
    print(f"\n  Precision: {results['precision']:.2%}")
    print(f"  Recall:    {results['recall']:.2%}")
    print(f"  F1 Score:  {results['f1_score']:.2%}")
    print(f"\n  False Positive Rate: {results['false_positive_rate']:.2%}")
    print(f"  False Negative Rate: {results['false_negative_rate']:.2%}")
    print(f"\n{'-'*60}\n")

    # Component scores
    print("COMPONENT SCORES:")
    print(f"  Flag Correctness:    {results['avg_flag_correctness']:.2%}")
    print(f"  Severity Accuracy:   {results['avg_severity_accuracy']:.2%}")
    print(f"  Indicator Detection: {results['avg_indicator_detection']:.2%}")
    print(f"  Risk Score Accuracy: {results['avg_risk_score_accuracy']:.2%}")
    print(f"\n{'-'*60}\n")

    # Severity distribution
    print("SEVERITY DISTRIBUTION:")
    severity_dist = results['severity_distribution']
    print(f"  Total Flagged: {severity_dist['total_flagged']}")
    for severity, count in severity_dist['severity_counts'].items():
        pct = severity_dist['severity_percentages'][severity]
        print(f"    {severity:8s}: {count:3d} ({pct:5.1f}%)")

    print(f"\n{'='*60}\n")


def run_evaluation(client: Client, dataset_name: str) -> Dict[str, Any]:
    """
    Runs the evaluation on the dataset.

    Args:
        client: LangSmith client
        dataset_name: Name of the dataset to evaluate

    Returns:
        Dictionary with evaluation results
    """
    print(f"\n{'='*60}")
    print(f"Running Evaluation")
    print(f"{'='*60}\n")

    # Get dataset
    dataset = client.read_dataset(dataset_name=dataset_name)
    examples = list(client.list_examples(dataset_id=dataset.id))

    print(f"Running AML agent on {len(examples)} test cases...\n")

    # Initialize AML agent
    agent = AMLAgent(llm_model="gpt-4o-mini", temperature=0.0)

    # Run agent on all examples and collect results
    runs = []
    for i, example in enumerate(examples, 1):
        print(f"  [{i}/{len(examples)}] Testing: {example.metadata['description']}")

        # Run the agent
        output = run_aml_agent_on_example(example, agent)

        # Create a mock Run object for evaluation
        # In production, this would be actual LangSmith runs
        run = type('Run', (), {
            'outputs': output,
            'inputs': example.inputs,
            'id': f"run-{i}",
        })()

        runs.append(run)

    print("\n✓ All test cases executed\n")
    print(f"{'-'*60}\n")
    print("Evaluating results...\n")

    # Run evaluators
    evaluation_results = []
    for run, example in zip(runs, examples):
        result = evaluate_transaction_flagging(run, example)
        evaluation_results.append({
            'example': example,
            'run': run,
            'evaluation': result,
        })

    # Calculate aggregate metrics
    total_cases = len(evaluation_results)
    overall_scores = [r['evaluation']['score'] for r in evaluation_results]
    overall_accuracy = sum(overall_scores) / len(overall_scores) if overall_scores else 0

    # Calculate component scores
    component_scores = {
        'flag_correctness': [],
        'severity_accuracy': [],
        'indicator_detection': [],
        'risk_score_accuracy': [],
    }

    for result in evaluation_results:
        scores = result['evaluation'].get('scores', {})
        for key in component_scores:
            component_scores[key].append(scores.get(key, 0))

    avg_component_scores = {
        f"avg_{key}": sum(values) / len(values) if values else 0
        for key, values in component_scores.items()
    }

    # Calculate classification metrics
    true_positives = 0
    true_negatives = 0
    false_positives = 0
    false_negatives = 0

    for result in evaluation_results:
        example = result['example']
        run = result['run']

        expected_should_flag = example.outputs.get("should_flag", False)
        alert = run.outputs.get("alert")
        actual_flagged = alert is not None

        if expected_should_flag and actual_flagged:
            true_positives += 1
        elif not expected_should_flag and not actual_flagged:
            true_negatives += 1
        elif not expected_should_flag and actual_flagged:
            false_positives += 1
        elif expected_should_flag and not actual_flagged:
            false_negatives += 1

    # Calculate rates
    total_actual_positives = true_positives + false_positives
    total_actual_negatives = true_negatives + false_negatives
    total_expected_positives = true_positives + false_negatives
    total_expected_negatives = true_negatives + false_positives

    precision = true_positives / total_actual_positives if total_actual_positives > 0 else 0
    recall = true_positives / total_expected_positives if total_expected_positives > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    false_positive_rate = false_positives / total_expected_negatives if total_expected_negatives > 0 else 0
    false_negative_rate = false_negatives / total_expected_positives if total_expected_positives > 0 else 0

    # Get severity distribution
    severity_distribution = evaluate_severity_distribution(runs, examples)

    # Compile results
    results = {
        'timestamp': datetime.now().isoformat(),
        'dataset_name': dataset_name,
        'total_cases': total_cases,
        'overall_accuracy': overall_accuracy,
        'true_positives': true_positives,
        'true_negatives': true_negatives,
        'false_positives': false_positives,
        'false_negatives': false_negatives,
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'false_positive_rate': false_positive_rate,
        'false_negative_rate': false_negative_rate,
        **avg_component_scores,
        'severity_distribution': severity_distribution,
        'detailed_results': evaluation_results,
    }

    return results


def main():
    """Main entry point for the evaluation script."""
    print(f"\n{'='*60}")
    print("AML TRANSACTION FLAGGING EVALUATION")
    print(f"{'='*60}\n")
    print(f"Project: {PROJECT_NAME}")
    print(f"Dataset: {DATASET_NAME}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize LangSmith client
    client = Client()

    try:
        # Step 1: Create/update dataset
        dataset_name = create_or_update_dataset(client)

        # Step 2: Run evaluation
        results = run_evaluation(client, dataset_name)

        # Step 3: Print results
        print_evaluation_results(results)

        # Step 4: Save results to file
        output_file = f"evaluation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_path = os.path.join(os.path.dirname(__file__), output_file)

        import json
        # Remove detailed results for cleaner JSON output
        summary_results = {k: v for k, v in results.items() if k != 'detailed_results'}

        with open(output_path, 'w') as f:
            json.dump(summary_results, f, indent=2, default=str)

        print(f"✓ Results saved to: {output_file}\n")
        print(f"View detailed traces in LangSmith: https://smith.langchain.com/\n")

        return results

    except Exception as e:
        print(f"\n✗ Evaluation failed: {e}\n")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Run the main function
    results = main()

    # Exit with appropriate code
    if results and results['overall_accuracy'] >= 0.8:
        print("✓ Evaluation passed (accuracy >= 80%)\n")
        sys.exit(0)
    elif results:
        print("⚠ Evaluation completed but accuracy below threshold\n")
        sys.exit(1)
    else:
        print("✗ Evaluation failed\n")
        sys.exit(2)
