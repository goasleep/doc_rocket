## Why

The current agent platform lacks critical capabilities for scaling complex, long-running workflows. As workflows grow in complexity and duration, they hit fundamental limitations: context overflow crashes long conversations, orchestrator contexts become bloated with subagent details, task coordination is limited to linear steps without dependency management, tools block execution serially, and skills waste tokens by loading full content into system prompts. These limitations prevent the platform from handling production-grade multi-agent workflows efficiently.

## What Changes

This enhancement introduces five core capabilities inspired by the `learn-claude-code` architecture:

1. **Context Compression**: Automatic and manual conversation summarization to prevent context overflow. When token count exceeds thresholds, old messages are compressed into summaries while preserving critical state.

2. **Subagent Isolation**: True isolation for child agent execution with fresh message contexts. Subagents run independently and return only final summaries to the parent, preventing orchestrator context bloat.

3. **Persistent Task Graph**: DAG-based task dependency management with MongoDB persistence. Tasks can declare `blocked_by` dependencies and are automatically unblocked when prerequisites complete.

4. **Background Tasks (Celery-based)**: Concurrent tool execution within the agent loop using Celery. Long-running operations execute asynchronously with notification-based completion tracking.

5. **Skill On-Demand Loading**: Two-tier skill system where only skill names/descriptions load into system prompts, and full content is fetched via `load_skill()` tool when needed.

## Capabilities

### New Capabilities
- `context-compression`: Automatic and manual conversation context compression with transcript persistence
- `subagent-isolation`: Isolated subagent execution with fresh contexts and summary-only returns
- `persistent-task-graph`: DAG-based task dependency management with auto-unblocking
- `celery-background-tasks`: Asynchronous tool execution using Celery within agent loops
- `skill-on-demand-loading`: Two-tier skill loading (catalog + on-demand content)

### Modified Capabilities
- `workflow-orchestration`: Enhanced to support task graph execution instead of linear step arrays

## Impact

**Backend:**
- New modules: `compression.py`, `subagent.py`, `background.py`, `task_graph.py`
- Modified: `BaseAgent`, `OrchestratorAgent`, tool registry, workflow execution
- New MongoDB collections: `task_nodes`, `transcripts`
- Celery task additions for background execution

**Frontend:**
- Minimal changes: Task graph visualization in workflow UI
- Background task status indicators

**Dependencies:**
- No new external dependencies (uses existing Celery, MongoDB, Beanie)

**APIs:**
- New tools: `compress_context`, `spawn_subagent`, `task_create`, `task_claim`, `background_run`, `check_background`, `load_skill`
- New workflow execution mode supporting task graphs
