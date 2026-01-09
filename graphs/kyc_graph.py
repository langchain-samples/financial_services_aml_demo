"""KYC onboarding graph using LangGraph."""

from typing import Annotated, Literal, TypedDict, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langsmith import traceable

from agents.prompts import (
    KYC_DOCUMENT_EXTRACTION_PROMPT,
    KYC_RISK_ASSESSMENT_PROMPT,
)
from agents.kyc_agent import (
    CustomerDocument,
    WatchlistMatch,
    RiskAssessment,
    KYCDecision,
)


class KYCState(TypedDict):
    """State for KYC onboarding workflow."""
    customer_id: str
    documents: dict
    extracted_info: Optional[CustomerDocument]
    watchlist_result: Optional[WatchlistMatch]
    risk_assessment: Optional[RiskAssessment]
    decision: Optional[KYCDecision]
    error: Optional[str]


class KYCAgentGraph:
    """KYC agent as a LangGraph workflow."""

    def __init__(self, llm_model: str = "gpt-4", temperature: float = 0.0):
        """Initialize KYC graph."""
        self.llm = ChatOpenAI(model=llm_model, temperature=temperature)
        self.graph = self._build_graph()

    @traceable(name="extract_document_info")
    def extract_document_info(self, state: KYCState) -> KYCState:
        """Extract customer information from documents."""
        documents = state["documents"]
        document_text = "\n".join([f"{k}: {v}" for k, v in documents.items()])

        prompt = ChatPromptTemplate.from_messages([
            ("system", KYC_DOCUMENT_EXTRACTION_PROMPT),
            ("human", "Extract information from these documents:\n\n{document_text}"),
        ])

        chain = prompt | self.llm
        response = chain.invoke({"document_text": document_text})

        # Parse response (in production, use structured output)
        extracted_info = CustomerDocument(
            full_name=documents.get("name", "Unknown"),
            date_of_birth=documents.get("dob", "Unknown"),
            address=documents.get("address", "Unknown"),
            nationality=documents.get("nationality", "Unknown"),
            id_document_type=documents.get("id_type", "Passport"),
            id_document_number=documents.get("id_number", "Unknown"),
            occupation=documents.get("occupation", "Unknown"),
            source_of_funds=documents.get("source_of_funds", "Unknown"),
        )

        return {**state, "extracted_info": extracted_info}

    @traceable(name="check_watchlist")
    def check_watchlist(self, state: KYCState) -> KYCState:
        """Check customer against watchlists and sanctions lists."""
        customer_info = state["extracted_info"]
        if not customer_info:
            return {**state, "error": "No customer info extracted"}

        # Mock watchlist check
        full_name = customer_info.full_name.lower()
        high_risk_names = ["john doe", "jane smith", "test suspicious"]
        matched = any(risk_name in full_name for risk_name in high_risk_names)

        watchlist_result = WatchlistMatch(
            matched=matched,
            match_type="SANCTIONS_LIST" if matched else None,
            match_details=f"Name matches entry in sanctions list" if matched else None,
        )

        return {**state, "watchlist_result": watchlist_result}

    @traceable(name="assess_risk")
    def assess_risk(self, state: KYCState) -> KYCState:
        """Assess customer risk level."""
        customer_info = state["extracted_info"]
        watchlist_match = state["watchlist_result"]

        if not customer_info or not watchlist_match:
            return {**state, "error": "Missing required information for risk assessment"}

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

        # Calculate risk score
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

        risk_assessment = RiskAssessment(
            risk_score=min(risk_score, 100),
            risk_level=risk_level,
            justification=response.content if hasattr(response, 'content') else f"Risk score: {risk_score}",
            factors=risk_factors,
        )

        return {**state, "risk_assessment": risk_assessment}

    @traceable(name="make_decision")
    def make_decision(self, state: KYCState) -> KYCState:
        """Make final KYC decision."""
        customer_info = state["extracted_info"]
        watchlist_match = state["watchlist_result"]
        risk_assessment = state["risk_assessment"]
        customer_id = state["customer_id"]

        if not all([customer_info, watchlist_match, risk_assessment]):
            return {**state, "error": "Missing required information for decision"}

        # Decision logic
        if watchlist_match.matched:
            decision_value = "REJECT"
            reasoning = "Customer matches watchlist/sanctions list"
        elif risk_assessment.risk_level == "HIGH":
            decision_value = "MANUAL_REVIEW"
            reasoning = f"High risk score ({risk_assessment.risk_score}) requires manual review"
        elif risk_assessment.risk_level == "MEDIUM":
            decision_value = "MANUAL_REVIEW"
            reasoning = f"Medium risk score ({risk_assessment.risk_score}) requires review"
        else:
            decision_value = "APPROVE"
            reasoning = f"Low risk score ({risk_assessment.risk_score}) - approved"

        decision = KYCDecision(
            decision=decision_value,
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

        return {**state, "decision": decision}

    def _build_graph(self):
        """Build the KYC workflow graph."""
        workflow = StateGraph(KYCState)

        # Add nodes
        workflow.add_node("extract_documents", self.extract_document_info)
        workflow.add_node("check_watchlist", self.check_watchlist)
        workflow.add_node("assess_risk", self.assess_risk)
        workflow.add_node("make_decision", self.make_decision)

        # Define edges
        workflow.set_entry_point("extract_documents")
        workflow.add_edge("extract_documents", "check_watchlist")
        workflow.add_edge("check_watchlist", "assess_risk")
        workflow.add_edge("assess_risk", "make_decision")
        workflow.add_edge("make_decision", END)

        return workflow.compile()


# Create graph instance for LangGraph Studio
graph = KYCAgentGraph().graph
