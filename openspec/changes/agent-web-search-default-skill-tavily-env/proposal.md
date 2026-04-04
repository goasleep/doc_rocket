## Why

The Tavily API key is currently stored in `SystemConfig.search.tavily_api_key`, coupling search configuration to the database and requiring UI-based management. This creates friction for deployment and makes `web_search` unavailable unless explicitly configured per-agent. Moving the key to environment variables and making `web_search` a default capability for all agents simplifies operations and ensures every agent can search the web when needed.

## What Changes

- Move `TAVILY_API_KEY` from `SystemConfig.search.tavily_api_key` to `settings.TAVILY_API_KEY` (environment variable)
- Make `web_search` a default tool for all agents, automatically included unless filtered out by agent type constraints
- Update `SystemConfigPublic` to no longer expose `search.tavily_api_key`
- Remove Tavily key input from the system settings UI
- Update all tests and callers that previously read the key from `SystemConfig`

## Capabilities

### New Capabilities
- `default-agent-tools`: Default tool injection for all agents, starting with `web_search`

### Modified Capabilities
- `system-config`: Tavily API key removed from database model and API responses; now loaded from env
- `agent-config`: Agents now receive `web_search` by default in their available tools schema
- `article-analysis`: `ReactAnalyzerAgent` checks `settings.TAVILY_API_KEY` instead of `SystemConfig.search.tavily_api_key`

## Impact

- Backend: `config.py`, `builtin.py`, `base.py`, `react_analyzer.py`, `subagent.py`, `system_config.py`, `system_config_routes.py`, `seed_tools.py`
- Frontend: `SystemSettings.tsx` (remove Tavily key field), `types.gen.ts` and `schemas.gen.ts` (auto-generated OpenAPI client)
- Tests: `test_web_tools.py`, `test_analyzer_agent.py`, `test_system_config.py`
- Deployment: `.env.example` must document `TAVILY_API_KEY`
