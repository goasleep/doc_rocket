## Why

当前写作工作流生成的文章仅包含文字内容，缺乏视觉元素。为提升文章质量和阅读体验，需要引入 AI 图片生成功能，让工作流能够自动为文章生成配图。

## What Changes

- 新增 `ImageAgent` 专用 Agent 类，负责 AI 图片生成
- 新增图像生成工具接口（预留国内服务接入点）
- 扩展 `WorkflowRun` 模型，支持存储生成的图片信息
- 新增 `image-generation` 工具到工具注册表
- 更新前端工作流页面，展示生成的图片
- Agent 配置页面支持配置 ImageAgent

## Capabilities

### New Capabilities
- `image-agent`: AI 图片生成 Agent，被动模式工作，由 Orchestrator 调用
- `image-storage`: 图片存储管理，集成七牛云 OSS
- `workflow-image-support`: 工作流支持图片资源

### Modified Capabilities
- `workflow-orchestrator`: 扩展协调逻辑，支持在适当时机调用 ImageAgent

## Impact

- **后端**: 新增 `ImageAgent` 类、图像生成工具接口、WorkflowRun 模型扩展
- **前端**: 工作流详情页展示图片、工作流列表显示图片数量
- **数据库**: WorkflowRun 集合新增 `generated_images` 字段
- **外部依赖**: 预留国内 AI 图像生成服务接入点（当前为接口占位）
