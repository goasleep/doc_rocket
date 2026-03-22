## ADDED Requirements

### Requirement: Tool document model
The system SHALL store Tools in MongoDB with fields: name (unique), description (shown to LLM), parameters_schema (JSON Schema object), executor ("python"|"script"), function_name (Python registry key or script command template), is_builtin (bool), is_active (bool), category (string tag), created_at.

#### Scenario: Tool document created by seed script
- **WHEN** the seed script runs
- **THEN** all built-in tools exist in the tools collection; re-running the seed script does not create duplicates (upsert by name)

### Requirement: Built-in tool registry
The system SHALL maintain a static Python dict `TOOL_REGISTRY: dict[str, Callable]` mapping tool function_name to its async implementation; only tools present in both TOOL_REGISTRY and the DB tools collection (is_active=True) are available to agents.

#### Scenario: Registry contains all built-in tools
- **WHEN** application starts
- **THEN** TOOL_REGISTRY contains entries for: web_search, fetch_url, activate_skill, run_skill_script, query_articles, save_draft

#### Scenario: Disabled tool not available to agent
- **WHEN** a tool has is_active=False in DB
- **THEN** it is excluded from the tool schema injected into the agent's LLM call, even if present in TOOL_REGISTRY

### Requirement: Tool CRUD API
The system SHALL provide REST endpoints for listing and updating tools (description, is_active, category); creating and deleting built-in tools SHALL be restricted to system operations only.

#### Scenario: List tools
- **WHEN** superuser calls GET /tools
- **THEN** system returns all tools with their current is_active state and category

#### Scenario: Disable a tool
- **WHEN** superuser PATCHes /tools/{id} with is_active=false
- **THEN** subsequent agent runs do not include this tool in their available tool schema

### Requirement: Tool seed script (idempotent)
The system SHALL provide a seed script that creates or updates all built-in tool documents using upsert-by-name; running the script multiple times SHALL produce the same result.

#### Scenario: Seed script is idempotent
- **WHEN** seed script runs twice
- **THEN** tool count in DB does not increase; existing tools are updated if schema changed

#### Scenario: Seed script creates missing tools
- **WHEN** a built-in tool is missing from DB (e.g., after DB reset)
- **THEN** seed script creates it with default description and schema

### Requirement: Tool dispatch in agent loop
The system SHALL resolve tool calls returned by the LLM to TOOL_REGISTRY functions and execute them with the provided arguments; results SHALL be appended to the message history as tool_result messages.

#### Scenario: Tool call dispatched and result returned
- **WHEN** LLM returns a tool_call with name="web_search" and arguments={"query": "AI trends"}
- **THEN** system calls TOOL_REGISTRY["web_search"](query="AI trends"), appends assistant message with tool_calls, then tool message with result to history, continues loop

#### Scenario: Unknown tool call
- **WHEN** LLM returns a tool_call with a name not in TOOL_REGISTRY
- **THEN** system appends tool_result message with content="Tool 'X' is not available", loop continues

#### Scenario: Tool raises exception
- **WHEN** a tool function raises an exception during execution
- **THEN** system catches it, appends tool_result with error description, increments per-tool consecutive-failure counter; if the same tool fails on 3 consecutive calls (without a successful call in between), loop terminates with current best output

### Requirement: web_search built-in tool
The system SHALL provide a web_search tool that accepts a query string and returns a list of search result titles, URLs, and snippets.

#### Scenario: web_search returns results
- **WHEN** agent calls web_search(query="FastAPI best practices")
- **THEN** tool returns structured results with title, url, snippet for each result

### Requirement: fetch_url built-in tool
The system SHALL provide a fetch_url tool that fetches the text content of a URL and returns it truncated to a configurable max length; parameters: `url: str` (required), `max_chars: int` (optional, default 8000); when truncated, result SHALL end with "[内容已截断]".

#### Scenario: fetch_url returns page text
- **WHEN** agent calls fetch_url(url="https://example.com/article")
- **THEN** tool returns the page's main text content stripped of HTML tags, truncated to max_chars characters

#### Scenario: fetch_url handles error
- **WHEN** URL is unreachable or returns non-200 status
- **THEN** tool returns error string with status code; agent receives this as tool result

#### Scenario: fetch_url truncates long content
- **WHEN** page text exceeds max_chars
- **THEN** content is truncated and "[内容已截断]" is appended to the result

### Requirement: ScriptExecutor abstraction
The system SHALL define a `ScriptExecutor` abstract interface with a single `run(command, scripts, working_dir, timeout) -> ExecutionResult` method; `LocalExecutor` SHALL be the default implementation.

#### Scenario: LocalExecutor writes scripts to temp dir
- **WHEN** LocalExecutor.run() is called with script files and a command
- **THEN** it writes all script files to a temporary directory, executes the command via subprocess, captures stdout/stderr, cleans up temp dir, returns ExecutionResult

#### Scenario: DockerExecutor interface reserved
- **WHEN** executor="docker" is configured
- **THEN** system raises NotImplementedError with message "DockerExecutor not yet implemented"
