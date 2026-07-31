# 实现任务：平台接口适配层（Phase 8 · 第一期）

项目：/home/a/桌面/ai-cs-agent（后端 backend/app，FastAPI + SQLAlchemy async + LangGraph + Chroma）

## 背景

设计文档：《/home/a/桌面/ai客服智能体研发项目/ai客服智能体技术方案_V1.1.md》§二十三「平台接口适配层（Phase 8）」——先读该章节再动手。

核心思想：接口管实时数据，知识库管规则政策。本期只做 Mock 实现跑通链路，不接任何真实平台。

## 任务

### 1. 新建 backend/app/platforms/ 包（本期主体）

- `__init__.py`
- `base.py`：Pydantic 数据模型 + 抽象契约（参考 §23.3 表格）
  - 模型：OrderInfo（order_no, status, total_amount, items[], can_refund, refund_deadline）、TrackingInfo（order_no, carrier, tracking_no, status, trace[], eta）、AfterSaleInfo（service_no, status, refund_amount, progress[]）、TraceNode（time, node, city）
  - 抽象契约类：IOrderService（get_order）、ILogisticsService（get_tracking）、IAfterSaleService（create_refund / query_after_sale）
  - 契约要点：时间字段 ISO 8601 字符串；金额统一分为单位整数；字段缺失返回 None 不抛错
- `mock_adapter.py`：MockAdapter 实现三个契约
  - 预设 3 个订单号（MOCK20260731001 派送中/顺丰、MOCK20260731002 已签收/中通、MOCK20260731003 已发货/圆通），每个含完整轨迹 trace（3 个节点以上）
  - 未知名订单号返回 None（不抛错）
- `factory.py`：`PlatformGateway`，`get_adapter()` 按配置 `settings.platform.provider` 返回对应 adapter，当前只有 mock，其他 provider 名（jd/taobao/pdd）返回 NotImplementedError 或回退 mock

### 2. 配置（backend/app/core/config.py）

新增 platform 配置段（照现有 pydantic-settings 风格）：
- provider: str = "mock"
- timeout: float = 3.0
- retry: int = 3
- shadow: bool = False

### 3. LogisticsAgent 接入实时数据（backend/app/agents/logistics_agent.py）

现有 chat_stream 已经做知识库检索拼 system（不要删）。在知识检索后追加：

- 用正则从用户消息提取订单号（匹配 `MOCK\d+` 或 `\d{8,}`），提取不到用 "MOCK20260731001" 作为演示单号
- 调用 PlatformGateway().get_adapter().get_tracking(order_no)，拿到 TrackingInfo 后把轨迹文本拼进 system（格式：承运商/运单号/当前状态/最近节点/预计送达；查不到时写"未查询到该订单的物流信息"）
- system 结构保持：口吻 + 知识库参考 + 实时轨迹，LLM 最终回复不超过 50 字
- 接口调用失败（异常）时降级：只保留知识库部分，不把错误暴露给用户

### 4. 单元测试（新建 backend/tests/test_platform_adapter.py）

- 测试 MockAdapter.get_tracking("MOCK20260731001") 返回顺丰/派送中/轨迹≥3节点
- 测试未知订单号返回 None
- 测试 PlatformGateway 默认 provider 为 mock 且能实例化

## 验收要求

1. 跑：`cd /home/a/桌面/ai-cs-agent && /usr/bin/python3 -m pytest backend/tests/ -q`（注意必须从项目根目录跑，fixtures 相对路径依赖项目根 CWD；backend/tests/ 里 test_tenant_isolation 有 3 个已知既有失败与本任务无关，不要修它们）
2. 跑：`/usr/bin/python3 -c "from app.platforms.factory import PlatformGateway; g=PlatformGateway(); a=g.get_adapter(); print(type(a).__name__)"`（在 backend 目录下）验证工厂可用
3. 不要动前端任何文件
4. 不要修改已有测试文件（只允许新建 test_platform_adapter.py）
5. 不要动 chat.py、complaint_flow.py、router_rules.yaml（本期只允许改 logistics_agent.py + config.py + 新增 platforms 包）
6. 汇报：改了哪些文件、每个文件改了什么、pytest 结果、实测一个 get_tracking 的输出示例
