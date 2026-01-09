# AIMessageChunk.concat() Merge Issue Guide

## Problem

The `AIMessageChunk.concat()` method (or `+` operator) makes incorrect assumptions when merging `additional_kwargs` fields:

1. **String fields are concatenated**: 
   - `"role": "assistant"` + `"role": "assistant"` → `"role": "assistantassistant"` ❌
   - Should be: `"role": "assistant"` ✅

2. **Number fields are added**:
   - `"created": 1734524005` + `"created": 1734524005` → `"created": 3469048010` ❌
   - Should be: `"created": 1734524005` ✅

## Why This Happens

The `concat()` method uses generic merge logic that:
- Concatenates strings (assuming they're content to append)
- Adds numbers (assuming they're counters or accumulators)
- Doesn't know the semantic meaning of fields in `additional_kwargs`

## Solutions

### Solution 1: Custom Merge Function (Recommended)

Use the `custom_merge_chunks()` function from `custom_chunk_merge.py`:

```python
from custom_chunk_merge import custom_merge_chunks
from langchain_core.messages import AIMessageChunk

chunks = [chunk1, chunk2, chunk3]

merged = custom_merge_chunks(
    chunks,
    additional_kwargs_merge_strategy={
        "role": lambda old, new: new,  # Keep last value
        "created": lambda old, new: new,  # Keep last value
        # Add custom logic for other fields
    },
    default_strategy="last"  # "last", "first", or "skip"
)
```

### Solution 2: Simplified Merge Function

For simple cases where you just want to keep the last value:

```python
from custom_chunk_merge import merge_chunks_simple

merged = merge_chunks_simple(
    chunks,
    keep_last_for_fields=["role", "created", "timestamp"]
)
```

### Solution 3: Manual Merge During Streaming

Merge chunks manually as you receive them:

```python
merged_chunk: AIMessageChunk | None = None

async for chunk in model.astream("Your prompt"):
    if merged_chunk is None:
        merged_chunk = chunk
    else:
        # Merge content (this works correctly)
        merged_content = merged_chunk.content + chunk.content
        
        # Manually merge additional_kwargs (keep last values)
        merged_kwargs = {}
        for c in [merged_chunk, chunk]:
            if c.additional_kwargs:
                merged_kwargs.update(c.additional_kwargs)
        
        # Create new chunk
        merged_chunk = AIMessageChunk(
            content=merged_content,
            additional_kwargs=merged_kwargs,
            response_metadata=chunk.response_metadata,
            id=merged_chunk.id,
            usage_metadata=chunk.usage_metadata,
        )
```

### Solution 4: Post-Process After Merging

If you've already merged chunks incorrectly, you can fix the `additional_kwargs`:

```python
# After using default concat()
merged = chunk1 + chunk2

# Fix additional_kwargs
fixed_kwargs = {}
for chunk in [chunk1, chunk2]:
    if chunk.additional_kwargs:
        # Keep last value for each field
        fixed_kwargs.update(chunk.additional_kwargs)

merged.additional_kwargs = fixed_kwargs
```

## Common Merge Strategies

### Keep Last Value (Most Common)
```python
"field_name": lambda old, new: new
```

### Keep First Value
```python
"field_name": lambda old, new: old
```

### Merge Lists
```python
"field_name": lambda old, new: old + new if isinstance(old, list) else [old, new]
```

### Merge Dicts
```python
"field_name": lambda old, new: {**old, **new} if isinstance(old, dict) else new
```

### Custom Logic
```python
"field_name": lambda old, new: (
    new if isinstance(new, str) and len(new) > len(str(old)) else old
)
```

## Best Practices

1. **Identify problematic fields**: Check which fields in `additional_kwargs` have the same value across chunks (like `role`, `created`, etc.)

2. **Use custom merge for streaming**: When streaming, use custom merge from the start rather than fixing afterwards

3. **Document your merge strategy**: Keep track of which fields need special handling

4. **Test with real data**: Verify that your merge strategy works with actual streaming output

## Example: Complete Streaming Workflow

```python
from langchain_openai import ChatOpenAI
from custom_chunk_merge import merge_chunks_simple

model = ChatOpenAI(model="gpt-4o")

# Stream and merge correctly
merged_chunk: AIMessageChunk | None = None

async for chunk in model.astream("Your prompt here"):
    if merged_chunk is None:
        merged_chunk = chunk
    else:
        # Use custom merge instead of default concat()
        merged_chunk = merge_chunks_simple(
            [merged_chunk, chunk],
            keep_last_for_fields=["role", "created", "timestamp"]
        )
    
    # Display content as it streams
    if chunk.content:
        print(chunk.content, end="", flush=True)

# Final merged chunk has correct additional_kwargs
print(f"\nRole: {merged_chunk.additional_kwargs.get('role')}")
print(f"Created: {merged_chunk.additional_kwargs.get('created')}")
```

## When to Use Each Solution

- **Solution 1 (Custom Merge)**: When you need fine-grained control over multiple fields
- **Solution 2 (Simple Merge)**: When you just want to keep last values for specific fields
- **Solution 3 (Manual Merge)**: When you're streaming and want to merge incrementally
- **Solution 4 (Post-Process)**: When you've already merged incorrectly and need to fix it

## Related Issues

- [LangChain GitHub Issue #24377](https://github.com/langchain-ai/langchain/issues/24377) - Discussion about merging tool calls in AIMessageChunk

## Files in This Repository

- `custom_chunk_merge.py` - Custom merge functions
- `streaming_chunks_example.py` - Practical examples
- `AIMESSAGE_CHUNK_MERGE_GUIDE.md` - This guide
