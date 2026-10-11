import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
    // Где запущен бэкенд. По умолчанию — на этом же компьютере.
    // Если бэкенд на другом ноутбуке в той же Wi-Fi сети, создайте файл .env.local
    // с одной строкой:  BACKEND_URL=http://192.168.1.15:8000   (IP ноутбука с бэкендом)
    const env = loadEnv(mode, process.cwd(), '')
    const backend = env.BACKEND_URL || 'http://localhost:8000'

    // Все запросы фронта на /api/... Vite тихо пересылает бэкенду.
    // Для браузера это «тот же сайт», поэтому никаких проблем с CORS.
    const proxy = { '/api': { target: backend, changeOrigin: true } }

    return {
        plugins: [react(), tailwindcss()],
        server: { host: true, proxy },   // host: true — фронт откроется и с других устройств в сети
        preview: { host: true, proxy },
    }
})
