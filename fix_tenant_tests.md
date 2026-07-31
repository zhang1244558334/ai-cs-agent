# 修复任务：租户隔离测试（backend/tests/test_tenant_isolation.py）3 个失败

项目：/home/a/桌面/ai-cs-agent

## 诊断结论（已确认，照此修）

1. **test_session_isolation / test_message_isolation 失败根因**：backend/tests/ 无 conftest.py，测试连真实开发库 data/chat.db（settings.database_url 默认值），第一次跑插入 test_sess_a/test_sess_b 残留，第二次跑 UNIQUE(platform, platform_session_id) 冲突。
2. **test_public_knowledge_shared 失败根因**：load_document() 只加载文件返回文档块，不写向量库；测试调 load_document 后结果被丢弃，从未 add_documents。向量库无数据 → retrieve 返回空 → 断言 len>0 失败。test_knowledge_isolation 同样是"空结果假通过"（断言空集里没有 tenant_b 自然过），需要一并修成真实写入。
3. Chroma 服务 localhost:8001 在跑（VectorStore available=True）。测试写入会污染真实 collection "knowledge_base"，必须用独立 collection。

## 任务

### 1. 新建 backend/tests/conftest.py

- 模块级（在测试 import 之前生效）：把 settings.database_url 指向独立测试库 `sqlite+aiosqlite:///./data/test_tenant.db`，然后重建 `app.core.database` 模块的 engine 和 async_session（import app.core.database 后重新赋值 database_mod.engine / database_mod.async_session，用相同的 create_async_engine 和 async_sessionmaker 参数）。注意 conftest.py 必须先于测试文件 import（pytest 保证 conftest 先加载）。
- autouse fixture：`init_db()` 建表 + 清空 sessions/messages 表（测试库清表安全，不影响真实 data/chat.db）
- 不要动真实 data/chat.db，不要删它

### 2. 修改 backend/tests/test_tenant_isolation.py

- **test_knowledge_isolation**：load_document 后真正写入向量库再检索：
  - 用独立 collection：`vs = VectorStore(collection_name="test_kb")`，`vs.add_documents(docs_a)` / `vs.add_documents(docs_b)`
  - `hybrid = Retriever(vector_store=vs)`（Retriever 接受 vector_store 参数）
  - 检索 tenant_a 验证结果里没有 tenant_b 的私有知识（保留原断言），并追加断言：结果非空（防止空结果假通过）
- **test_public_knowledge_shared**：同样 add_documents(public.md, is_public=True) 后，验证 tenant_a 和 tenant_b 都能检索到公共知识（保留原断言）
- **test_session_isolation / test_message_isolation**：逻辑不变（conftest 隔离 DB 后应通过）。如果 test_message_isolation 的 extra_metadata JSON 查询有问题，用 Python 侧过滤替代 SQL JSON 路径（查出 tenant_a 相关消息再断言），不要改数据模型

### 3. 验收

1. `cd /home/a/桌面/ai-cs-agent && /usr/bin/python3 -m pytest backend/tests/ -q`：期望 14 passed（11 旧 + 3 修复），0 failed
2. `cd /home/a/桌面/ai-cs-agent && /usr/bin/python3 -m pytest tests/ -q`（根目录回归）：期望 25 passed 不回归
3. 确认 data/chat.db 不再被写入测试数据（修复前残留的 test_sess_a/test_sess_b 保留不动，不删）
4. 不要动前端、不要动 app/ 下任何业务代码（本次只允许：新建 conftest.py + 修改 test_tenant_isolation.py）
5. 汇报：conftest 怎么隔离的、测试改了什么、两组 pytest 结果
