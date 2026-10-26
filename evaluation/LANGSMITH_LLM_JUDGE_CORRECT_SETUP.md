# LangSmith LLM-as-Judge: Correct Setup

Your current evaluator is **almost correct**, but the data isn't being formatted properly for the LLM. This guide fixes that.

## The Problem

Your prompt has template variables:
```
# Transaction Details
{transaction}

# Agent Decision
Flagged: {agent_flagged}
{agent_details}
```

But LangSmith is passing raw data:
```
<input>
input
</input>
<output>
output
</output>
```

The LLM can't extract `{transaction}`, `{agent_flagged}`, etc. from this.

## Solution 1: Use LangSmith's Built-in Template Format

LangSmith LLM-as-judge evaluators automatically pass `input` and `output`, so structure your prompt to work with these:

### Updated System Prompt

```
You are an expert AML compliance evaluator. Your job is to evaluate whether an AML transaction monitoring system correctly flagged a transaction.

Evaluate the agent's performance on these dimensions:

**Flag Correctness (Most Important - 40% weight)**
- Did the agent correctly decide to flag or not flag the transaction?
- A miss (false negative) is critical - suspicious transactions must be caught
- A false positive is problematic but less severe than missing a real threat

**Severity Accuracy (25% weight)**
- If flagged, was the severity level appropriate? (LOW, MEDIUM, HIGH, CRITICAL)
- Severity should match the risk level of the indicators
- Being off by one level is acceptable, but two+ levels is problematic

**Indicator Detection (20% weight)**
- Did the agent identify the key risk indicators?
- Missing critical indicators (like sanctions matches) is serious
- Extra indicators are okay if reasonable, but shouldn't replace expected ones

**Risk Score Accuracy (15% weight)**
- Was the numeric risk score (0-100) in the expected range?
- This is less critical than the other factors
- Allow some variance as long as severity level is correct

**Scoring Guide**:
- 1.0: Perfect evaluation, agent got everything right
- 0.9: Correct flag decision, minor issues with severity/indicators
- 0.8: Correct flag decision, some issues with severity or indicators
- 0.7: Correct flag decision, significant issues OR borderline edge case
- 0.6: Incorrect flag decision but understandable (edge case, close call)
- 0.5: Incorrect flag decision, clear error
- 0.3: Incorrect flag decision with multiple problems
- 0.0: Critical failure (false negative on obvious suspicious transaction)

Be strict but fair. Compliance is critical, so missed suspicious transactions should score very low (0.0-0.3).

Return your evaluation as a JSON object with:
{
  "score": <float between 0.0 and 1.0>,
  "reasoning": "<explanation of the score>",
  "flag_correct": <boolean>,
  "severity_appropriate": <boolean or null>,
  "indicators_detected": <boolean>,
  "risk_score_reasonable": <boolean>
}

Return ONLY the JSON object, no markdown formatting, no explanation text outside the JSON.
```

### Updated Human Prompt

**REMOVE** your custom template and use LangSmith's default format:

```
Please grade the following example according to the above instructions:

The input contains:
- transaction: The transaction details
- customer_history: The customer's transaction history

The output contains:
- alert: The agent's decision (null if not flagged, or object with severity, indicators, risk_score)

The reference/expected output (if available) contains:
- should_flag: Whether this transaction should be flagged
- expected_severity: Expected severity level
- expected_indicators: Expected risk indicators
- expected_risk_score: Expected risk score range

Analyze the input, output, and reference to determine if the agent made the correct decision.

<example>
<input>
{input}
</input>

<output>
{output}
</output>

<reference>
{reference}
</reference>
</example>
```

**Key Changes**:
1. Removed custom variables like `{transaction}`, `{agent_flagged}`, etc.
2. Use LangSmith's built-in `{input}`, `{output}`, `{reference}` variables
3. Let the LLM extract the fields from the JSON itself

## Solution 2: Use Custom Code Evaluator (More Control)

If you need more control over data formatting, use a **Custom Code** evaluator instead of LLM-as-judge:

```python
from langsmith.schemas import Run, Example
from openai import OpenAI
import json

def evaluator(run: Run, example: Example) -> dict:
    """
    Custom LLM-as-judge evaluator with proper data formatting.
    """
    # Extract data
    inputs = run.inputs if run.inputs else {}
    outputs = run.outputs if run.outputs else {}
    reference = example.outputs if example.outputs else {}

    transaction = inputs.get("transaction", {})
    customer_history = inputs.get("customer_history", [])
    alert = outputs.get("alert")

    # Format agent decision
    agent_flagged = alert is not None
    if alert:
        agent_details = f"""
Severity: {alert.get('severity', 'unknown')}
Risk Score: {alert.get('risk_score', 'unknown')}
Indicators: {', '.join(alert.get('indicators', []))}
Reasoning: {alert.get('reasoning', 'Not provided')}
"""
    else:
        agent_details = "No alert generated - transaction appears normal"

    # Format expected decision
    expected_flag = reference.get("should_flag", False)
    if expected_flag:
        expected_details = f"""
Expected Severity: {reference.get('expected_severity', 'unknown')}
Expected Indicators: {', '.join(reference.get('expected_indicators', []))}
Expected Risk Score: {reference.get('expected_risk_score', 'unknown')}
Reasoning: {reference.get('expected_reasoning', 'Not provided')}
"""
    else:
        expected_details = "Should NOT flag - this is a normal transaction"

    # Format transaction details for readability
    transaction_str = f"""
Transaction ID: {transaction.get('transaction_id', 'unknown')}
Amount: ${transaction.get('amount', 0):,.2f}
Source: {transaction.get('source', 'unknown')}
Destination: {transaction.get('destination', 'unknown')}
Type: {transaction.get('transaction_type', 'unknown')}
"""

    # Format customer history summary
    if customer_history:
        history_str = f"Customer has {len(customer_history)} previous transactions"
        avg_amount = sum(t.get('amount', 0) for t in customer_history) / len(customer_history)
        history_str += f"\nAverage transaction amount: ${avg_amount:,.2f}"
    else:
        history_str = "No customer history available"

    # Call LLM
    client = OpenAI()  # Uses OPENAI_API_KEY from environment

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """You are an expert AML compliance evaluator. Your job is to evaluate whether an AML transaction monitoring system correctly flagged a transaction.

Evaluate the agent's performance on these dimensions:

**Flag Correctness (Most Important - 40% weight)**
- Did the agent correctly decide to flag or not flag the transaction?
- A miss (false negative) is critical - suspicious transactions must be caught
- A false positive is problematic but less severe than missing a real threat

**Severity Accuracy (25% weight)**
- If flagged, was the severity level appropriate? (LOW, MEDIUM, HIGH, CRITICAL)
- Severity should match the risk level of the indicators
- Being off by one level is acceptable, but two+ levels is problematic

**Indicator Detection (20% weight)**
- Did the agent identify the key risk indicators?
- Missing critical indicators (like sanctions matches) is serious
- Extra indicators are okay if reasonable, but shouldn't replace expected ones

**Risk Score Accuracy (15% weight)**
- Was the numeric risk score (0-100) in the expected range?
- This is less critical than the other factors
- Allow some variance as long as severity level is correct

**Scoring Guide**:
- 1.0: Perfect evaluation, agent got everything right
- 0.9: Correct flag decision, minor issues with severity/indicators
- 0.8: Correct flag decision, some issues with severity or indicators
- 0.7: Correct flag decision, significant issues OR borderline edge case
- 0.6: Incorrect flag decision but understandable (edge case, close call)
- 0.5: Incorrect flag decision, clear error
- 0.3: Incorrect flag decision with multiple problems
- 0.0: Critical failure (false negative on obvious suspicious transaction)

Be strict but fair. Compliance is critical, so missed suspicious transactions should score very low (0.0-0.3).

Return your evaluation as a JSON object with:
{
  "score": <float between 0.0 and 1.0>,
  "reasoning": "<explanation of the score>",
  "flag_correct": <boolean>,
  "severity_appropriate": <boolean or null>,
  "indicators_detected": <boolean>,
  "risk_score_reasonable": <boolean>
}

Return ONLY the JSON object, no markdown formatting, no explanation text outside the JSON."""
            },
            {
                "role": "user",
                "content": f"""# Transaction Details
{transaction_str}

# Customer History
{history_str}

# Agent Decision
Flagged: {agent_flagged}
{agent_details}

# Expected Decision
Should Flag: {expected_flag}
{expected_details}

Provide your evaluation as a JSON object."""
            }
        ],
        temperature=0.1,
        response_format={"type": "json_object"}
    )

    # Parse LLM response
    try:
        result = json.loads(response.choices[0].message.content)
        score = result.get("score", 0.5)
        reasoning = result.get("reasoning", "No reasoning provided")

        return {
            "key": "aml_triage_quality",
            "score": score,
            "comment": reasoning,
            "metadata": {
                "flag_correct": result.get("flag_correct"),
                "severity_appropriate": result.get("severity_appropriate"),
                "indicators_detected": result.get("indicators_detected"),
                "risk_score_reasonable": result.get("risk_score_reasonable"),
            }
        }
    except Exception as e:
        return {
            "key": "aml_triage_quality",
            "score": 0.5,
            "comment": f"Error parsing LLM response: {str(e)}"
        }
```

### Advantages of Custom Code Approach:
✅ Full control over data formatting
✅ Can extract and format fields exactly as needed
✅ Can add error handling and fallbacks
✅ Can compute additional metrics
✅ More transparent - you see exactly what's being sent to the LLM

### Disadvantages:
❌ More code to maintain
❌ Need to handle OpenAI API calls yourself
❌ Requires OPENAI_API_KEY in environment

## Which Approach to Use?

### Use Built-in LLM-as-Judge (Solution 1) if:
- You want simplicity
- Your data structure is straightforward
- You're okay with the LLM extracting fields from JSON

### Use Custom Code (Solution 2) if:
- You need precise control over formatting
- You want to compute additional metrics
- You need complex data transformations
- You want to add validation or error handling

## Testing Your Setup

After updating, test on a single example:

1. Go to your dataset
2. Click on one example
3. Click "Evaluate" → Select your evaluator
4. Check the result:
   - **Score**: Should be between 0.0 and 1.0 (not just 0 or 1)
   - **Comment**: Should contain the reasoning
   - **Metadata**: Should contain flag_correct, severity_appropriate, etc.

## Expected Results

### Good Case (Score ~1.0)
```json
{
  "score": 1.0,
  "reasoning": "Perfect evaluation. Agent correctly flagged with HIGH severity, identified all indicators (sudden_large_transaction, high_risk_destination), risk score 72 is appropriate.",
  "flag_correct": true,
  "severity_appropriate": true,
  "indicators_detected": true,
  "risk_score_reasonable": true
}
```

### Mixed Case (Score ~0.85)
```json
{
  "score": 0.85,
  "reasoning": "Agent correctly flagged the transaction, but marked as CRITICAL when HIGH is more appropriate. All key indicators detected. Risk score slightly high at 78.",
  "flag_correct": true,
  "severity_appropriate": false,
  "indicators_detected": true,
  "risk_score_reasonable": false
}
```

### False Positive (Score ~0.5)
```json
{
  "score": 0.5,
  "reasoning": "Agent incorrectly flagged a normal transaction. Amount is high but consistent with customer history. Destination is not high-risk.",
  "flag_correct": false,
  "severity_appropriate": null,
  "indicators_detected": false,
  "risk_score_reasonable": false
}
```

### False Negative (Score ~0.0)
```json
{
  "score": 0.0,
  "reasoning": "CRITICAL FAILURE: Agent failed to flag obvious sanctions-related transaction to Iran. This is a major compliance violation.",
  "flag_correct": false,
  "severity_appropriate": null,
  "indicators_detected": false,
  "risk_score_reasonable": false
}
```

## Troubleshooting

### Still Getting Just 0 or 1

**Check**:
1. Feedback config is set to **Score** (not Boolean)
2. System prompt includes scoring guide with decimal values
3. LLM is returning JSON with decimal `score` field
4. Output parsing is extracting the `score` field correctly

### LLM Not Seeing the Data

**Problem**: LLM can't extract fields from raw JSON

**Fix**: Use Solution 2 (Custom Code) to format the data properly before sending to LLM

### JSON Parsing Errors

**Symptoms**: Evaluator fails with "Invalid JSON" errors

**Fixes**:
1. Add `response_format={"type": "json_object"}` to OpenAI call (GPT-4 only)
2. Add more explicit instructions: "Return ONLY JSON, no markdown"
3. Add error handling to catch and log parsing failures

### Scores Always 0.5

**Problem**: LLM is defaulting to middle score when uncertain

**Fix**: Make scoring guide more explicit:
```
IMPORTANT: Use the full range of scores (0.0, 0.3, 0.5, 0.7, 0.85, 0.9, 1.0).
Do not default to 0.5. Evaluate based on the criteria and assign appropriate score.
```

## Summary

Your setup is **almost correct** - you just need to fix how the data is passed to the LLM:

**Option 1 (Simpler)**: Let LangSmith pass raw `{input}`, `{output}`, `{reference}` and let the LLM extract fields

**Option 2 (Better)**: Use Custom Code evaluator to format data exactly as needed before calling the LLM

I recommend **Option 2** for your use case since you have specific formatting needs for the transaction details, customer history, and alert structure.

Copy the Custom Code evaluator from Solution 2 above and paste it into a new Custom Code evaluator in LangSmith UI.
