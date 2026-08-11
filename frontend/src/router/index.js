import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: () => import('../views/Dashboard.vue') },
    { path: '/chat', component: () => import('../views/Chat.vue') },
    { path: '/sessions', component: () => import('../views/Sessions.vue') },
    { path: '/knowledge', component: () => import('../views/Knowledge.vue') },
    { path: '/settings', component: () => import('../views/Settings.vue') },
    { path: '/review', component: () => import('../views/Review.vue') },
    { path: '/tenants', component: () => import('../views/Tenants.vue') },
    { path: '/test', component: () => import('../views/TestCenter.vue') },
  ],
})

export default router
