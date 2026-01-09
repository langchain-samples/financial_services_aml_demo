"""LangSmith configuration and setup utilities."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_langsmith_api_key() -> Optional[str]:
    """Get LangSmith API key from environment."""
    return os.getenv("LANGCHAIN_API_KEY")


def get_kyc_project_name() -> str:
    """Get KYC project name from environment."""
    return os.getenv("LANGCHAIN_KYC_PROJECT", "financial_services_deep_agent_demo")


def get_aml_project_name() -> str:
    """Get AML project name from environment."""
    return os.getenv("LANGCHAIN_AML_PROJECT", "financial_services_deep_agent_demo")


def get_default_project_name() -> str:
    """Get default LangSmith project name."""
    return os.getenv("LANGCHAIN_PROJECT", "financial_services_deep_agent_demo")


def configure_langsmith_tracing():
    """Configure LangSmith tracing environment variables."""
    # Set tracing to v2
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    
    # Set API key if not already set
    api_key = get_langsmith_api_key()
    if api_key:
        os.environ["LANGCHAIN_API_KEY"] = api_key
    
    # Set default project
    default_project = get_default_project_name()
    os.environ["LANGCHAIN_PROJECT"] = default_project


def get_trace_metadata(
    customer_id: Optional[str] = None,
    transaction_id: Optional[str] = None,
    risk_level: Optional[str] = None,
) -> dict:
    """Get metadata dictionary for LangSmith traces."""
    metadata = {}
    
    if customer_id:
        metadata["customer_id"] = customer_id
    if transaction_id:
        metadata["transaction_id"] = transaction_id
    if risk_level:
        metadata["risk_level"] = risk_level
    
    return metadata


# Initialize LangSmith tracing on import
configure_langsmith_tracing()
