"""Synthetic customer data generator."""

import uuid
from typing import Dict, List, Literal
from faker import Faker
from pydantic import BaseModel

from .config import CustomerLoadConfig


class CustomerProfile(BaseModel):
    """Customer profile for KYC onboarding."""
    customer_id: str
    name: str
    dob: str
    address: str
    nationality: str
    id_type: str
    id_number: str
    occupation: str
    source_of_funds: str
    risk_level: Literal["low", "medium", "high"]


class CustomerGenerator:
    """Generate synthetic customer profiles for KYC testing."""

    def __init__(self):
        """Initialize customer generator."""
        self.faker = Faker()
        Faker.seed(42)  # For reproducible results

        # High-risk countries for AML/KYC
        self.high_risk_countries = ["Iran", "North Korea", "Syria", "Cuba", "Russia"]
        self.medium_risk_countries = ["Venezuela", "Myanmar", "Belarus"]

        # High-risk occupations
        self.high_risk_occupations = ["Cash Business Owner", "Gambling Operator", "Cryptocurrency Trader"]
        self.medium_risk_occupations = ["Real Estate Developer", "Art Dealer", "Precious Metals Dealer"]

    def _generate_risk_level(self, risk_distribution: Dict[str, float]) -> Literal["low", "medium", "high"]:
        """Generate risk level based on distribution."""
        import random
        rand = random.random()
        if rand < risk_distribution.get("low", 0.7):
            return "low"
        elif rand < risk_distribution.get("low", 0.7) + risk_distribution.get("medium", 0.2):
            return "medium"
        else:
            return "high"

    def generate_customer(self, risk_level: Literal["low", "medium", "high"] = "low") -> CustomerProfile:
        """Generate a single customer profile."""
        customer_id = str(uuid.uuid4())

        # Generate base information
        name = self.faker.name()
        dob = self.faker.date_of_birth(minimum_age=18, maximum_age=80).strftime("%Y-%m-%d")
        address = self.faker.address().replace("\n", ", ")

        # Generate nationality based on risk level
        if risk_level == "high":
            nationality = self.faker.random.choice(self.high_risk_countries)
        elif risk_level == "medium":
            nationality = self.faker.random.choice(self.medium_risk_countries)
        else:
            nationality = self.faker.country()

        # Generate ID information
        id_type = self.faker.random.choice(["Passport", "National ID", "Driver's License"])
        id_number = self.faker.bothify(text="??#######")

        # Generate occupation based on risk level
        if risk_level == "high":
            occupation = self.faker.random.choice(self.high_risk_occupations)
        elif risk_level == "medium":
            occupation = self.faker.random.choice(self.medium_risk_occupations)
        else:
            occupation = self.faker.job()

        # Generate source of funds based on risk level
        if risk_level == "high":
            source_of_funds = self.faker.random.choice([
                "Cash deposits",
                "Cryptocurrency trading",
                "Gambling winnings",
                "Unknown source",
            ])
        elif risk_level == "medium":
            source_of_funds = self.faker.random.choice([
                "Business income",
                "Investment returns",
                "Inheritance",
            ])
        else:
            source_of_funds = self.faker.random.choice([
                "Employment salary",
                "Business income",
                "Investment returns",
                "Savings",
            ])

        return CustomerProfile(
            customer_id=customer_id,
            name=name,
            dob=dob,
            address=address,
            nationality=nationality,
            id_type=id_type,
            id_number=id_number,
            occupation=occupation,
            source_of_funds=source_of_funds,
            risk_level=risk_level,
        )

    def generate_customers(self, count: int, risk_distribution: Dict[str, float] = None) -> List[CustomerProfile]:
        """Generate multiple customer profiles."""
        if risk_distribution is None:
            risk_distribution = {"low": 0.7, "medium": 0.2, "high": 0.1}

        customers = []
        for _ in range(count):
            risk_level = self._generate_risk_level(risk_distribution)
            customer = self.generate_customer(risk_level)
            customers.append(customer)

        return customers

    def customer_to_documents(self, customer: CustomerProfile) -> Dict[str, str]:
        """Convert customer profile to document format for KYC agent."""
        return {
            "name": customer.name,
            "dob": customer.dob,
            "address": customer.address,
            "nationality": customer.nationality,
            "id_type": customer.id_type,
            "id_number": customer.id_number,
            "occupation": customer.occupation,
            "source_of_funds": customer.source_of_funds,
        }
