## ADDED Requirements

### Requirement: Task node data model
The system SHALL define a `TaskNode` document model with fields for subject, description, status, owner, dependencies, and timestamps.

#### Scenario: Task creation
- **WHEN** a task is created via `TaskGraphManager.create_task()`
- **THEN** the system SHALL persist a TaskNode with status PENDING
- **AND** include workflow_run_id for association

#### Scenario: Task with dependencies
- **WHEN** creating a task with `blocked_by=[task_id1, task_id2]`
- **THEN** the system SHALL store the dependency references
- **AND** update the blocked tasks' `blocks` arrays

### Requirement: Task status lifecycle
The system SHALL manage task status transitions: PENDING → IN_PROGRESS → COMPLETED/FAILED.

#### Scenario: Task claiming
- **WHEN** `task_claim(task_id, owner)` is called
- **THEN** the task status SHALL change from PENDING to IN_PROGRESS
- **AND** the owner field SHALL be set

#### Scenario: Task completion
- **WHEN** `complete_task(task_id)` is called
- **THEN** the task status SHALL change to COMPLETED
- **AND** completed_at SHALL be set to current timestamp

### Requirement: Automatic task unblocking
The system SHALL automatically unblock tasks when their dependencies are completed.

#### Scenario: Dependency resolution
- **WHEN** a task with `blocked_by=[completed_task]` is queried for readiness
- **THEN** `get_ready_tasks()` SHALL include this task
- **AND** the task SHALL be eligible for claiming

#### Scenario: Cascade unblocking
- **WHEN** a task completes and it blocks multiple other tasks
- **THEN** all blocked tasks SHALL become ready simultaneously
- **AND** each SHALL be available for independent claiming

### Requirement: Task graph tools
The system SHALL provide tools for agents to interact with the task graph.

#### Scenario: Task creation tool
- **WHEN** an agent calls `task_create(workflow_run_id, subject, blocked_by)`
- **THEN** a new task SHALL be created and persisted
- **AND** the task ID SHALL be returned

#### Scenario: Task listing tool
- **WHEN** an agent calls `task_list(workflow_run_id)`
- **THEN** all tasks for that workflow SHALL be returned
- **AND** include status, owner, and dependency information

#### Scenario: Task claiming tool
- **WHEN** an agent calls `task_claim(task_id, owner)`
- **THEN** the task SHALL be marked IN_PROGRESS with the owner
- **AND** return success or failure (if already claimed)

### Requirement: Cycle detection
The system SHALL prevent creation of circular dependencies in the task graph.

#### Scenario: Cycle prevention
- **WHEN** creating a task that would create a cycle (A blocks B, B blocks C, C blocks A)
- **THEN** the system SHALL reject the creation
- **AND** return an error indicating the cycle

### Requirement: Workflow integration
The system SHALL integrate task graph execution into the workflow system.

#### Scenario: Graph-based workflow execution
- **WHEN** a workflow is configured for task graph mode
- **THEN** the system SHALL execute ready tasks
- **AND** automatically proceed when tasks are unblocked
- **AND** complete when all tasks are done
