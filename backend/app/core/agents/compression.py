"""Context compression for agent conversations.

Implements two-tier compression:
1. Microcompact: Fast removal of old tool results, keeps last 3 exchanges
2. Compact: Full LLM-based summarization with transcript persistence
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.models.transcript import Transcript


class ContextCompressor:
    """Compresses agent conversation context to prevent token overflow."""

    # Default token threshold (80k tokens for 128k context window with safety margin)
    DEFAULT_THRESHOLD = 80000

    # Approximate tokens per character (rough heuristic)
    TOKENS_PER_CHAR = 0.25

    def __init__(self, token_threshold: int = DEFAULT_THRESHOLD):
        self.token_threshold = token_threshold

    def estimate_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Estimate token count using JSON size heuristic.

        Uses a simple approximation: ~4 chars per token on average.
        This is fast and sufficient for threshold checking.
        """
        if not messages:
            return 0

        # Serialize messages to JSON and estimate tokens
        try:
            json_str = json.dumps(messages, ensure_ascii=False)
            return int(len(json_str) * self.TOKENS_PER_CHAR)
        except (TypeError, ValueError):
            # Fallback: rough character count
            total_chars = sum(
                len(str(msg.get("content", ""))) +
                len(str(msg.get("tool_calls", "")))
                for msg in messages
            )
            return int(total_chars * self.TOKENS_PER_CHAR)

    def should_compress(self, messages: list[dict[str, Any]]) -> bool:
        """Check if compression is needed based on token threshold."""
        return self.estimate_tokens(messages) > self.token_threshold

    def microcompact(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Fast compression: clear old tool results, keep last 3 exchanges.

        An "exchange" is: assistant message (with tool_calls) + tool results.
        Keeps system messages and recent context intact.
        """
        if len(messages) <= 4:  # Keep short conversations intact
            return messages

        result: list[dict[str, Any]] = []

        # Always keep system messages
        for msg in messages:
            if msg.get("role") == "system":
                result.append(msg)

        # Find the last 3 assistant messages with tool_calls
        assistant_indices = [
            i for i, msg in enumerate(messages)
            if msg.get("role") == "assistant" and msg.get("tool_calls")
        ]

        # Keep messages from the 4th-to-last assistant onward
        if len(assistant_indices) > 3:
            keep_from = assistant_indices[-4]  # 4th from last
        else:
            keep_from = 0

        # Process messages from keep_from onward
        for i, msg in enumerate(messages[keep_from:], start=keep_from):
            if msg.get("role") == "system":
                continue  # Already added

            if msg.get("role") == "tool":
                # Compress old tool results
                if i < assistant_indices[-3] if len(assistant_indices) >= 3 else False:
                    # Skip old tool results entirely
                    continue
                else:
                    # Keep recent tool results but truncate if very long
                    content = msg.get("content", "")
                    if len(content) > 2000:
                        msg = msg.copy()
                        msg["content"] = content[:2000] + "\n...[truncated]"
                    result.append(msg)
            elif msg.get("role") == "assistant" and msg.get("tool_calls"):
                # For old assistant messages, keep only the reasoning/content, not tool_calls
                if i < assistant_indices[-3] if len(assistant_indices) >= 3 else False:
                    # Keep assistant message but remove detailed tool_calls
                    msg_copy = msg.copy()
                    tool_calls = msg_copy.get("tool_calls", [])
                    if tool_calls:
                        # Replace with summary
                        msg_copy["tool_calls"] = [
                            {
                                "id": tc.get("id", ""),
                                "type": "function",
                                "function": {
                                    "name": tc.get("function", {}).get("name", "unknown"),
                                    "arguments": "{...}",
                                },
                            }
                            for tc in tool_calls
                        ]
                    result.append(msg_copy)
                else:
                    result.append(msg)
            else:
                result.append(msg)

        return result

    async def compact(
        self,
        messages: list[dict[str, Any]],
        llm_client: Any,
        workflow_run_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], str]:
        """Full compression: save transcript and generate LLM summary.

        Args:
            messages: Full conversation history
            llm_client: LLM client for generating summary
            workflow_run_id: Optional workflow run ID for transcript association

        Returns:
            Tuple of (compressed messages, transcript_id)
        """
        # Save full transcript to database
        transcript_id = str(uuid.uuid4())
        transcript = Transcript(
            id=transcript_id,
            workflow_run_id=workflow_run_id,
            messages=messages.copy(),
            message_count=len(messages),
            compressed_at=datetime.now(timezone.utc),
        )
        await transcript.insert()

        # Generate summary using LLM
        summary_messages = self._build_summary_messages(messages)
        response = await llm_client.chat(summary_messages, tools=None)
        summary_text = response.content or "Conversation summary unavailable."

        # Build compressed message list
        compressed: list[dict[str, Any]] = []

        # Keep system messages
        for msg in messages:
            if msg.get("role") == "system":
                compressed.append(msg)

        # Add summary as a system message
        compressed.append({
            "role": "system",
            "content": f"[Context Compressed - Transcript ID: {transcript_id}]\n\nSummary of earlier conversation:\n{summary_text}",
        })

        # Keep the last user message for continuity
        last_user = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user = msg
                break

        if last_user:
            compressed.append(last_user)

        return compressed, transcript_id

    def _build_summary_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Build messages for LLM summarization."""
        # Extract conversation text
        conversation_parts: list[str] = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")

            if role == "system":
                continue  # Skip system prompts in summary
            elif role == "assistant":
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    tool_names = [tc.get("function", {}).get("name", "unknown") for tc in tool_calls]
                    conversation_parts.append(f"Assistant: {content or ''} [called tools: {', '.join(tool_names)}]")
                else:
                    conversation_parts.append(f"Assistant: {content}")
            elif role == "tool":
                # Truncate tool results
                content_str = str(content)
                if len(content_str) > 500:
                    content_str = content_str[:500] + "..."
                conversation_parts.append(f"Tool result: {content_str}")
            elif role == "user":
                conversation_parts.append(f"User: {content}")

        conversation_text = "\n\n".join(conversation_parts)

        return [
            {
                "role": "system",
                "content": "You are a conversation summarizer. Create a concise summary of the conversation that preserves key facts, decisions, and context needed to continue the task. Focus on what was accomplished and what remains to be done.",
            },
            {
                "role": "user",
                "content": f"Summarize this conversation:\n\n{conversation_text}",
            },
        ]


async def compress_context(
    reason: str = "",
    messages: list[dict[str, Any]] | None = None,
    workflow_run_id: str | None = None,
) -> str:
    """Tool: Manually trigger context compression.

    Args:
        reason: Optional reason for compression
        messages: Current message context (injected by dispatcher)
        workflow_run_id: Current workflow run ID (injected by dispatcher)

    Returns:
        Confirmation message with summary stats
    """
    from app.core.llm.factory import get_llm_client_by_config_name
    from app.models import LLMModelConfig

    if messages is None:
        return "Error: No messages context provided"

    compressor = ContextCompressor()

    # Get LLM client for summarization
    first = await LLMModelConfig.find_one(LLMModelConfig.is_active == True)  # noqa: E712
    if not first:
        return "Error: No LLM model config found"

    llm = await get_llm_client_by_config_name(first.name)

    # Perform full compression
    original_count = len(messages)
    original_tokens = compressor.estimate_tokens(messages)

    compressed, transcript_id = await compressor.compact(messages, llm, workflow_run_id)

    new_tokens = compressor.estimate_tokens(compressed)

    # Update the messages list in place (this modifies the caller's list)
    messages.clear()
    messages.extend(compressed)

    return (
        f"Context compressed.\n"
        f"Reason: {reason or 'manual trigger'}\n"
        f"Transcript ID: {transcript_id}\n"
        f"Original: {original_count} messages (~{original_tokens} tokens)\n"
        f"Compressed: {len(compressed)} messages (~{new_tokens} tokens)\n"
        f"Reduction: {original_tokens - new_tokens} tokens"
    )
