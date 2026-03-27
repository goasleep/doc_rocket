## ADDED Requirements

### Requirement: Automatic context compression trigger
The system SHALL automatically trigger context compression when the estimated token count of the conversation messages exceeds a configurable threshold.

#### Scenario: Token threshold exceeded
- **WHEN** the agent loop estimates message tokens exceed the threshold (default 80,000)
- **THEN** the system SHALL invoke context compression before the next LLM call

#### Scenario: Configurable threshold
- **WHEN** an agent is initialized with a custom token_threshold
- **THEN** the system SHALL use that threshold for compression decisions

### Requirement: Microcompact compression
The system SHALL implement microcompact compression that clears old tool results while preserving the last 3 exchanges.

#### Scenario: Microcompact execution
- **WHEN** microcompact is triggered
- **THEN** the system SHALL remove tool_result blocks from messages older than the last 3 exchanges
- **AND** preserve all system messages and user instructions

### Requirement: Full context compression with LLM
The system SHALL implement full compression that saves the complete transcript and generates a summary using an LLM.

#### Scenario: Full compression execution
- **WHEN** full compression is triggered
- **THEN** the system SHALL save the complete message history to disk
- **AND** invoke an LLM to generate a semantic summary
- **AND** replace the message history with the summary plus recent context

#### Scenario: Transcript persistence
- **WHEN** full compression saves a transcript
- **THEN** the transcript SHALL be stored with a unique ID
- **AND** include timestamp and original message count metadata

### Requirement: Manual compression tool
The system SHALL provide a `compress_context` tool that agents can call to manually trigger compression.

#### Scenario: Manual compression invocation
- **WHEN** an agent calls `compress_context(reason="preparing for complex analysis")`
- **THEN** the system SHALL trigger full compression
- **AND** return a confirmation with the summary length and transcript ID

### Requirement: Compression state preservation
The system SHALL preserve critical state (active tools, pending operations) across compression.

#### Scenario: State preservation during compression
- **WHEN** compression is triggered with active background tasks
- **THEN** the system SHALL include active task references in the summary
- **AND** maintain task tracking integrity
