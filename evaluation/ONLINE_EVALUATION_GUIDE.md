# Online Evaluation Guide

This guide explains how to use the online evaluation system to monitor AML agent traces in real-time and ensure correct transaction triage.

## Overview

The online evaluation system monitors production traces and:
- ✅ Evaluates triage decisions automatically
- ✅ Flags high-risk cases for human review
- ✅ Tracks confidence/accuracy metrics over time
- ✅ Adds problematic cases to annotation queues
- ✅ Alerts when accuracy drops below threshold

## Quick Start

### Run Once (Check Recent Traces)

```bash
# Evaluate traces from the last hour
python -m evaluation.online_evaluation --mode once

# Evaluate traces from the last 4 hours
python -m evaluation.online_evaluation --mode once --lookback 240
```

### Run Continuously (Production Monitoring)

```bash
# Check for new traces every minute
python -m evaluation.online_evaluation --mode continuous

# Check every 5 minutes
python -m evaluation.online_evaluation --mode continuous --interval 300

# Disable LLM judge (faster, uses only heuristics)
python -m evaluation.online_evaluation --mode continuous --no-llm-judge
```

## How It Works

### 1. Trace Monitoring

The system queries LangSmith for recent traces from your project:

```python
# Fetches traces from the last N minutes
runs = client.list_runs(
    project_name="financial_services_deep_agent_demo",
    start_time=cutoff_time,
    execution_order=1,  # Only root runs
    error=False,  # Only successful runs
)
```

### 2. Triage Evaluation

For each trace, it evaluates the triage decision using:

**Heuristic Checks** (fast, always enabled):
- High-value transactions (> $100k)
- Sanctions-related flags
- Critical severity alerts
- Multiple risk indicators (≥ 3)
- Edge cases near risk threshold (38-42)

**LLM Judge** (optional, more nuanced):
- Assesses overall decision quality
- Provides confidence score (0.0-1.0)
- Flags low-confidence decisions (< 0.7)

### 3. Review Flagging

Cases are flagged for human review based on:

| Criterion | Threshold | Priority |
|-----------|-----------|----------|
| Low confidence from LLM | < 0.7 | HIGH |
| High-value flagged | > $100k | HIGH |
| Very high-value | > $500k | CRITICAL |
| Sanctions-related | Any | CRITICAL |
| Critical severity | Any | CRITICAL |
| Edge case threshold | Risk 38-42 | MEDIUM |
| Multiple indicators | ≥ 3 indicators | MEDIUM |

### 4. Annotation Queue

Flagged cases are automatically:
- Added to `aml-production-review-queue`
- Tagged with review reason
- Linked back to original trace
- Visible in LangSmith UI for human review

### 5. Alerting

When average confidence drops below 80%:
```
⚠️  ACCURACY ALERT
Average confidence: 72%
Threshold: 80%
Review rate: 35%

Action required: Investigate recent changes to the system
```

## Configuration

### Environment Variables

```bash
# Required
export LANGCHAIN_API_KEY="your-api-key"
export OPENAI_API_KEY="your-openai-key"  # If using LLM judge

# Optional
export LANGCHAIN_PROJECT="financial_services_deep_agent_demo"
```

### Constants (edit in online_evaluation.py)

```python
PROJECT_NAME = "financial_services_deep_agent_demo"
ANNOTATION_QUEUE_NAME = "aml-production-review-queue"
EVALUATION_INTERVAL_SECONDS = 60  # Check every minute
ACCURACY_ALERT_THRESHOLD = 0.80  # Alert if below 80%
```

### Command-Line Options

```bash
python -m evaluation.online_evaluation \
  --mode continuous \          # once or continuous
  --lookback 120 \            # Minutes to look back (default: 60)
  --interval 300 \            # Seconds between checks (default: 60)
  --no-llm-judge \           # Disable LLM judge (faster)
  --no-queue                  # Disable annotation queue
```

## Example Output

### Single Run

```
======================================================================
Online Evaluation - 2025-01-13 14:30:00
======================================================================

Project: financial_services_deep_agent_demo
Lookback: 60 minutes

Found 15 new traces to evaluate

Evaluating: TXN-2025-001
  ✓ Confidence: 92%
Evaluating: TXN-2025-002
  ⚠️  NEEDS REVIEW: HIGH_VALUE_FLAGGED: $150,000.00 flagged for review
  ✓ Flagged for review: TXN-2025-002
Evaluating: TXN-2025-003
  ⚠️  NEEDS REVIEW: SANCTIONS: Sanctions-related alert (CRITICAL)
  ✓ Flagged for review: TXN-2025-003
...

======================================================================
Summary
======================================================================

  Total Evaluated: 15
  Average Confidence: 87%
  Needs Human Review: 3 (20.0%)

  Review Breakdown:
    HIGH_VALUE_FLAGGED: 1
    SANCTIONS: 1
    MULTIPLE_INDICATORS: 1

======================================================================
Next Steps:
======================================================================

1. Review flagged cases in LangSmith
2. Check annotation queue for cases needing human review
3. Set up continuous monitoring with --mode continuous
4. Configure alerting for accuracy drops
```

### Continuous Monitoring

```
======================================================================
STARTING CONTINUOUS ONLINE EVALUATION
======================================================================

Project: financial_services_deep_agent_demo
Interval: 60 seconds
LLM Judge: Enabled
Annotation Queue: Enabled

Press Ctrl+C to stop

======================================================================
Online Evaluation - 2025-01-13 14:30:00
======================================================================
...
Sleeping for 60 seconds...
======================================================================

======================================================================
Online Evaluation - 2025-01-13 14:31:00
======================================================================
...
```

## Integration with LangSmith UI

### View Flagged Cases

1. Go to https://smith.langchain.com/
2. Navigate to your project: `financial_services_deep_agent_demo`
3. **Filter by feedback**: `needs_review = 1.0`
4. See all cases flagged by online evaluation

### Annotation Queue

1. Navigate to **Annotation Queues** in sidebar
2. Open queue: `aml-production-review-queue`
3. Review flagged cases
4. Provide feedback (correct/incorrect + reasoning)
5. Export annotations for model improvement

### Trace Analysis

For each flagged case:
1. Click on the trace
2. See full execution flow
3. Review intermediate steps
4. Check input/output at each stage
5. Understand why it was flagged

## Use Cases

### 1. Production Monitoring

**Goal**: Ensure production system maintains accuracy

**Setup**:
```bash
# Run continuously in background
nohup python -m evaluation.online_evaluation \
  --mode continuous \
  --interval 300 \
  > logs/online_eval.log 2>&1 &
```

**Monitor**:
- Check logs for accuracy alerts
- Review annotation queue daily
- Track metrics over time

### 2. Post-Deployment Validation

**Goal**: Verify new deployment doesn't degrade quality

**Setup**:
```bash
# Before deployment: run once
python -m evaluation.online_evaluation --mode once --lookback 1440

# Deploy new version

# After deployment: run again
python -m evaluation.online_evaluation --mode once --lookback 60

# Compare metrics
```

**Check**:
- Average confidence score
- Review rate (should be similar)
- Types of cases flagged

### 3. Incident Investigation

**Goal**: Understand what went wrong during an incident

**Setup**:
```bash
# Evaluate specific time window
python -m evaluation.online_evaluation \
  --mode once \
  --lookback 120  # 2 hours before incident
```

**Analyze**:
- Which cases were flagged?
- What changed compared to normal?
- Are there patterns in failures?

### 4. Human-in-the-Loop Training

**Goal**: Build dataset of human-reviewed cases

**Setup**:
```bash
# Continuous monitoring with annotation queue
python -m evaluation.online_evaluation \
  --mode continuous \
  --interval 600  # Every 10 minutes
```

**Workflow**:
1. System flags uncertain cases
2. Compliance team reviews in UI
3. Team provides correct labels
4. Export annotations
5. Fine-tune model on human feedback

## Metrics to Track

### Key Metrics

1. **Average Confidence**: Overall quality indicator
   - Target: > 85%
   - Alert: < 80%

2. **Review Rate**: Percentage needing human review
   - Normal: 10-20%
   - High: > 30% (investigate)

3. **Review Reason Distribution**:
   - Track which criteria trigger most reviews
   - Adjust thresholds if needed

4. **Trace Volume**: Number of transactions processed
   - Monitor for anomalies
   - Capacity planning

### Tracking Over Time

Create a monitoring dashboard with:

```python
# Example: Log metrics to file
summary = evaluator.evaluate_recent_traces()

with open("metrics.jsonl", "a") as f:
    f.write(json.dumps({
        "timestamp": summary["timestamp"],
        "total_evaluated": summary["total_evaluated"],
        "avg_confidence": summary["avg_confidence"],
        "review_rate": summary["review_rate"],
    }) + "\n")
```

Then visualize with:
- Grafana
- Datadog
- Custom dashboard
- LangSmith UI charts

## Comparison: Online vs Offline Evaluation

| Aspect | Online | Offline |
|--------|--------|---------|
| **Timing** | Real-time | Batch |
| **Data** | Production traces | Test dataset |
| **Ground Truth** | Usually none | Always available |
| **Evaluation** | Heuristics + LLM judge | Rule-based + LLM judge |
| **Purpose** | Monitor production | Validate before deploy |
| **Frequency** | Continuous | On-demand |
| **Cost** | Low (heuristics only) | Higher (full evaluation) |

**Use both**:
- **Offline**: Pre-deployment validation, regression testing
- **Online**: Production monitoring, real-time quality assurance

## Advanced Configuration

### Custom Review Criteria

Edit `_should_review_online()` in [online_evaluation.py](online_evaluation.py:189-230):

```python
def _should_review_online(self, transaction_data, outputs, confidence_score):
    # Add your custom criteria
    transaction = transaction_data["transaction"]

    # Example: Flag specific countries
    if transaction.get("destination") in ["Country_X", "Country_Y"]:
        return True, "HIGH_RISK_COUNTRY"

    # Example: Flag specific customers
    if transaction.get("customer_id") in watchlist:
        return True, "WATCHLIST_CUSTOMER"

    # ... existing criteria
```

### Custom Alerting

Add alerting to `_send_accuracy_alert()`:

```python
def _send_accuracy_alert(self, summary):
    # Send email
    send_email(
        to="compliance-team@company.com",
        subject="AML System Accuracy Alert",
        body=f"Average confidence: {summary['avg_confidence']:.2%}"
    )

    # Send Slack notification
    post_to_slack(
        channel="#aml-alerts",
        text=f"⚠️ Accuracy drop detected: {summary['avg_confidence']:.2%}"
    )

    # Create incident ticket
    create_jira_ticket(
        project="COMPLIANCE",
        summary="AML accuracy below threshold",
        description=json.dumps(summary, indent=2)
    )
```

### Integration with CI/CD

```yaml
# .github/workflows/post-deploy.yml
name: Post-Deploy Validation

on:
  deployment_status:

jobs:
  validate:
    runs-on: ubuntu-latest
    if: github.event.deployment_status.state == 'success'

    steps:
      - uses: actions/checkout@v3

      - name: Run online evaluation
        env:
          LANGCHAIN_API_KEY: ${{ secrets.LANGCHAIN_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python -m evaluation.online_evaluation --mode once --lookback 60

      - name: Check metrics
        run: |
          # Parse output and fail if accuracy < 80%
          python scripts/check_metrics.py
```

## Troubleshooting

### No traces found

**Problem**: "No new traces to evaluate"

**Solutions**:
1. Check project name matches: `echo $LANGCHAIN_PROJECT`
2. Increase lookback: `--lookback 240`
3. Verify traces exist in LangSmith UI
4. Check date/time (timezone issues)

### All cases flagged for review

**Problem**: Review rate > 50%

**Solutions**:
1. Increase confidence threshold: Edit `confidence_score < 0.7` → `< 0.6`
2. Raise high-value threshold: Edit `amount > 100000` → `> 200000`
3. Disable LLM judge if too conservative: `--no-llm-judge`
4. Review and adjust criteria in `_should_review_online()`

### LLM judge errors

**Problem**: "Error in LLM judge evaluation"

**Solutions**:
1. Check OpenAI API key: `echo $OPENAI_API_KEY`
2. Verify API credits/quota
3. Run without LLM judge: `--no-llm-judge`
4. Check error logs for rate limiting

### Annotation queue errors

**Problem**: "Error adding to queue"

**Solutions**:
1. Check LangSmith API permissions
2. Verify queue exists: Visit UI → Annotation Queues
3. Run without queue: `--no-queue`
4. Check LangSmith API version compatibility

## Best Practices

### 1. Start Simple
- Begin with `--mode once` to test
- Gradually increase to continuous monitoring
- Enable features incrementally

### 2. Tune Thresholds
- Monitor false positive rate in annotation queue
- Adjust review criteria based on team capacity
- Balance automation vs human review

### 3. Review Regularly
- Check annotation queue daily
- Provide feedback on flagged cases
- Use feedback to improve criteria

### 4. Monitor Metrics
- Track average confidence over time
- Watch for sudden drops (indicates issues)
- Compare to offline evaluation results

### 5. Integrate with Operations
- Alert compliance team on CRITICAL cases
- Create dashboards for stakeholders
- Include in incident response procedures

## Next Steps

1. ✅ Run initial evaluation: `python -m evaluation.online_evaluation --mode once`
2. ✅ Review flagged cases in LangSmith UI
3. ✅ Adjust thresholds based on results
4. ✅ Set up continuous monitoring
5. ✅ Configure alerting for your team
6. ✅ Integrate with CI/CD pipeline
7. ✅ Build feedback loop with compliance team

## Related Documentation

- [Offline Evaluation](offline_evaluation_with_queue.py): Batch evaluation with test dataset
- [UI Evaluator Guide](UI_EVALUATOR_GUIDE.md): Configuring evaluators in LangSmith UI
- [LLM Judge Evaluator](llm_judge_evaluator.py): Detailed LLM-based evaluation
- [Test Dataset](test_dataset.py): Curated test cases for offline evaluation
