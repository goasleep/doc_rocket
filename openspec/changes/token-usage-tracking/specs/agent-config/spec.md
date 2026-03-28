## MODIFIED Requirements

### Requirement: Create agent configuration
The system SHALL allow creating an AgentConfig with name, role (writer/editor/reviewer/custom), responsibilities description, system_prompt, model_provider (kimi/claude/openai), model_id, and workflow_order. **The AgentConfig SHALL include a display name for use in token usage tracking and reporting.**

#### Scenario: Create writer agent with display name
- **WHEN** user submits a valid agent creation request with role="writer" and name="内容精修助手"
- **THEN** system creates the AgentConfig and the name is used in token usage reports

### Requirement: BaseAgent records token usage during execution
The system SHALL extend `BaseAgent` to automatically record token usage after each LLM call. The agent SHALL accept an optional `context` parameter containing entity_type, entity_id, and operation for associating token usage with specific entities.

#### Scenario: Agent execution records token usage
- **WHEN** `BaseAgent.run()` completes after making LLM calls
- **THEN** the total token usage is recorded via `TokenUsageService.record_usage()`

#### Scenario: Agent execution with context records entity-specific usage
- **WHEN** `BaseAgent.run()` is called with context={entity_type="article", entity_id="uuid", operation="analyze"}
- **THEN** the token usage is recorded with the provided entity information

#### Scenario: RefinerAgent records article refinement usage
- **WHEN** `RefinerAgent.run()` is called for article refinement
- **THEN** it automatically sets context with entity_type="article", operation="refine" and the article_id
