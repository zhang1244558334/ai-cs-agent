<template>
  <div class="sessions-page">
    <div class="page-header">
      <div class="page-breadcrumb">
        <i data-lucide="history" class="breadcrumb-icon"></i>
        <span>会话历史</span>
      </div>
      <el-input
        v-model="search"
        placeholder="搜索用户 ID"
        clearable
        class="search-input"
      />
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
            <span class="summary-user">{{ s.user_id || '-' }}</span>
            <el-tag v-if="s.last_intent" size="small" :type="intentTagType(s.last_intent)">
              {{ intentCN(s.last_intent) }}
            </el-tag>
            <span class="summary-msg">消息: {{ expandedMessages[s.id]?.length ?? '-' }}</span>
          </div>
          <div class="summary-meta">
            <el-tag :type="s.mode === 'ai' ? 'success' : 'warning'" size="small">{{ s.mode }}</el-tag>
            <span class="summary-time">{{ s.created_at }}</span>
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

const filteredSessions = computed(() => {
  if (!search.value) return sessions.value
  const q = search.value.toLowerCase()
  return sessions.value.filter(s => (s.user_id || '').toLowerCase().includes(q))
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
    const r = await fetch(`/api/sessions?limit=50&tenant_id=${localStorage.getItem('activeBusiness') || 'ecommerce'}`)
    sessions.value = (await r.json()) || []
  } catch (e) {
    sessions.value = []
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
.sessions-page {
  padding: 0 24px 24px;
  min-height: 100vh;
  background: #f0f2f5;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding: 20px 24px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
}
.page-breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.85);
}
.breadcrumb-icon {
  display: inline-flex;
  align-items: center;
  color: #1890ff;
}
.sessions-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  max-width: 860px;
}
.search-input {
  width: 220px;
}

/* ---- session list ---- */
.session-item {
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  margin-bottom: 10px;
  overflow: hidden;
}
.session-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  cursor: pointer;
  transition: background 0.15s;
}
.session-summary:hover {
  background: #fafafa;
}
.summary-main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}
.summary-user {
  font-weight: 600;
  color: rgba(0, 0, 0, 0.85);
}
.summary-msg {
  font-size: 12px;
  color: #999;
}
.summary-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.summary-time {
  font-size: 12px;
  color: #bbb;
  width: 140px;
  text-align: right;
}
.expand-icon {
  display: inline-flex;
  align-items: center;
  color: #bbb;
}

/* ---- expanded messages ---- */
.session-messages {
  padding: 0 16px 16px;
  background: #fafafa;
  border-top: 1px solid #f0f0f0;
}
.msg-loading,
.msg-empty {
  padding: 20px 0;
  text-align: center;
  font-size: 13px;
  color: #999;
}
.msg-row {
  display: flex;
  margin-top: 12px;
}
.msg-row.user {
  justify-content: flex-end;
}
.msg-row.assistant {
  justify-content: flex-start;
}
.msg-bubble {
  max-width: 70%;
  padding: 8px 12px;
  border-radius: 10px;
  word-break: break-word;
}
.msg-bubble.user {
  background: #1890ff;
  color: #fff;
  border-bottom-right-radius: 3px;
}
.msg-bubble.assistant {
  background: #f0f0f0;
  color: rgba(0, 0, 0, 0.85);
  border-bottom-left-radius: 3px;
}
.msg-text {
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.5;
}
.msg-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
}
.msg-time {
  font-size: 10px;
  opacity: 0.55;
}
.msg-bubble.user .msg-time {
  color: rgba(255, 255, 255, 0.7);
}
.msg-bubble.assistant .msg-time {
  color: #999;
}

.empty-row {
  padding: 40px 0;
  text-align: center;
  color: #bbb;
  font-size: 14px;
}
</style>
