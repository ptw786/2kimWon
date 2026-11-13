import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'

const here = fileURLToPath(new URL('.', import.meta.url))
const packages = fileURLToPath(new URL('../../packages', import.meta.url))

// 5173·5174·5175·8787·4173은 다른 프로젝트가 쓰므로 피한다(docs/구조.md).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5181,
    strictPort: true,
    host: '0.0.0.0',
    fs: { allow: [here, packages] },
    // WSL에서 /mnt/c(Windows 디스크)의 파일 변경은 알림이 오지 않아 폴링으로 감시한다.
    watch: process.env.WSL_DISTRO_NAME ? { usePolling: true, interval: 300 } : undefined,
    proxy: { '/api': { target: 'http://127.0.0.1:8010', changeOrigin: true } },
  },
  preview: {
    port: 5186,
    strictPort: true,
    host: '0.0.0.0',
    proxy: { '/api': { target: 'http://127.0.0.1:8010', changeOrigin: true } },
  },
  test: { include: ['tests/**/*.test.ts'] },
})
