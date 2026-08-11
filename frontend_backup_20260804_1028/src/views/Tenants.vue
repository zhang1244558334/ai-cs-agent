<template>
  <div class="tenants-page">
    <div class="page-card">
      <div style="display: flex; justify-content: space-between; align-items: center">
        <h2 class="page-title">租户管理</h2>
      <el-button type="primary" size="small" @click="showCreate = true">新建租户</el-button>
    </div>

    <el-table :data="tenants" style="width: 100%" v-loading="loading">
      <el-table-column prop="name" label="企业名称" />
      <el-table-column prop="contact_email" label="联系邮箱" />
      <el-table-column prop="api_key" label="API Key" />
      <el-table-column label="知识共享" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.knowledge_sharing_enabled ? 'success' : 'info'" size="small">
            {{ scope.row.knowledge_sharing_enabled ? '开启' : '关闭' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="scope">
          <el-tag :type="scope.row.is_active ? 'success' : 'danger'" size="small">
            {{ scope.row.is_active ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="scope">
          <el-button size="small" @click="editTenant(scope.row)">编辑</el-button>
          <el-button v-if="scope.row.is_active" size="small" type="danger" @click="deactivate(scope.row)">停用</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showCreate" title="新建租户" width="400px">
      <el-form :model="form" label-width="120px">
        <el-form-item label="企业名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="联系邮箱">
          <el-input v-model="form.contact_email" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="form.api_key" />
        </el-form-item>
        <el-form-item label="知识共享">
          <el-switch v-model="form.knowledge_sharing_enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="createTenant">确认</el-button>
      </template>
    </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const tenants = ref([])
const loading = ref(false)
const showCreate = ref(false)
const form = ref({ name: '', contact_email: '', api_key: '', knowledge_sharing_enabled: false })

async function fetchTenants() {
  loading.value = true
  const res = await fetch('/api/admin/tenants')
  tenants.value = await res.json()
  loading.value = false
}

async function createTenant() {
  await fetch('/api/admin/tenants', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(form.value),
  })
  showCreate.value = false
  form.value = { name: '', contact_email: '', api_key: '', knowledge_sharing_enabled: false }
  await fetchTenants()
}

async function deactivate(row) {
  await fetch(`/api/admin/tenants/${row.id}`, { method: 'DELETE' })
  await fetchTenants()
}

function editTenant(row) {
  // 简化：可以打开编辑弹窗，暂时仅支持查看
  form.value = { ...row }
  showCreate.value = true
}

onMounted(fetchTenants)
</script>

<style scoped>
.tenants-page {
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
  max-width: 1000px;
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
