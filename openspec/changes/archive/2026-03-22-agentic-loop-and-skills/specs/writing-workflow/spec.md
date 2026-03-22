## ADDED Requirements

### Requirement: Orchestrator-driven workflow mode
The system SHALL support an orchestrator-driven workflow mode activated when WorkflowRun.use_orchestrator=True; in this mode, OrchestratorAgent replaces the hardcoded linear pipeline as the execution engine.

#### Scenario: Orchestrator mode enabled for new run
- **WHEN** POST /workflows is called and system config has orchestrator mode enabled
- **THEN** WorkflowRun is created with use_orchestrator=True; Celery task invokes OrchestratorAgent.run() instead of the linear pipeline

#### Scenario: Orchestrator publishes SSE events
- **WHEN** OrchestratorAgent makes a routing decision or sub-agent completes
- **THEN** system publishes SSE event to Redis channel workflow:{run_id} with event type "agent_start", "agent_output", or "routing_decision"

#### Scenario: revision_started SSE event published on rejection
- **WHEN** OrchestratorAgent routes a draft back to Writer after editor rejection
- **THEN** system publishes SSE event {type: "revision_started", revision_count: N, feedback_preview: "<first 200 chars>"} before the Writer sub-agent begins

### Requirement: WorkflowRun orchestrator fields
The system SHALL add orchestrator_messages, routing_log, and iteration_count fields to WorkflowRun; these SHALL be populated during orchestrator-driven runs.

#### Scenario: Routing log accessible via API
- **WHEN** user calls GET /workflows/{id} after an orchestrator-driven run
- **THEN** response includes routing_log array with all routing events

## MODIFIED Requirements

### Requirement: Trigger writing workflow with multiple reference articles
The system SHALL allow triggering a writing workflow by selecting one or more analyzed articles as reference material, or by providing a topic/keywords for creative generation; the workflow is executed as an async Celery task; the execution engine is selected based on the WorkflowRun.use_orchestrator flag.

#### Scenario: Trigger imitation writing from multiple articles
- **WHEN** user selects one or more articles from the article list and clicks "触发仿写"
- **THEN** system calls POST /workflows with type="writing" and article_ids (list of UUIDs), Celery enqueues writing_workflow_task, frontend auto-navigates to /workflow?run_id={id}

#### Scenario: Writer Agent uses multiple article analyses as context
- **WHEN** writing_workflow_task runs with multiple article_ids
- **THEN** Writer Agent receives the ArticleAnalysis (structured summaries, NOT full content) for all referenced articles as context, enabling synthesis of multiple styles

#### Scenario: Trigger creative writing from topic
- **WHEN** user submits POST /workflows with type="writing" and a topic string (no article_ids)
- **THEN** system creates WorkflowRun with topic as input, enqueues writing_workflow_task, returns HTTP 202 with workflow_run_id
