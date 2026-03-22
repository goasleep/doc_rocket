# Agent Skills 学习文档

> 来源: https://agentskills.io — 开放标准，由 Anthropic 发起，现已被 Cursor、VS Code Copilot、Claude Code、OpenAI Codex 等主流 AI 工具采纳

---

## 一句话定义

**Agent Skills 不是函数调用，不是 API 工具，而是「可按需加载的指令包」。**

Skills 告诉 agent"怎么做某类任务"，而不是"调用某个函数"。

---

## 核心概念

### Skill 是什么？

一个 Skill 就是一个文件夹，里面至少有一个 `SKILL.md`：

```
my-skill/
├── SKILL.md          # 必须：元数据 + 指令
├── scripts/          # 可选：可执行脚本
├── references/       # 可选：参考文档
└── assets/           # 可选：模板、资源
```

`SKILL.md` 的格式：

```markdown
---
name: pdf-processing
description: 提取PDF文字、填写表单、合并文件。处理PDF时使用。
---

# PDF 处理

## 什么时候用这个 skill
当用户需要处理 PDF 文件时...

## 如何提取文字
使用 pdfplumber：
```python
import pdfplumber
with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```
```

关键字段：
- `name`：标识符（小写字母+连字符，最多64字符）
- `description`：**这是触发条件**，agent 根据它判断是否激活该 skill
- body：具体指令，Markdown 格式，无格式限制

---

## 三层渐进式加载（Progressive Disclosure）

这是 Agent Skills 最核心的设计理念：

```
阶段 1：目录发现（session 启动时）
  只加载 name + description（约 50-100 tokens/skill）
  agent 知道"有哪些 skill 可用"

阶段 2：指令激活（任务匹配时）
  加载完整 SKILL.md body（推荐 < 5000 tokens）
  agent 知道"这个 skill 怎么用"

阶段 3：资源按需（执行过程中）
  按需加载 scripts/、references/、assets/
  agent 知道"需要什么额外信息"
```

目的：20 个 skill 安装在系统里，但一次对话只 "支付" 实际用到的那几个的 token 成本。

---

## Skill 的工作流程

```
用户提问
    │
    ▼
Agent 扫描 skill 目录 → 读取所有 name + description
    │
    ▼
判断：当前任务匹配哪个 skill？
    │
    ├─ 匹配 → 加载该 skill 的完整 SKILL.md body
    │              │
    │              ▼
    │         Agent 遵照指令执行（可能调用 scripts/）
    │
    └─ 不匹配 → 用 agent 自身能力处理
```

---

## Skill 放在哪里？

标准约定的存放路径（按优先级）：

| 范围 | 路径 | 说明 |
|------|------|------|
| 项目级 | `<project>/.agents/skills/` | 跨 agent 工具兼容 |
| 项目级 | `<project>/.<client>/skills/` | 特定工具专用（如 `.claude/skills/`） |
| 用户级 | `~/.agents/skills/` | 全局可用 |
| 用户级 | `~/.<client>/skills/` | 特定工具全局 |

**优先级规则**：项目级 > 用户级（项目 skill 会覆盖同名用户 skill）

---

## Agent 实现 Skill 支持的 5 个步骤

按官方文档，一个支持 Skills 的 agent 需要做：

### Step 1：发现 Skill
- 扫描约定目录，找所有含 `SKILL.md` 的子文件夹
- 跳过 `.git/`、`node_modules/` 等
- 处理名称冲突（项目级优先）

### Step 2：解析 SKILL.md
- 提取 YAML frontmatter（name, description 等）
- 提取 Markdown body
- 容错处理（YAML 语法宽松，description 缺失则跳过）

### Step 3：向 LLM 公开 skill 目录
```xml
<available_skills>
  <skill>
    <name>pdf-processing</name>
    <description>提取PDF文字、填写表单。处理PDF时使用。</description>
    <location>/path/to/pdf-processing/SKILL.md</location>
  </skill>
</available_skills>
```
附带说明：「当任务匹配某 skill 的 description 时，用文件读取工具加载该 SKILL.md」

### Step 4：激活 Skill（两种方式）
- **文件读取激活**：LLM 用自身的文件读取工具直接读 SKILL.md（简单）
- **专用工具激活**：注册 `activate_skill(name)` 工具，返回格式化的 skill 内容（更可控）

### Step 5：管理 Skill 上下文
- 保护已激活 skill 的内容不被上下文压缩删掉
- 去重：同一 skill 不重复注入
- 可选：子 agent 模式（独立 session 执行 skill）

---

## 好的 Skill 写作规范

1. **description 是触发器**，要包含具体关键词，不要写 "帮助处理PDF"，要写 "提取PDF文字、填写PDF表单、合并PDF文件，当用户提到PDF、表单、文档提取时使用"

2. **body 写 agent 不知道的事**，不要解释"什么是PDF"，直接写用哪个库、哪个命令

3. **控制粒度**：
   - 固定的、容易出错的步骤 → 严格规定
   - 灵活的、有多种方案的 → 给默认值 + 备选

4. **Gotchas 章节高价值**：把那些"不说会踩坑"的知识写进去

5. **体积控制**：`SKILL.md` 建议 < 500 行，细节放 `references/`

---

## 与"工具调用（Function Calling）"的本质区别

这是理解 Agent Skills 的关键：

| | Agent Skills | Function Calling / Tool Use |
|---|---|---|
| 本质 | 指令包（知识/流程） | 可执行函数（代码） |
| 格式 | Markdown 文档 | JSON Schema + Python 函数 |
| agent 如何使用 | 读取后遵照指令行动 | 调用函数，得到返回值 |
| 谁执行 | agent 自己（根据指令） | 宿主环境执行代码 |
| 适合什么 | 复杂工作流、领域知识、流程规范 | 数据查询、外部 API、系统操作 |
| 典型例子 | "如何写一份法律合同审查报告" | `search_web("query")` |

**Skills 和 Tools 不是互斥的，而是互补的：**
- Skill 的 body 里面可以指令 agent 去调用 tool
- 例如：`web-research` skill 里写着"用 web_search 工具搜索，然后按这个格式整理结果..."

---

## 谁在用这个标准？

截至 2026 年，已支持 Agent Skills 的工具：
- **Anthropic**：Claude Code、Claude.ai
- **Microsoft/GitHub**：VS Code Copilot、GitHub Copilot
- **OpenAI**：OpenAI Codex
- **JetBrains**：Junie
- **Google**：Gemini CLI
- **其他**：Cursor、OpenHands、Goose、Roo Code、Spring AI、Laravel Boost...

---

## 示例：一个最简单的 Skill

```
.agents/skills/roll-dice/SKILL.md
```

```markdown
---
name: roll-dice
description: 掷骰子，生成真随机数。当用户要求掷骰子（d6、d20等）时使用。
---

掷骰子时，运行以下命令：

```bash
shuf -i 1-<sides> -n 1
```

将 `<sides>` 替换为骰子面数（如 6 面骰用 6，20 面骰用 20）。
```

当用户说"帮我掷一个 d20"，agent 识别到匹配，加载这个文件，按照指令运行 bash 命令，返回 1-20 的随机数。

---

## 总结：Agent Skills 解决什么问题？

**问题**：agent 很强，但不了解你的团队流程、项目惯例、领域知识。

**解法**：把这些知识写成 Skill（Markdown 文件），agent 按需加载，变成"了解你的 agent"。

**优势**：
- 写一次，跨 agent 工具复用（Cursor 里写的 skill，Claude Code 也能用）
- 版本控制（skills 放进 git）
- 渐进加载（不浪费 context window）
- 人可读（不是二进制，随时 review 和改进）
