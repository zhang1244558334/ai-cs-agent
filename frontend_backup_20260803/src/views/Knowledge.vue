<template>
  <div style="padding: 20px; max-width: 800px; margin: 0 auto">
    <h3>知识库管理</h3>
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px">
      <el-switch v-model="isPublic" active-text="共享到公共知识库" inactive-text="仅本租户私有" />
    </div>
    <el-upload
      :action="`/api/knowledge?is_public=${isPublic}&tenant_id=single`"
      :headers="{accept: 'application/json'}"
      :show-file-list="true"
      :on-success="onUpload"
      accept=".md,.txt,.csv,.html"
    >
      <el-button type="primary">上传文档</el-button>
      <template #tip><div style="font-size: 12px; color: #909399">支持 .md .txt .csv .html</div></template>
    </el-upload>
    <el-divider />
    <h4>已上传文档</h4>
    <div v-if="docs.length === 0" style="color: #909399">暂无文档</div>
    <div v-for="doc in docs" :key="doc.name" style="display: flex; justify-content: space-between; padding: 8px 0; align-items: center">
      <span>
        {{ doc.name }}
        <el-tag v-if="doc.is_public" size="small" type="success" style="margin-left: 8px">公共</el-tag>
        <el-tag v-else size="small" type="info" style="margin-left: 8px">私有</el-tag>
      </span>
      <el-button type="danger" size="small" @click="deleteDoc(doc.name)">删除</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
const docs = ref([])
const isPublic = ref(false)

async function loadDocs() {
  const r = await fetch('/api/knowledge')
  const d = await r.json()
  docs.value = (d.documents || []).map(name => ({ name, is_public: false }))
}
function onUpload() { loadDocs() }
async function deleteDoc(src) {
  await fetch('/api/knowledge/' + encodeURIComponent(src), { method: 'DELETE' })
  loadDocs()
}
onMounted(loadDocs)
</script>
