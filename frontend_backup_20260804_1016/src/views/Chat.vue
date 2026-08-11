<template>
  <div class="dashboard-page">
    <div class="chat-card">
      <div class="chat-header">
        <el-button size="small" @click="newSession">新会话</el-button>
        <span class="session-id">{{ sessionId ? '会话 ' + sessionId.slice(0, 8) : '未创建会话' }}</span>
      </div>

      <div id="msg-box" class="chat-body" @scroll="onScroll">
        <div v-for="(msg, i) in messages" :key="i" class="msg-wrapper" :class="msg.role">
          <div class="msg-bubble" :class="msg.role">
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
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'

const inputMsg = ref('')
const messages = ref([])
const loading = ref(false)
const sessionId = ref('')
const isAtBottom = ref(true)

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
  fetch('/api/sessions?limit=1').then(r => r.json()).then(sessions => {
    if (sessions.length > 0) {
      sessionId.value = sessions[0].id
      loadProactiveMessages()
    }
  })
})

function intentCN(intent) {
  const map = {
    price: '议价', logistics: '物流', after_sale: '售后',
    tech: '产品', default: '通用', handover: '转人工',
    complaint: '投诉', no_reply: '无回复', error: '错误',
  }
  return map[intent] || intent
}

function intentTagType(intent) {
  if (intent === 'handover') return 'warning'
  if (intent === 'complaint') return 'danger'
  if (intent === 'error') return 'danger'
  return 'info'
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
        '&platform_session_id=' + encodeURIComponent(sessionId.value || 'web') + '&user_id=admin',
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
.dashboard-page {
  padding: 24px;
  height: calc(100vh - 48px);
  background: #f0f2f5;
  display: flex;
  flex-direction: column;
}
.chat-card {
  display: flex;
  flex-direction: column;
  flex: 1;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  max-width: 860px;
  width: 100%;
  margin: 0 auto;
}

/* ---- header ---- */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-bottom: 1px solid #f0f0f0;
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
  margin-bottom: 16px;
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
  border-radius: 12px;
  word-break: break-word;
}
.msg-bubble.user {
  background: #1890ff;
  color: #fff;
  border-bottom-right-radius: 4px;
}
.msg-bubble.assistant {
  background: #f5f5f5;
  color: rgba(0, 0, 0, 0.85);
  border-bottom-left-radius: 4px;
}
.msg-text {
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.5;
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
  opacity: 0.4;
  transition: all 0.15s;
  line-height: 1;
}
.fb-btn:hover {
  opacity: 0.8;
  background: rgba(0, 0, 0, 0.06);
}
.fb-btn.active {
  opacity: 1;
  border-color: #1890ff;
  background: rgba(24, 144, 255, 0.08);
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
  background: #bbb;
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
  background: #fff;
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
  border-top: 1px solid #f0f0f0;
  align-items: center;
}
.chat-input {
  flex: 1;
}
.send-btn {
  width: 40px;
  height: 40px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.send-btn i {
  display: inline-flex;
  align-items: center;
}
</style>
