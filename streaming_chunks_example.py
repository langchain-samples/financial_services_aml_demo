"""
Example: Streaming message chunks with custom merge handling.

This demonstrates how to properly merge AIMessageChunk objects during streaming
when you have fields in additional_kwargs that shouldn't be concatenated or added.
"""

from langchain_core.messages import AIMessageChunk
from langchain_openai import ChatOpenAI
from custom_chunk_merge import custom_merge_chunks, merge_chunks_simple


async def stream_with_custom_merge_example():
    """
    Example of streaming with custom merge logic for additional_kwargs.
    """
    model = ChatOpenAI(model="gpt-4o")
    
    # Stream chunks
    chunks = []
    async for chunk in model.astream("Tell me a short joke"):
        chunks.append(chunk)
        print(chunk.content, end="", flush=True)
    
    print("\n\n=== Merging chunks ===")
    
    # Option 1: Use custom merge with specific strategies
    merged = custom_merge_chunks(
        chunks,
        additional_kwargs_merge_strategy={
            # For string fields like "role", keep the last value
            "role": lambda old, new: new,
            # For timestamp fields, keep the last value
            "created": lambda old, new: new,
            # For any other fields you care about, define custom logic
            # "some_list": lambda old, new: old + new if isinstance(old, list) else [old, new],
        },
        default_strategy="last"  # For fields not specified above, keep last value
    )
    
    print(f"Merged content: {merged.content}")
    print(f"Additional kwargs: {merged.additional_kwargs}")
    
    return merged


async def stream_with_simple_merge_example():
    """
    Simplified example using the convenience function.
    """
    model = ChatOpenAI(model="gpt-4o")
    
    # Stream and merge incrementally
    merged_chunk: AIMessageChunk | None = None
    
    async for chunk in model.astream("What is 2+2?"):
        if merged_chunk is None:
            merged_chunk = chunk
        else:
            # Use simple merge that keeps last value for all additional_kwargs fields
            merged_chunk = merge_chunks_simple(
                [merged_chunk, chunk],
                keep_last_for_fields=["role", "created"]  # Specify fields to keep last
            )
        print(chunk.content, end="", flush=True)
    
    print(f"\n\nFinal merged chunk:")
    print(f"Content: {merged_chunk.content}")
    print(f"Additional kwargs: {merged_chunk.additional_kwargs}")
    
    return merged_chunk


async def stream_manual_merge_example():
    """
    Manual merge example - full control over the process.
    """
    model = ChatOpenAI(model="gpt-4o")
    
    all_chunks = []
    async for chunk in model.astream("Count to 3"):
        all_chunks.append(chunk)
        print(chunk.content, end="", flush=True)
    
    print("\n\n=== Manual merge ===")
    
    # Manually merge content
    merged_content = "".join(chunk.content for chunk in all_chunks if chunk.content)
    
    # Manually handle additional_kwargs
    merged_kwargs = {}
    for chunk in all_chunks:
        if chunk.additional_kwargs:
            for key, value in chunk.additional_kwargs.items():
                # Strategy: keep last value for all fields
                merged_kwargs[key] = value
    
    # Create final merged chunk
    final_chunk = AIMessageChunk(
        content=merged_content,
        additional_kwargs=merged_kwargs,
        response_metadata=all_chunks[-1].response_metadata if all_chunks else {},
        id=all_chunks[0].id if all_chunks else None,
        usage_metadata=all_chunks[-1].usage_metadata if all_chunks else None,
        tool_calls=all_chunks[-1].tool_calls if all_chunks else None,
    )
    
    print(f"Final chunk content: {final_chunk.content}")
    print(f"Final additional_kwargs: {final_chunk.additional_kwargs}")
    
    return final_chunk


if __name__ == "__main__":
    import asyncio
    
    print("=== Example 1: Custom merge with strategies ===")
    asyncio.run(stream_with_custom_merge_example())
    
    print("\n\n=== Example 2: Simple merge ===")
    asyncio.run(stream_with_simple_merge_example())
    
    print("\n\n=== Example 3: Manual merge ===")
    asyncio.run(stream_manual_merge_example())
