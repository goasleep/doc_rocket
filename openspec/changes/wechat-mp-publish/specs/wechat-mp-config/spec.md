## ADDED Requirements

### Requirement: WeChat MP AppID and AppSecret configuration
The system SHALL allow superusers to configure WeChat Official Account (微信公众号) credentials including AppID and AppSecret in SystemConfig.

#### Scenario: Store WeChat MP credentials
- **WHEN** superuser updates system config with wechat_mp.app_id and wechat_mp.app_secret
- **THEN** system stores AppID in plaintext and encrypts AppSecret using Fernet (same mechanism as LLM API keys)
- **THEN** system stores enabled flag to control whether publishing is active

#### Scenario: AppSecret encrypted at rest
- **WHEN** system saves WeChat MP configuration
- **THEN** AppSecret is encrypted with Fernet before persistence; raw secret is never stored in plaintext

#### Scenario: Credentials masked in API response
- **WHEN** any user calls GET /system-config
- **THEN** response shows AppID in plaintext
- **THEN** response shows masked AppSecret (first 4 + "***" + last 4 chars) or empty string if not set

### Requirement: WeChat MP configuration validation
The system SHALL validate WeChat MP credentials by attempting to fetch access_token when configuration is saved or tested.

#### Scenario: Validate credentials on save
- **WHEN** superuser saves WeChat MP configuration
- **THEN** system attempts to fetch access_token from WeChat API
- **THEN** if credentials are invalid, system returns HTTP 400 with error message
- **THEN** if credentials are valid, configuration is saved

### Requirement: WeChat MP config update endpoint (superuser only)
The system SHALL expose endpoints for WeChat MP configuration accessible only to superusers.

#### Scenario: Get WeChat MP config
- **WHEN** superuser calls GET /system-config/wechat
- **THEN** system returns WeChat MP configuration with masked AppSecret

#### Scenario: Update WeChat MP config
- **WHEN** superuser calls PUT /system-config/wechat with {app_id, app_secret, enabled}
- **THEN** system validates and updates configuration
- **THEN** if app_secret is empty string, preserve existing secret (partial update)

#### Scenario: Non-superuser cannot access WeChat MP config
- **WHEN** a regular user calls GET or PUT /system-config/wechat
- **THEN** system returns HTTP 403 Forbidden
