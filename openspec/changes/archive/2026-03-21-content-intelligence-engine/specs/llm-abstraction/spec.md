## ADDED Requirements

### Requirement: Unified LLM client interface
The system SHALL provide a unified async LLM client interface with a `chat` method that accepts messages, optional tools, and a streaming flag; concrete implementations SHALL be provided for Kimi, Claude, and OpenAI.

#### Scenario: Chat call returns response
- **WHEN** any LLM client's chat method is called with a valid messages list
- **THEN** it returns a string response without raising provider-specific exceptions to the caller

#### Scenario: Chat call with tools returns tool calls
- **WHEN** LLM client's chat method is called with tools defined and LLM decides to call a tool
- **THEN** client returns structured tool call data in a provider-agnostic format

### Requirement: Kimi client using OpenAI SDK
The Kimi client SHALL use the `openai` Python SDK with `base_url="https://api.moonshot.cn/v1"` and the API key from SystemConfig.

#### Scenario: Kimi client initializes with SystemConfig key
- **WHEN** LLMClientFactory creates a Kimi client
- **THEN** it reads the Kimi API key from SystemConfig (decrypted) and instantiates AsyncOpenAI with moonshot base_url

### Requirement: Claude client using Anthropic SDK
The Claude client SHALL use the `anthropic` Python SDK; tool_use responses SHALL be normalized to the same provider-agnostic format as OpenAI tool calls.

#### Scenario: Claude client handles tool_use response
- **WHEN** Claude returns a tool_use response
- **THEN** client normalizes it to the unified tool call format before returning to caller

### Requirement: LLMClientFactory routing
The system SHALL provide a factory function `get_llm_client(provider, model_id)` that returns the appropriate client instance; if the provider's API key is not configured, it SHALL raise a descriptive error.

#### Scenario: Factory returns correct client
- **WHEN** get_llm_client("kimi", "moonshot-v1-32k") is called
- **THEN** factory returns a KimiClient configured for moonshot-v1-32k

#### Scenario: Factory raises error for unconfigured provider
- **WHEN** get_llm_client("openai", "gpt-4o") is called but OpenAI API key is not set in SystemConfig
- **THEN** factory raises LLMProviderNotConfiguredError with provider name in message

### Requirement: Streaming support
The LLM interface SHALL support token-level streaming; when stream=True, the chat method SHALL return an async generator yielding string chunks.

#### Scenario: Streaming yields incremental chunks
- **WHEN** chat is called with stream=True
- **THEN** method returns an async generator that yields string chunks as they arrive from the provider

### Requirement: Default model fallback
The system SHALL use the default model_id configured in SystemConfig for a given provider when no model_id is specified by the caller.

#### Scenario: Default model used when not specified
- **WHEN** get_llm_client("kimi") is called without model_id
- **THEN** factory uses SystemConfig.analysis.default_model_id for kimi provider
