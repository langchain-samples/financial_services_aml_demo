# Generating Synthetic Load

This guide explains how to generate synthetic customer and transaction load for the AML/KYC demo.

## Prerequisites

1. Start the FastAPI server:
   ```bash
   uvicorn app.main:app --reload
   ```

2. The server should be running at `http://localhost:8000`

## Generating Customer Load

### Using cURL

Generate 10 customers with default risk distribution (70% low, 20% medium, 10% high):
```bash
curl -X POST http://localhost:8000/load/customers \
  -H "Content-Type: application/json" \
  -d '{
    "count": 10,
    "risk_distribution": {
      "low": 0.7,
      "medium": 0.2,
      "high": 0.1
    }
  }'
```

Generate 50 customers with more high-risk profiles:
```bash
curl -X POST http://localhost:8000/load/customers \
  -H "Content-Type: application/json" \
  -d '{
    "count": 50,
    "risk_distribution": {
      "low": 0.5,
      "medium": 0.3,
      "high": 0.2
    }
  }'
```

### Using Python

```python
import requests

# Generate customer load
response = requests.post(
    "http://localhost:8000/load/customers",
    json={
        "count": 20,
        "risk_distribution": {
            "low": 0.7,
            "medium": 0.2,
            "high": 0.1
        }
    }
)

result = response.json()
print(f"Generated {result['customers_generated']} customers")
print(f"Message: {result['message']}")

# Access customer IDs for transaction generation
customer_ids = [c["customer_id"] for c in result["customers"]]
print(f"Customer IDs: {customer_ids[:5]}...")  # Show first 5
```

### Response Format

```json
{
  "success": true,
  "customers_generated": 10,
  "customers": [
    {
      "customer_id": "uuid-here",
      "name": "John Doe",
      "dob": "1990-01-01",
      "address": "123 Main St, City, Country",
      "nationality": "USA",
      "id_type": "Passport",
      "id_number": "AB123456",
      "occupation": "Software Engineer",
      "source_of_funds": "Employment salary",
      "risk_level": "low"
    },
    ...
  ],
  "message": "Generated 10 customers and queued for KYC processing"
}
```

## Generating Transaction Load

### Using cURL

Generate 20 transactions with 10% suspicious ratio:
```bash
curl -X POST http://localhost:8000/load/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "count": 20,
    "suspicious_ratio": 0.1
  }'
```

Generate transactions for specific customers:
```bash
curl -X POST http://localhost:8000/load/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "count": 50,
    "customer_ids": ["customer-id-1", "customer-id-2"],
    "suspicious_ratio": 0.15
  }'
```

### Using Python

```python
import requests

# First, generate customers to get customer IDs
customers_response = requests.post(
    "http://localhost:8000/load/customers",
    json={"count": 10}
)
customer_ids = [c["customer_id"] for c in customers_response.json()["customers"]]

# Generate transactions for those customers
transactions_response = requests.post(
    "http://localhost:8000/load/transactions",
    json={
        "count": 30,
        "customer_ids": customer_ids,
        "suspicious_ratio": 0.2  # 20% suspicious
    }
)

result = transactions_response.json()
print(f"Generated {result['transactions_generated']} transactions")
print(f"Message: {result['message']}")
```

### Response Format

```json
{
  "success": true,
  "transactions_generated": 20,
  "transactions": [
    {
      "transaction_id": "uuid-here",
      "customer_id": "customer-uuid",
      "amount": 5000.0,
      "currency": "USD",
      "transaction_type": "transfer",
      "origin": "USA",
      "destination": "Canada",
      "timestamp": "2024-01-15T10:30:00",
      "description": "Wire transfer"
    },
    ...
  ],
  "message": "Generated 20 transactions and queued for AML processing"
}
```

## Complete Workflow Example

Here's a complete Python script to generate load and process it:

```python
import requests
import time

BASE_URL = "http://localhost:8000"

# Step 1: Generate customers
print("Generating customers...")
customers_response = requests.post(
    f"{BASE_URL}/load/customers",
    json={
        "count": 25,
        "risk_distribution": {"low": 0.6, "medium": 0.3, "high": 0.1}
    }
)
customers_data = customers_response.json()
print(f"✓ Generated {customers_data['customers_generated']} customers")

# Extract customer IDs
customer_ids = [c["customer_id"] for c in customers_data["customers"]]

# Step 2: Generate transactions for those customers
print("Generating transactions...")
transactions_response = requests.post(
    f"{BASE_URL}/load/transactions",
    json={
        "count": 50,
        "customer_ids": customer_ids,
        "suspicious_ratio": 0.15
    }
)
transactions_data = transactions_response.json()
print(f"✓ Generated {transactions_data['transactions_generated']} transactions")

# Step 3: Wait a bit for background processing
print("Waiting for background processing...")
time.sleep(5)

print("\n✓ Load generation complete!")
print(f"  - {customers_data['customers_generated']} customers queued for KYC")
print(f"  - {transactions_data['transactions_generated']} transactions queued for AML")
print("\nView traces in LangSmith:")
print("  - All traces: https://smith.langchain.com (financial_services_deep_agent_demo)")
```

## Load Generation Parameters

### Customer Load Parameters

- **count** (int, 1-1000): Number of customers to generate
- **risk_distribution** (dict): Distribution of risk levels
  - Keys: `"low"`, `"medium"`, `"high"`
  - Values: Float between 0.0 and 1.0 (should sum to 1.0)

### Transaction Load Parameters

- **count** (int, 1-1000): Number of transactions to generate
- **customer_ids** (list, optional): Specific customer IDs to use. If not provided, random customer IDs are generated.
- **suspicious_ratio** (float, 0.0-1.0): Ratio of suspicious transactions (default: 0.1)

## Viewing Results in LangSmith

After generating load:

1. Navigate to [LangSmith UI](https://smith.langchain.com)
2. Select the `financial_services_deep_agent_demo` project
3. View real-time traces, metrics, and performance data for all operations (KYC and AML)
4. Filter by agent type using tags or metadata if needed

## Generating Anomaly Transactions for Human Review

The AML graph includes a human-in-the-loop interrupt that pauses execution when anomalies are detected. To generate transactions specifically designed to trigger this:

### Using cURL

Generate a transaction to a sanctioned country (will trigger human review):
```bash
curl -X POST "http://localhost:8000/load/transactions/anomalies?anomaly_type=sanctions" \
  -H "Content-Type: application/json"
```

Generate a large amount transaction:
```bash
curl -X POST "http://localhost:8000/load/transactions/anomalies?anomaly_type=large_amount" \
  -H "Content-Type: application/json"
```

Generate structuring pattern (multiple small transactions):
```bash
curl -X POST "http://localhost:8000/load/transactions/anomalies?anomaly_type=structuring" \
  -H "Content-Type: application/json"
```

### Using Python

```python
import requests

# Generate transaction to sanctioned country
response = requests.post(
    "http://localhost:8000/load/transactions/anomalies",
    params={"anomaly_type": "sanctions"}
)

result = response.json()
print(f"Generated {result['transactions_generated']} anomaly transaction(s)")
print(f"Message: {result['message']}")

# The transaction will trigger human review in LangGraph Studio
transaction = result['transactions'][0]
print(f"\nTransaction details:")
print(f"  ID: {transaction['transaction_id']}")
print(f"  Amount: ${transaction['amount']:,.2f}")
print(f"  Destination: {transaction['destination']}")
print(f"  This will trigger human review!")
```

### Available Anomaly Types

- **sanctions**: Transaction to sanctioned country (Iran, North Korea, Syria, Cuba)
- **structuring**: Multiple transactions just under $10k threshold
- **large_amount**: Very large transaction (>$50k)
- **high_risk_jurisdiction**: Transaction to high-risk country

### Testing Human Review in LangGraph Studio

1. Generate an anomaly transaction using the endpoint above
2. Copy the transaction data from the response
3. Open LangGraph Studio: `langgraph dev`
4. Select "AML Transaction Monitoring" graph
5. Paste the transaction data as input
6. Watch the graph execute - it will pause at `human_review` node
7. Provide your decision (APPROVE, REJECT, or ESCALATE)
8. Graph will resume based on your decision

## Tips

- Start with smaller counts (10-20) to test
- Use higher suspicious ratios (0.2-0.3) to see more alerts
- Generate customers first, then use their IDs for transactions to create realistic patterns
- Background tasks process the load asynchronously, so traces may appear gradually
- Check the FastAPI logs to see processing status
- Use `/load/transactions/anomalies` endpoint to generate transactions guaranteed to trigger human review
