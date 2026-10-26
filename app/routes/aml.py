"""AML API routes."""

from fastapi import APIRouter, HTTPException
from langsmith import traceable
from utils.trace_context import get_trace_context

from app.models import AMLAnalyzeRequest, AMLAnalyzeResponse
from agents.aml_agent import AMLAgent
from utils.langsmith_setup import get_aml_project_name
from app.routes.reviews import add_pending_review

router = APIRouter(prefix="/aml", tags=["AML"])

# Initialize AML agent
aml_agent = AMLAgent(project_name=get_aml_project_name())


@router.post("/analyze", response_model=AMLAnalyzeResponse)
@traceable(name="aml_analyze_endpoint", project_name="financial_services_deep_agent_demo", metadata=get_trace_context("aml_transaction_monitoring"))
async def analyze_transaction(request: AMLAnalyzeRequest) -> AMLAnalyzeResponse:
    """Analyze transaction for suspicious activity."""
    try:
        # Analyze transaction
        alert = aml_agent.analyze_transaction(request.transaction)

        # If alert is generated (anomalies detected), add to pending reviews
        if alert:
            # Determine severity from alert
            severity_map = {
                "CRITICAL": "HIGH",
                "HIGH": "HIGH",
                "MEDIUM": "MEDIUM",
                "LOW": "LOW",
            }
            severity = severity_map.get(alert.severity, "MEDIUM")
            
            # Get anomaly details from the alert
            anomalies = {
                "anomalies_detected": True,
                "anomaly_types": alert.indicators or [],
                "severity": severity,
                "details": alert.justification or f"Risk score: {alert.risk_score}",
            }
            add_pending_review(request.transaction, anomalies, alert)

        return AMLAnalyzeResponse(
            success=True,
            alert=alert,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AML analysis failed: {str(e)}")
