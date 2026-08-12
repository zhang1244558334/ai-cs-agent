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
          <span v-if="apiKeyMasked && !apiKey" style="margin-left:8px;font-size:12px;color:#999">已保存: {{ apiKeyMasked }}</span>
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
          <div style="display:flex;align-items:center;gap:8px">
            <el-input v-model="platformConfig[field.key]" :type="field.type === 'password' ? 'password' : 'text'" show-password :placeholder="'输入' + field.label" style="flex:1" />
            <el-button v-if="platformProvider === 'xianyu' && field.key === 'app_key'" size="small" disabled title="扫码登录暂不可用（闲鱼风控升级，请手动粘贴Cookie）">
              <i data-lucide="smartphone" style="width:14px;height:14px;vertical-align:middle;margin-right:4px"></i>扫码登录(暂停)
            </el-button>
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="save" :loading="saving">保存设置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 扫码登录弹窗 -->
    <el-dialog v-model="qrVisible" title="闲鱼扫码登录" width="380px" :close-on-click-modal="false" @closed="cancelQrLogin">
      <div style="text-align:center">
        <p style="font-size:13px;color:var(--text-secondary);margin-bottom:16px">
          打开<strong>闲鱼App</strong>，点击左上角扫一扫
        </p>
        <div v-if="qrStatus === 'error' || qrStatus === 'expired'" style="padding:40px 0;color:var(--text-muted)">
          <p>{{ qrError || '二维码已过期' }}</p>
          <el-button type="primary" size="small" @click="startQrLogin" :loading="qrLoading" style="margin-top:12px">重新生成</el-button>
        </div>
        <template v-else>
          <div v-if="qrStatus === 'generating'" style="padding:40px 0;color:var(--accent)">
            <i data-lucide="loader-2" style="width:14px;height:14px;vertical-align:middle;animation:spin 1s linear infinite"></i>
            生成二维码中...
          </div>
          <img v-else-if="qrDataUrl" :src="qrDataUrl" style="width:260px;height:260px;border-radius:12px;border:1px solid var(--glass-border)" />
          <div v-if="qrStatus === 'waiting'" style="margin-top:16px;color:var(--accent)">
            <i data-lucide="loader-2" style="width:14px;height:14px;vertical-align:middle;animation:spin 1s linear infinite"></i>
            等待扫码...
          </div>
          <div v-else-if="qrStatus === 'scanned'" style="margin-top:16px;color:#f59e0b">
            已扫码，请在手机上确认登录
          </div>
          <div v-else-if="qrStatus === 'done'" style="margin-top:16px;color:#10b981">
            登录成功！
          </div>
        </template>
      </div>
      <template #footer>
        <el-button @click="cancelQrLogin">取消</el-button>
        <el-button v-if="qrStatus === 'done'" type="primary" @click="applyQrLogin">应用Cookie</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const apiKey = ref('')
const apiKeyMasked = ref('')
const model = ref('deepseek-chat')
const baseUrl = ref('https://api.deepseek.com/v1')
const maxDiscount = ref(0.1)
const maxRounds = ref(5)
const saving = ref(false)
const platformProvider = ref('mock')
const platformConfig = ref({})
const platforms = ref([])
const currentPlatform = computed(() => platforms.value.find(p => p.key === platformProvider.value) || null)
const currentPlatformFields = computed(() => currentPlatform.value?.fields || [])

// 扫码登录
const qrVisible = ref(false)
const qrDataUrl = ref('')
const qrStatus = ref('')
const qrError = ref('')
const qrLoading = ref(false)
let qrTimer = null

async function startQrLogin() {
  qrLoading.value = true
  cancelQrLogin()
  try {
    const r = await fetch('/api/admin/platforms/qrcode/start', { method: 'POST' })
    const d = await r.json()
    if (d.status === 'generating') {
      qrStatus.value = 'generating'
      qrError.value = ''
      qrVisible.value = true
      pollQrStatus()  // 轮询直到二维码出来
    } else if (d.status === 'waiting') {
      qrDataUrl.value = d.qr_data_url
      qrStatus.value = 'waiting'
      qrError.value = ''
      qrVisible.value = true
      pollQrStatus()
    } else {
      ElMessage.warning(d.message || '启动扫码失败')
    }
  } catch (e) {
    ElMessage.error('启动扫码失败')
  }
  qrLoading.value = false
}

function pollQrStatus() {
  if (qrTimer) clearInterval(qrTimer)
  qrTimer = setInterval(async () => {
    try {
      const r = await fetch('/api/admin/platforms/qrcode/status')
      const d = await r.json()
      if (d.status === 'waiting' && d.qr_data_url && !qrDataUrl.value) {
        // 轮询拿到了SDK生成的二维码
        qrDataUrl.value = d.qr_data_url
      }
      qrStatus.value = d.status
      if (d.error) qrError.value = d.error
      if (d.status === 'done' || d.status === 'error' || d.status === 'expired') {
        clearInterval(qrTimer)
        qrTimer = null
      }
    } catch (e) {}
  }, 1500)
}

async function applyQrLogin() {
  try {
    const r = await fetch('/api/admin/platforms/qrcode/apply', { method: 'POST' })
    const d = await r.json()
    if (d.status === 'ok') {
      ElMessage.success('闲鱼登录成功，Cookie已保存')
      qrVisible.value = false
      // 重新加载设置
      loadSettings()
    } else {
      ElMessage.error(d.message || '保存失败')
    }
  } catch (e) {
    ElMessage.error('保存Cookie失败')
  }
}

function cancelQrLogin() {
  if (qrTimer) { clearInterval(qrTimer); qrTimer = null }
  qrVisible.value = false
  qrStatus.value = ''
  fetch('/api/admin/platforms/qrcode/cancel', { method: 'POST' }).catch(() => {})
}

async function loadPlatforms() {
  try {
    const r = await fetch('/api/admin/platforms')
    if (r.ok) {
      const d = await r.json()
      platforms.value = d.platforms || []
    }
  } catch(e) {}
}

async function loadSettings() {
  try {
    const r = await fetch('/api/admin/settings')
    if (r.ok) {
      const d = await r.json()
      model.value = d.model || model.value
      baseUrl.value = d.base_url || baseUrl.value
      maxDiscount.value = d.max_discount ?? maxDiscount.value
      maxRounds.value = d.max_rounds ?? maxRounds.value
      platformProvider.value = d.platform_provider || 'mock'
      apiKeyMasked.value = d.api_key_masked || ''
      // 平台配置
      try {
        const cfg = d.platform_config
        if (cfg && typeof cfg === 'string') {
          platformConfig.value = JSON.parse(cfg)
        } else if (cfg && typeof cfg === 'object') {
          platformConfig.value = cfg
        }
      } catch (e) { platformConfig.value = {} }
    }
  } catch(e) {}
}

function onPlatformChange(key) {
  // 切换平台时不清除已有key——用户可能只是想切换平台不重输key
}

onMounted(async () => {
  await Promise.all([loadSettings(), loadPlatforms()])
})

async function save() {
  saving.value = true
  try {
    const body = {
      model: model.value,
      base_url: baseUrl.value,
      api_key: apiKey.value || undefined,  // 没填就不更新（保留旧值）
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
      // 通知后端切换平台
      await fetch('/api/admin/platforms/activate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: platformProvider.value }),
      })
      apiKeyMasked.value = apiKey.value ? (apiKey.value.length > 8 ? apiKey.value.slice(0,4) + '****' + apiKey.value.slice(-4) : '****') : apiKeyMasked.value
      apiKey.value = ''  // 清除输入框（安全）
      ElMessage.success('保存成功，立即生效')
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
.settings-page { padding: 0 24px 24px; min-height: 100vh; }

.page-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 20px; padding: 16px 24px;
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  box-shadow: var(--glass-shadow);
}
.page-breadcrumb {
  display: flex; align-items: center; gap: 10px;
  font-size: 18px; font-weight: 700; color: var(--text-primary);
}
.breadcrumb-icon { display: inline-flex; align-items: center; color: var(--accent); }
.header-actions { display: flex; gap: 8px; }
.btn-icon { display: inline-flex; vertical-align: middle; margin-right: 2px; }

.settings-card {
  background: var(--glass-bg); backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border); border-radius: var(--radius-md);
  box-shadow: var(--glass-shadow); padding: 28px; max-width: 640px;
}
.settings-form { max-width: 480px; }
</style>
