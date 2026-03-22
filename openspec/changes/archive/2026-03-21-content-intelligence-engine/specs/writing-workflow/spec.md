## ADDED Requirements

### Requirement: Trigger writing workflow with multiple reference articles
The system SHALL allow triggering a writing workflow by selecting one or more analyzed articles as reference material, or by providing a topic/keywords for creative generation; the workflow is executed as an async Celery task and queued for processing.

#### Scenario: Trigger imitation writing from multiple articles
- **WHEN** user selects one or more articles from the article list and clicks "触发仿写"
- **THEN** system calls POST /workflows with type="writing" and article_ids (list of UUIDs), Celery enqueues writing_workflow_task, and frontend auto-navigates to /workflow?run_id={id}

#### Scenario: Writer Agent uses multiple article analyses as context
- **WHEN** writing_workflow_task runs with multiple article_ids
- **THEN** Writer Agent receives the ArticleAnalysis (structured summaries, NOT full content) for all referenced articles as context, enabling synthesis of multiple styles

#### Scenario: Trigger creative writing from topic
- **WHEN** user submits POST /workflows with type="writing" and a topic string (no article_ids)
- **THEN** system creates WorkflowRun with topic as input, enqueues writing_workflow_task, returns HTTP 202 with workflow_run_id

### Requirement: Task queuing and async execution
All writing workflow tasks SHALL be executed asynchronously via Celery; the API SHALL return immediately with a workflow_run_id; multiple concurrent workflows are supported through worker parallelism.

#### Scenario: Multiple concurrent writing tasks queued
- **WHEN** user triggers multiple writing workflows in quick succession
- **THEN** each creates a separate WorkflowRun in "pending" status, tasks are queued in Celery, and execute in order based on queue priority; each has its own SSE channel

#### Scenario: Task status visible before execution starts
- **WHEN** workflow_run_id is created but Celery has not yet started the task
- **THEN** WorkflowRun.status is "pending" and the workflow page shows "排队中..." with queue position if available

### Requirement: Page navigation on workflow trigger
The system SHALL automatically navigate to the workflow monitoring page after triggering a workflow.

#### Scenario: Auto-navigate to workflow page
- **WHEN** POST /workflows returns 202 with workflow_run_id
- **THEN** frontend navigates to /workflow?run_id={workflow_run_id}; the workflow page immediately establishes SSE subscription or begins polling

#### Scenario: Workflow page initializes from run_id on mount
- **WHEN** user lands on /workflow?run_id=xxx
- **THEN** page loads current WorkflowRun state via GET /workflows/{id}, then subscribes to SSE stream GET /workflows/{id}/stream if status is pending/running

### Requirement: Workflow page dual mode
The workflow page SHALL support two display modes so operations are available regardless of SSE connection.

**SSE mode (Chatbot view)**: Agent outputs stream as chat bubbles in real time via `@microsoft/fetch-event-source`.
**Polling mode (Status view)**: Page polls GET /workflows/{id} every 3 seconds, renders completed steps from persisted data.

Both modes expose the same review panel and action buttons when workflow reaches waiting_human state.

#### Scenario: Polling mode fallback
- **WHEN** SSE connection fails or user reloads after workflow completes
- **THEN** page loads full WorkflowRun from REST and renders all steps without SSE

### Requirement: SSE real-time streaming via Redis pub/sub
The system SHALL stream workflow events to the SSE endpoint via Redis pub/sub, enabling multi-worker deployments; the SSE endpoint subscribes to channel `workflow:{run_id}`.

#### Scenario: Event reaches SSE endpoint across workers
- **WHEN** a Celery worker publishes an event to `workflow:{run_id}` Redis channel
- **THEN** the FastAPI SSE endpoint (potentially on a different worker process) receives the event and streams it to the connected frontend client

#### Scenario: SSE keepalive during long LLM calls
- **WHEN** an LLM call takes more than 15 seconds
- **THEN** system sends a keepalive SSE comment (": keepalive") every 10 seconds

### Requirement: Human review panel
The system SHALL display a review panel when workflow reaches waiting_human state, showing Reviewer output, Editor title candidates, and action buttons.

The review panel SHALL include:
- Final draft preview
- Reviewer structured checklist: fact-check flags, legal risk notes, format issues (each manually checkable by user)
- 3 title candidates from Editor Agent (selectable; user can also type custom title)
- Action buttons: [✅ 批准] [✏️ 驳回 + 反馈] [🚫 终止]

#### Scenario: Approve workflow
- **WHEN** user selects a title and clicks approve (POST /workflows/{id}/approve)
- **THEN** WorkflowRun status → "done", Draft created with selected title, frontend navigates to /drafts/{id}

#### Scenario: Reject and requeue revision
- **WHEN** user clicks reject with feedback text (POST /workflows/{id}/reject)
- **THEN** system creates child WorkflowRun (parent_run_id → rejected run, user_feedback stored), enqueues writing_workflow_task.delay(child_run_id), frontend navigates to /workflow?run_id={child_run_id}

### Requirement: Workflow run history and persistence
All WorkflowRun records including AgentStep data SHALL be persisted in MongoDB and accessible via REST regardless of SSE connection state.

#### Scenario: Retrieve completed workflow
- **WHEN** user calls GET /workflows/{id}
- **THEN** system returns full WorkflowRun with all steps, inputs, outputs, timestamps

#### Scenario: List workflows with parent-child relationship
- **WHEN** user calls GET /workflows
- **THEN** paginated list sorted by created_at descending; runs with parent_run_id are annotated as revision runs

### Requirement: De-AI processing and title candidates
The Editor Agent SHALL rewrite high-AI-density sections and produce exactly 3 title candidates stored in the AgentStep output.

#### Scenario: Editor produces 3 title candidates
- **WHEN** Editor Agent completes
- **THEN** AgentStep.output contains title_candidates array with exactly 3 entries; these appear in the review panel and in Draft.title_candidates after approval

### Requirement: Abort workflow
The system SHALL allow aborting a workflow in pending, running, or waiting_human state.

#### Scenario: Abort running workflow
- **WHEN** user calls POST /workflows/{id}/abort
- **THEN** Celery task is revoked if pending, WorkflowRun status → "failed" with reason="aborted_by_user", SSE channel closed
