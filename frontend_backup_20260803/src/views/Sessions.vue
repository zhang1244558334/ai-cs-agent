<template>
  <div style="padding: 20px; max-width: 800px; margin: 0 auto">
    <h3>会话历史</h3>
    <div v-if="sessions.length === 0" style="color: #909399">暂无会话记录</div>
    <el-card v-for="s in sessions" :key="s.id" style="margin-bottom: 8px">
      <div style="display: flex; justify-content: space-between">
        <span><strong>{{ s.user_id }}</strong> @ {{ s.platform }}</span>
        <el-tag :type="s.mode === 'ai' ? 'success' : 'warning'" size="small">{{ s.mode }}</el-tag>
      </div>
      <div style="font-size: 12px; color: #909399; margin-top: 4px">
        {{ s.created_at }} | 意图: {{ s.last_intent || '-' }} | 议价: {{ s.bargain_count }} 次
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
const sessions = ref([])
async function load() {
  const r = await fetch('/api/sessions')
  try {
    const d = await r.json()
    sessions.value = Array.isArray(d) ? d : []
  } catch(e) { sessions.value = [] }
}
onMounted(load)
</script>
