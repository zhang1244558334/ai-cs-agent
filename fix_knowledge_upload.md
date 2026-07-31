# 修复任务：知识上传/更新接口向量库同步

项目：/home/a/桌面/ai-cs-agent（后端 backend/app/api/routes/knowledge.py）

## 诊断结论（已确认）

- POST /api/knowledge（upload_doc）：写文件 ✓，但 `len(load_document(...))` 只统计块数，从未调用 VectorStore.add_documents —— 上传的知识永远不进向量检索（关键词路仍能搜到，掩盖了问题）
- PATCH /api/knowledge/{source}（update_doc）：覆盖文件 ✓，但完全没有向量库同步 —— 旧向量残留、新内容不进检索
- DELETE /api/knowledge/{source}：删文件 + 删向量（正常，不要动）

## 任务（只改 backend/app/api/routes/knowledge.py）

### 1. upload_doc 补向量写入

```python
docs = load_document(dest, tenant_id=tenant_id, is_public=is_public)
vs = VectorStore()
vs.add_documents(docs)
```
- 返回里 `"chunks": len(docs)`
- 保持现有 deidentify（公共知识去标识化）逻辑不动

### 2. update_doc 补向量同步

- 签名加可选参数：`tenant_id: str = "single", is_public: bool = False`（前端未传时用默认值，行为与 upload 一致）
- 覆盖文件后：
  - `vs = VectorStore()`，`vs.delete_document(filepath)`（清旧向量，delete_document 按 metadata.source 匹配）
  - `docs = load_document(filepath, tenant_id=tenant_id, is_public=is_public)`，`vs.add_documents(docs)`
- 返回 `{"message": f"Updated {source}", "chunks": len(docs)}`
- 注意：delete_document 传入的路径要和 add 时 load_document 的 source 一致（filepath 就是 load_document 用的路径，天然一致）

### 3. 不要动

- delete_doc、search_knowledge、list_docs
- 其他任何文件、前端、已有测试

## 验收

1. 写一个临时验证脚本（放 /tmp 或 backend/ 下跑完删）用 FastAPI TestClient 或直接调用路由函数：
   - 上传临时文件 tests/fixtures/doc_a.md 内容（或新建 docs/_tmp_verify.md）→ 返回 chunks>0
   - `Retriever().retrieve("test query", top_k=5)` 能搜到该文档内容（上传生效）
   - PATCH 更新该文档 → 再次 retrieve 能搜到新内容（旧内容不残留）
   - DELETE 清理 → 确认向量同步删除、临时文件删除
2. 跑 `cd /home/a/桌面/ai-cs-agent && /usr/bin/python3 -m pytest backend/tests/ -q`：14 passed 不回归
3. 跑 `cd /home/a/桌面/ai-cs-agent && /usr/bin/python3 -m pytest tests/ -q`：25 passed 不回归
4. 汇报：改了什么、验证脚本输出、两组 pytest 结果
