import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Куда проксировать API в dev-режиме: по умолчанию локальный бэкенд,
// API_PROXY=https://market-aii.ru — чтобы посмотреть фронт с живыми данными.
const apiTarget = process.env.API_PROXY || 'http://127.0.0.1:8000'
const proxy = { target: apiTarget, changeOrigin: true, secure: true }

export default defineConfig({
  plugins: [vue()],
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': proxy,
      '/downloads': proxy,
    },
  },
})
