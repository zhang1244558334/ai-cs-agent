# AI 智能客服系统

基于 FastAPI + LangGraph + Vue 3 的通用 AI 客服引擎。一套代码，多平台通用。

## 架构

```
用户消息 → Bot Gateway → 三级路由（关键词→正则→LLM）→ Agent 执行 → SSE 流式回复
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              规则匹配（80%）         LLM 兜底（20%）
              0 成本，毫秒级          DeepSeek 实时生成
```

## 核心特性

- **快慢分离**：80% 问题用规则匹配，0 元调用费
- **多平台支持**：Bot Gateway 策略模式，写一个 adapter 接一个新平台
- **知识库 RAG**：上传文档，AI 查文档回答（支持 Chroma 向量搜索 + 关键词搜索双模式）
- **安全防御**：注入检测 + 敏感词过滤 + 脏话拦截
- **LangGraph 多步推理**：投诉处理走流程图，非普通回复
- **人工接管**：关键词触发 + 超时自动回切
- **议价引擎**：动态温度梯度让步，参数化配置
- **全部可配置**：路由规则、议价参数、客服话术、回复风格，改 YAML/改 prompt 就行

## 快速开始

```bash
# 1. 安装后端依赖
pip install -e .

# 2. 配置 API key
cp .env.example .env
# 编辑 .env，填入 CS_LLM_API_KEY

# 3. 初始化数据库
alembic upgrade head

# 4. 启动后端
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# 5. 启动前端（另一个终端）
cd frontend && npm install && npm run dev
```

打开 http://localhost:3000 开始聊天。

## API

| 接口 | 方法 | 说明 |
|:----|:----:|:----|
| `/health` | GET | 健康检查 |
| `/api/chats` | POST | 发送消息，SSE 流式返回 |
| `/api/sessions` | GET/POST | 会话列表/创建 |
| `/api/sessions/{id}` | GET/PATCH | 会话详情/模式切换 |
| `/api/sessions/{id}/messages` | GET | 对话历史 |
| `/api/knowledge` | GET/POST | 知识库列表/上传 |
| `/api/knowledge/{source}` | DELETE/PATCH | 删除/更新文档 |
| `/api/knowledge/search` | POST | 检索知识库 |

## 技术栈

- **后端**：FastAPI + SQLAlchemy + LangGraph + Chroma
- **前端**：Vue 3 + Element Plus + Vite
- **模型**：DeepSeek API / 兼容 OpenAI 的任何模型
- **数据库**：SQLite（可升级 PostgreSQL）
- **部署**：Docker Compose

## 项目结构

```
backend/app/
├── api/routes/        # API 路由
├── agents/            # Agent（默认/议价/技术/售后 + LangGraph 流程）
├── router/            # 三级路由（关键词/正则/LLM）
├── gateway/           # Bot Gateway 多平台接入
├── knowledge/         # 知识库（关键词检索 + Chroma 向量检索）
├── safety/            # 安全过滤（注入/敏感词/脏话）
├── human_handover/    # 人工接管
├── models/            # 数据模型
└── core/              # 基础设施（配置/数据库/LLM/日志）
```
