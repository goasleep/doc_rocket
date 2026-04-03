## ADDED Requirements

### Requirement: Insight snapshot model
The system SHALL provide an `InsightSnapshot` data model that stores pre-aggregated knowledge-base analytics for a global scope.

#### Scenario: Snapshot stores aggregated data
- **WHEN** snapshot generation completes successfully
- **THEN** the system persists an `InsightSnapshot` document containing keyword_cloud, emotional_trigger_cloud, framework_distribution, hook_type_distribution, suggestion_aggregation, topic_distribution, quality_score_distribution, and overview metrics

### Requirement: Retrieve latest insight snapshot
The system SHALL expose `GET /insights/snapshot/latest` to return the most recent global insight snapshot.

#### Scenario: Latest snapshot exists
- **WHEN** user calls `GET /insights/snapshot/latest`
- **THEN** the system returns the newest `InsightSnapshot` ordered by `created_at` desc

#### Scenario: No snapshot exists
- **WHEN** user calls `GET /insights/snapshot/latest` and no snapshot has ever been generated
- **THEN** the system returns HTTP 404

### Requirement: List snapshot history
The system SHALL expose `GET /insights/snapshot` to return a paginated list of snapshot history with metadata only.

#### Scenario: Retrieve history
- **WHEN** user calls `GET /insights/snapshot`
- **THEN** the system returns a list of snapshots including `id`, `created_at`, `scope`, `article_count`, `analyzed_count`, and `avg_quality_score`

### Requirement: Generate snapshot on demand
The system SHALL expose `POST /insights/snapshot/refresh` to trigger manual snapshot generation.

#### Scenario: Accept refresh request
- **WHEN** user calls `POST /insights/snapshot/refresh` and no snapshot task is currently running
- **THEN** the system creates a `TaskRun`, enqueues snapshot generation, and returns HTTP 202 with `task_run_id`

#### Scenario: Reject concurrent refresh
- **WHEN** user calls `POST /insights/snapshot/refresh` while another snapshot task is in `running` status
- **THEN** the system returns HTTP 429 without creating a new task

### Requirement: Word cloud data structure
The snapshot SHALL include word cloud arrays where each item contains `name` (text), `value` (frequency), and `avg_score` (average quality score of articles containing the word).

#### Scenario: Keyword cloud includes avg_score
- **WHEN** the snapshot is generated
- **THEN** every entry in `keyword_cloud` contains `name`, `value`, and `avg_score` for color mapping in the UI

### Requirement: Improvement suggestion aggregation
The snapshot SHALL group improvement suggestions by dimension and extract high-frequency keywords within each dimension.

#### Scenario: Suggestions grouped by dimension
- **WHEN** the snapshot is generated
- **THEN** `suggestion_aggregation` contains entries per dimension with a list of `{ name, value }` keyword items

### Requirement: Scheduled automatic snapshot refresh
The system SHALL register a redbeat schedule named `insight_snapshot_global` that triggers snapshot generation once per day.

#### Scenario: Daily scheduled refresh
- **WHEN** the redbeat schedule fires
- **THEN** the system generates a new global `InsightSnapshot` if no snapshot task is currently running
