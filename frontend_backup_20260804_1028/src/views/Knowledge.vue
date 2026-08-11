<template>
  <div class="knowledge-page">
    <div class="page-card">
      <h2 class="page-title">知识库管理</h2>
    <p style="font-size: 13px; color: #909399; margin-bottom: 16px">
      上传文档后自动分块→embedding→入库，30秒内客服即可回答相关问题
    </p>
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px">
      <el-switch v-model="isPublic" active-text="共享到公共知识库" inactive-text="仅本租户私有" />
    </div>
    <el-upload
      :action="`/api/knowledge?is_public=${isPublic}&tenant_id=single`"
      :headers="{accept: 'application/json'}"
      :show-file-list="true"
      :on-success="onUpload"
      accept=".md,.txt,.csv,.html,.pdf"
    >
      <el-button type="primary">上传知识文件</el-button>
      <template #tip><div style="font-size: 12px; color: #909399">支持 .md .txt .csv .html .pdf</div></template>
    </el-upload>

     <!-- 上传结果预览 -->
    <div v-if="uploadResult" class="upload-result-box" style="margin-top: 12px; background: #f6ffed; border: 1px solid #b7eb8f; border-radius: 8px; padding: 12px 16px">
      <div style="font-weight: 600; color: #52c41a; margin-bottom: 6px">
        ✅ {{ uploadResult.message }}（共 {{ uploadResult.chunks }} 个分块）
      </div>
      <div v-if="uploadResult.previews?.length" style="margin-top: 8px">
        <div style="font-size: 12px; color: #999; margin-bottom: 4px">分块预览：</div>
        <div v-for="p in uploadResult.previews" :key="p.index" style="font-size: 12px; color: #555; padding: 4px 8px; margin-bottom: 4px; background: #fff; border-radius: 4px; border: 1px solid #e8e8e8">
          <el-tag size="small" type="success" style="margin-right: 6px">#{{ p.index + 1 }}</el-tag>
          {{ p.preview }}...
        </div>
      </div>
    </div>

    <el-divider />
    <h4>已上传文档（{{ docs.length }}）</h4>
    <div v-if="docs.length === 0" style="color: #909399">暂无文档</div>
    <div v-for="doc in docs" :key="doc.name" style="display: flex; justify-content: space-between; padding: 8px 0; align-items: center">
      <span>
        {{ doc.name }}
        <el-tag v-if="doc.name.endsWith('.pdf')" size="small" type="warning" style="margin-left: 4px">PDF</el-tag>
        <el-tag v-if="doc.is_public" size="small" type="success" style="margin-left: 8px">公共</el-tag>
        <el-tag v-else size="small" type="info" style="margin-left: 8px">私有</el-tag>
      </span>
      <el-button type="danger" size="small" @click="deleteDoc(doc.name)">删除</el-button>
    </div>
  </div>
</div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
const docs = ref([])
const isPublic = ref(false)
const uploadResult = ref(null)

async function loadDocs() {
  const r = await fetch('/api/knowledge')
  const d = await r.json()
  docs.value = (d.documents || []).map(name => ({ name, is_public: false }))
}
function onUpload(resp) {
  uploadResult.value = resp
  loadDocs()
}
async function deleteDoc(src) {
  try {
    await ElMessageBox.confirm(`确定删除「${src}」？删除后客服将无法回答相关问题。`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await fetch('/api/knowledge/' + encodeURIComponent(src), { method: 'DELETE' })
    ElMessage.success('已删除')
    loadDocs()
  } catch (e) {
    // 取消
  }
}
onMounted(loadDocs)
</script>

<style scoped>
.knowledge-page {
  display: flex;
  justify-content: center;
  min-height: 100vh;
  background: #f0f2f5;
}
.page-card {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  max-width: 860px;
  width: 100%;
  margin: 24px;
  align-self: flex-start;
}
.page-title {
  margin: 0 0 16px;
  font-size: 20px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.85);
  border-left: 3px solid #1890ff;
  padding-left: 12px;
}
</style>
