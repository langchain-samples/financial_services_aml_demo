"""
Test script to debug MCP runtime context issue.

This script tests the MCP interceptor with runtime context access.
"""

from dataclasses import dataclass
from typing import Optional
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI


@dataclass
class Context:
    user_id: str
    api_key: str


async def inject_user_context(
    request: MCPToolCallRequest,
    handler,
):
    """Inject user credentials into MCP tool calls."""
    print(f"DEBUG: request.runtime = {request.runtime}")
    print(f"DEBUG: request.runtime type = {type(request.runtime)}")
    
    # Check if runtime is None
    if request.runtime is None:
        print("WARNING: request.runtime is None!")
        # Workaround: Try to get context from request.args or raise an error
        # You might need to pass context differently
        raise ValueError(
            "Runtime context is not available. "
            "Ensure you're passing context correctly in ainvoke(). "
            "Try using config={'context': {...}} instead of context={...}"
        )
    
    runtime = request.runtime
    print(f"DEBUG: runtime.context = {runtime.context}")
    
    # Access context attributes
    try:
        user_id = runtime.context.user_id
        api_key = runtime.context.api_key
        print(f"DEBUG: user_id = {user_id}, api_key = {api_key[:10]}...")
    except AttributeError as e:
        print(f"ERROR accessing context: {e}")
        raise
    
    # Add user context to tool arguments
    modified_request = request.override(
        args={**request.args, "user_id": user_id, "api_key": api_key}
    )
    return await handler(modified_request)


# Example usage
async def main():
    # Create MCP client with interceptor
    client = MultiServerMCPClient(
        {
            "my_server": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"],
            }
        },
        tool_interceptors=[inject_user_context],
    )
    
    # Get tools from MCP client
    tools = await client.get_tools()
    
    # Create agent with context schema
    agent = create_agent(
        "gpt-4o",
        tools,
        context_schema=Context
    )
    
    # Try different ways to pass context
    print("\n=== Testing Method 1: context parameter ===")
    try:
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": "List files"}]},
            context={"user_id": "user_123", "api_key": "sk-..."}
        )
        print("SUCCESS with context parameter")
    except Exception as e:
        print(f"FAILED with context parameter: {e}")
    
    print("\n=== Testing Method 2: config with context ===")
    try:
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": "List files"}]},
            config={"context": {"user_id": "user_123", "api_key": "sk-..."}}
        )
        print("SUCCESS with config['context']")
    except Exception as e:
        print(f"FAILED with config['context']: {e}")
    
    print("\n=== Testing Method 3: RunnableConfig format ===")
    from langchain_core.runnables import RunnableConfig
    try:
        config = RunnableConfig(
            configurable={"context": {"user_id": "user_123", "api_key": "sk-..."}}
        )
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": "List files"}]},
            config=config
        )
        print("SUCCESS with RunnableConfig")
    except Exception as e:
        print(f"FAILED with RunnableConfig: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
