## Context

Currently, `web_search` reads its Tavily API key from `SystemConfig.find_one().search.tavily_api_key`. This means:
- The key must be configured via the UI or seeded into the DB
- Every agent must explicitly have `web_search` in its `AgentConfig.tools` or `AgentConfig.skills` to use it
- `ReactAnalyzerAgent` checks the DB key before deciding whether to run web search

The codebase distinguishes between:
- **Tools**: Functions registered in `TOOL_REGISTRY` and dispatched by `dispatch_tool()`
- **Skills**: Instructive content documents loaded from the DB that get injected into the system prompt

`web_search` is already a Tool, not a Skill. There is no existing "default skill" or "default tool" mechanism.

## Goals / Non-Goals

**Goals:**
- Move Tavily API key to `settings.TAVILY_API_KEY` loaded from `.env`
- Ensure every agent can use `web_search` without requiring DB-level per-agent configuration
- Keep the change backward-compatible for agents that already list `web_search` in their tools
- Remove the Tavily key field from the System Settings UI

**Non-Goals:**
- Converting `web_search` into a Skill (it should remain a Tool)
- Changing how Skills are loaded or activated
- Introducing a fully generic pluggable default-tools system (only `web_search` is default for now)

## Decisions

### 1. Default tool, not default skill
**Decision**: Inject `web_search` at the `BaseAgent._build_tools_schema()` layer rather than creating a "default skill" abstraction.

**Rationale**: `web_search` is a Tool (callable function), not a Skill (prompt injection). The existing `skills` array controls prompt content via `_build_system_prompt()`, while `tools` controls the OpenAI tool schema via `_build_tools_schema()`. Adding `web_search` to the schema by default is the cleanest semantic fit.

**Alternative considered**: Make it a default skill that somehow loads a tool. Rejected because it conflates two already-separate concepts.

### 2. Merge `web_search` into effective tools in `BaseAgent`
**Decision**: In `_build_tools_schema()`, start with `effective_tools = list(agent_config.tools or []) + ["web_search"]`, deduplicate, then proceed with the existing DB + registry filtering.

**Rationale**: This is a single-line behavioral change with broad coverage. Every agent subclass (Writer, Editor, Reviewer, Refiner, Orchestrator, ReactAnalyzer) that uses the base event loop benefits automatically. Subagents that filter tools (e.g. Explore) will still work because filtering happens after the merge.

### 3. Environment variable overrides DB key
**Decision**: Read `TAVILY_API_KEY` from `Settings` in `core/config.py`. Remove `tavily_api_key` from `SearchConfig` and from the system-config API response.

**Rationale**: Environment variables are the standard pattern for secrets in this project (e.g. `SECRET_KEY`, `MONGODB_URL`). This removes encryption/decryption bookkeeping and makes the key available at import time.

### 4. Keep `SearchConfig` as an empty/default model
**Decision**: Do not delete the `SearchConfig` nested model entirely; leave it as an empty `BaseModel` default.

**Rationale**: Avoids a breaking DB migration for existing `SystemConfig` documents that contain a `search` subdocument. The field can be deprecated and later removed if desired.

### 5. Seed tools unchanged
**Decision**: Keep `web_search` in `seed_tools.py` and the `Tool` DB record.

**Rationale**: `_build_tools_schema()` still queries the DB for `Tool` records to build the OpenAI function definition. The tool must remain active in the DB for the default injection to resolve its schema.

## Risks / Trade-offs

- **[Risk]** Some agents previously did not have `web_search` available by design; now they will. **Mitigation**: This is an explicit product requirement. The only agents that restrict tools are Explore subagents, and `web_search` is already in their allow-list.
- **[Risk]** Existing tests mock `SystemConfig.find_one` to simulate missing/present Tavily keys. **Mitigation**: Update tests to patch `app.core.config.settings.TAVILY_API_KEY` instead.
- **[Risk]** Frontend generated client (`types.gen.ts`, `schemas.gen.ts`) still references `tavily_api_key`. **Mitigation**: After backend changes, regenerate the OpenAPI client; remove the Tavily field from `SystemSettings.tsx`.

## Migration Plan

1. Add `TAVILY_API_KEY` to your deployment environment before deploying the new code.
2. Deploy backend changes.
3. (Optional) Run a one-time DB update to clear `system_config.search.tavily_api_key` if you want to remove the stale secret from the database.
4. Regenerate frontend client types from the updated OpenAPI spec.
5. Deploy frontend changes.

Rollback: Revert the commit and restore the previous code that reads from `SystemConfig.search.tavily_api_key`.
