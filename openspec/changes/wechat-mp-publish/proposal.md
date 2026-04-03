## Why

当前平台的草稿编辑完成后，用户需要手动复制内容到微信公众号后台发布，流程繁琐且格式容易丢失。通过接入微信公众号发布API，用户可以直接从平台将编辑好的草稿一键发布到配置的公众号，大幅提升内容发布效率。

## What Changes

1. **新增微信公众号配置功能**
   - 在系统配置页面添加微信公众号（AppID + AppSecret）配置
   - 支持配置启用/禁用状态
   - AppSecret 加密存储，接口返回脱敏

2. **新增草稿预览功能**
   - 草稿编辑页面添加"预览"按钮
   - Markdown 自动转换为公众号兼容的 HTML
   - 弹窗展示渲染效果

3. **新增发布到公众号功能**
   - 草稿编辑页面添加"发布"按钮
   - 调用微信开放平台 API 创建并发布草稿
   - 发布前确认弹窗

4. **新增发布历史记录**
   - 记录每次发布的详情（草稿ID、标题、发布时间、目标公众号、文章链接、状态）
   - 新增发布历史页面展示记录列表
   - 支持查看发布失败原因

5. **扩展 SystemConfig 模型**
   - 添加 `wechat_mp` 配置字段

## Capabilities

### New Capabilities
- `wechat-mp-config`: 微信公众号配置管理（AppID/AppSecret 配置、加密存储、脱敏展示）
- `wechat-mp-publish`: 微信公众号发布功能（草稿预览、发布API调用、历史记录）

### Modified Capabilities
- `system-config`: 扩展配置模型，添加微信公众号配置字段
- `draft-management`: 添加发布相关按钮和交互（预览、发布到公众号）

## Impact

- **后端**: 新增 `wechat_mp.py` 模块（微信API封装）、发布历史模型和API、扩展 SystemConfig
- **前端**: 系统配置页面添加微信配置卡片、草稿编辑页面添加预览/发布按钮、新增发布历史页面
- **依赖**: 新增 `markdown` 库（MD转HTML）
- **数据库**: 新增 `publish_history` 集合
