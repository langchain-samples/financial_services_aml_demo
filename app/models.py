"""Pydantic models for API requests and responses."""

from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from agents.kyc_agent import KYCDecision
from agents.aml_agent import Alert, Transaction
from load_generator.customer_generator import CustomerProfile


class KYCOnboardRequest(BaseModel):
    """Request model for KYC onboarding."""
    customer_id: str
    documents: Dict[str, str] = Field(..., description="Customer documents as key-value pairs")


class KYCOnboardResponse(BaseModel):
    """Response model for KYC onboarding."""
    success: bool
    decision: Optional[KYCDecision] = None
    error: Optional[str] = None


class AMLAnalyzeRequest(BaseModel):
    """Request model for AML transaction analysis."""
    transaction: Transaction


class AMLAnalyzeResponse(BaseModel):
    """Response model for AML transaction analysis."""
    success: bool
    alert: Optional[Alert] = None
    error: Optional[str] = None


class LoadCustomersRequest(BaseModel):
    """Request model for customer load generation."""
    count: int = Field(ge=1, le=1000, description="Number of customers to generate")
    risk_distribution: Dict[str, float] = Field(
        default={"low": 0.7, "medium": 0.2, "high": 0.1},
        description="Risk level distribution",
    )


class LoadCustomersResponse(BaseModel):
    """Response model for customer load generation."""
    success: bool
    customers_generated: int
    customers: List[CustomerProfile]
    message: str


class LoadTransactionsRequest(BaseModel):
    """Request model for transaction load generation."""
    count: int = Field(ge=1, le=1000, description="Number of transactions to generate")
    customer_ids: Optional[List[str]] = Field(None, description="Customer IDs to use")
    suspicious_ratio: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Ratio of suspicious transactions",
    )


class LoadTransactionsResponse(BaseModel):
    """Response model for transaction load generation."""
    success: bool
    transactions_generated: int
    transactions: List[Transaction]
    message: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime = Field(default_factory=datetime.now)
