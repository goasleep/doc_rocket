## Why

当前文章分析系统存在明显局限：单步 LLM 调用缺乏深度推理，评分没有参考依据且缺乏解释，过程追溯只有一步无法看到思考过程，也无法搜索类似文章进行对比分析。需要基于 React Agent 模式重构分析系统，实现多步骤推理、对比分析、详细评分解释和完整过程追溯。

## What Changes

- **新增** `ReactAnalyzerAgent` - 基于 React Agent 模式的多步骤分析器，完全替换现有 `AnalyzerAgent`
- **新增** 质量评分标准模型 (`QualityRubric`) - 支持版本管理，明确各维度评分标准
- **新增** 外部参考文章模型 (`ExternalReference`) - 存储外部搜索到的参考文章，支持双向关联
- **扩展** `ArticleAnalysis` 模型 - 新增评分详情（带解释）、对比参考、改进建议、多步骤追溯
- **新增** 分析工具 - `search_similar_articles`, `save_external_reference`, `compare_with_reference`
- **新增** 外部参考文章管理页面 - 列表、搜索、筛选、查看引用关系
- **扩展** `AgentConfig.role` 枚举 - 新增 `analyzer` 角色
- **移除** 现有 `AnalyzerAgent` 单步分析实现

## Capabilities

### New Capabilities
- `react-analyzer`: React Agent 模式的文章分析引擎，支持多步骤推理、工具调用、对比分析
- `quality-rubric`: 质量评分标准管理，支持版本化和多维度评分配置
- `external-reference`: 外部参考文章管理，支持双向关联和引用追踪

### Modified Capabilities
- `article-analysis`: 分析结果数据结构扩展，新增评分详情、对比参考、改进建议、多步骤追溯

## Impact

- **后端**: 新增/修改数据模型、Agent 实现、工具函数、API 路由
- **前端**: 新增外部参考管理页面、分析详情展示组件更新
- **数据库**: 新增 `quality_rubrics`, `external_references` 集合，`article_analyses` 集合字段扩展
- **API**: 新增 `/external-references` 路由，扩展 `/analyses` 响应结构
- **兼容性**: 旧分析数据兼容（新字段有默认值），支持重新分析更新
