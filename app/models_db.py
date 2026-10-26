"""Database models for AML reviews."""

from sqlalchemy import Column, String, Float, DateTime, Text, JSON, Integer
from sqlalchemy.sql import func
from datetime import datetime
from app.database import Base
import json


class AMLReview(Base):
    """Database model for AML transaction reviews."""
    
    __tablename__ = "aml_reviews"
    
    # Primary key
    transaction_id = Column(String, primary_key=True, index=True)
    
    # Transaction details
    customer_id = Column(String, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    origin = Column(String)
    destination = Column(String)
    transaction_type = Column(String)
    timestamp = Column(DateTime, nullable=False, index=True)
    description = Column(Text)
    
    # Anomaly and alert information (stored as JSON)
    anomalies_detected = Column(String, default="false")  # "true" or "false" as string for SQLite
    anomaly_types = Column(Text)  # JSON array as string
    severity = Column(String, default="LOW")  # HIGH, MEDIUM, LOW
    anomaly_details = Column(Text)
    risk_score = Column(Float)
    alert_id = Column(String, index=True)
    
    # Review status and workflow
    status = Column(String, nullable=False, default="pending", index=True)  # pending, approved, rejected, escalated
    thread_id = Column(String)  # LangGraph thread ID for human-in-the-loop
    
    # Review action details
    review_action = Column(String)  # APPROVE, REJECT, ESCALATE
    reviewed_at = Column(DateTime)
    justification = Column(Text)
    compliance_check = Column(Text)  # JSON as string
    escalation_priority = Column(String)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def to_dict(self) -> dict:
        """Convert model to dictionary format (for API responses)."""
        return {
            "transaction_id": self.transaction_id,
            "customer_id": self.customer_id,
            "amount": self.amount,
            "currency": self.currency,
            "origin": self.origin,
            "destination": self.destination,
            "transaction_type": self.transaction_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "description": self.description,
            "anomalies": {
                "anomalies_detected": self.anomalies_detected == "true",
                "anomaly_types": json.loads(self.anomaly_types) if self.anomaly_types else [],
                "severity": self.severity,
                "details": self.anomaly_details or "",
            },
            "risk_score": self.risk_score,
            "alert_id": self.alert_id,
            "status": self.status,
            "thread_id": self.thread_id,
            "review_action": self.review_action,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "justification": self.justification,
            "compliance_check": json.loads(self.compliance_check) if self.compliance_check else None,
            "escalation_priority": self.escalation_priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AMLReview":
        """Create model instance from dictionary."""
        anomalies = data.get("anomalies", {})
        
        # Handle timestamp conversion
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                timestamp = datetime.now()
        elif timestamp is None:
            timestamp = datetime.now()
        
        # Handle reviewed_at conversion
        reviewed_at = data.get("reviewed_at")
        if isinstance(reviewed_at, str):
            try:
                reviewed_at = datetime.fromisoformat(reviewed_at)
            except ValueError:
                reviewed_at = None
        
        return cls(
            transaction_id=data["transaction_id"],
            customer_id=data["customer_id"],
            amount=data["amount"],
            currency=data.get("currency", "USD"),
            origin=data.get("origin"),
            destination=data.get("destination"),
            transaction_type=data.get("transaction_type"),
            timestamp=timestamp,
            description=data.get("description"),
            anomalies_detected="true" if anomalies.get("anomalies_detected", False) else "false",
            anomaly_types=json.dumps(anomalies.get("anomaly_types", [])),
            severity=anomalies.get("severity", "LOW"),
            anomaly_details=anomalies.get("details", ""),
            risk_score=data.get("risk_score"),
            alert_id=data.get("alert_id"),
            status=data.get("status", "pending"),
            thread_id=data.get("thread_id"),
            review_action=data.get("review_action"),
            reviewed_at=reviewed_at,
            justification=data.get("justification"),
            compliance_check=json.dumps(data["compliance_check"]) if data.get("compliance_check") else None,
            escalation_priority=data.get("escalation_priority"),
        )
