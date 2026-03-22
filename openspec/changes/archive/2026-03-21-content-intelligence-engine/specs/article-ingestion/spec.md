## ADDED Requirements

### Requirement: Automatic analysis on ingest
The system SHALL automatically enqueue an analyze_article_task immediately after any new Article is created, regardless of whether it came from a source fetch or manual submission; users SHALL NOT need to manually trigger analysis.

#### Scenario: Auto-analysis on source fetch
- **WHEN** fetch_source_task creates a new Article
- **THEN** system immediately calls analyze_article_task.delay(article_id); article status transitions raw → analyzing

#### Scenario: Auto-analysis on manual submission
- **WHEN** user submits a new article via /submit
- **THEN** system creates the Article and immediately calls analyze_article_task.delay(article_id); user is redirected to /articles/{id} which shows "分析中..." status

### Requirement: Ingest article from source fetch
The system SHALL create an Article document for each item returned by a source fetch using the source's api_config or RSS field mapping; duplicate articles (same URL) SHALL be skipped.

#### Scenario: New article ingested from API fetch
- **WHEN** fetch_source_task retrieves an article from an API source
- **THEN** system uses api_config field mapping to extract title/content/url/author/published_at, creates Article with status="raw", input_type="fetched", and immediately enqueues analyze_article_task

#### Scenario: New article ingested from RSS fetch
- **WHEN** fetch_source_task retrieves entries from an RSS source
- **THEN** system uses feedparser's standard field mapping to extract article fields, creates Article with status="raw", input_type="fetched", and immediately enqueues analyze_article_task

#### Scenario: Duplicate article skipped
- **WHEN** a source fetch returns an article whose URL already exists in the articles collection
- **THEN** system skips creation without creating a duplicate or enqueueing analysis

### Requirement: Independent manual submission page
The system SHALL provide a dedicated /submit page accessible from main navigation for manual article ingestion; this page is the primary manual entry point and is independent of the article library.

The /submit page SHALL support two modes:
- **Text mode**: user pastes article title + full content
- **URL mode**: user provides a URL; Fetcher Agent retrieves and extracts content automatically

Both modes auto-trigger analysis immediately on submission.

#### Scenario: Text mode submission
- **WHEN** user fills title and content on /submit and clicks Submit
- **THEN** system creates Article with input_type="manual", enqueues analyze_article_task, and redirects to /articles/{id} showing "分析中..." status

#### Scenario: URL mode submission
- **WHEN** user enters a URL on /submit and clicks Submit
- **THEN** system enqueues fetch_and_analyze_task (fetches URL content then analyzes), returns HTTP 202, and redirects to /articles/{id}

#### Scenario: URL mode deduplication — silent reuse
- **WHEN** user submits a URL via /submit and that URL already exists in the articles collection
- **THEN** system returns HTTP 200 with the existing article_id (no duplicate created, no duplicate analysis triggered); frontend redirects to /articles/{existing_id} as if it were a new submission; no error is shown to the user

### Requirement: Article list excludes content field
The system SHALL NOT return the full content field in list API responses; only summary fields SHALL be returned to keep payload sizes manageable.

#### Scenario: List response excludes content
- **WHEN** user requests GET /articles
- **THEN** response items contain id, title, status, input_type, source_id, quality_score, created_at but NOT the content field

### Requirement: Idempotent analysis task execution
The analyze_article_task SHALL be safe to call multiple times on the same article without causing duplicate analysis or data corruption.

Two mechanisms work together:

**1. Celery unique task ID** — when enqueuing analysis, always pass `task_id=f"analyze_{article_id}"`. Celery will not enqueue a new task if a task with that ID is already pending or running in the broker, silently discarding the duplicate call at the queue level.

**2. In-task status guard** — at the start of task execution, the task reads Article.status. If status is already `"analyzing"` or `"analyzed"`, the task returns immediately without making any LLM calls or writes. The status transition from `"raw"` to `"analyzing"` uses an atomic find-one-and-update so only one concurrent worker can proceed.

#### Scenario: Duplicate analysis call is silently dropped at queue level
- **WHEN** `analyze_article_task.delay(article_id, task_id=f"analyze_{article_id}")` is called while a task with the same ID is already pending in Celery
- **THEN** Celery discards the duplicate without error; only one task executes

#### Scenario: Concurrent workers skip already-processing article
- **WHEN** two Celery workers pick up analysis tasks for the same article simultaneously
- **THEN** the atomic status update ensures only the first worker transitions status to `"analyzing"` and proceeds; the second worker sees `"analyzing"` on re-read and returns immediately

#### Scenario: Re-analysis resets status guard
- **WHEN** user manually triggers re-analysis on an already-analyzed article (POST /analyses/)
- **THEN** system first resets Article.status to `"raw"`, then calls analyze_article_task.delay() with the unique task_id, allowing the task to proceed normally

### Requirement: Article status lifecycle
The system SHALL track article status: raw → analyzing → analyzed → archived.

#### Scenario: Status transitions via Celery task
- **WHEN** analyze_article_task starts on an article
- **THEN** status changes to "analyzing"; WHEN analysis completes, status changes to "analyzed"

#### Scenario: Archive article
- **WHEN** user calls DELETE /articles/{id}
- **THEN** article status changes to "archived" and it is excluded from default list queries

### Requirement: List articles with quality sort
The system SHALL provide a paginated article list with filtering by status, source_id, input_type, and sorting by quality_score or created_at.

#### Scenario: List by quality score
- **WHEN** user requests articles with sort=quality_score
- **THEN** system returns articles ordered by ArticleAnalysis.quality_score descending; articles still analyzing appear last

### Requirement: Article detail with analysis
The system SHALL return full article content and the associated ArticleAnalysis in the detail response.

#### Scenario: Get article with analysis
- **WHEN** user requests GET /articles/{id}
- **THEN** system returns all fields including content, plus embedded analysis object (or null if still analyzing)
