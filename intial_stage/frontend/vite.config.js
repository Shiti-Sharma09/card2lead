import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Assets are referenced relatively so the build also works when FastAPI
// serves it from any path.
export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    host: true, // listen on 0.0.0.0 so a phone / tunnel can reach the dev server
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
