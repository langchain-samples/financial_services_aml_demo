# Simple UI Evaluator - Copy & Paste Ready

Use this exact code when creating an evaluator in the LangSmith UI.

## Instructions

1. Go to your dataset in LangSmith: https://smith.langchain.com/
2. Click **"Create evaluator"** → **"Custom Code"**
3. Name: `AML Correctness`
4. Copy and paste the code below
5. Click **"Create"**

## Code to Copy

```python
def evaluate_example(run, example):
    """
    Evaluates if the AML agent correctly flagged the transaction.

    Args:
        run: The agent run with outputs
        example: The test example with expected outputs

    Returns:
        dict with score and comment
    """
    # Get actual output from agent
    outputs = run.outputs if hasattr(run, 'outputs') else {}
    alert = outputs.get("alert")
    actual_flagged = alert is not None

    # Get expected output
    reference = example.outputs if hasattr(example, 'outputs') else {}
    expected_flagged = reference.get("should_flag", False)

    # Calculate score
    if actual_flagged == expected_flagged:
        score = 1.0
        if actual_flagged:
            comment = "✓ Correctly flagged as suspicious"
        else:
            comment = "✓ Correctly identified as normal"
    else:
        score = 0.0
        if expected_flagged:
            comment = "✗ MISS: Should have flagged this transaction"
        else:
            comment = "✗ FALSE POSITIVE: Incorrectly flagged normal transaction"

    return {
        "score": score,
        "comment": comment
    }
```

## Alternative: Even Simpler Version

If the above doesn't work, use this ultra-simple version:

```python
def evaluate_example(run, example):
    alert = run.outputs.get("alert") if run.outputs else None
    expected = example.outputs.get("should_flag", False) if example.outputs else False
    actual = alert is not None

    score = 1.0 if actual == expected else 0.0
    comment = "Correct" if score == 1.0 else "Incorrect"

    return {"score": score, "comment": comment}
```

## What This Does

- ✅ Checks if agent flagged the transaction
- ✅ Compares to expected result
- ✅ Returns 1.0 (pass) or 0.0 (fail)
- ✅ Provides clear feedback

## Expected Results

When you run this evaluator:
- **Overall accuracy**: Should be 85-95%
- **Passed tests**: ~12-13 out of 14
- **Failed tests**: 1-2 edge cases

## Troubleshooting

### Error: "pyFunc is not a function"

This means the function signature is wrong. Make sure:
1. Function is named `evaluate_example` (not `evaluate`)
2. Takes exactly 2 parameters: `run` and `example`
3. Returns a dict with `score` and optionally `comment`

### Error: "AttributeError: 'dict' object has no attribute..."

Use safe access:
```python
# Instead of: run.outputs
# Use: getattr(run, 'outputs', {})
# Or: run.outputs if hasattr(run, 'outputs') else {}
```

## Next Step: Severity Evaluator

Once the correctness evaluator works, add a severity evaluator:

```python
def evaluate_example(run, example):
    outputs = run.outputs if hasattr(run, 'outputs') else {}
    alert = outputs.get("alert")

    reference = example.outputs if hasattr(example, 'outputs') else {}
    expected_severity = reference.get("expected_severity")

    # No alert needed
    if not reference.get("should_flag", False) and alert is None:
        return {"score": 1.0, "comment": "✓ No alert needed"}

    # Alert expected but not generated
    if alert is None:
        return {"score": 0.0, "comment": "✗ No alert generated"}

    # No expected severity specified
    if not expected_severity:
        return {"score": 1.0, "comment": f"Alert generated: {alert.get('severity')}"}

    # Check severity
    actual_severity = alert.get("severity")
    if actual_severity == expected_severity:
        return {"score": 1.0, "comment": f"✓ Correct: {actual_severity}"}
    else:
        return {"score": 0.5, "comment": f"⚠ Expected {expected_severity}, got {actual_severity}"}
```

## Demo Tips

1. **Start with the simplest version** - get it working first
2. **Show the creation process** - type/paste while presenting
3. **Run evaluation immediately** - show results right away
4. **Click through test cases** - show why they passed/failed
5. **Compare to LLM judge** - show both evaluators side-by-side
