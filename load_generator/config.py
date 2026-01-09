"""Configuration for load generation."""

from typing import Literal
from pydantic import BaseModel


class LoadProfile(BaseModel):
    """Load generation profile configuration."""
    profile_type: Literal["burst", "steady", "ramp_up"]
    rate: int  # requests per second
    duration: int  # seconds
    ramp_up_time: int = 0  # seconds to reach target rate


class CustomerLoadConfig(BaseModel):
    """Customer load generation configuration."""
    count: int
    risk_distribution: dict = {
        "low": 0.7,
        "medium": 0.2,
        "high": 0.1,
    }
    profile: LoadProfile


class TransactionLoadConfig(BaseModel):
    """Transaction load generation configuration."""
    count: int
    suspicious_ratio: float = 0.1  # 10% suspicious transactions
    profile: LoadProfile
