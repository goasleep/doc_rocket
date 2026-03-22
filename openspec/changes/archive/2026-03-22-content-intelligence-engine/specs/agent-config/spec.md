## ADDED Requirements

### Requirement: Create agent configuration
The system SHALL allow creating an AgentConfig with name, role (writer/editor/reviewer/custom), responsibilities description, system_prompt, model_provider (kimi/claude/openai), model_id, and workflow_order.

#### Scenario: Create writer agent
- **WHEN** user submits a valid agent creation request with role="writer"
- **THEN** system creates the AgentConfig and returns HTTP 201 with the created agent including assigned id

#### Scenario: Create agent with invalid model_provider
- **WHEN** user submits a request with model_provider not in ["kimi", "claude", "openai"]
- **THEN** system returns HTTP 422 validation error

### Requirement: List agent configurations
The system SHALL return all agent configurations sorted by workflow_order ascending.

#### Scenario: List agents in workflow order
- **WHEN** user requests GET /agents
- **THEN** system returns agents sorted by workflow_order ascending

### Requirement: Update agent configuration
The system SHALL allow updating any field of an existing AgentConfig; changes take effect on the next workflow run.

#### Scenario: Update system prompt
- **WHEN** user updates an agent's system_prompt
- **THEN** system saves the new prompt and subsequent workflow runs use the updated prompt

#### Scenario: Update non-existent agent
- **WHEN** user updates an agent with an ID that does not exist
- **THEN** system returns HTTP 404

### Requirement: Delete agent configuration
The system SHALL allow deleting an agent; if the agent is referenced in an in-progress WorkflowRun, deletion SHALL return HTTP 409.

#### Scenario: Delete idle agent
- **WHEN** user deletes an agent not referenced in any running workflow
- **THEN** system deletes the agent and returns HTTP 204

#### Scenario: Delete agent in active workflow
- **WHEN** user attempts to delete an agent referenced in a WorkflowRun with status="running"
- **THEN** system returns HTTP 409 with error message

### Requirement: Toggle agent active state
The system SHALL allow disabling an agent; disabled agents SHALL be skipped in workflow execution.

#### Scenario: Disabled agent skipped in workflow
- **WHEN** an agent has is_active=false
- **THEN** WorkflowEngine skips this agent's step and continues to the next active agent in workflow_order

### Requirement: Agent model selection visible in UI
The system SHALL surface available model_provider options and, for each provider, the list of available model IDs based on the providers configured in SystemConfig.

#### Scenario: Model options filtered by configured providers
- **WHEN** user opens the agent edit form
- **THEN** only model_providers with a configured API key in SystemConfig are available for selection
