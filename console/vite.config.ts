/// <reference types="vitest/config" />
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const contracts = fileURLToPath(new URL('../contracts', import.meta.url))

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@contracts': contracts },
  },
  worker: { format: 'es' },
  server: {
    fs: { allow: ['..'] },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: { modules: { classNameStrategy: 'non-scoped' } },
  },
})
