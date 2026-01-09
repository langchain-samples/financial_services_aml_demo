"""Custom evaluators for KYC and AML agents."""

from typing import Dict, Any, Optional
from langsmith import evaluate, traceable
from langsmith.schemas import Example, Run

from agents.kyc_agent import KYCDecision
from agents.aml_agent import Alert


@traceable(name="kyc_identity_verification_evaluator")
def evaluate_kyc_identity_verification(run: Run, example: Example) -> Dict[str, Any]:
    """Evaluate KYC identity verification accuracy."""
    # Extract decision from run outputs
    decision_data = run.outputs.get("decision", {}) if run.outputs else {}
    
    if not decision_data:
        return {"score": 0, "reasoning": "No decision found in run outputs"}
    
    # Check if watchlist match was correctly identified
    watchlist_matched = decision_data.get("watchlist_result", {}).get("matched", False)
    decision = decision_data.get("decision", "")
    
    # Expected: If watchlist match, should be REJECT
    if watchlist_matched and decision == "REJECT":
        score = 1.0
        reasoning = "Correctly rejected watchlist match"
    elif watchlist_matched and decision != "REJECT":
        score = 0.0
        reasoning = "Failed to reject watchlist match"
    elif not watchlist_matched and decision in ["APPROVE", "MANUAL_REVIEW"]:
        score = 1.0
        reasoning = "Correctly processed non-watchlist customer"
    else:
        score = 0.5
        reasoning = "Uncertain evaluation"
    
    return {
        "score": score,
        "reasoning": reasoning,
        "watchlist_matched": watchlist_matched,
        "decision": decision,
    }


@traceable(name="kyc_risk_classification_evaluator")
def evaluate_kyc_risk_classification(run: Run, example: Example) -> Dict[str, Any]:
    """Evaluate KYC risk classification correctness."""
    decision_data = run.outputs.get("decision", {}) if run.outputs else {}
    
    if not decision_data:
        return {"score": 0, "reasoning": "No decision found in run outputs"}
    
    risk_assessment = decision_data.get("risk_assessment", {})
    risk_level = risk_assessment.get("risk_level", "")
    risk_score = risk_assessment.get("risk_score", 0)
    decision = decision_data.get("decision", "")
    
    # Evaluate risk classification logic
    score = 0.0
    reasoning_parts = []
    
    # Check if risk level aligns with risk score
    if risk_score >= 70 and risk_level == "HIGH":
        score += 0.33
        reasoning_parts.append("High risk correctly classified")
    elif 40 <= risk_score < 70 and risk_level == "MEDIUM":
        score += 0.33
        reasoning_parts.append("Medium risk correctly classified")
    elif risk_score < 40 and risk_level == "LOW":
        score += 0.33
        reasoning_parts.append("Low risk correctly classified")
    
    # Check if decision aligns with risk level
    if risk_level == "HIGH" and decision == "MANUAL_REVIEW":
        score += 0.33
        reasoning_parts.append("High risk correctly requires review")
    elif risk_level == "LOW" and decision == "APPROVE":
        score += 0.33
        reasoning_parts.append("Low risk correctly approved")
    
    # Check if factors are present
    factors = risk_assessment.get("factors", [])
    if factors:
        score += 0.34
        reasoning_parts.append("Risk factors identified")
    
    return {
        "score": min(score, 1.0),
        "reasoning": "; ".join(reasoning_parts) if reasoning_parts else "No reasoning provided",
        "risk_level": risk_level,
        "risk_score": risk_score,
        "decision": decision,
    }


@traceable(name="aml_detection_accuracy_evaluator")
def evaluate_aml_detection_accuracy(run: Run, example: Example) -> Dict[str, Any]:
    """Evaluate AML suspicious activity detection accuracy."""
    # Check if alert was generated
    alert_data = run.outputs.get("alert") if run.outputs else None
    
    # Get expected outcome from example (if available)
    expected_suspicious = example.outputs.get("should_alert", False) if example.outputs else None
    
    if alert_data is None:
        # No alert generated
        if expected_suspicious:
            score = 0.0
            reasoning = "Failed to detect suspicious activity"
        else:
            score = 1.0
            reasoning = "Correctly identified non-suspicious transaction"
    else:
        # Alert was generated
        if expected_suspicious:
            score = 1.0
            reasoning = "Correctly detected suspicious activity"
        else:
            # False positive - but check severity
            severity = alert_data.get("severity", "")
            if severity == "LOW":
                score = 0.7
                reasoning = "Low severity false positive"
            else:
                score = 0.3
                reasoning = "High severity false positive"
    
    return {
        "score": score,
        "reasoning": reasoning,
        "alert_generated": alert_data is not None,
        "expected_suspicious": expected_suspicious,
    }


@traceable(name="aml_alert_relevance_evaluator")
def evaluate_aml_alert_relevance(run: Run, example: Example) -> Dict[str, Any]:
    """Evaluate AML alert relevance and quality."""
    alert_data = run.outputs.get("alert") if run.outputs else None
    
    if not alert_data:
        return {
            "score": 0.0,
            "reasoning": "No alert generated",
        }
    
    severity = alert_data.get("severity", "")
    risk_score = alert_data.get("risk_score", 0)
    indicators = alert_data.get("indicators", [])
    justification = alert_data.get("justification", "")
    
    score = 0.0
    reasoning_parts = []
    
    # Check if severity aligns with risk score
    if risk_score >= 80 and severity == "CRITICAL":
        score += 0.25
        reasoning_parts.append("Critical severity appropriate")
    elif risk_score >= 60 and severity == "HIGH":
        score += 0.25
        reasoning_parts.append("High severity appropriate")
    elif risk_score >= 40 and severity == "MEDIUM":
        score += 0.25
        reasoning_parts.append("Medium severity appropriate")
    elif risk_score < 40 and severity == "LOW":
        score += 0.25
        reasoning_parts.append("Low severity appropriate")
    
    # Check if indicators are present
    if indicators:
        score += 0.25
        reasoning_parts.append(f"{len(indicators)} indicators identified")
    
    # Check if justification is provided
    if justification:
        score += 0.25
        reasoning_parts.append("Justification provided")
    
    # Check if recommended action is appropriate
    recommended_action = alert_data.get("recommended_action", "")
    if recommended_action:
        score += 0.25
        reasoning_parts.append("Action recommended")
    
    return {
        "score": min(score, 1.0),
        "reasoning": "; ".join(reasoning_parts) if reasoning_parts else "No reasoning provided",
        "severity": severity,
        "risk_score": risk_score,
        "indicator_count": len(indicators),
    }


@traceable(name="compliance_check_evaluator")
def evaluate_compliance_check(run: Run, example: Example) -> Dict[str, Any]:
    """Evaluate compliance check completeness."""
    decision_data = run.outputs.get("decision", {}) if run.outputs else {}
    
    if not decision_data:
        return {"score": 0, "reasoning": "No decision found"}
    
    # Check for required compliance elements
    score = 0.0
    reasoning_parts = []
    
    # Check if watchlist check was performed
    watchlist_result = decision_data.get("watchlist_result", {})
    if watchlist_result:
        score += 0.33
        reasoning_parts.append("Watchlist check performed")
    
    # Check if risk assessment was performed
    risk_assessment = decision_data.get("risk_assessment", {})
    if risk_assessment:
        score += 0.33
        reasoning_parts.append("Risk assessment performed")
    
    # Check if reasoning is provided
    reasoning = decision_data.get("reasoning", "")
    if reasoning:
        score += 0.34
        reasoning_parts.append("Decision reasoning provided")
    
    return {
        "score": min(score, 1.0),
        "reasoning": "; ".join(reasoning_parts) if reasoning_parts else "No compliance checks found",
    }


# Evaluation configuration for LangSmith
EVALUATORS = {
    "kyc_identity_verification": evaluate_kyc_identity_verification,
    "kyc_risk_classification": evaluate_kyc_risk_classification,
    "aml_detection_accuracy": evaluate_aml_detection_accuracy,
    "aml_alert_relevance": evaluate_aml_alert_relevance,
    "compliance_check": evaluate_compliance_check,
}
