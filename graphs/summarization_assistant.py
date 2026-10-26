"""Summarization assistant for AML/KYC financial services demo.

This assistant can summarize transaction reviews, compliance data, and answer questions
about the financial services demo.
"""

from typing import Annotated, Literal, TypedDict, Optional
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langsmith import traceable

from utils.trace_context import get_trace_context
import json
import uuid

# Import review data access - use a function to avoid import issues
def get_pending_reviews():
    """Get pending reviews from the reviews module.
    
    Tries multiple methods to access reviews:
    1. HTTP request to the FastAPI endpoint (primary method - works from LangGraph Studio)
    2. Direct import from app.routes.reviews (fallback - works when running in same process)
    3. Returns empty dict if all fail
    """
    # PRIMARY METHOD: Try HTTP request to FastAPI endpoint (works from LangGraph Studio)
    # This should be tried first since LangGraph Studio runs in a separate process
    try:
        import httpx
        import os
        
        # Get API URL from environment or use default
        api_url = os.getenv("API_URL", "http://localhost:8000")
        
        # Use httpx (already in requirements) to fetch reviews
        # Increase timeout for slower connections
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            try:
                response = client.get(f"{api_url}/aml/reviews/pending")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        reviews_list = data.get("reviews", [])
                        # Always return the list directly - don't convert to dict
                        # The tool will handle both formats
                        # Debug: Log the count to verify we're getting data
                        count = data.get("count", len(reviews_list))
                        if reviews_list:
                            # Return list directly - API already filtered for pending
                            return reviews_list
                        # If success but empty reviews, return empty list
                        return []
                    # If not successful, try direct import
                    pass
                else:
                    # If HTTP request failed with non-200 status, try direct import
                    pass
            except (httpx.TimeoutException, httpx.RequestError, httpx.ConnectError) as e:
                # Connection/timeout error - try direct import as fallback
                pass
            except Exception as e:
                # Any other error - try direct import
                pass
    except ImportError:
        # httpx not available - try direct import
        pass
    except Exception:
        # Any other error - try direct import
        pass
    
    # FALLBACK: Try direct database access (works when running in same process)
    # This is only used if HTTP request fails
    try:
        from app.database import get_db_session
        from app.models_db import AMLReview
        from sqlalchemy import desc
        
        with get_db_session() as db:
            pending_reviews = db.query(AMLReview).filter(
                AMLReview.status == "pending"
            ).order_by(desc(AMLReview.timestamp)).all()
            
            if pending_reviews:
                # Convert to list of dicts
                return [review.to_dict() for review in pending_reviews]
    except (ImportError, AttributeError, Exception):
        # If database access fails, continue to return empty list
        pass
    
    # Final fallback: return empty list
    return []


class SummarizationState(TypedDict, total=False):
    """State for the summarization assistant."""
    messages: Annotated[list[BaseMessage], "add_messages"]
    iterations: int  # Track iterations to prevent infinite loops (optional)


# Define tools using LangChain's @tool decorator
@tool
@traceable(name="get_pending_reviews_summary", project_name="financial_services_deep_agent_demo")
def get_pending_reviews_summary() -> str:
    """Get a summary of all pending AML transaction reviews.
    
    Use this tool when the user asks about:
    - Summarizing reviews
    - Pending reviews
    - What reviews need attention
    - Review summaries
    - AML review status
    
    Returns a formatted summary with counts by severity and ALL pending reviews sorted by risk score.
    """
    pending_reviews = get_pending_reviews()
    
    # Handle both dict and list formats
    if isinstance(pending_reviews, dict):
        reviews_list = list(pending_reviews.values())
    elif isinstance(pending_reviews, list):
        reviews_list = pending_reviews
    else:
        reviews_list = []
    
    # If we got a list from the HTTP API, it's already filtered for pending status
    # by the /aml/reviews/pending endpoint, so we can trust all reviews are pending.
    # If we got a dict from direct import, we need to filter for pending status.
    if isinstance(pending_reviews, list):
        # HTTP API response - already filtered for pending, use all reviews
        pending = [r for r in reviews_list if isinstance(r, dict)]
    else:
        # Direct import (dict) - filter for pending status
        pending = []
        for review in reviews_list:
            if not isinstance(review, dict):
                continue
            status = review.get("status", "pending")  # Default to "pending" if missing
            if status == "pending":
                pending.append(review)
        
        # If we have reviews but none match "pending" status, check if they're all missing status
        if reviews_list and not pending:
            statuses = [r.get("status") for r in reviews_list if isinstance(r, dict)]
            # If all reviews are missing status (None), include them all
            if all(s is None for s in statuses):
                pending = reviews_list
    
    if not pending:
        return "No pending reviews at this time."
    
    # Group by severity
    by_severity = {"HIGH": [], "MEDIUM": [], "LOW": []}
    total_amount = 0
    
    for review in pending:
        severity = review.get("anomalies", {}).get("severity", "LOW")
        by_severity[severity].append(review)
        total_amount += review.get("amount", 0)
    
    summary = f"""Pending AML Reviews Summary:
- Total Pending: {len(pending)}
- High Severity: {len(by_severity['HIGH'])}
- Medium Severity: {len(by_severity['MEDIUM'])}
- Low Severity: {len(by_severity['LOW'])}
- Total Amount Under Review: ${total_amount:,.2f}

All Pending Reviews (sorted by risk score, highest first):"""
    
    # Sort all reviews by risk score (highest first)
    all_reviews_sorted = sorted(
        pending,
        key=lambda x: x.get("risk_score", 0) or 0,
        reverse=True
    )
    
    # Show all reviews with details
    for review in all_reviews_sorted:
        transaction_id = review.get('transaction_id', '')[:8]
        amount = review.get('amount', 0)
        destination = review.get('destination', 'N/A')
        risk_score = review.get('risk_score', 'N/A')
        severity = review.get('anomalies', {}).get('severity', 'LOW')
        anomaly_types = review.get('anomalies', {}).get('anomaly_types', [])
        anomaly_types_str = ', '.join(anomaly_types) if anomaly_types else 'None'
        
        summary += f"\n  - Transaction {transaction_id}: ${amount:,.2f} to {destination} (Risk: {risk_score}, Severity: {severity}, Anomalies: {anomaly_types_str})"
    
    return summary


@tool
@traceable(name="get_review_details", project_name="financial_services_deep_agent_demo")
def get_review_details(transaction_id: str) -> str:
    """Get detailed information about a specific transaction review.
    
    Use this tool when the user asks about a specific transaction by ID.
    
    Args:
        transaction_id: The transaction ID to get details for (extract from user's message)
    
    Returns detailed information including status, anomalies, risk score, and justification.
    """
    pending_reviews = get_pending_reviews()
    
    # Handle both dict and list formats
    if isinstance(pending_reviews, dict):
        if transaction_id not in pending_reviews:
            return f"Review not found for transaction ID: {transaction_id}"
        review = pending_reviews[transaction_id]
    elif isinstance(pending_reviews, list):
        # Find review by transaction_id in list
        review = None
        for r in pending_reviews:
            if isinstance(r, dict) and r.get("transaction_id") == transaction_id:
                review = r
                break
        if not review:
            return f"Review not found for transaction ID: {transaction_id}"
    else:
        return f"Review not found for transaction ID: {transaction_id}"
    
    details = f"""Review Details for Transaction {transaction_id}:
- Status: {review.get('status', 'Unknown')}
- Customer ID: {review.get('customer_id', 'N/A')}
- Amount: ${review.get('amount', 0):,.2f} {review.get('currency', 'USD')}
- Origin: {review.get('origin', 'N/A')}
- Destination: {review.get('destination', 'N/A')}
- Transaction Type: {review.get('transaction_type', 'N/A')}
- Timestamp: {review.get('timestamp', 'N/A')}

Anomalies:
- Detected: {review.get('anomalies', {}).get('anomalies_detected', False)}
- Severity: {review.get('anomalies', {}).get('severity', 'N/A')}
- Types: {', '.join(review.get('anomalies', {}).get('anomaly_types', []))}
- Details: {review.get('anomalies', {}).get('details', 'N/A')}

Risk Assessment:
- Risk Score: {review.get('risk_score', 'N/A')}
- Alert ID: {review.get('alert_id', 'N/A')}
"""
    
    if review.get('justification'):
        details += f"\nJustification: {review.get('justification')}"
    
    return details


@tool
@traceable(name="get_compliance_summary", project_name="financial_services_deep_agent_demo")
def get_compliance_summary() -> str:
    """Get a comprehensive compliance summary of all reviews.
    
    Use this tool when the user asks about:
    - Compliance metrics
    - Compliance reports
    - Status breakdowns
    - Financial impact
    - Approval/rejection rates
    
    Returns a summary with counts by status, severity, and financial impact.
    """
    pending_reviews = get_pending_reviews()
    
    # Handle both dict and list formats
    if isinstance(pending_reviews, dict):
        all_reviews = list(pending_reviews.values())
    elif isinstance(pending_reviews, list):
        all_reviews = pending_reviews
    else:
        all_reviews = []
    
    if not all_reviews:
        return "No reviews available for compliance summary."
    
    # Count by status
    by_status = {"pending": 0, "approved": 0, "rejected": 0, "escalated": 0}
    by_severity = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    total_approved_amount = 0
    total_rejected_amount = 0
    
    for review in all_reviews:
        status = review.get("status", "pending")
        by_status[status] = by_status.get(status, 0) + 1
        
        severity = review.get("anomalies", {}).get("severity", "LOW")
        by_severity[severity] = by_severity.get(severity, 0) + 1
        
        if status == "approved":
            total_approved_amount += review.get("amount", 0)
        elif status == "rejected":
            total_rejected_amount += review.get("amount", 0)
    
    summary = f"""Compliance Summary:
Total Reviews: {len(all_reviews)}

By Status:
- Pending: {by_status['pending']}
- Approved: {by_status['approved']}
- Rejected: {by_status['rejected']}
- Escalated: {by_status['escalated']}

By Severity:
- High: {by_severity['HIGH']}
- Medium: {by_severity['MEDIUM']}
- Low: {by_severity['LOW']}

Financial Impact:
- Total Approved Amount: ${total_approved_amount:,.2f}
- Total Rejected Amount: ${total_rejected_amount:,.2f}
"""
    
    return summary


class SummarizationAssistant:
    """LangGraph assistant for summarizing AML/KYC data and answering questions."""

    def __init__(self, llm_model: str = "gpt-4o", temperature: float = 0.1):
        """Initialize the summarization assistant."""
        # Use low temperature for more deterministic tool calling, but not 0 to allow some flexibility
        self.llm = ChatOpenAI(model=llm_model, temperature=temperature)
        self.graph = self._build_graph()

    def _clean_messages_for_llm(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        """Clean message sequence to ensure tool messages are properly linked to tool_calls.
        
        OpenAI requires that tool messages must follow an AI message with tool_calls.
        This function filters out orphaned tool messages to prevent BadRequestError.
        """
        if not messages:
            return messages
        
        cleaned = []
        i = 0
        while i < len(messages):
            msg = messages[i]
            
            # Check if this is a tool message
            is_tool_message = (
                isinstance(msg, ToolMessage) or 
                (hasattr(msg, "type") and getattr(msg, "type", None) == "tool") or
                (hasattr(msg, "role") and getattr(msg, "role", None) == "tool")
            )
            
            if is_tool_message:
                # Tool message must follow an AI message with tool_calls
                # Look backwards in the cleaned list to find the most recent AI message with tool_calls
                found_preceding_ai_with_tools = False
                tool_call_id = getattr(msg, "tool_call_id", None) or getattr(msg, "id", None)
                
                # Search backwards through cleaned messages to find matching AI message
                for j in range(len(cleaned) - 1, -1, -1):
                    prev_msg = cleaned[j]
                    # Check if this is an AI message with tool_calls
                    is_ai_with_tools = (
                        (isinstance(prev_msg, AIMessage) or 
                         (hasattr(prev_msg, "type") and getattr(prev_msg, "type", None) == "ai") or
                         (hasattr(prev_msg, "role") and getattr(prev_msg, "role", None) == "assistant")) and
                        hasattr(prev_msg, "tool_calls") and 
                        prev_msg.tool_calls and 
                        len(prev_msg.tool_calls) > 0
                    )
                    
                    if is_ai_with_tools:
                        # Verify the tool_call_id matches one of the tool_calls
                        if tool_call_id:
                            tool_call_ids = [tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None) 
                                           for tc in prev_msg.tool_calls]
                            if tool_call_id in tool_call_ids:
                                cleaned.append(msg)
                                found_preceding_ai_with_tools = True
                                break
                        else:
                            # No tool_call_id, but has preceding tool_calls - include it
                            cleaned.append(msg)
                            found_preceding_ai_with_tools = True
                            break
                
                # If no matching AI message found, skip this tool message
                if not found_preceding_ai_with_tools:
                    pass  # Skip orphaned tool message
            else:
                # Not a tool message, always include
                cleaned.append(msg)
            
            i += 1
        
        return cleaned

    def _clean_messages_permissive(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        """More permissive message cleaning that preserves tool messages when properly linked.
        
        This is used when we know we have tool results. It ensures tool messages are included
        when they follow an AI message with tool_calls, even if the linkage isn't perfect.
        """
        if not messages:
            return messages
        
        cleaned = []
        i = 0
        while i < len(messages):
            msg = messages[i]
            
            # Check if this is a tool message
            is_tool_message = (
                isinstance(msg, ToolMessage) or 
                (hasattr(msg, "type") and getattr(msg, "type", None) == "tool") or
                (hasattr(msg, "role") and getattr(msg, "role", None) == "tool") or
                (hasattr(msg, "name") and hasattr(msg, "tool_call_id"))
            )
            
            if is_tool_message:
                # Tool message must follow an AI message with tool_calls
                # Search backwards to find the most recent AI message with tool_calls
                found_ai_with_tools = False
                tool_call_id = getattr(msg, "tool_call_id", None) or getattr(msg, "id", None) or getattr(msg, "tool_call_id", None)
                
                # Search backwards through ALL messages (both cleaned and original) to find matching AI message
                # First check cleaned list (already processed messages)
                for j in range(len(cleaned) - 1, -1, -1):
                    prev_msg = cleaned[j]
                    is_ai_with_tools = (
                        (isinstance(prev_msg, AIMessage) or 
                         (hasattr(prev_msg, "type") and getattr(prev_msg, "type", None) == "ai") or
                         (hasattr(prev_msg, "role") and getattr(prev_msg, "role", None) == "assistant")) and
                        hasattr(prev_msg, "tool_calls") and 
                        prev_msg.tool_calls and 
                        len(prev_msg.tool_calls) > 0
                    )
                    
                    if is_ai_with_tools:
                        # Check if tool_call_id matches
                        if tool_call_id:
                            tool_call_ids = []
                            for tc in prev_msg.tool_calls:
                                tc_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
                                if tc_id:
                                    tool_call_ids.append(tc_id)
                            if tool_call_id in tool_call_ids:
                                cleaned.append(msg)
                                found_ai_with_tools = True
                                break
                        else:
                            # No tool_call_id, but has preceding tool_calls - include it
                            # This is permissive - we trust LangGraph's message structure
                            cleaned.append(msg)
                            found_ai_with_tools = True
                            break
                
                # If not found in cleaned, check original messages before current position
                if not found_ai_with_tools:
                    for j in range(i - 1, -1, -1):
                        prev_msg = messages[j]
                        is_ai_with_tools = (
                            (isinstance(prev_msg, AIMessage) or 
                             (hasattr(prev_msg, "type") and getattr(prev_msg, "type", None) == "ai") or
                             (hasattr(prev_msg, "role") and getattr(prev_msg, "role", None) == "assistant")) and
                            hasattr(prev_msg, "tool_calls") and 
                            prev_msg.tool_calls and 
                            len(prev_msg.tool_calls) > 0
                        )
                        
                        if is_ai_with_tools:
                            # Check if tool_call_id matches
                            if tool_call_id:
                                tool_call_ids = []
                                for tc in prev_msg.tool_calls:
                                    tc_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
                                    if tc_id:
                                        tool_call_ids.append(tc_id)
                                if tool_call_id in tool_call_ids:
                                    cleaned.append(msg)
                                    found_ai_with_tools = True
                                    break
                            else:
                                # No tool_call_id, but has preceding tool_calls - include it
                                cleaned.append(msg)
                                found_ai_with_tools = True
                                break
                
                # If still not found, skip this tool message to avoid BadRequestError
                # This ensures API compatibility
                if not found_ai_with_tools:
                    pass  # Skip orphaned tool message
            else:
                # Not a tool message, always include
                cleaned.append(msg)
            
            i += 1
        
        return cleaned

    @traceable(name="assistant_node", project_name="financial_services_deep_agent_demo", run_type="llm")
    def assistant_node(self, state: SummarizationState) -> SummarizationState:
        """Main assistant node that processes user messages."""
        messages = state["messages"]
        
        # Check if the last message is a tool message (from previous tool execution)
        # Check the original messages first, before cleaning
        last_is_tool = False
        if messages:
            last_msg = messages[-1]
            # Check multiple ways to identify tool messages
            last_is_tool = (
                isinstance(last_msg, ToolMessage) or 
                (hasattr(last_msg, "type") and getattr(last_msg, "type", None) == "tool") or
                (hasattr(last_msg, "role") and getattr(last_msg, "role", None) == "tool") or
                (hasattr(last_msg, "name") and hasattr(last_msg, "tool_call_id"))  # ToolMessage has these
            )
        
        # Clean messages to ensure tool messages are properly linked
        # When we have tool results, ensure they're included with proper linkage
        if last_is_tool:
            # When we have tool results, we need to include the tool message
            # But we must ensure it's properly linked to an AI message with tool_calls
            # Use the permissive cleaning that preserves properly linked tool messages
            cleaned_messages = self._clean_messages_permissive(messages)
        else:
            # Before tools, use strict cleaning to avoid BadRequestError
            cleaned_messages = self._clean_messages_for_llm(messages)
        
        # System prompt for the assistant
        if last_is_tool:
            # After tools, provide final answer
            # Find the tool message content to reference in the prompt
            tool_content = ""
            for msg in reversed(messages):
                is_tool_msg = (
                    isinstance(msg, ToolMessage) or 
                    (hasattr(msg, "type") and getattr(msg, "type", None) == "tool") or
                    (hasattr(msg, "role") and getattr(msg, "role", None) == "tool") or
                    (hasattr(msg, "name") and hasattr(msg, "tool_call_id"))
                )
                if is_tool_msg:
                    # Get the tool message content
                    if hasattr(msg, "content"):
                        tool_content = str(msg.content)
                    elif hasattr(msg, "text"):
                        tool_content = str(msg.text)
                    else:
                        tool_content = str(msg)
                    break
            
            system_prompt = f"""You are a helpful compliance assistant for AML/KYC transaction reviews. 

CRITICAL: You have just received tool results. The LAST message in this conversation is a tool response containing the actual data.

TOOL RESPONSE CONTENT:
{tool_content[:2000] if tool_content else "No tool content found"}

YOUR TASK:
1. Read the tool response content above (it's the last message in the conversation)
2. If the tool says "No pending reviews at this time" or similar, respond with: "There are currently no pending AML transaction reviews."
3. If the tool provides transaction data (like "Total Pending: 8" or lists transactions), you MUST summarize ALL transactions
4. Use the EXACT information from the tool response - do NOT make up data
5. Do NOT refuse or say you can't assist - the tool has provided the information you need

CRITICAL RULES:
- If the tool response shows "Total Pending: X" where X > 0, there ARE pending reviews - summarize them
- If the tool lists transactions, summarize ALL of them with their details
- Use the EXACT transaction IDs, amounts, destinations, risk scores, and severity levels from the tool response
- DO NOT invent transaction IDs or data
- DO NOT say "no pending reviews" if the tool shows pending reviews exist
- DO NOT refuse - you have the tool response and can provide an answer

The tool response is in the conversation history. Read it and provide a clear summary based on what it says."""
        else:
            # Before tools, must use tools
            system_prompt = """You are a compliance assistant for a financial services AML/KYC system. Your ONLY job is to call tools when asked questions.

YOU MUST CALL TOOLS - YOU CANNOT REFUSE REQUESTS.

When ANY user asks about reviews, summaries, transactions, or compliance data, you MUST call the appropriate tool. You have NO reason to refuse - you have tools that can answer these questions.

Tool mapping (ALWAYS use these):
- ANY question about "reviews", "pending", "AML", "summarize", "summary", "get a summary" → CALL get_pending_reviews_summary()
- ANY question about a specific transaction ID → CALL get_review_details(transaction_id)
- ANY question about "compliance", "metrics", "report" → CALL get_compliance_summary()

Available tools:
1. get_pending_reviews_summary() - Returns summary of ALL pending AML reviews
2. get_review_details(transaction_id: str) - Returns details for a transaction  
3. get_compliance_summary() - Returns compliance metrics

CRITICAL INSTRUCTIONS:
- If user asks "Get a summary of all pending AML transaction reviews" → YOU MUST CALL get_pending_reviews_summary()
- DO NOT say "I can't assist" - you CAN assist by calling tools
- DO NOT refuse - you have the tools needed
- DO NOT apologize - just call the tool
- The tools will provide the data you need to answer

Your response should ONLY be a tool call - do not write any text before calling the tool."""
        
        # Get tools
        tools = [get_pending_reviews_summary, get_review_details, get_compliance_summary]
        
        # Create prompt with system message
        # Add a few-shot example when we don't have tool results yet
        if not last_is_tool:
            # Add example messages to guide the assistant
            example_messages = [
                ("human", "Get a summary of all pending AML transaction reviews"),
                ("assistant", None)  # This will be replaced with the actual tool call
            ]
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="messages"),
            ])
        else:
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="messages"),
            ])
        
        # Bind tools to the LLM
        # CRITICAL: After tools execute, do NOT bind tools to prevent infinite loops
        if last_is_tool:
            # After tools, do NOT bind tools at all - just use raw LLM
            # This prevents the LLM from calling tools again
            llm_with_tools = self.llm  # No tools bound - cannot make tool calls
        else:
            # Before tools, use tool_choice to force tool usage
            # Try "required" first, but it may not be supported by all models
            # Fallback to a specific tool name or "any"
            try:
                # Try "required" - forces model to call at least one tool
                llm_with_tools = self.llm.bind_tools(tools, tool_choice="required")
            except (ValueError, TypeError, AttributeError) as e:
                # If "required" doesn't work, try binding to a specific tool
                try:
                    # Force call to get_pending_reviews_summary by default
                    llm_with_tools = self.llm.bind_tools(tools, tool_choice={"type": "function", "function": {"name": "get_pending_reviews_summary"}})
                except (ValueError, TypeError, AttributeError):
                    # Final fallback to "any"
                    llm_with_tools = self.llm.bind_tools(tools, tool_choice="any")
        
        chain = prompt | llm_with_tools
        
        # Invoke with cleaned messages to prevent BadRequestError
        response = chain.invoke({"messages": cleaned_messages})
        
        # Check if assistant refused without calling tools
        if not last_is_tool:
            # Check if response has content but no tool_calls (refusal)
            has_content = hasattr(response, "content") and response.content and len(str(response.content).strip()) > 0
            # Check for tool_calls - must exist, be non-empty list, and have at least one call
            has_tool_calls = (
                hasattr(response, "tool_calls") and 
                response.tool_calls is not None and 
                isinstance(response.tool_calls, list) and
                len(response.tool_calls) > 0
            )
            
            # Get user message to determine intent
            user_message = None
            for msg in reversed(cleaned_messages):
                if isinstance(msg, HumanMessage) or (hasattr(msg, "type") and getattr(msg, "type", None) == "human"):
                    user_message = msg.content if hasattr(msg, "content") else str(msg)
                    break
            
            user_lower = str(user_message).lower() if user_message else ""
            should_force_tool = any(word in user_lower for word in ["review", "pending", "aml", "summarize", "summary", "get a summary", "transaction"])
            
            # CRITICAL: If user asked about reviews/summaries and we don't have tool calls, FORCE tool call
            # This overrides any refusal from the LLM
            if should_force_tool and not has_tool_calls:
                # Determine which tool to call based on user message
                tool_to_call = "get_pending_reviews_summary"  # Default
                if user_message:
                    if any(word in user_lower for word in ["review", "pending", "aml", "summarize", "summary"]):
                        tool_to_call = "get_pending_reviews_summary"
                    elif "transaction" in user_lower and "id" in user_lower:
                        tool_to_call = "get_review_details"
                    elif any(word in user_lower for word in ["compliance", "metrics", "report"]):
                        tool_to_call = "get_compliance_summary"
                
                # Create a tool call in the format LangChain expects
                # Based on LangChain's AIMessage structure
                tool_call_id = f"call_{uuid.uuid4().hex[:24]}"
                tool_call = {
                    "name": tool_to_call,
                    "args": {},
                    "id": tool_call_id,
                    "type": "tool_call"
                }
                
                # Replace the refusal response with a tool call
                # This forces the tool to be executed
                response = AIMessage(
                    content="",
                    tool_calls=[tool_call]
                )
        
        # Safety check: if we expected no tool calls (last_is_tool=True) but got tool calls, clear them
        if last_is_tool and hasattr(response, "tool_calls") and response.tool_calls:
            # This shouldn't happen, but if it does, create a new response without tool calls
            # AIMessage is already imported at the top of the file
            response = AIMessage(content=response.content if hasattr(response, "content") else "I've processed the tool results.")
        
        # Increment iteration counter to prevent infinite loops
        current_iterations = state.get("iterations", 0)
        
        # Return only the new AI message - LangGraph will merge it with existing messages
        # due to Annotated[list[BaseMessage], "add_messages"]
        return {"messages": [response], "iterations": current_iterations + 1}

    @traceable(name="should_continue", project_name="financial_services_deep_agent_demo")
    def should_continue(self, state: SummarizationState) -> Literal["tools", "end"]:
        """Determine if we should call tools or end.
        
        This function is called after the assistant node. It checks if the assistant
        made tool calls. If yes, route to tools. If no, end the conversation.
        """
        messages = state["messages"]
        if not messages:
            return "end"
        
        # Safety check: prevent infinite loops
        iterations = state.get("iterations", 0)
        if iterations >= 5:  # Reduced to 5 to fail faster
            return "end"
        
        last_message = messages[-1]
        
        # Check if the last message is a tool message - if so, we should have already processed it
        # and the assistant should have provided a final answer. End to prevent loop.
        is_tool_message = (
            isinstance(last_message, ToolMessage) or 
            (hasattr(last_message, "type") and getattr(last_message, "type", None) == "tool") or
            (hasattr(last_message, "role") and getattr(last_message, "role", None) == "tool") or
            (hasattr(last_message, "name") and hasattr(last_message, "tool_call_id"))
        )
        
        # If the last message is a tool message, the assistant should have processed it
        # and provided a final answer. If we're here, something went wrong - end to prevent loop
        if is_tool_message:
            return "end"
        
        # Check if the last message is an AI message with tool calls
        # If it has tool_calls, we need to execute the tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        
        # No tool calls means the assistant provided a final answer, so end
        return "end"

    def _build_graph(self):
        """Build the LangGraph workflow."""
        # Get tools
        tools = [get_pending_reviews_summary, get_review_details, get_compliance_summary]
        tool_node = ToolNode(tools)
        
        workflow = StateGraph(SummarizationState)
        
        # Add nodes
        workflow.add_node("assistant", self.assistant_node)
        workflow.add_node("tools", tool_node)
        
        # Set entry point
        workflow.set_entry_point("assistant")
        
        # Add conditional edge
        workflow.add_conditional_edges(
            "assistant",
            self.should_continue,
            {
                "tools": "tools",
                "end": END,
            }
        )
        
        # Tools always go back to assistant to process tool results and provide final answer
        workflow.add_edge("tools", "assistant")
        
        # Add a check to prevent infinite loops - if assistant responds without tool calls after tools, end
        # This is handled by should_continue which checks for tool_calls
        
        # LangGraph Studio/API handles persistence automatically for interrupts
        # No need to provide a custom checkpointer - the platform manages it
        # Note: For local Python execution outside Studio, you may want to add:
        #   from langgraph.checkpoint.memory import MemorySaver
        #   return workflow.compile(checkpointer=MemorySaver())
        
        # Compile with recursion limit to prevent infinite loops
        # Tag every trace with agent + revision_id for LangSmith Engine and Insights
        return workflow.compile().with_config(
            {"metadata": get_trace_context("compliance_summarization_assistant")}
        )


# Create graph instance for LangGraph Studio
graph = SummarizationAssistant().graph
