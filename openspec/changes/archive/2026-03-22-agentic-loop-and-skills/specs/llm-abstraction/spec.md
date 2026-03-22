## MODIFIED Requirements

### Requirement: Unified LLM client interface
The system SHALL provide a unified async LLM client interface with a `chat` method that accepts messages, optional tools list (OpenAI function-calling format), and optional response_format; the method SHALL return a `ChatResponse` object containing either text content or a list of ToolCall objects (or both); concrete implementations SHALL be provided for Kimi and OpenAI only.

#### Scenario: Chat call returns text response
- **WHEN** any LLM client's chat method is called with a valid messages list and no tools
- **THEN** it returns ChatResponse with content set and tool_calls as empty list

#### Scenario: Chat call with tools returns tool calls
- **WHEN** LLM client's chat method is called with tools defined and LLM decides to call a tool
- **THEN** client returns ChatResponse with tool_calls list containing ToolCall(id, name, arguments) and content=None

#### Scenario: Chat call returns both content and tool calls
- **WHEN** LLM returns a response with both text and tool_calls (parallel tool call + commentary)
- **THEN** ChatResponse has both content and tool_calls populated

## REMOVED Requirements

### Requirement: Claude client using Anthropic SDK
**Reason**: Simplifying to OpenAI-compatible providers only (Kimi and OpenAI). Claude's tool_use format requires a separate normalization layer that adds complexity without benefit given that neither Kimi nor OpenAI require it.
**Migration**: Any AgentConfig with model_provider="claude" SHALL be treated as invalid at runtime; the factory SHALL raise LLMProviderNotConfiguredError("claude"); users must migrate to kimi or openai provider.

## ADDED Requirements

### Requirement: OpenAICompatibleClient shared base class
The system SHALL extract shared OpenAI SDK logic into a base class `OpenAICompatibleClient(LLMClient)` that both KimiClient and OpenAIClient extend; tool call parsing, response normalization, and error handling SHALL be implemented once in this base class.

#### Scenario: KimiClient and OpenAIClient share base implementation
- **WHEN** either KimiClient or OpenAIClient handles a tool_call response
- **THEN** both use the same ChatResponse normalization code from OpenAICompatibleClient

### Requirement: ChatResponse and ToolCall data types
The system SHALL define `ChatResponse` and `ToolCall` as dataclasses in `core/llm/base.py`; these SHALL be the sole return types from `LLMClient.chat()`.

#### Scenario: ToolCall has id, name, arguments
- **WHEN** LLM returns a function call with name="web_search" and arguments={"query": "test"}
- **THEN** ToolCall.id is the provider-assigned call id, ToolCall.name="web_search", ToolCall.arguments={"query": "test"}
