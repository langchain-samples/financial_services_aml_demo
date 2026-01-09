"""KYC API routes."""

from fastapi import APIRouter, HTTPException
from langsmith import traceable

from app.models import KYCOnboardRequest, KYCOnboardResponse
from agents.kyc_agent import KYCAgent
from utils.langsmith_setup import get_kyc_project_name

router = APIRouter(prefix="/kyc", tags=["KYC"])

# Initialize KYC agent
kyc_agent = KYCAgent(project_name=get_kyc_project_name())


@router.post("/onboard", response_model=KYCOnboardResponse)
@traceable(name="kyc_onboard_endpoint", project_name="financial_services_deep_agent_demo")
async def onboard_customer(request: KYCOnboardRequest) -> KYCOnboardResponse:
    """Process customer onboarding through KYC workflow."""
    try:
        decision = kyc_agent.process_onboarding(
            customer_id=request.customer_id,
            documents=request.documents,
        )

        return KYCOnboardResponse(
            success=True,
            decision=decision,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"KYC processing failed: {str(e)}")
