# Complete LLM-as-Judge Evaluator Setup for LangSmith UI

Copy-paste these prompts directly into your LangSmith UI evaluator.

## Evaluator Configuration

**Name**: `AML Transaction Triage Quality`

**Type**: LLM-as-Judge

**Model**: `gpt-4o-mini` (or `gpt-4o` for better accuracy)

**Feedback Type**: **Score** (0.0 to 1.0)

**Feedback Key**: `response_flag`

**Min Score Label**: `Critical Failure`

**Max Score Label**: `Perfect Evaluation`

---

## System Prompt

Copy everything below (including the blank line at the end):

```
You are an expert AML compliance evaluator. Your job is to evaluate whether an AML transaction monitoring system correctly flagged a transaction.

You will be given:
1. INPUT: The transaction details and customer history
2. OUTPUT: What the AML agent decided (alert object if flagged, null if not flagged)
3. REFERENCE: What the expected correct decision should be

Evaluate the agent's performance on these dimensions:

**Flag Correctness (Most Important - 40% weight)**
- Did the agent correctly decide to flag or not flag the transaction?
- Compare OUTPUT.alert (exists or null) with REFERENCE.should_flag
- A miss (false negative) is CRITICAL - suspicious transactions must be caught
- A false positive is problematic but less severe than missing a real threat

**Severity Accuracy (25% weight)**
- If flagged, was the severity level appropriate? (LOW, MEDIUM, HIGH, CRITICAL)
- Compare OUTPUT.alert.severity with REFERENCE.expected_severity
- Being off by one level is acceptable, but two+ levels is problematic

**Indicator Detection (20% weight)**
- Did the agent identify the key risk indicators?
- Compare OUTPUT.alert.indicators with REFERENCE.expected_indicators
- Missing critical indicators (like sanctions matches) is serious
- Extra indicators are okay if reasonable, but shouldn't replace expected ones

**Risk Score Accuracy (15% weight)**
- Was the numeric risk score (0-100) in the expected range?
- Compare OUTPUT.alert.risk_score with REFERENCE.expected_risk_score
- This is less critical than the other factors
- Allow some variance as long as severity level is correct

**Scoring Guide**:
- 1.0: Perfect evaluation, agent got everything right
- 0.95: Nearly perfect, one very minor issue
- 0.9: Correct flag decision, minor issues with severity/indicators
- 0.85: Correct flag decision, some issues with severity or indicators
- 0.8: Correct flag decision, multiple minor issues
- 0.7: Correct flag decision, significant issues OR borderline edge case
- 0.6: Incorrect flag decision but understandable (edge case, close call)
- 0.5: Incorrect flag decision, clear error
- 0.3: Incorrect flag decision with multiple problems
- 0.1: Critical failure (false negative on obvious suspicious transaction)
- 0.0: Catastrophic failure (false negative on sanctions or critical case)

**Evaluation Rules**:
1. If OUTPUT.alert exists and REFERENCE.should_flag is true → Agent flagged correctly
2. If OUTPUT.alert is null and REFERENCE.should_flag is false → Agent did NOT flag correctly
3. If OUTPUT.alert exists and REFERENCE.should_flag is false → FALSE POSITIVE (score 0.5-0.6)
4. If OUTPUT.alert is null and REFERENCE.should_flag is true → FALSE NEGATIVE (score 0.0-0.3)

**Be strict but fair**:
- Compliance is critical, so missed suspicious transactions should score very low (0.0-0.3)
- False positives should score around 0.5-0.6 (incorrect but not catastrophic)
- Minor issues with severity/indicators should only reduce score by 0.05-0.15

**Output Format**:
Return your evaluation as a JSON object with:
{
  "score": <float between 0.0 and 1.0>,
  "reasoning": "<clear explanation of the score covering all 4 dimensions>",
  "flag_correct": <boolean - did agent flag/not-flag correctly?>,
  "severity_appropriate": <boolean or null - was severity right? null if not flagged>,
  "indicators_detected": <boolean - were key indicators found?>,
  "risk_score_reasonable": <boolean - was risk score in expected range?>
}

**CRITICAL**: Use the full range of decimal scores (0.0, 0.3, 0.5, 0.7, 0.85, 0.9, 0.95, 1.0). Do NOT just return 1.0 or 0.0.

Return ONLY the JSON object. No markdown formatting (no ```json), no explanation text outside the JSON.
```

---

## Human Prompt

Copy everything below:

```
Please grade the following example according to the above instructions.

You will receive three pieces of information:

**INPUT**: Contains the transaction details (amount, destination, customer_id, etc.) and optionally customer_history

**OUTPUT**: Contains the agent's decision:
- If flagged: OUTPUT.alert will be an object with {severity, risk_score, indicators, reasoning}
- If NOT flagged: OUTPUT.alert will be null or absent

**REFERENCE**: Contains the expected correct decision:
- should_flag: boolean (true if should flag, false if should not)
- expected_severity: string (LOW/MEDIUM/HIGH/CRITICAL) if should flag
- expected_indicators: array of expected risk indicator strings
- expected_risk_score: number or range if should flag

Your task:
1. Extract the agent's decision from OUTPUT
2. Extract the expected decision from REFERENCE
3. Compare them across all 4 dimensions (flag correctness, severity, indicators, risk score)
4. Assign a confidence score based on the scoring guide
5. Return JSON with score, reasoning, and dimension assessments

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

---

## Output Parsing Configuration

**Output Key**: `score`

**Output Type**: Numeric (float)

**Range**: 0.0 to 1.0

---

## Example Expected Results

### Perfect Case (Score: 1.0)

**INPUT**:
```json
{
  "transaction": {
    "amount": 150000,
    "destination": "Iran",
    "transaction_type": "transfer"
  }
}
```

**OUTPUT**:
```json
{
  "alert": {
    "severity": "CRITICAL",
    "risk_score": 95,
    "indicators": ["sanctions_related", "high_value"],
    "reasoning": "Sanctions match detected"
  }
}
```

**REFERENCE**:
```json
{
  "should_flag": true,
  "expected_severity": "CRITICAL",
  "expected_indicators": ["sanctions_related", "high_value"],
  "expected_risk_score": 90
}
```

**Expected Evaluator Output**:
```json
{
  "score": 1.0,
  "reasoning": "Perfect evaluation. Agent correctly flagged with CRITICAL severity, identified all expected indicators (sanctions_related, high_value), and risk score 95 is appropriate for sanctions case.",
  "flag_correct": true,
  "severity_appropriate": true,
  "indicators_detected": true,
  "risk_score_reasonable": true
}
```

---

### Good Case with Minor Issue (Score: 0.9)

**OUTPUT**:
```json
{
  "alert": {
    "severity": "CRITICAL",
    "risk_score": 72,
    "indicators": ["sudden_large_transaction", "high_risk_destination"],
    "reasoning": "Large transaction to high-risk country"
  }
}
```

**REFERENCE**:
```json
{
  "should_flag": true,
  "expected_severity": "HIGH",
  "expected_indicators": ["sudden_large_transaction", "high_risk_destination"],
  "expected_risk_score": 70
}
```

**Expected Evaluator Output**:
```json
{
  "score": 0.9,
  "reasoning": "Agent correctly flagged the transaction and identified all expected indicators. However, severity was marked CRITICAL when HIGH would be more appropriate. Risk score is reasonable. Minor severity over-classification.",
  "flag_correct": true,
  "severity_appropriate": false,
  "indicators_detected": true,
  "risk_score_reasonable": true
}
```

---

### Borderline Case (Score: 0.7)

**OUTPUT**:
```json
{
  "alert": {
    "severity": "MEDIUM",
    "risk_score": 45,
    "indicators": ["sudden_large_transaction"],
    "reasoning": "Transaction amount higher than usual"
  }
}
```

**REFERENCE**:
```json
{
  "should_flag": true,
  "expected_severity": "HIGH",
  "expected_indicators": ["sudden_large_transaction", "high_risk_destination"],
  "expected_risk_score": 65
}
```

**Expected Evaluator Output**:
```json
{
  "score": 0.7,
  "reasoning": "Agent correctly flagged the transaction but with significant issues. Severity was MEDIUM when should be HIGH (two levels off). Missed key indicator 'high_risk_destination'. Risk score 45 is too low for expected 65. Correct flag decision but poor execution.",
  "flag_correct": true,
  "severity_appropriate": false,
  "indicators_detected": false,
  "risk_score_reasonable": false
}
```

---

### False Positive (Score: 0.5)

**OUTPUT**:
```json
{
  "alert": {
    "severity": "MEDIUM",
    "risk_score": 50,
    "indicators": ["large_transaction"],
    "reasoning": "High transaction amount"
  }
}
```

**REFERENCE**:
```json
{
  "should_flag": false,
  "expected_reasoning": "Customer regularly makes transactions of this size to this destination"
}
```

**Expected Evaluator Output**:
```json
{
  "score": 0.5,
  "reasoning": "Agent incorrectly flagged a normal transaction (false positive). While the amount is high, this is consistent with customer history. The destination is not high-risk. Clear incorrect decision but understandable given transaction size.",
  "flag_correct": false,
  "severity_appropriate": null,
  "indicators_detected": false,
  "risk_score_reasonable": false
}
```

---

### False Negative (Score: 0.1)

**OUTPUT**:
```json
{
  "alert": null
}
```

**REFERENCE**:
```json
{
  "should_flag": true,
  "expected_severity": "CRITICAL",
  "expected_indicators": ["sanctions_related"],
  "expected_risk_score": 95,
  "expected_reasoning": "Transaction to sanctioned country"
}
```

**Expected Evaluator Output**:
```json
{
  "score": 0.1,
  "reasoning": "CRITICAL FAILURE: Agent failed to flag a sanctions-related transaction. This is a major compliance violation. False negative on obvious high-risk case.",
  "flag_correct": false,
  "severity_appropriate": null,
  "indicators_detected": false,
  "risk_score_reasonable": false
}
```

---

## Testing Your Evaluator

### Step 1: Create the Evaluator

1. Go to LangSmith UI → Your Project
2. Click **Evaluators** tab
3. Click **Create Evaluator**
4. Choose **LLM-as-Judge**
5. Copy-paste the **System Prompt** above
6. Copy-paste the **Human Prompt** above
7. Set Feedback Type to **Score** (0.0 to 1.0)
8. Set Output Key to `score`
9. Click **Save**

### Step 2: Test on Dataset

1. Go to **Datasets** → `aml-transaction-flagging-tests`
2. Click **Run Evaluation**
3. Select your new evaluator
4. Click **Start**

### Step 3: Check Results

Look for:
- ✅ Scores between 0.0 and 1.0 (not just 0 or 1)
- ✅ Reasoning in the comment field
- ✅ Metadata fields (flag_correct, severity_appropriate, etc.)

### Step 4: Filter Results

**Show uncertain cases**:
```
score < 0.8
```

**Show critical failures**:
```
score < 0.3
```

**Show perfect cases**:
```
score >= 0.95
```

---

## Troubleshooting

### Issue: Still getting only 1.0 or 0.0

**Fix**: Check that Feedback Type is set to **Score** (not Boolean)

### Issue: No reasoning in results

**Fix**: Make sure Output Key is set to `score` to extract just the score, or leave empty to get full JSON

### Issue: Evaluator fails with JSON parsing error

**Fix**: Update to `gpt-4o` model which has better JSON formatting, or add `response_format: json_object` in advanced settings

### Issue: Scores seem random or inconsistent

**Fix**:
1. Reduce temperature to 0.1 (more deterministic)
2. Add more examples in the prompt
3. Make scoring criteria more explicit

### Issue: LLM not seeing OUTPUT or REFERENCE

**Fix**: Verify your dataset has:
- `should_flag` in example outputs (reference)
- `alert` in run outputs (actual agent decision)

---

## Summary

This evaluator will:

✅ Return confidence scores from 0.0 to 1.0 (not binary)
✅ Evaluate across 4 weighted dimensions
✅ Provide detailed reasoning
✅ Flag critical failures (false negatives) with very low scores
✅ Work on any trace with the correct structure
✅ No filtering by trace name needed

Copy both prompts above into your LangSmith evaluator and you're ready to go!
