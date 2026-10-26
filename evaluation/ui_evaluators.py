"""Simple evaluators designed to be configured in the LangSmith UI.

These evaluators are intentionally simple and use LangSmith's standard patterns
for easy configuration through the UI.
"""

from typing import Dict, Any


def simple_correctness_evaluator(outputs: Dict[str, Any], reference_outputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simple correctness evaluator that can be configured in LangSmith UI.

    Checks if the agent's flagging decision matches the expected decision.

    Args:
        outputs: Agent outputs with 'alert' key
        reference_outputs: Expected outputs with 'should_flag' key

    Returns:
        Dict with score and comment for LangSmith UI
    """
    # Get actual and expected
    alert = outputs.get("alert")
    actual_flagged = alert is not None
    expected_flagged = reference_outputs.get("should_flag", False)

    # Calculate score
    if actual_flagged == expected_flagged:
        score = 1.0
        if actual_flagged:
            comment = "✓ Correctly flagged suspicious transaction"
        else:
            comment = "✓ Correctly identified as normal transaction"
    else:
        score = 0.0
        if expected_flagged:
            comment = "✗ MISS: Should have flagged but didn't (False Negative)"
        else:
            comment = "✗ FALSE POSITIVE: Flagged when shouldn't have"

    return {
        "score": score,
        "comment": comment,
    }


def severity_accuracy_evaluator(outputs: Dict[str, Any], reference_outputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates if the severity level is correct.

    Args:
        outputs: Agent outputs with 'alert' key
        reference_outputs: Expected outputs with 'expected_severity' key

    Returns:
        Dict with score and comment for LangSmith UI
    """
    alert = outputs.get("alert")
    expected_severity = reference_outputs.get("expected_severity")

    # If no alert expected and none generated, perfect
    if not reference_outputs.get("should_flag", False) and alert is None:
        return {
            "score": 1.0,
            "comment": "✓ No alert needed - transaction is normal",
        }

    # If alert expected but not generated
    if alert is None:
        return {
            "score": 0.0,
            "comment": "✗ No alert generated but one was expected",
        }

    # Check severity
    actual_severity = alert.get("severity")

    if not expected_severity:
        return {
            "score": 1.0,
            "comment": f"Alert generated with severity: {actual_severity}",
        }

    if actual_severity == expected_severity:
        return {
            "score": 1.0,
            "comment": f"✓ Correct severity: {actual_severity}",
        }
    else:
        # Partial credit for being close
        severity_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        if actual_severity in severity_levels and expected_severity in severity_levels:
            expected_idx = severity_levels.index(expected_severity)
            actual_idx = severity_levels.index(actual_severity)
            diff = abs(expected_idx - actual_idx)
            score = max(0, 1.0 - (diff * 0.33))
            return {
                "score": score,
                "comment": f"⚠ Expected {expected_severity}, got {actual_severity} (off by {diff} level)",
            }
        else:
            return {
                "score": 0.0,
                "comment": f"✗ Expected {expected_severity}, got {actual_severity}",
            }


def risk_score_evaluator(outputs: Dict[str, Any], reference_outputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates if the risk score is in the expected range.

    Args:
        outputs: Agent outputs with 'alert' key
        reference_outputs: Expected outputs with 'min_risk_score' and 'max_risk_score'

    Returns:
        Dict with score and comment for LangSmith UI
    """
    alert = outputs.get("alert")
    min_expected = reference_outputs.get("min_risk_score", 0)
    max_expected = reference_outputs.get("max_risk_score", 100)

    # If no alert expected and none generated
    if not reference_outputs.get("should_flag", False) and alert is None:
        return {
            "score": 1.0,
            "comment": "✓ No alert - transaction is normal",
        }

    # If alert expected but not generated
    if alert is None:
        return {
            "score": 0.0,
            "comment": "✗ No alert generated",
        }

    # Check risk score
    actual_score = alert.get("risk_score", 0)

    if min_expected <= actual_score <= max_expected:
        return {
            "score": 1.0,
            "comment": f"✓ Risk score {actual_score} in range [{min_expected}-{max_expected}]",
        }
    else:
        # Partial credit based on distance
        if actual_score < min_expected:
            distance = min_expected - actual_score
        else:
            distance = actual_score - max_expected

        score = max(0, 1.0 - (distance / 100))
        return {
            "score": score,
            "comment": f"⚠ Risk score {actual_score} outside range [{min_expected}-{max_expected}]",
        }


# For LangSmith UI: Export as simple names
correctness = simple_correctness_evaluator
severity = severity_accuracy_evaluator
risk_score = risk_score_evaluator
