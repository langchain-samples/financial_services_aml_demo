# Online LLM Judge with Visible Reasoning

This version improves visibility of the reasoning in LangSmith UI by including a summary in the comment field.

## The Problem

When you filter traces by `triage_quality < 0.7`, you can see the score but not WHY it got that score. The reasoning is hidden in the feedback details.

## Solution

Modify the evaluator output to include a **short summary** in the comment that's visible in the list view, plus detailed reasoning in metadata.

---

## Updated System Prompt

Use the same system prompt from [ONLINE_LLM_JUDGE_SETUP.md](ONLINE_LLM_JUDGE_SETUP.md) but change the **Output Format** section (around line 101):

**Replace this**:
```
**Output Format**:
Return a JSON object with:
{
  "score": <float 0.0-1.0 representing confidence in decision quality>,
  "reasoning": "<detailed explanation covering indicators, severity, risk score, and why this score>",
  "needs_review": <boolean - true if score < 0.8 or special circumstances>,
  "review_reason": "<string - category like SANCTIONS, HIGH_VALUE, EDGE_CASE, LOW_CONFIDENCE, etc.>"
}
```

**With this**:
```
**Output Format**:
Return a JSON object with:
{
  "score": <float 0.0-1.0 representing confidence in decision quality>,
  "comment": "<SHORT summary (1-2 sentences) - this appears in list view>",
  "reasoning": "<DETAILED explanation covering indicators, severity, risk score, and why this score>",
  "needs_review": <boolean - true if score < 0.8 or special circumstances>,
  "review_reason": "<string - category like SANCTIONS, HIGH_VALUE, EDGE_CASE, LOW_CONFIDENCE, etc.>"
}

**Comment Guidelines**:
- Keep comment SHORT (50-100 chars) for list view visibility
- Include: review_reason + key issue
- Examples:
  - "SANCTIONS: Iran transaction needs verification"
  - "HIGH_VALUE: $600k not flagged, verify legitimate"
  - "EDGE_CASE: Risk 39 near threshold, borderline"
  - "LOW_CONFIDENCE: Weak indicators for flag"
  - "High confidence: Strong indicators, appropriate severity"
```

---

## Why This Helps

### Before (Current):
```
Trace List View:
- analyze_transaction | Score: 0.7 | [No visible reason]

You have to click into the trace → Feedback tab → Expand details → See reasoning
```

### After (With This Update):
```
Trace List View:
- analyze_transaction | Score: 0.7 | "EDGE_CASE: Risk 39 near threshold"

You can see immediately WHY it scored 0.7 without clicking in
```

---

## Updated Output Examples

### Sanctions Case (Score: 0.5)

**Before**:
```json
{
  "score": 0.5,
  "reasoning": "SANCTIONS-RELATED: Automatic score of 0.5 regardless of decision quality. Sanctions matches require mandatory human verification to ensure accuracy of country identification and sanctions list matching. Severity CRITICAL and risk score 95 are appropriate, but human must verify before action.",
  "needs_review": true,
  "review_reason": "SANCTIONS"
}
```

**After (Better)**:
```json
{
  "score": 0.5,
  "comment": "SANCTIONS: Iran transaction requires verification",
  "reasoning": "SANCTIONS-RELATED: Automatic score of 0.5 regardless of decision quality. Sanctions matches require mandatory human verification to ensure accuracy of country identification and sanctions list matching. Severity CRITICAL and risk score 95 are appropriate, but human must verify before action.",
  "needs_review": true,
  "review_reason": "SANCTIONS"
}
```

### High Value Not Flagged (Score: 0.6)

**After**:
```json
{
  "score": 0.6,
  "comment": "HIGH_VALUE_NOT_FLAGGED: $600k not alerted, verify legitimate",
  "reasoning": "Very high value transaction ($600k) was NOT flagged. This needs verification. While it may be legitimate if consistent with customer history, the amount alone warrants scrutiny. Without more context about customer profile, confidence is low that this is correct to not flag. Needs human review to verify this is indeed a normal transaction for this customer.",
  "needs_review": true,
  "review_reason": "VERY_HIGH_VALUE_NOT_FLAGGED"
}
```

### Edge Case (Score: 0.7)

**After**:
```json
{
  "score": 0.7,
  "comment": "EDGE_CASE: Risk 39 just above threshold, borderline decision",
  "reasoning": "Edge case near decision threshold. Risk score 39 is just above typical flagging threshold of 38-40. Only one weak indicator (moderate amount). MEDIUM severity may be appropriate but this is borderline. Decision could go either way. Needs human review to determine if this should be flagged or not.",
  "needs_review": true,
  "review_reason": "EDGE_CASE_THRESHOLD"
}
```

### Low Risk Flagged (Score: 0.6)

**After**:
```json
{
  "score": 0.6,
  "comment": "LOW_RISK_FLAGGED: No indicators but HIGH severity, likely false positive",
  "reasoning": "Low confidence in flag decision. Small amount ($5k), no high-risk destination, and NO indicators listed. Yet marked as HIGH severity with only moderate risk score of 35. Severity HIGH typically requires risk score 50-69, so 35 is inconsistent. Why was this flagged with no evidence? Likely false positive. Needs review.",
  "needs_review": true,
  "review_reason": "LOW_RISK_FLAGGED_NO_INDICATORS"
}
```

### Good Decision (Score: 0.95)

**After**:
```json
{
  "score": 0.95,
  "comment": "High confidence: Strong indicators, appropriate HIGH severity",
  "reasoning": "High confidence in flag decision. Three strong risk indicators (large amount $250k, high-risk destination, unusual for customer). HIGH severity is appropriate for this risk level. Risk score 72 aligns well with HIGH severity (50-69 range, slightly elevated is reasonable). Clear reasoning provided. This appears to be a justified flag.",
  "needs_review": false,
  "review_reason": null
}
```

---

## How to View Comments in LangSmith UI

Unfortunately, LangSmith doesn't show the **comment** field in the main trace list view. But you can see it in these places:

### 1. In the Trace Detail View
1. Click on a trace
2. Scroll to **Feedback** section
3. Look for `triage_quality` feedback
4. The comment will be visible there

### 2. In the Feedback Tab
1. Click on a trace
2. Click the **Feedback** tab (next to Run, Metadata)
3. Find `triage_quality`
4. Comment is shown in the value

### 3. Export to CSV/JSON
1. Select your filtered traces
2. Click **Export** button
3. Download as JSON
4. Open file and search for `"comment"` field

---

## Alternative: Use Custom Code Evaluator

If you want MORE control over what's visible, use a **Custom Code evaluator** instead of LLM-as-judge:

```python
from langsmith.schemas import Run, Example
from openai import OpenAI
import json

def evaluator(run: Run, example: Example) -> dict:
    """Online LLM judge with visible reasoning in comment field."""

    inputs = run.inputs if run.inputs else {}
    outputs = run.outputs if run.outputs else {}

    transaction = inputs.get("transaction", {})
    alert = outputs.get("alert")

    # Create short summary for quick identification
    if alert:
        risk_score = alert.get("risk_score", 0)
        severity = alert.get("severity", "UNKNOWN")
        amount = transaction.get("amount", 0)
        quick_summary = f"Flagged: {severity} (risk {risk_score}), ${amount:,.0f}"
    else:
        amount = transaction.get("amount", 0)
        quick_summary = f"Not flagged: ${amount:,.0f}"

    # Call LLM for detailed assessment
    client = OpenAI()

    prompt = f"""Assess this AML triage decision quality.

Transaction: {json.dumps(transaction, indent=2)}
Agent Decision: {json.dumps({"alert": alert}, indent=2)}

Return JSON with:
- score (0.0-1.0): confidence in decision quality
- comment (short, 50-100 chars): summary for quick view
- reasoning (detailed): full explanation
- needs_review (boolean)
- review_reason (string or null)

Use scoring from your training on AML compliance."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an AML compliance evaluator. Return only JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        # Prepend quick summary to comment
        original_comment = result.get("comment", "")
        enhanced_comment = f"{quick_summary} | {original_comment}"

        return {
            "key": "triage_quality",
            "score": result.get("score", 0.5),
            "comment": enhanced_comment[:200],  # Truncate if too long
            "metadata": {
                "reasoning": result.get("reasoning", ""),
                "needs_review": result.get("needs_review", False),
                "review_reason": result.get("review_reason"),
                "quick_summary": quick_summary
            }
        }

    except Exception as e:
        return {
            "key": "triage_quality",
            "score": 0.5,
            "comment": f"{quick_summary} | ERROR: {str(e)}",
            "metadata": {"error": str(e)}
        }
```

This custom code version:
- ✅ Creates a quick summary from the data (Flagged: HIGH (risk 72), $250,000)
- ✅ Calls LLM for detailed assessment
- ✅ Combines both in the comment field
- ✅ Puts full reasoning in metadata
- ✅ More control over what's visible

---

## Best Practice: Use Table View with Filters

In LangSmith UI:

1. **Filter** by `triage_quality < 0.8` (shows uncertain cases)
2. **Sort** by `triage_quality` ascending (worst first)
3. **Group** by `review_reason` if available in metadata
4. **Click** into traces to see full reasoning in Feedback tab

---

## Summary

The reasoning IS there, it's just hidden in the Feedback details. To make it more visible:

### Option 1 (Easier): Update LLM prompt
- Add `comment` field with short summary
- Keep `reasoning` field with details
- Short summary is more visible in UI

### Option 2 (Better): Use Custom Code
- Create enhanced comment with key info upfront
- Full control over formatting
- Can extract and display exactly what you need

### Option 3 (Best): Export and Analyze
- Export filtered traces to JSON/CSV
- Analyze in spreadsheet or notebook
- Full access to all fields including reasoning

For your use case filtering by `triage_quality < 0.7`, I recommend **Option 1** (update the prompt to include `comment` field) - it's the simplest way to get more visibility without changing evaluator type.
