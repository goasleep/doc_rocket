## MODIFIED Requirements

### Requirement: Structured analysis output
The Analyzer Agent SHALL produce a structured JSON analysis containing quality score, hook type, writing framework, emotional triggers, key phrases, structure, style, and target audience. The agent SHALL preferentially use `Article.content_md` when available, falling back to `Article.content` if `content_md` is null.

#### Scenario: Analysis uses content_md when available
- **WHEN** Analyzer Agent runs on an article where content_md is not null
- **THEN** agent sends content_md to the LLM (not content); analysis quality benefits from clean Markdown formatting

#### Scenario: Analysis falls back to content when content_md is null
- **WHEN** Analyzer Agent runs on an article where content_md is null (e.g., refine_status="failed" or legacy article)
- **THEN** agent uses Article.content as the analysis input; analysis proceeds normally

#### Scenario: Analysis produces all required fields
- **WHEN** Analyzer Agent completes on an article
- **THEN** system saves ArticleAnalysis with non-null values for: quality_score (0-100), hook_type, framework, emotional_triggers (list), key_phrases (list), keywords (list), structure (intro/body/cta), style (tone/formality/avg_sentence_length), target_audience

#### Scenario: Analysis handles short content gracefully
- **WHEN** article content is under 200 characters
- **THEN** Analyzer Agent still produces valid output with best-effort values and quality_score <= 40
