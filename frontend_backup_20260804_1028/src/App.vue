<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="sidebar-header">
        <i data-lucide="message-circle" class="header-icon"></i>
        <span>AI 智能客服系统</span>
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
import { onMounted, onUnmounted, watch, ref } from 'vue'
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
</style>
