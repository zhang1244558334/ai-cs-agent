import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import App from './App.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: () => import('./views/Chat.vue') },
    { path: '/knowledge', component: () => import('./views/Knowledge.vue') },
    { path: '/sessions', component: () => import('./views/Sessions.vue') },
    { path: '/settings', component: () => import('./views/Settings.vue') },
  ],
})

const app = createApp(App)
app.use(router)
app.use(ElementPlus)
app.mount('#app')
