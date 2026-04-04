# 七牛云 OSS 集成设计文档

**Date:** 2026-04-04  
**Scope:** 为内容引擎引入七牛云 OSS，支持草稿编辑器图片上传，并在发布到微信公众号时自动同步七牛云图片到微信 MP。

---

## 1. 需求总结

| 维度 | 决策 |
|------|------|
| 上传入口 | 通用接口 `POST /uploads/image` + 草稿 MDEditor 内粘贴/拖拽上传 |
| 微信发布 | 发布时自动提取草稿中的七牛云图片，下载后上传到微信 MP 并替换 URL |
| 凭证配置 | 仅 `.env` 环境变量（开发/生产统一管理） |
| Bucket 类型 | 公共空间，返回直链 URL |

---

## 2. 架构设计

### 2.1 新增后端模块

#### `backend/app/core/qiniu_oss.py`

`QiniuOSSClient` 封装官方 SDK，提供异步友好的上传接口：

- 从 `Settings` 读取 `QINIU_ACCESS_KEY`、`QINIU_SECRET_KEY`、`QINIU_BUCKET`、`QINIU_DOMAIN`。
- `upload_file(data: bytes, filename: str) -> str`：使用 `qiniu.Auth` + `qiniu.put_data` 在线程池中执行，返回完整外链 URL。
- 单例/实例模式均可，推荐实例模式（与 `WeChatMPClient` 一致）。

#### `backend/app/api/routes/uploads.py`

新增路由模块，挂载到 `/api/v1/uploads`：

- `POST /uploads/image`
  - 接收 `UploadFile = File(...)`
  - 校验 MIME type：`image/jpeg`, `image/png`, `image/gif`, `image/webp`
  - 校验大小：≤ 5MB
  - 调用 `QiniuOSSClient.upload_file()`
  - 返回 `UploadImageResponse`：`{ "url": "https://domain/xxx.jpg" }`
  - 需要登录（`CurrentUser`）

#### `backend/app/api/routes/drafts.py` 修改

在 `publish_draft` 流程中，在 `markdown_to_wechat_html()` 之前插入图片同步逻辑：

1. 用 `extract_images_from_markdown(content)` 提取所有图片 URL。
2. 过滤出属于 `QINIU_DOMAIN` 的图片 URL。
3. 对每个七牛云图片并行或串行处理：
   - `httpx.AsyncClient` 下载图片 bytes
   - `WeChatMPClient.upload_image(image_data, filename)` 上传到微信 MP
   - 在 `content` 中把原 URL 替换为微信返回的 `mmbiz.qpic.cn` URL
4. 把替换后的内容传给 `markdown_to_wechat_html()` 和后续 `add_draft()` / `submit_publish()` 流程。

异常处理：
- 单张图片下载或上传失败时记录 warning，保留原 URL（不阻断发布）
- 如果七牛云未配置（`QINIU_DOMAIN` 为空），跳过同步逻辑

### 2.2 环境变量

在 `.env` 模板和 `backend/app/core/config.py` 中新增：

```python
QINIU_ACCESS_KEY: str = ""
QINIU_SECRET_KEY: str = ""
QINIU_BUCKET: str = ""
QINIU_DOMAIN: str = ""  # 如 https://cdn.example.com
```

### 2.3 前端修改

#### `frontend/src/routes/_layout/drafts/$id.tsx`

为 `MDEditor` 增加图片粘贴和拖拽上传能力：

- `onPaste`：从 `ClipboardEvent` 中读取 `files`，过滤出图片文件，调用 `POST /uploads/image`。
- `onDrop`：从 `DragEvent` 中读取 `files`，同样处理。
- 上传成功后，通过 `event.preventDefault()` + 在当前光标/拖拽位置插入 `![图片描述](url)` 到 `content`。
- 使用 `fetch` 或 TanStack Query mutation 调用上传接口。
- 上传中显示轻量提示（toast 或 inline indicator）。

**不修改** `SystemSettings.tsx（因为配置走 `.env`）。

---

## 3. 数据流

```
用户粘贴图片到 MDEditor
        ↓
前端调用 POST /uploads/image
        ↓
后端：QiniuOSSClient.upload_file() → 返回直链 URL
        ↓
前端插入 ![描述](https://cdn.example.com/xxx.jpg)
        ↓
（后续编辑、预览均正常显示）
        ↓
用户点击「发布到公众号」
        ↓
后端 publish_draft：
  extract_images_from_markdown(content)
        ↓
  过滤出匹配 QINIU_DOMAIN 的 URL
        ↓
  下载图片 → WeChatMPClient.upload_image() → 替换为微信 URL
        ↓
  markdown_to_wechat_html(replaced_content)
        ↓
  add_draft() → submit_publish()
```

---

## 4. 错误处理策略

| 场景 | 行为 |
|------|------|
| 七牛云未配置 | `.env` 留空时，上传接口返回 503；发布流程跳过图片同步 |
| 上传非图片文件 | 返回 400 Bad Request |
| 上传文件 > 5MB | 返回 413 Payload Too Large |
| 七牛云 SDK 上传失败 | 抛出 HTTPException 500，带原始错误信息 |
| 发布时单张七牛图片下载失败 | log warning，保留原 URL，继续发布 |
| 发布时单张七牛图片上传到微信失败 | log warning，保留原 URL，继续发布 |

---

## 5. 依赖变更

**Backend**
- 新增 `qiniu>=7.13.0` 到 `backend/pyproject.toml`
- `python-multipart` 已存在，无需新增

**Frontend**
- 不新增依赖，复用现有 `fetch`/`useMutation`

---

## 6. 测试策略

- 后端 `uploads` 路由单元测试（使用 monkeypatch 替换 `QiniuOSSClient.upload_file`，避免真实上传）
- `drafts.py` 发布流程测试：mock 七牛图片下载和微信 upload_image，验证内容中 URL 被正确替换
- 前端端到端测试：在草稿编辑器中粘贴/拖拽图片，验证 markdown 中插入 URL

---

## 7. OpenAPI Client 更新

后端变更完成后需要重新生成前端 client：

```bash
bash scripts/generate-client.sh
```

---

## 8. 部署检查项

- [ ] `.env` 中已配置 `QINIU_ACCESS_KEY`、`QINIU_SECRET_KEY`、`QINIU_BUCKET`、`QINIU_DOMAIN`
- [ ] 后端 `docker compose ps` 状态正常
- [ ] `POST /api/v1/uploads/image` 能成功返回 URL
- [ ] 草稿编辑器内粘贴图片后 markdown 正确插入外链
- [ ] 发布到公众号时七牛云图片被替换为微信 MP 域名
