## ADDED Requirements

### Requirement: Analysis trace recorded per LLM call
The `ArticleAnalysis` document SHALL include a `trace` field containing a list of `AnalysisTraceStep` records, one per LLM call made during analysis. Each step SHALL capture: the complete messages array sent to the LLM, the raw response text received, whether JSON parsing succeeded, the call duration in milliseconds, and the call timestamp.

#### Scenario: Trace captured on successful analysis
- **WHEN** AnalyzerAgent completes a successful LLM call
- **THEN** ArticleAnalysis.trace contains one AnalysisTraceStep with messages_sent (full array), raw_response (full LLM text), parsed_ok=True, duration_ms (positive integer), and a timestamp

#### Scenario: Trace captured on failed JSON parse
- **WHEN** AnalyzerAgent receives an LLM response that fails JSON parsing
- **THEN** ArticleAnalysis.trace contains the step with raw_response set and parsed_ok=False; the agent still attempts regex fallback extraction

#### Scenario: Empty trace on analysis failure
- **WHEN** the LLM call itself raises an exception (network error, timeout)
- **THEN** ArticleAnalysis may not be created; if analysis fails, trace is not persisted (task fails and TaskRun records the error)

### Requirement: Trace included in analysis API response
The `ArticleAnalysisPublic` schema SHALL include the `trace` field, enabling frontend clients to retrieve and display the full trace without additional API calls.

#### Scenario: Analysis detail includes trace
- **WHEN** user retrieves an article via GET /articles/{id}
- **THEN** the embedded analysis object includes a `trace` array (may be empty for analyses created before this feature)

### Requirement: Frontend displays analysis trace in collapsible section
The article detail page's "分析结果" tab SHALL include a collapsible "分析过程追溯" section below the analysis cards, visible only when trace data exists.

#### Scenario: Trace section hidden when no trace data
- **WHEN** ArticleAnalysis.trace is empty or null
- **THEN** the "分析过程追溯" section is not rendered

#### Scenario: Trace section shows LLM call details
- **WHEN** user expands the "分析过程追溯" section
- **THEN** each AnalysisTraceStep is displayed with: step index, duration, parsed_ok status badge, messages (role-labeled blocks), and raw_response in a monospace code block
