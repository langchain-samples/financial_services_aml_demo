# LangSmith UI: Annotation Queue Integration Guide

This guide shows how to configure an evaluator in the LangSmith UI that automatically flags cases for human review and adds them to an annotation queue.

## Overview

The evaluator will:
1. Check if the AML agent flagged the transaction correctly
2. Identify cases that need human review based on criteria:
   - Low accuracy (score < 0.8)
   - False negatives (CRITICAL)
   - High-value transactions with medium confidence
   - Edge cases near decision boundaries
3. Return metadata that can be used to add cases to annotation queues

## Step 1: Create the Evaluator in LangSmith UI

1. Go to https://smith.langchain.com/
2. Navigate to **Datasets** → `aml-transaction-flagging-tests`
3. Click **"Create evaluator"** → **"Custom Code"**
4. **Name**: `AML Review Flagging Evaluator`
5. **Description**: `Identifies cases needing human review for annotation queue`

## Step 2: Copy This Code

```python
def evaluate_example(run, example):
    """
    Evaluates AML agent decisions and flags cases for human review.

    Returns score + metadata for annotation queue routing.
    """
    # Get outputs
    outputs = run.outputs if hasattr(run, 'outputs') else {}
    alert = outputs.get("alert")
    actual_flagged = alert is not None

    # Get expected outputs
    reference = example.outputs if hasattr(example, 'outputs') else {}
    expected_flagged = reference.get("should_flag", False)

    # Get transaction details for review criteria
    inputs = example.inputs if hasattr(example, 'inputs') else {}
    transaction = inputs.get("transaction", {})
    amount = transaction.get("amount", 0)

    # Calculate base score
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

    # Determine if needs review
    needs_review = False
    review_reason = None
    review_priority = "LOW"

    # Criteria 1: Incorrect decisions always need review
    if score == 0.0:
        needs_review = True
        if expected_flagged and not actual_flagged:
            review_reason = "FALSE_NEGATIVE"
            review_priority = "CRITICAL"
        else:
            review_reason = "FALSE_POSITIVE"
            review_priority = "HIGH"

    # Criteria 2: High-value transactions need extra scrutiny
    elif amount > 50000:
        needs_review = True
        review_reason = "HIGH_VALUE_TRANSACTION"
        review_priority = "MEDIUM"
        comment += f" | High-value: ${amount:,.0f}"

    # Criteria 3: Edge cases near risk threshold
    elif alert:
        risk_score = alert.get("risk_score", 0)
        if 38 <= risk_score <= 42:  # Near 40 threshold
            needs_review = True
            review_reason = "EDGE_CASE_THRESHOLD"
            review_priority = "MEDIUM"
            comment += f" | Risk score near threshold: {risk_score}"

    # Return evaluation with review metadata
    result = {
        "score": score,
        "comment": comment
    }

    # Add review metadata if needed
    if needs_review:
        result["metadata"] = {
            "needs_review": True,
            "review_reason": review_reason,
            "review_priority": review_priority,
            "transaction_amount": amount,
            "transaction_id": transaction.get("transaction_id", "unknown")
        }

    return result
```

## Step 3: Run Evaluation

After creating the evaluator:

```bash
# From your project directory
python -m evaluation.run_langsmith_evaluation --mode llm
```

Or run directly in UI:
1. Click **"Run Evaluation"** on your dataset
2. Select the `AML Review Flagging Evaluator`
3. Click **"Start Evaluation"**

## Step 4: Filter Cases for Annotation Queue

In the LangSmith UI, after evaluation runs:

1. Go to **Experiments** → Select your experiment
2. **Filter by metadata**: `needs_review = true`
3. **Sort by**: `review_priority` (CRITICAL → HIGH → MEDIUM → LOW)
4. Select filtered cases
5. Click **"Add to Annotation Queue"**
6. Choose or create queue: `aml-review-queue`

## Review Criteria Explained

### CRITICAL Priority
- **False Negatives**: Agent missed a suspicious transaction
- **Impact**: Compliance violation, regulatory risk
- **Action**: Immediate review required

### HIGH Priority
- **False Positives**: Agent incorrectly flagged normal transaction
- **Impact**: Customer friction, operational cost
- **Action**: Review within 24 hours

### MEDIUM Priority
- **High-value transactions**: > $50,000
- **Edge cases**: Risk scores 38-42 (near 40 threshold)
- **Impact**: Potential for significant loss if wrong
- **Action**: Review within 1 week

### LOW Priority
- **Correct decisions**: Score = 1.0, no special circumstances
- **Impact**: Quality assurance, training data
- **Action**: Sample review for continuous improvement

## Alternative: Programmatic Queue Addition

If you prefer to add cases to the queue programmatically (recommended for production):

```python
from langsmith import Client

client = Client()

# Get or create annotation queue
queue = client.create_annotation_queue(
    name="aml-review-queue",
    description="AML cases requiring human review"
)

# After running evaluation, filter and add runs
experiment = client.read_project(project_name="your-experiment-name")
for run in experiment.get_runs():
    # Check if needs review
    if run.feedback and any(
        f.key == "needs_review" and f.value.get("needs_review")
        for f in run.feedback
    ):
        client.create_feedback(
            run_id=run.id,
            key="queued_for_review",
            score=1.0,
            comment="Added to annotation queue"
        )
        # Add to queue
        # Note: Actual SDK method may vary by version
```

## Benefits of This Approach

✅ **Automated filtering**: Evaluation automatically identifies review cases
✅ **Prioritization**: CRITICAL/HIGH/MEDIUM/LOW for triage
✅ **Context preservation**: Full trace + metadata available for reviewers
✅ **Continuous improvement**: Human feedback loops back to model
✅ **Compliance**: Audit trail of all flagged cases and reviews

## Monitoring Review Queues

Track these metrics:
- **Review queue depth**: How many cases pending?
- **False negative rate**: Most critical metric
- **High-value transaction accuracy**: Extra scrutiny needed
- **Average review time**: Bottleneck identification
- **Reviewer agreement**: Inter-rater reliability

## Next Steps

1. ✅ Create evaluator in UI (copy code above)
2. ✅ Run evaluation on test dataset
3. ✅ Filter results by `needs_review = true`
4. ✅ Create annotation queue: `aml-review-queue`
5. ✅ Add filtered cases to queue
6. ✅ Assign reviewers from your compliance team
7. ✅ Export annotations for model fine-tuning

## Production Workflow

```
1. Transaction processed
   ↓
2. Evaluation runs (online or offline)
   ↓
3. Evaluator identifies review cases
   ↓
4. Cases automatically added to queue
   ↓
5. Compliance team reviews in UI
   ↓
6. Feedback collected (correct/incorrect + reasoning)
   ↓
7. Feedback used to improve model
   ↓
8. New evaluation run shows improvement
```

## Troubleshooting

### "metadata" not showing in results
- LangSmith may not display custom metadata in all views
- Use the API to retrieve full feedback objects
- Check experiment JSON export for metadata

### Cases not appearing in queue
- Ensure you're using the correct queue ID
- Check that runs have completed successfully
- Verify authentication/permissions for queue access

### Too many cases flagged for review
- Adjust thresholds (e.g., score < 0.7 instead of < 0.8)
- Increase high-value threshold (e.g., $100k instead of $50k)
- Add sampling logic for MEDIUM/LOW priority

### False negative not flagged as CRITICAL
- Check that `expected_should_flag` is set correctly in dataset
- Verify alert is truly `None` (not empty dict)
- Review evaluation logic for edge cases

## Resources

- LangSmith Annotation Queues: https://docs.smith.langchain.com/evaluation/annotation-queues
- Custom Evaluators: https://docs.smith.langchain.com/evaluation/custom-evaluators
- Feedback SDK: https://docs.smith.langchain.com/tracing/feedback
