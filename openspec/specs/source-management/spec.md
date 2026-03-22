## ADDED Requirements

### Requirement: Create subscription source
The system SHALL allow authenticated users to create a subscription source with name, type (api/rss), URL, optional API key, optional custom headers, and fetch configuration (interval_minutes, max_items_per_fetch).

For API-type sources, an api_config object is required specifying field mappings:
- `items_path`: JSONPath to the array of articles in the response (e.g., "data.items")
- `title_field`: field name for article title
- `content_field`: field name for article body
- `url_field`: field name for article URL (used for deduplication)
- `author_field` (optional)
- `published_at_field` (optional)

For RSS-type sources, api_config is NOT required; feedparser handles standard Atom/RSS field mapping automatically.

#### Scenario: Create API source successfully
- **WHEN** user submits a valid source creation request with type="api", URL, and api_config mapping
- **THEN** system creates the source with is_active=true, registers a celery-redbeat entry for the configured interval, and returns HTTP 201

#### Scenario: Create RSS source successfully
- **WHEN** user submits a source creation request with type="rss" and a feed URL (no api_config required)
- **THEN** system creates the source, registers a celery-redbeat scheduled entry, and returns HTTP 201

#### Scenario: Create API source without api_config rejected
- **WHEN** user creates an API source without providing api_config (missing items_path, title_field, or content_field)
- **THEN** system returns HTTP 422 with validation error listing missing fields

#### Scenario: Create source with duplicate name
- **WHEN** user submits a source creation request with a name that already exists
- **THEN** system returns HTTP 400 with error indicating duplicate name

### Requirement: List subscription sources
The system SHALL return a paginated list of all subscription sources, including last_fetched_at timestamp and fetched article count.

#### Scenario: List sources
- **WHEN** user requests the sources list
- **THEN** system returns all sources sorted by created_at descending with pagination metadata

### Requirement: Update subscription source
The system SHALL allow updating any field of an existing source; changing interval_minutes SHALL update the celery-redbeat schedule entry immediately.

#### Scenario: Update source interval reschedules job
- **WHEN** user updates a source's interval_minutes
- **THEN** system updates the celery-redbeat schedule entry and returns the updated source

#### Scenario: Update non-existent source
- **WHEN** user updates a source with an ID that does not exist
- **THEN** system returns HTTP 404

### Requirement: Delete subscription source
The system SHALL delete a source and remove its celery-redbeat schedule entry; articles already fetched from this source SHALL be retained.

#### Scenario: Delete source removes scheduled entry
- **WHEN** user deletes a source
- **THEN** system removes the celery-redbeat entry and returns HTTP 204; existing articles with this source_id are preserved

### Requirement: Toggle source active state
The system SHALL allow pausing and resuming a source without deleting its schedule entry.

#### Scenario: Pause active source
- **WHEN** user sets is_active=false on a source
- **THEN** celery-redbeat entry is disabled and no further automatic fetches occur until re-activated

#### Scenario: Resume paused source
- **WHEN** user sets is_active=true on a paused source
- **THEN** celery-redbeat entry is re-enabled and the next fetch runs at the next scheduled interval

### Requirement: Manual fetch trigger
The system SHALL allow users to immediately enqueue a fetch task for any source.

#### Scenario: Manual fetch enqueues Celery task
- **WHEN** user calls POST /sources/{id}/fetch
- **THEN** system calls fetch_source_task.delay(source_id) and returns HTTP 202

### Requirement: Concurrent fetch deduplication via distributed lock
The system SHALL prevent the same source from being fetched concurrently by multiple Celery workers.

The fetch_source_task SHALL acquire a Redis lock (`redis.set(f"fetch_lock:{source_id}", 1, nx=True, ex=300)`) at the start of execution; if the lock already exists the task exits immediately without fetching.

#### Scenario: Concurrent fetch prevented by Redis lock
- **WHEN** two fetch_source_task workers attempt to fetch the same source simultaneously
- **THEN** the first acquires the lock and proceeds; the second sees the lock already set and exits without fetching, preventing duplicate article creation

### Requirement: Scheduled automatic fetch via Celery Beat
The system SHALL use celery-redbeat to schedule per-source fetch tasks; schedules SHALL be stored in Redis and survive application restarts.

#### Scenario: Fetch resumes after restart
- **WHEN** the application restarts
- **THEN** celery-redbeat reloads all schedule entries from Redis and resumes scheduled fetches

#### Scenario: Fetch records last_fetched_at
- **WHEN** a fetch_source_task completes
- **THEN** system updates the source's last_fetched_at to the current UTC timestamp

### Requirement: RSS feed fetching
The system SHALL fetch and parse RSS/Atom feeds using feedparser; standard feed fields SHALL be automatically mapped to Article fields without requiring api_config.

#### Scenario: RSS articles ingested from feed
- **WHEN** fetch_source_task runs on an RSS source
- **THEN** feedparser parses the feed URL, each entry is mapped to Article fields (title from entry.title, content from entry.summary or entry.content, url from entry.link, author from entry.author, published_at from entry.published_parsed), and new articles are created

#### Scenario: RSS duplicate entries skipped
- **WHEN** an RSS feed entry URL already exists in the articles collection
- **THEN** that entry is skipped without creating a duplicate
