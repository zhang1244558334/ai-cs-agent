<template>
  <div style="padding: 20px; max-width: 800px; margin: 0 auto">
    <h3>客服对话</h3>
    <div id="msg-box" style="height: 400px; overflow-y: auto; border: 1px solid #dcdfe6; padding: 12px; margin-bottom: 12px; background: #fafafa; border-radius: 4px">
      <div v-for="(msg, i) in messages" :key="i" style="margin-bottom: 10px; text-align: msg.role === 'user' ? 'right' : 'left'">
        <el-tag :type="msg.role === 'user' ? '' : 'success'" size="small" style="margin-right: 6px">{{ msg.role === 'user' ? '我' : 'AI' }}</el-tag>
        <span style="background: msg.role === 'user' ? '#ecf5ff' : '#f0f9eb'; padding: 4px 10px; border-radius: 4px; display: inline-block; max-width: 70%">{{ msg.content }}</span>
        <div v-if="msg.intent" style="font-size: 11px; color: #909399; margin-top: 2px">意图：{{ msg.intent }}</div>
      </div>
      <div v-if="loading" style="color: #909399">AI 正在输入...</div>
    </div>
    <div style="display: flex; gap: 8px; margin-top: 12px">
      <el-input v-model="inputMsg" placeholder="输入消息，如：这个多少钱" @keyup.enter="send" :disabled="loading" />
      <el-button type="primary" @click="send" :loading="loading" :disabled="loading">发送</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

const inputMsg = ref('')
const messages = ref([])
const loading = ref(false)

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
    const resp = await fetch('/api/chats?message=' + encodeURIComponent(msg) + '&platform_session_id=web&user_id=admin', { method: 'POST' })
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
            if (data.token) {
              fullReply += data.token
              // 实时更新显示
              const last = messages.value[messages.value.length - 1]
              if (last && last.role === 'assistant') {
                last.content = fullReply
              } else {
                messages.value.push({ role: 'assistant', content: fullReply, intent: data.intent || '' })
              }
              scrollDown()
            }
            if (data.intent) intent = data.intent
          } catch(e) {}
        }
      }
    }
    // 最终更新
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.intent = intent
    }
  } catch(e) {
    console.error('请求失败:', e)
    messages.value.push({ role: 'assistant', content: '请求失败，请重试', intent: 'error' })
  }
  loading.value = false
  scrollDown()
}
</script>
