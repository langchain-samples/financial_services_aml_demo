# LangSmith UI: LLM-as-Judge Evaluator Setup

This guide shows how to configure an LLM-as-Judge evaluator in LangSmith UI that properly evaluates AML transaction triage decisions.

## Overview

Your current setup has the right structure, but let me help optimize it for better results. The key is ensuring the evaluator gets all the necessary context from your traces.

## Step 1: Verify Your Dataset Structure

Your evaluator expects these fields:

**Inputs** (example.inputs):
- `transaction`: The transaction details
- `customer_history`: The customer's transaction history

**Outputs** (reference/expected):
- `should_flag`: Boolean indicating expected decision
- `expected_severity`: String (LOW/MEDIUM/HIGH/CRITICAL)
- `expected_indicators`: List of expected risk indicators
- `expected_risk_score`: Numeric score (0-100)

**Run outputs** (actual from agent):
- `alert`: Object with `severity`, `indicators`, `risk_score` (or null if not flagged)

## Updated Evaluator Code

Here's an improved version that works better as an LLM-as-judge evaluator in LangSmith UI:

```python
from langsmith.schemas import Run, Example

def evaluator(run: Run, example: Example) -> dict:
    """
    Evaluates whether the AML agent correctly flagged a transaction.
    Returns true/false based on weighted criteria.
    """
    # Get outputs
    outputs = run.outputs if run.outputs else {}
    alert = outputs.get("alert")
    agent_flagged = alert is not None

    # Get expected outputs
    reference = example.outputs if hasattr(example, 'outputs') and example.outputs else {}
    expected_flag = reference.get("should_flag", False)

    # Get inputs
    inputs = run.inputs if hasattr(run, 'inputs') else {}
    transaction = inputs.get("transaction", {})

    # Initialize scores for each dimension
    flag_correctness = 0.0
    severity_accuracy = 0.0
    indicator_detection = 0.0
    risk_score_accuracy = 0.0

    # === Flag Correctness (40% weight) ===
    if (alert is not None) == expected_flagged:
        flag_score = 1.0
    else:
        # False negative (missed suspicious) is critical
        if expected_flagged and not agent_flagged:
            flag_score = 0.0  # Critical failure
        else:
            flag_score = 0.3  # False positive - not ideal but less critical

    # ... rest of evaluation logic

This is giving me binary true or false. How do I fix this to incorporate your confidence scoring?