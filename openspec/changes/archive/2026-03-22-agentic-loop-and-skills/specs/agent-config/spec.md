## ADDED Requirements

### Requirement: AgentConfig skills field
The system SHALL add a `skills` field to AgentConfig as a list of skill names (strings); at agent run time, the system loads the corresponding active Skill documents to build the skill catalog.

#### Scenario: Skills assigned to agent config
- **WHEN** user PATCHes an AgentConfig with skills=["web-research", "seo-check"]
- **THEN** subsequent runs of this agent inject a catalog with those two skills' name+description into the system prompt

#### Scenario: Non-existent skill name silently ignored
- **WHEN** AgentConfig.skills contains a name that does not exist in the skills collection
- **THEN** that entry is silently skipped when building the catalog; no error is raised

### Requirement: AgentConfig tools field
The system SHALL add a `tools` field to AgentConfig as a list of tool names (strings); at agent run time, only tools in this list that are also active in DB and present in TOOL_REGISTRY are made available.

#### Scenario: Tools available to agent
- **WHEN** AgentConfig.tools=["web_search", "fetch_url"] and both tools are active
- **THEN** LLM call includes both tools in the tool schema

### Requirement: AgentConfig max_iterations field
The system SHALL add a `max_iterations` field to AgentConfig (int, default 5) limiting the number of loop iterations for sub-agents; OrchestratorAgent defaults to 10.

#### Scenario: Max iterations enforced
- **WHEN** agent has max_iterations=3 and loop has run 3 times without final answer
- **THEN** loop exits with last available content and run is marked "interrupted"

## MODIFIED Requirements

### Requirement: Create agent configuration
The system SHALL allow creating an AgentConfig with name, role (writer/editor/reviewer/orchestrator/custom), responsibilities description, system_prompt, model_provider (kimi/openai), model_id, workflow_order, skills (list of skill names, default []), tools (list of tool names, default []), and max_iterations (default 5).

#### Scenario: Create writer agent with skills and tools
- **WHEN** user submits a valid agent creation request with role="writer", skills=["web-research"], tools=["web_search"]
- **THEN** system creates the AgentConfig and returns HTTP 201 with the created agent including assigned id

#### Scenario: Create agent with invalid model_provider
- **WHEN** user submits a request with model_provider not in ["kimi", "openai"]
- **THEN** system returns HTTP 422 validation error
