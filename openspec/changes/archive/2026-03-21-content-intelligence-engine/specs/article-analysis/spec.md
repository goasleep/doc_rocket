## ADDED Requirements

### Requirement: Trigger article analysis
The system SHALL allow triggering AI analysis on any article with status="raw" or "analyzed"; re-analysis SHALL overwrite the existing ArticleAnalysis.

#### Scenario: Trigger analysis on raw article
- **WHEN** user calls POST /analyses with article_id
- **THEN** system creates a WorkflowRun of type="analysis", sets article status to "analyzing", and returns HTTP 202 with workflow_run_id

#### Scenario: Re-analysis overwrites existing
- **WHEN** user triggers analysis on an already-analyzed article
- **THEN** system creates a new ArticleAnalysis replacing the old one and updates the article status back through analyzing → analyzed

### Requirement: Structured analysis output
The Analyzer Agent SHALL produce a structured JSON analysis containing quality score, hook type, writing framework, emotional triggers, key phrases, structure, style, and target audience.

#### Scenario: Analysis produces all required fields
- **WHEN** Analyzer Agent completes on an article
- **THEN** system saves ArticleAnalysis with non-null values for: quality_score (0-100), hook_type, framework, emotional_triggers (list), key_phrases (list), keywords (list), structure (intro/body/cta), style (tone/formality/avg_sentence_length), target_audience

#### Scenario: Analysis handles short content gracefully
- **WHEN** article content is under 200 characters
- **THEN** Analyzer Agent still produces valid output with best-effort values and quality_score <= 40

### Requirement: Quality scoring
The system SHALL calculate a composite quality_score (0-100) as a weighted average of content_depth, readability, originality, and virality_potential sub-scores.

#### Scenario: Quality score breakdown accessible
- **WHEN** user retrieves an ArticleAnalysis
- **THEN** response includes quality_score and quality_breakdown with all four sub-scores

### Requirement: Analysis result retrieval
The system SHALL provide endpoints to retrieve analysis by article_id or analysis_id, and list all analyses sorted by quality_score.

#### Scenario: Get analysis by article
- **WHEN** user calls GET /analyses?article_id={id}
- **THEN** system returns the most recent ArticleAnalysis for that article or 404 if none exists

### Requirement: Content truncation for long articles
The system SHALL truncate article content exceeding the configured max token limit before sending to the LLM, preserving the beginning and end of the article.

#### Scenario: Long article truncated before analysis
- **WHEN** article content exceeds max_tokens (configurable, default 8000 tokens)
- **THEN** system truncates middle content, appends a truncation notice, and proceeds with analysis
