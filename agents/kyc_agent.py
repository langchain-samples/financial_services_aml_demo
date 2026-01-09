"""KYC (Know Your Customer) onboarding agent."""

from typing import Dict, List, Optional, Literal
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langsmith import traceable
from pydantic import BaseModel, Field

from .prompts import (
    KYC_SYSTEM_PROMPT,
    KYC_DOCUMENT_EXTRACTION_PROMPT,
    KYC_RISK_ASSESSMENT_PROMPT,
)


class CustomerDocument(BaseModel):
    """Customer document information."""
    full_name: str
    date_of_birth: str
    address: str
    nationality: str
    id_document_type: str
    id_document_number: str
    occupation: str
    source_of_funds: str


class WatchlistMatch(BaseModel):
    """Watchlist match result."""
    matched: bool
    match_type: Optional[str] = None
    match_details: Optional[str] = None


class RiskAssessment(BaseModel):
    """Risk assessment result."""
    risk_score: int = Field(ge=0, le=100)
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    justification: str
    factors: List[str]


class KYCDecision(BaseModel):
    """KYC decision result."""
    decision: Literal["APPROVE", "REJECT", "MANUAL_REVIEW"]
    customer_id: str
    extracted_info: CustomerDocument
    watchlist_result: WatchlistMatch
    risk_assessment: RiskAssessment
    reasoning: str
    metadata: Dict = Field(default_factory=dict)


class KYCAgent:
    """KYC onboarding agent with document processing and risk assessment."""

    def __init__(
        self,
        llm_model: str = "gpt-4",
        temperature: float = 0.0,
        project_name: str = "financial_services_deep_agent_demo",
    ):
        """Initialize KYC agent."""
        self.llm = ChatOpenAI(model=llm_model, temperature=temperature)
        self.project_name = project_name

    @traceable(name="extract_document_info", project_name="financial_services_deep_agent_demo")
    def extract_document_info(self, documents: Dict[str, str]) -> CustomerDocument:
        """Extract customer information from documents."""
        document_text = "\n".join([f"{k}: {v}" for k, v in documents.items()])

        prompt = ChatPromptTemplate.from_messages([
            ("system", KYC_DOCUMENT_EXTRACTION_PROMPT),
            ("human", "Extract information from these documents:\n\n{document_text}"),
        ])

        chain = prompt | self.llm
        response = chain.invoke({"document_text": document_text})

        # Parse response (in production, use structured output)
        # For demo purposes, we'll create a mock extraction
        return CustomerDocument(
            full_name=documents.get("name", "Unknown"),
            date_of_birth=documents.get("dob", "Unknown"),
            address=documents.get("address", "Unknown"),
            nationality=documents.get("nationality", "Unknown"),
            id_document_type=documents.get("id_type", "Passport"),
            id_document_number=documents.get("id_number", "Unknown"),
            occupation=documents.get("occupation", "Unknown"),
            source_of_funds=documents.get("source_of_funds", "Unknown"),
        )

    @traceable(name="check_watchlist", project_name="financial_services_deep_agent_demo")
    def check_watchlist(self, customer_info: CustomerDocument) -> WatchlistMatch:
        """Check customer against watchlists and sanctions lists."""
        # Mock watchlist check (in production, integrate with real watchlist service)
        full_name = customer_info.full_name.lower()
        
        # Simulate watchlist matches for demo
        high_risk_names = ["john doe", "jane smith", "test suspicious"]
        matched = any(risk_name in full_name for risk_name in high_risk_names)
        
        if matched:
            return WatchlistMatch(
                matched=True,
                match_type="SANCTIONS_LIST",
                match_details=f"Name matches entry in sanctions list",
            )
        
        return WatchlistMatch(matched=False)

    @traceable(name="assess_risk", project_name="financial_services_deep_agent_demo")
    def assess_risk(self, customer_info: CustomerDocument, watchlist_match: WatchlistMatch) -> RiskAssessment:
        """Assess customer risk level."""
        # Build risk assessment prompt
        customer_summary = f"""
        Name: {customer_info.full_name}
        Nationality: {customer_info.nationality}
        Occupation: {customer_info.occupation}
        Source of Funds: {customer_info.source_of_funds}
        Watchlist Match: {watchlist_match.matched}
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", KYC_RISK_ASSESSMENT_PROMPT),
            ("human", "Assess risk for this customer:\n\n{customer_summary}"),
        ])

        chain = prompt | self.llm
        response = chain.invoke({"customer_summary": customer_summary})

        # Parse risk assessment (in production, use structured output)
        # For demo, calculate based on simple rules
        risk_score = 0
        risk_factors = []

        if watchlist_match.matched:
            risk_score += 50
            risk_factors.append("Watchlist match detected")

        high_risk_countries = ["iran", "north korea", "syria", "cuba"]
        if customer_info.nationality.lower() in high_risk_countries:
            risk_score += 30
            risk_factors.append("High-risk jurisdiction")

        if "cash" in customer_info.source_of_funds.lower():
            risk_score += 20
            risk_factors.append("Cash-based source of funds")

        if risk_score >= 70:
            risk_level = "HIGH"
        elif risk_score >= 40:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return RiskAssessment(
            risk_score=min(risk_score, 100),
            risk_level=risk_level,
            justification=response.content if hasattr(response, 'content') else f"Risk score: {risk_score}",
            factors=risk_factors,
        )

    @traceable(name="make_kyc_decision", project_name="financial_services_deep_agent_demo")
    def make_decision(
        self,
        customer_info: CustomerDocument,
        watchlist_match: WatchlistMatch,
        risk_assessment: RiskAssessment,
        customer_id: str,
    ) -> KYCDecision:
        """Make final KYC decision."""
        # Decision logic
        if watchlist_match.matched:
            decision = "REJECT"
            reasoning = "Customer matches watchlist/sanctions list"
        elif risk_assessment.risk_level == "HIGH":
            decision = "MANUAL_REVIEW"
            reasoning = f"High risk score ({risk_assessment.risk_score}) requires manual review"
        elif risk_assessment.risk_level == "MEDIUM":
            decision = "MANUAL_REVIEW"
            reasoning = f"Medium risk score ({risk_assessment.risk_score}) requires review"
        else:
            decision = "APPROVE"
            reasoning = f"Low risk score ({risk_assessment.risk_score}) - approved"

        return KYCDecision(
            decision=decision,
            customer_id=customer_id,
            extracted_info=customer_info,
            watchlist_result=watchlist_match,
            risk_assessment=risk_assessment,
            reasoning=reasoning,
            metadata={
                "agent_version": "1.0",
                "processing_time": "mock",
            },
        )

    @traceable(name="process_kyc_onboarding", project_name="financial_services_deep_agent_demo")
    def process_onboarding(self, customer_id: str, documents: Dict[str, str]) -> KYCDecision:
        """Process complete KYC onboarding workflow."""
        # Step 1: Extract document information
        customer_info = self.extract_document_info(documents)

        # Step 2: Check watchlists
        watchlist_match = self.check_watchlist(customer_info)

        # Step 3: Assess risk
        risk_assessment = self.assess_risk(customer_info, watchlist_match)

        # Step 4: Make decision
        decision = self.make_decision(customer_info, watchlist_match, risk_assessment, customer_id)

        return decision
