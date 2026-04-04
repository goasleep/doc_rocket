## ADDED Requirements

### Requirement: Default tool injection for all agents
The system SHALL automatically include `web_search` in the effective tool list for every agent, unless the agent type explicitly restricts available tools.

#### Scenario: BaseAgent receives web_search by default
- **WHEN** a BaseAgent builds its tool schema
- **THEN** `web_search` is included in the available tools even if the AgentConfig.tools list is empty

#### Scenario: Explore subagent retains web_search
- **WHEN** a SubagentRunner creates an Explore subagent
- **THEN** `web_search` remains in the filtered tool list because it is in the allowed_tools set

#### Scenario: AgentConfig with explicit tools still gets web_search
- **WHEN** an AgentConfig has tools=["fetch_url"]
- **THEN** the agent's effective tools include both "fetch_url" and "web_search"
