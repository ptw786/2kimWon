import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// packages/design/tokens.css를 그대로 가져오기 위해 두 단계 위(2팀/)까지 읽기를 허용한다.
const repoRoot = fileURLToPath(new URL('../..', import.meta.url));
// WSL에서 /mnt/c 아래 파일은 변경 알림이 오지 않아 폴링으로 감시한다.
const onWslMount = !!process.env.WSL_DISTRO_NAME && repoRoot.startsWith('/mnt/');

export default defineConfig({
  plugins: [react()],
  server: {
    // IPv4로 연다. host:true(::)면 Windows 브라우저 → WSL 전달이 안 되는 경우가 있었다(2026-11-14).
    host: '0.0.0.0',
    port: 5180,
    strictPort: true,
    fs: { allow: [repoRoot] },
    watch: onWslMount ? { usePolling: true, interval: 400 } : undefined,
    proxy: { '/api': { target: 'http://127.0.0.1:8010', changeOrigin: true } },
  },
  preview: { port: 5180, strictPort: true },
});
