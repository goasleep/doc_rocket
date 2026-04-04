## REMOVED Requirements

### Requirement: Tavily API key stored in SystemConfig
**Reason**: The Tavily API key is now managed via the TAVILY_API_KEY environment variable, removing the need for DB storage and UI-based key management.
**Migration**: Set TAVILY_API_KEY in your environment or .env file before deploying.

## MODIFIED Requirements

### Requirement: System config update endpoint (superuser only)
The system SHALL expose PATCH /system-config accessible only to superusers. The `search` field in the update body will no longer be used to set or retrieve a Tavily API key.

#### Scenario: GET system config no longer exposes Tavily key
- **WHEN** user calls GET /system-config
- **THEN** the response does not contain a raw or masked Tavily API key under the `search` field
