## ADDED Requirements

### Requirement: Draft preview button
The draft editor SHALL provide a "预览" button that opens a preview modal showing how the content will appear when published to WeChat MP.

#### Scenario: Open preview modal
- **WHEN** user clicks "预览" button on draft editor
- **THEN** frontend calls POST /drafts/{id}/preview
- **THEN** modal displays rendered HTML with WeChat MP styling
- **THEN** modal shows draft title and close button

### Requirement: Draft publish button
The draft editor SHALL provide a "发布到公众号" button that initiates the publish workflow.

#### Scenario: Open publish dialog
- **WHEN** user clicks "发布到公众号" button
- **THEN** if WeChat MP is not configured, show error toast "请先配置微信公众号"
- **THEN** if WeChat MP is configured, open publish confirmation dialog

#### Scenario: Publish confirmation dialog
- **WHEN** publish dialog opens
- **THEN** dialog shows: draft title preview, target公众号 name, "确认发布" and "取消" buttons
- **THEN** dialog warns that publishing is irreversible

#### Scenario: Confirm publish
- **WHEN** user clicks "确认发布" in dialog
- **THEN** frontend calls POST /drafts/{id}/publish with confirmed=true
- **THEN** on success, show success toast with article link
- **THEN** on failure, show error toast with reason

### Requirement: Draft publish status indicator
The draft editor SHALL display publish status if the draft has been published.

#### Scenario: Show published status
- **WHEN** draft has existing successful publish history
- **THEN** editor shows "已发布" badge with link to published article
- **THEN** badge includes publish time
