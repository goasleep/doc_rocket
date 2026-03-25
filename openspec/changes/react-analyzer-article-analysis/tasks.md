## 1. Data Models

- [x] 1.1 Create `QualityRubric`, `RubricDimension`, `RubricCriterion` models
- [x] 1.2 Create `ExternalReference` model
- [x] 1.3 Extend `AnalysisTraceStep` with step_name, step_type, parallel_group, tool_calls
- [x] 1.4 Create `QualityScoreDetail`, `ScoreEvidence`, `ComparisonReferenceEmbedded` models
- [x] 1.5 Extend `ArticleAnalysis` with new fields (quality_score_details, comparison_references, etc.)
- [x] 1.6 Extend `AgentConfig` role enum with "analyzer" and add analysis_config/react_config fields
- [x] 1.7 Create default QualityRubric v1 seed data

## 2. Analysis Tools

- [x] 2.1 Implement `search_similar_articles` tool (keyword search + LLM relevance check)
- [x] 2.2 Implement `get_article_analysis` tool
- [x] 2.3 Implement `save_external_reference` tool with deduplication logic
- [x] 2.4 Implement `compare_with_reference` tool
- [x] 2.5 Register new tools in TOOL_REGISTRY

## 3. ReactAnalyzerAgent

- [x] 3.1 Create `ReactAnalyzerAgent` class with step definitions
- [x] 3.2 Implement `_step_understand` method
- [x] 3.3 Implement `_step_kb_comparison` method
- [x] 3.4 Implement `_step_web_search` method
- [x] 3.5 Implement `_step_multidimensional_analysis` method (parallel)
- [x] 3.6 Implement `_step_scoring_with_reasoning` method
- [x] 3.7 Implement `_step_reflection` method
- [x] 3.8 Implement `run` method to orchestrate all steps

## 4. Task Integration

- [x] 4.1 Replace `AnalyzerAgent` import with `ReactAnalyzerAgent` in `analyze.py`
- [x] 4.2 Update `_analyze_article_async` to pass article_id to agent
- [x] 4.3 Update analysis result handling for new data structure
- [x] 4.4 Remove old `AnalyzerAgent` class

## 5. API Routes

- [x] 5.1 Create `/rubrics` CRUD endpoints
- [x] 5.2 Create `/rubrics/active` endpoint
- [x] 5.3 Create `/external-references` CRUD endpoints
- [x] 5.4 Create `/external-references/{id}/refetch` endpoint
- [x] 5.5 Extend `/analyses/{article_id}` response with new fields
- [x] 5.6 Create `/analyses/{article_id}/trace` endpoint

## 6. Frontend - Analysis Detail Page Updates

- [x] 6.1 Create `QualityScoreDetailCard` component
- [x] 6.2 Create `ComparisonReferenceCard` component
- [x] 6.3 Create `AnalysisTraceTimeline` component with parallel step grouping
- [x] 6.4 Create `AnalysisSummarySection` component
- [x] 6.5 Update `ArticleDetailPage` to use new components
- [x] 6.6 Update TypeScript types for new API responses

## 7. Frontend - External Reference Management

- [x] 7.1 Create `/external-references` list page with search/filter
- [x] 7.2 Create `/external-references/{id}` detail page
- [x] 7.3 Add external reference service functions
- [x] 7.4 Add route configuration

## 8. Frontend - Quality Rubric Management

- [x] 8.1 Create rubric management page (admin only)
- [x] 8.2 Create rubric form component
- [x] 8.3 Add rubric service functions

## 9. Testing

- [ ] 9.1 Write unit tests for new data models
- [ ] 9.2 Write unit tests for analysis tools
- [ ] 9.3 Write unit tests for ReactAnalyzerAgent steps (with mock LLM)
- [ ] 9.4 Write integration tests for analysis API
- [ ] 9.5 Write E2E test for complete analysis workflow
- [ ] 9.6 Write frontend component tests

## 10. Documentation & Polish

- [ ] 10.1 Update API documentation
- [ ] 10.2 Add component documentation
- [ ] 10.3 Verify all edge cases handled
- [ ] 10.4 Performance test with large articles

## Chrome DevTools Testing Verification

- [x] CORS configuration updated for port 5175
- [x] Login page loads and authentication works
- [x] External References page loads correctly (empty state)
- [x] Rubrics page loads with default rubric and 4 dimensions
- [x] Article detail page shows quality scores and analysis
- [x] No console errors observed
