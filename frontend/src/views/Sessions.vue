<template>
  <div class="sessions-page">
    <div class="page-header">
      <div class="page-breadcrumb">
        <i data-lucide="history" class="breadcrumb-icon"></i>
        <span>会话历史</span>
      </div>
      <div class="header-right">
        <label class="select-all-label">
          <input type="checkbox" :checked="allSelected" @change="toggleSelectAll" />
          <span>全选</span>
        </label>
        <el-input
          v-model="search"
          placeholder="搜索用户 ID"
          clearable
          class="search-input"
        />
      </div>
    </div>
    <div class="sessions-card">
      <div v-if="filteredSessions.length === 0" class="empty-row">暂无会话记录</div>

      <div
        v-for="s in filteredSessions"
        :key="s.id"
        class="session-item"
      >
        <div class="session-summary" @click="toggle(s.id)">
          <div class="summary-main">
            <input type="checkbox" :checked="selectedIds.has(s.id)" @click.stop @change="toggleSelect(s.id)" class="session-checkbox" />
            <span class="summary-user">{{ s.user_id || '-' }}</span>
            <el-tag v-if="s.last_intent" size="small" :type="intentTagType(s.last_intent)">
              {{ intentCN(s.last_intent) }}
            </el-tag>
            <span class="summary-msg">消息: {{ expandedMessages[s.id]?.length ?? '-' }}</span>
          </div>
          <div class="summary-meta">
            <el-tag :type="s.mode === 'ai' ? 'success' : 'warning'" size="small">{{ s.mode }}</el-tag>
            <span class="summary-time">{{ s.created_at }}</span>
            <el-button type="danger" size="small" @click.stop="deleteSession(s.id)">
              <i data-lucide="trash-2"></i>
            </el-button>
            <i :data-lucide="expanded === s.id ? 'chevron-up' : 'chevron-down'" class="expand-icon"></i>
          </div>
        </div>

        <div v-if="expanded === s.id" class="session-messages">
          <div v-if="loadingMsgs" class="msg-loading">加载中...</div>
          <div v-else-if="expandedMessages[s.id]?.length">
            <div
              v-for="m in expandedMessages[s.id]"
              :key="m.id"
              class="msg-row"
              :class="m.role"
            >
              <div class="msg-bubble" :class="m.role">
                <div class="msg-text">{{ m.content }}</div>
                <div class="msg-meta">
                  <span class="msg-time">{{ fmtTime(m.created_at) }}</span>
                  <el-tag
                    v-if="m.extra_metadata?.intent && m.role === 'assistant'"
                    size="small"
                    :type="intentTagType(m.extra_metadata.intent)"
                    effect="plain"
                  >{{ intentCN(m.extra_metadata.intent) }}</el-tag>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="msg-empty">暂无消息</div>
        </div>
      </div>
      <div v-if="selectedIds.size > 0" class="batch-bar">
        <span class="batch-count">已选 {{ selectedIds.size }} 项</span>
        <el-button type="danger" size="small" @click="batchDelete">批量删除</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated, nextTick } from 'vue'

const sessions = ref([])
const expanded = ref(null)
const expandedMessages = ref({})
const loadingMsgs = ref(false)
const search = ref('')
const selectedIds = ref(new Set())

const filteredSessions = computed(() => {
  if (!search.value) return sessions.value
  const q = search.value.toLowerCase()
  return sessions.value.filter(s => (s.user_id || '').toLowerCase().includes(q))
})

const allSelected = computed(() => {
  if (filteredSessions.value.length === 0) return false
  return filteredSessions.value.every(s => selectedIds.value.has(s.id))
})

function fmtTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function intentCN(intent) {
  const map = {
    price: '议价', logistics: '物流', after_sale: '售后',
    tech: '产品', default: '通用', handover: '转人工',
    complaint: '投诉', complain: '投诉', no_reply: '无回复',
    fee: '缴费', repair: '报修', notice: '公告',
  }
  return map[intent] || intent
}
function intentTagType(intent) {
  if (intent === 'handover') return 'warning'
  if (['complaint', 'complain'].includes(intent)) return 'danger'
  return 'info'
}

function refreshIcons() {
  nextTick(() => {
    if (window.lucide) {
      window.lucide.createIcons({ attrs: { width: '16', height: '16' } })
    }
  })
}

async function loadSessions() {
  try {
    const r = await fetch(`/api/sessions?limit=50`)
    sessions.value = (await r.json()) || []
  } catch (e) {
    sessions.value = []
  }
}

async function deleteSession(id) {
  if (!confirm('确定删除该会话及其所有消息？')) return
  try {
    const r = await fetch(`/api/sessions/${id}`, { method: 'DELETE' })
    if (!r.ok) { alert('删除失败'); return }
    sessions.value = sessions.value.filter(s => s.id !== id)
    if (expanded.value === id) expanded.value = null
    const set = new Set(selectedIds.value)
    set.delete(id)
    selectedIds.value = set
    refreshIcons()
    window.dispatchEvent(new CustomEvent('sessions-changed'))
  } catch (e) {
    alert('删除失败: ' + e.message)
  }
}

function toggleSelect(id) {
  const set = new Set(selectedIds.value)
  if (set.has(id)) set.delete(id)
  else set.add(id)
  selectedIds.value = set
}

function toggleSelectAll() {
  if (allSelected.value) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(filteredSessions.value.map(s => s.id))
  }
}

async function batchDelete() {
  if (!confirm(`确定删除选中的 ${selectedIds.value.size} 个会话及其消息？`)) return
  try {
    const ids = [...selectedIds.value]
    const r = await fetch('/api/sessions/batch-delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids }),
    })
    if (!r.ok) { alert('批量删除失败'); return }
    sessions.value = sessions.value.filter(s => !selectedIds.value.has(s.id))
    for (const id of ids) {
      if (expanded.value === id) expanded.value = null
    }
    selectedIds.value = new Set()
    refreshIcons()
    window.dispatchEvent(new CustomEvent('sessions-changed'))
  } catch (e) {
    // ignore
  }
}

async function toggle(id) {
  if (expanded.value === id) {
    expanded.value = null
    return
  }
  expanded.value = id
  if (expandedMessages.value[id]) {
    refreshIcons()
    return
  }
  loadingMsgs.value = true
  try {
    const r = await fetch(`/api/sessions/${id}/messages?limit=10`)
    expandedMessages.value[id] = (await r.json()) || []
  } catch (e) {
    expandedMessages.value[id] = []
  }
  loadingMsgs.value = false
  refreshIcons()
}

onMounted(() => {
  loadSessions()
  window.addEventListener('business-changed', () => {
    loadSessions()
  })
})
onActivated(() => {
  loadSessions()
})
</script>

<style scoped>
.sessions-page { padding: 0 24px 24px; min-height: 100vh; }

.page-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 20px; padding: 16px 24px;
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  box-shadow: var(--glass-shadow);
}
.page-breadcrumb {
  display: flex; align-items: center; gap: 10px;
  font-size: 18px; font-weight: 700; color: var(--text-primary);
}
.breadcrumb-icon { display: inline-flex; align-items: center; color: var(--accent); }
.header-actions { display: flex; gap: 8px; }
.btn-icon { display: inline-flex; vertical-align: middle; margin-right: 2px; }

.sessions-card {
  background: var(--glass-bg); backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border); border-radius: var(--radius-md);
  box-shadow: var(--glass-shadow); max-width: 860px;
}
.search-input { width: 220px; }
.header-right { display: flex; align-items: center; gap: 12px; }
.select-all-label { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; color: var(--accent); cursor: pointer; white-space: nowrap; background: var(--accent-light); padding: 6px 12px; border-radius: 8px; transition: all 0.2s; }
.select-all-label:hover { background: rgba(99,102,241,0.2); }
.select-all-label input { cursor: pointer; }
.session-item { border: 1px solid rgba(0,0,0,0.04); border-radius: 12px; margin-bottom: 10px; overflow: hidden; transition: all 0.2s; }
.session-item:hover { border-color: var(--glass-border); }
.session-summary { display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; cursor: pointer; transition: background 0.15s; }
.session-summary:hover { background: rgba(255,255,255,0.3); }
.summary-main { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }
.session-checkbox { flex-shrink: 0; cursor: pointer; }
.summary-user { font-weight: 600; color: var(--text-primary); }
.summary-msg { font-size: 12px; color: var(--text-muted); }
.summary-meta { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.summary-time { font-size: 12px; color: var(--text-muted); width: 140px; text-align: right; }
.expand-icon { display: inline-flex; align-items: center; color: var(--text-muted); }
.session-messages { padding: 0 18px 18px; background: rgba(255,255,255,0.2); border-top: 1px solid rgba(0,0,0,0.04); }
.msg-loading, .msg-empty { padding: 20px 0; text-align: center; font-size: 13px; color: var(--text-muted); }
.msg-row { display: flex; margin-top: 12px; }
.msg-row.user { justify-content: flex-end; }
.msg-row.assistant { justify-content: flex-start; }
.msg-bubble { max-width: 70%; padding: 10px 16px; border-radius: 14px; word-break: break-word; }
.msg-bubble.user { background: rgba(99,102,241,0.12); backdrop-filter: blur(12px); border: 1px solid rgba(99,102,241,0.15); color: var(--text-primary); border-bottom-right-radius: 4px; }
.msg-bubble.assistant { background: var(--glass-bg); backdrop-filter: blur(12px); border: 1px solid var(--glass-border); color: var(--text-primary); border-bottom-left-radius: 4px; }
.msg-text { white-space: pre-wrap; font-size: 13px; line-height: 1.6; }
.msg-meta { display: flex; align-items: center; gap: 6px; margin-top: 4px; }
.msg-time { font-size: 10px; color: var(--text-muted); }
.msg-bubble.user .msg-time { color: rgba(99,102,241,0.5); }
.msg-bubble.assistant .msg-time { color: var(--text-muted); }
.empty-row { padding: 40px 0; text-align: center; color: var(--text-muted); font-size: 14px; }
.batch-bar { display: flex; align-items: center; justify-content: space-between; margin-top: 14px; padding: 12px 18px; background: rgba(239,68,68,0.06); backdrop-filter: blur(12px); border: 1px solid rgba(239,68,68,0.15); border-radius: 12px; }
.batch-count { font-size: 13px; color: var(--danger); font-weight: 500; }
</style>
