"""AML Review management API routes."""

from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException
from langsmith import traceable
from pydantic import BaseModel
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from agents.aml_agent import Transaction, Alert

router = APIRouter(prefix="/aml/reviews", tags=["AML Reviews"])

# In-memory store for pending reviews (in production, use a database)
pending_reviews: Dict[str, Dict] = {}


class ReviewResponse(BaseModel):
    """Response model for review operations."""
    success: bool
    message: str
    review: Optional[Dict] = None


class ReviewsListResponse(BaseModel):
    """Response model for listing reviews."""
    success: bool
    reviews: List[Dict]
    count: int


@router.get("/pending", response_model=ReviewsListResponse)
@traceable(name="get_pending_reviews", project_name="financial_services_deep_agent_demo")
async def get_pending_reviews() -> ReviewsListResponse:
    """Get all pending AML transaction reviews."""
    # Filter pending reviews
    pending = [
        review for review in pending_reviews.values()
        if review.get("status") == "pending"
    ]
    
    # Sort by timestamp (newest first)
    pending.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return ReviewsListResponse(
        success=True,
        reviews=pending,
        count=len(pending),
    )


@router.get("/{transaction_id}", response_model=ReviewResponse)
@traceable(name="get_review", project_name="financial_services_deep_agent_demo")
async def get_review(transaction_id: str) -> ReviewResponse:
    """Get a specific review by transaction ID."""
    if transaction_id not in pending_reviews:
        raise HTTPException(status_code=404, detail="Review not found")
    
    return ReviewResponse(
        success=True,
        message="Review retrieved",
        review=pending_reviews[transaction_id],
    )


@router.post("/{transaction_id}/approve", response_model=ReviewResponse)
@traceable(name="approve_review", project_name="financial_services_deep_agent_demo", run_type="chain")
async def approve_review(transaction_id: str) -> ReviewResponse:
    """Approve a pending AML transaction review with deep tracing."""
    if transaction_id not in pending_reviews:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review = pending_reviews[transaction_id]
    if review.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Review is not pending")
    
    # Step 1: Validate review eligibility (nested trace)
    validation_result = _validate_review_eligibility(review)
    
    # Step 2: Generate review justification using LLM (nested trace)
    justification = _generate_review_justification(review, "APPROVE")
    
    # Step 3: Perform compliance check (nested trace)
    compliance_result = _perform_compliance_check(review, "APPROVE")
    
    # Step 4: Update review status
    review["status"] = "approved"
    review["reviewed_at"] = datetime.now().isoformat()
    review["review_action"] = "APPROVE"
    review["justification"] = justification
    review["compliance_check"] = compliance_result
    
    # Step 5: Log review action (nested trace)
    _log_review_action(review, "APPROVE")
    
    # If this is a LangGraph thread, resume with APPROVE
    thread_id = review.get("thread_id")
    if thread_id:
        try:
            from langgraph.checkpoint.memory import MemorySaver
            # Resume the graph with APPROVE decision
            # Note: This would need to be integrated with LangGraph SDK
            pass
        except Exception as e:
            print(f"Error resuming thread: {e}")
    
    return ReviewResponse(
        success=True,
        message="Review approved",
        review=review,
    )


@traceable(name="validate_review_eligibility", project_name="financial_services_deep_agent_demo", run_type="tool")
def _validate_review_eligibility(review: Dict) -> Dict:
    """Validate that a review is eligible for processing."""
    checks = {
        "has_transaction_id": bool(review.get("transaction_id")),
        "has_customer_id": bool(review.get("customer_id")),
        "has_anomalies": bool(review.get("anomalies", {}).get("anomalies_detected")),
        "is_pending": review.get("status") == "pending",
        "has_timestamp": bool(review.get("timestamp")),
    }
    
    all_valid = all(checks.values())
    
    return {
        "valid": all_valid,
        "checks": checks,
        "message": "Review is eligible" if all_valid else "Review validation failed",
    }


@traceable(name="generate_review_justification", project_name="financial_services_deep_agent_demo", run_type="llm")
def _generate_review_justification(review: Dict, action: str) -> str:
    """Generate a justification for the review decision using LLM."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a compliance officer reviewing an AML transaction alert.
Generate a concise, professional justification for your decision.
Focus on the key risk factors and why this decision is appropriate."""),
        ("human", """Transaction Details:
- Transaction ID: {transaction_id}
- Customer ID: {customer_id}
- Amount: {amount} {currency}
- Origin: {origin}
- Destination: {destination}
- Anomaly Severity: {severity}
- Anomaly Types: {anomaly_types}
- Risk Score: {risk_score}

Decision: {action}

Generate a brief justification (2-3 sentences) explaining why this {action} decision is appropriate for this transaction.""")
    ])
    
    chain = prompt | llm
    
    response = chain.invoke({
        "transaction_id": review.get("transaction_id", "N/A"),
        "customer_id": review.get("customer_id", "N/A"),
        "amount": review.get("amount", 0),
        "currency": review.get("currency", "USD"),
        "origin": review.get("origin", "N/A"),
        "destination": review.get("destination", "N/A"),
        "severity": review.get("anomalies", {}).get("severity", "UNKNOWN"),
        "anomaly_types": ", ".join(review.get("anomalies", {}).get("anomaly_types", [])),
        "risk_score": review.get("risk_score", "N/A"),
        "action": action,
    })
    
    return response.content


@traceable(name="perform_compliance_check", project_name="financial_services_deep_agent_demo", run_type="tool")
def _perform_compliance_check(review: Dict, action: str) -> Dict:
    """Perform compliance checks before finalizing review decision."""
    checks = {
        "regulatory_compliance": True,  # In production, this would check actual regulations
        "internal_policy_compliance": True,
        "audit_trail_created": True,
        "notification_required": review.get("anomalies", {}).get("severity") == "HIGH",
    }
    
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "timestamp": datetime.now().isoformat(),
    }


@traceable(name="log_review_action", project_name="financial_services_deep_agent_demo", run_type="tool")
def _log_review_action(review: Dict, action: str) -> Dict:
    """Log the review action for audit purposes."""
    log_entry = {
        "transaction_id": review.get("transaction_id"),
        "customer_id": review.get("customer_id"),
        "action": action,
        "timestamp": datetime.now().isoformat(),
        "reviewer": "system",  # In production, this would be the actual reviewer
        "risk_score": review.get("risk_score"),
        "severity": review.get("anomalies", {}).get("severity"),
    }
    
    # In production, this would write to a database or logging service
    print(f"[AUDIT LOG] Review action: {log_entry}")
    
    return {"logged": True, "log_entry": log_entry}


@router.post("/{transaction_id}/reject", response_model=ReviewResponse)
@traceable(name="reject_review", project_name="financial_services_deep_agent_demo", run_type="chain")
async def reject_review(transaction_id: str) -> ReviewResponse:
    """Reject a pending AML transaction review with deep tracing."""
    if transaction_id not in pending_reviews:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review = pending_reviews[transaction_id]
    if review.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Review is not pending")
    
    # Step 1: Validate review eligibility (nested trace)
    validation_result = _validate_review_eligibility(review)
    
    # Step 2: Generate review justification using LLM (nested trace)
    justification = _generate_review_justification(review, "REJECT")
    
    # Step 3: Perform compliance check (nested trace)
    compliance_result = _perform_compliance_check(review, "REJECT")
    
    # Step 4: Update review status
    review["status"] = "rejected"
    review["reviewed_at"] = datetime.now().isoformat()
    review["review_action"] = "REJECT"
    review["justification"] = justification
    review["compliance_check"] = compliance_result
    
    # Step 5: Log review action (nested trace)
    _log_review_action(review, "REJECT")
    
    # If this is a LangGraph thread, resume with REJECT
    thread_id = review.get("thread_id")
    if thread_id:
        try:
            # Resume the graph with REJECT decision
            pass
        except Exception as e:
            print(f"Error resuming thread: {e}")
    
    return ReviewResponse(
        success=True,
        message="Review rejected",
        review=review,
    )


@router.post("/{transaction_id}/escalate", response_model=ReviewResponse)
@traceable(name="escalate_review", project_name="financial_services_deep_agent_demo", run_type="chain")
async def escalate_review(transaction_id: str) -> ReviewResponse:
    """Escalate a pending AML transaction review with deep tracing."""
    if transaction_id not in pending_reviews:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review = pending_reviews[transaction_id]
    if review.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Review is not pending")
    
    # Step 1: Validate review eligibility (nested trace)
    validation_result = _validate_review_eligibility(review)
    
    # Step 2: Generate escalation rationale using LLM (nested trace)
    justification = _generate_review_justification(review, "ESCALATE")
    
    # Step 3: Perform compliance check (nested trace)
    compliance_result = _perform_compliance_check(review, "ESCALATE")
    
    # Step 4: Determine escalation priority (nested trace with LLM)
    escalation_priority = _determine_escalation_priority(review)
    
    # Step 5: Update review status
    review["status"] = "escalated"
    review["reviewed_at"] = datetime.now().isoformat()
    review["review_action"] = "ESCALATE"
    review["justification"] = justification
    review["compliance_check"] = compliance_result
    review["escalation_priority"] = escalation_priority
    
    # Step 6: Log review action (nested trace)
    _log_review_action(review, "ESCALATE")
    
    # If this is a LangGraph thread, resume with ESCALATE
    thread_id = review.get("thread_id")
    if thread_id:
        try:
            # Resume the graph with ESCALATE decision
            pass
        except Exception as e:
            print(f"Error resuming thread: {e}")
    
    return ReviewResponse(
        success=True,
        message="Review escalated",
        review=review,
    )


@traceable(name="determine_escalation_priority", project_name="financial_services_deep_agent_demo", run_type="llm")
def _determine_escalation_priority(review: Dict) -> Dict:
    """Determine the priority level for escalation using LLM."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a compliance officer determining escalation priority for an AML transaction review.
Return ONLY a JSON object with "priority" (LOW, MEDIUM, HIGH, CRITICAL) and "reason" (brief explanation)."""),
        ("human", """Transaction Details:
- Amount: {amount} {currency}
- Severity: {severity}
- Risk Score: {risk_score}
- Anomaly Types: {anomaly_types}
- Destination: {destination}

Determine the escalation priority and provide a brief reason.""")
    ])
    
    chain = prompt | llm
    
    response = chain.invoke({
        "amount": review.get("amount", 0),
        "currency": review.get("currency", "USD"),
        "severity": review.get("anomalies", {}).get("severity", "UNKNOWN"),
        "risk_score": review.get("risk_score", 0),
        "anomaly_types": ", ".join(review.get("anomalies", {}).get("anomaly_types", [])),
        "destination": review.get("destination", "N/A"),
    })
    
    import json
    try:
        result = json.loads(response.content)
    except:
        result = {"priority": "MEDIUM", "reason": "Standard escalation"}
    
    return result


def add_pending_review(transaction: Transaction, anomalies: Dict, alert: Optional[Alert] = None, thread_id: Optional[str] = None):
    """Add a review to the pending reviews store."""
    review = {
        "transaction_id": transaction.transaction_id,
        "customer_id": transaction.customer_id,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "origin": transaction.origin,
        "destination": transaction.destination,
        "transaction_type": transaction.transaction_type,
        "timestamp": transaction.timestamp.isoformat() if isinstance(transaction.timestamp, datetime) else transaction.timestamp,
        "description": transaction.description,
        "anomalies": {
            "anomalies_detected": anomalies.get("anomalies_detected", False),
            "anomaly_types": anomalies.get("anomaly_types", []),
            "severity": anomalies.get("severity", "LOW"),
            "details": anomalies.get("details", ""),
        },
        "risk_score": alert.risk_score if alert else None,
        "alert_id": alert.alert_id if alert else None,
        "status": "pending",
        "thread_id": thread_id,
        "created_at": datetime.now().isoformat(),
    }
    
    pending_reviews[transaction.transaction_id] = review
    return review
