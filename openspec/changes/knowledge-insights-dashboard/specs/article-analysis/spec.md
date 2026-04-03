## MODIFIED Requirements

### Requirement: Structured analysis output
The Analyzer Agent SHALL produce a structured JSON analysis containing quality score, hook type, writing framework, emotional triggers, key phrases, structure, style, target audience, topic, and article_type.

#### Scenario: Analysis produces all required fields
- **WHEN** Analyzer Agent completes on an article
- **THEN** system saves ArticleAnalysis with non-null values for: quality_score (0-100), hook_type, framework, emotional_triggers (list), key_phrases (list), keywords (list), structure (intro/body/cta), style (tone/formality/avg_sentence_length), target_audience, topic, article_type

#### Scenario: Analysis handles short content gracefully
- **WHEN** article content is under 200 characters
- **THEN** Analyzer Agent still produces valid output with best-effort values and quality_score <= 40
