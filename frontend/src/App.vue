<template>
  <div class="layout" :class="{ dark: darkMode }">
    <!-- 背景层：渐变 + 浮动光斑 -->
    <div class="bg-layer" aria-hidden="true">
      <div class="bg-gradient"></div>
      <div class="bg-blob blob-1"></div>
      <div class="bg-blob blob-2"></div>
      <div class="bg-blob blob-3"></div>
    </div>

    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-glass">
        <div class="sidebar-header">
          <div class="logo-mark">
            <i data-lucide="bot" class="logo-icon"></i>
          </div>
          <div class="logo-text">
            <span class="logo-title">AI 智能客服</span>
            <span class="logo-sub">Agent System</span>
          </div>
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

        <div class="nav-group-label">核心功能</div>
        <nav class="sidebar-nav">
          <router-link
            v-for="item in coreMenuItems"
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

        <div class="nav-group-label">系统管理</div>
        <nav class="sidebar-nav">
          <router-link
            v-for="item in adminMenuItems"
            :key="item.path"
            :to="item.path"
            class="menu-link"
            :class="{ active: route.path === item.path }"
          >
            <i :data-lucide="item.icon" class="menu-icon"></i>
            <span>{{ item.label }}</span>
          </router-link>
        </nav>

        <div class="sidebar-footer">
          <div class="footer-btn" @click="toggleDark">
            <i :data-lucide="darkMode ? 'sun' : 'moon'" class="footer-icon"></i>
            <span>{{ darkMode ? '日间模式' : '夜间模式' }}</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- 主内容 -->
    <main class="content">
      <router-view v-slot="{ Component }">
        <transition name="page-fade" mode="out-in">
          <keep-alive>
            <component :is="Component" />
          </keep-alive>
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, watch, ref, computed, nextTick } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const coreMenuItems = [
  { path: '/', label: '仪表盘', icon: 'layout-dashboard' },
  { path: '/chat', label: '对话', icon: 'message-circle' },
  { path: '/sessions', label: '会话', icon: 'history' },
  { path: '/knowledge', label: '知识库', icon: 'book-open' },
]

const adminMenuItems = [
  { path: '/review', label: '审批', icon: 'clipboard-check', badge: true },
  { path: '/tenants', label: '租户', icon: 'building-2' },
  { path: '/settings', label: '设置', icon: 'settings' },
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
  window.dispatchEvent(new CustomEvent('dark-mode-changed', { detail: { dark: darkMode.value } }))
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
  } catch (e) {}
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
/* ============================================
   CSS Variables — Light Mode (Default)
   ============================================ */
:root {
  --bg-base: #e8ecf4;
  --bg-gradient-1: #c3cfe2;
  --bg-gradient-2: #e2d5f3;
  --bg-gradient-3: #b8d4e3;

  --glass-bg: rgba(255, 255, 255, 0.55);
  --glass-bg-hover: rgba(255, 255, 255, 0.7);
  --glass-border: rgba(255, 255, 255, 0.45);
  --glass-shadow: 0 8px 32px rgba(31, 38, 135, 0.08);
  --glass-shadow-hover: 0 12px 40px rgba(31, 38, 135, 0.14);
  --glass-blur: 20px;

  --sidebar-glass-bg: rgba(15, 15, 35, 0.72);
  --sidebar-glass-border: rgba(255, 255, 255, 0.08);
  --sidebar-glass-blur: 28px;

  --text-primary: rgba(15, 23, 42, 0.88);
  --text-secondary: rgba(15, 23, 42, 0.55);
  --text-muted: rgba(15, 23, 42, 0.35);

  --accent: #6366f1;
  --accent-light: rgba(99, 102, 241, 0.12);
  --accent-glow: rgba(99, 102, 241, 0.25);

  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
  --info: #6366f1;

  --radius-sm: 10px;
  --radius-md: 14px;
  --radius-lg: 20px;
  --radius-xl: 24px;
}

/* ============================================
   CSS Variables — Dark Mode
   ============================================ */
body.dark {
  --bg-base: #0f0d1a;
  --bg-gradient-1: #15132e;
  --bg-gradient-2: #13102a;
  --bg-gradient-3: #0f0d1a;

  /* 暗色模式用实色卡片，不用毛玻璃 */
  --glass-bg: rgba(30, 28, 51, 0.92);
  --glass-bg-hover: rgba(35, 33, 58, 0.96);
  --glass-border: rgba(255, 255, 255, 0.08);
  --glass-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
  --glass-shadow-hover: 0 8px 24px rgba(0, 0, 0, 0.45);
  --glass-blur: 0px;

  --sidebar-glass-bg: rgba(15, 13, 26, 0.95);
  --sidebar-glass-border: rgba(255, 255, 255, 0.06);

  --text-primary: #c8c8d8;
  --text-secondary: #8a8a9c;
  --text-muted: #5a5a6c;

  --accent: #6cc3f0;
  --accent-light: rgba(79, 195, 247, 0.12);
  --accent-glow: rgba(79, 195, 247, 0.18);
}

/* ============================================
   Base Reset
   ============================================ */
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  transition: background 0.4s ease;
  overflow: hidden;
}

/* ============================================
   Layout
   ============================================ */
.layout {
  display: flex;
  height: 100vh;
  position: relative;
  overflow: hidden;
}

/* ============================================
   Background Layer — Gradient + Blobs
   ============================================ */
.bg-layer {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}
.bg-gradient {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, var(--bg-gradient-1) 0%, var(--bg-gradient-2) 50%, var(--bg-gradient-3) 100%);
  transition: background 0.5s ease;
}
.bg-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.5;
  animation: blobFloat 20s ease-in-out infinite;
}
.blob-1 {
  width: 500px; height: 500px;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.35), transparent 70%);
  top: -10%; right: -5%;
  animation-delay: 0s;
}
.blob-2 {
  width: 400px; height: 400px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.3), transparent 70%);
  bottom: -10%; left: 10%;
  animation-delay: -7s;
}
.blob-3 {
  width: 350px; height: 350px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.25), transparent 70%);
  top: 40%; left: 50%;
  animation-delay: -14s;
}
@keyframes blobFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(30px, -40px) scale(1.05); }
  50% { transform: translate(-20px, 20px) scale(0.95); }
  75% { transform: translate(15px, 30px) scale(1.02); }
}

/* ============================================
   Sidebar — Glassmorphism
   ============================================ */
.sidebar {
  width: 240px;
  flex-shrink: 0;
  position: relative;
  z-index: 10;
}
.sidebar-glass {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--sidebar-glass-bg);
  backdrop-filter: blur(var(--sidebar-glass-blur));
  -webkit-backdrop-filter: blur(var(--sidebar-glass-blur));
  border-right: 1px solid var(--sidebar-glass-border);
  color: rgba(255, 255, 255, 0.92);
}

/* Logo Area */
.sidebar-header {
  padding: 22px 20px 18px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.logo-mark {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
}
.logo-icon {
  display: inline-flex;
  align-items: center;
  color: #fff;
}
.logo-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.logo-title {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.logo-sub {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.35);
  text-transform: uppercase;
  letter-spacing: 1.5px;
  font-weight: 500;
}

/* Business Switcher */
.business-switcher {
  padding: 12px 14px 8px;
  position: relative;
}
.business-current {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.2s;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.05);
}
.business-current:hover {
  background: rgba(255, 255, 255, 0.08);
}
.biz-icon {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  color: rgba(255, 255, 255, 0.5);
}
.biz-name {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.75);
}
.biz-arrow {
  display: inline-flex;
  align-items: center;
  color: rgba(255, 255, 255, 0.25);
}
.business-menu {
  position: absolute;
  left: 14px;
  right: 14px;
  top: 100%;
  background: rgba(30, 28, 55, 0.92);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-sm);
  padding: 6px;
  z-index: 100;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
}
.biz-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.55);
  transition: all 0.15s;
}
.biz-option:hover {
  background: rgba(99, 102, 241, 0.12);
  color: rgba(255, 255, 255, 0.9);
}
.biz-option.active {
  background: rgba(99, 102, 241, 0.18);
  color: #a5b4fc;
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
  color: rgba(99, 102, 241, 0.6);
}
.biz-add:hover {
  color: #a5b4fc;
}

/* Nav Group Labels */
.nav-group-label {
  padding: 16px 22px 6px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  color: rgba(255, 255, 255, 0.2);
}

/* Nav */
.sidebar-nav {
  padding: 2px 8px;
}
.menu-link {
  display: flex;
  align-items: center;
  padding: 10px 14px;
  color: rgba(255, 255, 255, 0.45);
  text-decoration: none;
  font-size: 13.5px;
  border-radius: 10px;
  gap: 10px;
  transition: all 0.2s ease;
  margin-bottom: 2px;
  position: relative;
}
.menu-link:hover {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.75);
}
.menu-link.active {
  background: rgba(99, 102, 241, 0.15);
  color: #c7d2fe;
   font-weight: 600;
  box-shadow: inset 0 0 0 1px rgba(99, 102, 241, 0.2);
}
.menu-link.active::before {
  content: '';
  position: absolute;
  left: -8px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  background: var(--accent);
  border-radius: 0 3px 3px 0;
}
.menu-icon {
  display: inline-flex;
  align-items: center;
}
.menu-badge {
  margin-left: auto;
  background: var(--danger);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  min-width: 20px;
  height: 20px;
  line-height: 20px;
  text-align: center;
  border-radius: 10px;
  padding: 0 6px;
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.35);
}

/* Sidebar Footer */
.sidebar-footer {
  margin-top: auto;
  padding: 12px 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
.footer-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.35);
  transition: all 0.2s;
}
.footer-btn:hover {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.65);
}
.footer-icon {
  display: inline-flex;
  align-items: center;
}

/* ============================================
   Content Area
   ============================================ */
.content {
  flex: 1;
  overflow-y: auto;
  position: relative;
  z-index: 1;
  scrollbar-width: thin;
  scrollbar-color: rgba(0,0,0,0.12) transparent;
}
.content::-webkit-scrollbar {
  width: 6px;
}
.content::-webkit-scrollbar-track {
  background: transparent;
}
.content::-webkit-scrollbar-thumb {
  background: rgba(0,0,0,0.12);
  border-radius: 3px;
}

/* ============================================
   Page Transition
   ============================================ */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* ============================================
   Global Glass Card Classes
   ============================================ */
.page-header-card,
.glass-card {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  box-shadow: var(--glass-shadow);
  transition: box-shadow 0.3s ease, transform 0.3s ease, background 0.3s ease;
}
.page-header-card:hover,
.glass-card:hover {
  box-shadow: var(--glass-shadow-hover);
}

/* ============================================
   Dark Mode Overrides
   ============================================ */
.layout.dark .content::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.1);
}
.layout.dark .el-overlay,
.layout.dark .el-dialog {
  background: rgba(20, 18, 38, 0.9) !important;
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.06);
}
.layout.dark .el-card {
  background: var(--glass-bg) !important;
  backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border) !important;
  color: var(--text-primary) !important;
  box-shadow: var(--glass-shadow) !important;
}
.layout.dark .el-table {
  background: transparent !important;
  color: var(--text-primary) !important;
}
.layout.dark .el-table th {
  background: rgba(79, 195, 247, 0.06) !important;
  color: var(--text-primary) !important;
}
.layout.dark .el-table td {
  border-bottom-color: rgba(255,255,255,0.05) !important;
}
.layout.dark .el-table--striped .el-table__body tr.el-table__row--striped td {
  background: rgba(255,255,255,0.02) !important;
}
.layout.dark .el-table tr {
  background: transparent !important;
}
.layout.dark .el-input__wrapper {
  background: rgba(255,255,255,0.05) !important;
  box-shadow: 0 0 0 1px rgba(255,255,255,0.08) inset !important;
}
.layout.dark .el-input__inner {
  color: var(--text-primary) !important;
}
.layout.dark .el-button--default {
  background: rgba(255,255,255,0.06) !important;
  border-color: rgba(255,255,255,0.08) !important;
  color: var(--text-primary) !important;
}
.layout.dark .el-button--default:hover {
  background: rgba(255,255,255,0.1) !important;
}
.layout.dark .el-collapse-item__header {
  background: transparent !important;
  color: var(--text-primary) !important;
  border-bottom-color: rgba(255,255,255,0.06) !important;
}
.layout.dark .el-collapse-item__wrap {
  background: transparent !important;
  border-bottom-color: rgba(255,255,255,0.06) !important;
}
.layout.dark .el-divider {
  border-color: rgba(255,255,255,0.06) !important;
}
.layout.dark .el-tabs__item {
  color: var(--text-secondary) !important;
}
.layout.dark .el-tabs__item.is-active {
  color: var(--accent) !important;
}
.layout.dark .el-tabs__active-bar {
  background-color: var(--accent) !important;
}
.layout.dark .el-tabs__nav-wrap::after {
  background-color: rgba(255,255,255,0.06) !important;
}
.layout.dark .el-form-item__label {
  color: var(--text-primary) !important;
}
.layout.dark .el-empty__description p {
  color: var(--text-secondary) !important;
}
.layout.dark .el-switch__label {
  color: var(--text-secondary) !important;
}
.layout.dark .el-tag {
  backdrop-filter: blur(8px);
}
.layout.dark .el-dialog__header {
  color: var(--text-primary) !important;
}
.layout.dark .el-dialog__title {
  color: var(--text-primary) !important;
}
.layout.dark .el-upload-dragger {
  background: rgba(255,255,255,0.03) !important;
  border-color: rgba(255,255,255,0.08) !important;
}
.layout.dark .el-message-box {
  background: rgba(20, 18, 38, 0.95) !important;
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.06) !important;
}
.layout.dark .el-message-box__title {
  color: var(--text-primary) !important;
}
.layout.dark .el-message-box__message {
  color: var(--text-secondary) !important;
}
.layout.dark .el-pagination button,
.layout.dark .el-pager li {
  background: rgba(255,255,255,0.04) !important;
  color: var(--text-secondary) !important;
}
.layout.dark .el-pager li.is-active {
  background: var(--accent-light) !important;
  color: var(--accent) !important;
}
.layout.dark .el-select .el-input__wrapper {
  background: rgba(255,255,255,0.05) !important;
}
.layout.dark .el-select-dropdown__item {
  color: var(--text-primary) !important;
}
.layout.dark .el-select-dropdown__item:hover {
  background: rgba(79, 195, 247, 0.08) !important;
}
.layout.dark .el-popper {
  background: rgba(20, 18, 38, 0.95) !important;
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.06) !important;
}
.layout.dark .el-dropdown-menu {
  background: rgba(20, 18, 38, 0.95) !important;
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.06) !important;
}
.layout.dark .el-dropdown-menu__item {
  color: var(--text-primary) !important;
}
.layout.dark .el-dropdown-menu__item:hover {
  background: rgba(79, 195, 247, 0.08) !important;
}
.layout.dark .el-loading-mask {
  background: rgba(15, 13, 26, 0.6) !important;
}

/* 页面级暗色适配 */
.layout.dark .settings-page,
.layout.dark .sessions-page,
.layout.dark .knowledge-page,
.layout.dark .review-page,
.layout.dark .tenants-page,
.layout.dark .testcenter-page,
.layout.dark .chat-page {
  background: transparent !important;
}
.layout.dark .el-input-number .el-input__wrapper {
  background: rgba(255,255,255,0.05) !important;
}
</style>
