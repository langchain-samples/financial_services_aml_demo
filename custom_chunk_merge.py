"""
Custom merging function for AIMessageChunk that handles additional_kwargs correctly.

The default AIMessageChunk.concat() method incorrectly merges additional_kwargs:
- Strings are concatenated (e.g., "assistant" + "assistant" = "assistantassistant")
- Numbers are added (e.g., 1734524005 + 1734524005 = 3469048010)

This module provides a custom merge function that allows you to control how
additional_kwargs fields are merged.
"""

from typing import Any, Dict, Optional, Callable
from langchain_core.messages import AIMessageChunk


def custom_merge_chunks(
    chunks: list[AIMessageChunk],
    additional_kwargs_merge_strategy: Optional[Dict[str, Callable[[Any, Any], Any]]] = None,
    default_strategy: str = "last"  # "last", "first", "skip"
) -> AIMessageChunk:
    """
    Merge multiple AIMessageChunk objects with custom handling for additional_kwargs.
    
    Args:
        chunks: List of AIMessageChunk objects to merge
        additional_kwargs_merge_strategy: Dict mapping field names to merge functions.
            Each function receives (existing_value, new_value) and returns the merged value.
        default_strategy: Default strategy for fields not in additional_kwargs_merge_strategy.
            Options: "last" (keep last value), "first" (keep first value), "skip" (don't merge)
    
    Returns:
        Merged AIMessageChunk
    
    Example:
        >>> chunks = [
        ...     AIMessageChunk(content="Hello", additional_kwargs={"role": "assistant", "created": 1734524005}),
        ...     AIMessageChunk(content=" World", additional_kwargs={"role": "assistant", "created": 1734524005}),
        ... ]
        >>> merged = custom_merge_chunks(
        ...     chunks,
        ...     additional_kwargs_merge_strategy={
        ...         "role": lambda old, new: new,  # Keep last value
        ...         "created": lambda old, new: new,  # Keep last value
        ...     }
        ... )
        >>> merged.content
        'Hello World'
        >>> merged.additional_kwargs["role"]
        'assistant'  # Not "assistantassistant"
        >>> merged.additional_kwargs["created"]
        1734524005  # Not 3469048010
    """
    if not chunks:
        raise ValueError("Cannot merge empty list of chunks")
    
    if len(chunks) == 1:
        return chunks[0]
    
    # Manually merge content to avoid issues with additional_kwargs
    merged_content = ""
    for chunk in chunks:
        if chunk.content:
            merged_content += chunk.content
    
    # Merge other fields that work correctly with default concat
    # We'll use the last chunk's metadata as base, but merge properly
    base_chunk = chunks[-1]
    
    # Now handle additional_kwargs with our custom strategy
    merged_kwargs: Dict[str, Any] = {}
    
    # Collect all unique keys from all chunks
    all_keys = set()
    for chunk in chunks:
        if chunk.additional_kwargs:
            all_keys.update(chunk.additional_kwargs.keys())
    
    # Merge each key according to strategy
    for key in all_keys:
        values = [
            chunk.additional_kwargs.get(key)
            for chunk in chunks
            if chunk.additional_kwargs and key in chunk.additional_kwargs
        ]
        
        if not values:
            continue
        
        # Use custom strategy if provided
        if additional_kwargs_merge_strategy and key in additional_kwargs_merge_strategy:
            merge_func = additional_kwargs_merge_strategy[key]
            # Apply merge function sequentially
            result = values[0]
            for value in values[1:]:
                result = merge_func(result, value)
            merged_kwargs[key] = result
        else:
            # Use default strategy
            if default_strategy == "last":
                merged_kwargs[key] = values[-1]
            elif default_strategy == "first":
                merged_kwargs[key] = values[0]
            elif default_strategy == "skip":
                # Don't include in merged kwargs
                continue
            else:
                raise ValueError(f"Unknown default_strategy: {default_strategy}")
    
    # Merge tool_calls and tool_call_chunks (use last chunk's values, or merge if needed)
    # For most cases, tool calls appear in the last chunk
    merged_tool_calls = base_chunk.tool_calls
    merged_tool_call_chunks = base_chunk.tool_call_chunks
    merged_invalid_tool_calls = base_chunk.invalid_tool_calls
    
    # Merge response_metadata (keep last, or merge dicts)
    merged_response_metadata = base_chunk.response_metadata or {}
    for chunk in chunks[:-1]:
        if chunk.response_metadata:
            merged_response_metadata = {**merged_response_metadata, **chunk.response_metadata}
    
    # Merge usage_metadata (typically only in last chunk, but merge if present)
    merged_usage_metadata = base_chunk.usage_metadata
    
    # Create new chunk with correctly merged fields
    return AIMessageChunk(
        content=merged_content,
        additional_kwargs=merged_kwargs,
        response_metadata=merged_response_metadata,
        id=chunks[0].id,  # Use first chunk's ID
        usage_metadata=merged_usage_metadata,
        tool_calls=merged_tool_calls,
        tool_call_chunks=merged_tool_call_chunks,
        invalid_tool_calls=merged_invalid_tool_calls,
    )


def merge_chunks_simple(
    chunks: list[AIMessageChunk],
    keep_last_for_fields: Optional[list[str]] = None
) -> AIMessageChunk:
    """
    Simplified merge function that keeps the last value for specified fields.
    
    This is a convenience wrapper around custom_merge_chunks.
    
    Args:
        chunks: List of AIMessageChunk objects to merge
        keep_last_for_fields: List of field names in additional_kwargs that should
            keep the last value (default: None means keep last for all fields)
    
    Returns:
        Merged AIMessageChunk
    
    Example:
        >>> chunks = [
        ...     AIMessageChunk(content="Hello", additional_kwargs={"role": "assistant", "created": 1734524005}),
        ...     AIMessageChunk(content=" World", additional_kwargs={"role": "assistant", "created": 1734524005}),
        ... ]
        >>> merged = merge_chunks_simple(chunks, keep_last_for_fields=["role", "created"])
        >>> merged.content
        'Hello World'
        >>> merged.additional_kwargs["role"]
        'assistant'
    """
    if keep_last_for_fields is None:
        # Keep last for all fields by default
        strategy = {}
        default = "last"
    else:
        # Keep last for specified fields, skip others
        strategy = {
            field: lambda old, new: new
            for field in keep_last_for_fields
        }
        default = "skip"
    
    return custom_merge_chunks(
        chunks,
        additional_kwargs_merge_strategy=strategy,
        default_strategy=default
    )


# Example usage and testing
if __name__ == "__main__":
    from langchain_core.messages import AIMessageChunk
    
    # Create test chunks with problematic additional_kwargs
    chunk1 = AIMessageChunk(
        content="Hello",
        additional_kwargs={
            "role": "assistant",
            "created": 1734524005,
            "custom_field": "value1"
        }
    )
    
    chunk2 = AIMessageChunk(
        content=" World",
        additional_kwargs={
            "role": "assistant",  # Same value - should stay "assistant", not "assistantassistant"
            "created": 1734524005,  # Same value - should stay 1734524005, not 3469048010
            "custom_field": "value2"  # Different value - should keep last
        }
    )
    
    # Test default concat (shows the problem)
    print("=== Default concat() behavior (PROBLEMATIC) ===")
    default_merged = chunk1 + chunk2
    print(f"Content: {default_merged.content}")
    print(f"Role: {default_merged.additional_kwargs.get('role')}")
    print(f"Created: {default_merged.additional_kwargs.get('created')}")
    print(f"Custom field: {default_merged.additional_kwargs.get('custom_field')}")
    print()
    
    # Test custom merge (solution)
    print("=== Custom merge behavior (CORRECT) ===")
    custom_merged = custom_merge_chunks(
        [chunk1, chunk2],
        additional_kwargs_merge_strategy={
            "role": lambda old, new: new,  # Keep last
            "created": lambda old, new: new,  # Keep last
            "custom_field": lambda old, new: new,  # Keep last
        },
        default_strategy="last"
    )
    print(f"Content: {custom_merged.content}")
    print(f"Role: {custom_merged.additional_kwargs.get('role')}")
    print(f"Created: {custom_merged.additional_kwargs.get('created')}")
    print(f"Custom field: {custom_merged.additional_kwargs.get('custom_field')}")
    print()
    
    # Test simplified merge
    print("=== Simplified merge (keep last for all) ===")
    simple_merged = merge_chunks_simple([chunk1, chunk2])
    print(f"Content: {simple_merged.content}")
    print(f"Role: {simple_merged.additional_kwargs.get('role')}")
    print(f"Created: {simple_merged.additional_kwargs.get('created')}")
    print(f"Custom field: {simple_merged.additional_kwargs.get('custom_field')}")
