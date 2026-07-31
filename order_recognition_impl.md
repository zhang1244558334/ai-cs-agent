# 实现任务：订单识别状态机（Phase 8 · 第二期）+ 修复 tech/logistics 断链

项目：/home/a/桌面/ai-cs-agent（后端 backend/app）

## 背景

第一期平台适配层已完成（platforms 包 + LogisticsAgent 接 get_tracking），但存在两个问题：

1. **断链 bug**：chat.py 统一调 `agent.llm.chat_stream(msgs)`，绕过了 Agent 自己的 chat_stream 方法。导致 TechAgent/LogisticsAgent 内部的知识库检索、物流轨迹逻辑全部没被调用——tech/logistics 分支的 system prompt 是裸的（只有客服身份那几句）。必须改为调 `agent.chat_stream(msgs)`。
2. **订单不识别**：LogisticsAgent 用默认单号 MOCK20260731001 兜底，用户没给订单号也查假单；订单号不跨轮存储，用户第二轮只说"现在呢"就查不到同一单了。

设计文档：《/home/a/桌面/ai客服智能体研发项目/ai客服智能体技术方案_V1.1.md》§23.5「Agent 接入与订单识别」。

## 任务

### 1. 修复断链（chat.py）

文件：backend/app/api/routes/chat.py 普通 Agent 回复分支（约 218-255 行）

- `tech` / `logistics` 分支：改为 `async for token in agent.chat_stream(msgs):`（Agent 内部完成检索/轨迹/追问）
- `after_sale` / `price` / `default` 分支：保持现状（chat.py 拼检索 + `agent.llm.chat_stream(msgs)`）
- 流式循环、[DONE] 处理、filter_output、SSE 输出逻辑不变
- 先读 TechAgent.chat_stream 和 LogisticsAgent.chat_stream 确认它们的 yield 协议与 llm.chat_stream 一致（都 yield 字符串 token，可能含 [DONE]）

### 2. 订单号提取与跨轮存储（chat.py）

- 新增模块级函数 `_extract_order_no(message: str) -> str | None`：正则 `(MOCK\d+|\d{8,})` 提取，没有返回 None（放 chat.py 顶部，方便单测）
- 普通 Agent 回复分支（intent 非 handover/no_reply/complaint 时）：调 `_extract_order_no(original_message)`，提取到就写 `sess.extra_metadata["order_no"] = <订单号>`
  - 照现有 `_save_context` 的模式（sess.extra_metadata 是 JSON 字段），确认 session_mapper 何时持久化（读 session_mapper.py），保证 order_no 落库
- 组装 msgs 后、调流式之前：读取 `sess.extra_metadata.get("order_no")`（当前消息提取到新的优先），传给 logistics 分支的 Agent 调用
- 不要动：handover/no_reply/complaint 分支、query 重写、_load_history、BargainLog、_save_context 本身

### 3. LogisticsAgent 改造（backend/app/agents/logistics_agent.py）

- `chat_stream(self, messages: list, order_no: str | None = None)`：加 order_no 参数（默认 None，BaseAgent 其他子类不受影响）
- 删除 `_DEMO_ORDER_NO` 默认单号兜底、删除消息内正则提取（订单号统一由 chat.py 传入）
- `_fetch_tracking(order_no: str | None) -> str`：
  - order_no 为 None → 返回空字符串（不查）
  - 查到 → 现有轨迹文本格式
  - 查不到（None）→ "未查询到该订单的物流信息"
- system prompt 增加规则：当 order_no 为 None 时，追加一句"用户未提供订单号，请先向用户询问订单号，不要编造物流信息"；有 order_no 时把轨迹拼进"实时物流信息"
- 异常降级保留（try/except 返回空，不暴露错误）

### 4. 手机尾号验证（可配置，默认关）

- backend/app/core/config.py：PlatformSettings 加 `verify: bool = False`
- backend/app/platforms/mock_adapter.py：加模块级 `_PHONE_TAIL = {"MOCK20260731001": "8888", "MOCK20260731002": "6666", "MOCK20260731003": "1234"}`（不属于平台契约，放 Mock 层）
- LogisticsAgent.chat_stream：当 `settings.platform.verify` 为 True 且 order_no 存在时：
  - 从 user_msg 提取手机尾号（正则 `(\d{4})` 取消息中最后一个 4 位数字）
  - 没提取到 → system 追加"请向用户询问手机尾号以验证订单归属"，不查轨迹
  - 提取到但不匹配 `_PHONE_TAIL.get(order_no)` → system 追加"订单验证失败，请告知用户核实订单号或手机尾号"，不查轨迹
  - 匹配 → 正常查轨迹
- verify 默认 False，不影响现有演示流程

### 5. 单元测试（新建 backend/tests/test_order_recognition.py）

- 测试 `_extract_order_no`：命中 MOCK 单号 / 命中纯数字长单号 / 无订单号返回 None（需要 import 路径处理：chat.py 里函数可独立 import）
- 测试 LogisticsAgent 无 order_no 时不调用 get_tracking（monkeypatch gateway 或直接断言 system 内容含"询问订单号"）
- 测试 verify 开启时：无尾号 → 不查；错误尾号 → 不查；正确尾号 → 查（monkeypatch settings.platform.verify=True 和 _PHONE_TAIL）

## 验收要求

1. `cd /home/a/桌面/ai-cs-agent && /usr/bin/python3 -m pytest backend/tests/ -q`（从项目根跑；test_tenant_isolation 3 个已知失败不要管不要修）
2. 语法检查：`/usr/bin/python3 -m py_compile backend/app/api/routes/chat.py backend/app/agents/logistics_agent.py backend/app/platforms/mock_adapter.py`
3. 实测（backend 目录下）：
   - `_extract_order_no` 三个用例
   - LogisticsAgent 无订单号时 system 含"询问订单号"且不查轨迹
   - verify=True + 正确尾号返回轨迹文本
4. 不要动前端任何文件
5. 不要修改已有测试文件（只允许新建 test_order_recognition.py）
6. 不要动 complaint_flow.py、router_rules.yaml、knowledge 包、retriever.py、models
7. 汇报：改了哪些文件、每个文件改了什么、pytest 结果、实测输出
