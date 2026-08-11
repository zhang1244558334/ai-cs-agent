<template>
  <div class="chat-page">
    <div class="page-header">
      <div class="page-breadcrumb">
        <i data-lucide="message-circle" class="breadcrumb-icon"></i>
        <span>对话 · 客服工作台</span>
      </div>
      <el-button size="small" @click="newSession">+ 新会话</el-button>
    </div>

    <div class="chat-workspace">
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

      <div class="chat-main">
        <div class="chat-card">
          <div class="chat-header">
            <span class="session-id">{{ sessionId ? '会话 ' + sessionId.slice(0, 8) : '未创建会话' }}</span>
          </div>

          <div id="msg-box" class="chat-body" @scroll="onScroll">
            <div v-for="(msg, i) in messages" :key="i" class="msg-wrapper" :class="msg.role">
              <div v-if="msg.msgType === 'form_slot'" class="form-slot-bubble">
                <div class="form-slot-label">{{ msg.label || '请填写' }}</div>
                <div class="form-slot-prompt">{{ msg.content }}</div>
              </div>
              <div v-else-if="msg.msgType === 'form_confirm'" class="form-confirm-card">
                <div class="form-confirm-title">信息确认</div>
                <div class="form-confirm-body"><pre class="form-summary">{{ msg.content }}</pre></div>
                <div class="form-confirm-hint">请回复"确认"提交，或回复"修改"调整</div>
              </div>
              <div v-else-if="msg.msgType === 'form_done'" class="form-done-card">
                <div class="form-done-icon">✅</div>
                <div class="form-done-text">{{ msg.content }}</div>
              </div>
              <!-- 物流轨迹卡片 -->
              <div v-else-if="msg.msgType === 'card' && msg.cardType === 'logistics'" class="card-logistics">
                <div class="card-hd">
                  <i data-lucide="truck" class="card-hd-icon"></i>
                  <span>物流轨迹</span>
                  <span class="card-badge" :class="msg.cardData.status">{{ msg.cardData.status }}</span>
                </div>
                <div class="card-bd">
                  <div class="card-row"><span>订单号</span><span>{{ msg.cardData.order_no }}</span></div>
                  <div class="card-row"><span>承运商</span><span>{{ msg.cardData.carrier }}</span></div>
                  <div class="card-row"><span>运单号</span><span>{{ msg.cardData.tracking_no }}</span></div>
                  <div v-if="msg.cardData.eta" class="card-row"><span>预计送达</span><span class="eta">{{ msg.cardData.eta }}</span></div>
                </div>
                <div class="card-timeline" v-if="msg.cardData.trace?.length">
                  <div class="tl-title">物流详情</div>
                  <div class="tl-node" v-for="(t,i) in msg.cardData.trace" :key="i" :class="{on:i===msg.cardData.trace.length-1}">
                    <div class="tl-dot"></div>
                    <div><div class="tl-text">{{ t.node }}</div><div class="tl-meta">{{ t.time }} · {{ t.city }}</div></div>
                  </div>
                </div>
              </div>
              <!-- 售后卡片 -->
              <div v-else-if="msg.msgType === 'card' && msg.cardType === 'after_sale'" class="card-logistics">
                <div class="card-hd" style="background:linear-gradient(135deg,#fff7e6,#fff2e8)">
                  <i data-lucide="rotate-ccw" class="card-hd-icon" style="color:#fa8c16"></i>
                  <span>售后单</span>
                  <span class="card-badge" style="background:#fff7e6;color:#fa8c16">{{ msg.cardData.status }}</span>
                </div>
                <div class="card-bd">
                  <div class="card-row"><span>售后单号</span><span>{{ msg.cardData.service_no }}</span></div>
                  <div class="card-row"><span>关联订单</span><span>{{ msg.cardData.order_no }}</span></div>
                  <div class="card-row"><span>退款金额</span><span class="eta">{{ (msg.cardData.refund_amount/100).toFixed(2) }}元</span></div>
                </div>
              </div>
              <div v-else class="msg-bubble" :class="msg.role">
                <div class="msg-text">{{ msg.content }}</div>
                <div class="msg-meta">
                  <span class="msg-time">{{ msg.time }}</span>
                  <el-tag v-if="msg.is_proactive" size="small" type="warning" effect="plain" class="proactive-tag">系统主动</el-tag>
                  <el-tag
                    v-if="msg.intent && msg.role === 'assistant'"
                    size="small"
                    :type="intentTagType(msg.intent)"
                    effect="plain"
                  >{{ intentCN(msg.intent) }}</el-tag>
                  <span v-if="msg.role === 'assistant' && msg.id" class="feedback-btns">
                    <button
                      class="fb-btn"
                      :class="{ active: msg._feedback === 'thumbs_up' }"
                      @click.stop="sendFeedback(msg, 'thumbs_up')"
                      title="有用"
                    >👍</button>
                    <button
                      class="fb-btn"
                      :class="{ active: msg._feedback === 'thumbs_down' }"
                      @click.stop="sendFeedback(msg, 'thumbs_down')"
                      title="没用"
                    >👎</button>
                  </span>
                </div>
              </div>
            </div>

            <div v-if="loading" class="msg-wrapper assistant">
              <div class="msg-bubble assistant loading-bubble">
                <span class="dot-pulse"><i>.</i><i>.</i><i>.</i></span>
              </div>
            </div>

            <div v-show="!isAtBottom" class="scroll-bottom" @click="scrollDown">
              <i data-lucide="chevron-down"></i> 回到底部
            </div>
          </div>

          <div class="chat-footer">
            <el-input
              v-model="inputMsg"
              placeholder="输入消息，Enter 发送"
              @keyup.enter="send"
              :disabled="loading"
              class="chat-input"
            />
            <el-button type="primary" class="send-btn" @click="send" :disabled="loading || !inputMsg">
              <i data-lucide="send"></i>
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, onActivated, onUnmounted, computed } from 'vue'

const MSG_TYPES = {
  text: 'text',
  form_slot: 'form_slot',
  form_confirm: 'form_confirm',
  form_done: 'form_done'
}

const inputMsg = ref('')
const messages = ref([])
const loading = ref(false)
const sessionId = ref('')
const isAtBottom = ref(true)

const sessions = ref([])
const sessionSearch = ref('')
const filteredSessions = computed(() => {
  if (!sessionSearch.value) return sessions.value
  const q = sessionSearch.value.toLowerCase()
  return sessions.value.filter(s => (s.user_id || '').toLowerCase().includes(q))
})

function now() {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function refreshIcons() {
  nextTick(() => {
    if (window.lucide) {
      window.lucide.createIcons({ attrs: { width: '16', height: '16' } })
    }
  })
}

async function loadProactiveMessages() {
  if (!sessionId.value) return
  try {
    const resp = await fetch(`/api/sessions/${sessionId.value}/messages?limit=50`)
    if (!resp.ok) return
    const data = await resp.json()
    const proactive = data.filter(m => m.extra_metadata?.is_proactive)
    for (const m of proactive) {
      if (!messages.value.some(x => x.id === m.id)) {
        messages.value.push({
          id: m.id,
          role: m.role || 'assistant',
          content: m.content,
          is_proactive: true,
          time: m.created_at ? new Date(m.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : now(),
        })
      }
    }
    refreshIcons()
  } catch (e) {
    // ignore
  }
}

onMounted(() => {
  loadCurrentSession()
  loadSessions()
  pollTimer = setInterval(pollNewMessages, 3000)
  window.addEventListener('business-changed', () => {
    sessionId.value = ''
    messages.value = []
    loadCurrentSession()
    loadSessions()
  })
})
onActivated(() => {
  loadSessions()
})
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

let pollTimer = null
async function pollNewMessages() {
  if (!sessionId.value || loading.value) return
  try {
    const r = await fetch(`/api/sessions/${sessionId.value}/messages?limit=50`)
    if (!r.ok) return
    const data = await r.json()
    // 合并新消息（用id去重）
    const existingIds = new Set(messages.value.filter(m => m.id).map(m => m.id))
    let changed = false
    for (const m of data) {
      if (m.id && !existingIds.has(m.id)) {
        existingIds.add(m.id)
        messages.value.push({
          id: m.id,
          role: m.role,
          content: m.content,
          intent: m.extra_metadata?.intent,
          is_proactive: !!m.extra_metadata?.is_proactive,
          time: m.created_at ? new Date(m.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : now(),
        })
        changed = true
      }
    }
    if (changed && isAtBottom.value) scrollDown()
  } catch (e) { /* ignore */ }
}

function loadCurrentSession() {
  fetch(`/api/sessions?limit=1&tenant_id=${localStorage.getItem('activeBusiness') || 'ecommerce'}`).then(r => r.json()).then(sessions => {
    if (sessions.length > 0) {
      sessionId.value = sessions[0].id
      loadProactiveMessages()
    }
  })
}

function intentCN(intent) {
  const map = {
    price: '议价', logistics: '物流', after_sale: '售后',
    tech: '产品', default: '通用', handover: '转人工',
    complaint: '投诉', complain: '投诉', no_reply: '无回复', error: '错误',
    fee: '缴费', repair: '报修', notice: '公告',
  }
  return map[intent] || intent
}

function intentTagType(intent) {
  if (intent === 'handover') return 'warning'
  if (['complaint', 'complain'].includes(intent)) return 'danger'
  if (intent === 'error') return 'danger'
  return 'info'
}

function fmtSessionTime(t) {
  if (!t) return ''
  const d = new Date(t)
  const now = new Date()
  if (d.toDateString() === now.toDateString()) return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

async function loadSessions() {
  try {
    const r = await fetch(`/api/sessions?limit=30&tenant_id=${localStorage.getItem('activeBusiness') || 'ecommerce'}`)
    sessions.value = (await r.json()) || []
  } catch (e) { sessions.value = [] }
}

async function switchSession(id) {
  if (id === sessionId.value) return
  sessionId.value = id
  messages.value = []
  await loadProactiveMessages()
}

function onScroll() {
  const box = document.getElementById('msg-box')
  if (!box) return
  isAtBottom.value = (box.scrollHeight - box.scrollTop - box.clientHeight) < 80
}

function scrollDown() {
  nextTick(() => {
    const box = document.getElementById('msg-box')
    if (box) {
      box.scrollTop = box.scrollHeight
      isAtBottom.value = true
    }
  })
}

async function sendFeedback(msg, type) {
  if (!msg.id) return
  try {
    await fetch(`/api/messages/${msg.id}/feedback?feedback=${type}`, { method: 'POST' })
    msg._feedback = type
    refreshIcons()
  } catch (e) {
    console.error('反馈提交失败', e)
  }
}

function newSession() {
  sessionId.value = 'web_' + Date.now()
  messages.value = []
  inputMsg.value = ''
  refreshIcons()
}

async function send() {
  if (!inputMsg.value || loading.value) return
  const msg = inputMsg.value
  messages.value.push({ role: 'user', content: msg, time: now() })
  inputMsg.value = ''
  if (isAtBottom.value) scrollDown()

  loading.value = true
  let fullReply = ''
  let intent = ''

  try {
    const resp = await fetch(
      '/api/chats?message=' +
        encodeURIComponent(msg) +
        '&platform_session_id=' + encodeURIComponent(sessionId.value || 'web') + '&user_id=admin&tenant_id=' + (localStorage.getItem('activeBusiness') || 'ecommerce'),
      { method: 'POST' }
    )
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value, { stream: true })
      const lines = chunk.split('\n')
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.substring(6))
            if (data.intent) intent = data.intent
            if (data.message_id) {
              const last2 = messages.value[messages.value.length - 1]
              if (last2 && last2.role === 'assistant') last2.id = data.message_id
            }
            if (data.type === 'form_slot') {
              messages.value.push({
                role: 'assistant',
                content: data.prompt,
                msgType: 'form_slot',
                field: data.field,
                label: data.label,
                intent: data.intent,
                time: now(),
              })
              if (isAtBottom.value) scrollDown()
              continue
            }
            if (data.type === 'form_confirm') {
              messages.value.push({
                role: 'assistant',
                content: data.summary,
                msgType: 'form_confirm',
                actionLabel: data.action_label || '确认提交',
                intent: data.intent,
                time: now(),
              })
              if (isAtBottom.value) scrollDown()
              continue
            }
            if (data.type === 'form_done') {
              fullReply = data.result
              messages.value.push({
                role: 'assistant',
                content: data.result,
                msgType: 'form_done',
                intent: data.intent,
                time: now(),
              })
              if (isAtBottom.value) scrollDown()
              continue
            }
            if (data.type === 'card') {
              messages.value.push({
                role: 'assistant',
                content: '',
                msgType: 'card',
                cardType: data.card_type,
                cardData: data.data,
                intent: data.intent || intent,
                time: now(),
              })
              if (isAtBottom.value) scrollDown()
              continue
            }
            if (data.token) {
              fullReply += data.token
              const last = messages.value[messages.value.length - 1]
              if (last && last.role === 'assistant') {
                last.content = fullReply
              } else {
                messages.value.push({
                  role: 'assistant',
                  content: fullReply,
                  intent: intent,
                  time: now(),
                })
              }
              if (isAtBottom.value) scrollDown()
            }
          } catch (e) {
            // ignore parse errors on partial chunks
          }
        }
      }
    }
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.intent = intent
    }
  } catch (e) {
    console.error('请求失败:', e)
    messages.value.push({
      role: 'assistant',
      content: '请求失败，请重试',
      intent: 'error',
      time: now(),
    })
  }
  loading.value = false
  if (isAtBottom.value) scrollDown()
  refreshIcons()
}
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh);
  background: #f0f2f5;
}

/* ---- unified page header ---- */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 0 24px 16px;
  padding: 16px 24px;
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

/* ---- workspace ---- */
.chat-workspace {
  display: flex;
  flex: 1;
  overflow: hidden;
  padding: 0 24px 24px;
  gap: 16px;
}

/* ---- session panel ---- */
.session-panel {
  width: 280px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.panel-search {
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
}
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.session-item {
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: background 0.15s;
}
.session-item:hover {
  background: #f0f7ff;
}
.session-item.active {
  background: #e6f7ff;
  border-left: 3px solid #1890ff;
}
.session-item-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.session-user {
  font-weight: 600;
  font-size: 13px;
}
.session-time {
  font-size: 11px;
  color: #bbb;
}
.session-item-bottom {
  display: flex;
  align-items: center;
  gap: 6px;
}
.session-preview {
  font-size: 12px;
  color: #999;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

/* ---- chat main ---- */
.chat-main {
  flex: 1;
  min-width: 0;
}
.chat-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

/* ---- header ---- */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-bottom: 2px solid #f0f0f0;
}
.session-id {
  font-size: 12px;
  color: #999;
  font-family: monospace;
}

/* ---- body ---- */
.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  position: relative;
  scroll-behavior: smooth;
}
.msg-wrapper {
  display: flex;
  margin-bottom: 20px;
}
.msg-wrapper.user {
  justify-content: flex-end;
}
.msg-wrapper.assistant {
  justify-content: flex-start;
}
.msg-bubble {
  max-width: 72%;
  padding: 10px 14px;
  border-radius: 16px;
  word-break: break-word;
}
.msg-bubble.user {
  background: linear-gradient(135deg, #1890ff, #40a9ff);
  color: #fff;
  border-bottom-right-radius: 4px;
  box-shadow: 0 2px 6px rgba(24, 144, 255, 0.2);
}
.msg-bubble.assistant {
  background: #f7f8fa;
  color: rgba(0, 0, 0, 0.85);
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.msg-text {
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.6;
}
.msg-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  flex-wrap: wrap;
}
.msg-time {
  font-size: 11px;
  opacity: 0.55;
}
.msg-bubble.user .msg-time {
  color: rgba(255, 255, 255, 0.7);
}
.msg-bubble.assistant .msg-time {
  color: #999;
}
.proactive-tag {
  font-size: 11px !important;
}

/* ---- feedback buttons ---- */
.feedback-btns {
  display: inline-flex;
  gap: 4px;
  margin-left: 6px;
}
.fb-btn {
  background: none;
  border: 1px solid transparent;
  font-size: 13px;
  cursor: pointer;
  padding: 1px 3px;
  border-radius: 4px;
  opacity: 0.3;
  transition: all 0.15s;
  line-height: 1;
}
.fb-btn:hover {
  opacity: 0.9;
  background: rgba(0, 0, 0, 0.06);
}
.fb-btn.active {
  opacity: 1;
  border-color: #1890ff;
  background: rgba(24, 144, 255, 0.08);
  box-shadow: 0 1px 3px rgba(24, 144, 255, 0.15);
}

/* ---- loading dots ---- */
.loading-bubble {
  min-width: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.dot-pulse i {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #bfbfbf;
  margin: 0 2px;
  animation: dotBounce 1.4s infinite ease-in-out both;
  font-style: normal;
  font-size: 0;
  line-height: 0;
}
.dot-pulse i:nth-child(1) { animation-delay: -0.32s; }
.dot-pulse i:nth-child(2) { animation-delay: -0.16s; }
.dot-pulse i:nth-child(3) { animation-delay: 0s; }

@keyframes dotBounce {
  0%, 80%, 100% { transform: scale(0); opacity: 0.3; }
  40% { transform: scale(1); opacity: 1; }
}

/* ---- scroll-to-bottom ---- */
.scroll-bottom {
  position: sticky;
  bottom: 8px;
  left: 50%;
  transform: translateX(-50%);
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 16px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  border: 1px solid #e0e0e0;
  border-radius: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  font-size: 12px;
  color: #666;
  cursor: pointer;
  z-index: 10;
  transition: box-shadow 0.2s;
}
.scroll-bottom:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}
.scroll-bottom i {
  display: inline-flex;
  align-items: center;
}

/* ---- footer ---- */
.chat-footer {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  background: #fafafa;
  border-top: 1px solid #f0f0f0;
  align-items: center;
}
.chat-input {
  flex: 1;
}
.send-btn {
  width: 44px;
  height: 44px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 12px;
}
.send-btn i {
  display: inline-flex;
  align-items: center;
}

.chat-input :deep(.el-input__wrapper) {
  transition: box-shadow 0.2s;
}
.chat-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.15);
}

.form-slot-bubble {
  background: linear-gradient(135deg, #e6f7ff, #f0f5ff);
  border: 1px solid #91d5ff;
  border-radius: 12px;
  padding: 16px 20px;
  max-width: 80%;
}
.form-slot-label {
  font-size: 12px;
  color: #1890ff;
  font-weight: 600;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.form-slot-prompt {
  font-size: 14px;
  color: #333;
  line-height: 1.6;
}

.form-confirm-card {
  background: #fff;
  border: 2px solid #52c41a;
  border-radius: 12px;
  padding: 20px;
  max-width: 85%;
  box-shadow: 0 2px 12px rgba(82, 196, 26, 0.1);
}
.form-confirm-title {
  font-size: 16px;
  font-weight: 600;
  color: #52c41a;
  margin-bottom: 12px;
}
.form-confirm-body {
  margin-bottom: 12px;
}
.form-summary {
  white-space: pre-wrap;
  font-size: 14px;
  color: #333;
  line-height: 1.8;
  margin: 0;
  font-family: inherit;
  background: #f6ffed;
  padding: 12px;
  border-radius: 8px;
}
.form-confirm-hint {
  font-size: 12px;
  color: #999;
  text-align: center;
}

.form-done-card {
  background: linear-gradient(135deg, #f6ffed, #f0fff0);
  border: 1px solid #b7eb8f;
  border-radius: 12px;
  padding: 16px 20px;
  max-width: 80%;
}
.form-done-icon {
  font-size: 24px;
  margin-bottom: 8px;
}
.form-done-text {
  font-size: 14px;
  color: #333;
  line-height: 1.6;
}


/* ---- 物流卡片 ---- */
.card-logistics { background:#fff; border-radius:12px; box-shadow:0 2px 12px rgba(0,0,0,0.06); max-width:88%; overflow:hidden; }
.card-hd { display:flex; align-items:center; gap:8px; padding:14px 18px; background:linear-gradient(135deg,#e6f7ff,#f0f5ff); border-bottom:1px solid #e8f4fd; font-size:14px; font-weight:600; color:#333; }
.card-hd-icon { display:inline-flex; color:#1890ff; }
.card-badge { margin-left:auto; font-size:11px; padding:2px 10px; border-radius:10px; font-weight:500; }
.card-badge.d3e送中, .card-badge.运输中 { background:#e6f7ff; color:#1890ff; }
.card-badge.已签收 { background:#f6ffed; color:#52c41a; }
.card-badge.已发货 { background:#fff7e6; color:#fa8c16; }
.card-bd { padding:14px 18px; }
.card-row { display:flex; justify-content:space-between; padding:6px 0; font-size:13px; color:#666; border-bottom:1px dashed #f0f0f0; }
.card-row:last-child { border-bottom:none; }
.card-row span:first-child { color:#999; }
.eta { color:#52c41a; font-weight:600; }
.card-timeline { padding:0 18px 14px; }
.tl-title { font-size:12px; color:#999; margin-bottom:10px; padding-top:8px; border-top:1px solid #f0f0f0; }
.tl-node { display:flex; gap:10px; padding-bottom:14px; position:relative; }
.tl-node:not(:last-child)::before { content:''; position:absolute; left:4px; top:10px; bottom:0; width:1px; background:#e8e8e8; }
.tl-dot { width:9px; height:9px; border-radius:50%; background:#d9d9d9; flex-shrink:0; margin-top:3px; }
.tl-node.on .tl-dot { background:#1890ff; box-shadow:0 0 0 3px rgba(24,144,255,0.15); }
.tl-node.on .tl-text { color:#1890ff; font-weight:600; }
.tl-text { font-size:13px; color:#333; }
.tl-meta { font-size:11px; color:#999; margin-top:2px; }
</style>
