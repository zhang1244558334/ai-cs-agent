<template>
  <div style="padding:20px;max-width:800px;margin:0 auto">
    <h3>设置中心</h3>
    <el-form label-width="120px">
      <el-form-item label="模型">
        <el-input v-model="model" placeholder="deepseek-chat" />
      </el-form-item>
      <el-form-item label="API地址">
        <el-input v-model="baseUrl" placeholder="https://api.deepseek.com/v1" />
      </el-form-item>
      <el-form-item label="最大让步">
        <el-input-number v-model="maxDiscount" :min="0" :max="0.5" :step="0.05" />
      </el-form-item>
      <el-form-item label="议价轮次">
        <el-input-number v-model="maxRounds" :min="1" :max="10" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary">保存设置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const model = ref(localStorage.getItem('model') || 'deepseek-chat')
const baseUrl = ref(localStorage.getItem('baseUrl') || 'https://api.deepseek.com/v1')
const maxDiscount = ref(parseFloat(localStorage.getItem('maxDiscount') || '0.1'))
const maxRounds = ref(parseInt(localStorage.getItem('maxRounds') || '5'))
</script>
