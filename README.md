# 爆品内容引擎 (Content Intelligence Engine)

多 Agent 驱动的爆款内容创作平台，集文章订阅抓取、AI 分析、仿写流水线、人工审核于一体。

## 功能特性

- **订阅源管理**：支持 API 接口和 RSS 两种方式，定时自动抓取文章
- **AI 内容分析**：提取 Hook 类型、写作框架、情绪触发、质量评分等维度
- **多 Agent 写作流水线**：Writer → Editor → Reviewer 三段式，SSE 实时进度
- **人工审核门控**：Reviewer 完成后暂停，由人工选定标题后进入草稿
- **草稿编辑器**：Markdown 分屏编辑，支持去AI味改写、导出 `.md` 文件
- **多 LLM 提供商**：Kimi（月之暗面）/ Claude / OpenAI，按需切换
- **API Key 加密**：Fernet 加密存储于 MongoDB，系统设置页面管理

## 技术栈

| 层次 | 技术 |
|---|---|
| **Backend** | FastAPI + Beanie ODM + MongoDB + Motor |
| **Auth** | fastapi-users v15（JWT，argon2 密码哈希） |
| **异步任务** | Celery + Redis（celery-redbeat 定时调度） |
| **LLM** | Kimi / Claude / OpenAI（可扩展抽象层） |
| **Frontend** | React 19 + TypeScript + Vite + TanStack Router/Query |
| **UI** | Tailwind CSS v4 + shadcn/ui |
| **包管理** | `uv`（Python）、`pnpm`（JS） |
| **基础设施** | Docker Compose + Traefik |

## 快速开始

### 1. 克隆并启动

```bash
git clone <repo-url> content-engine
cd content-engine
cp .env.example .env   # 按需修改
docker compose up -d
```

访问：
- 前端：http://localhost:5173
- API 文档：http://localhost:8000/docs
- Flower（Celery 监控）：http://localhost:5555

### 2. 配置 LLM API Key

启动后登录管理员账号，进入 **系统设置 → API Keys** 页面，填写以下任意一个提供商的 Key：

| 提供商 | 环境变量（`.env` 中预填）| 说明 |
|---|---|---|
| Kimi（月之暗面）| `KIMI_API_KEY` | 推荐，中文效果最佳 |
| Anthropic Claude | `ANTHROPIC_API_KEY` | 英文能力强 |
| OpenAI | `OPENAI_API_KEY` | 通用 |

也可以在 `.env` 中直接填写，服务启动时会自动加密存入数据库。

### 3. 开始使用

1. **订阅源** → 添加 API/RSS 订阅源，点击「立即抓取」
2. **手动投稿** → 粘贴文章正文或输入 URL
3. **文章库** → 选中已分析文章，点击「触发仿写」
4. **工作流** → 实时查看 Writer/Editor/Reviewer 进度，审核后选标题
5. **仿写稿件** → 在编辑器中精修，使用「去AI味」润色，导出发布

## 环境变量

`.env` 文件关键配置：

```dotenv
# 基础（必填）
SECRET_KEY=<生成随机字符串>
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=<强密码>

# MongoDB
MONGODB_URL=mongodb://mongodb:27017
MONGODB_DB=app

# Redis（Celery broker）
REDIS_URL=redis://redis:6379/0

# LLM API Keys（至少填一个）
KIMI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

生成随机 SECRET_KEY：

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 开发

见 [development.md](./development.md)。

## 部署

见 [deployment.md](./deployment.md)。

## 架构概览

```
frontend/
├── src/routes/_layout/
│   ├── sources.tsx          # 订阅源管理
│   ├── submit.tsx           # 手动投稿
│   ├── articles/            # 文章库（列表 + 详情）
│   ├── agents.tsx           # Agent 配置
│   ├── workflow.tsx         # 工作流监控 + 审核
│   ├── drafts/              # 仿写稿件（列表 + 编辑器）
│   └── settings.tsx         # 系统设置（含 API Keys）
│
backend/app/
├── models/                  # Beanie Document 数据模型
├── core/
│   ├── llm/                 # LLM 抽象层（Kimi/Claude/OpenAI）
│   ├── agents/              # Fetcher/Analyzer/Writer/Editor/Reviewer
│   ├── redis_client.py      # async/sync Redis + SSE 流
│   └── encryption.py        # Fernet 加密
├── tasks/                   # Celery 异步任务
└── api/routes/              # FastAPI 路由（8 个模块）
```

## 测试

```bash
# 单元 + 任务 + 集成（需 MongoDB 测试实例）
MONGODB_URL=mongodb://localhost:27018 MONGODB_DB=test_app \
  uv run pytest tests/ -v

# 仅单元测试
uv run pytest tests/unit/ tests/tasks/ -v
```

全部 83 个测试覆盖加密、LLM factory、5 种 Agent、4 类 Celery 任务、8 个 API 路由模块及 SSE 流。

## License

MIT
