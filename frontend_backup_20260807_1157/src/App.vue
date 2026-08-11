<template>
  <div class="layout" :class="{ dark: darkMode }">
    <aside class="sidebar">
      <div class="sidebar-header">
        <i data-lucide="message-circle" class="header-icon"></i>
        <span>AI 智能客服系统</span>
      </div>
      <div class="business-switcher">
        <div class="business-current" @click="showBizMenu = !showBizMenu">
          <i :data-lucide="currentBiz.icon || 'shopping-cart'" class="biz-icon"></i>
          <span class="biz-name">{{ currentBiz.name }}</span>
          <i data-lucide="chevron-down" class="biz-arrow"></i>
        </div>
        <div v-if="showBizMenu" class="business-menu">
          <div v-for="biz in filteredBusinesses" :key="biz.id"
               class="biz-option"
               :class="{ active: biz.id === activeBusiness }"
               @click="switchBusiness(biz)">
            <i :data-lucide="biz.icon || 'building-2'" class="biz-option-icon"></i>
            <span>{{ biz.name }}</span>
          </div>
          <div class="biz-divider"></div>
          <div class="biz-option biz-add" @click="addBusiness">
            <i data-lucide="plus"></i> 新增业务线
          </div>
        </div>
      </div>
      <nav class="sidebar-nav">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="menu-link"
          :class="{ active: route.path === item.path }"
        >
          <i :data-lucide="item.icon" class="menu-icon"></i>
          <span>{{ item.label }}</span>
          <span v-if="item.badge && pendingBadge" class="menu-badge">{{ pendingBadge }}</span>
        </router-link>
      </nav>
      <div class="sidebar-footer" @click="toggleDark">
        <i :data-lucide="darkMode ? 'sun' : 'moon'"></i>
        <span>{{ darkMode ? '日间模式' : '夜间模式' }}</span>
      </div>
    </aside>
    <main class="content">
      <router-view v-slot="{ Component }">
        <keep-alive>
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, watch, ref, computed, nextTick } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const menuItems = [
  { path: '/', label: '仪表盘', icon: 'layout-dashboard' },
  { path: '/chat', label: '对话', icon: 'message-circle' },
  { path: '/sessions', label: '会话', icon: 'history' },
  { path: '/knowledge', label: '知识库', icon: 'book-open' },
  { path: '/settings', label: '设置', icon: 'settings' },
  { path: '/review', label: '审批', icon: 'clipboard-check', badge: true },
  { path: '/tenants', label: '租户', icon: 'building-2' },
]

const darkMode = ref(localStorage.getItem('darkMode') === 'true')
const pendingBadge = ref(0)
let badgeTimer = null

const activeBusiness = ref(localStorage.getItem('activeBusiness') || 'ecommerce')
const businesses = ref([])
const showBizMenu = ref(false)

const currentBiz = computed(() =>
  businesses.value.find(b => b.id === activeBusiness.value) || { id: 'ecommerce', name: '电商客服', icon: 'shopping-cart' }
)

const filteredBusinesses = computed(() =>
  businesses.value.filter(b => b.active !== false)
)

async function loadBusinesses() {
  try {
    const r = await fetch('/api/businesses')
    const d = await r.json()
    businesses.value = d.businesses || []
  } catch (e) { /* keep default */ }
}

function switchBusiness(biz) {
  activeBusiness.value = biz.id
  localStorage.setItem('activeBusiness', biz.id)
  showBizMenu.value = false
  window.dispatchEvent(new CustomEvent('business-changed', { detail: biz.id }))
  nextTick(() => { if (window.lucide) window.lucide.createIcons() })
}

function toggleDark() {
  darkMode.value = !darkMode.value
  localStorage.setItem('darkMode', darkMode.value ? 'true' : 'false')
  document.body.classList.toggle('dark', darkMode.value)
  nextTick(() => { if (window.lucide) window.lucide.createIcons() })
}

function addBusiness() {
  const name = prompt('新业务线名称（如：金融客服）')
  if (!name) return
  fetch('/api/businesses', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, icon: 'briefcase' }),
  }).then(r => r.json()).then(() => {
    loadBusinesses()
    showBizMenu.value = false
  })
}

async function fetchPendingBadge() {
  try {
    const r = await fetch('/api/admin/proposals')
    const data = await r.json()
    const l2 = data.l2 || []
    pendingBadge.value = l2.filter(p => p.status === 'pending').length
  } catch (e) {
    // ignore
  }
}

function loadIcons() {
  if (window.lucide) {
    window.lucide.createIcons({ attrs: { width: '16', height: '16' } })
  }
}

onMounted(() => {
  if (darkMode.value) document.body.classList.add('dark')
  fetchPendingBadge()
  badgeTimer = setInterval(fetchPendingBadge, 30000)
  loadBusinesses()
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.business-switcher')) showBizMenu.value = false
  })
  if (window.lucide) {
    loadIcons()
    return
  }
  const script = document.createElement('script')
  script.src = 'https://unpkg.com/lucide@latest'
  script.onload = loadIcons
  document.head.appendChild(script)
})

onUnmounted(() => {
  if (badgeTimer) clearInterval(badgeTimer)
})

watch(route, () => {
  setTimeout(loadIcons, 0)
})
</script>

<style>
.layout {
  display: flex;
  height: 100vh;
}
.sidebar {
  width: 220px;
  background: linear-gradient(180deg, #0f0f23 0%, #1a1a2e 40%, #16213e 100%);
  color: #fff;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.sidebar-header {
  padding: 20px 16px;
  font-size: 18px;
  font-weight: 700;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  white-space: nowrap;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.header-icon {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}
.sidebar-nav {
  flex: 1;
  padding: 8px 0;
  overflow-y: auto;
}
.menu-link {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  color: rgba(255, 255, 255, 0.5);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  border-left: 4px solid transparent;
  gap: 10px;
}
.menu-link:hover {
  background: rgba(79, 195, 247, 0.08);
  color: rgba(255, 255, 255, 0.8);
  transform: translateX(2px);
}
.menu-link.active {
  background: rgba(79, 195, 247, 0.12);
  color: #4fc3f7;
  border-left-color: #4fc3f7;
  font-weight: 600;
}
.menu-icon {
  display: inline-flex;
  align-items: center;
}
.menu-badge {
  margin-left: auto;
  background: #ff4d4f;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  min-width: 18px;
  height: 18px;
  line-height: 18px;
  text-align: center;
  border-radius: 9px;
  padding: 0 5px;
}
.content {
  flex: 1;
  overflow-y: auto;
  background: #e4e7ed;
}

.page-header-card {
  background: #fff;
  border-radius: 8px;
  padding: 18px 24px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  margin: 20px 24px 0;
  transition: box-shadow 0.2s, transform 0.2s;
}
.page-header-card:hover {
  box-shadow: 0 2px 6px rgba(0,0,0,0.1), 0 6px 20px rgba(0,0,0,0.06);
  transform: translateY(-1px);
}

.business-switcher {
  padding: 8px 12px;
  position: relative;
}
.business-current {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}
.business-current:hover {
  background: rgba(79, 195, 247, 0.08);
}
.biz-icon {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}
.biz-name {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.8);
}
.biz-arrow {
  display: inline-flex;
  align-items: center;
  color: rgba(255, 255, 255, 0.3);
  font-size: 12px;
}
.business-menu {
  position: absolute;
  left: 12px;
  right: 12px;
  top: 100%;
  background: #1e1e36;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 4px;
  z-index: 100;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}
.biz-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  transition: all 0.15s;
}
.biz-option:hover {
  background: rgba(79, 195, 247, 0.1);
  color: rgba(255, 255, 255, 0.9);
}
.biz-option.active {
  background: rgba(79, 195, 247, 0.15);
  color: #4fc3f7;
  font-weight: 600;
}
.biz-option-icon {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}
.biz-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.06);
  margin: 4px 8px;
}
.biz-add {
  color: rgba(79, 195, 247, 0.6);
}
.biz-add:hover {
  color: #4fc3f7;
}

/* ---- dark mode toggle ---- */
.sidebar-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.4);
  font-size: 13px;
  cursor: pointer;
  transition: color 0.2s;
}
.sidebar-footer:hover {
  color: rgba(255, 255, 255, 0.7);
  background: rgba(79, 195, 247, 0.06);
}
.sidebar-footer i {
  display: inline-flex;
  align-items: center;
}

/* ---- dark mode transitions ---- */
body {
  transition: background 0.3s;
}
.content,
.page-header,
.page-header-card,
.stat-card,
.chart-card,
.chat-card,
.list-card,
.mini-list-card,
.session-panel,
.msg-bubble,
.chat-footer,
.chat-header,
.chat-body,
.panel-search {
  transition: background 0.3s, color 0.3s, border-color 0.3s, box-shadow 0.3s;
}

/* ---- dark mode: layout ---- */
body.dark {
  background: #0f0d1a;
}
.layout.dark .content {
  background: #17152b;
}

/* ---- dark mode: page headers & cards ---- */
.layout.dark .page-header,
.layout.dark .page-header-card,
.layout.dark .stat-card,
.layout.dark .chart-card,
.layout.dark .chat-card,
.layout.dark .list-card,
.layout.dark .mini-list-card {
  background: #1e1c33 !important;
  color: #b8b8c8 !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
}
.layout.dark .page-header-card:hover {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25), 0 6px 20px rgba(0, 0, 0, 0.18);
}

/* ---- dark mode: session panel ---- */
.layout.dark .session-panel {
  background: #1e1c33;
}
.layout.dark .panel-search {
  border-bottom-color: #2a2844;
}
.layout.dark .session-item {
  color: #b8b8c8;
}
.layout.dark .session-item .session-user {
  color: #c8c8d8;
}
.layout.dark .session-item .session-time,
.layout.dark .session-item .session-preview {
  color: #7a7a8c;
}
.layout.dark .session-item:hover {
  background: rgba(79, 195, 247, 0.06);
}
.layout.dark .session-item.active {
  background: rgba(24, 144, 255, 0.1);
}

/* ---- dark mode: chat area ---- */
.layout.dark .chat-header {
  border-bottom-color: #2a2844;
  background: #1e1c33;
}
.layout.dark .chat-header .session-id {
  color: #7a7a8c;
}
.layout.dark .chat-body {
  background: #1e1c33;
}
.layout.dark .chat-footer {
  background: #1e1c33;
  border-top-color: #2a2844;
}
.layout.dark .chat-input :deep(.el-input__wrapper) {
  background: #1e1c33;
  box-shadow: 0 0 0 1px #2a2844 inset;
}
.layout.dark .chat-input :deep(.el-input__inner) {
  color: #b8b8c8;
}

/* ---- dark mode: message bubbles ---- */
.layout.dark .msg-bubble.assistant {
  background: #1e1c33;
  color: #b8b8c8;
}
.layout.dark .msg-wrapper.user .msg-bubble {
  background: #2d2350 !important;
  color: #b8b8c8 !important;
}
.layout.dark .msg-bubble.user .msg-time {
  color: rgba(255, 255, 255, 0.45);
}
.layout.dark .msg-bubble.assistant .msg-time {
  color: #6a6a7c;
}
.layout.dark .msg-text {
  color: #b8b8c8;
}
.layout.dark .loading-bubble {
  background: #1e1c33 !important;
}

/* ---- dark mode: labels & text ---- */
.layout.dark .stat-label,
.layout.dark .stat-value {
  color: #c8c8d8;
}
.layout.dark .chart-title,
.layout.dark .list-title,
.layout.dark .mini-list-title {
  color: #c8c8d8;
}
.layout.dark .page-breadcrumb {
  color: #c8c8d8;
}
.layout.dark .mini-row {
  border-bottom-color: #2a2844;
}
.layout.dark .mini-content {
  color: #9999a8;
}
.layout.dark .table-header {
  color: #7a7a8c;
  border-bottom-color: #2a2844;
}
.layout.dark .table-row {
  color: #b8b8c8;
  border-bottom-color: #2a2844;
}
.layout.dark .table-row:hover {
  background: rgba(79, 195, 247, 0.06);
}
.layout.dark .empty-row {
  color: #5a5a6c;
}

/* ---- dark mode: scroll-to-bottom ---- */
.layout.dark .scroll-bottom {
  background: rgba(30, 28, 51, 0.92);
  border-color: #2a2844;
  color: #b8b8c8;
}

/* ---- dark mode: form cards ---- */
.layout.dark .form-slot-bubble {
  background: #1a1830;
  border-color: #2a2844;
}
.layout.dark .form-slot-label {
  color: #7a8af5;
}
.layout.dark .form-slot-prompt {
  color: #b8b8c8;
}
.layout.dark .form-confirm-card {
  background: #1e1c33;
  border-color: #3d4f2a;
}
.layout.dark .form-summary {
  background: #1a182e;
  color: #b8b8c8;
}
.layout.dark .form-confirm-hint {
  color: #6a6a7c;
}
.layout.dark .form-done-card {
  background: #1a1830;
  border-color: #2a2844;
}
.layout.dark .form-done-text {
  color: #b8b8c8;
}

/* ---- dark mode: logistics cards ---- */
.layout.dark .card-logistics {
  background: #1e1c33;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
}
.layout.dark .card-hd {
  background: #1a1830;
  border-bottom-color: #2a2844;
  color: #b8b8c8;
}
.layout.dark .card-bd {
  color: #9999a8;
}
.layout.dark .card-row {
  border-bottom-color: #2a2844;
  color: #9999a8;
}
.layout.dark .card-row span:first-child {
  color: #6a6a7c;
}
.layout.dark .card-timeline {
  border-top-color: #2a2844;
}

/* ---- dark mode: stat-card borders ---- */
.layout.dark .stat-card {
  border-top-color: transparent !important;
}

/* ---- dark mode: dashboard page bg ---- */
.layout.dark .dashboard-page {
  background: #17152b;
}
.layout.dark .chat-page {
  background: #17152b;
}
.layout.dark .knowledge-page,
.layout.dark .settings-page,
.layout.dark .review-page,
.layout.dark .tenants-page,
.layout.dark .sessions-page,
.layout.dark .test-page,
.layout.dark .testcenter-page {
  background: #17152b !important;
}
.layout.dark .settings-card,
.layout.dark .page-card,
.layout.dark .stats-bar,
.layout.dark .stats-item {
  background: #1e1c33 !important;
  color: #b8b8c8 !important;
}
.layout.dark .el-card,
.layout.dark .el-table {
  background: #1e1c33 !important;
  color: #b8b8c8 !important;
}
.layout.dark .el-table th {
  background: #252040 !important;
  color: #c8c8d8 !important;
}
.layout.dark .el-table td {
  border-bottom-color: #2a2844 !important;
}
.layout.dark .el-table--striped .el-table__body tr.el-table__row--striped td {
  background: #1a1830 !important;
}
.layout.dark .el-input__wrapper {
  background: #1e1c33 !important;
  box-shadow: 0 0 0 1px #2a2844 inset !important;
}
.layout.dark .el-input__inner {
  color: #b8b8c8 !important;
}
.layout.dark .el-button--default {
  background: #252040 !important;
  border-color: #2a2844 !important;
  color: #b8b8c8 !important;
}
</style>
