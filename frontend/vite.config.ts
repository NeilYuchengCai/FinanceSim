import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { splitVendorChunkPlugin } from 'vite'

export default defineConfig({
  plugins: [react(), splitVendorChunkPlugin()],
  server: {
    port: 5174,
    proxy: {
      '/api': {
        // 后端实际监听 8000；此前指向 8080 导致前端所有接口请求代理失败
        target: 'http://localhost:8000',
        changeOrigin: true,
        // WebSocket 必须显式开启代理，否则 /api/v1/ws/prices 连不上
        ws: true
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-charts': ['recharts', 'lightweight-charts'],
          'vendor-utils': ['axios', 'zustand', 'date-fns'],
        }
      }
    },
    // 图表库(recharts/lightweight-charts)本身体积大，单独成 chunk 已是最优拆分；
    // 阈值上调到与真实产物匹配，避免误导性的构建告警。
    chunkSizeWarningLimit: 700,
  }
})
