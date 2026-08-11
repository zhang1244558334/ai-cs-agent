<template>
  <div class="review-page">
    <div class="page-header">
      <div class="page-breadcrumb">
        <i data-lucide="clipboard-check" class="breadcrumb-icon"></i>
        <span>归因审批</span>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="refresh">刷新列表</el-button>
      </div>
    </div>
    <div class="page-card">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="L2 待审批" name="l2">
        <el-empty v-if="l2List.length === 0" description="暂无待审批提案" />
        <el-card v-for="item in l2List" :key="item.id" style="margin-bottom: 12px">
          <div style="display: flex; justify-content: space-between; align-items: center">
            <div>
              <el-tag :type="typeTag(item.attribution_type)" size="small">{{ typeLabel(item.attribution_type) }}</el-tag>
              <span style="margin-left: 8px; font-weight: bold">{{ item.action }}</span>
              <span style="margin-left: 8px; color: #999; font-size: 13px">{{ item.target }}</span>
              <el-tag size="small" type="warning" style="margin-left: 8px">{{ item.level }}</el-tag>
            </div>
            <div>
              <el-button type="primary" size="small" @click="approve(item)">采纳</el-button>
              <el-button type="danger" size="small" @click="reject(item)">驳回</el-button>
              <el-button size="small" @click="defer(item)">稍后</el-button>
            </div>
          </div>
          <p style="margin: 8px 0 0; font-size: 13px; color: #666">{{ item.content }}</p>
          <p v-if="item.detail" style="margin: 4px 0 0; font-size: 12px; color: #999">{{ item.detail }}</p>
        </el-card>
      </el-tab-pane>
      <el-tab-pane label="L1 已执行" name="l1">
        <el-empty v-if="l1List.length === 0" description="暂无自动执行记录" />
        <el-card v-for="item in l1List" :key="item.id" style="margin-bottom: 12px">
          <div style="display: flex; justify-content: space-between">
            <div>
              <el-tag :type="typeTag(item.attribution_type)" size="small">{{ typeLabel(item.attribution_type) }}</el-tag>
              <span style="margin-left: 8px">{{ item.action }}</span>
              <el-tag v-if="item.status === 'verified'" size="small" type="success" style="margin-left: 8px">已自动执行·验证通过</el-tag>
              <el-tag v-else-if="item.status === 'verification_failed'" size="small" type="danger" style="margin-left: 8px">已自动执行·验证失败(已回滚)</el-tag>
              <el-tag v-else size="small" type="warning" style="margin-left: 8px">已执行·待验证</el-tag>
            </div>
          </div>
          <p style="margin: 8px 0 0; font-size: 13px; color: #666">{{ item.content }}</p>
        </el-card>
      </el-tab-pane>
      <el-tab-pane label="L3 需研判" name="l3">
        <el-empty v-if="l3List.length === 0" description="暂无待研判提案" />
        <el-card v-for="item in l3List" :key="item.id" style="margin-bottom: 12px">
          <div style="display: flex; justify-content: space-between">
            <div>
              <el-tag :type="typeTag(item.attribution_type)" size="small">{{ typeLabel(item.attribution_type) }}</el-tag>
              <span style="margin-left: 8px; color: #999">{{ item.detail }}</span>
            </div>
            <el-button size="small" @click="markDone(item)">标记已处理</el-button>
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const activeTab = ref('l2')
const l1List = ref([])
const l2List = ref([])
const l3List = ref([])

function typeLabel(t) {
  return { A: '知识库缺失', B: '路由错误', C: '话术问题', D: '正常转接' }[t] || t
}
function typeTag(t) {
  return { A: 'warning', B: 'danger', C: 'info', D: 'success' }[t] || ''
}

async function refresh() {
  const res = await fetch('/api/admin/proposals')
  const data = await res.json()
  l1List.value = data.l1 || []
  l2List.value = data.l2 || []
  l3List.value = data.l3 || []
}

async function approve(item) {
  await fetch(`/api/admin/proposals/${item.id}/approve`, { method: 'POST' })
  await refresh()
}
async function reject(item) {
  await fetch(`/api/admin/proposals/${item.id}/reject`, { method: 'POST' })
  await refresh()
}
async function defer(item) {
  await fetch(`/api/admin/proposals/${item.id}/defer`, { method: 'POST' })
  await refresh()
}
async function markDone(item) {
  await fetch(`/api/admin/proposals/${item.id}/done`, { method: 'POST' })
  await refresh()
}

onMounted(refresh)
</script>

<style scoped>
.review-page { padding: 0 24px 24px; min-height: 100vh; }

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

.page-card {
  background: var(--glass-bg); backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border); border-radius: var(--radius-md);
  box-shadow: var(--glass-shadow); padding: 24px; max-width: 900px;
}
.page-card :deep(.el-card) {
  background: rgba(255,255,255,0.35) !important; backdrop-filter: blur(12px);
  border: 1px solid var(--glass-border) !important;
  border-radius: var(--radius-sm) !important;
  box-shadow: none !important; transition: all 0.25s;
}
.page-card :deep(.el-card:hover) {
 background: var(--glass-bg-hover) !important;
  box-shadow: 0 4px 16px rgba(31,38,135,0.08) !important;
}
.page-card :deep(.el-card .el-button + .el-button) { margin-left: 12px; }
</style>
