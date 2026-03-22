## MODIFIED Requirements

### Requirement: Automatic analysis on ingest
The system SHALL automatically enqueue a `refine_article_task` immediately after any new Article is created; the refine task SHALL then enqueue `analyze_article_task` upon completion (success or failure). Users SHALL NOT need to manually trigger refinement or analysis.

#### Scenario: Auto-refine-then-analyze on source fetch
- **WHEN** fetch_source_task creates a new Article
- **THEN** system creates a refine TaskRun and immediately calls refine_article_task.delay(article_id, task_run_id); article refine_status is "pending"; upon refine completion, analyze_article_task is automatically enqueued

#### Scenario: Auto-refine-then-analyze on manual submission
- **WHEN** user submits a new article via /submit
- **THEN** system creates the Article and enqueues refine_article_task; user is redirected to /articles/{id} which shows refinement and analysis in progress via the task history timeline

### Requirement: Ingest article from source fetch
The system SHALL create an Article document for each item returned by a source fetch using the source's api_config or RSS field mapping; duplicate articles (same URL) SHALL be skipped.

#### Scenario: New article ingested from API fetch
- **WHEN** fetch_source_task retrieves an article from an API source
- **THEN** system uses api_config field mapping to extract title/content/url/author/published_at, creates Article with status="raw", refine_status="pending", input_type="fetched", and immediately enqueues refine_article_task

#### Scenario: New article ingested from RSS fetch
- **WHEN** fetch_source_task retrieves entries from an RSS source
- **THEN** system uses feedparser's standard field mapping to extract article fields, creates Article with status="raw", refine_status="pending", input_type="fetched", and immediately enqueues refine_article_task

#### Scenario: Duplicate article skipped
- **WHEN** a source fetch returns an article whose URL already exists in the articles collection
- **THEN** system skips creation without creating a duplicate or enqueueing refinement or analysis
