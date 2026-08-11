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
            <el-button v-if="sessionId" type="danger" size="small" @click="deleteCurrentSession">
              <i data-lucide="trash-2"></i>
            </el-button>
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
  window.addEventListener('sessions-changed', loadSessions)
})
onActivated(() => {
  loadSessions()
})
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  window.removeEventListener('sessions-changed', loadSessions)
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

async function deleteCurrentSession() {
  if (!sessionId.value) return
  if (!confirm('确定删除当前会话及其所有消息？')) return
  try {
    const r = await fetch(`/api/sessions/${sessionId.value}`, { method: 'DELETE' })
    if (!r.ok) { alert('删除失败'); return }
    sessionId.value = ''
    messages.value = []
    await loadSessions()
    refreshIcons()
    window.dispatchEvent(new CustomEvent('sessions-changed'))
  } catch (e) {
    alert('删除失败: ' + e.message)
  }
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
  height: 100vh;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 0 24px 16px;
  padding: 16px 24px;
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

.chat-workspace {
  display: flex; flex: 1; overflow: hidden;
  padding: 0 24px 24px; gap: 16px;
}

.session-panel {
  width: 270px; flex-shrink: 0;
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  box-shadow: var(--glass-shadow);
  display: flex; flex-direction: column; overflow: hidden;
}
.panel-search {
  padding: 14px;
  border-bottom: 1px solid rgba(0,0,0,0.04);
}
.session-list { flex: 1; overflow-y: auto; padding: 8px; }
.session-item {
  padding: 12px 14px; border-radius: 12px; cursor: pointer;
  margin-bottom: 4px; transition: all 0.2s;
  border: 1px solid transparent;
}
.session-item:hover {
  background: var(--glass-bg-hover);
  border-color: var(--glass-border);
}
.session-item.active {
  background: rgba(99, 102, 241, 0.1);
  border-color: rgba(99, 102, 241, 0.2);
  box-shadow: inset 0 0 0 1px rgba(99, 102, 241, 0.15);
}
.session-item-top {
  display: flex; justify-content: space-between;
  align-items: center; margin-bottom: 4px;
}
.session-user { font-weight: 600; font-size: 13px; color: var(--text-primary); }
.session-time { font-size: 11px; color: var(--text-muted); }
.session-item-bottom { display: flex; align-items: center; gap: 6px; }
.session-preview {
  font-size: 12px; color: var(--text-secondary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1;
}

.chat-main { flex: 1; min-width: 0; }
.chat-card {
  height: 100%; display: flex; flex-direction: column;
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  box-shadow: var(--glass-shadow);
  overflow: hidden;
}
.chat-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 22px;
  border-bottom: 1px solid rgba(0,0,0,0.04);
}
.session-id { font-size: 12px; color: var(--text-muted); font-family: monospace; letter-spacing: 0.5px; }

.chat-body { flex: 1; overflow-y: auto; padding: 24px; position: relative; scroll-behavior: smooth; }
.msg-wrapper { display: flex; margin-bottom: 20px; }
.msg-wrapper.user { justify-content: flex-end; }
.msg-wrapper.assistant { justify-content: flex-start; }

.msg-bubble {
  max-width: 72%; padding: 12px 18px; border-radius: 18px;
  word-break: break-word;
}
.msg-bubble.user {
  background: rgba(99, 102, 241, 0.12);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(99, 102, 241, 0.15);
  color: var(--text-primary);
  border-bottom-right-radius: 6px;
}
.msg-bubble.assistant {
  background: var(--glass-bg);
  backdrop-filter: blur(16px);
  border: 1px solid var(--glass-border);
  color: var(--text-primary);
  border-bottom-left-radius: 6px;
  box-shadow: 0 2px 8px rgba(31, 38, 135, 0.04);
}
.msg-text { white-space: pre-wrap; font-size: 14px; line-height: 1.7; }
.msg-meta { display: flex; align-items: center; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
.msg-time { font-size: 11px; color: var(--text-muted); }
.msg-bubble.user .msg-time { color: rgba(99, 102, 241, 0.5); }
.proactive-tag { font-size: 11px !important; }

.feedback-btns { display: inline-flex; gap: 4px; margin-left: 8px; }
.fb-btn {
  background: rgba(0,0,0,0.04); border: 1px solid rgba(0,0,0,0.06);
  font-size: 13px; cursor: pointer; padding: 2px 6px; border-radius: 8px;
  opacity: 0.4; transition: all 0.2s; line-height: 1;
}
.fb-btn:hover { opacity: 0.85; background: rgba(99, 102, 241, 0.08); border-color: rgba(99, 102, 241, 0.15); }
.fb-btn.active {
  opacity: 1; border-color: var(--accent); background: rgba(99, 102, 241, 0.1);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.15);
}

.loading-bubble { min-width: 52px; display: flex; align-items: center; justify-content: center; }
.dot-pulse i {
  display: inline-block; width: 7px; height: 7px; border-radius: 50%;
  background: var(--accent); margin: 0 3px;
  animation: dotBounce 1.4s infinite ease-in-out both;
  font-style: normal; font-size: 0; line-height: 0;
}
.dot-pulse i:nth-child(1) { animation-delay: -0.32s; }
.dot-pulse i:nth-child(2) { animation-delay: -0.16s; }
.dot-pulse i:nth-child(3) { animation-delay: 0s; }
@keyframes dotBounce {
  0%, 80%, 100% { transform: scale(0); opacity: 0.2; }
  40% { transform: scale(1); opacity: 1; }
}

.scroll-bottom {
  position: sticky; bottom: 10px; left: 50%; transform: translateX(-50%);
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 18px;
  background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(12px);
  border: 1px solid var(--glass-border); border-radius: 20px;
  box-shadow: var(--glass-shadow); font-size: 12px; color: var(--text-secondary);
  cursor: pointer; z-index: 10; transition: all 0.2s;
}
.scroll-bottom:hover { background: rgba(255,255,255,0.85); box-shadow: 0 12px 40px rgba(31,38,135,0.14); }
.scroll-bottom i { display: inline-flex; align-items: center; }

.chat-footer {
  display: flex; gap: 10px; padding: 14px 20px;
  background: rgba(255, 255, 255, 0.3); backdrop-filter: blur(16px);
  border-top: 1px solid rgba(255, 255, 255, 0.15); align-items: center;
}
.chat-input { flex: 1; }
.send-btn {
  width: 44px; height: 44px; padding: 0;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; border-radius: 12px;
  background: var(--accent) !important; border-color: var(--accent) !important;
  box-shadow: 0 4px 14px var(--accent-glow); transition: all 0.2s;
}
.send-btn:hover { transform: translateY(-1px); box-shadow: 0 6px 20px var(--accent-glow); }
.send-btn i { display: inline-flex; align-items: center; }
.chat-input :deep(.el-input__wrapper) {
  background: rgba(255,255,255,0.35) !important; backdrop-filter: blur(8px);
  border-radius: 12px !important;
  box-shadow: 0 0 0 1px rgba(255,255,255,0.25) inset !important;
  transition: all 0.2s;
}
.chat-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px var(--accent-glow), 0 0 0 1px rgba(255,255,255,0.25) inset !important;
  background: rgba(255,255,255,0.5) !important;
}

.form-slot-bubble {
  background: rgba(99, 102, 241, 0.08); backdrop-filter: blur(12px);
  border: 1px solid rgba(99, 102, 241, 0.18); border-radius: 16px;
  padding: 18px 22px; max-width: 80%;
}
.form-slot-label {
  font-size: 11px; color: var(--accent); font-weight: 700;
  margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.8px;
}
.form-slot-prompt { font-size: 14px; color: var(--text-primary); line-height: 1.7; }
.form-confirm-card {
  background: rgba(16, 185, 129, 0.06); backdrop-filter: blur(12px);
  border: 1px solid rgba(16, 185, 129, 0.18); border-radius: 16px;
  padding: 22px; max-width: 85%; box-shadow: 0 4px 20px rgba(16,185,129,0.08);
}
.form-confirm-title { font-size: 15px; font-weight: 700; color: var(--success); margin-bottom: 14px; }
.form-confirm-body { margin-bottom: 14px; }
.form-summary {
  white-space: pre-wrap; font-size: 13px; color: var(--text-primary); line-height: 1.8; margin: 0;
  font-family: inherit; background: rgba(16,185,129,0.06);
  padding: 14px; border-radius: 12px; border: 1px solid rgba(16,185,129,0.1);
}
.form-confirm-hint { font-size: 12px; color: var(--text-muted); text-align: center; }
.form-done-card {
  background: rgba(16,185,129,0.08); backdrop-filter: blur(12px);
  border: 1px solid rgba(16,185,129,0.15); border-radius: 16px;
  padding: 18px 22px; max-width: 80%;
}
.form-done-icon { font-size: 22px; margin-bottom: 8px; }
.form-done-text { font-size: 14px; color: var(--text-primary); line-height: 1.7; }

.card-logistics {
  background: rgba(255,255,255,0.6); backdrop-filter: blur(16px);
  border: 1px solid var(--glass-border); border-radius: 16px;
  box-shadow: var(--glass-shadow); max-width: 88%; overflow: hidden;
}
.card-hd {
  display: flex; align-items: center; gap: 10px; padding: 14px 20px;
  background: rgba(99,102,241,0.07); border-bottom: 1px solid rgba(99,102,241,0.1);
  font-size: 14px; font-weight: 600; color: var(--text-primary);
}
.card-hd-icon { display: inline-flex; color: var(--accent); }
.card-badge {
  margin-left: auto; font-size: 11px; padding: 3px 12px;
  border-radius: 12px; font-weight: 600; backdrop-filter: blur(8px);
}
.card-badge.派送中, .card-badge.运输中 { background: rgba(99,102,241,0.12); color: var(--accent); }
.card-badge.已签收 { background: rgba(16,185,129,0.12); color: var(--success); }
.card-badge.已发货 { background: rgba(245,158,11,0.12); color: var(--warning); }
.card-bd { padding: 14px 20px; }
.card-row {
  display: flex; justify-content: space-between; padding: 8px 0; font-size: 13px;
  color: var(--text-secondary); border-bottom: 1px solid rgba(0,0,0,0.03);
}
.card-row:last-child { border-bottom: none; }
.card-row span:first-child { color: var(--text-muted); }
.eta { color: var(--success); font-weight: 600; }
.card-timeline { padding: 0 20px 16px; }
.tl-title {
  font-size: 12px; color: var(--text-muted); margin-bottom: 12px;
  padding-top: 10px; border-top: 1px solid rgba(0,0,0,0.03);
}
.tl-node { display: flex; gap: 12px; padding-bottom: 14px; position: relative; }
.tl-node:not(:last-child)::before {
  content:''; position: absolute; left: 4px; top: 12px; bottom: 0;
  width: 1px; background: rgba(0,0,0,0.06);
}
.tl-dot { width: 9px; height: 9px; border-radius: 50%; background: rgba(0,0,0,0.1); flex-shrink: 0; margin-top: 4px; }
.tl-node.on .tl-dot { background: var(--accent); box-shadow: 0 0 0 4px var(--accent-glow); }
.tl-node.on .tl-text { color: var(--accent); font-weight: 600; }
.tl-text { font-size: 13px; color: var(--text-primary); }
.tl-meta { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

/* ---- dark mode: Chat ---- */
.layout.dark .chat-page {
  background: transparent;
}
.layout.dark .chat-footer {
  background: rgba(30, 28, 51, 0.85) !important;
  backdrop-filter: blur(16px);
  border-top-color: rgba(255,255,255,0.06);
}
.layout.dark .chat-input :deep(.el-input__wrapper) {
  background: rgba(255,255,255,0.06) !important;
  box-shadow: 0 0 0 1px rgba(255,255,255,0.1) inset !important;
}
.layout.dark .chat-input :deep(.el-input__wrapper.is-focus) {
  background: rgba(255,255,255,0.1) !important;
  box-shadow: 0 0 0 2px rgba(79, 195, 247, 0.3), 0 0 0 1px rgba(255,255,255,0.1) inset !important;
}
.layout.dark .chat-input :deep(.el-input__inner) {
  color: var(--text-primary) !important;
}
.layout.dark .chat-input :deep(.el-input__inner::placeholder) {
  color: var(--text-muted) !important;
}
.layout.dark .chat-body {
  background: transparent;
}
.layout.dark .chat-header {
  border-bottom-color: rgba(255,255,255,0.06);
}
.layout.dark .chat-header .session-id {
  color: var(--text-secondary);
}
.layout.dark .msg-bubble.user {
  background: rgba(79, 195, 247, 0.12) !important;
  border-color: rgba(79, 195, 247, 0.18) !important;
}
.layout.dark .msg-bubble.assistant {
  background: rgba(255,255,255,0.04) !important;
  border-color: rgba(255,255,255,0.06) !important;
}
.layout.dark .session-panel {
  background: rgba(30, 28, 51, 0.6);
}
.layout.dark .session-item {
  color: var(--text-secondary);
}
.layout.dark .session-item.active {
  background: rgba(79, 195, 247, 0.08);
}
.layout.dark .session-item:hover {
  background: rgba(255,255,255,0.04);
}
</style>