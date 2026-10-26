# AML Transaction Flagging Evaluation System

## Overview

A comprehensive LangSmith-integrated evaluation system for testing the accuracy and reliability of the AML (Anti-Money Laundering) transaction flagging agent.

## What Was Built

### 1. LLM-as-a-Judge Evaluator ✨

**File**: [evaluation/llm_judge_evaluator.py](evaluation/llm_judge_evaluator.py)

An intelligent evaluator that uses GPT-4o to assess the AML agent's performance. This appears in the LangSmith evaluators UI and provides:

- **Qualitative Assessment**: Nuanced evaluation of agent decisions
- **Component Scoring**: Breaks down performance into 4 dimensions
- **Reasoning**: Explains why scores were given
- **Critical Issues**: Identifies serious problems (missed threats, false positives)
- **Recommendations**: Suggests specific improvements

**Key Features**:
- Appears natively in LangSmith UI
- Provides rich, human-readable feedback
- Evaluates correctness, severity, indicators, and risk scores
- Weighted scoring (flag correctness is most important)

### 2. Rule-Based Evaluator

**File**: [evaluation/aml_evaluator.py](evaluation/aml_evaluator.py)

A deterministic evaluator that provides precise quantitative metrics:

- **Flag Correctness**: Binary decision accuracy (40% weight)
- **Severity Accuracy**: Severity level appropriateness (25% weight)
- **Indicator Detection**: Risk indicator completeness (20% weight)
- **Risk Score Accuracy**: Numeric score precision (15% weight)

Also includes aggregate metrics:
- False positive rate
- False negative rate
- Severity distribution

### 3. Comprehensive Test Dataset

**File**: [evaluation/test_dataset.py](evaluation/test_dataset.py)

14 curated test cases covering all major scenarios:

| Category | Cases | Examples |
|----------|-------|----------|
| **Sanctions** | 3 | Transactions to Iran, North Korea, Syria |
| **Structuring** | 2 | Multiple $9.5k deposits to evade $10k threshold |
| **Large Amounts** | 2 | $500k transfer vs. $2k average; $1M to Cayman Islands |
| **High Frequency** | 1 | 20 transactions in 20 days |
| **Normal** | 4 | Payroll deposits, ATM withdrawals, supplier payments |
| **Edge Cases** | 2 | Exactly $10k, large but consistent business transaction |

Each test case includes:
- Transaction details and customer history
- Expected flagging decision
- Expected severity, indicators, and risk score range
- Metadata for categorization and reporting

### 4. LangSmith Integration

**File**: [evaluation/run_langsmith_evaluation.py](evaluation/run_langsmith_evaluation.py)

Automated evaluation runner that:
1. Creates/updates dataset in LangSmith
2. Runs AML agent on all test cases
3. Applies LLM judge and/or rule-based evaluators
4. Logs everything to LangSmith with full traces
5. Generates comprehensive reports

**Two Modes**:
- `--mode llm`: LLM judge only (recommended)
- `--mode both`: LLM judge + rule-based (comprehensive)

### 5. Documentation & Examples

**Files**:
- [evaluation/README.md](evaluation/README.md) - Full documentation
- [evaluation/QUICKSTART.md](evaluation/QUICKSTART.md) - 5-minute getting started
- [evaluation/example_usage.py](evaluation/example_usage.py) - Code examples
- [evaluation/test_evaluator.py](evaluation/test_evaluator.py) - Unit tests

## Quick Start

### Run Evaluation

```bash
# Set API keys
export LANGCHAIN_API_KEY="your-langsmith-key"
export OPENAI_API_KEY="your-openai-key"

# Run evaluation with LLM judge
cd /path/to/deep_agent_finance_demo
python -m evaluation.run_langsmith_evaluation --mode llm
```

### View Results

Visit https://smith.langchain.com/ to see:
- Overall accuracy scores
- Individual test case results with LLM feedback
- Full execution traces
- Component score breakdowns
- Critical issues and recommendations

## Evaluation Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Test Dataset (14 cases)                                   │
│    • Sanctions, structuring, large amounts, normal, etc.    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Run AML Agent                                             │
│    • Analyze transaction + history                           │
│    • Generate alert (or not)                                 │
│    • Determine severity, indicators, risk score              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. LLM Judge Evaluates                                       │
│    • GPT-4o compares output vs. expected                     │
│    • Scores 4 dimensions (flag, severity, indicators, risk)  │
│    • Provides reasoning and recommendations                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Results in LangSmith                                      │
│    • Overall accuracy score                                  │
│    • Per-case feedback and traces                            │
│    • Aggregate metrics and charts                            │
└─────────────────────────────────────────────────────────────┘
```

## Key Metrics

### Overall Accuracy
Weighted average of component scores:
- **Target**: ≥ 80%
- **Weights**: Flag (40%), Severity (25%), Indicators (20%), Risk Score (15%)

### Classification Metrics
- **Precision**: Of flagged transactions, % actually suspicious
- **Recall**: Of suspicious transactions, % correctly flagged
- **F1 Score**: Harmonic mean of precision and recall

### Error Rates
- **False Positive Rate**: Legitimate transactions incorrectly flagged
  - **Target**: < 10%
- **False Negative Rate**: Suspicious transactions missed (CRITICAL!)
  - **Target**: < 5%

### Severity Distribution
Breakdown of alert severity levels:
- CRITICAL, HIGH, MEDIUM, LOW
- Should align with actual risk levels in test cases

## Example Output

```
============================================================
AML TRANSACTION FLAGGING EVALUATION
Using LLM-as-a-Judge Evaluator
============================================================

Project: financial_services_deep_agent_demo
Dataset: aml-transaction-flagging-tests

============================================================
Creating Dataset: aml-transaction-flagging-tests
============================================================

Total test cases: 14
Expected positives: 8
Expected negatives: 6

✓ Dataset ready with 14 test cases

============================================================
Running Evaluation
============================================================

Evaluator: LLM Judge (GPT-4o)
Starting experiment: aml-eval-20260113-103045

[Test cases run with LLM judge feedback...]

============================================================
Evaluation Complete!
============================================================

View results in LangSmith:
  https://smith.langchain.com/

The LangSmith UI shows:
  • Overall accuracy: 92.5%
  • 13/14 test cases passed
  • Detailed LLM feedback for each case
  • Component score breakdowns
  • Full traces for debugging
```

## LangSmith UI Features

### Evaluation Dashboard
- Aggregate metrics at a glance
- Score trends over time
- Comparison across experiments

### Test Case View
For each test case, see:
1. **Input**: Transaction + history
2. **Output**: Agent's decision
3. **Expected**: Correct decision
4. **LLM Feedback**:
   - Overall Score: 95%
   - Component Scores:
     - Flag Correctness: 100%
     - Severity Accuracy: 100%
     - Indicator Detection: 90%
     - Risk Score Accuracy: 85%
   - Reasoning: "Agent correctly identified..."
   - Critical Issues: []
   - Recommendations: ["Consider also checking..."]

### Trace View
- Step-by-step execution
- Intermediate results
- Timing information
- Debug information

## Use Cases

### 1. Baseline Establishment
```bash
# Run evaluation to establish baseline
python -m evaluation.run_langsmith_evaluation --mode llm

# Note the overall accuracy (e.g., 87%)
```

### 2. Regression Testing
```bash
# Before deploying changes
python -m evaluation.run_langsmith_evaluation --mode llm

# Compare to baseline in LangSmith UI
# Only deploy if accuracy >= baseline
```

### 3. A/B Testing
```python
# Test two different agent configurations
results_v1 = evaluate(agent_v1, data=DATASET_NAME, evaluators=[aml_llm_judge])
results_v2 = evaluate(agent_v2, data=DATASET_NAME, evaluators=[aml_llm_judge])

# Compare in LangSmith UI
```

### 4. Continuous Improvement
```bash
# Run evaluation regularly
python -m evaluation.run_langsmith_evaluation --mode llm

# Review failures in LangSmith
# Fix agent logic
# Re-run and verify improvement
```

### 5. CI/CD Integration
```yaml
# In your CI pipeline (e.g., GitHub Actions)
- name: Run AML Evaluation
  run: |
    python -m evaluation.run_langsmith_evaluation --mode llm
  env:
    LANGCHAIN_API_KEY: ${{ secrets.LANGCHAIN_API_KEY }}
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

## Files Created

```
evaluation/
├── __init__.py                    # Package initialization
├── README.md                      # Full documentation
├── QUICKSTART.md                  # 5-minute getting started guide
│
├── llm_judge_evaluator.py         # ⭐ LLM-as-a-judge evaluator
├── aml_evaluator.py               # Rule-based evaluator
├── test_dataset.py                # 14 curated test cases
│
├── run_langsmith_evaluation.py    # LangSmith integration script
├── run_evaluation.py              # Standalone evaluation script
├── example_usage.py               # Code examples
└── test_evaluator.py              # Unit tests
```

## Key Design Decisions

### Why LLM-as-a-Judge?
- **Nuanced Evaluation**: Can assess reasoning quality, not just metrics
- **Rich Feedback**: Provides actionable recommendations
- **Human-Like**: Evaluates like a compliance officer would
- **LangSmith Native**: Appears in evaluators UI automatically

### Why Also Keep Rule-Based?
- **Deterministic**: Consistent, reproducible scores
- **Fast**: No LLM API calls needed
- **Precise**: Exact numeric metrics
- **Fallback**: Works if LLM judge fails

### Why 14 Test Cases?
- **Comprehensive**: Covers all major risk categories
- **Manageable**: Fast to run, easy to understand
- **Balanced**: Mix of positives (8) and negatives (6)
- **Extensible**: Easy to add more cases

## Best Practices

### Before Deployment
1. Run evaluation to ensure accuracy ≥ 80%
2. Review any failures in LangSmith UI
3. Fix issues and re-evaluate
4. Only deploy when tests pass

### Monitoring
1. Run evaluation weekly
2. Track accuracy trends in LangSmith
3. Investigate any degradation
4. Add real-world edge cases to test dataset

### Debugging Failures
1. Find failed test case in LangSmith UI
2. Read LLM judge feedback for specific issues
3. View full trace to see agent reasoning
4. Fix agent logic in [agents/aml_agent.py](agents/aml_agent.py)
5. Re-run evaluation to verify fix

### Adding Test Cases
1. Identify real-world edge case
2. Add to [test_dataset.py](evaluation/test_dataset.py)
3. Define expected outputs
4. Re-run evaluation
5. Iterate on agent logic if needed

## Technical Details

### Evaluator Signature
```python
def evaluator(run: Run, example: Example) -> Dict[str, Any]:
    """
    Args:
        run: LangSmith run with agent outputs
        example: Test example with expected outputs

    Returns:
        {
            "key": "evaluator_name",
            "score": 0.0 to 1.0,
            "comment": "Feedback text",
            "metadata": {...}  # Optional
        }
    """
```

### Scoring Weights
```python
weights = {
    "flag_correctness": 0.40,    # Most critical
    "severity_accuracy": 0.25,   # Important
    "indicator_detection": 0.20, # Important
    "risk_score_accuracy": 0.15, # Less critical
}
```

### LLM Judge Model
- **Model**: GPT-4o (configurable)
- **Temperature**: 0 (deterministic)
- **Fallback**: Rule-based evaluator if LLM fails

## Future Enhancements

Potential improvements:
- [ ] Add more test cases (targeting 30-50)
- [ ] Parameterized test generation
- [ ] Performance benchmarking (latency, cost)
- [ ] Multi-model LLM judge comparison
- [ ] Real-time alerting on accuracy drops
- [ ] Integration with model versioning
- [ ] A/B testing automation
- [ ] Cost tracking per evaluation

## Support & Resources

- **Quick Start**: [QUICKSTART.md](evaluation/QUICKSTART.md)
- **Full Docs**: [evaluation/README.md](evaluation/README.md)
- **Examples**: [example_usage.py](evaluation/example_usage.py)
- **Tests**: [test_evaluator.py](evaluation/test_evaluator.py)
- **LangSmith Docs**: https://docs.smith.langchain.com/
- **LangSmith UI**: https://smith.langchain.com/

## Summary

You now have a production-ready evaluation system that:

✅ Uses LLM-as-a-judge for intelligent evaluation
✅ Integrates natively with LangSmith UI
✅ Provides comprehensive test coverage (14 test cases)
✅ Generates actionable feedback and recommendations
✅ Tracks metrics over time
✅ Supports CI/CD integration
✅ Is easy to extend and customize

**Get started in 5 minutes**: See [QUICKSTART.md](evaluation/QUICKSTART.md)
