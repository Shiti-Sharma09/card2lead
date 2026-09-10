import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Assets are referenced relatively so the build also works when FastAPI serves
// it from any path.
const API_PREFIXES = ['/auth', '/events', '/me', '/assignees', '/health', '/docs', '/openapi.json']
const target = process.env.VITE_API_PROXY || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    host: true, // listen on 0.0.0.0 so a phone / tunnel can reach the dev server
    port: 5173,
    proxy: Object.fromEntries(
      API_PREFIXES.map((p) => [p, { target, changeOrigin: true }]),
    ),
  },
})
