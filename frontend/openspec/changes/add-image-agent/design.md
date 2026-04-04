## Context

当前系统采用多 Agent 协作的写作工作流架构：
- **OrchestratorAgent**: 协调整个写作流程
- **WriterAgent**: 生成文章内容
- **EditorAgent**: 编辑优化内容
- **ReviewerAgent**: 审核内容质量

工作流通过 Celery 异步执行，使用 Redis 进行事件流推送。已集成七牛云 OSS 用于文件存储。

需要新增 **ImageAgent** 作为独立的图片生成 Agent，采用被动模式工作——由 Orchestrator 在适当时机调用，而非自主决定何时生成图片。

## Goals / Non-Goals

**Goals:**
- 创建独立的 ImageAgent 类，遵循现有 Agent 架构模式
- 实现图像生成工具接口，预留国内服务接入点
- 集成七牛云 OSS 存储生成的图片
- 扩展 WorkflowRun 模型存储图片元数据
- 前端展示生成的图片

**Non-Goals:**
- 不实现具体的国内 AI 图像服务（仅预留接口）
- 不决定图片数量、位置和风格（由 EditorAgent 决定）
- 不支持图片编辑/修改功能（仅生成）
- 不实现图片缓存/CDN 优化

## Decisions

### 1. ImageAgent 作为独立 Agent（而非 Skill）
**选择**: 创建独立的 ImageAgent 类，继承 BaseAgent

**理由**:
- 图片生成是复杂的多步骤任务（分析内容→生成提示词→调用API→上传存储），需要独立的配置和生命周期
- 与 WriterAgent/EditorAgent 保持架构一致性
- 便于后续扩展（如支持多种图像服务、图片风格配置等）

**替代方案**: 作为 Skill 绑定到 WriterAgent
-  rejected: 会增加 WriterAgent 复杂度，且不符合单一职责原则

### 2. 被动模式调用
**选择**: ImageAgent 不主动判断是否需要生成图片，由 Orchestrator 或 EditorAgent 决定调用时机

**理由**:
- 图片需求判断（数量、位置、风格）属于编辑决策，应由 EditorAgent 负责
- ImageAgent 只专注于"根据要求生成图片"这一单一职责
- 便于用户通过配置控制是否启用图片生成功能

### 3. 图像服务接口预留
**选择**: 定义抽象接口 `ImageGenerator`，当前提供占位实现

**理由**:
- 用户计划接入国内服务，但具体服务未定
- 接口预留后，后续只需实现具体 Provider 即可
- 便于单元测试（可 Mock 实现）

### 4. 图片存储在 WorkflowRun 中
**选择**: 扩展 WorkflowRun 模型，新增 `generated_images` 字段存储图片元数据

**数据结构**:
```python
class GeneratedImage(BaseModel):
    id: uuid.UUID
    prompt: str  # 使用的提示词
    url: str     # 七牛云 URL
    position: str  # 插入位置标记（如 "cover", "section-1"）
    created_at: datetime
```

**理由**:
- 图片是工作流的产物，与文章输出关联
- 便于前端根据工作流 ID 获取相关图片
- 支持一张文章配多张图片

### 5. 前端展示方式
**选择**: 在工作流详情页底部新增"生成的图片"区域，以网格形式展示

**理由**:
- 图片是工作流输出的一部分，与最终文章并列展示
- 网格布局便于查看多张图片
- 点击图片可查看大图和提示词详情

## Risks / Trade-offs

**[Risk] 图像生成服务延迟高，阻塞工作流**
→ Mitigation: 图像生成作为可选步骤，配置 `max_wait_time` 超时后跳过；后续可改为异步后台生成

**[Risk] 图片生成成本不可控**
→ Mitigation: 在 AgentConfig 中配置 `max_images_per_article` 限制数量；记录 TokenUsage 追踪成本

**[Risk] 图片质量不稳定**
→ Mitigation: 提示词由 LLM 优化生成；保存提示词便于人工重试

**[Trade-off] 图片存储成本**
- 七牛云 OSS 按量付费，大量图片可能产生费用
- 缓解: 图片压缩后再上传；定期清理未使用的图片

## Migration Plan

1. **数据库**: WorkflowRun 集合新增 `generated_images` 字段（可选，无需迁移旧数据）
2. **配置**: 在 Agent 配置页面手动添加 ImageAgent 配置
3. **部署**: 无中断部署，新功能默认关闭，通过配置启用
4. **回滚**: 删除 ImageAgent 配置即可回滚

## Open Questions

1. 国内 AI 图像服务的具体选型（通义万相、文心一格、智谱等）
2. 是否需要图片内容安全审核（涉黄/涉暴检测）
3. 是否支持用户上传参考图进行风格迁移
