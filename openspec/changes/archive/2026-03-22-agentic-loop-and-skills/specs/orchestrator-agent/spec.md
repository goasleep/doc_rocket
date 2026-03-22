## ADDED Requirements

### Requirement: OrchestratorAgent as workflow leader
The system SHALL provide an OrchestratorAgent that runs its own agentic event loop and coordinates Writer, Editor, and Reviewer sub-agents via delegation tools; the Orchestrator SHALL replace the hardcoded linear pipeline in workflow.py.

#### Scenario: Orchestrator drives full workflow
- **WHEN** a WorkflowRun is started with use_orchestrator=True
- **THEN** OrchestratorAgent.run() is called; it uses delegation tools to invoke sub-agents, routes results, and terminates when finalize() is called or max_iterations reached

#### Scenario: Orchestrator fallback to linear pipeline
- **WHEN** WorkflowRun.use_orchestrator=False
- **THEN** system uses the existing linear Writer→Editor→Reviewer pipeline (backward compatibility)

### Requirement: Delegation tools
The system SHALL provide OrchestratorAgent with built-in delegation tools: delegate_to_writer, delegate_to_editor, delegate_to_reviewer, and finalize.

#### Scenario: delegate_to_writer invokes WriterAgent
- **WHEN** Orchestrator calls delegate_to_writer(task, context, revision_feedback=None)
- **THEN** system instantiates WriterAgent with its AgentConfig, runs its agentic loop, returns the draft text to Orchestrator as tool result

#### Scenario: delegate_to_editor invokes EditorAgent
- **WHEN** Orchestrator calls delegate_to_editor(draft)
- **THEN** system instantiates EditorAgent, runs its loop, returns structured result (approved bool, content, feedback, title_candidates) to Orchestrator

#### Scenario: finalize terminates workflow
- **WHEN** Orchestrator calls finalize(content, title_candidates)
- **THEN** loop exits, WorkflowRun.final_output is set, status transitions to "waiting_human"

### Requirement: Non-linear routing (editor can reject back to writer)
The OrchestratorAgent SHALL support routing work back to Writer when Editor rejects the draft; the Orchestrator's LLM decides routing based on editor feedback.

#### Scenario: Editor rejects, Orchestrator routes back to Writer
- **WHEN** delegate_to_editor returns approved=False with feedback
- **THEN** Orchestrator may call delegate_to_writer again with revision_feedback included in context; this counts as a new iteration

#### Scenario: Maximum revision cycles
- **WHEN** Orchestrator has called delegate_to_writer more than `max_revisions` times (default 3) without editor approval
- **THEN** Orchestrator proceeds to finalize with best available draft regardless of approval status; routing_log records "max_revisions_reached"

### Requirement: max_revisions configuration
The OrchestratorAgent SHALL support a `max_revisions: int` parameter (default 3) that limits how many times the Writer can be asked to revise; this is a constructor parameter on OrchestratorAgent, not stored in AgentConfig.

#### Scenario: max_revisions=0 disables revision
- **WHEN** OrchestratorAgent is created with max_revisions=0
- **THEN** after the first editor review (regardless of approval), Orchestrator calls finalize immediately

### Requirement: WorkflowRun routing log
The system SHALL record each routing decision made by the Orchestrator in WorkflowRun.routing_log as a list of RoutingEvent objects with fields: timestamp, from_agent, to_agent, reason (LLM-generated rationale excerpt).

#### Scenario: Routing log captures revision decision
- **WHEN** Orchestrator sends draft back to Writer with feedback
- **THEN** routing_log appends entry {from_agent: "editor", to_agent: "writer", reason: "<excerpt>"}

### Requirement: Sub-agent execution recorded in AgentStep
Each sub-agent invocation (via delegation tool) SHALL be recorded as an AgentStep in WorkflowRun.steps, including the sub-agent's full message history, tools_used, skills_activated, and iteration_count.

#### Scenario: AgentStep captures sub-agent loop state
- **WHEN** WriterAgent completes with 3 loop iterations and called web_search twice
- **THEN** corresponding AgentStep has messages=[...full history...], tools_used=["web_search"], iteration_count=3

### Requirement: revision_started SSE event
The system SHALL publish a `revision_started` SSE event to the workflow Redis channel whenever the Orchestrator routes a draft back to Writer for revision; the event payload SHALL include `revision_count` (int, 1-based) and `feedback_preview` (first 200 chars of editor feedback).

#### Scenario: revision_started event published
- **WHEN** Orchestrator calls delegate_to_writer a second time (after editor rejection)
- **THEN** system publishes SSE event {type: "revision_started", revision_count: 1, feedback_preview: "...first 200 chars..."} before WriterAgent starts

### Requirement: Orchestrator system prompt configurable
The OrchestratorAgent SHALL use an AgentConfig with role="orchestrator"; if no such config exists, a default system prompt is used that instructs the LLM to coordinate the writing team and route based on quality.

#### Scenario: Custom orchestrator prompt applied
- **WHEN** an AgentConfig with role="orchestrator" exists and is_active=True
- **THEN** OrchestratorAgent uses its system_prompt; otherwise uses built-in default
