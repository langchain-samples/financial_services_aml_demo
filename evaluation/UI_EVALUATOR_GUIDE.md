# Configuring Evaluators in LangSmith UI

This guide shows how to configure evaluators directly in the LangSmith UI for demos and quick testing.

## Why Use UI Evaluators?

- **Quick Setup**: No code needed, configure through UI
- **Demo Friendly**: Easy to show during presentations
- **Visual**: See evaluator configuration and results in one place
- **Sharable**: Team members can configure without coding

## Available Simple Evaluators

We've created 3 simple evaluators in [ui_evaluators.py](ui_evaluators.py):

1. **Correctness**: Did agent flag correctly? (binary pass/fail)
2. **Severity**: Was severity level appropriate?
3. **Risk Score**: Was risk score in expected range?

## How to Configure in LangSmith UI

### Step 1: Navigate to Dataset

1. Go to https://smith.langchain.com/
2. Click **Datasets** in left sidebar
3. Select `aml-transaction-flagging-tests`

### Step 2: Create Evaluator

1. Click **"Create your first evaluator"** (or **"Add evaluator"**)
2. Choose evaluator type:

#### Option A: Custom Code Evaluator (Recommended for our evaluators)

1. Select **"Custom Code"**
2. **Name**: `AML Correctness Checker`
3. **Code**:
```python
def evaluate(outputs: dict, reference_outputs: dict) -> dict:
    """Check if agent correctly flagged transaction."""
    alert = outputs.get("alert")
    actual_flagged = alert is not None
    expected_flagged = reference_outputs.get("should_flag", False)

    if actual_flagged == expected_flagged:
        score = 1.0
        if actual_flagged:
            comment = "✓ Correctly flagged suspicious transaction"
        else:
            comment = "✓ Correctly identified as normal transaction"
    else:
        score = 0.0
        if expected_flagged:
            comment = "✗ MISS: Should have flagged but didn't"
        else:
            comment = "✗ FALSE POSITIVE: Flagged incorrectly"

    return {"score": score, "comment": comment}
```
4. Click **"Create"**

#### Option B: LLM as Judge (Alternative)

1. Select **"LLM as Judge"**
2. **Name**: `AML LLM Evaluator`
3. **Prompt Template**:
```
You are evaluating an AML transaction flagging system.

Transaction: {input}
Agent Decision: {output}
Expected Decision: {reference}

Did the agent correctly flag this transaction?
- If the agent should flag and did: Score 1.0
- If the agent should not flag and didn't: Score 1.0
- Otherwise: Score 0.0

Return a JSON with:
{
  "score": 0.0 to 1.0,
  "reasoning": "brief explanation"
}
```
4. **Model**: `gpt-4o` or `gpt-4o-mini`
5. Click **"Create"**

### Step 3: Run Evaluation

Once evaluator is configured:

1. Click **"Run Evaluation"** on the dataset page
2. Select your evaluator(s)
3. Choose or upload test runs
4. Click **"Start Evaluation"**

Results will show:
- Overall accuracy
- Per-example scores
- Comments/feedback for each

## Example Evaluators You Can Copy-Paste

### 1. Simple Correctness (Binary)

```python
def evaluate(outputs: dict, reference_outputs: dict) -> dict:
    alert = outputs.get("alert")
    expected = reference_outputs.get("should_flag", False)
    actual = alert is not None

    score = 1.0 if actual == expected else 0.0
    comment = "Correct" if score == 1.0 else "Incorrect"

    return {"score": score, "comment": comment}
```

### 2. Severity with Partial Credit

```python
def evaluate(outputs: dict, reference_outputs: dict) -> dict:
    alert = outputs.get("alert")
    expected_severity = reference_outputs.get("expected_severity")

    if not alert:
        return {"score": 0.0, "comment": "No alert generated"}

    actual = alert.get("severity")

    if actual == expected_severity:
        return {"score": 1.0, "comment": f"Correct: {actual}"}

    # Partial credit
    levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    if actual in levels and expected_severity in levels:
        diff = abs(levels.index(actual) - levels.index(expected_severity))
        score = max(0, 1.0 - (diff * 0.33))
        return {
            "score": score,
            "comment": f"Expected {expected_severity}, got {actual}"
        }

    return {"score": 0.0, "comment": "Invalid severity"}
```

### 3. Risk Score Range

```python
def evaluate(outputs: dict, reference_outputs: dict) -> dict:
    alert = outputs.get("alert")
    min_score = reference_outputs.get("min_risk_score", 0)
    max_score = reference_outputs.get("max_risk_score", 100)

    if not alert:
        return {"score": 0.0, "comment": "No alert"}

    actual = alert.get("risk_score", 0)

    if min_score <= actual <= max_score:
        return {
            "score": 1.0,
            "comment": f"Risk score {actual} in range [{min_score}-{max_score}]"
        }

    # Partial credit for being close
    distance = min(abs(actual - min_score), abs(actual - max_score))
    score = max(0, 1.0 - (distance / 100))

    return {
        "score": score,
        "comment": f"Risk score {actual} outside range"
    }
```

## Demo Flow

For a live demo, follow this flow:

### 1. Show the Dataset
- Navigate to the dataset
- Show the 14 test cases
- Explain the categories (sanctions, structuring, etc.)

### 2. Configure Evaluator in UI
- Click "Create evaluator"
- Copy-paste the "Simple Correctness" code above
- Name it something descriptive
- Save it

### 3. Run Test Experiment
From command line:
```bash
python -m evaluation.run_langsmith_evaluation --mode llm
```

### 4. Show Results
- Go to Experiments tab
- Click on the latest experiment
- Show:
  - Overall accuracy metric
  - Per-test-case results
  - Both UI evaluator and LLM judge results
  - Traces for debugging

### 5. Compare Evaluators
Show how:
- Simple correctness gives binary pass/fail
- LLM judge provides detailed reasoning
- Multiple evaluators give different perspectives

## Benefits of UI Evaluators for Demos

✅ **No Code Deploy**: Configure during demo, no git push needed
✅ **Live Editing**: Modify evaluator logic in real-time
✅ **Visual**: Audience sees configuration and results
✅ **Interactive**: Can adjust thresholds and re-run
✅ **Accessible**: Non-technical stakeholders can understand

## When to Use Each Approach

| Approach | Best For |
|----------|----------|
| **UI Evaluators** | Demos, quick tests, stakeholder reviews |
| **Custom Code Evaluators** | Production, CI/CD, complex logic |
| **LLM as Judge** | Qualitative feedback, nuanced evaluation |

## Pro Tips

1. **Start Simple**: Use binary correctness for demos
2. **Add Complexity**: Show how to add partial credit
3. **Multiple Evaluators**: Run 2-3 evaluators to show different metrics
4. **Live Editing**: Adjust thresholds in UI during demo
5. **Compare Results**: Show UI vs LLM judge side-by-side

## Common Demo Questions & Answers

**Q: Can I use custom Python libraries?**
A: In UI evaluators, you're limited to standard library. For custom libs, use code-based approach.

**Q: How do I share evaluators with my team?**
A: UI evaluators are workspace-scoped. Team members can see and use them.

**Q: Can I export evaluator config?**
A: Not directly, but you can copy the code and save to version control.

**Q: Which is better: UI or code?**
A: UI for demos/exploration, code for production/CI-CD.

## Next Steps

After demo:
1. ✅ Show UI evaluators (simple, visual)
2. ✅ Show code-based evaluators (production-ready)
3. ✅ Show LLM judge (advanced, nuanced)
4. ✅ Discuss which approach fits their use case

For production deployments, recommend using the code-based evaluators in [llm_judge_evaluator.py](llm_judge_evaluator.py) and [aml_evaluator.py](aml_evaluator.py).
