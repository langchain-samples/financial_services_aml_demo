"""Synthetic transaction data generator."""

import uuid
from typing import List, Literal
from datetime import datetime, timedelta
from faker import Faker
from pydantic import BaseModel

from .config import TransactionLoadConfig
from agents.aml_agent import Transaction


class TransactionGenerator:
    """Generate synthetic transactions for AML testing."""

    def __init__(self):
        """Initialize transaction generator."""
        self.faker = Faker()
        Faker.seed(42)  # For reproducible results

        # High-risk destinations
        self.high_risk_destinations = ["Iran", "North Korea", "Syria", "Cuba", "Russia"]
        self.medium_risk_destinations = ["Venezuela", "Myanmar", "Belarus"]

        # Transaction types
        self.transaction_types = ["deposit", "withdrawal", "transfer"]

    def generate_transaction(
        self,
        customer_id: str,
        suspicious: bool = False,
        base_time: datetime = None,
    ) -> Transaction:
        """Generate a single transaction."""
        if base_time is None:
            base_time = datetime.now()

        transaction_id = str(uuid.uuid4())
        
        # Generate amount based on suspicious flag
        if suspicious:
            # Suspicious patterns: either very large or structured (multiple small)
            import random
            if random.random() > 0.5:
                # Large suspicious transaction
                amount = self.faker.random.randint(50000, 1000000)
            else:
                # Structured transaction (just under reporting threshold)
                amount = self.faker.random.randint(9000, 9999)
        else:
            # Normal transaction
            amount = self.faker.random.randint(100, 10000)

        currency = "USD"
        transaction_type = self.faker.random.choice(self.transaction_types)

        # Generate origin and destination
        origin = self.faker.country()
        
        if suspicious:
            # Higher chance of high-risk destination
            import random
            if random.random() < 0.7:
                destination = self.faker.random.choice(self.high_risk_destinations)
            else:
                destination = self.faker.random.choice(self.medium_risk_destinations)
        else:
            destination = self.faker.country()

        # Generate timestamp (within last 30 days)
        days_ago = self.faker.random.randint(0, 30)
        timestamp = base_time - timedelta(days=days_ago, hours=self.faker.random.randint(0, 23))

        description = self.faker.sentence() if not suspicious else "Suspicious transaction pattern"

        return Transaction(
            transaction_id=transaction_id,
            customer_id=customer_id,
            amount=amount,
            currency=currency,
            transaction_type=transaction_type,
            origin=origin,
            destination=destination,
            timestamp=timestamp,
            description=description,
        )

    def generate_transactions(
        self,
        customer_ids: List[str],
        count: int,
        suspicious_ratio: float = 0.1,
    ) -> List[Transaction]:
        """Generate multiple transactions."""
        transactions = []
        suspicious_count = int(count * suspicious_ratio)
        normal_count = count - suspicious_count

        # Generate normal transactions
        for _ in range(normal_count):
            customer_id = self.faker.random.choice(customer_ids) if customer_ids else str(uuid.uuid4())
            transaction = self.generate_transaction(customer_id, suspicious=False)
            transactions.append(transaction)

        # Generate suspicious transactions
        for _ in range(suspicious_count):
            customer_id = self.faker.random.choice(customer_ids) if customer_ids else str(uuid.uuid4())
            transaction = self.generate_transaction(customer_id, suspicious=True)
            transactions.append(transaction)

        # Shuffle to mix normal and suspicious
        import random
        random.shuffle(transactions)

        return transactions

    def generate_anomaly_transaction(
        self,
        customer_id: str,
        anomaly_type: Literal["sanctions", "structuring", "large_amount", "high_risk_jurisdiction"] = "sanctions",
        base_time: datetime = None,
    ) -> Transaction:
        """Generate a transaction specifically designed to trigger an anomaly for human review.
        
        Args:
            customer_id: Customer ID for the transaction
            anomaly_type: Type of anomaly to trigger
                - "sanctions": Transaction to sanctioned country
                - "structuring": Multiple small transactions (use with history)
                - "large_amount": Very large transaction amount
                - "high_risk_jurisdiction": Transaction to high-risk country
            base_time: Base timestamp for transaction
        """
        if base_time is None:
            base_time = datetime.now()

        transaction_id = str(uuid.uuid4())
        currency = "USD"
        transaction_type = "transfer"

        if anomaly_type == "sanctions":
            # Transaction to sanctioned country
            amount = self.faker.random.randint(10000, 50000)
            origin = "USA"
            destination = self.faker.random.choice(self.high_risk_destinations)
            description = "Wire transfer to sanctioned jurisdiction"
        elif anomaly_type == "structuring":
            # Small amount that would be part of structuring pattern
            amount = self.faker.random.randint(9000, 9999)
            origin = "USA"
            destination = "Canada"
            description = "Potential structuring transaction"
        elif anomaly_type == "large_amount":
            # Very large transaction
            amount = self.faker.random.randint(100000, 500000)
            origin = "USA"
            destination = self.faker.country()
            description = "Large transaction amount"
        elif anomaly_type == "high_risk_jurisdiction":
            # Transaction to high-risk but not sanctioned country
            amount = self.faker.random.randint(20000, 100000)
            origin = "USA"
            destination = self.faker.random.choice(self.medium_risk_destinations)
            description = "Transaction to high-risk jurisdiction"
        else:
            # Default to sanctions
            amount = self.faker.random.randint(10000, 50000)
            origin = "USA"
            destination = self.faker.random.choice(self.high_risk_destinations)
            description = "Wire transfer"

        # Generate timestamp
        days_ago = self.faker.random.randint(0, 7)  # Recent transactions
        timestamp = base_time - timedelta(days=days_ago, hours=self.faker.random.randint(0, 23))

        return Transaction(
            transaction_id=transaction_id,
            customer_id=customer_id,
            amount=amount,
            currency=currency,
            transaction_type=transaction_type,
            origin=origin,
            destination=destination,
            timestamp=timestamp,
            description=description,
        )

    def generate_structuring_pattern(
        self,
        customer_id: str,
        count: int = 6,
        base_time: datetime = None,
    ) -> List[Transaction]:
        """Generate a series of transactions that form a structuring pattern.
        
        This creates multiple transactions just under $10k threshold to trigger
        structuring detection, which will require human review.
        """
        if base_time is None:
            base_time = datetime.now()

        transactions = []
        for i in range(count):
            transaction = self.generate_anomaly_transaction(
                customer_id=customer_id,
                anomaly_type="structuring",
                base_time=base_time - timedelta(days=count - i - 1),
            )
            transactions.append(transaction)

        return transactions
