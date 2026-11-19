import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/exports': 'http://localhost:8000',
      '/temp': 'http://localhost:8000',
      '/assets/music': 'http://localhost:8000'
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true
  }
})
