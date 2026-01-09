# Frontend Integration Guide

This guide explains how to use the deep-agents-ui frontend to manage AML transaction reviews.

## Overview

The deep-agents-ui has been integrated with the AML/KYC demo to provide a web interface for managing multiple AML transaction reviews. This allows compliance officers to:

- View all pending AML transaction reviews in a dashboard
- Filter reviews by severity, status, and amount
- Approve, reject, or escalate transactions
- Monitor high-severity cases
- Track review history

## Setup

### 1. Install Frontend Dependencies

Navigate to the deep-agents-ui directory:

```bash
cd deep-agents-ui
yarn install
```

### 2. Configure API URL

The frontend needs to know where the FastAPI backend is running. You can:

**Option A: Set in UI**
- Open the AML Reviews page
- Enter the API URL in the header (defaults to `http://localhost:8000`)
- The URL is saved to localStorage

**Option B: Environment Variable**
Create a `.env.local` file in `deep-agents-ui/`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Start the Services

**Terminal 1: FastAPI Backend**
```bash
cd deep_agent_finance_demo
uvicorn app.main:app --reload
```

**Terminal 2: Frontend**
```bash
cd deep-agents-ui
yarn dev
```

The frontend will be available at `http://localhost:3000`

## Using the AML Reviews Interface

### Accessing the Interface

1. Navigate to `http://localhost:3000`
2. Click the **"AML Reviews"** button in the header
3. Or go directly to `http://localhost:3000/aml-reviews`

### Features

#### Dashboard View

- **Pending Count**: Shows number of transactions awaiting review
- **High Severity Count**: Highlights critical cases requiring immediate attention
- **Auto-refresh**: Automatically polls for new reviews every 5 seconds
- **Manual Refresh**: Click "Refresh" button to update immediately

#### Review Cards

Each review card displays:
- Transaction ID and customer ID
- Transaction amount and currency
- Origin and destination countries
- Transaction timestamp
- Anomaly severity badge (LOW/MEDIUM/HIGH)
- Status badge (PENDING/APPROVED/REJECTED/ESCALATED)
- Risk score (if available)
- List of detected anomalies

#### Actions

For pending reviews, you can:
- **Approve**: Allow the transaction to proceed (alert still generated)
- **Reject**: Block the transaction immediately
- **Escalate**: Send to senior analyst for further review

#### Filtering

Use the filters to:
- Filter by severity (LOW, MEDIUM, HIGH)
- Filter by status (pending, approved, rejected, escalated)
- Filter by amount range (min/max)

## API Endpoints

The frontend uses these FastAPI endpoints:

- `GET /aml/reviews/pending` - Get all pending reviews
- `GET /aml/reviews/{transaction_id}` - Get specific review
- `POST /aml/reviews/{transaction_id}/approve` - Approve a review
- `POST /aml/reviews/{transaction_id}/reject` - Reject a review
- `POST /aml/reviews/{transaction_id}/escalate` - Escalate a review

## Workflow

### 1. Generate Anomaly Transactions

Use the load generator to create transactions that trigger reviews:

```bash
curl -X POST "http://localhost:8000/load/transactions/anomalies?anomaly_type=sanctions"
```

### 2. View in Frontend

1. Open `http://localhost:3000/aml-reviews`
2. Pending reviews will appear automatically
3. High-severity cases are highlighted

### 3. Review and Decide

1. Click on a review card to see full details
2. Choose an action:
   - **Approve** for legitimate transactions
   - **Reject** for confirmed suspicious activity
   - **Escalate** for complex cases requiring expert review

### 4. Monitor Status

- Reviews update in real-time
- Status badges show current state
- Filter to see only pending reviews

## Integration with LangGraph Studio

The AML reviews interface works alongside LangGraph Studio:

- **LangGraph Studio**: For interactive debugging and testing individual transactions
- **AML Reviews UI**: For managing multiple reviews in production-like scenarios

Both can be used together:
1. Test transactions in LangGraph Studio to understand the workflow
2. Use the Reviews UI to manage bulk reviews from load generation

## Customization

### Styling

The UI uses Tailwind CSS. Customize styles in:
- `deep-agents-ui/src/app/aml-reviews/page.tsx`
- `deep-agents-ui/src/app/components/AMLReviewCard.tsx`

### API Integration

Modify the hook in:
- `deep-agents-ui/src/app/hooks/useAMLReviews.ts`

### Filters

Add new filters in:
- `deep-agents-ui/src/app/components/AMLFilters.tsx`

## Troubleshooting

### No Reviews Showing

1. Check that the FastAPI backend is running
2. Verify the API URL is correct
3. Generate some anomaly transactions:
   ```bash
   curl -X POST "http://localhost:8000/load/transactions/anomalies?anomaly_type=sanctions"
   ```

### CORS Errors

If you see CORS errors, ensure the FastAPI app has CORS enabled (already configured in `app/main.py`).

### API Connection Issues

- Check that the backend is running on the correct port
- Verify the API URL in the frontend header
- Check browser console for detailed error messages

## Next Steps

- Add database persistence for reviews (currently in-memory)
- Add user authentication and authorization
- Add bulk actions (approve/reject multiple at once)
- Add export functionality for compliance reporting
- Add audit logging for all review actions
- Integrate with real watchlist/sanctions services
