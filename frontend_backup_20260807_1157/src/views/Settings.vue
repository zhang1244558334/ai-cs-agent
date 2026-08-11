<template>
  <div class="settings-page">
    <div class="page-header">
      <div class="page-breadcrumb">
        <i data-lucide="settings" class="breadcrumb-icon"></i>
        <span>设置中心</span>
      </div>
    </div>
    <div class="settings-card">

      <el-form label-width="100px" class="settings-form">
        <el-form-item label="API Key">
          <el-input v-model="apiKey" type="password" show-password placeholder="sk-xxxx" autocomplete="off" />
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
        <!-- 平台接入 -->
        <el-divider content-position="left">平台接入</el-divider>
        <el-form-item label="接入平台">
          <el-select v-model="platformProvider" placeholder="选择电商平台" @change="onPlatformChange" style="width:240px">
            <el-option v-for="p in platforms" :key="p.key" :label="p.name" :value="p.key">
              <span style="display:flex;align-items:center;gap:8px">
                <i :data-lucide="p.icon" style="width:14px;height:14px"></i>
                {{ p.name }}
              </span>
            </el-option>
          </el-select>
          <span v-if="currentPlatform" style="margin-left:12px;font-size:12px;color:#999">{{ currentPlatform.description }}</span>
        </el-form-item>
        <el-form-item v-for="field in currentPlatformFields" :key="field.key" :label="field.label">
          <el-input v-model="platformConfig[field.key]" :type="field.type === 'password' ? 'password' : 'text'" show-password :placeholder="'输入' + field.label" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="save" :loading="saving">保存设置</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const apiKey = ref('')
const model = ref('deepseek-chat')
const baseUrl = ref('https://api.deepseek.com/v1')
const maxDiscount = ref(0.1)
const maxRounds = ref(5)
const saving = ref(false)
const platformProvider = ref(localStorage.getItem('platformProvider') || 'mock')
const platformConfig = ref({})
const platforms = ref([])
const currentPlatform = computed(() => platforms.value.find(p => p.key === platformProvider.value) || null)
const currentPlatformFields = computed(() => currentPlatform.value?.fields || [])

async function loadPlatforms() {
  try {
    const r = await fetch('/api/admin/platforms')
    if (r.ok) {
      const d = await r.json()
      platforms.value = d.platforms || []
    }
  } catch(e) {}
}

function onPlatformChange(key) {
  localStorage.setItem('platformProvider', key)
  const saved = localStorage.getItem('platformConfig_' + key)
  platformConfig.value = saved ? JSON.parse(saved) : {}
}

onMounted(() => {
  // 一次性清除旧的localStorage脏数据
  ['apiKey','model','baseUrl','maxDiscount','maxRounds'].forEach(k => localStorage.removeItem(k))
  loadPlatforms()
  onPlatformChange(platformProvider.value)
})

async function save() {
  saving.value = true
  try {
    const body = {
      model: model.value,
      base_url: baseUrl.value,
      api_key: apiKey.value,
      max_discount: maxDiscount.value,
      max_rounds: maxRounds.value,
      platform_provider: platformProvider.value,
      platform_config: JSON.stringify(platformConfig.value),
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
      localStorage.setItem('platformProvider', platformProvider.value)
      localStorage.setItem('platformConfig_' + platformProvider.value, JSON.stringify(platformConfig.value))
      // 通知后端切换平台
      await fetch('/api/admin/platforms/activate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: platformProvider.value }),
      })
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
.settings-page {
  padding: 0 24px 24px;
  min-height: 100vh;
  background: #f0f2f5;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding: 20px 24px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
}
.page-breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.85);
}
.breadcrumb-icon {
  display: inline-flex;
  align-items: center;
  color: #1890ff;
}
.settings-card {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  max-width: 640px;
}
.settings-form {
  max-width: 480px;
}
</style>
