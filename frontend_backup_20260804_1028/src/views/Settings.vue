<template>
  <div class="dashboard-page">
    <div class="settings-card">
      <h2 class="page-title">设置中心</h2>

      <el-form label-width="100px" class="settings-form">
        <el-form-item label="API Key">
          <el-input v-model="apiKey" type="password" show-password placeholder="sk-xxxx" />
        </el-form-item>
        <el-form-item label="模型">
          <el-input v-model="model" placeholder="deepseek-chat" />
        </el-form-item>
        <el-form-item label="API 地址">
          <el-input v-model="baseUrl" placeholder="https://api.deepseek.com/v1" />
        </el-form-item>
        <el-form-item label="最大让步">
          <el-input-number v-model="maxDiscount" :min="0" :max="0.5" :step="0.05" />
        </el-form-item>
        <el-form-item label="议价轮次">
          <el-input-number v-model="maxRounds" :min="1" :max="10" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="save" :loading="saving">保存设置</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const apiKey = ref(localStorage.getItem('apiKey') || '')
const model = ref(localStorage.getItem('model') || 'deepseek-chat')
const baseUrl = ref(localStorage.getItem('baseUrl') || 'https://api.deepseek.com/v1')
const maxDiscount = ref(parseFloat(localStorage.getItem('maxDiscount') || '0.1'))
const maxRounds = ref(parseInt(localStorage.getItem('maxRounds') || '5'))
const saving = ref(false)

async function save() {
  saving.value = true
  try {
    const body = {
      model: model.value,
      base_url: baseUrl.value,
      api_key: apiKey.value,
      max_discount: maxDiscount.value,
      max_rounds: maxRounds.value,
    }
    const r = await fetch('/api/admin/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (r.ok) {
      localStorage.setItem('apiKey', apiKey.value)
      localStorage.setItem('model', model.value)
      localStorage.setItem('baseUrl', baseUrl.value)
      localStorage.setItem('maxDiscount', maxDiscount.value)
      localStorage.setItem('maxRounds', maxRounds.value)
      ElMessage.success('保存成功')
    } else {
      const err = await r.json().catch(() => ({}))
      ElMessage.error(err.detail || '保存失败')
    }
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.message || '网络错误'))
  }
  saving.value = false
}
</script>

<style scoped>
.dashboard-page {
  padding: 24px;
  min-height: 100vh;
  background: #f0f2f5;
}
.settings-card {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
  max-width: 640px;
}
.page-title {
  margin: 0 0 24px;
  font-size: 20px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.85);
}
.settings-form {
  max-width: 480px;
}
</style>
