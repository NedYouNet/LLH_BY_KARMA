import { useState } from 'react'
import { auth, errorMessage } from '../api'

function extractToken(value) {
    const text = value.trim()
    try { return new URL(text).searchParams.get('token') || text } catch { return text }
}

export default function EmailVerification({ email = '', devToken = '', initialToken = '', onVerified, onBack }) {
    const [token, setToken] = useState(initialToken)
    const [address, setAddress] = useState(email)
    const [message, setMessage] = useState('')
    const [busy, setBusy] = useState(false)

    async function verify(value) {
        if (busy) return
        const cleanToken = extractToken(value)
        if (!cleanToken) { setMessage('Вставьте токен или ссылку из письма.'); return }
        setBusy(true)
        setMessage('')
        try { await auth.verifyEmail(cleanToken); onVerified(address.trim()) }
        catch (error) { setMessage(errorMessage(error)) }
        finally { setBusy(false) }
    }

    async function resend(event) {
        event.preventDefault()
        if (busy) return
        setBusy(true)
        setMessage('')
        try {
            const result = await auth.resendVerification(address.trim())
            setMessage(result.message || 'Запрос отправлен. Проверьте письмо с подтверждением.')
        } catch (error) { setMessage(errorMessage(error)) }
        finally { setBusy(false) }
    }

    return <div className="mt-6 space-y-4">
        <h2 className="text-xl font-semibold">Подтверждение почты</h2>
        <p>Откройте письмо{email ? ` для ${email}` : ''} и вставьте сюда ссылку или токен подтверждения.</p>
        {import.meta.env.DEV && <p className="text-sm">Локальные письма: <a href="http://localhost:8025" target="_blank" rel="noreferrer" className="text-purple-700 underline">открыть Mailpit</a>.</p>}
        <form onSubmit={e => { e.preventDefault(); verify(token) }} className="space-y-3">
            <label className="block">Ссылка или токен
                <input required value={token} onChange={e => setToken(e.target.value)} disabled={busy} className="mt-1 w-full rounded-lg border p-3" />
            </label>
            <button disabled={busy} className="rounded-lg bg-purple-600 p-3 text-white disabled:opacity-50">{busy ? 'Отправляем…' : 'Подтвердить почту'}</button>
        </form>
        {import.meta.env.DEV && devToken && <button type="button" disabled={busy} onClick={() => verify(devToken)} className="text-purple-700 underline">Подтвердить токеном, который сервер вернул для разработки</button>}
        <form onSubmit={resend} className="space-y-3">
            <label className="block">Почта для повторного письма
                <input type="email" required autoComplete="email" value={address} onChange={e => setAddress(e.target.value)} disabled={busy} className="mt-1 w-full rounded-lg border p-3" />
            </label>
            <button disabled={busy} className="text-purple-700 underline">Отправить письмо повторно</button>
        </form>
        {message && <p role="status" className="rounded-lg bg-gray-100 p-3">{message}</p>}
        <button type="button" disabled={busy} onClick={onBack} className="text-purple-700 underline">Перейти ко входу</button>
    </div>
}
