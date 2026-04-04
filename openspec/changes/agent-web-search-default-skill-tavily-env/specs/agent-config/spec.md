## MODIFIED Requirements

### Requirement: Create agent configuration
The system SHALL allow creating an AgentConfig with name, role, responsibilities description, system_prompt, model_config_name, skills, and tools. In addition, all agents SHALL receive `web_search` as a default tool.

#### Scenario: Newly created agent has web_search available
- **WHEN** user creates an AgentConfig with an empty tools list
- **THEN** the agent can still invoke `web_search` at runtime
