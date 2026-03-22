## ADDED Requirements

### Requirement: Skill document model
The system SHALL store Skills in MongoDB with fields: name (unique, kebab-case), description (used as trigger condition), body (full SKILL.md Markdown instructions), scripts (list of embedded script files with filename/content/language), needs_network (bool, default false), is_active (bool), source ("imported"|"user"; "builtin" is reserved for future use and has no seed data in this change), imported_from (nullable URL/path), created_at, updated_at.

#### Scenario: Create skill with scripts
- **WHEN** user POSTs to /skills with name, description, body, and a scripts array
- **THEN** system creates the Skill document in MongoDB and returns HTTP 201 with the created skill including assigned id

#### Scenario: Skill name must be unique
- **WHEN** user creates a skill with a name that already exists
- **THEN** system returns HTTP 409 Conflict

### Requirement: Skill CRUD API
The system SHALL provide REST endpoints for listing, retrieving, creating, updating, and deleting skills; all endpoints SHALL require superuser authentication.

#### Scenario: List active skills
- **WHEN** superuser calls GET /skills
- **THEN** system returns paginated list of all skills sorted by name ascending

#### Scenario: Update skill body
- **WHEN** superuser PATCHes /skills/{id} with a new body
- **THEN** system updates the skill; next agent run using this skill loads the updated body

#### Scenario: Delete skill
- **WHEN** superuser DELETEs /skills/{id}
- **THEN** system removes the skill document; AgentConfig.skills references to this name are silently ignored at runtime

### Requirement: Import skill from SKILL.md format
The system SHALL provide an import endpoint that accepts a raw SKILL.md string (or URL to fetch one) and converts it to a Skill document using the agentskills.io format as the source schema.

#### Scenario: Import from SKILL.md text
- **WHEN** user POSTs to /skills/import with raw SKILL.md content
- **THEN** system parses YAML frontmatter (name, description), extracts body, stores as Skill with source="imported", returns HTTP 201

#### Scenario: Import from URL
- **WHEN** user POSTs to /skills/import with a URL pointing to a raw SKILL.md file
- **THEN** system fetches the URL, parses SKILL.md format, creates Skill with imported_from=url, returns HTTP 201

#### Scenario: Import with invalid SKILL.md
- **WHEN** imported content is missing required frontmatter fields (name or description)
- **THEN** system returns HTTP 422 with validation error details

### Requirement: Skill catalog injection
The system SHALL inject a skill catalog into the agent's system prompt at the start of each agent run; the catalog SHALL contain only name and description for each active skill assigned to the agent.

#### Scenario: Catalog injected into system prompt
- **WHEN** an agent run starts and the agent has active skills assigned
- **THEN** system appends an `<available_skills>` XML block to the system prompt listing each skill's name and description

#### Scenario: No catalog when no skills assigned
- **WHEN** an agent has no skills assigned (empty skills list)
- **THEN** no `<available_skills>` block is added to the system prompt

### Requirement: activate_skill built-in tool
The system SHALL provide an `activate_skill` built-in tool that, when called by the agent with a skill name, fetches the full Skill.body from MongoDB and injects it into the conversation as a `<skill_content>` tagged message.

#### Scenario: Agent activates skill during loop
- **WHEN** agent calls activate_skill("web-research") as a tool call
- **THEN** system fetches Skill where name="web-research", returns body wrapped in `<skill_content name="web-research">...</skill_content>`, adds result to message history

#### Scenario: Activate non-existent skill
- **WHEN** agent calls activate_skill with a name that does not exist in DB
- **THEN** tool returns error string "Skill 'X' not found"; agent receives this as tool result and continues loop

### Requirement: Skill script execution
When a Skill body instructs the agent to run a bundled script, the agent SHALL execute it via the `run_skill_script` built-in tool which delegates to the configured ScriptExecutor.

#### Scenario: Run Python script from skill
- **WHEN** agent calls run_skill_script(skill_name="pdf-extract", script="scripts/extract.py", args="--input data.txt")
- **THEN** system fetches skill scripts from DB, writes to temp directory, executes via LocalExecutor, returns stdout/stderr/exit_code to agent

#### Scenario: Script timeout
- **WHEN** a skill script runs longer than the configured timeout (default 30s)
- **THEN** executor kills the process and returns ExecutionResult with exit_code=-1 and stderr="Timeout after 30s"
