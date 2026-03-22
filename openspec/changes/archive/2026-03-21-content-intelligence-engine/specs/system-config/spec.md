## ADDED Requirements

### Requirement: SystemConfig singleton document
The system SHALL maintain a single SystemConfig document in MongoDB; if none exists on startup, the system SHALL create one with default values.

#### Scenario: SystemConfig initialized on startup
- **WHEN** the application starts and no SystemConfig exists in MongoDB
- **THEN** system creates SystemConfig with defaults: kimi as default provider, interval_minutes=60, max_concurrent_fetches=3

### Requirement: LLM provider API key management with Fernet encryption
The system SHALL store and update API keys for each LLM provider (kimi, claude, openai) encrypted at rest using Fernet symmetric encryption.

The Fernet key SHALL be derived from SECRET_KEY using SHA256 + base64 encoding:
```python
fernet_key = base64.urlsafe_b64encode(
    hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
)
```
This ensures a valid 32-byte URL-safe base64 key regardless of SECRET_KEY length or format.

#### Scenario: API key stored encrypted
- **WHEN** user saves a Kimi API key via the settings endpoint
- **THEN** system encrypts the key with Fernet before persisting; raw key is never stored in plaintext

#### Scenario: API key masked in API response
- **WHEN** user calls GET /system-config
- **THEN** response shows masked values (first 4 + "***" + last 4 chars) for all API keys

#### Scenario: API key decrypted for LLM calls
- **WHEN** LLMClientFactory requests the API key for a provider
- **THEN** system decrypts the stored value in memory and passes it to the client constructor

### Requirement: Redis configuration
The system SHALL store Redis connection URL in config (REDIS_URL environment variable); Redis is used as Celery broker, result backend, and SSE pub/sub bus.

#### Scenario: Redis URL configured via environment
- **WHEN** application starts
- **THEN** REDIS_URL is read from environment (default: redis://localhost:6379/0) and used by both FastAPI and Celery worker processes

### Requirement: Scheduler configuration
The system SHALL store scheduler settings: default_interval_minutes and max_concurrent_fetches used when creating new Sources.

#### Scenario: New source uses default interval
- **WHEN** user creates a source without specifying interval_minutes
- **THEN** system uses SystemConfig.scheduler.default_interval_minutes as the interval

### Requirement: Analysis and writing model defaults
The system SHALL store default model_provider and model_id for analysis and writing workflows separately.

#### Scenario: New agent uses default model
- **WHEN** user creates a new AgentConfig without specifying model_provider
- **THEN** system assigns SystemConfig.writing.default_model_provider and default_model_id

### Requirement: Environment variable import on first start
The system SHALL automatically import LLM API keys from environment variables (KIMI_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY) into SystemConfig on first startup.

#### Scenario: API key imported from env on first start
- **WHEN** application starts for the first time and KIMI_API_KEY env var is set
- **THEN** system creates SystemConfig, encrypts and stores the key for kimi provider

### Requirement: System config update endpoint (superuser only)
The system SHALL expose PATCH /system-config accessible only to superusers.

#### Scenario: Non-superuser cannot update system config
- **WHEN** a regular user calls PATCH /system-config
- **THEN** system returns HTTP 403 Forbidden
