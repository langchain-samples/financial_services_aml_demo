"""Unit tests for the AML evaluator.

Run with: pytest evaluation/test_evaluator.py -v
"""

import pytest
from datetime import datetime
from evaluation.aml_evaluator import (
    evaluate_transaction_flagging,
    evaluate_false_positive_rate,
    evaluate_false_negative_rate,
    evaluate_severity_distribution,
)
from evaluation.test_dataset import get_test_dataset, get_dataset_summary


class MockRun:
    """Mock LangSmith Run object for testing."""

    def __init__(self, outputs):
        self.outputs = outputs


class MockExample:
    """Mock LangSmith Example object for testing."""

    def __init__(self, inputs, outputs):
        self.inputs = inputs
        self.outputs = outputs


class TestEvaluateTransactionFlagging:
    """Tests for the main evaluator function."""

    def test_correct_flag_high_score(self):
        """Test that correctly flagging a transaction gives high score."""
        example = MockExample(
            inputs={},
            outputs={
                "should_flag": True,
                "expected_severity": "CRITICAL",
                "expected_indicators": ["SANCTIONS_MATCH"],
                "min_risk_score": 70,
                "max_risk_score": 100,
            },
        )

        run = MockRun(
            outputs={
                "alert": {
                    "severity": "CRITICAL",
                    "risk_score": 85,
                    "indicators": ["SANCTIONS_MATCH"],
                }
            }
        )

        result = evaluate_transaction_flagging(run, example)

        assert result["score"] >= 0.9, "Perfect match should score >= 90%"
        assert result["scores"]["flag_correctness"] == 1.0
        assert result["scores"]["severity_accuracy"] == 1.0
        assert result["scores"]["indicator_detection"] == 1.0
        assert result["scores"]["risk_score_accuracy"] == 1.0

    def test_correct_no_flag_high_score(self):
        """Test that correctly not flagging gives high score."""
        example = MockExample(
            inputs={},
            outputs={
                "should_flag": False,
                "expected_severity": None,
                "expected_indicators": [],
                "min_risk_score": 0,
                "max_risk_score": 30,
            },
        )

        run = MockRun(outputs={"alert": None})

        result = evaluate_transaction_flagging(run, example)

        assert result["score"] == 1.0, "Correct non-flag should score 100%"
        assert result["scores"]["flag_correctness"] == 1.0

    def test_false_positive_low_score(self):
        """Test that false positive (flagging when shouldn't) gives low score."""
        example = MockExample(
            inputs={},
            outputs={
                "should_flag": False,
                "expected_severity": None,
                "expected_indicators": [],
                "min_risk_score": 0,
                "max_risk_score": 30,
            },
        )

        run = MockRun(
            outputs={
                "alert": {
                    "severity": "HIGH",
                    "risk_score": 70,
                    "indicators": ["LARGE_AMOUNT"],
                }
            }
        )

        result = evaluate_transaction_flagging(run, example)

        assert result["score"] < 0.5, "False positive should score low"
        assert result["scores"]["flag_correctness"] == 0.0

    def test_false_negative_low_score(self):
        """Test that false negative (not flagging when should) gives low score."""
        example = MockExample(
            inputs={},
            outputs={
                "should_flag": True,
                "expected_severity": "CRITICAL",
                "expected_indicators": ["SANCTIONS_MATCH"],
                "min_risk_score": 70,
                "max_risk_score": 100,
            },
        )

        run = MockRun(outputs={"alert": None})

        result = evaluate_transaction_flagging(run, example)

        assert result["score"] < 0.5, "False negative should score low"
        assert result["scores"]["flag_correctness"] == 0.0

    def test_partial_credit_severity_mismatch(self):
        """Test partial credit for close severity level."""
        example = MockExample(
            inputs={},
            outputs={
                "should_flag": True,
                "expected_severity": "CRITICAL",
                "expected_indicators": ["SANCTIONS_MATCH"],
                "min_risk_score": 70,
                "max_risk_score": 100,
            },
        )

        run = MockRun(
            outputs={
                "alert": {
                    "severity": "HIGH",  # One level below CRITICAL
                    "risk_score": 85,
                    "indicators": ["SANCTIONS_MATCH"],
                }
            }
        )

        result = evaluate_transaction_flagging(run, example)

        # Should get partial credit for severity
        assert 0.5 < result["score"] < 1.0, "Should get partial credit"
        assert result["scores"]["flag_correctness"] == 1.0
        assert 0 < result["scores"]["severity_accuracy"] < 1.0

    def test_partial_credit_missing_indicators(self):
        """Test partial credit for missing some indicators."""
        example = MockExample(
            inputs={},
            outputs={
                "should_flag": True,
                "expected_severity": "HIGH",
                "expected_indicators": ["STRUCTURING", "HIGH_FREQUENCY"],
                "min_risk_score": 60,
                "max_risk_score": 80,
            },
        )

        run = MockRun(
            outputs={
                "alert": {
                    "severity": "HIGH",
                    "risk_score": 70,
                    "indicators": ["STRUCTURING"],  # Missing HIGH_FREQUENCY
                }
            }
        )

        result = evaluate_transaction_flagging(run, example)

        # Should get partial credit for indicators
        assert result["scores"]["indicator_detection"] == 0.5
        assert 0.6 < result["score"] < 0.95

    def test_risk_score_out_of_range(self):
        """Test penalty for risk score outside expected range."""
        example = MockExample(
            inputs={},
            outputs={
                "should_flag": True,
                "expected_severity": "MEDIUM",
                "expected_indicators": ["HIGH_FREQUENCY"],
                "min_risk_score": 40,
                "max_risk_score": 60,
            },
        )

        run = MockRun(
            outputs={
                "alert": {
                    "severity": "MEDIUM",
                    "risk_score": 80,  # Above expected range
                    "indicators": ["HIGH_FREQUENCY"],
                }
            }
        )

        result = evaluate_transaction_flagging(run, example)

        # Should get reduced risk_score_accuracy
        assert result["scores"]["risk_score_accuracy"] < 1.0


class TestAggregateFunctions:
    """Tests for aggregate evaluation functions."""

    def test_false_positive_rate_calculation(self):
        """Test false positive rate calculation."""
        examples = [
            MockExample({}, {"should_flag": False}),
            MockExample({}, {"should_flag": False}),
            MockExample({}, {"should_flag": False}),
            MockExample({}, {"should_flag": False}),
        ]

        runs = [
            MockRun({"alert": None}),  # True negative
            MockRun({"alert": {"severity": "LOW"}}),  # False positive
            MockRun({"alert": None}),  # True negative
            MockRun({"alert": {"severity": "MEDIUM"}}),  # False positive
        ]

        result = evaluate_false_positive_rate(runs, examples)

        assert result["false_positives"] == 2
        assert result["true_negatives"] == 2
        assert result["false_positive_rate"] == 0.5

    def test_false_negative_rate_calculation(self):
        """Test false negative rate calculation."""
        examples = [
            MockExample({}, {"should_flag": True}),
            MockExample({}, {"should_flag": True}),
            MockExample({}, {"should_flag": True}),
            MockExample({}, {"should_flag": True}),
        ]

        runs = [
            MockRun({"alert": {"severity": "HIGH"}}),  # True positive
            MockRun({"alert": None}),  # False negative
            MockRun({"alert": {"severity": "CRITICAL"}}),  # True positive
            MockRun({"alert": None}),  # False negative
        ]

        result = evaluate_false_negative_rate(runs, examples)

        assert result["false_negatives"] == 2
        assert result["true_positives"] == 2
        assert result["false_negative_rate"] == 0.5

    def test_severity_distribution(self):
        """Test severity distribution calculation."""
        examples = [MockExample({}, {}) for _ in range(5)]

        runs = [
            MockRun({"alert": {"severity": "CRITICAL"}}),
            MockRun({"alert": {"severity": "HIGH"}}),
            MockRun({"alert": {"severity": "HIGH"}}),
            MockRun({"alert": {"severity": "MEDIUM"}}),
            MockRun({"alert": None}),  # Not flagged
        ]

        result = evaluate_severity_distribution(runs, examples)

        assert result["total_flagged"] == 4
        assert result["severity_counts"]["CRITICAL"] == 1
        assert result["severity_counts"]["HIGH"] == 2
        assert result["severity_counts"]["MEDIUM"] == 1
        assert result["severity_counts"]["LOW"] == 0
        assert result["severity_percentages"]["CRITICAL"] == 25.0
        assert result["severity_percentages"]["HIGH"] == 50.0


class TestDataset:
    """Tests for the test dataset."""

    def test_dataset_not_empty(self):
        """Test that dataset contains test cases."""
        dataset = get_test_dataset()
        assert len(dataset) > 0, "Dataset should not be empty"

    def test_dataset_structure(self):
        """Test that each test case has required structure."""
        dataset = get_test_dataset()

        for case in dataset:
            # Check inputs
            assert "inputs" in case
            assert "transaction" in case["inputs"]
            assert "customer_history" in case["inputs"]

            # Check outputs
            assert "outputs" in case
            assert "should_flag" in case["outputs"]
            assert "expected_severity" in case["outputs"]
            assert "expected_indicators" in case["outputs"]
            assert "min_risk_score" in case["outputs"]
            assert "max_risk_score" in case["outputs"]

            # Check metadata
            assert "metadata" in case
            assert "category" in case["metadata"]
            assert "description" in case["metadata"]
            assert "test_type" in case["metadata"]

            # Validate transaction structure
            txn = case["inputs"]["transaction"]
            assert "transaction_id" in txn
            assert "customer_id" in txn
            assert "amount" in txn
            assert "currency" in txn
            assert "transaction_type" in txn
            assert "origin" in txn
            assert "destination" in txn
            assert "timestamp" in txn

    def test_dataset_summary(self):
        """Test dataset summary generation."""
        summary = get_dataset_summary()

        assert "total_cases" in summary
        assert "categories" in summary
        assert "test_types" in summary
        assert "expected_positives" in summary
        assert "expected_negatives" in summary

        assert summary["total_cases"] > 0
        assert summary["expected_positives"] > 0
        assert summary["expected_negatives"] > 0

    def test_dataset_balance(self):
        """Test that dataset is reasonably balanced."""
        summary = get_dataset_summary()

        total = summary["total_cases"]
        positives = summary["expected_positives"]
        negatives = summary["expected_negatives"]

        # Should have both positive and negative cases
        assert positives > 0, "Need positive test cases"
        assert negatives > 0, "Need negative test cases"

        # Neither should dominate too heavily (reasonable balance)
        assert positives / total >= 0.3, "At least 30% should be positive"
        assert negatives / total >= 0.3, "At least 30% should be negative"

    def test_dataset_categories_coverage(self):
        """Test that dataset covers major risk categories."""
        summary = get_dataset_summary()
        categories = summary["categories"]

        # Should have multiple categories
        assert len(categories) >= 4, "Should have at least 4 categories"

        # Should cover key risk areas
        expected_categories = ["sanctions", "structuring", "large_amount", "normal"]
        for category in expected_categories:
            assert (
                category in categories
            ), f"Should have {category} test cases"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
