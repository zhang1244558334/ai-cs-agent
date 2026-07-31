<template>
  <el-container style="height: 100vh">
    <el-header style="display: flex; align-items: center; background: #409eff; color: #fff; padding: 0 20px">
      <h2 style="margin: 0; font-size: 18px">AI 智能客服系统</h2>
      <el-menu
        :default-active="route.path"
        mode="horizontal"
        style="margin-left: 40px; background: transparent; border: none"
        text-color="#fff"
        active-text-color="#fff"
        router
      >
        <el-menu-item index="/">对话</el-menu-item>
        <el-menu-item index="/sessions">会话</el-menu-item>
        <el-menu-item index="/knowledge">知识库</el-menu-item>
        <el-menu-item index="/settings">设置</el-menu-item>
        <el-menu-item index="/review">审批</el-menu-item>
        <el-menu-item index="/tenants">租户</el-menu-item>
        <el-menu-item index="/test">🧪 测试</el-menu-item>
      </el-menu>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { useRoute } from 'vue-router'
const route = useRoute()
</script>
