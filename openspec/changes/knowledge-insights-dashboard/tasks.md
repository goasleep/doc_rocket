## 1. Data Model & Agent Changes

- [ ] 1.1 Add `topic` and `article_type` fields to `ArticleAnalysis` model
- [ ] 1.2 Update `ReactAnalyzerAgent.run()` to include `topic` and `article_type` in returned dict
- [ ] 1.3 Create `InsightSnapshot` Beanie Document model with all snapshot fields

## 2. Backend Aggregation Service

- [ ] 2.1 Implement `InsightSnapshotService.generate()` with batch pagination (500 docs/batch)
- [ ] 2.2 Implement keyword cloud aggregation with frequency + avg quality score
- [ ] 2.3 Implement emotional trigger cloud aggregation
- [ ] 2.4 Implement framework/hook type/topic distribution aggregations
- [ ] 2.5 Implement improvement suggestion aggregation (group by dimension + keyword frequency)
- [ ] 2.6 Implement quality score distribution histogram aggregation
- [ ] 2.7 Implement overview metrics (total articles, analyzed count, avg quality score)

## 3. API Routes

- [ ] 3.1 Create `backend/app/api/routes/insights.py` with `GET /insights/snapshot/latest`
- [ ] 3.2 Add `GET /insights/snapshot` for snapshot history list
- [ ] 3.3 Add `POST /insights/snapshot/refresh` with TaskRun concurrency check (429 if running)
- [ ] 3.4 Register insights router in `backend/app/api/main.py`

## 4. Celery Task & Redbeat Schedule

- [ ] 4.1 Create `backend/app/tasks/insight_snapshot.py` Celery task
- [ ] 4.2 Add redbeat `insight_snapshot_global` schedule registration on startup
- [ ] 4.3 Wire TaskRun status updates (`pending` -> `running` -> `done`/`failed`) in task

## 5. Frontend Dependencies & Client

- [ ] 5.1 Add `echarts`, `echarts-for-react`, `echarts-wordcloud` to `frontend/package.json`
- [ ] 5.2 Run `pnpm install`
- [ ] 5.3 Regenerate OpenAPI client via `pnpm run generate-client` after backend routes are up

## 6. Frontend Insights Dashboard Page

- [ ] 6.1 Create `frontend/src/routes/_layout/insights.tsx` route page
- [ ] 6.2 Build overview metric cards (total articles, analyzed count, avg quality score)
- [ ] 6.3 Build keyword word cloud chart with ECharts
- [ ] 6.4 Build emotional trigger word cloud chart
- [ ] 6.5 Build framework/pie and hook type/pie distribution charts
- [ ] 6.6 Build improvement suggestion word cloud with dimension tabs
- [ ] 6.7 Build topic distribution bar chart
- [ ] 6.8 Build quality score distribution histogram
- [ ] 6.9 Add manual refresh button with loading state and generation timestamp display
- [ ] 6.10 Add sidebar navigation entry for Insights page

## 7. Testing & Validation

- [ ] 7.1 Test API endpoints manually (latest, history, refresh)
- [ ] 7.2 Verify word cloud renders correctly in browser
- [ ] 7.3 Verify TaskRun blocks concurrent refresh requests
- [ ] 7.4 Verify redbeat schedule appears in Redis/beat UI
