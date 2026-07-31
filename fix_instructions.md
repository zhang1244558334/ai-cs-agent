# 修复任务：知识库铺到全场景（P0/P1）

项目：/home/a/桌面/ai-cs-agent（后端 backend/app，FastAPI + LangGraph + SQLAlchemy async + Chroma）

## 背景

6 场景全链路测试（退款/物流/支付/优惠/账号/投诉）发现：284 条真实 FAQ 只有 TechAgent 接了检索，其余 Agent（DefaultAgent/AfterSaleAgent/PriceAgent）和 complaint 流程全是裸 LLM 生成，答错规则（退货运费谁出、丢件赔多少）。logistics 意图路由到了 default_agent 但没有 LogisticsAgent。

Retriever 位于 backend/app/knowledge/retriever.py，接口：`await Retriever(alpha=0.7).retrieve(query, top_k=3)` 返回 list[dict]，每项含 text 和 metadata。TechAgent（backend/app/agents/tech_agent.py）已有标准接入范例，照它的写法做。

## 任务

### 1. chat.py 普通回复分支接知识库（问题7，P0）

文件：backend/app/api/routes/chat.py，普通 Agent 回复分支（intent 为 after_sale/price/default 时，约第 217-234 行）。

- 在构造 msgs 前，用 Retriever(alpha=0.7) 对 original_message 做一次 retrieve（top_k=3）
- 把检索结果拼进 system_msg：参考 TechAgent 的写法（"参考以下知识回答用户问题，如果知识库没有答案请如实告知。\n\n参考知识：\n{knowledge}"）
- 保留现有 system 内容（客服身份/不复述用户问题/50字限制），知识追加在后面
- 不要改动：_load_history、query 重写、handover/no_reply/complaint 分支、BargainLog 逻辑
- 注意：Retriever 初始化放函数内或模块级都行，但每次请求都要真实检索，不要缓存知识

### 2. 新建 LogisticsAgent（问题9b，P1）

文件：backend/app/agents/logistics_agent.py（新建）

- 继承 BaseAgent，参考 TechAgent 的 chat_stream 写法（内部做 retrieve，把知识拼进 system）
- system 口吻："你是物流客服助手。参考以下知识回答用户关于发货、快递、物流时效、配送、签收的问题，如果知识库没有答案请如实告知。回复简洁不超过50字。"
- 保留 chat_stream 流式接口（chat.py 用 agent.llm.chat_stream(msgs) 的方式）

### 3. chat.py 加 logistics 分支（问题9b，P1）

文件：backend/app/api/routes/chat.py

- 在 Agent 选择分支加：`elif intent == "logistics": agent = LogisticsAgent()`
- import 相应类

### 4. 路由修正（问题9a，P1）

文件：config/router_rules.yaml

- after_sale 的 keywords 有"退"字，太宽，会误吞"改配送时间"等物流问法。把"退"字保留（退货/退款相关问法很多），但要给 logistics 补关键词："改配送时间"、"改地址"、"配送"、"派送"、"签收"、"什么时候发货"、"几天到"、"多久到"
- logistics priority 已设 3（最高），检查确认 keyword_matcher 的优先级语义：logistics 命中应优先于 after_sale

### 5. complaint 流程查知识库（问题8，P0）

文件：backend/app/agents/langgraph_flows/complaint_flow.py

- check_policy 节点：删除硬编码 `"根据退换货政策，7天内可免费退货"`，改为用 Retriever(alpha=0.7) 检索 state["message"]，把检索到的知识作为 policy 文本（取 top_k=2 拼接）；如果没检索到，policy 写"未找到相关政策，需转人工确认"
- generate_solution 节点：prompt 里把检索到的知识也拼进去（参考 check_policy 的检索结果），让 LLM 依据真实政策给方案
- classify_severity 保留（high 转人工是合理产品逻辑，不要动）
- 注意：complaint_flow.py 是模块级初始化，Retriever 也在模块级初始化一次即可

## 验收要求

1. 改完跑 `cd /home/a/桌面/ai-cs-agent/backend && /usr/bin/python3 -m pytest tests/ -x -q`（注意用 /usr/bin/python3，系统 python3 可能指向没有依赖的虚拟环境）
2. 确保没改坏：多轮历史、query 重写、议价、handover 逻辑保持原样
3. 不要动前端任何文件
4. 不要动 tests/ 下的测试文件
5. 汇报时列出：改了哪些文件、每个文件改了什么、pytest 结果、有没有遇到问题

如果 pytest 需要联网（DeepSeek API）而失败，把失败原因分类：断言失败=真问题要修；网络/API 错误=环境问题，说明即可。
