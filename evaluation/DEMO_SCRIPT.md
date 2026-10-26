# AML Evaluator Demo Script

Quick script for demonstrating the AML transaction flagging evaluation system.

## Setup (Before Demo)

```bash
# 1. Ensure API keys are set
export LANGCHAIN_API_KEY="your-key"
export OPENAI_API_KEY="your-key"

# 2. Create dataset (if not already done)
python -m evaluation.run_langsmith_evaluation --mode llm
```

## Demo Flow (10 minutes)

### Part 1: Show the Problem (2 min)

**Setup**: Open LangSmith UI to Datasets page

**Say**:
> "We have an AML system that flags suspicious transactions. But how do we know it's working correctly? We need systematic evaluation."

**Show**:
1. Navigate to `aml-transaction-flagging-tests` dataset
2. Click through a few examples
3. Point out the variety: sanctions, structuring, large amounts, normal transactions

**Key Point**:
> "14 carefully crafted test cases covering all major scenarios"

---

### Part 2: Configure Simple Evaluator in UI (3 min)

**Setup**: Stay on dataset page

**Say**:
> "Let me show you how easy it is to create an evaluator right here in the UI - no code deployment needed."

**Demo Steps**:

1. Click **"Create your first evaluator"**
2. Select **"Custom Code"**
3. **Name**: `Transaction Flagging Correctness`
4. **Paste this code**:

```python
def evaluate(outputs: dict, reference_outputs: dict) -> dict:
    """Check if agent correctly flagged the transaction."""
    alert = outputs.get("alert")
    actual_flagged = alert is not None
    expected_flagged = reference_outputs.get("should_flag", False)

    if actual_flagged == expected_flagged:
        score = 1.0
        comment = "✓ Correct decision"
    else:
        score = 0.0
        if expected_flagged:
            comment = "✗ MISS: Should have flagged"
        else:
            comment = "✗ FALSE POSITIVE"

    return {"score": score, "comment": comment}
```

5. Click **"Create"**

**Say**:
> "That's it! Now we have an evaluator that checks if our agent makes the right flagging decisions. Let's run it."

---

### Part 3: Run Evaluation & Show Results (3 min)

**Setup**: Have experiment ready or run live

**Option A - Pre-run (Safer)**:
Before demo, run:
```bash
python -m evaluation.run_langsmith_evaluation --mode both
```

**Option B - Live (More impressive)**:
Run during demo:
```bash
python -m evaluation.run_langsmith_evaluation --mode llm
```

**Show Results**:

1. Navigate to **Experiments** tab
2. Click latest experiment (`aml-eval-TIMESTAMP`)
3. **Point out**:
   - Overall accuracy score (should be ~85-95%)
   - Number of tests passed/failed
   - Both evaluators running:
     - Your UI evaluator (simple correctness)
     - LLM judge (detailed feedback)

4. **Click on a test case** (pick a passed one):
   - Show the input (transaction details)
   - Show the output (alert details)
   - Show evaluator feedback
   - Show LLM judge reasoning

5. **Click on a failed case** (if any):
   - Show why it failed
   - Show LLM judge recommendations
   - Discuss how this helps improve the system

**Key Points**:
> "Notice we're running TWO evaluators:
> - Simple correctness (binary pass/fail)
> - LLM judge (nuanced feedback with reasoning)
>
> This gives us both quantitative metrics AND qualitative insights."

---

### Part 4: Show Production Code (2 min)

**Setup**: Open your IDE or GitHub

**Say**:
> "For production, you wouldn't configure evaluators in the UI - you'd use code for version control and CI/CD integration."

**Show**:

1. Open `evaluation/llm_judge_evaluator.py`
   - Point out the sophisticated LLM-based evaluation
   - Show the prompt engineering
   - Mention weighted scoring (flag 40%, severity 25%, etc.)

2. Open `evaluation/aml_evaluator.py`
   - Show rule-based metrics
   - Point out false positive/negative calculations
   - Mention precision, recall, F1

3. Open `evaluation/run_langsmith_evaluation.py`
   - Show how it integrates with LangSmith's `evaluate()` function
   - Point out concurrency settings
   - Mention CI/CD integration potential

**Say**:
> "In production, this runs automatically:
> - Every git push triggers evaluation
> - Must pass 80% accuracy to deploy
> - Results tracked over time in LangSmith
> - Team gets notified of regressions"

---

## Key Talking Points

### Benefits Highlighted

✅ **Fast Iteration**: Configure evaluators in minutes, not hours
✅ **Multiple Perspectives**: Rule-based + LLM judge = comprehensive
✅ **Production Ready**: Code-based for CI/CD integration
✅ **Visual Results**: Stakeholders can review in UI
✅ **Actionable Feedback**: LLM provides specific improvement suggestions

### Common Questions

**Q: How accurate is the LLM judge?**
A: "We also run rule-based evaluators as a sanity check. When they agree, high confidence. When they disagree, that's interesting - worth investigating."

**Q: Isn't this expensive to run?**
A: "LLM judge uses GPT-4o-mini (cheap). 14 test cases = ~$0.10 per run. Worth it to catch bugs before production."

**Q: Can we add more test cases?**
A: "Absolutely! Just add to `test_dataset.py`. We recommend 30-50 cases for comprehensive coverage."

**Q: What about false negatives?**
A: "That's our #1 concern. The evaluator weights flag correctness highest (40%). Missing a suspicious transaction is worse than a false positive."

**Q: Can non-technical people use this?**
A: "Yes! They can review results in the LangSmith UI, see why tests pass/fail, and even configure simple evaluators without coding."

---

## Backup: Live Debugging Demo

If you have extra time or want to show debugging:

1. **Pick a failing test case** (or create one)
2. **Click "View Trace"**
3. **Show the execution flow**:
   - Transaction comes in
   - Pattern analysis
   - Sanctions check
   - Anomaly detection
   - Alert generation
4. **Show intermediate results** at each step
5. **Identify where logic fails**
6. **Discuss how to fix it**

**Say**:
> "This is the power of LangSmith - not just pass/fail, but full observability into WHY decisions were made."

---

## Wrap Up

**Summary**:
> "We've shown three ways to evaluate:
> 1. **UI Evaluators** - Quick, visual, demo-friendly
> 2. **Code Evaluators** - Production-ready, version-controlled
> 3. **LLM Judge** - Nuanced feedback, continuous improvement
>
> All integrated in one platform, tracking accuracy over time."

**Next Steps** (if interested):
1. Set up their own test dataset
2. Configure evaluators for their use case
3. Integrate with CI/CD pipeline
4. Set up alerting for accuracy drops

---

## Time Variations

**5-min version**: Parts 1 + 2 + 3 (skip production code)
**10-min version**: All parts
**15-min version**: All parts + live debugging
**20-min version**: All + Q&A + live test case creation

---

## Files Reference

- **Demo Evaluators**: [ui_evaluators.py](ui_evaluators.py)
- **UI Guide**: [UI_EVALUATOR_GUIDE.md](UI_EVALUATOR_GUIDE.md)
- **Production Code**: [llm_judge_evaluator.py](llm_judge_evaluator.py)
- **Test Dataset**: [test_dataset.py](test_dataset.py)
- **Run Script**: [run_langsmith_evaluation.py](run_langsmith_evaluation.py)
