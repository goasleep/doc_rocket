## 1. Data Models

- [x] 1.1 Create `backend/app/models/token_usage.py` with `TokenUsage` Document
- [x] 1.2 Create `TokenUsageDaily` Document in same file
- [x] 1.3 Add Pydantic schemas for API responses (TokenUsagePublic, TokenUsageDailyPublic)
- [x] 1.4 Export models from `backend/app/models/__init__.py`
- [x] 1.5 Add Beanie indexes for efficient queries (date, agent_config_id, entity_type, entity_id)

## 2. LLM Client Extension

- [x] 2.1 Extend `backend/app/core/llm/base.py` - add `UsageData` dataclass with prompt_tokens, completion_tokens, total_tokens
- [x] 2.2 Extend `ChatResponse` to include optional `usage: UsageData | None` field
- [x] 2.3 Modify `backend/app/core/llm/openai_compatible.py` to extract usage from API response
- [x] 2.4 Handle case where usage is missing (streaming responses) - set usage to None
- [x] 2.5 Unit test: Verify usage extraction from mock OpenAI response

## 3. Token Usage Service

- [x] 3.1 Create `backend/app/services/token_usage.py` with `TokenUsageService` class
- [x] 3.2 Implement `record_usage()` method - creates TokenUsage and updates TokenUsageDaily atomically
- [x] 3.3 Implement `get_agent_daily_stats(start_date, end_date)` for agent aggregation
- [x] 3.4 Implement `get_entity_usage(entity_type, entity_id)` for article-specific queries
- [x] 3.5 Implement `get_today_stats()` for dashboard quick stats
- [x] 3.6 Unit tests for all service methods with memory MongoDB

## 4. BaseAgent Integration

- [x] 4.1 Extend `backend/app/core/agents/base.py` - add `context` parameter to `run()` method
- [x] 4.2 Modify `BaseAgent.run()` to record token usage after each LLM call
- [x] 4.3 Add `_record_token_usage()` helper method to BaseAgent
- [x] 4.4 Modify `RefinerAgent.run()` to accept and pass context with article info
- [x] 4.5 Update `backend/app/tasks/refine.py` to pass article context when creating RefinerAgent
- [x] 4.6 Unit test: Verify BaseAgent records usage correctly

## 5. REST API

- [x] 5.1 Create `backend/app/api/routes/token_usage.py` router
- [x] 5.2 Implement `GET /api/v1/token-usage/today` for today's stats
- [x] 5.3 Implement `GET /api/v1/token-usage/yesterday` for yesterday's stats
- [x] 5.4 Implement `GET /api/v1/token-usage/trend` for time-series data
- [x] 5.5 Implement `GET /api/v1/token-usage/agents` with date range query params
- [x] 5.6 Implement `GET /api/v1/token-usage/agents/{agent_id}` for single agent stats
- [x] 5.7 Implement `GET /api/v1/token-usage/articles/{article_id}` for article breakdown
- [x] 5.8 Register router in `backend/app/api/main.py`
- [x] 5.9 Integration tests for all endpoints

## 6. Frontend API Client

- [x] 6.1 Add token usage types to frontend (TokenUsage, TokenUsageDaily interfaces) - auto-generated
- [x] 6.2 Create `frontend/src/client/services/tokenUsageService.ts` - auto-generated
- [x] 6.3 Add TanStack Query hooks: `useAgentTokenStats`, `useArticleTokenUsage`
- [x] 6.4 Add `useAgentTrendData` hook for chart time-series data
- [x] 6.5 Generate OpenAPI client

## 7. Frontend Components

- [x] 7.1 Create `frontend/src/components/token-usage/TokenUsageCard.tsx` for stat display
- [x] 7.2 Create `frontend/src/components/token-usage/TokenUsageBreakdown.tsx` for operation list
- [x] 7.3 Create `frontend/src/components/token-usage/TokenUsageSkeleton.tsx` for loading state
- [x] 7.4 Add number formatting utility (thousand separators)
- [x] 7.5 **Install chart library** (recharts or chart.js with react-chartjs-2)
- [x] 7.6 Create `frontend/src/components/token-usage/TokenTrendChart.tsx` (line chart for time series)
- [x] 7.7 Create `frontend/src/components/token-usage/TokenDistributionChart.tsx` (pie/donut for operation breakdown)
- [x] 7.8 Create `frontend/src/components/token-usage/AgentComparisonChart.tsx` (bar chart for agent comparison)
- [x] 7.9 Add chart color utilities (Tailwind palette integration)

## 8. Frontend Pages Integration

- [x] 8.1 Modify `frontend/src/routes/_layout/agents.tsx` - add TokenUsageCard for today/yesterday stats
- [x] 8.2 Modify `frontend/src/routes/_layout/agents.tsx` - add TokenTrendChart with 7d/30d/90d selector
- [x] 8.3 Modify `frontend/src/routes/_layout/agents.tsx` - add AgentComparisonChart for multi-agent view
- [x] 8.4 Modify article detail page - add TokenUsageBreakdown section
- [x] 8.5 Modify article detail page - add TokenDistributionChart (pie chart)
- [x] 8.6 Ensure responsive design for mobile viewports (charts stack vertically)
- [x] 8.7 Add error boundaries for token usage components
- [x] 8.8 Add chart loading states (skeletons)

## 9. Unit Tests

- [x] 9.1 Test `TokenUsage` model creation and validation
- [x] 9.2 Test `TokenUsageDaily` atomic increment logic
- [x] 9.3 Test `TokenUsageService.record_usage()` with various inputs
- [x] 9.4 Test `TokenUsageService` aggregation queries
- [x] 9.5 Test `BaseAgent` context passing and usage recording
- [x] 9.6 Mock LLM client for agent testing

## 10. Integration Tests

- [x] 10.1 Test `GET /api/v1/token-usage/agents` query with date filters
- [x] 10.2 Test article token usage endpoint with seeded data
- [x] 10.3 Test end-to-end: Agent execution → TokenUsage recorded → API returns data
- [x] 10.4 Test concurrent token usage recording (race condition handling)

## 11. E2E Tests with Chrome DevTools

- [x] 11.1 Create `frontend/tests/token-usage.spec.ts` Playwright test file
- [x] 11.2 Test: Agent page displays token usage cards
- [x] 11.3 Test: Agent page displays trend chart with data
- [x] 11.4 Test: Article detail page shows token breakdown
- [x] 11.5 Test: Article detail page shows distribution chart
- [x] 11.6 Test: Chart time range selector (7d/30d/90d) works correctly
- [x] 11.7 Use Chrome DevTools MCP: Run Lighthouse accessibility audit on Agent page
- [x] 11.8 Use Chrome DevTools MCP: Verify responsive layout on mobile viewport
- [x] 11.9 Use Chrome DevTools MCP: Check for console errors during token usage display
- [x] 11.10 Use Chrome DevTools MCP: Verify chart rendering performance

## 12. Deployment

- [x] 12.1 Verify MongoDB indexes are created on startup
- [x] 12.2 Add feature flag for token usage tracking (optional)
- [x] 12.3 Update `CLAUDE.md` with new models and API documentation
- [x] 12.4 Run full test suite: `uv run pytest` and `pnpm exec playwright test`
- [x] 12.5 Build and deploy: `docker compose up -d`
- [x] 12.6 Verify in production: Trigger article refinement and check TokenUsage recorded
