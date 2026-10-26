"""Load generation API routes."""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from langsmith import traceable
from utils.trace_context import get_trace_context

from app.models import (
    LoadCustomersRequest,
    LoadCustomersResponse,
    LoadTransactionsRequest,
    LoadTransactionsResponse,
)
from load_generator.customer_generator import CustomerGenerator
from load_generator.transaction_generator import TransactionGenerator
from agents.kyc_agent import KYCAgent
from agents.aml_agent import AMLAgent
from utils.langsmith_setup import get_kyc_project_name, get_aml_project_name
from app.routes.reviews import add_pending_review

router = APIRouter(prefix="/load", tags=["Load Generation"])

# Initialize generators and agents
customer_generator = CustomerGenerator()
transaction_generator = TransactionGenerator()
kyc_agent = KYCAgent(project_name=get_kyc_project_name())
aml_agent = AMLAgent(project_name=get_aml_project_name())


async def process_customer_async(customer, kyc_agent_instance):
    """Process a single customer through KYC."""
    documents = customer_generator.customer_to_documents(customer)
    try:
        kyc_agent_instance.process_onboarding(customer.customer_id, documents)
    except Exception as e:
        print(f"Error processing customer {customer.customer_id}: {e}")


async def process_transaction_async(transaction, aml_agent_instance):
    """Process a single transaction through AML."""
    try:
        alert = aml_agent_instance.analyze_transaction(transaction)
        
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
            add_pending_review(transaction, anomalies, alert)
    except Exception as e:
        print(f"Error processing transaction {transaction.transaction_id}: {e}")


@router.post("/customers", response_model=LoadCustomersResponse)
@traceable(name="load_customers_endpoint", project_name="financial_services_deep_agent_demo", metadata=get_trace_context("kyc_onboarding"))
async def generate_customer_load(
    request: LoadCustomersRequest,
    background_tasks: BackgroundTasks,
) -> LoadCustomersResponse:
    """Generate synthetic customer load and process through KYC."""
    try:
        # Generate customers
        customers = customer_generator.generate_customers(
            count=request.count,
            risk_distribution=request.risk_distribution,
        )

        # Process customers through KYC in background
        for customer in customers:
            documents = customer_generator.customer_to_documents(customer)
            background_tasks.add_task(
                process_customer_async,
                customer,
                kyc_agent,
            )

        return LoadCustomersResponse(
            success=True,
            customers_generated=len(customers),
            customers=customers,
            message=f"Generated {len(customers)} customers and queued for KYC processing",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Customer load generation failed: {str(e)}")


@router.post("/transactions", response_model=LoadTransactionsResponse)
@traceable(name="load_transactions_endpoint", project_name="financial_services_deep_agent_demo", metadata=get_trace_context("aml_transaction_monitoring"))
async def generate_transaction_load(
    request: LoadTransactionsRequest,
    background_tasks: BackgroundTasks,
) -> LoadTransactionsResponse:
    """Generate synthetic transaction load and process through AML."""
    try:
        # Generate transactions
        transactions = transaction_generator.generate_transactions(
            customer_ids=request.customer_ids or [],
            count=request.count,
            suspicious_ratio=request.suspicious_ratio,
        )

        # Process transactions through AML in background
        for transaction in transactions:
            background_tasks.add_task(
                process_transaction_async,
                transaction,
                aml_agent,
            )

        return LoadTransactionsResponse(
            success=True,
            transactions_generated=len(transactions),
            transactions=transactions,
            message=f"Generated {len(transactions)} transactions and queued for AML processing",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transaction load generation failed: {str(e)}")


@router.post("/transactions/anomalies", response_model=LoadTransactionsResponse)
@traceable(name="load_anomaly_transactions_endpoint", project_name="financial_services_deep_agent_demo", metadata=get_trace_context("aml_transaction_monitoring"))
async def generate_anomaly_transaction_load(
    anomaly_type: str = Query("sanctions", description="Type of anomaly: sanctions, structuring, large_amount, high_risk_jurisdiction"),
    customer_id: str = Query(None, description="Customer ID (auto-generated if not provided)"),
    process: bool = Query(False, description="Process transactions through AML and create reviews"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> LoadTransactionsResponse:
    """Generate transactions specifically designed to trigger anomalies for human review.
    
    Args:
        anomaly_type: Type of anomaly to generate
            - "sanctions": Transaction to sanctioned country (Iran, North Korea, etc.)
            - "structuring": Multiple small transactions under $10k threshold
            - "large_amount": Very large transaction (>$50k)
            - "high_risk_jurisdiction": Transaction to high-risk country
        process: If True, process transactions through AML and create reviews in the frontend
    """
    try:
        import uuid
        if not customer_id:
            customer_id = str(uuid.uuid4())

        transactions = []
        
        if anomaly_type == "structuring":
            # Generate a series of structuring transactions
            transactions = transaction_generator.generate_structuring_pattern(
                customer_id=customer_id,
                count=6,
            )
        else:
            # Generate single anomaly transaction
            transaction = transaction_generator.generate_anomaly_transaction(
                customer_id=customer_id,
                anomaly_type=anomaly_type,
            )
            transactions = [transaction]

        # Optionally process transactions through AML to create reviews
        if process:
            for transaction in transactions:
                background_tasks.add_task(
                    process_transaction_async,
                    transaction,
                    aml_agent,
                )
            message = f"Generated {len(transactions)} anomaly transaction(s) of type '{anomaly_type}' and queued for AML processing. Reviews will appear in the frontend."
        else:
            message = f"Generated {len(transactions)} anomaly transaction(s) of type '{anomaly_type}'. Use these in LangGraph Studio to test human-in-the-loop review, or set process=true to create reviews in the frontend."

        return LoadTransactionsResponse(
            success=True,
            transactions_generated=len(transactions),
            transactions=transactions,
            message=message,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anomaly transaction generation failed: {str(e)}")
