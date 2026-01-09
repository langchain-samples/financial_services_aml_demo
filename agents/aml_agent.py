"""AML (Anti-Money Laundering) transaction monitoring agent."""

from typing import Dict, List, Optional, Literal
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langsmith import traceable
from pydantic import BaseModel, Field

from .prompts import (
    AML_SYSTEM_PROMPT,
    AML_TRANSACTION_ANALYSIS_PROMPT,
    AML_ALERT_GENERATION_PROMPT,
)


class Transaction(BaseModel):
    """Transaction data model."""
    transaction_id: str
    customer_id: str
    amount: float
    currency: str = "USD"
    transaction_type: str  # "deposit", "withdrawal", "transfer"
    origin: str
    destination: str
    timestamp: datetime
    description: Optional[str] = None


class TransactionPattern(BaseModel):
    """Transaction pattern analysis."""
    pattern_type: str
    frequency: int
    total_amount: float
    average_amount: float
    suspicious_indicators: List[str]


class SanctionsCheck(BaseModel):
    """Sanctions list check result."""
    checked: bool
    matched: bool
    match_details: Optional[str] = None


class AnomalyDetection(BaseModel):
    """Anomaly detection result."""
    anomalies_detected: bool
    anomaly_types: List[str]
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    details: str


class Alert(BaseModel):
    """AML alert."""
    alert_id: str
    transaction_id: str
    customer_id: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    risk_score: int = Field(ge=0, le=100)
    indicators: List[str]
    recommended_action: str
    justification: str
    timestamp: datetime = Field(default_factory=datetime.now)


class AMLAgent:
    """AML transaction monitoring agent with pattern analysis and alert generation."""

    def __init__(
        self,
        llm_model: str = "gpt-4",
        temperature: float = 0.0,
        project_name: str = "financial_services_deep_agent_demo",
    ):
        """Initialize AML agent."""
        self.llm = ChatOpenAI(model=llm_model, temperature=temperature)
        self.project_name = project_name
        # Mock transaction history (in production, use database)
        self.transaction_history: Dict[str, List[Transaction]] = {}

    @traceable(name="analyze_transaction_pattern", project_name="financial_services_deep_agent_demo")
    def analyze_transaction_pattern(
        self, transaction: Transaction, customer_history: List[Transaction]
    ) -> TransactionPattern:
        """Analyze transaction patterns for suspicious activity."""
        if not customer_history:
            return TransactionPattern(
                pattern_type="NEW_CUSTOMER",
                frequency=1,
                total_amount=transaction.amount,
                average_amount=transaction.amount,
                suspicious_indicators=[],
            )

        # Analyze patterns
        recent_transactions = [
            t for t in customer_history
            if (transaction.timestamp - t.timestamp).days <= 30
        ]

        total_amount = sum(t.amount for t in recent_transactions) + transaction.amount
        frequency = len(recent_transactions) + 1
        average_amount = total_amount / frequency

        suspicious_indicators = []

        # Check for structuring (breaking large transactions into smaller ones)
        if transaction.amount < 10000 and frequency > 5:
            suspicious_indicators.append("Potential structuring - multiple transactions under $10k")

        # Check for rapid movement
        if frequency > 10:
            suspicious_indicators.append("High transaction frequency")

        # Check for unusual amounts
        if transaction.amount > average_amount * 3:
            suspicious_indicators.append("Unusually large transaction amount")

        pattern_type = "NORMAL"
        if suspicious_indicators:
            pattern_type = "SUSPICIOUS"

        return TransactionPattern(
            pattern_type=pattern_type,
            frequency=frequency,
            total_amount=total_amount,
            average_amount=average_amount,
            suspicious_indicators=suspicious_indicators,
        )

    @traceable(name="check_sanctions", project_name="financial_services_deep_agent_demo")
    def check_sanctions(self, transaction: Transaction) -> SanctionsCheck:
        """Check transaction against sanctions lists."""
        # Mock sanctions check (in production, integrate with real service)
        high_risk_destinations = ["iran", "north korea", "syria", "cuba"]
        
        destination_lower = transaction.destination.lower()
        matched = any(country in destination_lower for country in high_risk_destinations)

        if matched:
            return SanctionsCheck(
                checked=True,
                matched=True,
                match_details=f"Destination {transaction.destination} is on sanctions list",
            )

        return SanctionsCheck(checked=True, matched=False)

    @traceable(name="detect_anomalies", project_name="financial_services_deep_agent_demo")
    def detect_anomalies(
        self,
        transaction: Transaction,
        pattern: TransactionPattern,
        sanctions_check: SanctionsCheck,
    ) -> AnomalyDetection:
        """Detect anomalies in transaction."""
        anomaly_types = []
        severity = "LOW"

        if sanctions_check.matched:
            anomaly_types.append("SANCTIONS_MATCH")
            severity = "HIGH"

        if pattern.pattern_type == "SUSPICIOUS":
            anomaly_types.extend(pattern.suspicious_indicators)
            if severity == "LOW":
                severity = "MEDIUM"

        # Check for unusual geography
        high_risk_countries = ["iran", "north korea", "syria", "cuba", "russia"]
        if any(country in transaction.destination.lower() for country in high_risk_countries):
            anomaly_types.append("HIGH_RISK_JURISDICTION")
            if severity in ["LOW", "MEDIUM"]:
                severity = "HIGH"

        # Check for large amounts
        if transaction.amount > 50000:
            anomaly_types.append("LARGE_AMOUNT")
            if severity == "LOW":
                severity = "MEDIUM"

        return AnomalyDetection(
            anomalies_detected=len(anomaly_types) > 0,
            anomaly_types=anomaly_types,
            severity=severity,
            details=f"Detected {len(anomaly_types)} anomaly types",
        )

    @traceable(name="generate_alert", project_name="financial_services_deep_agent_demo")
    def generate_alert(
        self,
        transaction: Transaction,
        pattern: TransactionPattern,
        sanctions_check: SanctionsCheck,
        anomalies: AnomalyDetection,
    ) -> Optional[Alert]:
        """Generate alert if suspicious activity is detected."""
        if not anomalies.anomalies_detected:
            return None

        # Calculate risk score
        risk_score = 0
        indicators = []

        if sanctions_check.matched:
            risk_score += 50
            indicators.append("Sanctions list match")

        if pattern.suspicious_indicators:
            risk_score += 30
            indicators.extend(pattern.suspicious_indicators)

        if anomalies.severity == "HIGH":
            risk_score += 20
            indicators.append("High severity anomalies")

        risk_score = min(risk_score, 100)

        # Determine alert severity
        if risk_score >= 80:
            alert_severity = "CRITICAL"
            recommended_action = "IMMEDIATE_FREEZE"
        elif risk_score >= 60:
            alert_severity = "HIGH"
            recommended_action = "REVIEW_REQUIRED"
        elif risk_score >= 40:
            alert_severity = "MEDIUM"
            recommended_action = "MONITOR"
        else:
            alert_severity = "LOW"
            recommended_action = "LOG_ONLY"

        alert_id = f"AML-{transaction.transaction_id}-{int(datetime.now().timestamp())}"

        return Alert(
            alert_id=alert_id,
            transaction_id=transaction.transaction_id,
            customer_id=transaction.customer_id,
            severity=alert_severity,
            risk_score=risk_score,
            indicators=indicators,
            recommended_action=recommended_action,
            justification=f"Risk score: {risk_score}. Indicators: {', '.join(indicators)}",
        )

    @traceable(name="analyze_transaction", project_name="financial_services_deep_agent_demo")
    def analyze_transaction(self, transaction: Transaction) -> Optional[Alert]:
        """Complete AML transaction analysis workflow."""
        # Get customer transaction history
        customer_history = self.transaction_history.get(transaction.customer_id, [])

        # Step 1: Analyze transaction patterns
        pattern = self.analyze_transaction_pattern(transaction, customer_history)

        # Step 2: Check sanctions
        sanctions_check = self.check_sanctions(transaction)

        # Step 3: Detect anomalies
        anomalies = self.detect_anomalies(transaction, pattern, sanctions_check)

        # Step 4: Generate alert if needed
        alert = self.generate_alert(transaction, pattern, sanctions_check, anomalies)

        # Update transaction history
        if transaction.customer_id not in self.transaction_history:
            self.transaction_history[transaction.customer_id] = []
        self.transaction_history[transaction.customer_id].append(transaction)

        return alert
