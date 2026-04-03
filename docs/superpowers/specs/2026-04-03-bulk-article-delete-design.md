# 批量删除文章 + 前端分页设计文档

## 目标

为文章库增加批量删除功能和前端分页，提升数据管理和页面性能。

## 需求确认

- 用户必须勾选文章后，才能执行批量删除。
- 删除为物理删除：直接从 MongoDB 移除 `Article` 和关联的 `ArticleAnalysis`。
- 前端文章列表增加分页组件，配合后端 `skip`/`limit` 参数，避免一次性加载过多数据。

## 架构

### 后端

1. **新增 API 端点** `POST /api/v1/articles/bulk-delete`
   - 请求体：`{ "ids": ["uuid1", "uuid2", ...] }`
   - 行为：
     - 先删除所有 `article_id` 在 `ids` 中的 `ArticleAnalysis` 记录。
     - 再删除所有 `id` 在 `ids` 中的 `Article` 记录。
     - 返回成功删除的文章数量。
   - 使用 Beanie 的 `delete_many` 或等效查询保证效率。
   - 无需事务（MongoDB 单机/副本集事务可选，但非必要）。

2. **现有列表端点不变**
   - `GET /api/v1/articles/` 已支持 `skip`、`limit`，前端分页直接复用。

### 前端

1. **分页组件**
   - 在 `ArticlesTableContent` 中引入分页状态 `page`（1-based）。
   - 每页默认大小：`10` 或 `20`。
   - 调用 `ArticlesService.listArticles` 时传入 `skip`、`limit`。
   - 使用 shadcn/ui 的 `<Pagination />` 组件（或项目现有分页实现）。

2. **批量删除交互**
   - 在已有的"已选 N 篇"工具栏中新增"批量删除"按钮（红色/次要变体）。
   - 点击后弹出 `confirm("确认删除选中的 N 篇文章？此操作不可恢复。")` 确认。
   - 成功后清空选择，刷新列表和分页计数。

3. **清空选择时机**
   - 分页切换时自动清空 `selected`，避免跨页选择状态混乱。

## 数据流

```
用户勾选文章 -> 点击"批量删除" -> confirm 确认
                                    |
                                    v
                         调用 ArticlesService.bulkDeleteArticles({ ids })
                                    |
                                    v
                        后端删除 ArticleAnalysis + Article
                                    |
                                    v
                         返回删除数量 -> 前端刷新 articles query + 清空 selected
```

## 错误处理

- 后端：如果 `ids` 为空列表，返回 400 Bad Request。
- 前端：删除失败时显示 `showErrorToast`，成功时显示 `showSuccessToast`。

## 测试

- 后端：为 `POST /articles/bulk-delete` 编写 Pytest 测试，验证物理删除和关联分析删除。
- 前端：通过手动验证分页和批量删除交互（目前无前端单元测试框架）。

## 风险

- 物理删除不可恢复，已通过 `confirm()` 二次确认降低误操作风险。
