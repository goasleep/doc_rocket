## MODIFIED Requirements

### Requirement: Structured analysis output
The Analyzer Agent SHALL produce a structured JSON analysis. Before performing a web search, the agent SHALL verify that `settings.TAVILY_API_KEY` is configured.

#### Scenario: Web search step checks environment variable
- **WHEN** ReactAnalyzerAgent reaches the web search step
- **THEN** it reads `settings.TAVILY_API_KEY` from the environment; if absent or empty, it skips the search step
