# LangSmith Engine

[LangSmith Engine](https://docs.langchain.com/langsmith/engine-overview) is an agent
that reads this project's production traces, groups recurring failures into
**issues**, diagnoses their root cause against the code, and proposes fixes as
draft pull requests. It also turns failing traces into dataset examples for
offline evals, and reopens issues that come back.

For this demo, Engine catches things like:

- The AML agent under-rating sanctions or structuring alerts, picked up from online evaluator scores
- Severity / risk score mismatches in `generate_alert`
- Summarization assistant tool-call failures and latency spikes
- Regressions after a prompt change, linked to the commit through `revision_id`

## What this repo already does for Engine

| Engine input | Where it comes from |
|---|---|
| `revision_id` trace metadata | `utils/trace_context.py`, attached to every graph via `.with_config()`. Uses `REVISION_ID` if set, otherwise the git SHA. |
| `agent` trace metadata | Same place. Use it to scope Engine to a single workflow. |
| Feedback signals (high priority for Engine) | Online evaluation (`evaluation/online_evaluation.py`), annotation queues (`evaluation/offline_evaluation_with_queue.py`), and SDK feedback |
| Code for root-cause diagnosis and PRs | This repo (LangGraph, supported for code fixes) |
| Agent context | [`AGENT_OVERVIEW.md`](AGENT_OVERVIEW.md) |

## Setup

1. **Enable for the org** (Org Admin): **Settings → Engine →** turn on **Enable Engine** and accept the AI features terms.
2. **Generate traffic** so there are traces to analyze:
   ```bash
   uvicorn app.main:app --reload
   curl -X POST http://localhost:8000/load/transactions -H "Content-Type: application/json" \
     -d '{"count": 50, "suspicious_ratio": 0.3}'
   curl -X POST http://localhost:8000/load/customers -H "Content-Type: application/json" \
     -d '{"count": 25}'
   ```
3. **Turn on Engine for the project:** select **Engine** in the sidebar, then choose `financial_services_deep_agent_demo` (or **+ Set up another project**).
   - *Connect a repository* (recommended): install the GitHub App for this repo. Engine gets read access and can open **draft** PRs. It never merges.
   - *Preferences*: pick **Tool Call Failures** and **Latency**, and add a custom concern such as *"Missed sanctions or structuring detections are critical."*
   - *Analysis level*: **Standard**. The dialog shows the estimated monthly LSU cost.
   - *Scope* (optional): metadata `agent` = `aml_transaction_monitoring` to focus on the AML agent.
4. Click **Start Analyzing**. The first scan can take up to 20 minutes.
5. When the generated **Agent Overview** opens, merge in [`AGENT_OVERVIEW.md`](AGENT_OVERVIEW.md) and click **Accept & Continue**.
6. Optional: under **Configure Engine**, set Slack or webhook notifications and a **Spend limit**.

## Demo flow

1. Open the project's **Engine** tab and show the issues, ranked by severity, each with supporting traces.
2. Open a high-severity issue to show the diagnosis, the linked traces, and the `revision_id` where it started.
3. Show the proposed draft PR, for example a prompt fix in `agents/prompts.py`.
4. Add the generated dataset examples to the AML eval dataset and re-run `python evaluation/run_langsmith_evaluation.py` to confirm the fix.
5. Close or reprioritize an issue to show how Engine learns your preferences, which it records in the Agent Overview's **User Preferences** section.

## Setting `revision_id` in deployments

Where there's no `.git` directory (Docker images, LangGraph Platform), set it explicitly:

```env
REVISION_ID=<git sha or release tag>
```

## Cost

Engine bills in LangChain Standard Units (LSUs, $1 each), based on traces analyzed, LLM volume, and repo size.
Recurring scans use LSUs even when they find nothing new. Org Admins can cap spend under **Settings → Engine**
(the default limit is 750 LSU/month).
