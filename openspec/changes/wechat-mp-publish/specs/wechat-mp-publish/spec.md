## ADDED Requirements

### Requirement: Draft preview as WeChat MP HTML
The system SHALL provide a preview endpoint that converts draft Markdown content to WeChat MP compatible HTML.

#### Scenario: Preview draft as HTML
- **WHEN** user calls POST /drafts/{id}/preview
- **THEN** system converts draft.content from Markdown to HTML using markdown library
- **THEN** system applies WeChat MP compatible CSS styles
- **THEN** system returns {title, html_content} for preview display

#### Scenario: Preview includes formatted content
- **WHEN** preview is generated
- **THEN** HTML includes proper formatting for: headings, paragraphs, lists, bold, italic, links, blockquotes, code blocks
- **THEN** content is wrapped in a container with WeChat MP style CSS

### Requirement: Publish draft to WeChat MP
The system SHALL allow publishing a draft to configured WeChat Official Account.

#### Scenario: Successfully publish draft
- **WHEN** user calls POST /drafts/{id}/publish with confirmed=true
- **THEN** system checks WeChat MP is enabled and configured
- **THEN** system fetches access_token from WeChat API
- **THEN** system creates draft article via WeChat /draft/add API
- **THEN** system submits draft for publishing via WeChat /freepublish/submit API
- **THEN** system creates PublishHistory record with status="success"
- **THEN** system returns {success: true, publish_id, article_url}

#### Scenario: Publish without confirmation
- **WHEN** user calls POST /drafts/{id}/publish without confirmed=true
- **THEN** system returns HTTP 400 with error message "Confirmation required"

#### Scenario: Publish when WeChat MP not configured
- **WHEN** user calls POST /drafts/{id}/publish but WeChat MP is not enabled or missing credentials
- **THEN** system returns HTTP 400 with error message "WeChat MP not configured"

#### Scenario: Publish fails due to WeChat API error
- **WHEN** WeChat API returns error (invalid token, content violation, etc.)
- **THEN** system creates PublishHistory record with status="failed" and error_message
- **THEN** system returns HTTP 502 with error details from WeChat

### Requirement: Publish history tracking
The system SHALL maintain a history of all publish attempts with details and status.

#### Scenario: Record successful publish
- **WHEN** draft is successfully published to WeChat MP
- **THEN** system creates PublishHistory with: draft_id, title, target_platform="wechat_mp", target_name (公众号名称), status="success", published_url, created_at

#### Scenario: Record failed publish
- **WHEN** draft publish fails
- **THEN** system creates PublishHistory with: draft_id, title, target_platform="wechat_mp", status="failed", error_message, created_at

#### Scenario: List publish history
- **WHEN** user calls GET /publish-history
- **THEN** system returns paginated list of PublishHistory records sorted by created_at descending

#### Scenario: Filter publish history by status
- **WHEN** user calls GET /publish-history?status=failed
- **THEN** system returns only records with matching status

### Requirement: Fetch publish status
The system SHALL provide endpoint to check publish status using WeChat publish_id.

#### Scenario: Check publish status
- **WHEN** user calls GET /publish-history/{id}/status
- **THEN** system queries WeChat API for publish status
- **THEN** system returns current status and any available article URL
