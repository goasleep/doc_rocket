## 1. Backend — Settings & Environment

- [ ] 1.1 Add `TAVILY_API_KEY: str = ""` to `backend/app/core/config.py` in the `Settings` class
- [ ] 1.2 Add `TAVILY_API_KEY=` to `.env.example`

## 2. Backend — Remove Tavily Key from SystemConfig Model & API

- [ ] 2.1 Remove `tavily_api_key: str = ""` from `SearchConfig` in `backend/app/models/system_config.py`; keep `SearchConfig` as an empty `BaseModel` for backward compatibility
- [ ] 2.2 Update `_to_public()` in `backend/app/api/routes/system_config.py` to stop populating `search.tavily_api_key`
- [ ] 2.3 Remove `search: SearchConfig | None = None` from `SystemConfigUpdate` (or leave it accepting no-op updates)

## 3. Backend — Update Tool Implementation

- [ ] 3.1 Rewrite `web_search()` in `backend/app/core/tools/builtin.py` to read `from app.core.config import settings` and use `settings.TAVILY_API_KEY` instead of `SystemConfig.find_one()`
- [ ] 3.2 Remove the `from app.models import SystemConfig` import from `web_search()` (local import inside the function)

## 4. Backend — Make web_search a Default Tool

- [ ] 4.1 Modify `BaseAgent._build_tools_schema()` in `backend/app/core/agents/base.py` to merge `web_search` into the effective tool list: start with `effective_tools = list(tool_names) + ["web_search"]`, then deduplicate with `list(dict.fromkeys(...))`
- [ ] 4.2 Ensure no changes are needed to `SubagentRunner._filter_tools_for_explore()` because `web_search` is already in the allowed list

## 5. Backend — Update ReactAnalyzerAgent

- [ ] 5.1 Update `_step_web_search()` in `backend/app/core/agents/react_analyzer.py` to check `settings.TAVILY_API_KEY` instead of `SystemConfig.search.tavily_api_key`
- [ ] 5.2 Remove the local `SystemConfig` import if it is no longer used elsewhere in the file

## 6. Backend — Update Tests

- [ ] 6.1 Update `backend/tests/core/tools/test_web_tools.py`: patch `app.core.config.settings.TAVILY_API_KEY = ""` (or mock) instead of `SystemConfig.find_one`
- [ ] 6.2 Update `backend/tests/core/agents/test_analyzer_agent.py`: if any test mocks `SystemConfig` for Tavily, switch to patching `settings.TAVILY_API_KEY`
- [ ] 6.3 Update `backend/tests/core/agents/test_base_agent_loop.py`: add or adjust test(s) to assert that an agent with empty `tools` still receives `web_search` in its effective schema
- [ ] 6.4 Update `backend/tests/integration/api/test_system_config.py`: remove any assertions about `search.tavily_api_key` if present

## 7. Frontend — Remove Tavily Key from System Settings UI

- [ ] 7.1 In `frontend/src/components/UserSettings/SystemSettings.tsx`, remove any Tavily API key input field (it does not currently exist; verify there is no hidden reference to `search.tavily_api_key`)
- [ ] 7.2 Regenerate frontend OpenAPI client (`npm run generate-client` or equivalent) so `types.gen.ts` and `schemas.gen.ts` no longer include `tavily_api_key` under SearchConfig
- [ ] 7.3 Verify the system settings page loads without errors after type regeneration

## 8. Verification & Cleanup

- [ ] 8.1 Run backend tests: `cd backend && pytest tests/core/tools/test_web_tools.py tests/core/agents/test_base_agent_loop.py tests/core/agents/test_analyzer_agent.py tests/integration/api/test_system_config.py`
- [ ] 8.2 Run backend linters: `cd backend && ruff check app/core/config.py app/core/tools/builtin.py app/core/agents/base.py app/core/agents/react_analyzer.py app/models/system_config.py app/api/routes/system_config.py`
- [ ] 8.3 Verify `seed_tools.py` still seeds `web_search` correctly (no code changes required, just confirm)
