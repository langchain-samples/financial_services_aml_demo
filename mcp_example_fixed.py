"""
Fixed example of MCP interceptor with runtime context.

This shows the correct way to pass context to access it in MCP interceptors.
"""

from dataclasses import dataclass
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
    # Debug: Check if runtime is available
    if request.runtime is None:
        raise ValueError(
            "Runtime context is None. This can happen if:\n"
            "1. Context is not passed correctly to agent.ainvoke()\n"
            "2. Tools are not executed through create_agent's runtime\n"
            "3. Version mismatch in langchain-mcp-adapters\n\n"
            "Try:\n"
            "- Pass context as: context=Context(user_id='...', api_key='...')\n"
            "- Ensure you're using the latest versions of langchain and langchain-mcp-adapters"
        )
    
    runtime = request.runtime
    
    # Access context attributes
    try:
        user_id = runtime.context.user_id
        api_key = runtime.context.api_key
    except AttributeError as e:
        raise ValueError(
            f"Could not access context attributes: {e}\n"
            f"Runtime context type: {type(runtime.context)}\n"
            f"Runtime context value: {runtime.context}"
        ) from e

    # Add user context to tool arguments
    # You can also add headers if your MCP server supports them
    modified_request = request.override(
        args={**request.args, "user_id": user_id, "api_key": api_key}
    )
    
    # If you need to add auth headers to the HTTP request:
    # You might need to modify the client configuration instead
    # or use a custom transport that adds headers
    
    return await handler(modified_request)


async def main():
    """Example usage of MCP client with context injection."""
    
    # Create MCP client with interceptor
    client = MultiServerMCPClient(
        {
            "my_server": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            }
        },
        tool_interceptors=[inject_user_context],
    )
    
    # Get tools from MCP client
    tools = await client.get_tools()
    
    # Create agent with context schema
    # IMPORTANT: Use the dataclass type, not an instance
    agent = create_agent(
        ChatOpenAI(model="gpt-4o"),
        tools,
        context_schema=Context  # Pass the type, not an instance
    )
    
    # Invoke with user context
    # IMPORTANT: Pass context as a dataclass instance
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "List files in /tmp"}]},
        context=Context(user_id="user_123", api_key="sk-...")  # Pass instance
    )
    
    print(result)
    return result


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
