"""Tests for KYC and AML agents."""

import pytest
from datetime import datetime

from agents.kyc_agent import KYCAgent, CustomerDocument
from agents.aml_agent import AMLAgent, Transaction


def test_kyc_agent_initialization():
    """Test KYC agent initialization."""
    agent = KYCAgent()
    assert agent is not None
    assert agent.project_name == "financial_services_deep_agent_demo"


def test_kyc_document_extraction():
    """Test KYC document extraction."""
    agent = KYCAgent()
    documents = {
        "name": "John Doe",
        "dob": "1990-01-01",
        "address": "123 Main St, City, Country",
        "nationality": "USA",
        "id_type": "Passport",
        "id_number": "AB123456",
        "occupation": "Software Engineer",
        "source_of_funds": "Employment salary",
    }
    
    customer_info = agent.extract_document_info(documents)
    assert customer_info.full_name == "John Doe"
    assert customer_info.nationality == "USA"


def test_kyc_watchlist_check():
    """Test KYC watchlist checking."""
    agent = KYCAgent()
    customer_info = CustomerDocument(
        full_name="John Doe",
        date_of_birth="1990-01-01",
        address="123 Main St",
        nationality="USA",
        id_document_type="Passport",
        id_document_number="AB123456",
        occupation="Engineer",
        source_of_funds="Salary",
    )
    
    watchlist_match = agent.check_watchlist(customer_info)
    assert isinstance(watchlist_match.matched, bool)


def test_kyc_risk_assessment():
    """Test KYC risk assessment."""
    agent = KYCAgent()
    customer_info = CustomerDocument(
        full_name="Test User",
        date_of_birth="1990-01-01",
        address="123 Main St",
        nationality="USA",
        id_document_type="Passport",
        id_document_number="AB123456",
        occupation="Engineer",
        source_of_funds="Salary",
    )
    
    from agents.kyc_agent import WatchlistMatch
    watchlist_match = WatchlistMatch(matched=False)
    
    risk_assessment = agent.assess_risk(customer_info, watchlist_match)
    assert risk_assessment.risk_score >= 0
    assert risk_assessment.risk_score <= 100
    assert risk_assessment.risk_level in ["LOW", "MEDIUM", "HIGH"]


def test_aml_agent_initialization():
    """Test AML agent initialization."""
    agent = AMLAgent()
    assert agent is not None
    assert agent.project_name == "financial_services_deep_agent_demo"


def test_aml_transaction_analysis():
    """Test AML transaction analysis."""
    agent = AMLAgent()
    
    transaction = Transaction(
        transaction_id="test-123",
        customer_id="customer-123",
        amount=5000.0,
        currency="USD",
        transaction_type="transfer",
        origin="USA",
        destination="Canada",
        timestamp=datetime.now(),
        description="Test transaction",
    )
    
    alert = agent.analyze_transaction(transaction)
    # Alert may or may not be generated depending on transaction characteristics
    assert alert is None or alert.risk_score >= 0


def test_aml_sanctions_check():
    """Test AML sanctions checking."""
    agent = AMLAgent()
    
    transaction = Transaction(
        transaction_id="test-123",
        customer_id="customer-123",
        amount=10000.0,
        currency="USD",
        transaction_type="transfer",
        origin="USA",
        destination="Iran",  # High-risk destination
        timestamp=datetime.now(),
    )
    
    sanctions_check = agent.check_sanctions(transaction)
    assert sanctions_check.checked is True
    # Iran should match sanctions list
    assert sanctions_check.matched is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
