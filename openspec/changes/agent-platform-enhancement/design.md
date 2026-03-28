## Context

The current agent platform uses a simple linear workflow execution model where:
- `BaseAgent.run()` implements a basic iterative agent loop
- `OrchestratorAgent` coordinates writer/editor/reviewer agents through direct calls
- Skills are loaded with full content into system prompts
- Tasks execute sequentially without dependency management
- All tool execution is synchronous and blocking

This design is sufficient for simple workflows but hits scalability limits:
1. Long conversations exceed model context windows
2. Orchestrator context accumulates all subagent intermediate steps
3. Complex workflows cannot express parallelizable tasks with dependencies
4. Long-running tools block the entire agent loop
5. Skills waste tokens by loading unused content

## Goals / Non-Goals

**Goals:**
- Implement automatic context compression when token thresholds are exceeded
- Enable true subagent isolation with fresh contexts and summary-only returns
- Support DAG-based task dependencies with automatic unblocking
- Allow concurrent tool execution via Celery background tasks
- Optimize skill loading with two-tier system (catalog + on-demand)
- Maintain backward compatibility with existing agent configurations
- Provide complete test coverage for all new capabilities

**Non-Goals:**
- Multi-agent parallel execution within single workflow (future enhancement)
- Distributed agent execution across multiple servers
- Automatic skill discovery (skills must still be configured)
- Frontend workflow builder UI (minimal frontend changes only)
- Migration of existing workflow runs to new task graph model

## Decisions

### Context Compression Strategy
- **Decision**: Implement two-tier compression: microcompact (clear old tool results) and full compact (LLM summarization)
- **Rationale**: Microcompact is fast and preserves recent context; full compact uses LLM to preserve semantic meaning
- **Alternative considered**: Always use LLM summarization - rejected due to cost and latency for minor compression needs
- **Threshold**: 80,000 tokens trigger (configurable), based on typical 128K context window with 40% safety margin

### Subagent Isolation Model
- **Decision**: Fresh `messages[]` per subagent, return only final assistant message
- **Rationale**: Prevents parent context pollution while preserving subagent autonomy
- **Alternative considered**: Shared context with pruning - rejected due to complexity and risk of information loss
- **Agent types**: "Explore" (read/bash only) vs "general-purpose" (full tools) for security

### Task Graph Storage
- **Decision**: MongoDB documents with `blocked_by`/`blocks` arrays, not graph database
- **Rationale**: Existing infrastructure, sufficient for workflow-scale graphs, Beanie ODM integration
- **Alternative considered**: Neo4j or RedisGraph - rejected due to infrastructure complexity
- **Unlock mechanism**: On task completion, scan for tasks blocked by completed task and update status

### Background Task Implementation
- **Decision**: Use Celery with Redis broker, not asyncio subprocess
- **Rationale**: Existing Celery infrastructure, proper task persistence, monitoring via Flower
- **Alternative considered**: `asyncio.create_subprocess` - rejected due to lack of persistence and monitoring
- **Notification**: Polling-based check within agent loop, not push-based WebSocket

### Skill Loading Architecture
- **Decision**: Two-tier: names/descriptions in system prompt, full content via tool
- **Rationale**: Minimizes token usage while maintaining discoverability
- **Alternative considered**: Lazy loading based on task keywords - rejected due to unreliability
- **Cache**: Skill content cached in-memory after first load

## Risks / Trade-offs

**[Risk] Compression loses critical context** → Mitigation: Save full transcript to disk before compression; provide manual compression trigger for user control

**[Risk] Subagent timeouts leave parent hanging** → Mitigation: Configurable timeout with partial result return; parent can check subagent status

**[Risk] Task graph deadlocks** → Mitigation: Cycle detection on task creation; maximum graph depth limits

**[Risk] Background task result loss** → Mitigation: Celery result backend persistence; task result TTL of 24 hours

**[Risk] Skill loading latency** → Mitigation: In-memory caching; preload commonly used skills

## Migration Plan

1. **Phase 1**: Deploy new modules alongside existing code (no breaking changes)
2. **Phase 2**: Update orchestrator to use subagent isolation (opt-in via config)
3. **Phase 3**: Enable task graph for new workflows (existing workflows use linear mode)
4. **Phase 4**: Deprecate direct skill loading in favor of on-demand (6-month timeline)

**Rollback**: Feature flags for each capability allow individual disable

## Open Questions

1. Should subagent execution be logged separately or as part of parent workflow?
2. What is the optimal token threshold for compression across different models?
3. Should background tasks support callbacks or only polling?
