<template>
  <div style="padding: 20px; max-width: 800px; margin: 0 auto">
    <h3>客服对话</h3>
    <div id="msg-box" style="height: 400px; overflow-y: auto; border: 1px solid #dcdfe6; padding: 12px; margin-bottom: 12px; background: #fafafa">
      <div v-for="(msg, i) in messages" :key="i" style="margin-bottom: 8px">
        <el-tag :type="msg.role === 'user' ? 'primary' : 'success'" size="small">{{ msg.role === 'user' ? '我' : 'AI' }}</el-tag>
        <span style="margin-left: 8px">{{ msg.content }}</span>
        <div v-if="msg.intent" style="font-size: 12px; color: #909399; margin-top: 2px">意图: {{ msg.intent }}</div>
      </div>
    </div>
    <div style="display: flex; gap: 8px">
      <el-input v-model="inputMsg" placeholder="输入消息，如：这个多少钱" @keyup.enter="send" />
      <el-button type="primary" @click="send" :loading="loading">发送</el-button>
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
  if (!inputMsg.value) return
  loading.value = true
  const msg = inputMsg.value
  messages.value.push({ role: 'user', content: msg })
  inputMsg.value = ''
  scrollDown()
  try {
    const resp = await fetch('/api/chats?message=' + encodeURIComponent(msg) + '&platform_session_id=web&user_id=admin')
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let fullReply = ''
    let intent = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const text = decoder.decode(value)
      for (const line of text.split('\n')) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.token) fullReply += data.token
            if (data.intent) intent = data.intent
            if (data.done) {
              messages.value.push({ role: 'assistant', content: fullReply, intent })
              fullReply = ''
              scrollDown()
            }
          } catch(e) {}
        }
      }
    }
  } catch(e) { console.error(e) }
  loading.value = false
}
</script>
