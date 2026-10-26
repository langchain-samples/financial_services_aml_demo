# LangSmith UI: Online Evaluation Setup

This guide shows how to create an evaluator in the LangSmith UI that checks if traces are being correctly triaged by the AML agent.

## Overview

You can create evaluators in the LangSmith UI that:
- Run on **any trace** in your project (not just test datasets)
- Evaluate production traffic in real-time
- Flag cases for annotation queues
- Track triage quality metrics

## Step 1: Navigate to Evaluators

Two ways to create evaluators in LangSmith UI:

### Option A: From Dataset (Recommended for Testing)
1. Go to https://smith.langchain.com/
2. Click **Datasets** → `aml-transaction-flagging-tests`
3. Click **"Create evaluator"**

### Option B: From Project (For Production Monitoring)
1. Go to https://smith.langchain.com/
2. Click **Projects** → `financial_services_deep_agent_demo`
3. Click **"Evaluators"** tab
4. Click **"Create evaluator"**

## Step 2: Choose Evaluator Type

Select **"Custom Code"** (not "LLM as Judge")

## Step 3: Configure Evaluator

**Name**: `AML Triage Quality Checker`

**Description**: `Evaluates if transactions are correctly triaged and flags cases for human review`

## Step 4: Copy This Code

### Basic Version (No Ground Truth Needed)

This works on **any trace**, even without expected outputs:

```python
from langsmith.schemas import Run, Example

def evaluator(run: Run, example: Example) -> dict:
    """
    Evaluates AML triage decisions on production traces.
    Works even without ground truth by checking for risk indicators.
    """
    # Get outputs
    outputs = run.outputs if run.outputs else {}
    alert = outputs.get("alert")

    # Get inputs
    inputs = run.inputs if run.inputs else {}
    transaction = inputs.get("transaction", {})

    # Extract key info
    amount = transaction.get("amount", 0)
    destination = transaction.get("destination", "")

    # Initialize evaluation
    needs_review = False
    review_reason = ""
    confidence = 1.0
    comment = ""

    # Check if alert was generated
    if alert:
        risk_score = alert.get("risk_score", 0)
        severity = alert.get("severity", "")
        indicators = alert.get("indicators", [])

        # CRITICAL: Sanctions-related always needs review
        if any("sanction" in str(ind).lower() for ind in indicators):
            needs_review = True
            review_reason = "SANCTIONS"
            confidence = 0.5  # Uncertain, needs human verification
            comment = "🔴 CRITICAL: Sanctions-related alert - requires human review"

        # HIGH: Large amounts flagged
        elif amount > 100000:
            needs_review = True
            review_reason = "HIGH_VALUE"
            confidence = 0.7
            comment = f"⚠️ HIGH: ${amount:,.0f} transaction flagged - verify accuracy"

        # MEDIUM: Edge cases near threshold
        elif 38 <= risk_score <= 42:
            needs_review = True
            review_reason = "EDGE_CASE"
            confidence = 0.8
            comment = f"⚠️ MEDIUM: Risk score {risk_score} near threshold - edge case"

        # MEDIUM: Critical severity
        elif severity == "CRITICAL":
            needs_review = True
            review_reason = "CRITICAL_SEVERITY"
            confidence = 0.7
            comment = f"⚠️ MEDIUM: Marked as CRITICAL severity - verify appropriateness"

        # MEDIUM: Multiple indicators
        elif len(indicators) >= 3:
            needs_review = True
            review_reason = "MULTIPLE_INDICATORS"
            confidence = 0.75
            comment = f"⚠️ MEDIUM: {len(indicators)} risk indicators - complex case"

        else:
            # Alert seems reasonable
            comment = f"✓ Alert generated with risk score {risk_score}, severity {severity}"

    else:
        # No alert generated
        # Flag very high-value even if not alerted
        if amount > 500000:
            needs_review = True
            review_reason = "VERY_HIGH_VALUE_NO_ALERT"
            confidence = 0.6
            comment = f"⚠️ HIGH: ${amount:,.0f} NOT flagged - verify this is correct"
        else:
            comment = "✓ No alert generated"

    # Return evaluation result
    result = {
        "key": "triage_quality",
        "score": confidence,
        "comment": comment
    }

    # Add metadata for filtering in UI
    if needs_review:
        result["metadata"] = {
            "needs_review": True,
            "review_reason": review_reason,
            "priority": "CRITICAL" if review_reason == "SANCTIONS" else "HIGH" if amount > 100000 else "MEDIUM",
            "transaction_amount": amount
        }

    return result
```

### Advanced Version (With Ground Truth Comparison)

Use this if you have expected outputs in your dataset:

```python
from langsmith.schemas import Run, Example

def evaluator(run: Run, example: Example) -> dict:
    """
    Evaluates AML triage with ground truth comparison when available.
    """
    # Get outputs
    outputs = run.outputs if run.outputs else {}
    alert = outputs.get("alert")
    actual_flagged = alert is not None

    # Get inputs
    inputs = run.inputs if run.inputs else {}
    transaction = inputs.get("transaction", {})
    amount = transaction.get("amount", 0)

    # Get expected outputs (if available)
    reference = example.outputs if example.outputs else {}
    expected_flagged = reference.get("should_flag")

    # Initialize
    needs_review = False
    review_reason = ""
    score = 0.5  # Default: uncertain
    comment = ""

    # If we have ground truth, compare
    if expected_flagged is not None:
        if actual_flagged == expected_flagged:
            score = 1.0
            if actual_flagged:
                comment = "✓ Correctly flagged as suspicious"
            else:
                comment = "✓ Correctly identified as normal"
        else:
            score = 0.0
            needs_review = True
            if expected_flagged and not actual_flagged:
                review_reason = "FALSE_NEGATIVE"
                comment = "🔴 CRITICAL: Missed suspicious transaction (FALSE NEGATIVE)"
            else:
                review_reason = "FALSE_POSITIVE"
                comment = "⚠️ HIGH: Incorrectly flagged normal transaction (FALSE POSITIVE)"

    # Additional checks even if no ground truth
    if alert:
        risk_score = alert.get("risk_score", 0)
        severity = alert.get("severity", "")
        indicators = alert.get("indicators", [])

        # Sanctions always needs review
        if any("sanction" in str(ind).lower() for ind in indicators):
            needs_review = True
            if not review_reason:
                review_reason = "SANCTIONS"
                score = 0.5
                comment = "🔴 CRITICAL: Sanctions-related - verify accuracy"

        # High-value transactions
        if amount > 100000 and not needs_review:
            needs_review = True
            review_reason = "HIGH_VALUE"
            score = max(score, 0.7)
            comment = f"{comment} | High-value: ${amount:,.0f}"

        # Edge cases
        if 38 <= risk_score <= 42 and not needs_review:
            needs_review = True
            review_reason = "EDGE_CASE"
            score = max(score, 0.8)
            comment = f"{comment} | Edge case: risk {risk_score}"

    # Build result
    result = {
        "key": "triage_correctness",
        "score": score,
        "comment": comment.strip()
    }

    if needs_review:
        result["metadata"] = {
            "needs_review": True,
            "review_reason": review_reason,
            "priority": "CRITICAL" if "FALSE_NEGATIVE" in review_reason or "SANCTIONS" in review_reason else "HIGH",
            "amount": amount
        }

    return result
```

## Step 5: Save Evaluator

Click **"Create"** or **"Save"**

## Step 6: Run on Traces

### Method A: Run on Test Dataset

1. Go to **Datasets** → `aml-transaction-flagging-tests`
2. Click **"Run Evaluation"**
3. Select your evaluator
4. Click **"Start"**

### Method B: Run on Production Traces

1. Go to **Projects** → `financial_services_deep_agent_demo`
2. Filter traces by date/time range
3. Select multiple traces (checkbox)
4. Click **"Evaluate"**
5. Choose your evaluator
6. Click **"Run"**

### Method C: Run on Specific Experiment

1. Go to **Experiments** tab
2. Click on an experiment
3. Click **"Add Evaluator"**
4. Select your evaluator
5. Click **"Run"**

## Step 7: View Results

After evaluation runs:

### Filter for Cases Needing Review

1. In the results view, add filter:
   - Field: `metadata.needs_review`
   - Operator: `=`
   - Value: `true`

2. Sort by priority:
   - Field: `metadata.priority`
   - Order: Descending (CRITICAL → HIGH → MEDIUM)

### View Individual Cases

Click on any trace to see:
- Input transaction details
- Agent's decision (alert or no alert)
- Evaluator feedback and score
- Review reason and priority
- Full execution trace

## Step 8: Create Annotation Queue

For flagged cases:

1. Select traces where `needs_review = true`
2. Click **"Add to Annotation Queue"**
3. Choose or create: `aml-triage-review-queue`
4. Click **"Add"**

## Step 9: Review in Annotation Queue

1. Navigate to **Annotation Queues** (left sidebar)
2. Open `aml-triage-review-queue`
3. Review each case:
   - Was the triage decision correct?
   - If alert: was it appropriate?
   - If no alert: should there have been one?
4. Provide feedback:
   - **Correct**: Agent made right decision
   - **Incorrect**: Agent made wrong decision
   - **Comments**: Explain why

## Automation Options

### Option 1: Scheduled Evaluation (Coming Soon)

LangSmith will support scheduled evaluators:
- Run every N hours
- Automatically evaluate new traces
- Auto-flag for annotation queue

**Current Workaround**: Use the Python script with cron:

```bash
# crontab -e
# Run every hour
0 * * * * cd /path/to/project && python -m evaluation.online_evaluation --mode once >> logs/eval.log 2>&1
```

### Option 2: GitHub Actions

```yaml
# .github/workflows/online-eval.yml
name: Online Evaluation

on:
  schedule:
    - cron: '0 */4 * * *'  # Every 4 hours
  workflow_dispatch:  # Manual trigger

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run online evaluation
        env:
          LANGCHAIN_API_KEY: ${{ secrets.LANGCHAIN_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python -m evaluation.online_evaluation --mode once --lookback 240
```

### Option 3: LangSmith API

Programmatically evaluate traces:

```python
from langsmith import Client

client = Client()

# Get recent runs
runs = client.list_runs(
    project_name="financial_services_deep_agent_demo",
    start_time=datetime.now() - timedelta(hours=1)
)

# Run evaluator on each
for run in runs:
    # Evaluator runs automatically if configured in UI
    pass
```

## Best Practices

### 1. Start with Basic Version

- Use the simple evaluator first
- Test on your dataset
- Verify it catches the right cases

### 2. Tune Thresholds

Based on your results:
- Adjust amount thresholds (`100000` → `200000`)
- Modify risk score ranges (`38-42` → `35-45`)
- Add/remove criteria

### 3. Monitor Review Queue

- Check daily for new cases
- Provide feedback consistently
- Track inter-rater agreement

### 4. Iterate on Criteria

As you learn from reviews:
- Add new criteria for patterns you discover
- Remove criteria that flag too many false positives
- Adjust confidence scores

### 5. Combine with Offline Evaluation

- Use **offline** for pre-deployment testing
- Use **online** for production monitoring
- Compare metrics between both

## Troubleshooting

### "TypeError: pyFunc is not a function"

**Fix**: Ensure:
1. Function name is exactly `evaluator`
2. Has signature: `evaluator(run: Run, example: Example)`
3. Imports at top: `from langsmith.schemas import Run, Example`
4. Returns dict with `key` and `score`

### "AttributeError: 'NoneType' object has no attribute..."

**Fix**: Add safe access:
```python
# Instead of: run.outputs.get("alert")
# Use:
outputs = run.outputs if run.outputs else {}
alert = outputs.get("alert")
```

### Evaluator not showing in list

**Fix**:
1. Make sure you saved it
2. Refresh the page
3. Check you're in the right project
4. Try creating in Dataset instead of Project

### No metadata in results

**Issue**: LangSmith may not display all metadata fields

**Workaround**:
- Click "Export" to download results JSON
- Use LangSmith API to fetch full results
- Check trace details page

## Example Walkthrough

### Scenario: Monitor Last 24 Hours of Production

**Step 1**: Create the evaluator in UI (copy Basic Version code above)

**Step 2**: Go to your project

**Step 3**: Filter traces:
- Date range: Last 24 hours
- Status: Successful

**Step 4**: Select all traces (or sample)

**Step 5**: Click "Evaluate" → Choose evaluator → Run

**Step 6**: Wait for completion (progress bar)

**Step 7**: View results:
```
Total evaluated: 847 traces
Average score: 0.82
Needs review: 134 (15.8%)

Review breakdown:
- HIGH_VALUE: 89
- SANCTIONS: 12
- EDGE_CASE: 23
- MULTIPLE_INDICATORS: 10
```

**Step 8**: Filter for `needs_review = true`

**Step 9**: Sort by `priority` (CRITICAL first)

**Step 10**: Review sanctions cases first (12 traces)

**Step 11**: Add to annotation queue for team review

**Step 12**: Export feedback to improve model

## Comparison: UI vs Python Script

| Feature | UI Evaluator | Python Script |
|---------|-------------|---------------|
| **Setup** | Quick, no code deploy | Requires deployment |
| **Running** | Manual or via API | Automated (cron/CI) |
| **Customization** | Limited to UI code editor | Full Python flexibility |
| **Monitoring** | Manual checks | Continuous automated |
| **Alerting** | Manual | Automated (email/Slack) |
| **Best For** | Ad-hoc checks, demos | Production monitoring |

**Recommendation**:
- Use **UI** for initial setup and testing
- Use **Python script** for production continuous monitoring
- Use **both** for comprehensive coverage

## Next Steps

1. ✅ Create evaluator in UI using code above
2. ✅ Test on your test dataset first
3. ✅ Run on last hour of production traces
4. ✅ Review flagged cases
5. ✅ Tune thresholds based on results
6. ✅ Set up annotation queue workflow
7. ✅ Deploy Python script for continuous monitoring
8. ✅ Train team on reviewing flagged cases

## Related Resources

- [Online Evaluation Python Script](online_evaluation.py)
- [Online Evaluation Guide](ONLINE_EVALUATION_GUIDE.md)
- [Offline Evaluation](offline_evaluation_with_queue.py)
- [UI Evaluator Guide](UI_EVALUATOR_GUIDE.md)
- [LangSmith Docs](https://docs.smith.langchain.com/)
