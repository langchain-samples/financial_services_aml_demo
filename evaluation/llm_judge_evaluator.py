"""LangSmith LLM-as-a-Judge evaluator for AML transaction flagging.

This evaluator uses an LLM to evaluate whether the AML agent correctly
flagged transactions. It will appear in LangSmith's evaluators UI.
"""

from typing import Any, Dict, Optional
from langsmith.schemas import Example, Run
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


# Initialize the judge LLM
judge_llm = ChatOpenAI(model="gpt-4o", temperature=0)


# Evaluation prompt template
JUDGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert AML compliance evaluator. Your job is to evaluate whether an AML transaction monitoring system correctly flagged a transaction.

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

You MUST respond with a valid JSON object matching this schema:

{{
  "type": "object",
  "properties": {{
    "flag_correctness": {{
      "type": "number",
      "description": "Score 0.0-1.0 for whether agent correctly flagged or not flagged",
      "minimum": 0.0,
      "maximum": 1.0
    }},
    "severity_accuracy": {{
      "type": "number",
      "description": "Score 0.0-1.0 for whether severity level was appropriate",
      "minimum": 0.0,
      "maximum": 1.0
    }},
    "indicator_detection": {{
      "type": "number",
      "description": "Score 0.0-1.0 for whether expected risk indicators were detected",
      "minimum": 0.0,
      "maximum": 1.0
    }},
    "risk_score_accuracy": {{
      "type": "number",
      "description": "Score 0.0-1.0 for whether risk score was in expected range",
      "minimum": 0.0,
      "maximum": 1.0
    }},
    "overall_score": {{
      "type": "number",
      "description": "Weighted average: flag_correctness*0.4 + severity_accuracy*0.25 + indicator_detection*0.2 + risk_score_accuracy*0.15",
      "minimum": 0.0,
      "maximum": 1.0
    }},
    "reasoning": {{
      "type": "string",
      "description": "Brief explanation of scores"
    }},
    "critical_issues": {{
      "type": "array",
      "items": {{"type": "string"}},
      "description": "List of critical problems like false negatives or missed sanctions"
    }},
    "recommendations": {{
      "type": "array",
      "items": {{"type": "string"}},
      "description": "List of suggestions for improvement"
    }}
  }},
  "required": ["flag_correctness", "severity_accuracy", "indicator_detection", "risk_score_accuracy", "overall_score", "reasoning", "critical_issues", "recommendations"]
}}

Be strict but fair. Compliance is critical, so missed suspicious transactions are very serious.
Return ONLY the JSON object, no other text."""),
    ("user", """# Transaction Details
{transaction}

# Customer History
{customer_history}

# Agent Decision
Flagged: {agent_flagged}
{agent_details}

# Expected Decision
Should Flag: {expected_flag}
{expected_details}

Provide your evaluation as a JSON object.""")
])


def llm_judge_evaluator(run: Run, example: Example) -> Dict[str, Any]:
    """
    LLM-as-a-Judge evaluator for AML transaction flagging.

    This evaluator uses an LLM to assess the quality of the AML agent's
    flagging decision. It will appear in LangSmith's evaluation UI.

    Args:
        run: The LangSmith run containing the agent's output
        example: The test example with expected outputs

    Returns:
        Dictionary with evaluation score and feedback
    """
    # Extract inputs
    inputs = example.inputs
    transaction = inputs.get("transaction", {})
    customer_history = inputs.get("customer_history", [])

    # Extract expected outputs
    expected_should_flag = example.outputs.get("should_flag", False)
    expected_severity = example.outputs.get("expected_severity")
    expected_indicators = example.outputs.get("expected_indicators", [])
    expected_min_risk = example.outputs.get("min_risk_score", 0)
    expected_max_risk = example.outputs.get("max_risk_score", 100)

    # Extract agent outputs
    outputs = run.outputs or {}
    alert = outputs.get("alert")
    agent_flagged = alert is not None

    # Format transaction details
    transaction_str = f"""
Transaction ID: {transaction.get('transaction_id')}
Customer ID: {transaction.get('customer_id')}
Amount: ${transaction.get('amount'):,.2f} {transaction.get('currency', 'USD')}
Type: {transaction.get('transaction_type')}
Origin: {transaction.get('origin')}
Destination: {transaction.get('destination')}
Description: {transaction.get('description', 'N/A')}
"""

    # Format history
    if customer_history:
        history_str = f"{len(customer_history)} previous transactions:\n"
        for i, hist in enumerate(customer_history[:5], 1):  # Show first 5
            history_str += f"  {i}. ${hist.get('amount', 0):,.2f} {hist.get('transaction_type', 'N/A')}\n"
        if len(customer_history) > 5:
            history_str += f"  ... and {len(customer_history) - 5} more"
    else:
        history_str = "No previous transaction history"

    # Format agent decision
    if agent_flagged:
        agent_details = f"""
Severity: {alert.get('severity')}
Risk Score: {alert.get('risk_score')}/100
Indicators: {', '.join(alert.get('indicators', []))}
Recommended Action: {alert.get('recommended_action')}
Justification: {alert.get('justification', 'N/A')}
"""
    else:
        agent_details = "No alert generated - transaction was not flagged."

    # Format expected decision
    if expected_should_flag:
        expected_details = f"""
Expected Severity: {expected_severity}
Expected Indicators: {', '.join(expected_indicators)}
Expected Risk Score Range: {expected_min_risk}-{expected_max_risk}
"""
    else:
        expected_details = "Transaction should not be flagged (normal transaction)."

    # Call judge LLM
    try:
        chain = JUDGE_PROMPT | judge_llm
        response = chain.invoke({
            "transaction": transaction_str,
            "customer_history": history_str,
            "agent_flagged": "Yes" if agent_flagged else "No",
            "agent_details": agent_details,
            "expected_flag": "Yes" if expected_should_flag else "No",
            "expected_details": expected_details,
        })

        # Parse JSON response
        import json
        import re

        # Clean the response content
        content = response.content

        # Remove markdown code blocks if present
        if "```json" in content:
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*$', '', content)
        elif "```" in content:
            content = re.sub(r'```\s*', '', content)

        # Try to find JSON object in the response
        content = content.strip()

        # Try to parse
        evaluation = json.loads(content)

        # Format for LangSmith
        return {
            "key": "aml_flagging_accuracy",
            "score": evaluation.get("overall_score", 0.0),
            "comment": format_judge_feedback(evaluation),
            "metadata": {
                "component_scores": {
                    "flag_correctness": evaluation.get("flag_correctness", 0.0),
                    "severity_accuracy": evaluation.get("severity_accuracy", 0.0),
                    "indicator_detection": evaluation.get("indicator_detection", 0.0),
                    "risk_score_accuracy": evaluation.get("risk_score_accuracy", 0.0),
                },
                "critical_issues": evaluation.get("critical_issues", []),
                "recommendations": evaluation.get("recommendations", []),
            }
        }

    except Exception as e:
        # Fallback to rule-based evaluation if LLM fails
        print(f"LLM judge failed, using fallback: {e}")
        return fallback_evaluation(run, example)


def format_judge_feedback(evaluation: Dict[str, Any]) -> str:
    """Format the judge's evaluation into readable feedback."""
    lines = []

    # Overall score
    overall = evaluation.get("overall_score", 0.0)
    lines.append(f"Overall Score: {overall:.2%}\n")

    # Component scores
    lines.append("Component Scores:")
    lines.append(f"  Flag Correctness:    {evaluation.get('flag_correctness', 0):.2%}")
    lines.append(f"  Severity Accuracy:   {evaluation.get('severity_accuracy', 0):.2%}")
    lines.append(f"  Indicator Detection: {evaluation.get('indicator_detection', 0):.2%}")
    lines.append(f"  Risk Score Accuracy: {evaluation.get('risk_score_accuracy', 0):.2%}")
    lines.append("")

    # Reasoning
    reasoning = evaluation.get("reasoning", "")
    if reasoning:
        lines.append(f"Reasoning: {reasoning}\n")

    # Critical issues
    critical = evaluation.get("critical_issues", [])
    if critical:
        lines.append("⚠️  Critical Issues:")
        for issue in critical:
            lines.append(f"  - {issue}")
        lines.append("")

    # Recommendations
    recommendations = evaluation.get("recommendations", [])
    if recommendations:
        lines.append("💡 Recommendations:")
        for rec in recommendations:
            lines.append(f"  - {rec}")

    return "\n".join(lines)


def fallback_evaluation(run: Run, example: Example) -> Dict[str, Any]:
    """
    Fallback rule-based evaluation if LLM judge fails.
    Uses the original logic from aml_evaluator.py.
    """
    from evaluation.aml_evaluator import evaluate_transaction_flagging

    result = evaluate_transaction_flagging(run, example)

    # Reformat for consistency
    return {
        "key": "aml_flagging_accuracy",
        "score": result["score"],
        "comment": f"(Fallback evaluation)\n\n{result['comment']}",
        "metadata": {
            "component_scores": result.get("scores", {}),
            "fallback_used": True,
        }
    }


# Alternative: Simpler LLM judge using LangSmith's built-in patterns
def create_llm_judge_simple():
    """
    Creates a simple LLM judge evaluator using LangSmith's patterns.

    This is an alternative approach that's simpler but less customizable.
    """
    from langsmith.evaluation import LangChainStringEvaluator

    prompt = """You are evaluating an AML transaction flagging system.

Transaction: {input}
Agent Output: {prediction}
Expected: {reference}

Did the agent correctly flag this transaction? Consider:
1. Was the flag decision correct?
2. Was the severity appropriate?
3. Were the right indicators identified?

Score from 0-1, where 1 is perfect and 0 is completely wrong.
Explain your reasoning briefly.

Score:"""

    return LangChainStringEvaluator(
        name="aml_simple_judge",
        prompt=prompt,
        model="gpt-4o",
        temperature=0,
    )


# For LangSmith evaluate() function
def aml_llm_judge(run: Run, example: Example) -> Dict[str, Any]:
    """
    Main evaluator function to be used with LangSmith evaluate().

    Usage:
        from langsmith.evaluation import evaluate
        from evaluation.llm_judge_evaluator import aml_llm_judge

        evaluate(
            predict_function,
            data="aml-transaction-flagging-tests",
            evaluators=[aml_llm_judge],
        )
    """
    return llm_judge_evaluator(run, example)
