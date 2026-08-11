<template>
  <div class="dashboard-page">
    <div class="page-header">
      <div class="page-breadcrumb">
        <i data-lucide="layout-dashboard" class="breadcrumb-icon"></i>
        <span>仪表盘</span>
      </div>
      <div class="header-actions">
        <el-button type="primary" size="small" @click="runAttribution" :loading="attributionLoading">
          <i data-lucide="play" class="btn-icon"></i> 运行归因
        </el-button>
        <el-button type="primary" size="small" @click="runAutoExecute" :loading="executeLoading">
          <i data-lucide="zap" class="btn-icon"></i> 执行提案
        </el-button>
        <el-button type="primary" size="small" @click="runWeeklyReport" :loading="reportLoading">
          <i data-lucide="bar-chart-3" class="btn-icon"></i> 生成周报
        </el-button>
      </div>
    </div>

    <div class="stat-row">
      <div class="stat-card">
        <span class="stat-icon health"><i data-lucide="heart-pulse"></i></span>
        <div class="stat-body">
          <div class="stat-value">
            <span class="health-dot green"></span>{{ dashboard.health === 'ok' ? '正常' : '异常' }}
          </div>
          <div class="stat-label">系统健康</div>
        </div>
      </div>
      <div class="stat-card">
        <span class="stat-icon primary"><i data-lucide="message-square"></i></span>
        <div class="stat-body">
          <div class="stat-value">{{ dashboard.today ?? 0 }}</div>
          <div class="stat-label">今日消息</div>
        </div>
      </div>
      <div class="stat-card">
        <span class="stat-icon warning"><i data-lucide="shield-alert"></i></span>
        <div class="stat-body">
          <div class="stat-value">{{ dashboard.flagged ?? 0 }}</div>
          <div class="stat-label">质检标记</div>
        </div>
      </div>
      <div class="stat-card">
        <span class="stat-icon danger"><i data-lucide="clipboard-list"></i></span>
        <div class="stat-body">
          <div class="stat-value">{{ dashboard.proposals ?? 0 }}</div>
          <div class="stat-label">待处理提案</div>
        </div>
      </div>
    </div>

    <div class="bento-row">
      <div class="bento-main">
        <div class="chart-card large">
          <h3 class="chart-title">24小时会话量趋势</h3>
          <div ref="lineChart" class="chart-box"></div>
        </div>
      </div>
      <div class="bento-side">
        <div class="chart-card">
          <h3 class="chart-title">意图分布（24h）</h3>
          <div ref="pieChart" class="chart-box small-chart"></div>
        </div>
        <div class="mini-list-card">
          <h3 class="mini-list-title">最近对话</h3>
          <div v-if="dashboard.recent_chats?.length">
            <div v-for="chat in dashboard.recent_chats.slice(0,5)" :key="chat.id" class="mini-row">
              <el-tag size="small" :type="intentTagType(chat.intent)">{{ chat.intent || '-' }}</el-tag>
              <span class="mini-content">{{ chat.content }}</span>
            </div>
          </div>
          <div v-else class="empty-row">暂无对话记录</div>
        </div>
      </div>
    </div>

    <div class="list-card">
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
            <el-tag size="small" :type="attrTag(p.attribution_type)">{{ attrLabel(p.attribution_type) }}</el-tag>
          </span>
          <span class="col-desc" :title="p.content">{{ p.action || '' }} {{ p.content || '' }}</span>
          <span class="col-level">
            <el-tag size="small" :type="levelTag(p.level)">{{ p.level }}</el-tag>
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
  } catch (e) {
    // ignore
  }
}

function renderCharts() {
  const d = dashboard.value
  if (!d.intent_stats || !d.hourly_stats) return
  
  nextTick(() => {
    // 饼图 - 意图分布
    if (pieChart.value) {
      if (!pieInstance) pieInstance = echarts.init(pieChart.value)
      pieInstance.setOption({
        tooltip: { trigger: 'item' },
        legend: { bottom: 0, textStyle: { fontSize: 11 } },
        series: [{
          type: 'pie',
          radius: ['40%', '70%'],
          center: ['50%', '45%'],
          label: { fontSize: 11 },
          data: d.intent_stats.map(i => ({
            name: intentCN(i.name),
            value: i.value
          }))
        }]
      })
    }
    // 折线图 - 24h趋势
    if (lineChart.value) {
      if (!lineInstance) lineInstance = echarts.init(lineChart.value)
      lineInstance.setOption({
        tooltip: { trigger: 'axis' },
        grid: { left: 40, right: 16, top: 10, bottom: 24 },
        xAxis: {
          type: 'category',
          data: d.hourly_stats.map(i => i.hour),
          axisLabel: { fontSize: 10, rotate: 45 }
        },
        yAxis: {
          type: 'value',
          minInterval: 1,
          axisLabel: { fontSize: 10 }
        },
        series: [{
          type: 'line',
          data: d.hourly_stats.map(i => i.count),
          smooth: true,
          lineStyle: { color: '#1890ff', width: 2 },
          areaStyle: { color: 'rgba(24,144,255,0.1)' },
          itemStyle: { color: '#1890ff' }
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
  } catch (e) {
    ElMessage.error('归因分析失败')
  }
  attributionLoading.value = false
}

async function runAutoExecute() {
  executeLoading.value = true
  try {
    const r = await fetch('/api/admin/auto-execute', { method: 'POST' })
    ElMessage.success('L1 提案已执行')
    load()
  } catch (e) {
    ElMessage.error('执行失败')
  }
  executeLoading.value = false
}

async function runWeeklyReport() {
  reportLoading.value = true
  try {
    const r = await fetch('/api/admin/weekly-report', { method: 'POST' })
    ElMessage.success('周报已生成')
  } catch (e) {
    ElMessage.error('周报生成失败')
  }
  reportLoading.value = false
}

function intentTagType(intent) {
  if (['handover', 'no_reply'].includes(intent)) return 'warning'
  if (['complaint', 'complain'].includes(intent)) return 'danger'
  if (['after_sale', 'price'].includes(intent)) return 'success'
  return 'info'
}

function intentCN(intent) {
  const map = {
    price: '议价', logistics: '物流', after_sale: '售后',
    tech: '产品', default: '通用', handover: '转人工',
    complaint: '投诉', complain: '投诉', no_reply: '无回复', error: '错误',
    fee: '缴费', repair: '报修', notice: '公告',
  }
  return map[intent] || intent
}

function attrLabel(t) {
  return { A: '知识缺失', B: '路由错误', C: '话术问题', D: '正常转接' }[t] || t
}
function attrTag(t) {
  return { A: 'warning', B: 'danger', C: '', D: 'success' }[t] || 'info'
}
function levelTag(level) {
  return { L1: 'success', L2: 'warning', L3: '' }[level] || 'info'
}
function statusText(s) {
  return { pending: '待处理', approved: '已采纳', rejected: '已驳回', deferred: '暂缓', done: '已完成' }[s] || s || '待处理'
}

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
  padding: 0 24px 24px;
  min-height: 100vh;
  background: #f0f2f5;
}

/* ---- unified page header ---- */
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
.header-actions {
  display: flex;
  gap: 8px;
}
.btn-icon {
  display: inline-flex;
  vertical-align: middle;
  margin-right: 2px;
}

/* ---- stat cards ---- */
.stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.stat-card {
  display: flex;
  align-items: center;
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  gap: 16px;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1), 0 2px 8px rgba(0, 0, 0, 0.06);
}
.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-icon.health  { background: linear-gradient(135deg, #f6ffed, #d9f7be); color: #52c41a; }
.stat-icon.primary { background: linear-gradient(135deg, #e6f7ff, #bae7ff); color: #1890ff; }
.stat-icon.warning { background: linear-gradient(135deg, #fff7e6, #ffe7ba); color: #fa8c16; }
.stat-icon.danger  { background: linear-gradient(135deg, #fff2f0, #ffccc7); color: #ff4d4f; }

.stat-body {
  flex: 1;
  min-width: 0;
}
.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1.2;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 8px;
}
.health-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.health-dot.green { background: #52c41a; }
.health-dot.red   { background: #ff4d4f; }

.stat-label {
  font-size: 12px;
  color: #8c8c8c;
  margin-top: 4px;
}

/* ---- bento grid ---- */
.bento-row {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}
.bento-main {
  min-width: 0;
}
.bento-side {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.bento-main .chart-box {
  height: 360px;
}
.bento-side .chart-box.small-chart {
  height: 220px;
}

/* ---- chart cards ---- */
.chart-card {
  background: #fff;
  border-radius: 8px;
  padding: 16px 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.chart-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1), 0 2px 8px rgba(0, 0, 0, 0.06);
}
.chart-title {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.85);
  position: relative;
}
.chart-title::after {
  content: '';
  display: block;
  width: 32px;
  height: 2px;
  background: #1890ff;
  margin-top: 6px;
  border-radius: 1px;
}
.chart-box {
  width: 100%;
  overflow: hidden;
}

/* ---- mini list card ---- */
.mini-list-card {
  background: #fff;
  border-radius: 8px;
  padding: 12px 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  flex: 1;
}
.mini-list-title {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.85);
}
.mini-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid #f5f5f5;
  font-size: 12px;
}
.mini-row:last-child {
  border-bottom: none;
}
.mini-content {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: rgba(0, 0, 0, 0.65);
}

/* ---- list cards ---- */
.list-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  margin-bottom: 20px;
}
.list-title {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.85);
  border-left: 3px solid #1890ff;
  padding-left: 12px;
}

/* table layout */
.table-header {
  display: flex;
  padding: 8px 0;
  font-size: 13px;
  color: #8c8c8c;
  font-weight: 500;
  border-bottom: 1px solid #f0f0f0;
}
.table-row {
  display: flex;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.15s;
  font-size: 13px;
  color: rgba(0, 0, 0, 0.65);
}
.table-row:last-child {
  border-bottom: none;
}
.table-row:hover {
  background: #f0f7ff;
}
.col-intent { width: 90px; flex-shrink: 0; }
.col-content { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding: 0 12px; }
.col-time   { width: 160px; flex-shrink: 0; text-align: right; color: #999; }
.col-type   { width: 90px; flex-shrink: 0; }
.col-desc   { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding: 0 12px; }
.col-level  { width: 60px; flex-shrink: 0; }
.col-status { width: 80px; flex-shrink: 0; text-align: right; color: #999; }

.empty-row {
  padding: 24px 0;
  text-align: center;
  color: #bbb;
  font-size: 13px;
}
</style>
