import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8234',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8234',
        ws: true,
      },
    },
  },
})
