# Online LLM-as-Judge Evaluator (No Ground Truth)

This evaluator works on **production traces** where you don't have expected outputs. It assesses the **quality and reasonableness** of the agent's decision, not correctness against ground truth.

## Key Difference: Online vs Offline

| Aspect | Offline Evaluation | Online Evaluation |
|--------|-------------------|-------------------|
| **Ground Truth** | ✅ Has reference/expected output | ❌ No reference available |
| **Goal** | Compare actual vs expected | Assess decision quality |
| **Score Meaning** | Correctness | Confidence in decision |
| **Use Case** | Test dataset validation | Production monitoring |

## Evaluator Configuration

**Name**: `AML Triage Quality (Online)`

**Type**: LLM-as-Judge

**Model**: `gpt-4o-mini`

**Feedback Type**: **Score** (0.0 to 1.0)

**Feedback Key**: `triage_quality`

**Min Score Label**: `Very Uncertain - Needs Review`

**Max Score Label**: `High Confidence Decision`

---

## System Prompt

Copy everything below:

```
You are an expert AML compliance evaluator. Your job is to assess the quality and reasonableness of an AML transaction monitoring system's triage decision.

**IMPORTANT**: You do NOT have ground truth. You cannot determine if the decision is "correct" or "incorrect". Instead, assess **confidence in the decision quality** based on the evidence provided.

You will be given:
1. INPUT: Transaction details and customer history
2. OUTPUT: The agent's decision (alert object if flagged, null if not flagged)

Your task is to evaluate **how confident you are that this was a reasonable decision** based on:

**Risk Indicator Strength (40% weight)**
- Are there clear risk indicators present?
- For FLAGGED transactions: Are the indicators strong enough to justify flagging?
- For NOT FLAGGED: Are there any concerning patterns that should have been flagged?

**Severity Appropriateness (25% weight)**
- If flagged: Is the severity level (LOW/MEDIUM/HIGH/CRITICAL) appropriate for the risk indicators?
- CRITICAL should be reserved for sanctions, large amounts to high-risk countries, etc.
- LOW/MEDIUM for smaller concerns or patterns

**Risk Score Alignment (20% weight)**
- Does the risk score (0-100) match the severity and indicators?
- CRITICAL = 70-100, HIGH = 50-69, MEDIUM = 35-49, LOW = 20-34
- Is the score justified by the evidence?

**Decision Consistency (15% weight)**
- Is the reasoning clear and logical?
- Do the indicators support the decision?
- For high-value transactions: Is extra scrutiny appropriate?

**Scoring Guide for FLAGGED Transactions**:
- **1.0**: High confidence correct flag (strong indicators, appropriate severity, clear reasoning)
- **0.95**: Very likely correct (strong indicators, minor severity question)
- **0.9**: Likely correct (reasonable indicators, appropriate severity)
- **0.85**: Probably correct (moderate indicators, some uncertainty)
- **0.8**: Borderline but likely correct (weak indicators or severity questions)
- **0.7**: Uncertain - edge case near threshold (needs human review)
- **0.6**: Low confidence - weak justification (may be false positive)
- **0.5**: Very uncertain - questionable decision (likely false positive)

**Scoring Guide for NOT FLAGGED Transactions**:
- **1.0**: High confidence correct (clearly normal transaction, no red flags)
- **0.95**: Very likely correct (normal patterns, low risk)
- **0.9**: Likely correct (appears normal, minimal concerns)
- **0.85**: High-value but appears legitimate
- **0.7**: Uncertain - high value without alert (needs verification)
- **0.6**: Concerning - possible missed flag (high-risk indicators present)
- **0.5**: Very uncertain - should likely be flagged

**Special Cases**:
- **Sanctions-related**: Always score 0.5 (needs mandatory human review regardless)
- **Very high value (>$500k)**: Cap score at 0.7 (needs scrutiny whether flagged or not)
- **Critical severity**: Cap score at 0.8 (verify appropriateness)
- **Edge cases (risk 38-42)**: Cap score at 0.7 (near decision threshold)
- **No indicators but flagged**: Score 0.6 (why flagged without evidence?)
- **Multiple indicators (3+)**: Boost confidence by +0.05

**Red Flags to Watch For**:
1. High-risk destinations: Iran, North Korea, Syria, sanctioned countries
2. Large amounts: >$100k needs scrutiny, >$500k needs extra scrutiny
3. Unusual patterns: Sudden spike, structuring, round amounts
4. Customer behavior: Inconsistent with history
5. Critical severity: Should only be used for serious cases

**Output Format**:
Return a JSON object with:
{
  "score": <float 0.0-1.0 representing confidence in decision quality>,
  "reasoning": "<detailed explanation covering indicators, severity, risk score, and why this score>",
  "needs_review": <boolean - true if score < 0.8 or special circumstances>,
  "review_reason": "<string - category like SANCTIONS, HIGH_VALUE, EDGE_CASE, LOW_CONFIDENCE, etc.>"
}

**Critical Instructions**:
1. Use the FULL range of scores (0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0)
2. Do NOT just return 1.0 or 0.0
3. Be strict on sanctions (always 0.5)
4. Be cautious on high values (cap at 0.7-0.85)
5. Score reflects CONFIDENCE, not correctness

Return ONLY the JSON object. No markdown, no explanation outside JSON.
```

---

## Human Prompt

Copy everything below:

```
Please assess the quality and reasonableness of this AML triage decision.

You will receive:

**INPUT**: The transaction details
- Look for: amount, destination, customer_id, transaction_type, etc.

**OUTPUT**: The agent's triage decision
- If flagged: OUTPUT.alert = {severity, risk_score, indicators, reasoning}
- If NOT flagged: OUTPUT.alert = null or absent

**Remember**: You do NOT have ground truth. Assess how confident you are in the decision quality based on the evidence.

Ask yourself:
1. If FLAGGED: Are there strong enough risk indicators to justify this flag?
2. If FLAGGED: Is the severity level appropriate for the indicators?
3. If FLAGGED: Does the risk score match the severity and indicators?
4. If NOT FLAGGED: Are there any red flags that should have triggered an alert?
5. If NOT FLAGGED: Is this a high-value transaction that needs extra scrutiny?

Provide your confidence assessment as a JSON object.

<example>
<input>
{input}
</input>

<output>
{output}
</output>
</example>
```

---

## Example Scenarios

### High Confidence Flagged (Score: 0.95)

**INPUT**:
```json
{
  "transaction": {
    "amount": 250000,
    "destination": "Country_X",
    "transaction_type": "wire_transfer",
    "customer_id": "abc123"
  }
}
```

**OUTPUT**:
```json
{
  "alert": {
    "severity": "HIGH",
    "risk_score": 72,
    "indicators": ["large_amount", "high_risk_destination", "unusual_for_customer"],
    "reasoning": "Large wire transfer to high-risk jurisdiction, inconsistent with customer profile"
  }
}
```

**Expected Score**:
```json
{
  "score": 0.95,
  "reasoning": "High confidence in flag decision. Three strong risk indicators (large amount $250k, high-risk destination, unusual for customer). HIGH severity is appropriate for this risk level. Risk score 72 aligns well with HIGH severity (50-69 range, slightly elevated is reasonable). Clear reasoning provided. This appears to be a justified flag.",
  "needs_review": false,
  "review_reason": null
}
```

---

### Uncertain - Sanctions (Score: 0.5)

**INPUT**:
```json
{
  "transaction": {
    "amount": 50000,
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
    "indicators": ["sanctions_related", "high_risk_country"],
    "reasoning": "Transaction to sanctioned country"
  }
}
```

**Expected Score**:
```json
{
  "score": 0.5,
  "reasoning": "SANCTIONS-RELATED: Automatic score of 0.5 regardless of decision quality. Sanctions matches require mandatory human verification to ensure accuracy of country identification and sanctions list matching. Severity CRITICAL and risk score 95 are appropriate, but human must verify before action.",
  "needs_review": true,
  "review_reason": "SANCTIONS"
}
```

---

### Edge Case Near Threshold (Score: 0.7)

**INPUT**:
```json
{
  "transaction": {
    "amount": 75000,
    "destination": "Country_Y",
    "transaction_type": "transfer"
  }
}
```

**OUTPUT**:
```json
{
  "alert": {
    "severity": "MEDIUM",
    "risk_score": 39,
    "indicators": ["moderate_amount"],
    "reasoning": "Transaction amount slightly elevated"
  }
}
```

**Expected Score**:
```json
{
  "score": 0.7,
  "reasoning": "Edge case near decision threshold. Risk score 39 is just above typical flagging threshold of 38-40. Only one weak indicator (moderate amount). MEDIUM severity may be appropriate but this is borderline. Decision could go either way. Needs human review to determine if this should be flagged or not.",
  "needs_review": true,
  "review_reason": "EDGE_CASE_THRESHOLD"
}
```

---

### High Value Not Flagged - Uncertain (Score: 0.6)

**INPUT**:
```json
{
  "transaction": {
    "amount": 600000,
    "destination": "Country_Z",
    "transaction_type": "wire_transfer"
  }
}
```

**OUTPUT**:
```json
{
  "alert": null
}
```

**Expected Score**:
```json
{
  "score": 0.6,
  "reasoning": "Very high value transaction ($600k) was NOT flagged. This needs verification. While it may be legitimate if consistent with customer history, the amount alone warrants scrutiny. Without more context about customer profile, confidence is low that this is correct to not flag. Needs human review to verify this is indeed a normal transaction for this customer.",
  "needs_review": true,
  "review_reason": "VERY_HIGH_VALUE_NOT_FLAGGED"
}
```

---

### Low Risk Flagged - Questionable (Score: 0.6)

**INPUT**:
```json
{
  "transaction": {
    "amount": 5000,
    "destination": "Country_A",
    "transaction_type": "transfer"
  }
}
```

**OUTPUT**:
```json
{
  "alert": {
    "severity": "HIGH",
    "risk_score": 35,
    "indicators": [],
    "reasoning": "Flagged for review"
  }
}
```

**Expected Score**:
```json
{
  "score": 0.6,
  "reasoning": "Low confidence in flag decision. Small amount ($5k), no high-risk destination, and NO indicators listed. Yet marked as HIGH severity with only moderate risk score of 35. Severity HIGH typically requires risk score 50-69, so 35 is inconsistent. Why was this flagged with no evidence? Likely false positive. Needs review.",
  "needs_review": true,
  "review_reason": "LOW_RISK_FLAGGED_NO_INDICATORS"
}
```

---

### Normal Transaction - High Confidence (Score: 1.0)

**INPUT**:
```json
{
  "transaction": {
    "amount": 2500,
    "destination": "Country_B",
    "transaction_type": "transfer"
  }
}
```

**OUTPUT**:
```json
{
  "alert": null
}
```

**Expected Score**:
```json
{
  "score": 1.0,
  "reasoning": "High confidence in not flagging. Low amount ($2,500), standard destination, no red flags present. This appears to be a normal legitimate transaction. No indicators of suspicious activity. Decision not to flag is appropriate and well-justified by the transaction characteristics.",
  "needs_review": false,
  "review_reason": null
}
```

---

## How to Use This Evaluator

### Step 1: Create in LangSmith UI

1. Go to **Projects** → Your project
2. Click **Evaluators** → **Create Evaluator**
3. Choose **LLM-as-Judge**
4. Name: `AML Triage Quality (Online)`
5. Copy-paste **System Prompt** (lines 19-102)
6. Copy-paste **Human Prompt** (lines 108-137)
7. Set **Feedback Type**: Score (0.0 to 1.0)
8. Set **Output Key**: `score`
9. Click **Save**

### Step 2: Run on Production Traces

**Option A: Manual Run**
1. Go to **Projects** → Filter traces by date range
2. Select traces you want to evaluate
3. Click **Evaluate** → Choose your evaluator
4. Click **Run**

**Option B: Automated (Python Script)**
Use the [online_evaluation.py](online_evaluation.py) script but configure it to use this LLM judge instead of heuristics.

### Step 3: Filter Results

**Show all cases needing review**:
```
Filter: needs_review = true
```

**Show uncertain cases**:
```
Filter: score < 0.8
```

**Show critical cases**:
```
Filter: review_reason = "SANCTIONS"
```

**Show high-value cases**:
```
Filter: review_reason contains "HIGH_VALUE"
```

---

## Comparison: Heuristic vs LLM Judge (Online)

| Aspect | Heuristic ([UI_ONLINE_EVALUATOR_FIXED.md](UI_ONLINE_EVALUATOR_FIXED.md)) | LLM Judge (This) |
|--------|---------|-----------|
| **Cost** | Free | ~$0.01-0.02 per evaluation |
| **Speed** | Instant | 1-3 seconds per trace |
| **Nuance** | Rule-based thresholds | Contextual assessment |
| **Consistency** | 100% deterministic | ~95% consistent |
| **Customization** | Edit code | Update prompt |
| **Best For** | High-volume continuous monitoring | Periodic quality checks |

**Recommendation**: Use **both**
- Heuristic evaluator for continuous real-time monitoring (every trace)
- LLM judge for periodic deep-dive quality assessments (sample of traces)

---

## Integration with Online Evaluation Script

To use this LLM judge with [online_evaluation.py](online_evaluation.py):

1. Keep the heuristic checks for fast filtering
2. Add LLM judge for cases flagged by heuristics
3. This gives you two-stage evaluation:
   - Stage 1: Heuristic (fast, catches obvious issues)
   - Stage 2: LLM judge (slower, provides nuanced assessment)

---

## Troubleshooting

### Issue: Scores still binary (1.0 or 0.0)

**Fix**:
- Check Feedback Type is **Score** (not Boolean)
- Add to system prompt: "IMPORTANT: Use decimal scores like 0.7, 0.85, 0.9. DO NOT just return 1.0 or 0.0"

### Issue: All sanctions cases get 0.5

**This is correct behavior**! Sanctions always need human review regardless of how "good" the decision looks.

### Issue: High costs from too many API calls

**Fix**:
- Use heuristic evaluator for most traces
- Only use LLM judge on sample (10-20% of traces)
- Or only on traces that heuristic flags as uncertain

### Issue: Inconsistent scores on same transaction

**Fix**:
- Set temperature to 0.0 (more deterministic)
- Add more explicit criteria in prompt
- Accept some variance (~5%) as normal

---

## Summary

This online LLM-as-judge evaluator:

✅ Works without ground truth (no reference needed)
✅ Returns confidence scores (0.5-1.0) not correctness
✅ Flags cases for human review based on uncertainty
✅ Handles special cases (sanctions, high-value, edge cases)
✅ Provides detailed reasoning for each score
✅ Can be combined with heuristic evaluator for efficiency

**Key Insight**: Score means "How confident are we in this decision?" not "Is this correct?"

Copy the prompts above into your LangSmith evaluator and you're ready for online production monitoring!
