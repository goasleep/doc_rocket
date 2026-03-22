## ADDED Requirements

### Requirement: Agent event loop replaces single LLM call
The system SHALL replace the single `llm.chat()` call in BaseAgent.run() with an iterative event loop; the loop SHALL continue until the LLM returns a response with no tool_calls, or max_iterations is reached.

#### Scenario: Loop terminates on text-only response
- **WHEN** LLM returns a ChatResponse with content set and tool_calls empty
- **THEN** agent exits the loop and returns content as the final result

#### Scenario: Loop continues on tool_call response
- **WHEN** LLM returns a ChatResponse with one or more tool_calls
- **THEN** agent executes each tool, appends results to message history, and calls LLM again

#### Scenario: Loop terminates at max_iterations
- **WHEN** agent has iterated max_iterations times without a text-only response
- **THEN** agent exits loop, returns last non-None content (or empty string), sets run status to "interrupted"

### Requirement: Message history accumulation
The system SHALL maintain a growing message list across loop iterations; each iteration appends the assistant's response (with tool_calls) and one tool_result message per tool call.

#### Scenario: Tool result appended with correct role
- **WHEN** agent executes a tool call with id="call_123"
- **THEN** message {"role": "tool", "tool_call_id": "call_123", "content": "<result>"} is appended to history

#### Scenario: Multiple tool calls in one response handled sequentially
- **WHEN** LLM returns a response with 2 tool_calls in a single turn
- **THEN** both tools are executed, both results appended, and a single new LLM call is made with the full updated history

### Requirement: Consecutive tool failure guard
The system SHALL track consecutive failures for each tool; if the same tool fails 3 times in a row, the loop SHALL terminate with the last available content.

#### Scenario: Same tool fails 3 times
- **WHEN** tool "web_search" raises an exception on 3 consecutive calls
- **THEN** loop exits, agent returns current best content with a warning note

### Requirement: AgentRunContext tracks loop state
The system SHALL maintain an AgentRunContext during each agent.run() call, tracking: iteration_count, tools_used (set of tool names called), skills_activated (set of skill names loaded), and start_time.

#### Scenario: Context exposes tools_used after run
- **WHEN** agent finishes a run that called web_search and activate_skill
- **THEN** AgentRunContext.tools_used contains {"web_search", "activate_skill"}

### Requirement: Tool schema assembled from AgentConfig.tools
The system SHALL assemble the OpenAI-compatible tool schema for each LLM call from the agent's assigned tools (AgentConfig.tools) filtered by is_active=True in DB and presence in TOOL_REGISTRY.

#### Scenario: Tool schema injected into LLM call
- **WHEN** agent has tools=["web_search", "fetch_url"] and both are active
- **THEN** LLM call includes tools parameter with 2 OpenAI-format tool definitions

#### Scenario: No tools schema when agent has no tools
- **WHEN** AgentConfig.tools is empty
- **THEN** LLM call is made without tools parameter (plain chat mode)

### Requirement: AnalyzerAgent exception (no agentic loop)
The AnalyzerAgent SHALL NOT use the BaseAgent event loop; it retains its specialized `run() -> dict` override that makes a single LLM call in JSON mode and parses the response.

#### Scenario: AnalyzerAgent ignores tools field
- **WHEN** AnalyzerAgent is run, even if its AgentConfig.tools is non-empty
- **THEN** no tools parameter is passed to the LLM call; AgentConfig.tools is silently ignored for AnalyzerAgent

### Requirement: AgentStep schema upgrade
The AgentStep model SHALL be extended with fields populated after each sub-agent run: messages (list of message dicts from the agent's loop), tools_used (list of tool names from AgentRunContext.tools_used), skills_activated (list of skill names from AgentRunContext.skills_activated), iteration_count (int); all new fields SHALL have defaults to preserve backward compatibility with existing AgentStep records.

#### Scenario: AgentStep populated after sub-agent run
- **WHEN** WriterAgent.run() completes after 2 loop iterations, having called web_search once
- **THEN** AgentStep.messages contains the full message history, AgentStep.tools_used=["web_search"], AgentStep.iteration_count=2
