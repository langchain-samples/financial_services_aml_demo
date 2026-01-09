# MCP Runtime Context Fix

## Problem

When using MCP tool interceptors with `create_agent`, `request.runtime` is `None` even though context is provided in `ainvoke()`.

## Root Cause

The runtime context is only available when tools are executed through LangGraph's runtime system. The context needs to be passed correctly, and the agent must be using the proper execution flow.

## Solution 1: Correct Context Passing (Recommended)

The context should be passed as a **separate keyword argument** to `ainvoke()`, not as part of the input dict or config:

```python
from dataclasses import dataclass
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from langchain.agents import create_agent

@dataclass
class Context:
    user_id: str
    api_key: str

async def inject_user_context(
    request: MCPToolCallRequest,
    handler,
):
    """Inject user credentials into MCP tool calls."""
    # Runtime should be available when executed through create_agent
    if request.runtime is None:
        raise ValueError(
            "Runtime context not available. "
            "Ensure tools are executed through create_agent."
        )
    
    runtime = request.runtime
    user_id = runtime.context.user_id
    api_key = runtime.context.api_key

    # Add user context to tool arguments or headers
    modified_request = request.override(
        args={**request.args, "user_id": user_id, "api_key": api_key}
    )
    return await handler(modified_request)

client = MultiServerMCPClient(
    {...},
    tool_interceptors=[inject_user_context],
)
tools = await client.get_tools()
agent = create_agent("gpt-4o", tools, context_schema=Context)

# CORRECT: Pass context as a keyword argument
result = await agent.ainvoke(
    {"messages": [{"role": "user", "content": "Search my orders"}]},
    context=Context(user_id="user_123", api_key="sk-...")
)
```

## Solution 2: Workaround with Config (If Solution 1 doesn't work)

If the runtime is still None, you can access context from the config:

```python
async def inject_user_context(
    request: MCPToolCallRequest,
    handler,
):
    """Inject user credentials into MCP tool calls."""
    # Try to get context from runtime first
    if request.runtime is not None:
        runtime = request.runtime
        user_id = runtime.context.user_id
        api_key = runtime.context.api_key
    else:
        # Fallback: Try to get from config
        # Note: This is a workaround and may not work in all cases
        config = getattr(request, 'config', None)
        if config and hasattr(config, 'configurable'):
            context = config.configurable.get('context', {})
            user_id = context.get('user_id')
            api_key = context.get('api_key')
        else:
            raise ValueError("Cannot access context - runtime is None and no config available")
    
    # Add user context to tool arguments
    modified_request = request.override(
        args={**request.args, "user_id": user_id, "api_key": api_key}
    )
    return await handler(modified_request)
```

## Solution 3: Pass Context via Tool Arguments (Alternative)

If runtime context is not available, you can pass the context through the agent's state or messages:

```python
async def inject_user_context(
    request: MCPToolCallRequest,
    handler,
):
    """Inject user credentials into MCP tool calls."""
    # If runtime is None, try to extract from tool args or state
    if request.runtime is None:
        # Check if context was passed via args
        user_id = request.args.get("_user_id")
        api_key = request.args.get("_api_key")
        
        if not user_id or not api_key:
            raise ValueError(
                "Runtime context not available and context not found in args. "
                "Ensure context is passed correctly to agent.ainvoke()"
            )
    else:
        runtime = request.runtime
        user_id = runtime.context.user_id
        api_key = runtime.context.api_key

    # Add user context to tool arguments
    modified_request = request.override(
        args={**request.args, "user_id": user_id, "api_key": api_key}
    )
    return await handler(modified_request)
```

## Debugging Steps

1. **Check LangChain version**: Ensure you're using a recent version that supports runtime context:
   ```bash
   pip install --upgrade langchain langchain-core langchain-mcp-adapters
   ```

2. **Verify agent creation**: Make sure you're using `create_agent` from `langchain.agents`, not a custom implementation.

3. **Check context schema**: The `context_schema` must match the dataclass/type you're passing:
   ```python
   # Context schema must match the type
   agent = create_agent("gpt-4o", tools, context_schema=Context)
   
   # Pass matching type
   result = await agent.ainvoke(
       {"messages": [...]},
       context=Context(user_id="...", api_key="...")  # Must be Context instance
   )
   ```

4. **Add debug logging**:
   ```python
   async def inject_user_context(request, handler):
       print(f"Runtime: {request.runtime}")
       print(f"Runtime type: {type(request.runtime)}")
       if request.runtime:
           print(f"Context: {request.runtime.context}")
       # ... rest of code
   ```

## Known Issues

- Runtime context may be `None` if tools are executed outside of LangGraph's runtime
- Some versions of `langchain-mcp-adapters` may have bugs with runtime context propagation
- Context must be passed as a dataclass instance, not a dict

## References

- [LangChain MCP Documentation](https://docs.langchain.com/oss/python/langchain/mcp#accessing-runtime-context)
- [LangGraph Runtime Context](https://docs.langchain.com/oss/python/langchain/runtime)
