## ADDED Requirements

### Requirement: Celery-based background task execution
The system SHALL execute long-running tools as Celery tasks, allowing the agent loop to continue.

#### Scenario: Background task initiation
- **WHEN** an agent calls `background_run(command, timeout)`
- **THEN** the system SHALL create a Celery task
- **AND** return immediately with a task ID
- **AND** the command SHALL execute in a Celery worker

#### Scenario: Task ID format
- **WHEN** a background task is created
- **THEN** the task ID SHALL be a unique 8-character string
- **AND** be suitable for subsequent status checks

### Requirement: Background task status tracking
The system SHALL track the status of background tasks: running, completed, or error.

#### Scenario: Status checking
- **WHEN** an agent calls `check_background(task_id)`
- **THEN** the system SHALL return the current status
- **AND** include result if completed
- **AND** include error message if failed

#### Scenario: Check all tasks
- **WHEN** an agent calls `check_background()` without task_id
- **THEN** the system SHALL return status of all tasks for the current agent
- **AND** include completed tasks that haven't been acknowledged

### Requirement: Notification queue integration
The system SHALL integrate background task notifications into the agent loop.

#### Scenario: Notification on completion
- **WHEN** a background task completes
- **THEN** the completion SHALL be added to a notification queue
- **AND** be included in the next agent loop iteration

#### Scenario: Notification format
- **WHEN** notifications are delivered to the agent
- **THEN** they SHALL include task ID, status, result/error, and runtime

### Requirement: Task timeout handling
The system SHALL enforce timeouts on background tasks and handle expiration.

#### Scenario: Timeout enforcement
- **WHEN** a background task exceeds its timeout
- **THEN** the task SHALL be marked as error
- **AND** partial output SHALL be captured if available

#### Scenario: Default timeout
- **WHEN** background_run is called without timeout
- **THEN** the system SHALL use a default of 120 seconds

### Requirement: Celery task definition
The system SHALL define a Celery task for background command execution.

#### Scenario: Celery task registration
- **WHEN** the Celery worker starts
- **THEN** the `execute_background_command` task SHALL be registered
- **AND** be available for `background_run` invocations

#### Scenario: Result persistence
- **WHEN** a background task completes
- **THEN** the result SHALL be stored in the Celery result backend
- **AND** be retrievable via `AsyncResult(task_id)`

### Requirement: Concurrent task limits
The system SHALL enforce limits on concurrent background tasks per agent.

#### Scenario: Limit enforcement
- **WHEN** an agent has 5 running background tasks
- **AND** attempts to start a 6th
- **THEN** the system SHALL reject with a limit exceeded error
- **AND** suggest checking existing tasks first
