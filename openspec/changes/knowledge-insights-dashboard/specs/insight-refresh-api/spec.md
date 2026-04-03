## ADDED Requirements

### Requirement: Manual refresh API
The system SHALL expose `POST /insights/snapshot/refresh` to allow authenticated users to manually trigger a global insight snapshot refresh.

#### Scenario: Successful manual refresh
- **WHEN** an authenticated user calls `POST /insights/snapshot/refresh` and no snapshot task is in `running` status
- **THEN** the system creates a `TaskRun` with `task_type="insight_snapshot"`, status set to `pending`, enqueues the generation task, and returns HTTP 202 with `task_run_id`

#### Scenario: Concurrent refresh rejected
- **WHEN** an authenticated user calls `POST /insights/snapshot/refresh` while a snapshot task with status `running` already exists
- **THEN** the system returns HTTP 429 with a message indicating a snapshot is already in progress

### Requirement: Task tracking integration
The insight snapshot refresh SHALL reuse the existing `TaskRun` model for observability, storing `status`, `started_at`, `completed_at`, and `error_message`.

#### Scenario: TaskRun records success
- **WHEN** the snapshot generation task completes successfully
- **THEN** the corresponding `TaskRun` status is updated to `done` and `completed_at` is set

#### Scenario: TaskRun records failure
- **WHEN** the snapshot generation task fails with an exception
- **THEN** the corresponding `TaskRun` status is updated to `failed`, `error_message` contains the exception text, and `completed_at` is set
