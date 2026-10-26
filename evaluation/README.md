# AML Transaction Flagging Evaluation

This directory contains comprehensive evaluation tools for testing the accuracy and reliability of the AML (Anti-Money Laundering) transaction flagging system.

## Overview

The evaluation system checks whether the AML agent correctly identifies and flags suspicious transactions based on various risk indicators including:

- **Sanctions matches**: Transactions to/from sanctioned countries
- **Structuring patterns**: Multiple transactions designed to evade reporting thresholds
- **Unusually large amounts**: Transactions significantly larger than customer's typical behavior
- **High frequency**: Excessive transaction volume in a short period
- **Normal transactions**: Legitimate transactions that should not be flagged

## Components

### 1. Evaluator (`aml_evaluator.py`)

The main evaluation logic that scores agent performance across multiple dimensions:

#### Primary Evaluator: `evaluate_transaction_flagging()`

Evaluates each transaction on:
- **Flag Correctness (40% weight)**: Did the agent correctly flag or not flag the transaction?
- **Severity Accuracy (25% weight)**: Was the severity level (LOW/MEDIUM/HIGH/CRITICAL) appropriate?
- **Indicator Detection (20% weight)**: Did the agent detect the expected risk indicators?
- **Risk Score Accuracy (15% weight)**: Was the risk score (0-100) in the expected range?

Returns an overall accuracy score and detailed feedback.

#### Aggregate Metrics

Additional evaluators calculate:
- **False Positive Rate**: Percentage of legitimate transactions incorrectly flagged
- **False Negative Rate**: Percentage of suspicious transactions missed
- **Severity Distribution**: Breakdown of alert severity levels

### 2. Test Dataset (`test_dataset.py`)

Curated test cases organized by category:

| Category | Test Cases | Description |
|----------|-----------|-------------|
| Sanctions | 3 | Transactions to Iran, North Korea, Syria |
| Structuring | 2 | Multiple transactions near $10k threshold |
| Large Amounts | 2 | Unusually large transactions vs. history |
| High Frequency | 1 | Excessive transaction volume |
| Normal | 4 | Legitimate transactions (true negatives) |
| Edge Cases | 2 | Boundary conditions |

**Total**: 14 comprehensive test cases covering all major risk scenarios

Each test case includes:
```python
{
    "inputs": {
        "transaction": {...},        # Transaction details
        "customer_history": [...]    # Historical transactions
    },
    "outputs": {
        "should_flag": bool,              # Expected flag decision
        "expected_severity": str,         # Expected severity level
        "expected_indicators": [str],     # Expected risk indicators
        "min_risk_score": int,            # Minimum expected score
        "max_risk_score": int             # Maximum expected score
    },
    "metadata": {
        "category": str,                  # Test category
        "description": str,               # Human-readable description
        "test_type": str                  # true_positive/true_negative
    }
}
```

### 3. Evaluation Runner (`run_evaluation.py`)

Automated script that:
1. Creates/updates test dataset in LangSmith
2. Runs AML agent on all test cases
3. Applies evaluators to measure accuracy
4. Generates comprehensive evaluation report
5. Saves results to JSON file

## Usage

### Quick Start

Run the complete evaluation suite:

```bash
cd /path/to/deep_agent_finance_demo
python -m evaluation.run_evaluation
```

### Expected Output

```
============================================================
AML TRANSACTION FLAGGING EVALUATION
============================================================

Project: financial_services_deep_agent_demo
Dataset: aml-transaction-flagging-tests
Time: 2026-01-13 10:30:00

============================================================
Creating/Updating Dataset: aml-transaction-flagging-tests
============================================================

Total test cases: 14
Categories: {'sanctions': 3, 'structuring': 2, 'large_amount': 2, ...}
Expected positives: 8
Expected negatives: 6

✓ Dataset ready with 14 test cases

============================================================
Running Evaluation
============================================================

Running AML agent on 14 test cases...

  [1/14] Testing: Transfer to sanctioned country (Iran)
  [2/14] Testing: Transfer to sanctioned country (North Korea)
  ...
  [14/14] Testing: Large transaction consistent with business pattern

✓ All test cases executed

============================================================
EVALUATION RESULTS
============================================================

Overall Accuracy: 92.50%
Total Test Cases: 14

------------------------------------------------------------

CLASSIFICATION METRICS:
  True Positives:    8
  True Negatives:    5
  False Positives:   1
  False Negatives:   0

  Precision: 88.89%
  Recall:    100.00%
  F1 Score:  94.12%

  False Positive Rate: 16.67%
  False Negative Rate: 0.00%

------------------------------------------------------------

COMPONENT SCORES:
  Flag Correctness:    92.86%
  Severity Accuracy:   95.00%
  Indicator Detection: 90.00%
  Risk Score Accuracy: 88.75%

------------------------------------------------------------

SEVERITY DISTRIBUTION:
  Total Flagged: 9
    CRITICAL:   4 ( 44.4%)
    HIGH   :    3 ( 33.3%)
    MEDIUM :    2 ( 22.2%)
    LOW    :    0 (  0.0%)

============================================================

✓ Results saved to: evaluation_results_20260113_103045.json
✓ Evaluation passed (accuracy >= 80%)
```

### Integration with LangSmith

The evaluation automatically integrates with LangSmith for:

1. **Dataset Management**: Test cases are stored as a versioned dataset
2. **Trace Collection**: All agent runs are traced and viewable in LangSmith UI
3. **Evaluation Metrics**: Results are logged for comparison across runs
4. **Historical Analysis**: Track accuracy improvements over time

View results at: https://smith.langchain.com/

### Custom Evaluation

Use individual evaluators programmatically:

```python
from evaluation import (
    evaluate_transaction_flagging,
    evaluate_false_positive_rate,
    get_test_dataset
)

# Get test data
test_cases = get_test_dataset()

# Run your agent
for test_case in test_cases:
    result = run_aml_agent(test_case['inputs'])

    # Evaluate
    score = evaluate_transaction_flagging(result, test_case)
    print(f"Score: {score['score']:.2%}")
    print(f"Feedback: {score['comment']}")
```

### Adding New Test Cases

To add custom test cases:

1. Edit `test_dataset.py`
2. Add a new test case dictionary following the schema
3. Re-run evaluation to include new cases

Example:

```python
{
    "inputs": {
        "transaction": {
            "transaction_id": "TEST-CUSTOM-001",
            "customer_id": "CUST-999",
            "amount": 25000.0,
            "currency": "USD",
            "transaction_type": "transfer",
            "origin": "United States",
            "destination": "Panama",
            "timestamp": datetime.now().isoformat(),
            "description": "Custom test case",
        },
        "customer_history": [],
    },
    "outputs": {
        "should_flag": True,
        "expected_severity": "HIGH",
        "expected_indicators": ["HIGH_RISK_JURISDICTION"],
        "min_risk_score": 60,
        "max_risk_score": 80,
    },
    "metadata": {
        "category": "custom",
        "description": "Test case description",
        "test_type": "true_positive",
    },
}
```

## Evaluation Metrics

### Primary Metrics

- **Overall Accuracy**: Weighted average of all component scores (target: ≥ 80%)
- **Precision**: Of flagged transactions, how many were actually suspicious?
- **Recall**: Of suspicious transactions, how many were flagged?
- **F1 Score**: Harmonic mean of precision and recall

### Error Analysis

- **False Positives**: Legitimate transactions incorrectly flagged (target: < 10%)
- **False Negatives**: Suspicious transactions missed (target: < 5%)

### Component Scores

- **Flag Correctness**: Binary decision accuracy
- **Severity Accuracy**: Severity level appropriateness
- **Indicator Detection**: Risk indicator completeness
- **Risk Score Accuracy**: Numeric score precision

## Continuous Improvement

### Baseline Establishment

Run evaluation regularly to establish baseline:
```bash
# Run and save baseline
python -m evaluation.run_evaluation > baseline_results.txt
```

### Regression Testing

Before deploying changes:
```bash
# Run evaluation and compare to baseline
python -m evaluation.run_evaluation
# Check that accuracy >= baseline
```

### A/B Testing

Compare different agent versions:
```python
# Test agent v1
results_v1 = run_evaluation(agent_v1)

# Test agent v2
results_v2 = run_evaluation(agent_v2)

# Compare
print(f"V1 Accuracy: {results_v1['overall_accuracy']:.2%}")
print(f"V2 Accuracy: {results_v2['overall_accuracy']:.2%}")
```

## Best Practices

1. **Run before deployment**: Always run evaluation before deploying agent changes
2. **Track over time**: Monitor accuracy trends in LangSmith
3. **Investigate failures**: Review false positives/negatives to improve agent logic
4. **Update test cases**: Add real-world edge cases as they're discovered
5. **Set thresholds**: Establish minimum acceptable accuracy levels (e.g., 80% overall, <10% FP rate)

## Files

- `aml_evaluator.py` - Evaluation logic and metrics
- `test_dataset.py` - Curated test cases
- `run_evaluation.py` - Automated evaluation runner
- `README.md` - This documentation
- `__init__.py` - Package initialization

## Requirements

Ensure these packages are installed:
```bash
pip install langsmith langchain langchain-core
```

## Troubleshooting

### "Dataset not found" error
Ensure LangSmith API key is set:
```bash
export LANGCHAIN_API_KEY="your-api-key"
```

### "Module not found" error
Run from project root:
```bash
cd /path/to/deep_agent_finance_demo
python -m evaluation.run_evaluation
```

### Low accuracy scores
Review failed test cases in output and check:
- Agent logic in `agents/aml_agent.py`
- Risk thresholds and weights
- Indicator detection logic

## Future Enhancements

Potential improvements:
- [ ] Parameterized test generation for edge cases
- [ ] Integration with CI/CD pipeline
- [ ] Real-time monitoring and alerting
- [ ] Comparative analysis across model versions
- [ ] Performance benchmarking (latency, throughput)
- [ ] Cost analysis per evaluation run
