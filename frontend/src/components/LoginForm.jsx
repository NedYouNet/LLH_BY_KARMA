import { useState } from 'react'
import { auth, errorMessage } from '../api'

export default function LoginForm({ initialEmail = '', onLoggedIn, onVerify }) {
    const [email, setEmail] = useState(initialEmail)
    const [password, setPassword] = useState('')
    const [message, setMessage] = useState('')
    const [needsVerification, setNeedsVerification] = useState(false)
    const [busy, setBusy] = useState(false)

    async function handleSubmit(event) {
        event.preventDefault()
        if (busy) return
        setBusy(true)
        setMessage('')
        setNeedsVerification(false)
        try {
            await auth.login(email.trim(), password)
            setPassword('')
            await onLoggedIn()
        } catch (error) {
            setMessage(errorMessage(error))
            setNeedsVerification(error.code === 'EMAIL_NOT_VERIFIED')
        } finally { setBusy(false) }
    }

    async function demoLogin(email) {
        if (busy) return
        setBusy(true); setMessage('')
        try { await auth.login(email, 'demo12345'); await onLoggedIn() }
        catch (error) { setMessage(errorMessage(error)) }
        finally { setBusy(false) }
    }

    return <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <fieldset disabled={busy} className="space-y-4">
            <label className="block">Электронная почта
                <input type="email" required autoComplete="username" value={email} onChange={e => { setEmail(e.target.value); setNeedsVerification(false) }} className="mt-1 w-full rounded-lg border p-3" />
            </label>
            <label className="block">Пароль
                <input type="password" required autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} className="mt-1 w-full rounded-lg border p-3" />
            </label>
            <button type="submit" className="w-full rounded-lg bg-purple-600 p-3 text-white disabled:opacity-50">{busy ? 'Входим…' : 'Войти'}</button>
        </fieldset>
        {import.meta.env.DEV && <div className="flex flex-wrap gap-2">
            {Object.entries({ 'candidate@demo.ru': 'Кандидат (демо)', 'newbie@demo.ru': 'Новичок (демо)', 'employer@demo.ru': 'Работодатель (демо)' }).map(([email, label]) => <button key={email} type="button" disabled={busy} onClick={() => demoLogin(email)} className="rounded bg-purple-100 px-3 py-2 text-purple-800">{label}</button>)}
        </div>}
        {message && <p role="alert" className="rounded-lg bg-red-50 p-3 text-red-800">{message}</p>}
        {needsVerification && <button type="button" onClick={() => onVerify(email.trim())} className="text-purple-700 underline">Подтвердить почту</button>}
    </form>
}
