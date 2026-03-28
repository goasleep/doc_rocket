## MODIFIED Requirements

### Requirement: Unified LLM client interface
The system SHALL provide a unified async LLM client interface with a `chat` method that accepts messages, optional tools, and a streaming flag; concrete implementations SHALL be provided for Kimi, Claude, and OpenAI. **The ChatResponse SHALL include a `usage` field containing token consumption data (prompt_tokens, completion_tokens, total_tokens).**

#### Scenario: Chat call returns response with usage
- **WHEN** any LLM client's chat method is called with a valid messages list
- **THEN** it returns a ChatResponse including the response content AND a usage object with prompt_tokens, completion_tokens, and total_tokens

#### Scenario: Chat call with tools returns tool calls and usage
- **WHEN** LLM client's chat method is called with tools defined and LLM decides to call a tool
- **THEN** client returns structured tool call data in a provider-agnostic format AND the usage object with token counts

### Requirement: OpenAI compatible client extracts usage from response
The system SHALL extend `OpenAICompatibleClient` to extract the `usage` field from the OpenAI API response and include it in the returned `ChatResponse`.

#### Scenario: OpenAI response includes usage data
- **WHEN** the OpenAI API returns a response with usage={prompt_tokens: 100, completion_tokens: 50, total_tokens: 150}
- **THEN** the ChatResponse.usage contains the same values

#### Scenario: OpenAI response missing usage data
- **WHEN** the OpenAI API returns a response without a usage field (e.g., streaming response)
- **THEN** the ChatResponse.usage is None or contains zeros
