import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/status': 'http://localhost:8000',
      '/upload': 'http://localhost:8000',
      '/start': 'http://localhost:8000',
      '/stop': 'http://localhost:8000',
      '/download': 'http://localhost:8000',
      '/select-output-path': 'http://localhost:8000',
      '/select-input-path': 'http://localhost:8000',
      '/heartbeat': 'http://localhost:8000',
    }
  }
})
