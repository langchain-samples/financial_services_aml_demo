# LangSmith Insights

[Insights](https://docs.langchain.com/langsmith/insights) clusters traces into
categories and subcategories so you can see how the agents are used and where
they fail, without reviewing traces by hand. Requires a Plus or Enterprise plan
and an Insights model configuration in the workspace.

Engine continuously finds and fixes *issues*. Insights answers open-ended
questions like *"what kinds of transactions are we alerting on, and which ones
do analysts overturn?"*

## Saved report configs (CLI)

Each config is scoped to one agent through the `agent` trace metadata set in
`utils/trace_context.py`.

| Config | Agent | Schedule |
|---|---|---|
| [`aml_alert_quality.json`](aml_alert_quality.json) | AML transaction monitoring | Mondays 09:00 UTC, last 7 days |
| [`kyc_onboarding_outcomes.json`](kyc_onboarding_outcomes.json) | KYC onboarding | Mondays 09:00 UTC, last 7 days |
| [`compliance_assistant_usage.json`](compliance_assistant_usage.json) | Compliance summarization assistant | Daily 08:00 UTC, last 24 hours |

Requires [LangSmith CLI](https://docs.langchain.com/langsmith/langsmith-cli) v0.2.60 or later:

```bash
brew install langchain-ai/tap/langsmith-cli   # or: curl -fsSL https://cli.langsmith.com/install.sh | sh
langsmith auth login                          # or export LANGSMITH_API_KEY

# Save the config, start its schedule, and run the first report
langsmith insights create --project financial_services_deep_agent_demo \
  --config insights/aml_alert_quality.json --wait

# Inspect results
langsmith insights list --project financial_services_deep_agent_demo --limit 5
langsmith insights get <insight-id> --project financial_services_deep_agent_demo

# Re-run on demand, or change a saved config
langsmith insights config list --project financial_services_deep_agent_demo
langsmith insights run <config-id> --project financial_services_deep_agent_demo --wait
langsmith insights config update <config-id> --project financial_services_deep_agent_demo \
  --config insights/aml_alert_quality.json
```

To add per-trace **attributes** (for example a boolean `missed_sanctions_hit`
with `filter_by`), categories, or a custom sample size, open the saved config in
the UI: **Tracing Projects → financial_services_deep_agent_demo → Insights**.

## Analyst decisions (Python SDK)

Analyst approve/reject/escalate decisions live in the SQLite review database,
not in LangSmith. `generate_review_insights.py` uploads them with
`Client.generate_insights()` and clusters them, which shows which alert types
analysts overturn as false positives.

```bash
python -m insights.generate_review_insights --limit 500 --wait
python -m insights.generate_review_insights --include-pending --model anthropic
```

## Cost and runtime

Reports take up to 30 minutes. 1,000 traces cost roughly $1–2 with OpenAI models
or $3–4 with Anthropic models.
