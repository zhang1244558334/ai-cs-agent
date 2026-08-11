# ⚠️ 只改 Knowledge.vue 的 template 和 CSS，script setup 里一行都不要动！
# ⚠️ 不改任何 JS 函数、API 调用、ref/computed/watch

> 知识库页面布局重塑：从裸列表升级为有层次感的管理界面

# 目标效果
类似 Notion 数据库视图或飞书多维表格 —— 文档不是裸露在外的，而是收纳在统计面板和表格里，有筛选、搜索、分层展示。

# Template 改造

## 整体结构（替换现有 template）
```
<div class="knowledge-page">
  <!-- 页头保持不变 -->
  <div class="page-header">
    <div class="page-breadcrumb">
      <i data-lucide="book-open" class="breadcrumb-icon"></i>
      <span>知识库管理</span>
    </div>
    <div class="header-actions">
      <el-button type="primary" size="small" @click="activeTab = 'upload'">
        <i data-lucide="upload"></i> 上传文档
      </el-button>
    </div>
  </div>

  <!-- 统计卡片条 -->
  <div class="stats-bar">
    <div class="stats-item">
      <div class="stats-icon" style="background:linear-gradient(135deg,#e6f7ff,#bae7ff);color:#1890ff">
        <i data-lucide="file-text"></i>
      </div>
      <div class="stats-body">
        <div class="stats-value">{{ docs.length }}</div>
        <div class="stats-label">文档总数</div>
      </div>
    </div>
    <div class="stats-item">
      <div class="stats-icon" style="background:linear-gradient(135deg,#f6ffed,#d9f7be);color:#52c41a">
        <i data-lucide="grid-3x3"></i>
      </div>
      <div class="stats-body">
        <div class="stats-value">{{ totalChunks }}</div>
        <div class="stats-label">分块总数</div>
      </div>
    </div>
    <div class="stats-item">
      <div class="stats-icon" style="background:linear-gradient(135deg,#fff7e6,#ffe7ba);color:#fa8c16">
        <i data-lucide="database"></i>
      </div>
      <div class="stats-body">
        <div class="stats-value">384维</div>
        <div class="stats-label">向量维度</div>
      </div>
    </div>
    <div class="stats-item">
      <div class="stats-icon" style="background:linear-gradient(135deg,#f9f0ff,#efdbff);color:#722ed1">
        <i data-lucide="clock"></i>
      </div>
      <div class="stats-body">
        <div class="stats-value">{{ lastUpdated }}</div>
        <div class="stats-label">最后更新</div>
      </div>
    </div>
  </div>

  <!-- 主卡片 -->
  <div class="page-card">
    <!-- Tab 切换 -->
    <div class="tab-bar">
      <div class="tab-item" :class="{ active: activeTab === 'docs' }" @click="activeTab = 'docs'">
        <i data-lucide="list"></i> 文档列表
      </div>
      <div class="tab-item" :class="{ active: activeTab === 'upload' }" @click="activeTab = 'upload'">
        <i data-lucide="upload-cloud"></i> 上传管理
      </div>
    </div>

    <!-- Tab: 文档列表 -->
    <div v-if="activeTab === 'docs'">
      <!-- 工具栏 -->
      <div class="toolbar">
        <el-input v-model="docSearch" placeholder="搜索文档..." size="small" clearable class="toolbar-search">
          <template #prefix><i data-lucide="search"></i></template>
        </el-input>
        <div class="toolbar-right">
          <el-switch v-model="isPublic" active-text="公共" inactive-text="私有" size="small" />
          <span class="toolbar-count">共 {{ filteredDocs.length }} 个文档</span>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="filteredDocs.length === 0" class="empty-state">
        <div class="empty-icon"><i data-lucide="inbox"></i></div>
        <div class="empty-title">{{ docs.length === 0 ? '知识库还是空的' : '没有匹配的文档' }}</div>
        <div class="empty-desc">{{ docs.length === 0 ? '上传产品手册、FAQ、政策文档，让客服变得更聪明' : '试试换个关键词' }}</div>
        <el-button v-if="docs.length === 0" type="primary" size="small" @click="activeTab = 'upload'">
          <i data-lucide="upload"></i> 上传第一篇文档
        </el-button>
      </div>

      <!-- 文档表格 -->
      <div v-else class="doc-table">
        <div class="table-header">
          <span class="col-name">文档名称</span>
          <span class="col-type">类型</span>
          <span class="col-chunks">分块</span>
          <span class="col-visibility">可见性</span>
          <span class="col-action">操作</span>
        </div>
        <div v-for="doc in filteredDocs" :key="doc.name" class="table-row">
          <span class="col-name">
            <span class="file-icon">
              <i v-if="doc.name.endsWith('.pdf')" data-lucide="file-text" style="color:#ff4d4f"></i>
              <i v-else-if="doc.name.endsWith('.md')" data-lucide="file-code" style="color:#1890ff"></i>
              <i v-else-if="doc.name.endsWith('.csv')" data-lucide="file-spreadsheet" style="color:#52c41a"></i>
              <i v-else data-lucide="file" style="color:#999"></i>
            </span>
            <span class="file-name">{{ doc.name }}</span>
          </span>
          <span class="col-type">
            <el-tag :type="fileTypeTag(doc.name)" size="small">{{ fileExt(doc.name) }}</el-tag>
          </span>
          <span class="col-chunks">{{ doc.chunks || '-' }}</span>
          <span class="col-visibility">
            <el-tag v-if="doc.is_public" size="small" type="success">公共</el-tag>
            <el-tag v-else size="small" type="info">私有</el-tag>
          </span>
          <span class="col-action">
            <el-button type="danger" size="small" text @click="deleteDoc(doc.name)">删除</el-button>
          </span>
        </div>
      </div>
    </div>

    <!-- Tab: 上传管理 -->
    <div v-if="activeTab === 'upload'">
      <p class="upload-desc">上传文档后自动分块 → embedding → 入库，30秒内客服即可回答相关问题</p>
      <div class="upload-area">
        <el-upload
          :action="`/api/knowledge?is_public=${isPublic}&tenant_id=single`"
          :headers="{accept: 'application/json'}"
          :show-file-list="true"
          :on-success="onUpload"
          accept=".md,.txt,.csv,.html,.pdf"
          drag
        >
          <div class="upload-dragger-content">
            <i data-lucide="upload-cloud" style="display:block;margin:0 auto 8px"></i>
            <div class="upload-text">点击或拖拽文件到此处上传</div>
            <div class="upload-hint">支持 .md .txt .csv .html .pdf</div>
          </div>
        </el-upload>
      </div>

      <!-- 上传结果预览保持不变 -->
      <div v-if="uploadResult" class="upload-result-box">
        <div style="font-weight: 600; color: #52c41a; margin-bottom: 6px">
          ✅ {{ uploadResult.message }}（共 {{ uploadResult.chunks }} 个分块）
        </div>
        <div v-if="uploadResult.previews?.length" style="margin-top: 8px">
          <div style="font-size: 12px; color: #999; margin-bottom: 4px">分块预览：</div>
          <div v-for="p in uploadResult.previews" :key="p.index" class="preview-item">
            <el-tag size="small" type="success" style="margin-right: 6px">#{{ p.index + 1 }}</el-tag>
            {{ p.preview }}...
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
```

# Script setup 新增（加在现有 import 和 ref 下面，原有代码不动）

```javascript
// ===== 知识库布局新增（追加，不修改原有代码） =====
const activeTab = ref('docs')
const docSearch = ref('')
const totalChunks = ref(0)
const lastUpdated = ref('--')

const filteredDocs = computed(() => {
  if (!docSearch.value) return docs.value
  const q = docSearch.value.toLowerCase()
  return docs.value.filter(d => d.name.toLowerCase().includes(q))
})

function fileExt(name) {
  const ext = name.split('.').pop().toUpperCase()
  return ext || '--'
}

function fileTypeTag(name) {
  if (name.endsWith('.pdf')) return 'danger'
  if (name.endsWith('.md')) return ''
  if (name.endsWith('.csv')) return 'success'
  return 'info'
}

// 更新统计
function updateStats() {
  totalChunks.value = docs.value.reduce((sum, d) => sum + (d.chunks || 0), 0)
  if (docs.value.length > 0) {
    lastUpdated.value = new Date().toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  }
}
```

在 `import` 行加上 `computed`（如果还没有的话）。

在 `loadDocs` 函数末尾加 `updateStats()`。

在 `onUpload` 函数末尾加 `updateStats()`。

# CSS 样式（替换现有 style，保留 page-header 相关样式不变）

```css
.knowledge-page {
  display: flex; flex-direction: column; min-height: 100vh;
  background: #f0f2f5; padding: 0 24px 24px;
}
/* --- 统计条 --- */
.stats-bar {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px;
}
.stats-item {
  display: flex; align-items: center; gap: 14px;
  background: #fff; border-radius: 8px; padding: 16px 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04);
  transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
}
.stats-item:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.1), 0 2px 8px rgba(0,0,0,0.06); }
.stats-icon {
  width: 44px; height: 44px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.stats-body { flex: 1; min-width: 0; }
.stats-value { font-size: 22px; font-weight: 700; color: #1a1a2e; line-height: 1.2; }
.stats-label { font-size: 12px; color: #8c8c8c; margin-top: 2px; }

/* --- 主卡片 --- */
.page-card {
  background: #fff; border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04);
  overflow: hidden;
}

/* --- Tab 切换 --- */
.tab-bar {
  display: flex; border-bottom: 1px solid #f0f0f0; padding: 0 24px;
}
.tab-item {
  display: flex; align-items: center; gap: 6px;
  padding: 14px 20px; font-size: 14px; color: #8c8c8c;
  cursor: pointer; border-bottom: 2px solid transparent;
  transition: all 0.2s; user-select: none;
}
.tab-item:hover { color: #1890ff; }
.tab-item.active { color: #1890ff; border-bottom-color: #1890ff; font-weight: 600; }

/* --- 工具栏 --- */
.toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 24px; border-bottom: 1px solid #f5f5f5;
}
.toolbar-search { width: 240px; }
.toolbar-right { display: flex; align-items: center; gap: 16px; }
.toolbar-count { font-size: 13px; color: #999; }

/* --- 空状态 --- */
.empty-state {
  display: flex; flex-direction: column; align-items: center;
  padding: 60px 24px; text-align: center;
}
.empty-icon { margin-bottom: 16px; color: #d9d9d9; }
.empty-title { font-size: 16px; font-weight: 600; color: rgba(0,0,0,0.85); margin-bottom: 8px; }
.empty-desc { font-size: 13px; color: #999; margin-bottom: 20px; }

/* --- 文档表格 --- */
.doc-table { padding: 0 24px 16px; }
.doc-table .table-header {
  display: flex; padding: 12px 0; font-size: 12px; color: #8c8c8c;
  font-weight: 500; border-bottom: 1px solid #f0f0f0;
}
.doc-table .table-row {
  display: flex; align-items: center; padding: 12px 0;
  border-bottom: 1px solid #f5f5f5; transition: background 0.15s; font-size: 13px;
}
.doc-table .table-row:last-child { border-bottom: none; }
.doc-table .table-row:hover { background: #fafafa; }
.col-name { flex: 1; display: flex; align-items: center; gap: 8px; min-width: 0; }
.col-type { width: 66px; flex-shrink: 0; }
.col-chunks { width: 66px; flex-shrink: 0; color: #666; text-align: center; }
.col-visibility { width: 80px; flex-shrink: 0; }
.col-action { width: 70px; flex-shrink: 0; text-align: right; }
.file-icon { display: inline-flex; align-items: center; flex-shrink: 0; }
.file-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: rgba(0,0,0,0.85); }

/* --- 上传区 --- */
.upload-desc { font-size: 13px; color: #909399; margin: 0 0 16px; padding: 0 24px; }
.upload-area { padding: 0 24px 24px; }
.upload-dragger-content { padding: 30px 0; }
.upload-text { font-size: 15px; color: rgba(0,0,0,0.65); margin-bottom: 4px; }
.upload-hint { font-size: 12px; color: #bbb; }
.upload-result-box {
  margin: 16px 24px 24px; background: #f6ffed; border: 1px solid #b7eb8f;
  border-radius: 8px; padding: 16px;
}
.preview-item {
  font-size: 12px; color: #555; padding: 4px 8px; margin-bottom: 4px;
  background: #fff; border-radius: 4px; border: 1px solid #e8e8e8;
}
```

# 关键规则
1. 原有 JS 函数 loadDocs/onUpload/deleteDoc 不动
2. 原有 ref (docs/isPublic/uploadResult) 不动
3. 原有 import 行加上 computed（如果没有的话）
4. loadDocs 末尾加 updateStats() 调用
5. onUpload 末尾加 updateStats() 调用
6. 新代码追加在原有代码后面，不修改原有代码
