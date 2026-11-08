import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
export default defineConfig({
  plugins: [react(),tailwindcss()],
  server: {port: 5173, strictPort:true, proxy: {'/api': {
    target:'http://127.0.0.1:8000',
    configure(proxy) {
      proxy.on('error', (_error, _request, response) => {
        if (response && !response.headersSent && typeof response.writeHead === 'function') {
          response.writeHead(502, {'Content-Type':'application/json; charset=utf-8'})
          response.end(JSON.stringify({detail:'FastAPI에 연결할 수 없습니다. 127.0.0.1:8000에서 백엔드가 실행 중인지 확인하세요.'}))
        }
      })
    }
  }}}
})
