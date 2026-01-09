"""AML Review management API routes."""

from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException
from langsmith import traceable
from pydantic import BaseModel
from datetime import datetime

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
@traceable(name="approve_review", project_name="financial_services_deep_agent_demo")
async def approve_review(transaction_id: str) -> ReviewResponse:
    """Approve a pending AML transaction review."""
    if transaction_id not in pending_reviews:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review = pending_reviews[transaction_id]
    if review.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Review is not pending")
    
    # Update review status
    review["status"] = "approved"
    review["reviewed_at"] = datetime.now().isoformat()
    review["review_action"] = "APPROVE"
    
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


@router.post("/{transaction_id}/reject", response_model=ReviewResponse)
@traceable(name="reject_review", project_name="financial_services_deep_agent_demo")
async def reject_review(transaction_id: str) -> ReviewResponse:
    """Reject a pending AML transaction review."""
    if transaction_id not in pending_reviews:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review = pending_reviews[transaction_id]
    if review.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Review is not pending")
    
    # Update review status
    review["status"] = "rejected"
    review["reviewed_at"] = datetime.now().isoformat()
    review["review_action"] = "REJECT"
    
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
@traceable(name="escalate_review", project_name="financial_services_deep_agent_demo")
async def escalate_review(transaction_id: str) -> ReviewResponse:
    """Escalate a pending AML transaction review."""
    if transaction_id not in pending_reviews:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review = pending_reviews[transaction_id]
    if review.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Review is not pending")
    
    # Update review status
    review["status"] = "escalated"
    review["reviewed_at"] = datetime.now().isoformat()
    review["review_action"] = "ESCALATE"
    
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
