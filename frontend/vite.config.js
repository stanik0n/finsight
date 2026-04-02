import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/query':         'http://api:8000',
      '/health':        'http://api:8000',
      '/schema':        'http://api:8000',
      '/anomalies':     'http://api:8000',
      '/market-snapshot': 'http://api:8000',
      '/market-news':   'http://api:8000',
      '/notes':         'http://api:8000',
      '/portfolio':     'http://api:8000',
      '/stream-status': 'http://api:8000',
    },
  },
})
