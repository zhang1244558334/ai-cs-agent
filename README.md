# 🧠 AI 智能客服 Agent

> 一套代码，多平台通用。四级路由 + 多Agent调度 + 知识库RAG + 自我优化闭环。  
> 已接入闲鱼真实WebSocket消息通道，Bot 7×24自动回复。

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)](https://fastapi.tiangolo.com)
[![Vue](https://img.shields.io/badge/Vue-3.4+-4FC08D)](https://vuejs.org)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek-536DFE)](https://deepseek.com)

---

## ✨ 核心亮点

| 特性 | 说明 |
|------|------|
| **快慢分离路由** | 关键词(80%, <1ms) → 向量(15%) → LLM兜底(5%)，省钱又快 |
| **多平台通用** | Gateway/Adapter模式，接一个新平台只需实现6个接口方法 |
| **真实平台接入** | 闲鱼WebSocket真机，消息推送→解密→AI回复→发送，端到端 |
| **自我优化闭环** | 质检→归因→提案→自动修复→验证→生效，8步全自动 |
| **多轮表单引擎** | YAML驱动槽位收集，状态持久化，支持取消/超时/意图切换 |
| **商品自动索引** | 收到消息自动提取itemId→API拉详情→转QA→入库，零手工 |
| **设置热切换** | 改模型/API key/议价参数，不重启进程即时生效 |
| **主动扫描** | 60s轮询事件→AI生成推送→频率控制(日限3次+夜静) |
| **安全防护** | 输入注入检测 + 输出敏感词过滤(20+脏话词库) |

---

## 🏗 架构

```
用户消息 → 平台Bot（闲鱼WebSocket / Web）
          ↓
     Gateway适配层（SessionMapper → 平台会话→内部会话映射）
          ↓
     四级路由链（关键词 → 正则 → BGE向量 → LLM兜底）
          ↓
     Agent调度（议价/售后/物流/技术/投诉/默认，6个专业Agent）
          ↓
     RAG检索（ChromaDB + BGE-small-zh，混合检索α=0.7）
          ↓
     LLM生成 → SSE流式 / WebSocket 回复
          ↓
     质检标记 → 归因分析 → 自优化闭环
```

---

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -e .

# 2. 配置
cp .env.example .env   # 填入 DeepSeek API Key

# 3. 初始化数据库 + 灌入知识库
alembic upgrade head
python scripts/seed_knowledge.py
python scripts/seed_intent_examples.py

# 4. 启动 ChromaDB
docker compose up -d

# 5. 启动后端
HF_HUB_OFFLINE=1 uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# 6. 启动前端（另一个终端）
cd frontend && npm install && npm run dev
```

打开 http://localhost:5173 进入管理后台。

---

## 📦 项目结构

```
ai-cs-agent/
├── backend/app/
│   ├── api/routes/          # FastAPI路由（chat/sessions/admin/knowledge/business）
│   ├── agents/              # 6个Agent + LangGraph投诉流程
│   │   └── langgraph_flows/ # complaint_flow: 6节点状态机
│   ├── router/              # 四级路由（keyword→regex→vector→LLM）
│   ├── gateway/
│   │   ├── interfaces/      # IBotPlatform抽象接口（6方法）
│   │   ├── adapters/        # 平台适配器（xianyu/taobao/jd/pdd/web）
│   │   └── services/        # SessionMapper + BotOrchestrator
│   ├── knowledge/           # ChromaDB + BGE + 混合检索(α=0.7)
│   ├── forms/               # 多轮表单引擎（YAML驱动）
│   ├── proactive/           # 主动扫描器 + 用户状态管理
│   ├── attribution/         # 归因引擎（ABCD四类）
│   ├── safety/              # 注入检测 + 敏感词过滤
│   ├── human_handover/      # 人工接管（超时1h自动回切）
│   ├── models/              # 7张表（session/message/tenant/item/bargain_log等）
│   └── core/                # 基础设施（LLM热切换/多租户/日志）
├── frontend/src/            # Vue 3 + Element Plus（毛玻璃+暗色模式）
├── config/                  # YAML规则 + 业务配置 + 表单模板
├── docs/                    # 37个FAQ文档（电商13+闲鱼12+物业12）
├── scripts/                 # 种子数据/健康检查/自动执行/归因报告
└── tests/                   # 单元测试 + 租户隔离 + 平台适配
```

---

## 🤖 Agent 体系

| Agent | 职责 | 特殊机制 |
|-------|------|----------|
| **PriceAgent** | 议价 | 动态温度梯度(0.3起递增)，最大让步+轮次YAML配置 |
| **AfterSaleAgent** | 售后 | RAG检索退货/退款政策，支持Mock订单查询 |
| **LogisticsAgent** | 物流 | 轨迹查询+RAG检索配送政策 |
| **TechAgent** | 技术咨询 | RAG检索商品参数/材质/功能 |
| **ComplaintFlow** | 投诉 | LangGraph 6节点状态机(定级→查单→查政策→方案→确认→转人工) |
| **DefaultAgent** | 兜底 | 通用对话+商品信息注入 |

---

## 📊 数据库

7张表：`sessions` → `messages`（一对多），`tenants`，`items`，`bargain_logs`，`handover_logs`，`proactive_logs`

- **租户隔离**：SQL WHERE过滤 + ChromaDB metadata过滤
- **JSON列变更追踪**：MutableDict.as_mutable(JSON)解决ORM不追踪dict内部修改
- **SQLite**：开发零配置，SQLAlchemy ORM保证一键切PostgreSQL

---

## 🛡 安全

| 层级 | 位置 | 内容 |
|------|------|------|
| 第1层 | 请求入口 | Prompt注入关键词检测 |
| 第2层 | LLM内部 | LLM自判注入 |
| 第3层 | 输出出口 | 敏感词过滤（微信/QQ/银行卡）+ 脏话拦截(20+词) |
| 第4层 | 工具调用 | 高风险操作需确认 |

---

## 📈 自我优化闭环（8步）

```
质检标记(bigram重叠检测) → 归因分析(ABCD四类)
  → 决策提案(L1自动/L2审批/L3研判)
    → 自动执行 → 自动验证 → 回滚(失败自动回退)
      → 周报生成 → 前端可视化
```

---

## 🛠 技术栈

**后端**：Python 3.10+ / FastAPI / SQLAlchemy(async) / LangGraph / ChromaDB / BGE-small-zh / websockets / Docker

**前端**：Vue 3 / Element Plus / Vite / ECharts / SSE流式

**模型**：DeepSeek-chat（热切换，兼容任何OpenAI API）

---

## 📝 开发日志

详见 `CHANGELOG.md` 和 `/home/a/桌面/ai客服智能体研发项目/开发问题日志.md`，记录了从Phase 0到Phase 6的30+个问题及其根因/修复/教训。

**License**: MIT
