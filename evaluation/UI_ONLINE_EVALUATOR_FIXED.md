# Fixed Online Evaluator for LangSmith UI

This evaluator properly scores traces based on decision quality indicators, not just 1 or 0.

## The Problem

The current evaluator gives scores of 1.0 or 0.0, which doesn't show nuance. We need a scoring system that reflects **confidence in the decision**, not just pass/fail.

## Solution: Confidence-Based Scoring

Instead of binary pass/fail, score based on:
- **1.0 (100%)**: High confidence the decision is correct
- **0.9-0.99**: Likely correct but worth monitoring
- **0.7-0.89**: Medium confidence, may need review
- **0.5-0.69**: Low confidence, should review
- **< 0.5**: Very uncertain, definitely needs review

## Fixed Evaluator Code

Copy this into your LangSmith UI evaluator:

```python
from langsmith.schemas import Run, Example

def evaluator(run: Run, example: Example) -> dict:
    """
    Evaluates AML triage quality with confidence-based scoring.

    Scoring:
    - 1.0: High confidence decision is correct
    - 0.9: Likely correct, monitor
    - 0.8: Some uncertainty
    - 0.7: Medium confidence, may need review
    - 0.6: Low confidence, should review
    - 0.5: Very uncertain, definitely review
    """
    # Get outputs safely
    outputs = run.outputs if run.outputs else {}
    alert = outputs.get("alert")

    # Get inputs safely
    inputs = run.inputs if run.inputs else {}
    transaction = inputs.get("transaction", {})

    # Extract transaction details
    amount = transaction.get("amount", 0)
    destination = transaction.get("destination", "")
    customer_id = transaction.get("customer_id", "")

    # Initialize scoring
    confidence_score = 1.0  # Start optimistic
    flags = []
    needs_review = False
    review_reason = ""

    # === DECISION WAS TO FLAG (Alert Generated) ===
    if alert:
        risk_score = alert.get("risk_score", 0)
        severity = alert.get("severity", "")
        indicators = alert.get("indicators", [])

        # Strong indicators - high confidence
        if any("sanction" in str(ind).lower() for ind in indicators):
            # SANCTIONS: Always needs human verification
            confidence_score = 0.5
            needs_review = True
            review_reason = "SANCTIONS"
            flags.append("🔴 CRITICAL: Sanctions hit - MUST verify accuracy")

        elif severity == "CRITICAL" and risk_score >= 70:
            # High risk + critical = likely correct but verify
            confidence_score = 0.8
            needs_review = True
            review_reason = "CRITICAL_HIGH_RISK"
            flags.append(f"⚠️ Critical severity + risk {risk_score} - verify appropriateness")

        elif risk_score >= 60:
            # High risk score = likely correct
            confidence_score = 0.95
            flags.append(f"✓ High risk score ({risk_score}) suggests correct flag")

        elif 50 <= risk_score < 60:
            # Medium-high risk = probably correct
            confidence_score = 0.9
            flags.append(f"✓ Medium-high risk ({risk_score})")

        elif 40 <= risk_score < 50:
            # Medium risk = less certain
            confidence_score = 0.85
            flags.append(f"⚠️ Medium risk ({risk_score}) - borderline case")

        elif 38 <= risk_score < 40:
            # Just above threshold = edge case
            confidence_score = 0.7
            needs_review = True
            review_reason = "EDGE_CASE_LOW"
            flags.append(f"⚠️ Edge case: risk {risk_score} just above threshold")

        else:
            # Low risk but still flagged = questionable
            confidence_score = 0.6
            needs_review = True
            review_reason = "LOW_RISK_FLAGGED"
            flags.append(f"⚠️ LOW risk ({risk_score}) but flagged - verify not false positive")

        # Adjust based on amount
        if amount > 500000:
            # Very high value = extra scrutiny needed regardless
            confidence_score = min(confidence_score, 0.7)
            needs_review = True
            if not review_reason:
                review_reason = "VERY_HIGH_VALUE"
            flags.append(f"💰 Very high value: ${amount:,.0f} - verify decision")

        elif amount > 100000:
            # High value = moderate scrutiny
            confidence_score = min(confidence_score, 0.85)
            flags.append(f"💰 High value: ${amount:,.0f}")

        # Check for multiple indicators (increases confidence it should be flagged)
        if len(indicators) >= 3:
            confidence_score = min(confidence_score + 0.05, 1.0)  # Slight boost
            flags.append(f"✓ Multiple indicators ({len(indicators)}) support flag")
        elif len(indicators) == 0:
            # No indicators but flagged? Suspicious
            confidence_score = min(confidence_score, 0.6)
            needs_review = True
            if not review_reason:
                review_reason = "NO_INDICATORS"
            flags.append("⚠️ Flagged but no indicators listed")

    # === DECISION WAS NOT TO FLAG (No Alert) ===
    else:
        # Most transactions shouldn't be flagged, so default confidence is high
        confidence_score = 1.0

        # But check for red flags that suggest it SHOULD have been flagged

        # Very high amounts not flagged = needs verification
        if amount > 500000:
            confidence_score = 0.6
            needs_review = True
            review_reason = "VERY_HIGH_VALUE_NOT_FLAGGED"
            flags.append(f"⚠️ ${amount:,.0f} NOT flagged - verify this is legitimate")

        elif amount > 250000:
            confidence_score = 0.85
            flags.append(f"💰 High value (${amount:,.0f}) not flagged - likely ok but note")

        # Check for high-risk destinations (if you have a list)
        # Example: if destination in ["Country_A", "Country_B"]:
        #     confidence_score = 0.7
        #     needs_review = True
        #     review_reason = "HIGH_RISK_DESTINATION_NOT_FLAGGED"
        #     flags.append(f"⚠️ High-risk destination ({destination}) not flagged")

        # Otherwise assume correctly not flagged
        if not flags:
            flags.append("✓ Not flagged - appears legitimate")

    # Build comment
    comment = " | ".join(flags)

    # Build result
    result = {
        "key": "triage_quality",
        "score": confidence_score,
        "comment": comment
    }

    # Add metadata for filtering
    if needs_review or confidence_score < 0.8:
        result["metadata"] = {
            "needs_review": True,
            "review_reason": review_reason if review_reason else "LOW_CONFIDENCE",
            "confidence": confidence_score,
            "amount": amount,
            "flagged": alert is not None
        }

    return result
```

## How Scoring Works Now

### For Flagged Transactions (Alert Generated)

| Scenario | Score | Needs Review? | Reason |
|----------|-------|---------------|--------|
| Sanctions hit | 0.5 | ✅ Yes | Always verify sanctions |
| Risk 70+ (Critical) | 0.8 | ✅ Yes | Verify severity appropriate |
| Risk 60-69 | 0.95 | ❌ No | High confidence correct |
| Risk 50-59 | 0.9 | ❌ No | Likely correct |
| Risk 40-49 | 0.85 | ❌ No | Probably correct |
| Risk 38-39 | 0.7 | ✅ Yes | Edge case near threshold |
| Risk < 38 | 0.6 | ✅ Yes | Low risk but flagged? |
| + Very high value (>$500k) | -0.3 | ✅ Yes | Extra scrutiny |
| + High value (>$100k) | -0.15 | Maybe | Moderate scrutiny |
| + Multiple indicators (3+) | +0.05 | ❌ No | Increases confidence |
| + No indicators | 0.6 | ✅ Yes | Why flagged? |

### For Non-Flagged Transactions (No Alert)

| Scenario | Score | Needs Review? | Reason |
|----------|-------|---------------|--------|
| Normal transaction | 1.0 | ❌ No | Likely legitimate |
| High value (>$250k) | 0.85 | ❌ No | Note but likely ok |
| Very high value (>$500k) | 0.6 | ✅ Yes | Should verify legitimate |

## Example Results

### Good Case (Score 0.95)
```
Transaction: $50,000 to Country_X
Alert: Yes (Risk: 65, Severity: HIGH)
Score: 0.95
Comment: ✓ High risk score (65) suggests correct flag
Needs Review: No
```

### Edge Case (Score 0.7)
```
Transaction: $75,000 to Country_Y
Alert: Yes (Risk: 39, Severity: MEDIUM)
Score: 0.7
Comment: ⚠️ Edge case: risk 39 just above threshold
Needs Review: Yes
Reason: EDGE_CASE_LOW
```

### Critical Case (Score 0.5)
```
Transaction: $25,000 to Iran
Alert: Yes (Risk: 85, Severity: CRITICAL)
Score: 0.5
Comment: 🔴 CRITICAL: Sanctions hit - MUST verify accuracy
Needs Review: Yes
Reason: SANCTIONS
```

### Suspicious Non-Flag (Score 0.6)
```
Transaction: $600,000 to Country_Z
Alert: No
Score: 0.6
Comment: ⚠️ $600,000 NOT flagged - verify this is legitimate
Needs Review: Yes
Reason: VERY_HIGH_VALUE_NOT_FLAGGED
```

## Filtering Results

After running the evaluator:

### Show All Cases Needing Review
- Filter: `metadata.needs_review = true`
- Shows: Low confidence scores, edge cases, sanctions, high-value

### Show Only High-Confidence Cases
- Filter: `score >= 0.9`
- Shows: Decisions we're confident about

### Show Uncertain Cases
- Filter: `score < 0.8`
- Shows: All cases with some uncertainty

### Show by Priority
- Filter by `metadata.review_reason`:
  - `SANCTIONS` (most critical)
  - `VERY_HIGH_VALUE` or `VERY_HIGH_VALUE_NOT_FLAGGED`
  - `CRITICAL_HIGH_RISK`
  - `EDGE_CASE_LOW`
  - `LOW_RISK_FLAGGED`

## Tuning the Scoring

Adjust these based on your needs:

### Make Stricter (More Cases Flagged for Review)
```python
# Change:
elif 40 <= risk_score < 50:
    confidence_score = 0.85  # Currently don't flag

# To:
elif 40 <= risk_score < 50:
    confidence_score = 0.75  # Now flags for review (< 0.8)
    needs_review = True
    review_reason = "MEDIUM_RISK_BORDERLINE"
```

### Adjust Value Thresholds
```python
# Change:
if amount > 500000:  # Current very high threshold

# To:
if amount > 250000:  # Lower threshold = more scrutiny
```

### Add Custom Rules
```python
# Add after amount checks:

# Flag specific high-risk destinations
high_risk_countries = ["Country_A", "Country_B", "Country_C"]
if destination in high_risk_countries:
    confidence_score = min(confidence_score, 0.7)
    needs_review = True
    if not review_reason:
        review_reason = "HIGH_RISK_DESTINATION"
    flags.append(f"⚠️ High-risk destination: {destination}")

# Flag frequent transactors
if customer_has_high_frequency:  # Add your logic
    confidence_score = min(confidence_score, 0.8)
    flags.append("⚠️ High transaction frequency for customer")
```

## Summary

This evaluator now gives you:

✅ **Nuanced scores** (not just 1 or 0) showing confidence in decisions

✅ **Automatic flagging** of cases that need human review

✅ **Clear explanations** of why each score was assigned

✅ **Filterable metadata** to find specific types of cases

✅ **Tunable thresholds** to adjust sensitivity

The score reflects **how confident we are that the triage decision was correct**, not just whether it matched some ground truth (which doesn't exist in production monitoring).
