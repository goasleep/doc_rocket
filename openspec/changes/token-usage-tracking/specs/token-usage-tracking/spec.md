## ADDED Requirements

### Requirement: TokenUsage model records LLM call consumption
The system SHALL provide a `TokenUsage` Beanie Document model that records each LLM call's token consumption with fields: agent_config_id, agent_config_name, model_name, entity_type, entity_id, operation, prompt_tokens, completion_tokens, total_tokens, and created_at.

#### Scenario: TokenUsage created from LLM response
- **WHEN** an LLM call completes with usage data (prompt_tokens=1000, completion_tokens=500)
- **THEN** a TokenUsage document is created with total_tokens=1500 and the correct metadata

#### Scenario: TokenUsage handles missing usage gracefully
- **WHEN** an LLM call completes without usage data in response
- **THEN** a TokenUsage document is created with all token fields set to 0 and usage_missing flag set to True

### Requirement: TokenUsageDaily aggregates daily consumption
The system SHALL provide a `TokenUsageDaily` Beanie Document model that aggregates token consumption by date, agent_config_id, and model_name with atomic increment operations.

#### Scenario: Daily aggregation on first call of the day
- **WHEN** the first TokenUsage is recorded for a given agent/model/date combination
- **THEN** a new TokenUsageDaily document is created with call_count=1 and token sums matching the usage

#### Scenario: Daily aggregation accumulates subsequent calls
- **WHEN** additional TokenUsage is recorded for the same agent/model/date combination
- **THEN** the existing TokenUsageDaily document is atomically updated with incremented counters

### Requirement: TokenUsageService records and queries usage
The system SHALL provide a `TokenUsageService` class with methods: `record_usage()` for recording consumption, `get_agent_daily_stats()` for agent statistics, and `get_entity_usage()` for entity-specific queries.

#### Scenario: Service records usage with context
- **WHEN** `record_usage()` is called with agent_config, model_name, entity info, and token counts
- **THEN** both TokenUsage and TokenUsageDaily documents are created/updated

#### Scenario: Service returns agent daily statistics
- **WHEN** `get_agent_daily_stats()` is called with date range
- **THEN** it returns aggregated statistics grouped by agent_config_id and model_name

### Requirement: REST API for token usage queries
The system SHALL provide REST endpoints: `GET /api/v1/token-usage/agents` for agent statistics with date filtering, and `GET /api/v1/token-usage/articles/{article_id}` for article-specific usage details.

#### Scenario: Query agent token usage with date range
- **WHEN** `GET /api/v1/token-usage/agents?start_date=2026-03-26&end_date=2026-03-27` is called
- **THEN** it returns aggregated token usage for all agents within the date range

#### Scenario: Query single article token usage
- **WHEN** `GET /api/v1/token-usage/articles/{article_id}` is called
- **THEN** it returns total tokens and breakdown by operation (refine, analyze, etc.)

### Requirement: LLM Client returns token usage in response
The system SHALL extend `ChatResponse` to include a `usage` field containing prompt_tokens, completion_tokens, and total_tokens. The `OpenAICompatibleClient` SHALL extract this data from the API response.

#### Scenario: OpenAI compatible client extracts usage
- **WHEN** `OpenAICompatibleClient.chat()` receives a response with usage field
- **THEN** the returned ChatResponse includes the usage data

### Requirement: BaseAgent records token usage automatically
The system SHALL extend `BaseAgent` to automatically record token usage after each LLM call by calling `TokenUsageService.record_usage()` with context information.

#### Scenario: Agent run records usage with workflow context
- **WHEN** `BaseAgent.run()` is called with workflow_run_id in context
- **THEN** each LLM call's token usage is recorded with entity_type="workflow" and the workflow_run_id

#### Scenario: Agent run records usage with article context
- **WHEN** `RefinerAgent.run()` is called for article refinement
- **THEN** token usage is recorded with entity_type="article", entity_id=article_id, and operation="refine"
