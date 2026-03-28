## ADDED Requirements

### Requirement: Subagent isolation with fresh context
The system SHALL execute subagents with a fresh message context, isolated from the parent agent's conversation history.

#### Scenario: Fresh context creation
- **WHEN** a subagent is spawned with `spawn_subagent(task, agent_type)`
- **THEN** the subagent SHALL receive only the task description as initial context
- **AND** SHALL NOT have access to the parent's message history

#### Scenario: Agent type selection
- **WHEN** spawning with `agent_type="Explore"`
- **THEN** the subagent SHALL only have read and bash tools
- **WHEN** spawning with `agent_type="general-purpose"`
- **THEN** the subagent SHALL have full tool access

### Requirement: Summary-only return
The system SHALL return only the subagent's final output to the parent, not the full execution trace.

#### Scenario: Subagent completion
- **WHEN** a subagent completes its task
- **THEN** only the final assistant message SHALL be returned to the parent
- **AND** intermediate tool calls and results SHALL NOT be included

#### Scenario: Subagent timeout
- **WHEN** a subagent exceeds its maximum iteration limit
- **THEN** the system SHALL return a partial result indicator
- **AND** include any output generated up to that point

### Requirement: Subagent runner implementation
The system SHALL provide a `SubagentRunner` class for executing isolated subagents.

#### Scenario: Runner execution
- **WHEN** `SubagentRunner.run(agent_role, prompt, max_iterations)` is called
- **THEN** the system SHALL create a new agent instance with the specified role
- **AND** execute the agent loop with the provided prompt
- **AND** return the final result as a string

### Requirement: Orchestrator integration
The system SHALL modify `OrchestratorAgent` to use subagent isolation for writer/editor/reviewer delegation.

#### Scenario: Orchestrator delegation
- **WHEN** orchestrator delegates to writer agent
- **THEN** it SHALL use `SubagentRunner` instead of direct agent calls
- **AND** receive only the final draft, not the writing process

### Requirement: Subagent error handling
The system SHALL handle subagent failures gracefully with appropriate error propagation.

#### Scenario: Subagent failure
- **WHEN** a subagent encounters an error during execution
- **THEN** the error SHALL be caught and formatted as a user-friendly message
- **AND** returned to the parent agent for decision
