## 1. Context Compression

- [x] 1.1 Create `backend/app/core/agents/compression.py` with `ContextCompressor` class
- [x] 1.2 Implement `estimate_tokens()` method using message JSON size heuristic
- [x] 1.3 Implement `microcompact()` to clear old tool results, keep last 3 exchanges
- [x] 1.4 Implement `compact()` with transcript saving to MongoDB and LLM summarization
- [x] 1.5 Add `compress_context` tool to `backend/app/core/tools/builtin.py`
- [x] 1.6 Integrate compression check into `BaseAgent.run()` before LLM calls
- [x] 1.7 Create `backend/app/models/transcript.py` for transcript persistence
- [x] 1.8 Write tests: `tests/core/agents/test_compression.py`

## 2. Subagent Isolation

- [x] 2.1 Create `backend/app/core/agents/subagent.py` with `SubagentRunner` class
- [x] 2.2 Implement `run()` method with fresh messages context
- [x] 2.3 Implement agent type selection ("Explore" vs "general-purpose")
- [x] 2.4 Add `spawn_subagent` tool to `backend/app/core/tools/builtin.py`
- [x] 2.5 Modify `OrchestratorAgent` to use `SubagentRunner` for delegation
- [x] 2.6 Implement subagent timeout handling with partial result return
- [x] 2.7 Write tests: `tests/core/agents/test_subagent.py`

## 3. Persistent Task Graph

- [x] 3.1 Create `backend/app/models/task_graph.py` with `TaskNode` Beanie document
- [x] 3.2 Implement `TaskGraphManager` class with `create_task()`, `complete_task()`, `get_ready_tasks()`, `claim_task()`
- [x] 3.3 Implement cycle detection for dependency validation
- [x] 3.4 Create `backend/app/core/tools/task_graph.py` with task tools
- [x] 3.5 Add `task_create`, `task_list`, `task_claim`, `task_update` tools to registry
- [x] 3.6 Modify `backend/app/tasks/workflow.py` for task graph execution mode
- [x] 3.7 Write tests: `tests/models/test_task_graph.py`, `tests/core/tools/test_task_graph.py`

## 4. Celery Background Tasks

- [x] 4.1 Create Celery task `execute_background_command` in `backend/app/tasks/background.py`
- [x] 4.2 Create `backend/app/core/agents/background.py` with `BackgroundTaskManager`
- [x] 4.3 Implement `run()` to create Celery tasks and return task ID
- [x] 4.4 Implement `check()` for task status retrieval via Celery result backend
- [x] 4.5 Add `background_run` and `check_background` tools to `backend/app/core/tools/builtin.py`
- [x] 4.6 Integrate notification queue into `BaseAgent.run()` loop
- [x] 4.7 Implement concurrent task limit enforcement (max 5 per agent)
- [x] 4.8 Write tests: `tests/core/agents/test_background.py`, `tests/tasks/test_background.py`

## 5. Skill On-Demand Loading

- [x] 5.1 Modify `BaseAgent._build_system_prompt()` to include skill catalog (names only)
- [x] 5.2 Add `load_skill` tool to `backend/app/core/tools/builtin.py`
- [x] 5.3 Implement skill content caching with TTL
- [x] 5.4 Add cache invalidation on skill update
- [x] 5.5 Update `backend/scripts/seed_tools.py` with `load_skill` tool definition
- [x] 5.6 Write tests: `tests/core/agents/test_skill_loading.py`

## 6. Integration and Testing

- [x] 6.1 Update `backend/app/core/tools/registry.py` to register all new tools
- [ ] 6.2 Create integration test: `tests/api/routes/test_workflows_enhanced.py`
- [ ] 6.3 Test context compression in long workflow scenario
- [ ] 6.4 Test subagent isolation with orchestrator workflow
- [ ] 6.5 Test task graph with dependent tasks
- [ ] 6.6 Test background task execution and notification
- [ ] 6.7 Test skill on-demand loading end-to-end
- [ ] 6.8 Run full test suite: `uv run pytest tests/ -v`

## 7. Documentation

- [ ] 7.1 Update `CLAUDE.md` with new agent capabilities
- [ ] 7.2 Document new tools in `backend/app/core/tools/README.md` (create if needed)
- [ ] 7.3 Add example workflow using task graph
