# AML Evaluator Quick Start Guide

Get started with evaluating your AML transaction flagging system in 5 minutes.

## Prerequisites

Ensure you have API keys set:

```bash
export LANGCHAIN_API_KEY="your-langsmith-api-key"
export OPENAI_API_KEY="your-openai-api-key"
```

## Option 1: LLM-as-a-Judge Evaluation (Recommended)

Use an LLM to evaluate your AML agent's performance. Results appear in the LangSmith UI.

```bash
cd /path/to/deep_agent_finance_demo
python -m evaluation.run_langsmith_evaluation --mode llm
```

**What this does:**
1. Creates a dataset in LangSmith with 14 test cases
2. Runs your AML agent on each test case
3. Uses GPT-4o to evaluate each result
4. Logs everything to LangSmith with detailed feedback

**Expected output:**
```
============================================================
Creating Dataset: aml-transaction-flagging-tests
============================================================

Dataset Summary:
  Total test cases: 14
  Expected positives: 8
  Expected negatives: 6

✓ Created dataset

============================================================
Running Evaluation
============================================================

Evaluator: LLM Judge (GPT-4o)
Starting experiment: aml-eval-20260113-103045

[Running evaluation...]

============================================================
Evaluation Complete!
============================================================

View detailed results in LangSmith:
  https://smith.langchain.com/
```

## Option 2: Dual Evaluation (LLM + Rule-Based)

Get both qualitative LLM feedback and quantitative metrics:

```bash
python -m evaluation.run_langsmith_evaluation --mode both
```

**What you get:**
- **LLM Judge**: Nuanced evaluation with reasoning and recommendations
- **Rule-Based**: Precise numeric scores for flag correctness, severity, indicators, etc.

## Option 3: Custom Evaluation Script

For more control, use the programmatic API:

```python
from langsmith.evaluation import evaluate
from evaluation import aml_llm_judge
from agents.aml_agent import analyze_transaction

# Your prediction function
async def predict(inputs):
    transaction = inputs["transaction"]
    history = inputs.get("customer_history", [])
    result = await analyze_transaction(transaction, history)
    return {"alert": result.get("alert")}

# Run evaluation
results = evaluate(
    predict,
    data="aml-transaction-flagging-tests",
    evaluators=[aml_llm_judge],
    experiment_prefix="my-aml-test",
)
```

## What You'll See in LangSmith

### 1. Evaluation Dashboard
- Overall accuracy score
- Pass/fail rate
- Component score breakdown

### 2. Individual Test Cases
For each test case:
- **Input**: Transaction details and history
- **Output**: Agent's flagging decision
- **Expected**: What the correct decision should be
- **LLM Feedback**: Detailed evaluation with:
  - Component scores (flag correctness, severity, indicators, risk score)
  - Reasoning for the scores
  - Critical issues identified
  - Recommendations for improvement

### 3. Traces
- Full execution trace for each test case
- Step-by-step agent reasoning
- Useful for debugging failures

## Understanding the Scores

### Overall Score
Weighted average of component scores:
- **Flag Correctness (40%)**: Did agent flag/not flag correctly?
- **Severity Accuracy (25%)**: Was severity level appropriate?
- **Indicator Detection (20%)**: Were risk indicators identified?
- **Risk Score Accuracy (15%)**: Was risk score in expected range?

### Target Metrics
- Overall Accuracy: ≥ 80%
- False Positive Rate: < 10%
- False Negative Rate: < 5% (critical!)

## Test Dataset

The evaluation includes 14 carefully curated test cases:

| Category | Cases | Description |
|----------|-------|-------------|
| Sanctions | 3 | Transactions to Iran, North Korea, Syria |
| Structuring | 2 | Multiple transactions near $10k threshold |
| Large Amounts | 2 | Unusually large vs. customer history |
| High Frequency | 1 | Excessive transaction volume |
| Normal | 4 | Legitimate transactions (should not flag) |
| Edge Cases | 2 | Boundary conditions |

## Common Issues

### "Dataset not found"
Run the evaluation script once to create the dataset:
```bash
python -m evaluation.run_langsmith_evaluation --mode llm
```

### "LANGCHAIN_API_KEY not found"
Set your LangSmith API key:
```bash
export LANGCHAIN_API_KEY="your-key"
```
Get one at: https://smith.langchain.com/settings

### "OPENAI_API_KEY not found"
Set your OpenAI API key (needed for LLM judge):
```bash
export OPENAI_API_KEY="your-key"
```

### Low Accuracy Scores
Review failed cases in LangSmith UI:
1. Look at LLM judge feedback for specific issues
2. Check agent traces to see reasoning
3. Adjust agent logic in [agents/aml_agent.py](../agents/aml_agent.py)
4. Re-run evaluation

## Next Steps

1. **Baseline**: Run evaluation to establish baseline accuracy
2. **Iterate**: Make improvements to agent logic
3. **Compare**: Re-run evaluation and compare to baseline
4. **CI/CD**: Integrate into your deployment pipeline
5. **Monitor**: Track accuracy trends over time in LangSmith

## Advanced Usage

### Add Custom Test Cases

Edit [test_dataset.py](test_dataset.py) and add your test case:

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
        "description": "My custom test case",
        "test_type": "true_positive",
    },
}
```

### Use Different LLM for Judge

Edit [llm_judge_evaluator.py](llm_judge_evaluator.py):

```python
# Change this line:
judge_llm = ChatOpenAI(model="gpt-4o", temperature=0)

# To use a different model:
judge_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)  # Cheaper
# or
judge_llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")  # Claude
```

### Run in CI/CD

Add to your CI pipeline:

```bash
# In your CI script
python -m evaluation.run_langsmith_evaluation --mode llm

# Check exit code
if [ $? -eq 0 ]; then
    echo "Evaluation passed"
else
    echo "Evaluation failed - check LangSmith"
    exit 1
fi
```

## Support

- 📖 Full Documentation: [README.md](README.md)
- 💻 Example Code: [example_usage.py](example_usage.py)
- 🧪 Unit Tests: [test_evaluator.py](test_evaluator.py)
- 🌐 LangSmith Docs: https://docs.smith.langchain.com/

## Feedback

Found an issue or have suggestions? Please let us know!
