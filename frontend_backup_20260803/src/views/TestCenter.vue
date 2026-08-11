<template>
  <div style="padding: 20px; max-width: 1000px; margin: 0 auto">
    <h2>🧪 全功能测试中心</h2>
    <p style="color: #909399; margin-bottom: 20px">按层分组，点按钮测功能，结果实时显示</p>

    <el-collapse v-model="activeLayers">
      <!-- ========== 第一二层 ========== -->
      <el-collapse-item title="📦 第一·二层：对话 + 路由 + Agent + RAG" name="l2">
        <div style="display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 12px">
          <el-input v-model="testMsg" placeholder="输入测试消息" style="width: 300px" />
          <el-button type="primary" @click="sendChat">发送消息</el-button>
          <el-button @click="sendChatShort">发送短指代（那个呢）</el-button>
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px">
          <el-button @click="listSessions">会话列表</el-button>
          <el-button @click="searchKnowledge">知识库搜索</el-button>
        </div>
        <el-input v-model="searchQuery" placeholder="搜索关键词" style="width: 300px; margin-right: 8px" />
        <pre v-if="resultL2" class="result-box">{{ resultL2 }}</pre>
      </el-collapse-item>

      <!-- ========== 第三层 ========== -->
      <el-collapse-item title="🔄 第三层：自我优化闭环" name="l3">
        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px">
          <el-button type="warning" @click="runAttribution">▶ 运行归因分析</el-button>
          <el-button @click="listProposals">查看提案列表</el-button>
        </div>
        <div v-if="proposals.l1.length > 0 || proposals.l2.length > 0 || proposals.l3.length > 0">
          <el-table :data="allProposals" size="small" max-height="300">
            <el-table-column prop="level" label="级别" width="60" />
            <el-table-column prop="action" label="操作" width="120" />
            <el-table-column prop="target" label="目标" width="160" />
            <el-table-column prop="content" label="内容" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="100" />
            <el-table-column label="操作" width="180">
              <template #default="scope">
                <el-button v-if="scope.row.status === 'pending'" size="small" type="primary" @click="approveProposal(scope.row.id)">采纳</el-button>
                <el-button v-if="scope.row.status === 'pending'" size="small" type="danger" @click="rejectProposal(scope.row.id)">驳回</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <pre v-if="resultL3" class="result-box">{{ resultL3 }}</pre>
      </el-collapse-item>

      <!-- ========== 第四层 ========== -->
      <el-collapse-item title="📢 第四层：主动式服务" name="l4">
        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px">
          <el-button type="success" @click="seedEvents">🌱 灌模拟事件</el-button>
          <el-button @click="listProactiveLogs">查看推送日志</el-button>
        </div>
        <pre v-if="resultL4" class="result-box">{{ resultL4 }}</pre>
      </el-collapse-item>

      <!-- ========== 第五层 ========== -->
      <el-collapse-item title="🏢 第五层：多企业协同" name="l5">
        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px">
          <el-button type="primary" @click="createTenant">➕ 创建测试租户</el-button>
          <el-button @click="listTenants">租户列表</el-button>
        </div>
        <div v-if="tenants.length > 0">
          <el-table :data="tenants" size="small" max-height="200">
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="contact_email" label="邮箱" />
            <el-table-column prop="is_active" label="状态">
              <template #default="s">{{ s.row.is_active ? '✅' : '❌' }}</template>
            </el-table-column>
            <el-table-column label="操作">
              <template #default="s">
                <el-button v-if="s.row.is_active" size="small" type="danger" @click="deactivateTenant(s.row.id)">停用</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <pre v-if="resultL5" class="result-box">{{ resultL5 }}</pre>
      </el-collapse-item>

      <!-- ========== 第六层 ========== -->
      <el-collapse-item title="🤖 第六层：自主进化（可实施）" name="l6">
        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px">
          <el-button @click="runAutoExecute">⚡ 自动执行 L1</el-button>
          <el-button @click="runWeeklyReport">📊 生成归因周报</el-button>
        </div>
        <pre v-if="resultL6" class="result-box">{{ resultL6 }}</pre>
      </el-collapse-item>
    </el-collapse>

    <el-divider />
    <div style="display: flex; gap: 8px">
      <el-button type="info" @click="clearAll">清空所有结果</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const activeLayers = ref(['l2', 'l3', 'l4', 'l5', 'l6'])
const testMsg = ref('这个多少钱')
const searchQuery = ref('价格')
const resultL2 = ref('')
const resultL3 = ref('')
const resultL4 = ref('')
const resultL5 = ref('')
const resultL6 = ref('')
const proposals = ref({ l1: [], l2: [], l3: [] })
const tenants = ref([])

const allProposals = computed(() => [
  ...proposals.value.l1.map(p => ({ ...p, level: 'L1' })),
  ...proposals.value.l2.map(p => ({ ...p, level: 'L2' })),
  ...proposals.value.l3.map(p => ({ ...p, level: 'L3' })),
])

async function api(url, opts = {}) {
  try {
    const r = await fetch(url, opts)
    return await r.json()
  } catch (e) {
    return { error: e.message }
  }
}

async function sendChat() {
  const r = await fetch(`/api/chats?message=${encodeURIComponent(testMsg.value)}&platform_session_id=test&user_id=demo`, { method: 'POST' })
  const reader = r.body.getReader()
  const decoder = new TextDecoder()
  let full = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    full += decoder.decode(value, { stream: true })
  }
  resultL2.value = full.substring(0, 500)
}
async function sendChatShort() {
  testMsg.value = '那个呢'
  const r = await fetch(`/api/chats?message=${encodeURIComponent('那个呢')}&platform_session_id=test&user_id=demo`, { method: 'POST' })
  const reader = r.body.getReader()
  let full = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    full += new TextDecoder().decode(value)
  }
  resultL2.value = full.substring(0, 500)
}
async function listSessions() {
  resultL2.value = JSON.stringify(await api('/api/sessions'), null, 2)
}
async function searchKnowledge() {
  resultL2.value = JSON.stringify(await api(`/api/knowledge/search?query=${encodeURIComponent(searchQuery.value)}&top_k=3`, { method: 'POST' }), null, 2)
}
async function runAttribution() {
  resultL3.value = JSON.stringify(await api('/api/admin/attribution/run', { method: 'POST' }), null, 2)
}
async function listProposals() {
  const data = await api('/api/admin/proposals')
  proposals.value = data
  resultL3.value = `L1: ${data.l1.length} | L2: ${data.l2.length} | L3: ${data.l3.length}`
}
async function approveProposal(id) {
  await api(`/api/admin/proposals/${id}/approve`, { method: 'POST' })
  await listProposals()
}
async function rejectProposal(id) {
  await api(`/api/admin/proposals/${id}/reject`, { method: 'POST' })
  await listProposals()
}
async function seedEvents() {
  resultL4.value = JSON.stringify(await api('/api/admin/seed-events', { method: 'POST' }), null, 2)
}
async function listProactiveLogs() {
  resultL4.value = JSON.stringify(await api('/api/sessions?limit=5'), null, 2)
}
async function createTenant() {
  const n = '测试企业_' + Date.now().toString(36)
  resultL5.value = JSON.stringify(await api('/api/admin/tenants', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: n, contact_email: 'test@test.com', api_key: 'key_' + n, knowledge_sharing_enabled: true }),
  }), null, 2)
  await listTenants()
}
async function listTenants() {
  const data = await api('/api/admin/tenants')
  tenants.value = data
  resultL5.value = `共 ${data.length} 个租户`
}
async function deactivateTenant(id) {
  resultL5.value = JSON.stringify(await api(`/api/admin/tenants/${id}`, { method: 'DELETE' }), null, 2)
  await listTenants()
}
async function runAutoExecute() {
  resultL6.value = JSON.stringify(await api('/api/admin/auto-execute', { method: 'POST' }), null, 2)
}
async function runWeeklyReport() {
  resultL6.value = JSON.stringify(await api('/api/admin/weekly-report', { method: 'POST' }), null, 2)
}
function clearAll() {
  resultL2.value = resultL3.value = resultL4.value = resultL5.value = resultL6.value = ''
  proposals.value = { l1: [], l2: [], l3: [] }
  tenants.value = []
}
</script>

<style scoped>
.result-box {
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 12px;
  font-size: 12px;
  max-height: 300px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin-top: 12px;
}
</style>
