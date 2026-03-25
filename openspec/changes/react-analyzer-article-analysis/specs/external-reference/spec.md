## Overview

外部参考文章管理系统，存储分析过程中引用的外部文章，支持双向关联查询。

## Requirements

### Functional Requirements

#### REQ-001: 存储结构
外部参考文章必须包含：
- url: 文章链接（唯一）
- title: 标题
- source: 来源（web_search/manual）
- content: 完整内容（10000字上限）
- content_snippet: 摘要
- fetched_at: 获取时间
- search_query: 搜索关键词
- metadata: 原始搜索结果元数据
- referencer_article_ids: 引用该参考的文章ID列表

#### REQ-002: 双向关联
- 从 ArticleAnalysis 可查询引用的外部参考
- 从 ExternalReference 可查询引用该参考的文章

#### REQ-003: 去重机制
- 同一 URL 只保存一条记录
- 多篇文章引用时，追加到 referencer_article_ids

#### REQ-004: 管理功能
- 列表查看所有外部参考（搜索、筛选、分页）
- 查看被哪些文章引用
- 重新抓取内容
- 手动添加参考文章
- 删除（仅未被引用时可删除）

#### REQ-005: API
- `GET /external-references`: 列表
- `GET /external-references/{id}`: 详情
- `POST /external-references`: 手动添加
- `PATCH /external-references/{id}`: 编辑
- `DELETE /external-references/{id}`: 删除
- `POST /external-references/{id}/refetch`: 重新抓取

### Data Model

```python
class ExternalReference(Document):
    id: UUID
    url: str  # unique
    title: str
    source: str  # web_search | manual
    content: str  # max 10000 chars
    content_snippet: str
    fetched_at: datetime
    search_query: str
    metadata: dict
    referencer_article_ids: list[UUID]
    created_at: datetime
```

### Frontend Pages

- `/external-references`: 列表页（搜索、筛选、分页）
- `/external-references/{id}`: 详情页（内容、引用关系）
