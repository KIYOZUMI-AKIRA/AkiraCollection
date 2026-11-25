# PersonalChief · 私厨 🍳

> 你的 AI 私人厨师：拍一张食材照片（或直接输入食材清单），它会识别食材、联网检索菜谱、按「营养 + 难度」双维度打分排序，输出一份结构化的菜谱推荐报告，并且记得你们聊过的每一轮。

## 功能特性

- 📷 **多模态识别**：支持食材照片（图片 URL）或纯文字食材清单
- 🔍 **智能菜谱检索**：调用 Tavily 联网搜索，以「可用食材清单」为核心关键词查找菜谱
- ⭐ **双维度评分**：从营养价值和制作难度两个维度量化打分，简单又营养的菜谱排名靠前
- 📋 **结构化报告**：输出包含食谱信息、得分、推荐理由、参考图片的推荐报告
- 🧠 **会话记忆**：基于 LangGraph + PostgreSQL checkpoint，按 `thread_id` 保存多轮对话上下文
- ☁️ **图片上传**：阿里云 OSS 预签名 URL，前端直传、后端只签发
- 💬 **流式输出**：对话接口逐块流式返回回复内容

## 技术栈

| 层 | 技术 |
| --- | --- |
| 语言 / 环境 | Python 3.11（`>=3.10,<3.12`）、uv、Docker |
| Web 框架 | FastAPI（含静态前端托管 + CORS） |
| 智能体 | LangChain 1.x `create_agent` + LangGraph 1.x |
| 大模型 | DeepSeek（`deepseek-chat`） |
| 搜索工具 | Tavily Search |
| 记忆存储 | PostgreSQL 16 + pgvector（LangGraph PostgresSaver） |
| 文件存储 | 阿里云 OSS（北京 region，预签名上传） |
| 前端 | Next.js 构建的静态资源（`app/static`） |

## 目录结构

```
PersonalChief/
├── app/
│   ├── agents/
│   │   └── Personal_chief.py   # 私厨智能体：系统提示词、工具、模型、checkpoint 记忆、流式对话
│   ├── api/v1/
│   │   ├── chat.py             # 对话接口（流式对话 / 历史消息 / 清空历史）
│   │   └── oss.py              # 阿里云 OSS 上传预签名 URL 接口
│   ├── common/
│   │   └── logger.py           # 日志配置
│   ├── models/
│   │   └── schemas.py          # Pydantic 请求模型（ChatRequest）
│   ├── main.py                 # FastAPI 入口：路由挂载 + 前端静态资源 + SPA fallback
│   └── static/                 # Next.js 构建产物（前端页面）
├── docker-compose.yml          # PostgreSQL (pgvector/pg16) 服务
├── langgraph.json              # LangGraph CLI / Studio 配置（graph: chief_agent）
├── pyproject.toml              # 项目与依赖声明（uv 管理）
└── uv.lock                     # 锁定的依赖版本
```

## 快速开始

### 1. 环境要求

- Python 3.10 ~ 3.11（`.python-version` 为 3.11）
- [uv](https://docs.astral.sh/uv/)
- Docker（用于运行 PostgreSQL）

### 2. 启动 PostgreSQL

```bash
docker compose up -d
```

默认连接信息（与代码中硬编码一致）：`postgresql://langchain:langchain@localhost:5432/langchain`

### 3. 安装依赖

```bash
uv sync
```

### 4. 配置环境变量

```bash
cp .env.example .env    # Windows 下: copy .env.example .env
```

按下方「环境变量」表格填写。最少需要模型密钥和 `TAVILY_API_KEY`；不上传图片可以不配 OSS 相关变量。

> checkpoint 数据表由应用启动时自动初始化（`PostgresSaver.setup()`，幂等），无需手动建表。

### 5. 启动服务

```bash
uv run python -m app.main
```

打开浏览器访问 **http://127.0.0.1:8001**。

### 可选：LangGraph 方式启动

项目根目录有 `langgraph.json`（graph 名为 `chief_agent`，环境变量从 `.env` 加载），也可以用 LangGraph CLI 启动：

```bash
langgraph dev
```

然后打开 **http://127.0.0.1:2024**（LangGraph Studio 调试界面）。

## 环境变量

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | 视情况 | 使用 DeepSeek 官方集成时所需（`langchain-deepseek` 已安装） |
| `OPENAI_API_KEY` | 视情况 | 若模型实际走 OpenAI 兼容接口初始化时所需 |
| `OPENAI_BASE_URL` | 视情况 | OpenAI 兼容接口地址；用 DeepSeek 官方接口时填 `https://api.deepseek.com` |
| `TAVILY_API_KEY` | 是 | Tavily 联网搜索密钥 |
| `ALIBABA_CLOUD_ACCESS_KEY_ID` | 上传图片时 | 阿里云 OSS 访问凭证 |
| `ALIBABA_CLOUD_ACCESS_KEY_SECRET` | 上传图片时 | 阿里云 OSS 访问凭证 |
| `OSS_BUCKET` | 上传图片时 | OSS 存储桶名 |
| `OSS_ENDPOINT` | 否 | OSS 域名，默认 `oss-cn-beijing.aliyuncs.com` |
| `LANGSMITH_API_KEY` | 否 | LangSmith 链路追踪（可选） |

> 模型相关说明：`app/agents/Personal_chief.py` 中 `create_agent(model="deepseek-chat", ...)` 以字符串形式传模型，由 LangChain 的 `init_chat_model` 解析。若接口报模型或密钥错误，可将其改为显式的 `ChatDeepSeek(model="deepseek-chat")`（从 `langchain_deepseek` 导入），并配置 `DEEPSEEK_API_KEY`。

## API 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/v1/chat/stream` | 流式对话 |
| `GET` | `/api/v1/chat/messages?thread_id=xxx` | 获取某个会话的历史消息 |
| `DELETE` | `/api/v1/chat/messages?thread_id=xxx` | 清空某个会话的历史消息 |
| `GET` | `/api/v1/oss/presign?filename=xxx.jpg` | 获取 OSS 预签名上传 URL（1 小时有效） |

请求示例（流式对话）：

```bash
curl -X POST http://127.0.0.1:8001/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "家里有土豆、青椒和猪肉，今晚做什么菜？", "thread_id": "user-001"}'
```

请求体字段：`message`（必填，用户输入）、`image_url`（可选，食材照片 URL）、`thread_id`（必填，会话标识，用于多轮记忆）。

预签名上传响应示例：

```json
{
  "uploadUrl": "https://xxx.oss-cn-beijing.aliyuncs.com/xxx.jpg?Expires=...",
  "contentType": "image/jpeg",
  "accessUrl": "https://<OSS_BUCKET>.<OSS_ENDPOINT>/xxx.jpg"
}
```

前端拿到 `uploadUrl` 后用 PUT 直传文件，再把 `accessUrl` 作为 `image_url` 传给对话接口。

## 智能体工作流程

```
用户输入（文字 / 食材照片 URL）
        │
        ▼
① 识别与评估食材：辨识照片中的食材，评估新鲜度与可用量，整理「当前可用食材清单」
        │
        ▼
② 智能食谱检索：调用 web_search（Tavily），以食材清单为核心关键词查找菜谱
        │
        ▼
③ 多维度评估排序：对候选食谱按「营养价值 + 制作难度」量化打分并排序
        │
        ▼
④ 结构化方案输出：食谱信息、得分、推荐理由、参考图片
        │
        ▼
会话记录写入 PostgreSQL checkpoint（按 thread_id 关联多轮记忆）
```

## 注意事项 / 已知问题

- **数据库连接串硬编码**在 `app/agents/Personal_chief.py`（约第 31 行），默认值与 `docker-compose.yml` 一致；修改连接信息需同步改这两处。
- **历史消息只返回文本**：图片消息在历史记录中以 `📷 [图片]` 占位展示，多模态内容的 URL 不会随历史返回，如有需要可扩展 `_extract_text`。
- **CORS 全开**：`main.py` 中 `allow_origins=["*"]` 便于插件/前端联调，生产环境建议收紧为具体域名。
- `pyproject.toml` 里 `[project.scripts] langchain = "my_chain:main"` 是模板残留（`my_chain` 模块不存在），可忽略或删除。
