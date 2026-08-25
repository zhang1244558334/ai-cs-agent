# ⚠️ 最重要的警告：只改 CSS 和 HTML 结构（template 标签），JavaScript 逻辑一行都不要碰！
# ⚠️ 不许改任何 script setup 里的代码、不许改 API 调用、不许改数据绑定、不许改 computed/watch

> 前端布局重构：Dashboard Bento网格、Chat双栏工作台、全局页头区
> 所有现有功能必须保持完全不变

# 项目上下文
- 框架：Vue 3 + Element Plus + ECharts + Lucide 图标
- 侧边栏：220px 宽，#1a1a2e 渐变
- 内容区：flex:1，#f0f2f5 底色
- 当前路由：/ (仪表盘) /chat /sessions /knowledge /settings /review /tenants /test-center

# 三大布局改造

## 改造一：Dashboard — Bento Grid 不对称布局

### Template结构改为：
```
<div class="dashboard-page">
  <!-- 页头 -->
  <div class="page-header">
    <div class="page-breadcrumb">🏠 仪表盘</div>
    <div class="header-actions">
      ...现有三个按钮保持不变...
    </div>
  </div>

  <!-- KPI卡片行 -->
  <div class="stat-row">
    ...四个 stat-card 保持不变...
  </div>

  <!-- Bento网格区：大图 + 小图/列表 -->
  <div class="bento-row">
    <div class="bento-main">
      <!-- 24h趋势图，占2/3 -->
      <div class="chart-card large">
        <h3 class="chart-title">24小时会话量趋势</h3>
        <div ref="lineChart" class="chart-box"></div>
      </div>
    </div>
    <div class="bento-side">
      <!-- 意图分布饼图，占1/3 -->
      <div class="chart-card">
        <h3 class="chart-title">意图分布（24h）</h3>
        <div ref="pieChart" class="chart-box small-chart"></div>
      </div>
      <!-- 最近对话紧凑列表 -->
      <div class="mini-list-card">
        <h3 class="mini-list-title">最近对话</h3>
        <div v-if="dashboard.recent_chats?.length">
          <div v-for="chat in dashboard.recent_chats.slice(0,5)" :key="chat.id" class="mini-row">
            <el-tag size="small" :type="intentTagType(chat.intent)">{{ chat.intent || '-' }}</el-tag>
            <span class="mini-content">{{ chat.content }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 最近提案 —— 全宽表格 -->
  <div class="list-card">
    <h3 class="list-title">最近提案</h3>
    ...现有提案表格保持不变...
  </div>
</div>
```

### CSS关键（scoped）：
- `.bento-row { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; }`
- `.bento-main .chart-box { height: 360px; }`
- `.bento-side .chart-box.small-chart { height: 200px; }`
- `.mini-list-card { background:#fff; border-radius:8px; padding:12px 16px; box-shadow:0 2px 8px rgba(0,0,0,0.06); flex:1; }`
- `.mini-row { display:flex; align-items:center; gap:8px; padding:6px 0; border-bottom:1px solid #f5f5f5; font-size:12px; }`
- 页头样式见下面"通用页头"

### JS不动：
- dashboard.value 不变
- pieChart/lineChart ref 不变
- 图表 option 配置不变（但 chart-box 高度由 CSS 控制，不影响 ECharts）
- 所有函数（renderCharts、runAttribution 等）不变

## 改造二：Chat — 双栏客服工作台

### Template结构改为：
```
<div class="chat-page">
  <!-- 页头 -->
  <div class="page-header">
    <div class="page-breadcrumb">💬 对话 · 客服工作台</div>
    <el-button size="small" @click="newSession">+ 新会话</el-button>
  </div>

  <div class="chat-workspace">
    <!-- 左侧会话列表 -->
    <div class="session-panel">
      <div class="panel-search">
        <el-input v-model="sessionSearch" placeholder="搜索会话..." size="small" clearable />
      </div>
      <div class="session-list">
        <div v-for="s in filteredSessions" :key="s.id"
             class="session-item"
             :class="{ active: s.id === sessionId }"
             @click="switchSession(s.id)">
          <div class="session-item-top">
            <span class="session-user">{{ s.user_id || '访客' }}</span>
            <span class="session-time">{{ fmtSessionTime(s.created_at) }}</span>
          </div>
          <div class="session-item-bottom">
            <el-tag v-if="s.last_intent" size="small" :type="intentTagType(s.last_intent)">{{ intentCN(s.last_intent) }}</el-tag>
            <span class="session-preview">{{ s.last_message || '暂无消息' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧对话区 -->
    <div class="chat-main">
      <div class="chat-card">
        <div class="chat-header">
          <span class="session-id">{{ sessionId ? '会话 ' + sessionId.slice(0, 8) : '未创建会话' }}</span>
        </div>
        <div id="msg-box" class="chat-body" @scroll="onScroll">
          ...现有消息渲染完全不变...
          ...loading dots 不变...
          ...scroll-bottom 按钮不变...
        </div>
        <div class="chat-footer">
          ...现有输入框+发送按钮完全不变...
        </div>
      </div>
    </div>
  </div>
</div>
```

### 需要新增的 script setup 代码（加在现有 import 和 ref 下方，不改原有代码）：
```javascript
// ===== 会话列表面板（新增） =====
const sessions = ref([])
const sessionSearch = ref('')
const filteredSessions = computed(() => {
  if (!sessionSearch.value) return sessions.value
  const q = sessionSearch.value.toLowerCase()
  return sessions.value.filter(s => (s.user_id || '').toLowerCase().includes(q))
})

function fmtSessionTime(t) {
  if (!t) return ''
  const d = new Date(t)
  const now = new Date()
  if (d.toDateString() === now.toDateString()) return d.toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit'})
  return d.toLocaleDateString('zh-CN', {month:'short',day:'numeric'})
}

async function loadSessions() {
  try {
    const r = await fetch('/api/sessions?limit=30')
    sessions.value = (await r.json()) || []
  } catch(e) { sessions.value = [] }
}

async function switchSession(id) {
  if (id === sessionId.value) return
  sessionId.value = id
  messages.value = []
  await loadProactiveMessages()
}

// 在 onMounted 里追加 loadSessions()
// 在现有 onMounted 的末尾加一行: loadSessions()
```

### CSS关键（scoped）：
- `.chat-page { display:flex; flex-direction:column; height:calc(100vh); background:#f0f2f5; }`
- `.chat-workspace { display:flex; flex:1; overflow:hidden; padding:0 24px 24px; gap:16px; }`
- `.session-panel { width:280px; flex-shrink:0; background:#fff; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.06); display:flex; flex-direction:column; overflow:hidden; }`
- `.session-list { flex:1; overflow-y:auto; padding:8px; }`
- `.session-item { padding:12px; border-radius:6px; cursor:pointer; margin-bottom:4px; transition:background 0.15s; }`
- `.session-item:hover { background:#f0f7ff; }`
- `.session-item.active { background:#e6f7ff; border-left:3px solid #1890ff; }`
- `.chat-main { flex:1; min-width:0; }`
- `.chat-card { height:100%; display:flex; flex-direction:column; }`
- `.session-item-top { display:flex; justify-content:space-between; align-items:center; margin-bottom:4px; }`
- `.session-user { font-weight:600; font-size:13px; }`
- `.session-time { font-size:11px; color:#bbb; }`
- `.session-item-bottom { display:flex; align-items:center; gap:6px; }`
- `.session-preview { font-size:12px; color:#999; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; flex:1; }`

## 改造三：全局页头 —— 所有页面统一

### 每个页面顶部加页头区：
```
<div class="page-header">
  <div class="page-breadcrumb">
    <i data-lucide="图标名" class="breadcrumb-icon"></i>
    <span>页面标题</span>
  </div>
  <div class="header-actions">
    <!-- 该页面的操作按钮 -->
  </div>
</div>
```

### 各页面页头配置：
| 页面 | 图标 | 标题 | 右侧操作 |
|------|------|------|---------|
| Dashboard | layout-dashboard | 仪表盘 | 运行归因 / 执行提案 / 生成周报 |
| Chat | message-circle | 对话 · 客服工作台 | 新会话 |
| Sessions | history | 会话历史 | 搜索框 |
| Knowledge | book-open | 知识库管理 | 上传按钮 |
| Settings | settings | 设置中心 | — |
| Review | clipboard-check | 归因审批 | 刷新按钮 |
| Tenants | building-2 | 租户管理 | 新建租户 |
| TestCenter | flask-conical | 测试中心 | 清空结果 |

### 通用页头 CSS（每个页面都要加，或者写一个全局样式）：
```css
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding: 20px 24px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04);
}
.page-breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: rgba(0,0,0,0.85);
}
.breadcrumb-icon {
  display: inline-flex;
  align-items: center;
  color: #1890ff;
}
```

### 内容区调整
- 原来每个页面的 `.dashboard-page`（或各自的外层 div）padding 改为 `0 24px 24px`
- 页头单独在 padding 区域之上（全宽白色条）
- 内容卡片统一 margin-bottom: 16px

## 全局样式补丁（加到 App.vue 的 style 里，不加 scoped）

```css
/* 全局页头卡片 */
.page-header-card {
  background: #fff;
  border-radius: 8px;
  padding: 18px 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04);
  margin: 20px 24px 0;
}
```

## 实现顺序
1. Dashboard.vue — Bento Grid改造（改动最大）
2. Chat.vue — 双栏工作台（改动最大）
3. App.vue — 全局页头样式
4. Sessions.vue — 加页头
5. Knowledge.vue — 加页头
6. Settings.vue — 加页头
7. Review.vue — 加页头
8. Tenants.vue — 加页头
9. TestCenter.vue — 加页头

## 关键规则
1. ⚠️ 不删不改任何现有的 JS 函数体
2. ⚠️ 不删不改任何 computed/watch/onMounted（只能往末尾追加代码）
3. ⚠️ 不删不改任何 API fetch 调用
4. ⚠️ 不删不改任何 v-for/v-if 数据绑定表达式
5. Chat.vue 新增的会话列表数据来自已有的 `/api/sessions` 接口
6. 所有新 CSS 用 scoped，不污染全局
7. 页头面包屑的 Lucide 图标用 `<i data-lucide="xxx">` 渲染
