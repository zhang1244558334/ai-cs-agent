# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- 项目初始脚手架搭建
- 目录骨架、pyproject.toml、Makefile、Docker Compose、配置文件

### Phase 0 — 工程脚手架（2026-07-27）
- 创建项目目录骨架（backend/app/ 下 10 个包 + frontend/src + docs + tests）
- pyproject.toml 配置 FastAPI/LangGraph/SQLAlchemy/Chroma 等依赖
- Makefile（8 目标：install/lint/test/dev/migrate/up/down/clean）
- Docker Compose（chromadb 服务）
- .env.example + config/config.yaml（三段配置）
- .gitignore + git init + 初始提交
- README.md + CHANGELOG.md

### Phase 1 — FastAPI 骨架与基础设施（2026-07-27）
- FastAPI 应用工厂（CORS + lifespan + 全局异常处理器）
- 配置系统（pydantic-settings + CS_ 前缀环境变量覆写）
- SQLAlchemy async 引擎 + 5 张 ORM 模型（sessions/messages/items/bargain_logs/handover_logs），对齐 V1.1 §4.2
- Alembic 数据库迁移
- 3 组 API 路由桩（/api/chats /api/sessions /api/knowledge）
- LLM 适配层（AsyncOpenAI + 3 次重试 + 降级文案）
- 结构化日志（JSONL 格式 + request_id/session_id/duration/tokens）
- 健康检查接口 GET /health
- Vue 3 + Element Plus 前端骨架
- 3 条测试用例通过

### Phase 2 — 三级路由 + Agent 核心 + MVP 链路（2026-07-27）
- Bot Gateway 策略模式（IBotPlatform 接口 + WebAdapter + SessionMapper + Orchestrator）
- 三级路由（关键词匹配器 + 正则匹配器 + LLM 意图分类 + Router 编排）
- Agent 核心（BaseAgent 抽象基类 + DefaultAgent + PriceAgent 动态议价）
- 领域配置文件（config/router_rules.yaml + config/bargain.yaml）
- SSE 流式响应（StreamingResponse + chat_stream 逐 token 推送）
- 对话历史写入 messages 表
- 议价记录写入 bargain_logs 表 + bargain_count 递增
- UUID 主键方案适配 SQLite async
- 配置 DeepSeek API key，MVP 端到端测试通过（询价/问候/转人工）

### Fixed
- pyproject.toml build-backend 路径修复（setuptools.backends._legacy → setuptools.build_meta.__legacy__）
- requires-python 降为 >=3.10（当前环境 Python 3.10）
- docker-compose 移除无效 backend 服务引用
- .gitignore 补充 *.egg-info/
- README Python 版本号与 pyproject.toml 同步
- 模型字段与 V1.1 §4.2 对齐修正
- SQLite async 下 BigInteger autoincrement → UUID 主键
