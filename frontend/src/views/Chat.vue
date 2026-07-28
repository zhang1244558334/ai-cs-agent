<template>
  <div style="padding: 20px; max-width: 800px; margin: 0 auto; height: calc(100vh - 100px); display: flex; flex-direction: column">
    <h3 style="margin-top: 0">客服对话</h3>
    <div
      id="msg-box"
      style="flex: 1; overflow-y: auto; border: 1px solid #dcdfe6; padding: 12px; background: #fafafa; border-radius: 4px; margin-bottom: 12px"
    >
      <div v-for="(msg, i) in messages" :key="i" style="margin-bottom: 12px">
        <div :style="{ textAlign: msg.role === 'user' ? 'right' : 'left' }">
          <el-tag
            :type="msg.role === 'user' ? '' : 'success'"
            size="small"
            style="margin-right: 6px"
          >
            {{ msg.role === 'user' ? '我' : 'AI' }}
          </el-tag>
          <span
            :style="{
              background: msg.role === 'user' ? '#ecf5ff' : '#f0f9eb',
              padding: '6px 12px',
              borderRadius: '4px',
              display: 'inline-block',
              maxWidth: '70%',
              whiteSpace: 'pre-wrap',
            }"
          >
            {{ msg.content }}
          </span>
        </div>
        <div
          v-if="msg.intent"
          :style="{ textAlign: msg.role === 'user' ? 'right' : 'left', marginTop: '4px' }"
        >
          <el-tag
            :type="intentTagType(msg.intent)"
            size="small"
            effect="plain"
          >
            {{ msg.intent }}
          </el-tag>
        </div>
      </div>
      <div v-if="loading" style="color: #909399; text-align: left">
        <el-tag type="success" size="small" style="margin-right: 6px">AI</el-tag>
        <span style="color: #909399">正在输入...</span>
      </div>
    </div>
    <div style="display: flex; gap: 8px; margin-top: 12px">
      <el-input
        v-model="inputMsg"
        placeholder="输入消息，如：这个多少钱"
        @keyup.enter="send"
        :disabled="loading"
        clearable
      />
      <el-button type="primary" @click="send" :loading="loading" :disabled="loading">
        发送
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

const inputMsg = ref('')
const messages = ref([])
const loading = ref(false)

function intentTagType(intent) {
  if (intent === 'handover') return 'warning'
  if (intent === 'complaint') return 'danger'
  if (intent === 'error') return 'danger'
  return 'info'
}

function scrollDown() {
  nextTick(() => {
    const box = document.getElementById('msg-box')
    if (box) box.scrollTop = box.scrollHeight
  })
}

async function send() {
  if (!inputMsg.value || loading.value) return
  const msg = inputMsg.value
  messages.value.push({ role: 'user', content: msg })
  inputMsg.value = ''
  scrollDown()

  loading.value = true
  let fullReply = ''
  let intent = ''

  try {
    const resp = await fetch(
      '/api/chats?message=' +
        encodeURIComponent(msg) +
        '&platform_session_id=web&user_id=admin',
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
                })
              }
              scrollDown()
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
    })
  }
  loading.value = false
  scrollDown()
}
</script>
