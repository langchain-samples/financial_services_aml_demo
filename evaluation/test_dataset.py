"""Test dataset for AML transaction flagging evaluation.

This module contains curated test cases with known expected outcomes
for evaluating the AML agent's transaction flagging accuracy.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any


def get_test_dataset() -> List[Dict[str, Any]]:
    """
    Returns a comprehensive test dataset for AML evaluation.

    Each test case includes:
    - inputs: Transaction data
    - outputs: Expected evaluation results
    - metadata: Test case description and category
    """
    base_time = datetime.now()

    test_cases = [
        # ============================================================
        # CATEGORY 1: SANCTIONS MATCHES (Should be flagged)
        # ============================================================
        {
            "inputs": {
                "transaction": {
                    "transaction_id": "TEST-SANC-001",
                    "customer_id": "CUST-001",
                    "amount": 5000.0,
                    "currency": "USD",
                    "transaction_type": "transfer",
                    "origin": "United States",
                    "destination": "Iran",
                    "timestamp": base_time.isoformat(),
                    "description": "Wire transfer to Tehran",
                },
                "customer_history": [],
            },
            "outputs": {
                "should_flag": True,
                "expected_severity": "CRITICAL",
                "expected_indicators": ["SANCTIONS_MATCH", "HIGH_RISK_JURISDICTION"],
                "min_risk_score": 70,
                "max_risk_score": 100,
            },
            "metadata": {
                "category": "sanctions",
                "description": "Transfer to sanctioned country (Iran)",
                "test_type": "true_positive",
            },
        },
        {
            "inputs": {
                "transaction": {
                    "transaction_id": "TEST-SANC-002",
                    "customer_id": "CUST-002",
                    "amount": 15000.0,
                    "currency": "USD",
                    "transaction_type": "transfer",
                    "origin": "United Kingdom",
                    "destination": "North Korea",
                    "timestamp": base_time.isoformat(),
                    "description": "Business payment",
                },
                "customer_history": [],
            },
            "outputs": {
                "should_flag": True,
                "expected_severity": "CRITICAL",
                "expected_indicators": ["SANCTIONS_MATCH", "HIGH_RISK_JURISDICTION"],
                "min_risk_score": 70,
                "max_risk_score": 100,
            },
            "metadata": {
                "category": "sanctions",
                "description": "Transfer to sanctioned country (North Korea)",
                "test_type": "true_positive",
            },
        },
        {
            "inputs": {
                "transaction": {
                    "transaction_id": "TEST-SANC-003",
                    "customer_id": "CUST-003",
                    "amount": 8000.0,
                    "currency": "USD",
                    "transaction_type": "withdrawal",
                    "origin": "United States",
                    "destination": "Syria",
                    "timestamp": base_time.isoformat(),
                    "description": "Cash withdrawal",
                },
                "customer_history": [],
            },
            "outputs": {
                "should_flag": True,
                "expected_severity": "CRITICAL",
                "expected_indicators": ["SANCTIONS_MATCH", "HIGH_RISK_JURISDICTION"],
                "min_risk_score": 70,
                "max_risk_score": 100,
            },
            "metadata": {
                "category": "sanctions",
                "description": "Transaction to sanctioned country (Syria)",
                "test_type": "true_positive",
            },
        },
        # ============================================================
        # CATEGORY 2: STRUCTURING PATTERNS (Should be flagged)
        # ============================================================
        {
            "inputs": {
                "transaction": {
                    "transaction_id": "TEST-STRUCT-001",
                    "customer_id": "CUST-100",
                    "amount": 9500.0,
                    "currency": "USD",
                    "transaction_type": "deposit",
                    "origin": "United States",
                    "destination": "United States",
                    "timestamp": base_time.isoformat(),
                    "description": "Cash deposit",
                },
                "customer_history": [
                    {
                        "transaction_id": f"HIST-{i}",
                        "customer_id": "CUST-100",
                        "amount": 9500.0,
                        "transaction_type": "deposit",
                        "timestamp": (base_time - timedelta(days=i)).isoformat(),
                    }
                    for i in range(1, 11)  # 10 similar transactions
                ],
            },
            "outputs": {
                "should_flag": True,
                "expected_severity": "HIGH",
                "expected_indicators": ["STRUCTURING", "HIGH_FREQUENCY"],
                "min_risk_score": 60,
                "max_risk_score": 85,
            },
            "metadata": {
                "category": "structuring",
                "description": "Multiple deposits just under $10k threshold",
                "test_type": "true_positive",
            },
        },
        {
            "inputs": {
                "transaction": {
                    "transaction_id": "TEST-STRUCT-002",
                    "customer_id": "CUST-101",
                    "amount": 9900.0,
                    "currency": "USD",
                    "transaction_type": "withdrawal",
                    "origin": "United States",
                    "destination": "United States",
                    "timestamp": base_time.isoformat(),
                    "description": "ATM withdrawal",
                },
                "customer_history": [
                    {
                        "transaction_id": f"HIST-W-{i}",
                        "customer_id": "CUST-101",
                        "amount": 9800.0 + (i * 50),
                        "transaction_type": "withdrawal",
                        "timestamp": (base_time - timedelta(hours=i * 6)).isoformat(),
                    }
                    for i in range(1, 8)  # 7 similar withdrawals in 2 days
                ],
            },
            "outputs": {
                "should_flag": True,
                "expected_severity": "HIGH",
                "expected_indicators": ["STRUCTURING", "HIGH_FREQUENCY"],
                "min_risk_score": 60,
                "max_risk_score": 85,
            },
            "metadata": {
                "category": "structuring",
                "description": "Multiple withdrawals near reporting threshold",
                "test_type": "true_positive",
            },
        },
        # ============================================================
        # CATEGORY 3: UNUSUALLY LARGE AMOUNTS (Should be flagged)
        # ============================================================
        {
            "inputs": {
                "transaction": {
                    "transaction_id": "TEST-LARGE-001",
                    "customer_id": "CUST-200",
                    "amount": 500000.0,
                    "currency": "USD",
                    "transaction_type": "transfer",
                    "origin": "United States",
                    "destination": "Switzerland",
                    "timestamp": base_time.isoformat(),
                    "description": "Large wire transfer",
                },
                "customer_history": [
                    {
                        "transaction_id": f"HIST-NORM-{i}",
                        "customer_id": "CUST-200",
                        "amount": 2000.0 + (i * 100),
                        "transaction_type": "transfer",
                        "timestamp": (base_time - timedelta(days=i * 3)).isoformat(),
                    }
                    for i in range(1, 10)  # Typical transactions around $2-3k
                ],
            },
            "outputs": {
                "should_flag": True,
                "expected_severity": "HIGH",
                "expected_indicators": ["LARGE_AMOUNT"],
                "min_risk_score": 50,
                "max_risk_score": 75,
            },
            "metadata": {
                "category": "large_amount",
                "description": "Transaction significantly larger than customer history",
                "test_type": "true_positive",
            },
        },
        {
            "inputs": {
                "transaction": {
                    "transaction_id": "TEST-LARGE-002",
                    "customer_id": "CUST-201",
                    "amount": 1000000.0,
                    "currency": "USD",
                    "transaction_type": "withdrawal",
                    "origin": "United States",
                    "destination": "Cayman Islands",
                    "timestamp": base_time.isoformat(),
                    "description": "Large cash withdrawal",
                },
                "customer_history": [
                    {
                        "transaction_id": f"HIST-SMALL-{i}",
                        "customer_id": "CUST-201",
                        "amount": 500.0,
                        "transaction_type": "withdrawal",
                        "timestamp": (base_time - timedelta(days=i * 7)).isoformat(),
                    }
                    for i in range(1, 5)  # Small regular withdrawals
                ],
            },
            "outputs": {
                "should_flag": True,
                "expected_severity": "CRITICAL",
                "expected_indicators": ["LARGE_AMOUNT", "HIGH_RISK_JURISDICTION"],
                "min_risk_score": 70,
                "max_risk_score": 95,
            },
            "metadata": {
                "category": "large_amount",
                "description": "Extremely large withdrawal to tax haven",
                "test_type": "true_positive",
            },
        },
        # ============================================================
        # CATEGORY 4: HIGH FREQUENCY (Should be flagged)
        # ============================================================
        {
            "inputs": {
                "transaction": {
                    "transaction_id": "TEST-FREQ-001",
                    "customer_id": "CUST-300",
                    "amount": 3000.0,
                    "currency": "USD",
                    "transaction_type": "transfer",
                    "origin": "United States",
                    "destination": "United Kingdom",
                    "timestamp": base_time.isoformat(),
                    "description": "International transfer",
                },
                "customer_history": [
                    {
                        "transaction_id": f"HIST-FREQ-{i}",
                        "customer_id": "CUST-300",
                        "amount": 3000.0 + (i * 200),
                        "transaction_type": "transfer",
                        "timestamp": (base_time - timedelta(days=i)).isoformat(),
                    }
                    for i in range(1, 20)  # 20 transactions in 20 days
                ],
            },
            "outputs": {
                "should_flag": True,
                "expected_severity": "MEDIUM",
                "expected_indicators": ["HIGH_FREQUENCY"],
                "min_risk_score": 40,
                "max_risk_score": 65,
            },
            "metadata": {
                "category": "high_frequency",
                "description": "Unusually high transaction frequency",
                "test_type": "true_positive",
            },
        },
        # ============================================================
        # CATEGORY 5: NORMAL TRANSACTIONS (Should NOT be flagged)
        # ============================================================
        {
            "inputs": {
                "transaction": {
                    "transaction_id": "TEST-NORMAL-001",
                    "customer_id": "CUST-400",
                    "amount": 2500.0,
                    "currency": "USD",
                    "transaction_type": "deposit",
                    "origin": "United States",
                    "destination": "United States",
                    "timestamp": base_time.isoformat(),
                    "description": "Payroll deposit",
                },
                "customer_history": [
                    {
                        "transaction_id": f"HIST-PAY-{i}",
                        "customer_id": "CUST-400",
                        "amount": 2500.0,
                        "transaction_type": "deposit",
                        "timestamp": (base_time - timedelta(days=i * 14)).isoformat(),
                    }
                    for i in range(1, 5)  # Regular bi-weekly payroll
                ],
            },
            "outputs": {
                "should_flag": False,
                "expected_severity": None,
                "expected_indicators": [],
                "min_risk_score": 0,
                "max_risk_score": 30,
            },
            "metadata": {
                "category": "normal",
                "description": "Regular payroll deposit",
                "test_type": "true_negative",
            },
        },
        {
            "inputs": {
                "transaction": {
                    "transaction_id": "TEST-NORMAL-002",
                    "customer_id": "CUST-401",
                    "amount": 150.0,
                    "currency": "USD",
                    "transaction_type": "withdrawal",
                    "origin": "United States",
                    "destination": "United States",
                    "timestamp": base_time.isoformat(),
                    "description": "ATM withdrawal",
                },
                "customer_history": [
                    {
                        "transaction_id": f"HIST-ATM-{i}",
                        "customer_id": "CUST-401",
                        "amount": 100.0 + (i * 25),
                        "transaction_type": "withdrawal",
                        "timestamp": (base_time - timedelta(days=i * 7)).isoformat(),
                    }
                    for i in range(1, 4)  # Weekly ATM withdrawals
                ],
            },
            "outputs": {
                "should_flag": False,
                "expected_severity": None,
                "expected_indicators": [],
                "min_risk_score": 0,
                "max_risk_score": 20,
            },
            "metadata": {
                "category": "normal",
                "description": "Regular small ATM withdrawal",
                "test_type": "true_negative",
            },
        },
        {
            "inputs": {
                "transaction": {
                    "transaction_id": "TEST-NORMAL-003",
                    "customer_id": "CUST-402",
                    "amount": 5000.0,
                    "currency": "USD",
                    "transaction_type": "transfer",
                    "origin": "United States",
                    "destination": "Canada",
                    "timestamp": base_time.isoformat(),
                    "description": "Payment to supplier",
                },
                "customer_history": [
                    {
                        "transaction_id": f"HIST-SUPP-{i}",
                        "customer_id": "CUST-402",
                        "amount": 4500.0 + (i * 250),
                        "transaction_type": "transfer",
                        "timestamp": (base_time - timedelta(days=i * 30)).isoformat(),
                    }
                    for i in range(1, 6)  # Monthly supplier payments
                ],
            },
            "outputs": {
                "should_flag": False,
                "expected_severity": None,
                "expected_indicators": [],
                "min_risk_score": 0,
                "max_risk_score": 25,
            },
            "metadata": {
                "category": "normal",
                "description": "Regular business payment to low-risk country",
                "test_type": "true_negative",
            },
        },
        {
            "inputs": {
                "transaction": {
                    "transaction_id": "TEST-NORMAL-004",
                    "customer_id": "CUST-403",
                    "amount": 1200.0,
                    "currency": "USD",
                    "transaction_type": "transfer",
                    "origin": "United States",
                    "destination": "Germany",
                    "timestamp": base_time.isoformat(),
                    "description": "Rent payment",
                },
                "customer_history": [
                    {
                        "transaction_id": f"HIST-RENT-{i}",
                        "customer_id": "CUST-403",
                        "amount": 1200.0,
                        "transaction_type": "transfer",
                        "timestamp": (base_time - timedelta(days=i * 30)).isoformat(),
                    }
                    for i in range(1, 12)  # 11 months of rent payments
                ],
            },
            "outputs": {
                "should_flag": False,
                "expected_severity": None,
                "expected_indicators": [],
                "min_risk_score": 0,
                "max_risk_score": 20,
            },
            "metadata": {
                "category": "normal",
                "description": "Regular monthly rent payment",
                "test_type": "true_negative",
            },
        },
        # ============================================================
        # CATEGORY 6: EDGE CASES
        # ============================================================
        {
            "inputs": {
                "transaction": {
                    "transaction_id": "TEST-EDGE-001",
                    "customer_id": "CUST-500",
                    "amount": 10000.0,  # Exactly at threshold
                    "currency": "USD",
                    "transaction_type": "deposit",
                    "origin": "United States",
                    "destination": "United States",
                    "timestamp": base_time.isoformat(),
                    "description": "Cash deposit",
                },
                "customer_history": [],
            },
            "outputs": {
                "should_flag": False,  # Exactly $10k is reportable but not necessarily suspicious
                "expected_severity": None,
                "expected_indicators": [],
                "min_risk_score": 0,
                "max_risk_score": 40,
            },
            "metadata": {
                "category": "edge_case",
                "description": "Transaction exactly at reporting threshold",
                "test_type": "true_negative",
            },
        },
        {
            "inputs": {
                "transaction": {
                    "transaction_id": "TEST-EDGE-002",
                    "customer_id": "CUST-501",
                    "amount": 50000.0,
                    "currency": "USD",
                    "transaction_type": "transfer",
                    "origin": "United States",
                    "destination": "Japan",
                    "timestamp": base_time.isoformat(),
                    "description": "Real estate purchase",
                },
                "customer_history": [
                    {
                        "transaction_id": f"HIST-BUSINESS-{i}",
                        "customer_id": "CUST-501",
                        "amount": 45000.0 + (i * 2000),
                        "transaction_type": "transfer",
                        "timestamp": (base_time - timedelta(days=i * 90)).isoformat(),
                    }
                    for i in range(1, 4)  # Quarterly large business transactions
                ],
            },
            "outputs": {
                "should_flag": False,  # Large but consistent with history
                "expected_severity": None,
                "expected_indicators": [],
                "min_risk_score": 0,
                "max_risk_score": 35,
            },
            "metadata": {
                "category": "edge_case",
                "description": "Large transaction consistent with business pattern",
                "test_type": "true_negative",
            },
        },
    ]

    return test_cases


def get_dataset_summary() -> Dict[str, Any]:
    """
    Returns a summary of the test dataset.
    """
    dataset = get_test_dataset()

    categories = {}
    test_types = {"true_positive": 0, "true_negative": 0, "false_positive": 0, "false_negative": 0}

    for case in dataset:
        category = case["metadata"]["category"]
        test_type = case["metadata"]["test_type"]

        categories[category] = categories.get(category, 0) + 1
        test_types[test_type] = test_types.get(test_type, 0) + 1

    return {
        "total_cases": len(dataset),
        "categories": categories,
        "test_types": test_types,
        "expected_positives": sum(1 for c in dataset if c["outputs"]["should_flag"]),
        "expected_negatives": sum(1 for c in dataset if not c["outputs"]["should_flag"]),
    }
