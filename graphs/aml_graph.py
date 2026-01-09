"""AML transaction monitoring graph using LangGraph."""

from typing import TypedDict, Optional, Literal
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from langsmith import traceable

from agents.prompts import (
    AML_TRANSACTION_ANALYSIS_PROMPT,
    AML_ALERT_GENERATION_PROMPT,
)
from agents.aml_agent import (
    Transaction,
    TransactionPattern,
    SanctionsCheck,
    AnomalyDetection,
    Alert,
)


class AMLState(TypedDict):
    """State for AML transaction analysis workflow."""
    transaction: Transaction
    customer_history: list[Transaction]  # Can be empty list
    pattern: Optional[TransactionPattern]
    sanctions_check: Optional[SanctionsCheck]
    anomalies: Optional[AnomalyDetection]
    alert: Optional[Alert]
    human_review_action: Optional[Literal["APPROVE", "REJECT", "ESCALATE"]]
    error: Optional[str]


class AMLAgentGraph:
    """AML agent as a LangGraph workflow."""

    def __init__(self, llm_model: str = "gpt-4", temperature: float = 0.0):
        """Initialize AML graph."""
        self.llm = ChatOpenAI(model=llm_model, temperature=temperature)
        # Mock transaction history (in production, use database)
        self.transaction_history: dict[str, list[Transaction]] = {}
        self.graph = self._build_graph()

    @traceable(name="normalize_input")
    def normalize_input(self, state: AMLState) -> AMLState:
        """Normalize input - convert dict to Transaction objects if needed.
        
        LangGraph Studio passes JSON as dicts, so we need to convert them to
        Transaction Pydantic models for proper attribute access.
        """
        # Convert transaction dict to Transaction object if needed
        transaction = state.get("transaction")
        if isinstance(transaction, dict):
            # Pydantic will automatically parse ISO datetime strings
            transaction = Transaction(**transaction)
        elif not isinstance(transaction, Transaction):
            # If it's not a dict or Transaction, try to convert
            if hasattr(transaction, 'model_dump'):
                transaction = Transaction(**transaction.model_dump())
            else:
                transaction = Transaction(**dict(transaction))
        
        # Convert customer_history items to Transaction objects if needed
        customer_history = state.get("customer_history") or []
        normalized_history = []
        for txn in customer_history:
            if isinstance(txn, dict):
                normalized_history.append(Transaction(**txn))
            elif isinstance(txn, Transaction):
                normalized_history.append(txn)
            else:
                # Try to convert other types
                if hasattr(txn, 'model_dump'):
                    normalized_history.append(Transaction(**txn.model_dump()))
                else:
                    normalized_history.append(Transaction(**dict(txn)))
        
        return {
            **state,
            "transaction": transaction,
            "customer_history": normalized_history,
        }

    @traceable(name="analyze_pattern")
    def analyze_pattern(self, state: AMLState) -> AMLState:
        """Analyze transaction patterns for suspicious activity."""
        transaction = state["transaction"]
        customer_history = state.get("customer_history") or []

        if not customer_history:
            pattern = TransactionPattern(
                pattern_type="NEW_CUSTOMER",
                frequency=1,
                total_amount=transaction.amount,
                average_amount=transaction.amount,
                suspicious_indicators=[],
            )
            return {**state, "pattern": pattern}

        # Analyze patterns
        recent_transactions = [
            t for t in customer_history
            if (transaction.timestamp - t.timestamp).days <= 30
        ]

        total_amount = sum(t.amount for t in recent_transactions) + transaction.amount
        frequency = len(recent_transactions) + 1
        average_amount = total_amount / frequency

        suspicious_indicators = []

        # Check for structuring
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

        pattern = TransactionPattern(
            pattern_type=pattern_type,
            frequency=frequency,
            total_amount=total_amount,
            average_amount=average_amount,
            suspicious_indicators=suspicious_indicators,
        )

        return {**state, "pattern": pattern}

    @traceable(name="check_sanctions")
    def check_sanctions(self, state: AMLState) -> AMLState:
        """Check transaction against sanctions lists."""
        transaction = state["transaction"]

        # Mock sanctions check
        high_risk_destinations = ["iran", "north korea", "syria", "cuba"]
        destination_lower = transaction.destination.lower()
        matched = any(country in destination_lower for country in high_risk_destinations)

        sanctions_check = SanctionsCheck(
            checked=True,
            matched=matched,
            match_details=f"Destination {transaction.destination} is on sanctions list" if matched else None,
        )

        return {**state, "sanctions_check": sanctions_check}

    @traceable(name="detect_anomalies")
    def detect_anomalies(self, state: AMLState) -> AMLState:
        """Detect anomalies in transaction."""
        transaction = state["transaction"]
        pattern = state["pattern"]
        sanctions_check = state["sanctions_check"]

        if not pattern or not sanctions_check:
            return {**state, "error": "Missing required information for anomaly detection"}

        anomaly_types = []
        severity = "LOW"

        if sanctions_check.matched:
            anomaly_types.append("SANCTIONS_MATCH")
            severity = "HIGH"

        if pattern.pattern_type == "SUSPICIOUS":
            suspicious_indicators = pattern.suspicious_indicators or []
            if suspicious_indicators:
                anomaly_types.extend(suspicious_indicators)
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

        anomalies = AnomalyDetection(
            anomalies_detected=len(anomaly_types) > 0,
            anomaly_types=anomaly_types,
            severity=severity,
            details=f"Detected {len(anomaly_types)} anomaly types",
        )

        return {**state, "anomalies": anomalies}

    @traceable(name="generate_alert")
    def generate_alert(self, state: AMLState) -> AMLState:
        """Generate alert if suspicious activity is detected."""
        transaction = state["transaction"]
        pattern = state["pattern"]
        sanctions_check = state["sanctions_check"]
        anomalies = state["anomalies"]

        if not all([pattern, sanctions_check, anomalies]):
            return {**state, "error": "Missing required information for alert generation"}

        if not anomalies.anomalies_detected:
            return {**state, "alert": None}

        # Calculate risk score
        risk_score = 0
        indicators = []

        if sanctions_check.matched:
            risk_score += 50
            indicators.append("Sanctions list match")

        if pattern:
            suspicious_indicators = pattern.suspicious_indicators or []
            if suspicious_indicators:
                risk_score += 30
                indicators.extend(suspicious_indicators)

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

        alert = Alert(
            alert_id=alert_id,
            transaction_id=transaction.transaction_id,
            customer_id=transaction.customer_id,
            severity=alert_severity,
            risk_score=risk_score,
            indicators=indicators,
            recommended_action=recommended_action,
            justification=f"Risk score: {risk_score}. Indicators: {', '.join(indicators)}",
        )

        return {**state, "alert": alert}

    @traceable(name="human_review")
    def human_review(self, state: AMLState) -> AMLState:
        """Human-in-the-loop review node for anomaly cases."""
        transaction = state["transaction"]
        anomalies = state["anomalies"]
        pattern = state.get("pattern")
        sanctions_check = state.get("sanctions_check")

        if not anomalies or not anomalies.anomalies_detected:
            return {**state, "human_review_action": "APPROVE"}

        # Calculate preliminary risk score for review
        risk_score = 0
        indicators = []
        
        if sanctions_check and sanctions_check.matched:
            risk_score += 50
            indicators.append("Sanctions list match")
        
        if pattern:
            suspicious_indicators = pattern.suspicious_indicators or []
            if suspicious_indicators:
                risk_score += 30
                indicators.extend(suspicious_indicators)
        
        if anomalies.severity == "HIGH":
            risk_score += 20
            indicators.append("High severity anomalies")
        
        risk_score = min(risk_score, 100)

        # Prepare review information
        review_message = f"""
AML Transaction Review Required

Transaction ID: {transaction.transaction_id}
Customer ID: {transaction.customer_id}
Amount: ${transaction.amount:,.2f} {transaction.currency}
Origin: {transaction.origin}
Destination: {transaction.destination}
Transaction Type: {transaction.transaction_type}
Timestamp: {transaction.timestamp}

ANOMALIES DETECTED:
- Severity: {anomalies.severity}
- Anomaly Types: {', '.join(anomalies.anomaly_types) if anomalies.anomaly_types else 'None'}
- Details: {anomalies.details if anomalies.details else 'N/A'}

PRELIMINARY RISK ASSESSMENT:
- Risk Score: {risk_score}/100
- Key Indicators: {', '.join(indicators) if indicators else 'None'}

Please review this transaction and provide your decision:
- APPROVE: Allow the transaction to proceed (alert will be generated)
- REJECT: Block the transaction immediately
- ESCALATE: Send to senior analyst for further review
"""

        # Interrupt for human input - this pauses execution until resumed
        user_decision = interrupt(review_message)
        
        # When resumed, user_decision will contain the human's response
        # Validate the decision
        if not user_decision or user_decision.upper() not in ["APPROVE", "REJECT", "ESCALATE"]:
            user_decision = "ESCALATE"  # Default to escalation for invalid input
        else:
            user_decision = user_decision.upper()

        return {**state, "human_review_action": user_decision}

    def should_require_human_review(self, state: AMLState) -> Literal["human_review", "generate_alert"]:
        """Conditional edge function to determine if human review is needed."""
        anomalies = state.get("anomalies")
        
        if anomalies and anomalies.anomalies_detected:
            # Require human review for any detected anomalies
            return "human_review"
        
        return "generate_alert"

    def after_human_review(self, state: AMLState) -> Literal["generate_alert", END]:
        """Route after human review based on decision."""
        action = state.get("human_review_action")
        
        if action == "APPROVE":
            # If approved, still generate alert but mark as reviewed
            return "generate_alert"
        elif action == "REJECT":
            # If rejected, end immediately (transaction blocked)
            return END
        else:  # ESCALATE
            # If escalated, generate alert with escalated severity
            return "generate_alert"

    def _build_graph(self):
        """Build the AML workflow graph."""
        workflow = StateGraph(AMLState)

        # Add nodes
        workflow.add_node("normalize_input", self.normalize_input)
        workflow.add_node("analyze_pattern", self.analyze_pattern)
        workflow.add_node("check_sanctions", self.check_sanctions)
        workflow.add_node("detect_anomalies", self.detect_anomalies)
        workflow.add_node("human_review", self.human_review)
        workflow.add_node("generate_alert", self.generate_alert)

        # Define edges
        workflow.set_entry_point("normalize_input")
        workflow.add_edge("normalize_input", "analyze_pattern")
        workflow.add_edge("analyze_pattern", "check_sanctions")
        workflow.add_edge("check_sanctions", "detect_anomalies")
        
        # Conditional edge: if anomalies detected, require human review
        workflow.add_conditional_edges(
            "detect_anomalies",
            self.should_require_human_review,
            {
                "human_review": "human_review",
                "generate_alert": "generate_alert",
            }
        )
        
        # After human review, route based on decision
        workflow.add_conditional_edges(
            "human_review",
            self.after_human_review,
            {
                "generate_alert": "generate_alert",
                END: END,
            }
        )
        
        workflow.add_edge("generate_alert", END)

        # LangGraph Studio/API handles persistence automatically for interrupts
        # No need to provide a custom checkpointer - the platform manages it
        # Note: For local Python execution outside Studio, you may want to add:
        #   from langgraph.checkpoint.memory import MemorySaver
        #   return workflow.compile(checkpointer=MemorySaver())
        return workflow.compile()


# Create graph instance for LangGraph Studio
graph = AMLAgentGraph().graph
