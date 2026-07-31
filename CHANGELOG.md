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

### Phase 2 — 三级路由 + Agent 核心 + MVP 链路（2026-07-28）
- Bot Gateway 策略模式（IBotPlatform 接口 + WebAdapter + SessionMapper + Orchestrator）
- 三级路由（关键词匹配器 + 正则匹配器 + LLM 意图分类 + Router 编排）
- Agent 核心（BaseAgent 抽象基类 + DefaultAgent + PriceAgent 动态议价）
- 领域配置文件（config/router_rules.yaml + config/bargain.yaml）
- SSE 流式响应（StreamingResponse + chat_stream 逐 token 推送）
- 对话历史写入 messages 表
- 议价记录写入 bargain_logs 表 + bargain_count 递增
- UUID 主键方案适配 SQLite async
- 配置 DeepSeek API key，MVP 端到端测试通过（询价/问候/转人工）
- 22 条测试用例通过（路由/知识库/安全/API/人工接管）

### Phase 3 — 自我优化闭环（2026-07-29 规划）
- 技术架构文档 V1.1 定稿（docs/技术架构文档-V1.1.md）
- Phase 路线图文档定稿（docs/阶段路线图.md）
- 失败对话自动归因引擎设计：handover → 类型分析（知识库缺失/路由错误/话术问题/正常转接）
- 三级决策授权模型：自动执行(L1) / 建议批准(L2) / 人工研判(L3)
- 版本控制与回滚机制设计
- 管理后台"待审批"功能规划

### Fixed
- pyproject.toml build-backend 路径修复（setuptools.backends._legacy → setuptools.build_meta.__legacy__）
- requires-python 降为 >=3.10（当前环境 Python 3.10）
- docker-compose 移除无效 backend 服务引用
- .gitignore 补充 *.egg-info/

## 2026-07-31 — 多轮上下文修复 + 断链修复 + 健康检查体系

### Fixed
- **多轮对话失忆**：chat.py 生成回复时 `msgs` 未带历史上下文，LLM每轮失忆答非所问。新增 `_load_history()`（messages表最近8条，过滤handover/no_reply轮），msgs = [system] + history + [当前消息]；system prompt 加角色边界规则
- **TechAgent断链**：tech意图落入 default_agent，RAG检索能力未生效。chat.py 加 tech 分支，TechAgent 补 chat_stream() 流式
- **删除不删向量**：knowledge.py delete_doc 只删磁盘文件，Chroma 残留旧数据。改为同步调 VectorStore.delete_document()
- **人工超时不回切**：check_timeout_human() 未调用，转人工后永不自动切回AI。chat 接口收到消息时检查超时(1h)自动回切
- **数据库缺表**：sessions/messages/tenants 等核心表未建（alembic_version 有记录但表不存在）。create_all 建全表 + models/__init__.py 补 Tenant/ProactiveLog 注册
- **关键词检索英文误匹配**：keyword_retriever 后备切分命中英文品牌名，改为只保留含中文的片段

### Changed
- 意图示例句 70→92 条（tech 7→20：续航/拍照/快充/防水；default 31→40：推荐/哪个好/值得买）
- 路由向量相似度阈值 0.65→0.35（品牌词稀释意图词，原阈值过严）
- LLM意图分类器 prompt 重写：给每个意图定义+示例，"拍照好吗是tech不是after_sale"
- 知识库扩充：4文档→11文档，284条真实FAQ（京东/淘宝/拼多多官方帮助中心采集），Chroma按Q&A对分块239块
- 向量检索换用 BAAI/bge-small-zh-v1.5 中文embedding（原默认英文模型搜中文全乱匹配）
- 结构化日志接线：logger.py JSONL 初始化 + chat.py 三埋点（chat_request/routed/done）

### Added
- scripts/dead_code_check.py：AST死代码扫描（make check）
- tests/test_regression_memory.py：3个回归用例（多轮上下文/tech路由/删除同步）
- scripts/health_check.py：四合一体检（死代码+pytest+coverage+mypy）
- scripts/seed_knowledge.py：知识库按Q&A对分块重建
- 每日09:00 cron 自动体检（Hermes cronjob）

## 2026-07-31 — 知识库全场景接入 + LogisticsAgent + Complaint 流程修复（6场景测试 P0/P1）

背景：6 场景全链路测试（退款/物流/支付/优惠/账号/投诉）暴露 284 条真实 FAQ 只在 TechAgent 生效，其余场景知识库断链、答错规则（退货运费谁出、丢件赔多少）。

### Fixed
- **知识库形同虚设（P0）**：DefaultAgent/AfterSaleAgent/PriceAgent 的回复分支与 chat.py 普通分支均为裸 system prompt，知识库仅 tech 意图生效。chat.py 普通回复分支（after_sale/price/default）接入 Retriever(alpha=0.7) top_k=3 检索，知识拼入 system prompt（"参考以下知识回答用户问题，如果知识库没有答案请如实告知"），保留客服身份/不复述/50字限制；Retriever 模块级单例，每次请求真实检索不缓存
- **Complaint 流程硬编码政策（P0）**：check_policy 写死"7天内可免费退货"（与真实知识库"无理由退货运费买家承担"矛盾）；generate_solution 不查知识库由 LLM 自由发挥；confirm_resolution 硬编码 user_accepts=True 假闭环。改为 check_policy 检索 top_k=2 拼接真实政策，无结果时返回"未找到相关政策，需转人工确认"；generate_solution prompt 注入政策知识并约束政策缺失时建议转人工；classify_severity（high→人工）为合理产品逻辑予以保留
- **Logistics 空壳（P1）**：后端无 LogisticsAgent，"快递/物流"落入 default_agent 回"我帮您查一下"空话。新建 LogisticsAgent（继承 BaseAgent，Retriever(alpha=0.7) 检索拼 system + chat_stream 流式接口），chat.py Agent 选择分支新增 logistics 分支
- **路由误判（P1）**："改配送时间"等物流问法被 after_sale 关键词吞掉。router_rules.yaml 新增 logistics 意图，11 个关键词（发货/快递/物流/配送/派送/签收/改配送时间/改地址/什么时候发货/几天到/多久到），priority 3 最高优先于 after_sale；after_sale 保留"退"字（退货/退款问法依赖）

### Verified
- 手工验证：12 个物流关键词命中 logistics；after_sale 既有用例（我要退货/退款怎么操作/发错货了/东西坏了）未被抢占；check_policy 实测"快递丢件了怎么赔偿"能检索到真实 FAQ
- pytest（backend/tests/，从项目根 CWD 运行）：4 项租户隔离测试中 test_knowledge_isolation 通过；剩余 3 项失败（session/message 唯一约束冲突、公共知识检索为空）均为多企业功能既有问题，与本次改动文件无 import 关联，非本次引入
- ruff：logistics_agent.py 零告警，chat.py/complaint_flow.py 告警均为改动前既有行
- 未改动任何前端文件与 tests/ 下测试文件

## 2026-07-31 — 平台接口适配层（Phase 8 · 第一期）

背景：电商场景需查询订单/物流/售后实时数据，个人无法获取平台开放接口资质（需企业审核），先构建平台无关适配层 + Mock 实现跑通链路，接入真实平台时仅新增 Adapter。设计见技术方案 V1.1 §二十三。

### Added
- **backend/app/platforms/ 包**：统一契约（base.py 三个抽象服务 IOrderService/ILogisticsService/IAfterSaleService + Pydantic 模型 OrderInfo/TrackingInfo/AfterSaleInfo/TraceNode，字段缺失返回 None 不抛错）；MockAdapter（预设 3 订单全量数据，金额分单位/时间 ISO 8601，create_refund 校验 can_refund）；PlatformGateway 工厂按配置选择实现，非 mock provider 抛 NotImplementedError
- **配置**：PlatformSettings（CS_PLATFORM_ 前缀，provider=mock/timeout=3/retry=3/shadow=false）
- **LogisticsAgent 接入实时数据**：知识库检索后追加调 get_tracking（正则提取订单号，无则默认演示单号），轨迹文本（承运商/运单号/状态/最近节点/预计送达）拼入 system；接口异常静默降级为纯知识库回答，不暴露错误
- **backend/tests/test_platform_adapter.py**：3 条单测（命中订单结构/未知订单 None/工厂实例化）

### Verified
- pytest backend/tests/（项目根 CWD）：4 passed（3 新平台单测 + test_knowledge_isolation），3 failed 均为既有租户隔离问题（与本次无关，未修）
- 实测：MOCK20260731001 顺丰/派送中/4 节点/今日 18:00 前送达；MOCK20260731002 中通/已签收；未知订单返回 None；MOCK20260731003 可退状态与截止日期正确
- ruff 全过；未动前端、未改已有测试文件、未动 chat.py/complaint_flow.py/router_rules.yaml

## 2026-07-31 — 订单识别状态机 + tech/logistics 断链修复（Phase 8 · 第二期）

背景：第一期发现 chat.py 统一调 agent.llm.chat_stream，绕过 Agent 自身 chat_stream，TechAgent/LogisticsAgent 内部检索与轨迹逻辑从未生效（tech/logistics 分支 system 为裸 prompt）；且订单号无跨轮记忆、无订单号时用默认演示单号兜底。

### Fixed
- **tech/logistics 断链（隐蔽 bug）**：chat.py 流式调用改为按分支选择——tech/logistics 调 `agent.chat_stream(msgs)`（Agent 内部检索+轨迹+追问生效），after_sale/price/default 保持 chat.py 拼检索 + llm.chat_stream。连带修复回归测试 FakeTechAgent 缺 chat_stream 方法（测试类补透传方法）
- **默认单号兜底删除**：LogisticsAgent 不再用 MOCK20260731001 假兜底，无订单号时 system 明确"请先向用户询问订单号，不要编造物流信息"，由 LLM 追问

### Added
- **订单号提取与跨轮存储**：chat.py 新增 `_extract_order_no`（正则 MOCK\d+ 或 8 位以上数字），提取到即写入 session.extra_metadata.order_no（与 last_context_time 同事务提交）；每轮组装消息后读取已存订单号传给 logistics 分支，用户后续轮次不带订单号也能查同一单
- **手机尾号验证（可配置默认关）**：PlatformSettings 新增 verify=false；mock_adapter 新增 _PHONE_TAIL（3 订单尾号映射）；verify 开启时无尾号→询问、尾号不匹配→验证失败不查、匹配→放行查询（从消息取最后一个 4 位数字）
- **backend/tests/test_order_recognition.py**：4 条单测（_extract_order_no 三用例/无单号不查/verify 三态）

### Verified
- pytest backend/tests/（项目根）：11 passed，3 failed 均为既有租户隔离问题
- 根目录回归 tests/：25 passed 全绿（修复 FakeTechAgent 后 tech 场景回归恢复）
- 实测：无订单号 → system 含"询问订单号"且无轨迹；默认 verify → 有轨迹；verify=True 正确尾号 → 有轨迹；错误尾号 → 验证失败无轨迹
- 改动 6 文件：chat.py / logistics_agent.py / config.py / mock_adapter.py / test_order_recognition.py（新）/ test_regression_memory.py（测试适配）；未动前端、complaint_flow.py、router_rules.yaml、knowledge 包

## 2026-07-31 — 租户隔离测试修复（Phase 8 · 第三期）

背景：backend/tests/test_tenant_isolation.py 长期 3 项失败——test_session_isolation/test_message_isolation 报 UNIQUE(platform, platform_session_id) 冲突，test_public_knowledge_shared 检索公共知识返回空。

### Fixed
- **测试污染真实库**：backend/tests/ 无 conftest，测试直连真实开发库 data/chat.db，首次运行插入 test_sess_a/test_sess_b 残留，二次运行唯一约束冲突。新增 backend/tests/conftest.py：模块级 CS_DATABASE_URL 指向独立测试库 data/test_tenant.db 并重建 engine/async_session，autouse fixture 建表 + 每次测试前清空 sessions/messages
- **知识未真正入库（假通过）**：测试调 load_document() 后结果被丢弃，从未写入向量库——test_knowledge_isolation 是"空结果假通过"，test_public_knowledge_shared 断言 len>0 真实暴露。改为 _fresh_kb()（独立 collection test_kb，删旧重建保证重复运行确定性）+ add_documents 真正入库，并追加"结果非空"断言杜绝假通过
- 未动 app/ 业务代码；data/chat.db 修复前残留的测试数据按要求保留未删

### Verified
- pytest backend/tests/（项目根）：14 passed / 0 failed（11 旧 + 3 修复，全绿）
- pytest tests/（根目录回归）：25 passed / 0 failed 无回归
- 隔离确认：data/test_tenant.db 生成、会话表空；data/chat.db mtime 早于本次运行未被新测试写入
- ruff 全绿；未动前端、未动其他测试文件

## 2026-07-31 — 知识上传/更新接口向量库同步修复（Phase 8 · 收尾）

背景：审查发现 knowledge.py 上传接口只统计文档块数、从未写入向量库（关键词路仍能搜到，掩盖问题）；更新接口覆盖文件后无任何向量同步（旧向量残留、新内容不进检索）。

### Fixed
- **upload_doc 补向量写入**：load_document 后调 VectorStore().add_documents(docs)，上传的知识真正进入向量检索；返回 chunks 改为实际文档数
- **update_doc 补向量同步**：签名加 tenant_id/is_public 可选参数（与 upload 对齐），覆盖文件后先 delete_document 清旧向量再 add_documents 写新内容，返回 chunks

### Verified
- 全链路实测（TestClient）：上传 → 检索命中；更新 → 新内容生效、旧内容无残留；删除 → 向量同步清除。验证用纯英文查询词，关键词检索路必空，命中必来自向量库，证明向量同步真实生效
- pytest backend/tests/：14 passed；pytest tests/：25 passed，均不回归
- 只改 backend/app/api/routes/knowledge.py；新增代码零 ruff 告警

## 2026-07-31 — 路由误判补完：账号类归 default + LLM 分类器补 logistics

背景：逐项核对开发问题日志时实测发现，问题9 路由误判表 3 条只修了 1 条——"账号被盗了怎么办"仍被路由到 after_sale。

### Fixed
- **LLM 分类器 prompt 缺陷**：无 logistics 意图定义、账号类无归属说明，"账号被盗"被判为售后。prompt 补 logistics 定义 + 账号类归 default + 两条边界说明；valid 意图列表补 logistics（否则分类结果被丢弃回落 default）
- **向量层兜底**：intent_examples 重建，default 示例 40→45 条（补账号被盗/密码忘了/冻结/注销/登不上），账号类问题走向量匹配稳定归类，不依赖 LLM

### Verified
- 路由实测 15 用例全过：5 账号类→default、3 物流→logistics、3 售后→after_sale、4 基准不回归
- pytest backend/tests/：14 passed；pytest tests/：25 passed
- 开发问题日志问题9 补记修复过程

## 2026-07-31 — 全场景 e2e 测试（14 场景）+ 6 项修复

背景：模拟用户对全部电商场景（tech/price/售后/物流/投诉/转人工/账号/支付/优惠/多轮）端到端对答，同时监视调用链。首轮 6/14，逐项修复后 14/14。

### Fixed
- **多轮持久化失效（P0 隐蔽 bug）**：extra_metadata 普通 JSON 列不追踪内部变更，context_history/order_no 的局部修改从不落库（仅首轮整体赋值生效）。Session/Message 改用 MutableDict.as_mutable(JSON)
- **complaint 触发词太宽**：route_with_graph 的 ["投诉","退货","退款"] 吞掉所有售后咨询，收窄为投诉特有表达
- **≤3 字拼接破坏明确意图**："转人工"被指代拼接改判 tech，拼接条件排除 handover
- **订单号路由补丁**：含订单号或短指代+已存单号且最近物流话题 → 强制 logistics（排除 handover/complaint/no_reply）；拼接时还原被截断的订单号
- **50 字截断关键条款**：丢件赔偿漏"3-7倍"，prompt 加关键条款优先完整例外
- **filter_output 误伤**：支付宝/银行卡是支付 FAQ 必答词被黑名单拦截，移除并改逐词替换、去单字危险词

### Verified
- e2e 14/14 全过（含跨轮记忆：第二圈"现在呢"正确查同一单顺丰轨迹）
- pytest backend/tests/：14 passed；tests/：26 passed（+1 新断言）
- 开发问题日志补记问题14-18
