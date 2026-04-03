## 1. Backend - SystemConfig Extension

- [ ] 1.1 Add WechatMPConfig model to system_config.py with app_id, app_secret_encrypted, enabled fields
- [ ] 1.2 Add wechat_mp field to SystemConfig document with default factory
- [ ] 1.3 Update SystemConfigPublic to include wechat_mp field (with masked secret)
- [ ] 1.4 Update SystemConfigUpdate to support wechat_mp updates
- [ ] 1.5 Add encryption/decryption helpers for WeChat AppSecret (reuse Fernet pattern)

## 2. Backend - WeChat MP API Client

- [ ] 2.1 Create backend/app/core/wechat_mp.py module
- [ ] 2.2 Implement get_access_token() with caching (7200s TTL)
- [ ] 2.3 Implement validate_credentials() for config validation
- [ ] 2.4 Implement create_draft() API call to WeChat
- [ ] 2.5 Implement publish_draft() API call to WeChat
- [ ] 2.6 Implement get_account_info() to fetch公众号名称
- [ ] 2.7 Add error handling and error code mapping

## 3. Backend - Publish History Model

- [ ] 3.1 Create PublishHistory document model in models/publish_history.py
- [ ] 3.2 Add PublishHistory to models/__init__.py
- [ ] 3.3 Add PublishHistoryPublic and PublishHistoriesPublic schemas
- [ ] 3.4 Add PublishHistory to init_beanie() in db.py

## 4. Backend - API Routes

- [ ] 4.1 Add GET /system-config/wechat endpoint (superuser only, masked response)
- [ ] 4.2 Add PUT /system-config/wechat endpoint (superuser only, with validation)
- [ ] 4.3 Add POST /drafts/{id}/preview endpoint (Markdown to HTML conversion)
- [ ] 4.4 Add POST /drafts/{id}/publish endpoint (confirmed=true required)
- [ ] 4.5 Add GET /publish-history endpoint (paginated list)
- [ ] 4.6 Add GET /publish-history/{id}/status endpoint (check WeChat status)

## 5. Backend - Markdown to HTML Conversion

- [ ] 5.1 Add markdown library to pyproject.toml dependencies
- [ ] 5.2 Create markdown_to_wechat_html() function with WeChat CSS styles
- [ ] 5.3 Handle basic elements: headings, paragraphs, lists, bold, italic, links, blockquotes, code

## 6. Frontend - System Config Page

- [ ] 6.1 Add WeChatConfigCard component with AppID, AppSecret inputs
- [ ] 6.2 Add enabled toggle switch
- [ ] 6.3 Add "测试连接" button to validate credentials
- [ ] 6.4 Integrate into Settings page
- [ ] 6.5 Handle AppSecret masking (show placeholder if already set)

## 7. Frontend - Draft Editor Enhancements

- [ ] 7.1 Add "预览" button to draft editor toolbar
- [ ] 7.2 Create PreviewModal component showing HTML render
- [ ] 7.3 Add "发布到公众号" button
- [ ] 7.4 Create PublishConfirmDialog component
- [ ] 7.5 Show publish status badge if already published
- [ ] 7.6 Add link to published article

## 8. Frontend - Publish History Page

- [ ] 8.1 Create /publish-history route
- [ ] 8.2 Create PublishHistoryList component with table view
- [ ] 8.3 Show columns: title, target, status, time, actions
- [ ] 8.4 Add link to open published article
- [ ] 8.5 Add navigation menu item

## 9. Frontend - API Client Updates

- [ ] 9.1 Add WeChat config types to client schemas
- [ ] 9.2 Add publish history types to client schemas
- [ ] 9.3 Regenerate OpenAPI client (or add manual service functions)

## 10. Testing & Documentation

- [ ] 10.1 Test WeChat API client with mock responses
- [ ] 10.2 Test config validation flow
- [ ] 10.3 Test publish flow end-to-end
- [ ] 10.4 Add error handling for network failures
- [ ] 10.5 Update CLAUDE.md with WeChat MP setup instructions
