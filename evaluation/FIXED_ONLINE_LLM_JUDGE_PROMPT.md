# Fixed Online LLM-as-Judge Prompt (Data Actually Passes Through)

The issue is that `{input}` and `{output}` aren't being populated. Here's the corrected version.

## Root Cause

LangSmith's LLM-as-judge evaluators use special variable interpolation. The variables need to match exactly what LangSmith provides.

## Fixed Human Prompt

**Replace your entire Human Prompt with this:**

```
Please assess the quality and reasonableness of this AML triage decision.

You will evaluate a transaction monitoring decision based on the input and output below.

TRANSACTION INPUT:
The input contains transaction details including amount, destination, customer_id, transaction_type, etc.

AGENT OUTPUT:
The output contains the agent's triage decision:
- If flagged: an "alert" object with severity, risk_score, indicators, reasoning
- If NOT flagged: alert will be null or the field will be absent

Your task:
1. Extract transaction details from the input
2. Determine if the agent flagged the transaction (check for "alert" in output)
3. Assess the quality of this decision based on risk indicators
4. Return a confidence score (0.0-1.0) and reasoning

INPUT:
{input}

OUTPUT:
{output}

Provide your confidence assessment as a JSON object with:
- score (0.0-1.0)
- comment (short summary, 50-100 chars)
- reasoning (detailed explanation)
- needs_review (boolean)
- review_reason (string or null)
```

## Alternative: Use the "inputs" and "outputs" Variables

If the above doesn't work, try these variable names:

```
INPUT:
{inputs}

OUTPUT:
{outputs}
```

Or try:

```
INPUT:
{run.inputs}

OUTPUT:
{run.outputs}
```

## Best Solution: Use Custom Code Evaluator

Since the built-in LLM-as-judge variable interpolation is inconsistent, I recommend switching to a **Custom Code evaluator** which gives you full control:

### Complete Custom Code Evaluator

Create a new evaluator in LangSmith UI:
1. Type: **Custom Code** (not LLM-as-judge)
2. Copy this entire code:

```python
from langsmith.schemas import Run, Example
import os
import json

def evaluator(run: Run, example: Example) -> dict:
    """
    Online LLM-as-judge evaluator that actually receives the data.
    """

    # Import OpenAI here (available in LangSmith sandbox)
    try:
        from openai import OpenAI
    except ImportError:
        return {
            "key": "triage_quality",
            "score": 0.5,
            "comment": "Error: OpenAI not available in sandbox"
        }

    # Extract data from run
    inputs = run.inputs if run.inputs else {}
    outputs = run.outputs if run.outputs else {}

    transaction = inputs.get("transaction", {})
    customer_history = inputs.get("customer_history", [])
    alert = outputs.get("alert")

    # Quick validation
    if not transaction:
        return {
            "key": "triage_quality",
            "score": 0.5,
            "comment": "No transaction data found in inputs"
        }

    # Format transaction for LLM
    transaction_str = json.dumps(transaction, indent=2)

    # Format customer history summary
    if customer_history:
        history_summary = f"{len(customer_history)} previous transactions"
        if len(customer_history) > 0:
            avg_amount = sum(t.get("amount", 0) for t in customer_history) / len(customer_history)
            history_summary += f", avg amount: ${avg_amount:,.2f}"
    else:
        history_summary = "No customer history"

    # Format alert
    if alert:
        alert_str = json.dumps(alert, indent=2)
        decision_summary = f"FLAGGED with {alert.get('severity', 'unknown')} severity"
    else:
        alert_str = "null (not flagged)"
        decision_summary = "NOT FLAGGED"

    # Create prompt for LLM
    system_prompt = """You are an expert AML compliance evaluator. Assess the quality and reasonableness of transaction triage decisions.

You do NOT have ground truth. Return a confidence score (0.0-1.0) based on:

**Scoring Guide**:
- 1.0: High confidence decision is reasonable (strong indicators justify the decision)
- 0.9: Likely reasonable (good indicators, minor questions)
- 0.85: Probably reasonable (moderate indicators)
- 0.8: Borderline reasonable (some uncertainty)
- 0.7: Uncertain - edge case or weak justification (needs review)
- 0.6: Low confidence - questionable decision
- 0.5: Very uncertain - likely incorrect (sanctions = always 0.5)

**Special Rules**:
- Sanctions-related: Always 0.5 (needs mandatory review)
- Very high value (>$500k): Cap at 0.7 (needs scrutiny)
- Critical severity: Cap at 0.8 (verify appropriateness)
- Edge cases (risk 38-42): Cap at 0.7
- No indicators but flagged: 0.6 (questionable)

Return ONLY valid JSON:
{
  "score": <float 0.0-1.0>,
  "comment": "<short summary, 50-100 chars>",
  "reasoning": "<detailed explanation>",
  "needs_review": <boolean>,
  "review_reason": "<string or null>"
}"""

    user_prompt = f"""Assess this AML triage decision:

TRANSACTION:
{transaction_str}

CUSTOMER HISTORY:
{history_summary}

AGENT DECISION:
{decision_summary}

ALERT OUTPUT:
{alert_str}

Provide your assessment as JSON."""

    # Call OpenAI
    try:
        client = OpenAI()  # Uses OPENAI_API_KEY from environment

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        # Parse response
        result = json.loads(response.choices[0].message.content)

        score = result.get("score", 0.5)
        comment = result.get("comment", "No comment")
        reasoning = result.get("reasoning", "No reasoning")
        needs_review = result.get("needs_review", score < 0.8)
        review_reason = result.get("review_reason")

        # Build metadata
        metadata = {
            "reasoning": reasoning,
            "needs_review": needs_review,
            "review_reason": review_reason,
            "transaction_amount": transaction.get("amount", 0),
            "flagged": alert is not None
        }

        return {
            "key": "triage_quality",
            "score": score,
            "comment": comment,
            "metadata": metadata
        }

    except Exception as e:
        return {
            "key": "triage_quality",
            "score": 0.5,
            "comment": f"Error calling LLM: {str(e)}",
            "metadata": {"error": str(e)}
        }
```

### Why Custom Code is Better

✅ **Direct access** to `run.inputs` and `run.outputs`
✅ **No variable interpolation issues** - you extract data yourself
✅ **Full control** over what gets sent to the LLM
✅ **Error handling** - can catch and report issues
✅ **Formatting** - can format transaction data exactly as needed

## Environment Variables

Make sure you have `OPENAI_API_KEY` set in your LangSmith environment:

1. Go to Settings in LangSmith
2. Add environment variable: `OPENAI_API_KEY` = your key
3. This allows the custom code evaluator to call OpenAI

## Testing the Fix

After creating the custom code evaluator:

1. **Test on one trace first**:
   - Go to a single trace in your project
   - Click "Evaluate" → Select your new custom code evaluator
   - Click "Run"
   - Check if it returns a real score and comment (not the "No transaction" error)

2. **Run on filtered set**:
   - Once confirmed working, run on your full trace set
   - Filter by `triage_quality` score
   - Verify you see actual assessments, not error messages

## Quick Debug: Check What Variables Are Available

If you want to see what variables LangSmith is actually providing, create a simple test evaluator:

```python
from langsmith.schemas import Run, Example
import json

def evaluator(run: Run, example: Example) -> dict:
    """Debug: Show what data is available"""

    available_data = {
        "run.inputs": str(run.inputs)[:200] if run.inputs else "None",
        "run.outputs": str(run.outputs)[:200] if run.outputs else "None",
        "example.inputs": str(example.inputs)[:200] if hasattr(example, 'inputs') and example.inputs else "None",
        "example.outputs": str(example.outputs)[:200] if hasattr(example, 'outputs') and example.outputs else "None"
    }

    return {
        "key": "debug",
        "score": 1.0,
        "comment": json.dumps(available_data)[:200]
    }
```

Run this on one trace to see what data is actually available.

---

## Summary

The issue is that `{input}` and `{output}` in your LLM-as-judge prompt aren't being populated with actual data.

**Best fix**: Use the **Custom Code evaluator** above which:
- Directly accesses `run.inputs` and `run.outputs`
- Formats the data properly for the LLM
- Calls OpenAI with the formatted prompt
- Returns proper feedback with scores

This will give you actual assessments instead of "No transaction was provided" errors.

Would you like me to help you set up the custom code evaluator in LangSmith?
