## Context

当前平台支持草稿编辑、AI改写、导出等功能，但缺少直接发布到外部平台的能力。用户需要手动复制内容到微信公众号后台，流程繁琐。

微信开放平台提供公众号管理API，包括草稿箱管理和发布能力。通过接入这些API，可以实现从平台直接发布到公众号。

## Goals / Non-Goals

**Goals:**
- 支持配置微信公众号 AppID + AppSecret
- 支持将草稿预览为公众号样式的HTML
- 支持一键发布草稿到配置的公众号
- 记录发布历史，支持查看发布状态和文章链接

**Non-Goals:**
- 图片上传到微信素材库（二期功能）
- 定时发布功能
- 多公众号管理（只支持配置一个公众号）
- 微信菜单管理、用户管理等其他API功能
- 支持其他平台（微博、知乎等）

## Decisions

### Decision: 使用微信开放平台接口而非微信公众平台
**Rationale:** 微信开放平台支持管理多个公众号，扩展性更好。虽然当前只实现单公众号配置，但为将来多账号管理预留空间。

**Alternatives considered:**
- 微信公众平台接口：每个公众号单独配置，适合单账号场景，但扩展性差

### Decision: AppSecret 使用 Fernet 对称加密
**Rationale:** 与现有 LLM API Key 加密机制保持一致，使用相同的 Fernet 密钥派生方式（SHA256 + base64）。简化代码维护，统一安全配置。

**Implementation:**
```python
fernet_key = base64.urlsafe_b64encode(
    hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
)
```

### Decision: Markdown 转 HTML 使用 Python `markdown` 库
**Rationale:** 后端转换可以复用微信API所需的HTML格式处理，前端只需展示结果。避免前端转换后后端再次处理的重复工作。

**CSS 样式:** 使用内联样式模拟微信公众号文章样式，确保预览和实际发布效果一致。

### Decision: 发布流程采用"预览 → 确认 → 发布"三步
**Rationale:** 微信公众号发布是不可逆操作，添加预览和确认步骤减少误操作。用户可以在预览阶段检查格式是否正确。

### Decision: PublishHistory 独立集合存储
**Rationale:** 发布历史与草稿生命周期分离，草稿删除后历史记录仍然保留用于审计。支持多次发布同一草稿（更新文章场景）。

## Risks / Trade-offs

**[Risk] 微信 API 调用频率限制** → Mitigation: 实现简单的 rate limit 缓存，access_token 缓存 7200 秒（微信有效期），避免频繁调用 token 接口。

**[Risk] 微信 API 返回中文错误信息** → Mitigation: 建立常见错误码映射表，提供友好的中文错误提示。

**[Risk] 图片外链可能失效** → Mitigation: 当前版本在预览中显示图片外链警告，提示用户二期将支持自动上传。文档中明确说明当前限制。

**[Risk] AppSecret 泄露** → Mitigation: 加密存储，接口脱敏返回，仅 superuser 可配置，操作日志记录。

**[Trade-off] 只支持文本，图片需手动处理** → 接受此限制作为 MVP 范围，二期实现图片自动上传。

## Migration Plan

1. **部署前:** 确保 `SECRET_KEY` 已设置（用于加密）
2. **部署:** 正常部署后端和前端代码
3. **配置:** superuser 在系统配置页面设置微信公众号 AppID + AppSecret
4. **验证:** 使用预览功能检查配置是否正确

**Rollback:** 如出现问题，可通过禁用 wechat_mp.enabled 快速关闭功能，不影响其他系统功能。

## Open Questions

None - requirements are clear for MVP scope.
