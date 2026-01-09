# LangGraph Studio Guide

This guide explains how to use LangGraph Studio to visualize, debug, and develop the KYC and AML agent workflows.

## What is LangGraph Studio?

LangGraph Studio is a visual development environment for building and debugging LangGraph applications. It provides:
- **Visual Graph Editor**: See your workflow as a graph with nodes and edges
- **Step-by-Step Execution**: Watch your agent execute each step in real-time
- **State Inspection**: Inspect the state at any point in the workflow
- **Interactive Debugging**: Test different inputs and see how the graph responds
- **Live Editing**: Modify your graph and see changes immediately

## Setup

### 1. Install LangGraph CLI

```bash
pip install langgraph-cli
```

### 2. Start LangGraph Studio

Navigate to the project directory and run:

```bash
langgraph dev
```

This will:
- Start the LangGraph Studio server
- Open your browser to `http://localhost:8123`
- Load the graphs defined in `langgraph.json`

### 3. Verify Configuration

The `langgraph.json` file defines which graphs are available:

```json
{
  "graphs": {
    "KYC Onboarding Agent": "./graphs/kyc_graph.py:graph",
    "AML Transaction Monitoring": "./graphs/aml_graph.py:graph"
  }
}
```

## Using the Graphs

### KYC Onboarding Agent

The KYC graph processes customer onboarding through these steps:

1. **extract_documents**: Extracts customer information from submitted documents
2. **check_watchlist**: Verifies customer against watchlists and sanctions lists
3. **assess_risk**: Calculates risk score based on customer profile
4. **make_decision**: Makes final decision (Approve/Reject/Manual Review)

#### Example Input

```json
{
  "customer_id": "customer-123",
  "documents": {
    "name": "John Doe",
    "dob": "1990-01-01",
    "address": "123 Main St, City, Country",
    "nationality": "USA",
    "id_type": "Passport",
    "id_number": "AB123456",
    "occupation": "Software Engineer",
    "source_of_funds": "Employment salary"
  }
}
```

#### Testing High-Risk Customer

To test a high-risk scenario:

```json
{
  "customer_id": "customer-456",
  "documents": {
    "name": "John Doe",
    "dob": "1985-05-15",
    "address": "456 High Risk St",
    "nationality": "Iran",
    "id_type": "Passport",
    "id_number": "IR789012",
    "occupation": "Cash Business Owner",
    "source_of_funds": "Cash deposits"
  }
}
```

This should trigger:
- Watchlist check (if name matches)
- High risk assessment (due to nationality and source of funds)
- Manual review or rejection decision

### AML Transaction Monitoring

The AML graph analyzes transactions through these steps:

1. **analyze_pattern**: Analyzes transaction patterns for suspicious activity
2. **check_sanctions**: Checks transaction against sanctions lists
3. **detect_anomalies**: Identifies anomalies (unusual amounts, patterns, geographies)
4. **human_review**: **Human-in-the-loop interrupt** - Pauses for human review when anomalies are detected
5. **generate_alert**: Creates alerts with severity levels if suspicious activity detected

#### Human-in-the-Loop Feature

When anomalies are detected, the graph automatically pauses and requests human review. The human reviewer can:
- **APPROVE**: Allow the transaction to proceed (alert still generated)
- **REJECT**: Block the transaction immediately
- **ESCALATE**: Send to senior analyst for further review

This ensures critical decisions are made with human oversight.

#### Example Input

**Important**: The transaction must be wrapped in a `transaction` key, and `customer_history` is required (can be empty array).

```json
{
  "transaction": {
    "transaction_id": "txn-123",
    "customer_id": "customer-123",
    "amount": 50000.0,
    "currency": "USD",
    "transaction_type": "transfer",
    "origin": "USA",
    "destination": "Canada",
    "timestamp": "2024-01-15T10:30:00",
    "description": "Wire transfer"
  },
  "customer_history": []
}
```

**Common Error**: If you get `KeyError('transaction')`, make sure you're wrapping the transaction data in a `transaction` key, not providing it directly.

#### Testing Suspicious Transaction

To test suspicious activity detection:

```json
{
  "transaction": {
    "transaction_id": "txn-456",
    "customer_id": "customer-789",
    "amount": 9500.0,
    "currency": "USD",
    "transaction_type": "transfer",
    "origin": "USA",
    "destination": "Iran",
    "timestamp": "2024-01-15T10:30:00",
    "description": "Suspicious transaction"
  },
  "customer_history": []
}
```

This should trigger:
- Sanctions check (Iran is on sanctions list)
- High-risk jurisdiction detection
- Alert generation with CRITICAL or HIGH severity

#### Testing Structuring Pattern

To test structuring detection (multiple small transactions):

```json
{
  "transaction": {
    "transaction_id": "txn-789",
    "customer_id": "customer-123",
    "amount": 9500.0,
    "currency": "USD",
    "transaction_type": "transfer",
    "origin": "USA",
    "destination": "Canada",
    "timestamp": "2024-01-15T10:30:00"
  },
  "customer_history": [
    {
      "transaction_id": "txn-001",
      "customer_id": "customer-123",
      "amount": 9800.0,
      "currency": "USD",
      "transaction_type": "transfer",
      "origin": "USA",
      "destination": "Canada",
      "timestamp": "2024-01-14T09:00:00"
    },
    {
      "transaction_id": "txn-002",
      "customer_id": "customer-123",
      "amount": 9700.0,
      "currency": "USD",
      "transaction_type": "transfer",
      "origin": "USA",
      "destination": "Canada",
      "timestamp": "2024-01-13T08:00:00"
    },
    {
      "transaction_id": "txn-003",
      "customer_id": "customer-123",
      "amount": 9600.0,
      "currency": "USD",
      "transaction_type": "transfer",
      "origin": "USA",
      "destination": "Canada",
      "timestamp": "2024-01-12T07:00:00"
    },
    {
      "transaction_id": "txn-004",
      "customer_id": "customer-123",
      "amount": 9400.0,
      "currency": "USD",
      "transaction_type": "transfer",
      "origin": "USA",
      "destination": "Canada",
      "timestamp": "2024-01-11T06:00:00"
    },
    {
      "transaction_id": "txn-005",
      "customer_id": "customer-123",
      "amount": 9300.0,
      "currency": "USD",
      "transaction_type": "transfer",
      "origin": "USA",
      "destination": "Canada",
      "timestamp": "2024-01-10T05:00:00"
    }
  ]
}
```

This should detect structuring (multiple transactions just under $10k threshold).

#### Testing Human-in-the-Loop Interrupt

To test the human review interrupt, use a transaction that will trigger anomalies:

```json
{
  "transaction": {
    "transaction_id": "txn-review-001",
    "customer_id": "customer-123",
    "amount": 75000.0,
    "currency": "USD",
    "transaction_type": "transfer",
    "origin": "USA",
    "destination": "Iran",
    "timestamp": "2024-01-15T10:30:00",
    "description": "Large transaction to sanctioned country"
  },
  "customer_history": []
}
```

When you run this in LangGraph Studio:
1. The graph will execute through `analyze_pattern`, `check_sanctions`, and `detect_anomalies`
2. At `detect_anomalies`, anomalies will be detected (sanctions match + high-risk jurisdiction + large amount)
3. The conditional edge will route to `human_review` node
4. **Execution will pause** and show a review message
5. You'll be prompted to provide a decision: "APPROVE", "REJECT", or "ESCALATE"
6. After providing your decision, the graph will resume:
   - If APPROVE: Continues to generate alert
   - If REJECT: Ends immediately (transaction blocked)
   - If ESCALATE: Continues to generate alert with escalated status

## Features in LangGraph Studio

### Visual Graph View

- See the complete workflow as a graph
- Nodes represent each step in the process
- Edges show the flow between steps
- Color coding indicates node status (pending, running, completed, error)

### State Inspection

- Click on any node to see the state at that point
- View all state variables and their values
- Inspect intermediate results between steps

### Execution Tracing

- Watch the graph execute step-by-step
- See which node is currently running
- View the execution path through the graph
- Identify bottlenecks or errors

### Input/Output Testing

- Test different inputs without modifying code
- See immediate results
- Compare outputs for different scenarios
- Iterate quickly on prompt changes

### Human-in-the-Loop Interrupts

- **Automatic Pausing**: Graph execution pauses when anomalies are detected
- **Review Interface**: Clear review message with all relevant transaction details
- **Decision Making**: Provide APPROVE, REJECT, or ESCALATE decision
- **Resume Execution**: Graph continues based on your decision
- **State Persistence**: Uses checkpointer to maintain state during interrupt

## Tips for Development

1. **Start Simple**: Test with basic inputs first, then add complexity
2. **Use State Inspection**: Check state at each node to understand data flow
3. **Test Edge Cases**: Try high-risk customers, suspicious transactions, etc.
4. **Iterate on Prompts**: Modify prompts in the graph files and see results immediately
5. **Compare Scenarios**: Run multiple tests side-by-side to compare outcomes

## Troubleshooting

### Graph Not Appearing

- Check that `langgraph.json` has correct paths
- Verify the graph variable is exported correctly (e.g., `graph = ...`)
- Ensure all dependencies are installed

### Import Errors

- Make sure all imports are correct
- Check that dependencies in `requirements.txt` are installed
- Verify Python path is set correctly

### State Type Errors

- Ensure state TypedDict matches the actual state structure
- Check that all required fields are provided in input
- Verify optional fields use `Optional[...]` type hints

### KeyError('transaction')

If you get `KeyError('transaction')` when providing input, you need to wrap your transaction data in a `transaction` key.

**Incorrect format** (transaction data directly):
```json
{
  "transaction_id": "df7cc946-f438-44ec-8c4e-6cdde80c0b85",
  "customer_id": "86627ee6-7f17-4b4a-99c2-577fd535490c",
  "amount": 435243.0,
  ...
}
```

**Correct format** (transaction wrapped in `transaction` key):
```json
{
  "transaction": {
    "transaction_id": "df7cc946-f438-44ec-8c4e-6cdde80c0b85",
    "customer_id": "86627ee6-7f17-4b4a-99c2-577fd535490c",
    "amount": 435243.0,
    "currency": "USD",
    "transaction_type": "transfer",
    "origin": "USA",
    "destination": "Bouvet Island (Bouvetoya)",
    "timestamp": "2026-01-07T18:27:00.025975",
    "description": "Large transaction amount"
  },
  "customer_history": []
}
```

The `customer_history` field is also required (can be an empty array `[]`).

## Next Steps

- Modify the graphs to add new nodes or change logic
- Add conditional edges for more complex workflows
- Integrate with real watchlist/sanctions services
- Add human-in-the-loop checkpoints for high-risk cases
- Implement feedback loops for continuous improvement
