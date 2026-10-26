# LLM-as-Judge with Confidence Scoring in LangSmith

Your current LLM-as-judge evaluator is set to **Boolean** output, which only gives true/false (1/0). This guide shows how to change it to return **confidence scores** (0.0 to 1.0) that reflect nuanced evaluation.

## The Problem

**Current Setup**:
- Feedback Config: **Boolean** (true/false)
- Result: Binary 1 or 0
- Loss of information: Can't show "mostly correct" or "borderline" cases

**What You Want**:
- Confidence score: 0.0 to 1.0
- Shows nuance: 0.95 = high confidence correct, 0.6 = uncertain, etc.

## Solution: Change to Score-Based Evaluation

### Step 1: Update Your Feedback Config

In LangSmith UI when creating/editing your evaluator:

**OLD (Current)**:
```
Feedback Type: Boolean
Output: true or false (1 or 0)
```

**NEW (Change to)**:
```
Feedback Type: Score
Score Range: 0.0 to 1.0
Output: Numeric score representing confidence
```

### Step 2: Update Your Evaluator Prompt

Change your system prompt to output a confidence score instead of boolean:

```
system

You are an expert AML compliance evaluator. Your job is to evaluate whether an AML transaction monitoring system correctly flagged a transaction.

You will be given:
1. The transaction details
2. The customer's transaction history
3. What the AML agent decided (flagged or not, severity, risk indicators, risk score)
4. What the expected correct decision should be

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

**User Prompt** (remains similar):
```
human

# Transaction Details
{transaction}

# Customer History
{customer_history}

# Agent Decision
Flagged: {agent_flagged}
{agent_details}

# Expected Decision
Should Flag: {expected_flag}
{expected_details}

Provide your evaluation as a JSON object.
```

### Step 3: Configure JSON Output Parsing

In LangSmith UI, configure the evaluator to extract the `score` field from the JSON response:

**Output Key**: `score`
**Type**: Numeric (0.0 to 1.0)

This tells LangSmith to parse the JSON and extract the `score` field as the feedback score.

## How Scoring Works

### Perfect Cases (Score: 1.0)
- Agent correctly flagged suspicious transaction
- Severity matches expected level
- All key indicators detected
- Risk score in expected range

**Example**:
```json
{
  "score": 1.0,
  "reasoning": "Perfect evaluation. Agent correctly flagged the transaction with HIGH severity, identified all key indicators (sudden_large_transaction, high_risk_destination), and assigned appropriate risk score of 72.",
  "flag_correct": true,
  "severity_appropriate": true,
  "indicators_detected": true,
  "risk_score_reasonable": true
}
```

### Good Cases (Score: 0.85-0.95)
- Agent correctly flagged/not flagged
- Minor issues with severity level or indicators
- Overall decision was correct

**Example**:
```json
{
  "score": 0.9,
  "reasoning": "Agent correctly flagged the transaction, but marked as CRITICAL when HIGH would be more appropriate. All indicators detected and risk score reasonable.",
  "flag_correct": true,
  "severity_appropriate": false,
  "indicators_detected": true,
  "risk_score_reasonable": true
}
```

### Borderline Cases (Score: 0.6-0.8)
- Correct flag decision but significant issues
- OR edge case where wrong decision is understandable

**Example**:
```json
{
  "score": 0.7,
  "reasoning": "Agent correctly flagged, but missed the key 'sanctions_related' indicator and only marked as MEDIUM severity when should be CRITICAL. Risk score too low at 45.",
  "flag_correct": true,
  "severity_appropriate": false,
  "indicators_detected": false,
  "risk_score_reasonable": false
}
```

### Incorrect Cases (Score: 0.3-0.5)
- Wrong flag decision
- Clear error, not edge case

**Example - False Positive**:
```json
{
  "score": 0.5,
  "reasoning": "Agent incorrectly flagged a normal transaction. While the amount was high ($75k), this is consistent with customer history and destination is not high-risk.",
  "flag_correct": false,
  "severity_appropriate": null,
  "indicators_detected": false,
  "risk_score_reasonable": false
}
```

**Example - False Negative (Less Critical)**:
```json
{
  "score": 0.3,
  "reasoning": "Agent failed to flag a suspicious transaction with multiple risk indicators (sudden spike, high-risk destination). This is concerning but customer has some legitimate high-value history.",
  "flag_correct": false,
  "severity_appropriate": null,
  "indicators_detected": false,
  "risk_score_reasonable": false
}
```

### Critical Failures (Score: 0.0-0.2)
- False negative on obvious suspicious transaction
- Sanctions miss
- Multiple critical problems

**Example**:
```json
{
  "score": 0.0,
  "reasoning": "CRITICAL FAILURE: Agent failed to flag a clear sanctions-related transaction to Iran. This is a major compliance violation.",
  "flag_correct": false,
  "severity_appropriate": null,
  "indicators_detected": false,
  "risk_score_reasonable": false
}
```

## Alternative: Simpler Numeric Scoring (No JSON)

If JSON parsing is difficult in your LangSmith setup, use a simpler approach:

**System Prompt** (simplified):
```
You are an expert AML compliance evaluator. Evaluate whether the AML agent correctly flagged a transaction.

Return ONLY a single number between 0.0 and 1.0 representing your confidence that the agent made the correct decision:

- 1.0: Perfect, agent got everything right
- 0.9: Correct decision, minor issues
- 0.8: Correct decision, some issues
- 0.7: Correct decision, significant issues OR edge case
- 0.6: Incorrect decision but understandable
- 0.5: Clear incorrect decision
- 0.3: Incorrect with multiple problems
- 0.0: Critical failure (false negative on obvious case)

Return ONLY the numeric score, nothing else.
```

**Feedback Config**:
- Type: Score
- Range: 0.0 to 1.0
- No JSON parsing needed

## Step-by-Step: Updating Your Current Evaluator

### In LangSmith UI:

1. **Go to your evaluator**: Projects → Evaluators → `eval_financial_services_deep_agent_demo_analyze_transaction_offline_ded81d8e`

2. **Edit Feedback Config**:
   - Change from: **Boolean**
   - Change to: **Score** (0.0 to 1.0)

3. **Update System Prompt**:
   - Add the scoring guide (see above)
   - Change instruction from "Return ONLY the JSON" to include the `score` field
   - Keep your weighted criteria (40%/25%/20%/15%)

4. **Configure Output Parsing**:
   - If using JSON: Set output key to `score`
   - If using simple numeric: No parsing needed

5. **Save and Test**:
   - Run on a few test cases
   - Verify you get scores like 0.85, 0.6, 1.0 instead of just 1 or 0

## Filtering Results

After running with confidence scores, you can filter:

### Show All Uncertain Cases
```
Filter: score < 0.8
```
Shows cases where the agent had issues or made mistakes

### Show Critical Failures
```
Filter: score < 0.5
```
Shows cases where the agent made significant errors

### Show Perfect Cases
```
Filter: score >= 0.95
```
Shows high-confidence correct decisions

### Show by Category
Use the additional fields from JSON output:
- `flag_correct = false` → Wrong flag decision
- `severity_appropriate = false` → Severity issues
- `indicators_detected = false` → Missed indicators

## Comparison: Boolean vs Confidence Scoring

| Scenario | Boolean Output | Confidence Score Output |
|----------|---------------|------------------------|
| Perfect decision | 1 (true) | 1.0 |
| Correct flag, wrong severity | 1 (true) | 0.9 |
| Correct flag, missed indicator | 1 (true) | 0.85 |
| Edge case, wrong decision | 0 (false) | 0.7 |
| Clear wrong decision | 0 (false) | 0.5 |
| False negative on obvious case | 0 (false) | 0.0 |

**Key difference**: Confidence scoring shows **gradients of correctness**, not just binary pass/fail.

## Integration with UI_ONLINE_EVALUATOR_FIXED.md

You can combine approaches:

1. **LLM-as-Judge** (this setup): For test dataset evaluation with ground truth
   - Uses expected outputs to calculate weighted scores
   - More expensive (OpenAI API calls)
   - More nuanced assessment

2. **Heuristic Evaluator** ([UI_ONLINE_EVALUATOR_FIXED.md](UI_ONLINE_EVALUATOR_FIXED.md)): For production monitoring without ground truth
   - Uses risk indicators to assess confidence
   - Free (no API calls)
   - Fast and scalable

**Use both**:
- LLM-as-Judge for offline evaluation on test dataset
- Heuristic evaluator for online production monitoring

## Troubleshooting

### Still Getting Boolean (true/false)

**Check**:
1. Feedback Config is set to **Score**, not Boolean
2. Evaluator prompt returns numeric score
3. Output parsing is configured for the `score` field

### JSON Parsing Errors

**Solutions**:
1. Add instruction: "Return ONLY JSON, no markdown"
2. Use simpler numeric-only output (no JSON)
3. Check LangSmith version supports JSON parsing

### Scores Always 1.0 or 0.0

**Problem**: LLM is still treating it as binary

**Fix**: Update prompt to emphasize gradients:
```
IMPORTANT: You MUST return a decimal score showing gradients of correctness.
Do NOT just return 1.0 or 0.0.
Use the full range: 0.0, 0.3, 0.5, 0.7, 0.85, 0.9, 0.95, 1.0
```

## Next Steps

1. ✅ Change feedback config from Boolean to Score
2. ✅ Update evaluator prompt with scoring guide
3. ✅ Configure JSON output parsing (if using JSON)
4. ✅ Test on a few examples
5. ✅ Run full evaluation on test dataset
6. ✅ Filter results by score to find problem cases
7. ✅ Compare with heuristic evaluator results

## Summary

By changing from **Boolean** to **Score-based** evaluation, you get:

✅ **Nuanced scoring**: See gradients of correctness (0.85, 0.6, etc.)
✅ **Better filtering**: Find borderline cases, not just wrong ones
✅ **More information**: Understand *why* scores are lower
✅ **Prioritization**: Sort by score to tackle worst cases first
✅ **Confidence metrics**: Track average confidence over time

This addresses your original complaint: "My online evaluator is marking transactions 1 and 0 whether they are correctly flagged or not"

Now it will mark them with confidence scores that show the quality of the decision!
