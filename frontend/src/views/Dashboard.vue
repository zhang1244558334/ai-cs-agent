<template>
  <div class="dashboard-page">
    <div class="page-header glass-card">
      <div class="page-breadcrumb">
        <i data-lucide="layout-dashboard" class="breadcrumb-icon"></i>
        <span>仪表盘</span>
      </div>
      <div class="header-actions">
        <el-button type="primary" size="small" @click="runAttribution" :loading="attributionLoading" round>
          <i data-lucide="play" class="btn-icon"></i> 运行归因
        </el-button>
        <el-button type="primary" size="small" @click="runAutoExecute" :loading="executeLoading" round>
          <i data-lucide="zap" class="btn-icon"></i> 执行提案
        </el-button>
        <el-button type="primary" size="small" @click="runWeeklyReport" :loading="reportLoading" round>
          <i data-lucide="bar-chart-3" class="btn-icon"></i> 生成周报
        </el-button>
      </div>
    </div>

    <div class="stat-row">
      <div class="stat-card glass-card">
        <div class="stat-icon-wrap health">
          <i data-lucide="heart-pulse"></i>
        </div>
        <div class="stat-body">
          <div class="stat-value">
            <span class="health-dot" :class="dashboard.health === 'ok' ? 'green' : 'red'"></span>
            {{ dashboard.health === 'ok' ? '正常' : '异常' }}
          </div>
          <div class="stat-label">系统健康</div>
        </div>
      </div>
      <div class="stat-card glass-card">
        <div class="stat-icon-wrap primary">
          <i data-lucide="message-square"></i>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ dashboard.today ?? 0 }}</div>
          <div class="stat-label">今日消息</div>
        </div>
      </div>
      <div class="stat-card glass-card">
        <div class="stat-icon-wrap warning">
          <i data-lucide="shield-alert"></i>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ dashboard.flagged ?? 0 }}</div>
          <div class="stat-label">质检标记</div>
        </div>
      </div>
      <div class="stat-card glass-card">
        <div class="stat-icon-wrap danger">
          <i data-lucide="clipboard-list"></i>
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ dashboard.proposals ?? 0 }}</div>
          <div class="stat-label">待处理提案</div>
        </div>
      </div>
    </div>

    <div class="bento-row">
      <div class="bento-main">
        <div class="chart-card glass-card large">
          <h3 class="chart-title">24小时会话量趋势</h3>
          <div ref="lineChart" class="chart-box"></div>
        </div>
      </div>
      <div class="bento-side">
        <div class="chart-card glass-card">
          <h3 class="chart-title">意图分布（24h）</h3>
          <div ref="pieChart" class="chart-box small-chart"></div>
        </div>
        <div class="mini-list-card glass-card">
          <h3 class="mini-list-title">最近对话</h3>
          <div v-if="dashboard.recent_chats?.length">
            <div v-for="chat in dashboard.recent_chats.slice(0,5)" :key="chat.id" class="mini-row">
              <el-tag size="small" :type="intentTagType(chat.intent)" effect="dark" round>{{ chat.intent || '-' }}</el-tag>
              <span class="mini-content">{{ chat.content }}</span>
            </div>
          </div>
          <div v-else class="empty-row">暂无对话记录</div>
        </div>
      </div>
    </div>

    <div class="list-card glass-card">
      <h3 class="list-title">最近提案</h3>
      <div class="table-header">
        <span class="col-type">类型</span>
        <span class="col-desc">操作描述</span>
        <span class="col-level">级别</span>
        <span class="col-status">状态</span>
      </div>
      <div v-if="dashboard.recent_proposals?.length">
        <div v-for="p in dashboard.recent_proposals" :key="p.id" class="table-row">
          <span class="col-type">
            <el-tag size="small" :type="attrTag(p.attribution_type)" effect="dark" round>{{ attrLabel(p.attribution_type) }}</el-tag>
          </span>
          <span class="col-desc" :title="p.content">{{ p.action || '' }} {{ p.content || '' }}</span>
          <span class="col-level">
            <el-tag size="small" :type="levelTag(p.level)" effect="dark" round>{{ p.level }}</el-tag>
          </span>
          <span class="col-status">{{ statusText(p.status) }}</span>
        </div>
      </div>
      <div v-else class="empty-row">暂无提案</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onActivated, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'

const dashboard = ref({})
const pieChart = ref(null)
const lineChart = ref(null)
let pieInstance = null
let lineInstance = null

const attributionLoading = ref(false)
const executeLoading = ref(false)
const reportLoading = ref(false)

let timer = null

function refreshIcons() {
  nextTick(() => {
    if (window.lucide) {
      window.lucide.createIcons({ attrs: { width: '16', height: '16' } })
    }
  })
}

async function load() {
  try {
    const r = await fetch(`/api/admin/dashboard?tenant_id=${localStorage.getItem('activeBusiness') || 'ecommerce'}`)
    if (r.ok) {
      dashboard.value = await r.json()
      refreshIcons()
      renderCharts()
    }
  } catch (e) {}
}

function renderCharts() {
  const d = dashboard.value
  if (!d.intent_stats || !d.hourly_stats) return
  
  nextTick(() => {
    if (pieChart.value) {
      if (!pieInstance) pieInstance = echarts.init(pieChart.value)
      pieInstance.setOption({
        tooltip: { trigger: 'item', backgroundColor: 'rgba(255,255,255,0.9)', borderColor: 'rgba(0,0,0,0.06)', textStyle: { color: '#1e293b' } },
        legend: { bottom: 0, textStyle: { fontSize: 11, color: 'var(--text-secondary)' } },
        series: [{
          type: 'pie',
          radius: ['40%', '70%'],
          center: ['50%', '45%'],
          label: { fontSize: 11, color: 'var(--text-primary)' },
          itemStyle: { borderRadius: 6, borderColor: 'rgba(255,255,255,0.3)', borderWidth: 2 },
          data: d.intent_stats.map(i => ({ name: intentCN(i.name), value: i.value }))
        }]
      })
    }
    if (lineChart.value) {
      if (!lineInstance) lineInstance = echarts.init(lineChart.value)
      lineInstance.setOption({
        tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.9)', borderColor: 'rgba(0,0,0,0.06)', textStyle: { color: '#1e293b' } },
        grid: { left: 40, right: 16, top: 10, bottom: 24 },
        xAxis: {
          type: 'category',
          data: d.hourly_stats.map(i => i.hour),
          axisLabel: { fontSize: 10, rotate: 45, color: 'var(--text-muted)' },
          axisLine: { lineStyle: { color: 'rgba(0,0,0,0.06)' } },
        },
        yAxis: {
          type: 'value', minInterval: 1,
          axisLabel: { fontSize: 10, color: 'var(--text-muted)' },
          splitLine: { lineStyle: { color: 'rgba(0,0,0,0.04)', type: 'dashed' } },
        },
        series: [{
          type: 'line',
          data: d.hourly_stats.map(i => i.count),
          smooth: true,
          lineStyle: { color: 'var(--accent)', width: 2.5 },
          areaStyle: {
            color: {
              type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(99, 102, 241, 0.2)' },
                { offset: 1, color: 'rgba(99, 102, 241, 0)' }
              ]
            }
          },
          itemStyle: { color: 'var(--accent)' },
          symbolSize: 4,
        }]
      })
    }
  })
}

async function runAttribution() {
  attributionLoading.value = true
  try {
    const r = await fetch('/api/admin/attribution/run', { method: 'POST' })
    const d = await r.json()
    ElMessage.success(`归因完成: flagged=${d.flagged || 0} handover=${d.handover || 0}`)
    load()
  } catch (e) { ElMessage.error('归因分析失败') }
  attributionLoading.value = false
}

async function runAutoExecute() {
  executeLoading.value = true
  try {
    const r = await fetch('/api/admin/auto-execute', { method: 'POST' })
    ElMessage.success('L1 提案已执行')
    load()
  } catch (e) { ElMessage.error('执行失败') }
  executeLoading.value = false
}

async function runWeeklyReport() {
  reportLoading.value = true
  try {
    const r = await fetch('/api/admin/weekly-report', { method: 'POST' })
    ElMessage.success('周报已生成')
  } catch (e) { ElMessage.error('周报生成失败') }
  reportLoading.value = false
}

function intentTagType(intent) {
  if (['handover', 'no_reply'].includes(intent)) return 'warning'
  if (['complaint', 'complain'].includes(intent)) return 'danger'
  if (['after_sale', 'price'].includes(intent)) return 'success'
  return 'info'
}
function intentCN(intent) {
  const map = { price: '议价', logistics: '物流', after_sale: '售后', tech: '产品', default: '通用', handover: '转人工', complaint: '投诉', complain: '投诉', no_reply: '无回复', error: '错误', fee: '缴费', repair: '报修', notice: '公告' }
  return map[intent] || intent
}
function attrLabel(t) { return { A: '知识缺失', B: '路由错误', C: '话术问题', D: '正常转接' }[t] || t }
function attrTag(t) { return { A: 'warning', B: 'danger', C: '', D: 'success' }[t] || 'info' }
function levelTag(level) { return { L1: 'success', L2: 'warning', L3: '' }[level] || 'info' }
function statusText(s) { return { pending: '待处理', approved: '已采纳', rejected: '已驳回', deferred: '暂缓', done: '已完成' }[s] || s || '待处理' }

onMounted(() => {
  load()
  timer = setInterval(load, 5000)
  window.addEventListener('resize', handleResize)
  window.addEventListener('business-changed', () => { load() })
})
onActivated(() => { load() })
onUnmounted(() => {
  if (timer) clearInterval(timer)
  window.removeEventListener('resize', handleResize)
  if (pieInstance) pieInstance.dispose()
  if (lineInstance) lineInstance.dispose()
})
function handleResize() {
  if (pieInstance) pieInstance.resize()
  if (lineInstance) lineInstance.resize()
}
</script>

<style scoped>
.dashboard-page {
  padding: 24px;
  min-height: 100vh;
  position: relative;
}

/* ---- Page Header ---- */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  margin-bottom: 20px;
}
.page-breadcrumb {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.2px;
}
.breadcrumb-icon {
  display: inline-flex;
  align-items: center;
  color: var(--accent);
}
.header-actions {
  display: flex;
  gap: 8px;
}
.btn-icon {
  display: inline-flex;
  vertical-align: middle;
  margin-right: 2px;
}

/* ---- Stat Cards ---- */
.stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.stat-card {
  display: flex;
  align-items: center;
  padding: 20px;
  gap: 16px;
}
.stat-card:hover {
  transform: translateY(-3px);
}
.stat-icon-wrap {
  width: 50px;
  height: 50px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-icon-wrap.health {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(16, 185, 129, 0.05));
  color: var(--success);
}
.stat-icon-wrap.primary {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(99, 102, 241, 0.05));
  color: var(--accent);
}
.stat-icon-wrap.warning {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.05));
  color: var(--warning);
}
.stat-icon-wrap.danger {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(239, 68, 68, 0.05));
  color: var(--danger);
}
.stat-body { flex: 1; min-width: 0; }
.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
  display: flex;
  align-items: center;
  gap: 8px;
}
.health-dot {
  display: inline-block;
  width: 10px; height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.health-dot.green { background: var(--success); box-shadow: 0 0 10px rgba(16, 185, 129, 0.5); }
.health-dot.red { background: var(--danger); box-shadow: 0 0 10px rgba(239, 68, 68, 0.5); }
.stat-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
  font-weight: 500;
}

/* ---- Bento Grid ---- */
.bento-row {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}
.bento-main { min-width: 0; }
.bento-side {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.bento-main .chart-box { height: 360px; }
.bento-side .chart-box.small-chart { height: 220px; }

/* ---- Chart Cards ---- */
.chart-card {
  padding: 20px;
}
.chart-card:hover {
  transform: translateY(-2px);
}
.chart-title {
  margin: 0 0 12px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}
.chart-title::before {
  content: '';
  display: block;
  width: 3px;
  height: 16px;
  background: var(--accent);
  border-radius: 2px;
}
.chart-box { width: 100%; overflow: hidden; }

/* ---- Mini List Card ---- */
.mini-list-card {
  padding: 18px;
  flex: 1;
}
.mini-list-title {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}
.mini-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(0,0,0,0.04);
  font-size: 12px;
}
.mini-row:last-child { border-bottom: none; }
.mini-content {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-secondary);
}

/* ---- List Card ---- */
.list-card {
  padding: 24px;
  margin-bottom: 20px;
}
.list-title {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}
.list-title::before {
  content: '';
  display: block;
  width: 3px;
  height: 18px;
  background: var(--accent);
  border-radius: 2px;
}

/* ---- Table ---- */
.table-header {
  display: flex;
  padding: 10px 0;
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid rgba(0,0,0,0.05);
}
.table-row {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid rgba(0,0,0,0.03);
  transition: background 0.15s;
  font-size: 13px;
  color: var(--text-secondary);
}
.table-row:last-child { border-bottom: none; }
.table-row:hover { background: rgba(99, 102, 241, 0.04); }
.col-type { width: 100px; flex-shrink: 0; }
.col-desc { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding: 0 12px; }
.col-level { width: 60px; flex-shrink: 0; }
.col-status { width: 80px; flex-shrink: 0; text-align: right; color: var(--text-muted); }
.empty-row {
  padding: 32px 0;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}
</style>