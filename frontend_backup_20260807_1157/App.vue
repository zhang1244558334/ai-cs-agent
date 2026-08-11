<template>
  <div class="layout">
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
  background: #f0f2f5;
}

.page-header-card {
  background: #fff;
  border-radius: 8px;
  padding: 18px 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  margin: 20px 24px 0;
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
</style>
