import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '127.0.0.1',
    proxy: {
      '/auth': 'http://127.0.0.1:8000',
      '/documents': 'http://127.0.0.1:8000',
      '/reviews': 'http://127.0.0.1:8000',
      '/kb': 'http://127.0.0.1:8000',
      '/memory': 'http://127.0.0.1:8000',
      '/diagrams': 'http://127.0.0.1:8000',
      '/audit': 'http://127.0.0.1:8000',
      '/settings': 'http://127.0.0.1:8000',
      '/build-projects': 'http://127.0.0.1:8000',
      '/dashboard': 'http://127.0.0.1:8000',
      '/seed': 'http://127.0.0.1:8000',
      '/ai': 'http://127.0.0.1:8000',
      '/batch-reviews': 'http://127.0.0.1:8000',
      '/standards': 'http://127.0.0.1:8000',
      '/requirements-documents': 'http://127.0.0.1:8000',
      '/lessons': 'http://127.0.0.1:8000',
      '/risk-catalog': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
});
