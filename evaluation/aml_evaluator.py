"""LangSmith evaluator for AML transaction flagging correctness.

This evaluator checks whether the AML agent correctly identifies and flags
suspicious transactions based on expected behavior.
"""

from typing import Any, Dict, List, Optional
from langsmith.schemas import Example, Run
from langsmith.evaluation import evaluate
from datetime import datetime


def evaluate_transaction_flagging(run: Run, example: Example) -> Dict[str, Any]:
    """
    Evaluates whether the AML agent correctly flagged a transaction.

    Args:
        run: The LangSmith run containing the agent's output
        example: The test example with expected outputs

    Returns:
        Dictionary with evaluation scores and feedback
    """
    # Extract expected values from the example
    expected_should_flag = example.outputs.get("should_flag", False)
    expected_severity = example.outputs.get("expected_severity")
    expected_indicators = set(example.outputs.get("expected_indicators", []))
    expected_min_risk_score = example.outputs.get("min_risk_score", 0)
    expected_max_risk_score = example.outputs.get("max_risk_score", 100)

    # Extract actual values from the agent's run
    outputs = run.outputs or {}
    alert = outputs.get("alert")

    # Initialize scores
    scores = {
        "flag_correctness": 0.0,      # Did agent correctly flag/not flag?
        "severity_accuracy": 0.0,      # Was severity level appropriate?
        "indicator_detection": 0.0,    # Did agent detect expected indicators?
        "risk_score_accuracy": 0.0,    # Was risk score in expected range?
        "overall_accuracy": 0.0,       # Overall weighted score
    }

    feedback_messages = []

    # 1. Check if transaction was correctly flagged
    actual_flagged = alert is not None
    if actual_flagged == expected_should_flag:
        scores["flag_correctness"] = 1.0
        feedback_messages.append(
            f"✓ Correctly {'flagged' if actual_flagged else 'did not flag'} transaction"
        )
    else:
        scores["flag_correctness"] = 0.0
        if expected_should_flag:
            feedback_messages.append(
                "✗ MISS: Transaction should have been flagged but was not"
            )
        else:
            feedback_messages.append(
                "✗ FALSE POSITIVE: Transaction should not have been flagged"
            )

    # If we expected no flag and none was generated, we're done
    if not expected_should_flag and not actual_flagged:
        scores["severity_accuracy"] = 1.0
        scores["indicator_detection"] = 1.0
        scores["risk_score_accuracy"] = 1.0
        scores["overall_accuracy"] = 1.0
        return {
            "key": "transaction_flagging_accuracy",
            "score": scores["overall_accuracy"],
            "comment": "\n".join(feedback_messages),
            "scores": scores,
        }

    # If transaction was flagged, evaluate the alert details
    if alert:
        # 2. Check severity level
        actual_severity = alert.get("severity")
        if expected_severity:
            if actual_severity == expected_severity:
                scores["severity_accuracy"] = 1.0
                feedback_messages.append(f"✓ Correct severity: {actual_severity}")
            else:
                # Partial credit for being close
                severity_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
                if actual_severity in severity_order and expected_severity in severity_order:
                    expected_idx = severity_order.index(expected_severity)
                    actual_idx = severity_order.index(actual_severity)
                    diff = abs(expected_idx - actual_idx)
                    scores["severity_accuracy"] = max(0, 1.0 - (diff * 0.33))
                    feedback_messages.append(
                        f"⚠ Severity mismatch: expected {expected_severity}, got {actual_severity}"
                    )
                else:
                    scores["severity_accuracy"] = 0.0
                    feedback_messages.append(
                        f"✗ Invalid severity: expected {expected_severity}, got {actual_severity}"
                    )
        else:
            # No expected severity specified, just check it's valid
            if actual_severity in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
                scores["severity_accuracy"] = 1.0
            else:
                scores["severity_accuracy"] = 0.5

        # 3. Check indicators
        actual_indicators = set(alert.get("indicators", []))
        if expected_indicators:
            # Calculate overlap
            intersection = expected_indicators & actual_indicators
            union = expected_indicators | actual_indicators

            if len(union) > 0:
                scores["indicator_detection"] = len(intersection) / len(expected_indicators)
            else:
                scores["indicator_detection"] = 1.0

            missing_indicators = expected_indicators - actual_indicators
            extra_indicators = actual_indicators - expected_indicators

            if missing_indicators:
                feedback_messages.append(
                    f"⚠ Missing indicators: {', '.join(missing_indicators)}"
                )
            if extra_indicators:
                feedback_messages.append(
                    f"⚠ Extra indicators detected: {', '.join(extra_indicators)}"
                )
            if not missing_indicators and not extra_indicators:
                feedback_messages.append(
                    f"✓ All expected indicators detected: {', '.join(actual_indicators)}"
                )
        else:
            # No expected indicators specified
            scores["indicator_detection"] = 1.0
            feedback_messages.append(
                f"ℹ Detected indicators: {', '.join(actual_indicators)}"
            )

        # 4. Check risk score
        actual_risk_score = alert.get("risk_score", 0)
        if expected_min_risk_score <= actual_risk_score <= expected_max_risk_score:
            scores["risk_score_accuracy"] = 1.0
            feedback_messages.append(
                f"✓ Risk score in expected range: {actual_risk_score} "
                f"(expected {expected_min_risk_score}-{expected_max_risk_score})"
            )
        else:
            # Partial credit based on how far off
            range_size = expected_max_risk_score - expected_min_risk_score
            if actual_risk_score < expected_min_risk_score:
                distance = expected_min_risk_score - actual_risk_score
            else:
                distance = actual_risk_score - expected_max_risk_score

            # Linear decay: 0.1 deduction per 10 points off
            scores["risk_score_accuracy"] = max(0, 1.0 - (distance / 100))
            feedback_messages.append(
                f"⚠ Risk score outside expected range: {actual_risk_score} "
                f"(expected {expected_min_risk_score}-{expected_max_risk_score})"
            )
    else:
        # Transaction should have been flagged but wasn't
        scores["severity_accuracy"] = 0.0
        scores["indicator_detection"] = 0.0
        scores["risk_score_accuracy"] = 0.0

    # 5. Calculate overall accuracy (weighted average)
    weights = {
        "flag_correctness": 0.40,      # Most important: did we flag correctly?
        "severity_accuracy": 0.25,     # Important: right severity level?
        "indicator_detection": 0.20,   # Important: detected right issues?
        "risk_score_accuracy": 0.15,   # Less critical: exact score
    }

    scores["overall_accuracy"] = sum(
        scores[key] * weight for key, weight in weights.items()
    )

    # Add overall score to feedback
    feedback_messages.insert(
        0,
        f"Overall Accuracy: {scores['overall_accuracy']:.2%} "
        f"(Flag: {scores['flag_correctness']:.0%}, "
        f"Severity: {scores['severity_accuracy']:.0%}, "
        f"Indicators: {scores['indicator_detection']:.0%}, "
        f"Risk Score: {scores['risk_score_accuracy']:.0%})"
    )

    return {
        "key": "transaction_flagging_accuracy",
        "score": scores["overall_accuracy"],
        "comment": "\n".join(feedback_messages),
        "scores": scores,
    }


def evaluate_false_positive_rate(runs: List[Run], examples: List[Example]) -> Dict[str, float]:
    """
    Calculates the false positive rate across all evaluations.

    Args:
        runs: List of LangSmith runs
        examples: List of test examples

    Returns:
        Dictionary with false positive metrics
    """
    false_positives = 0
    true_negatives = 0

    for run, example in zip(runs, examples):
        expected_should_flag = example.outputs.get("should_flag", False)
        outputs = run.outputs or {}
        alert = outputs.get("alert")
        actual_flagged = alert is not None

        if not expected_should_flag:
            if actual_flagged:
                false_positives += 1
            else:
                true_negatives += 1

    total_negatives = false_positives + true_negatives
    false_positive_rate = false_positives / total_negatives if total_negatives > 0 else 0

    return {
        "false_positive_rate": false_positive_rate,
        "false_positives": false_positives,
        "true_negatives": true_negatives,
    }


def evaluate_false_negative_rate(runs: List[Run], examples: List[Example]) -> Dict[str, float]:
    """
    Calculates the false negative rate (missed detections) across all evaluations.

    Args:
        runs: List of LangSmith runs
        examples: List of test examples

    Returns:
        Dictionary with false negative metrics
    """
    false_negatives = 0
    true_positives = 0

    for run, example in zip(runs, examples):
        expected_should_flag = example.outputs.get("should_flag", False)
        outputs = run.outputs or {}
        alert = outputs.get("alert")
        actual_flagged = alert is not None

        if expected_should_flag:
            if not actual_flagged:
                false_negatives += 1
            else:
                true_positives += 1

    total_positives = false_negatives + true_positives
    false_negative_rate = false_negatives / total_positives if total_positives > 0 else 0

    return {
        "false_negative_rate": false_negative_rate,
        "false_negatives": false_negatives,
        "true_positives": true_positives,
    }


def evaluate_severity_distribution(runs: List[Run], examples: List[Example]) -> Dict[str, Any]:
    """
    Analyzes the distribution of severity levels in flagged transactions.

    Args:
        runs: List of LangSmith runs
        examples: List of test examples

    Returns:
        Dictionary with severity distribution metrics
    """
    severity_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    total_flagged = 0

    for run in runs:
        outputs = run.outputs or {}
        alert = outputs.get("alert")

        if alert:
            total_flagged += 1
            severity = alert.get("severity")
            if severity in severity_counts:
                severity_counts[severity] += 1

    # Calculate percentages
    severity_percentages = {
        severity: (count / total_flagged * 100) if total_flagged > 0 else 0
        for severity, count in severity_counts.items()
    }

    return {
        "severity_counts": severity_counts,
        "severity_percentages": severity_percentages,
        "total_flagged": total_flagged,
    }
