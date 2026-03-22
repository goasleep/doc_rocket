## ADDED Requirements

### Requirement: Article Markdown refinement via RefinerAgent
The system SHALL provide a `RefinerAgent` that converts raw fetched article text into clean, well-structured Markdown. The agent SHALL preserve all core information without adding or removing content, and SHALL be optimized for Chinese technology articles.

The agent SHALL:
- Remove navigation bar residue, advertisement text, duplicate copyright notices, and other noise
- Restore document structure: heading levels, paragraphs, lists, code blocks
- Fix encoding artifacts and excessive whitespace
- Maintain the original language ratio in mixed Chinese-English content
- Output pure Markdown with no explanatory text added by the agent

#### Scenario: Refiner produces clean Markdown from noisy plain text
- **WHEN** RefinerAgent.run() is called with raw fetched content containing navigation residue and flat text
- **THEN** the agent returns a Markdown string with proper headings, paragraphs, and noise removed; core content is unchanged

#### Scenario: Refiner handles already-clean content
- **WHEN** RefinerAgent.run() is called with content that is already well-formatted
- **THEN** the agent returns the content in Markdown with minimal changes; no content is added

### Requirement: Article stores refined Markdown
The `Article` document SHALL include two new fields: `content_md` (the refined Markdown string, nullable) and `refine_status` (the refinement lifecycle state).

`refine_status` SHALL follow the lifecycle: `pending` → `refining` → `refined` | `failed`.

#### Scenario: New article starts with refine_status=pending
- **WHEN** a new Article is created (from fetch or manual submission)
- **THEN** `content_md` is null and `refine_status` is "pending"

#### Scenario: Refinement updates content_md and refine_status
- **WHEN** refine_article_task completes successfully
- **THEN** Article.content_md is set to the Markdown string and Article.refine_status is "refined"

#### Scenario: Refinement failure sets failed status
- **WHEN** refine_article_task raises an exception
- **THEN** Article.refine_status is set to "failed" and Article.content_md remains null

### Requirement: Refine task integrated with TaskRun system
The `refine_article_task` SHALL create and update a `TaskRun` record with `task_type="refine"` throughout its lifecycle, consistent with existing analyze and fetch tasks.

#### Scenario: TaskRun created before refine task enqueue
- **WHEN** fetch flow enqueues refine_article_task
- **THEN** a TaskRun with task_type="refine", status="pending" is created first and its ID passed to the task

#### Scenario: TaskRun reflects task lifecycle
- **WHEN** refine_article_task starts executing
- **THEN** TaskRun status transitions to "running" with started_at set; on completion, status is "done" with ended_at; on failure, status is "failed" with error_message

### Requirement: Refine failure gracefully degrades to direct analysis
When refinement fails, the system SHALL NOT block the analysis pipeline. Analysis SHALL proceed using the original `Article.content` as fallback.

#### Scenario: Degraded analysis after refine failure
- **WHEN** refine_article_task fails
- **THEN** system sets Article.refine_status="failed" and immediately enqueues analyze_article_task using Article.content

### Requirement: Frontend displays refined Markdown in article detail
The article detail page SHALL include a "精修版" tab that renders `content_md` using the existing MDEditor.Markdown component.

#### Scenario: Refined content rendered as Markdown
- **WHEN** user opens article detail and content_md is not null
- **THEN** "精修版" tab renders the Markdown with proper formatting via MDEditor.Markdown

#### Scenario: Pending/in-progress state shown
- **WHEN** content_md is null and refine_status is "pending" or "refining"
- **THEN** tab shows an appropriate waiting/in-progress indicator

#### Scenario: Failed state shown
- **WHEN** content_md is null and refine_status is "failed"
- **THEN** tab shows a message indicating refinement failed and analysis used the original content
