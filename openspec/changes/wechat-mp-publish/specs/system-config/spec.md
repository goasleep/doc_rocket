## MODIFIED Requirements

### Requirement: LLM provider API key management with Fernet encryption
The system SHALL store and update API keys for each LLM provider (kimi, claude, openai) encrypted at rest using Fernet symmetric encryption.

The Fernet key SHALL be derived from SECRET_KEY using SHA256 + base64 encoding:
```python
fernet_key = base64.urlsafe_b64encode(
    hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
)
```
This ensures a valid 32-byte URL-safe base64 key regardless of SECRET_KEY length or format.

**EXTENDED TO**: Also apply to WeChat MP AppSecret encryption.

#### Scenario: API key stored encrypted
- **WHEN** user saves a Kimi API key via the settings endpoint
- **THEN** system encrypts the key with Fernet before persisting; raw key is never stored in plaintext

#### Scenario: API key masked in API response
- **WHEN** user calls GET /system-config
- **THEN** response shows masked values (first 4 + "***" + last 4 chars) for all API keys
- **THEN** response also shows masked WeChat MP AppSecret if configured

#### Scenario: API key decrypted for LLM calls
- **WHEN** LLMClientFactory requests the API key for a provider
- **THEN** system decrypts the stored value in memory and passes it to the client constructor

## ADDED Requirements

### Requirement: WeChat MP configuration in SystemConfig
The SystemConfig document SHALL include wechat_mp field for storing WeChat Official Account credentials.

#### Scenario: SystemConfig includes WeChat MP defaults
- **WHEN** system creates default SystemConfig
- **THEN** wechat_mp field is initialized with {app_id: "", app_secret_encrypted: "", enabled: false}

### Requirement: System config returns WeChat MP status
The GET /system-config endpoint SHALL include WeChat MP configuration status.

#### Scenario: WeChat MP config in response
- **WHEN** user calls GET /system-config
- **THEN** response includes wechat_mp field with {app_id, app_secret_masked, enabled}
