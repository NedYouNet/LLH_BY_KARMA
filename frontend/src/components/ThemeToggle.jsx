import { useLayoutEffect, useState } from 'react'

const storageKey = 'fsp-color-theme'

function readTheme() {
    try {
        return localStorage.getItem(storageKey) === 'dark' ? 'dark' : 'light'
    } catch {
        return 'light'
    }
}

export default function ThemeToggle() {
    const [theme, setTheme] = useState(readTheme)

    useLayoutEffect(() => {
        document.documentElement.dataset.theme = theme
        try { localStorage.setItem(storageKey, theme) } catch { /* Тема работает и без хранилища. */ }
    }, [theme])

    useLayoutEffect(() => {
        function onStorage(event) {
            if (event.key === storageKey || event.key === null) setTheme(readTheme())
        }
        window.addEventListener('storage', onStorage)
        return () => window.removeEventListener('storage', onStorage)
    }, [])

    const dark = theme === 'dark'
    return <button type="button" className="ml-auto flex shrink-0 items-center gap-2 rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-sm font-medium text-gray-800 hover:bg-purple-100" aria-label={dark ? 'Включить светлую тему' : 'Включить тёмную тему'} aria-pressed={dark} onClick={() => setTheme(dark ? 'light' : 'dark')}>
        <span aria-hidden="true">{dark ? '☀' : '☾'}</span>
        {dark ? 'Светлая тема' : 'Тёмная тема'}
    </button>
}
