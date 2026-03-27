## ADDED Requirements

### Requirement: Two-tier skill loading system
The system SHALL implement a two-tier skill loading system where only skill names and descriptions are loaded into the system prompt, with full content loaded on-demand via tool call.

#### Scenario: System prompt with skill catalog
- **WHEN** an agent is initialized with skills configured
- **THEN** the system prompt SHALL include only skill names and descriptions
- **AND** SHALL NOT include full skill body content
- **AND** include instructions to use `load_skill(name)` to access full content

#### Scenario: Skill loading via tool
- **WHEN** an agent calls `load_skill(name)`
- **THEN** the full skill body SHALL be returned as a tool result
- **AND** be formatted with `<skill name="{name}">` XML tags

### Requirement: Skill catalog format
The system SHALL format the skill catalog in system prompts using consistent XML-style tags.

#### Scenario: Catalog format
- **WHEN** multiple skills are available
- **THEN** the system prompt SHALL include `<available_skills>` section
- **AND** each skill SHALL be formatted as `<skill name="{name}">{description}</skill>`

### Requirement: Skill caching
The system SHALL cache loaded skill content to avoid repeated database queries.

#### Scenario: Skill cache hit
- **WHEN** `load_skill(name)` is called for a recently loaded skill
- **THEN** the cached content SHALL be returned
- **AND** no database query SHALL be executed

#### Scenario: Cache invalidation
- **WHEN** a skill is updated in the database
- **THEN** the cached version SHALL be invalidated
- **AND** subsequent loads SHALL fetch fresh content

### Requirement: Skill availability checking
The system SHALL provide clear error messages for unavailable skills.

#### Scenario: Unknown skill request
- **WHEN** `load_skill(name)` is called with a non-existent skill
- **THEN** the error message SHALL list available skills
- **AND** suggest checking the skill name

#### Scenario: Inactive skill request
- **WHEN** `load_skill(name)` is called for an inactive skill
- **THEN** the system SHALL return an error indicating the skill is inactive

### Requirement: Backward compatibility
The system SHALL maintain backward compatibility with existing skill activation mechanism.

#### Scenario: Explicit skill activation
- **WHEN** an agent calls `activate_skill(name)` (legacy method)
- **THEN** the skill SHALL be loaded and activated as before
- **AND** continue to function for existing agent configurations
