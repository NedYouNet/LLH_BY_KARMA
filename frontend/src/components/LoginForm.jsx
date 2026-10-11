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
        setNeedsVerification(false)
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
        <section aria-labelledby="demo-login-title" className="rounded-xl border border-gray-200 bg-gray-50 p-4 space-y-3">
            <h2 id="demo-login-title" className="font-semibold">Попробовать платформу</h2>
            <p className="text-sm text-gray-600">Войдите в демо-аккаунт без регистрации. Пароль для всех: <code className="font-semibold select-all">demo12345</code>.</p>
            <div className="grid min-w-0 gap-3 sm:grid-cols-3">
                {[
                    ['candidate@demo.ru', 'Кандидат', 'Профиль, результаты теста и приглашения'],
                    ['newbie@demo.ru', 'Новый кандидат', 'Анкета и прохождение теста с нуля'],
                    ['employer@demo.ru', 'Работодатель', 'Вакансии, подбор кандидатов и отклики'],
                ].map(([address, label, description]) => <div key={address} className="min-w-0 rounded-lg border border-gray-200 bg-white p-3 space-y-2">
                    <h3 className="font-medium">{label}</h3>
                    <p className="text-sm text-gray-600">{description}</p>
                    <p className="text-sm break-all"><code className="select-all">{address}</code></p>
                    <button type="button" disabled={busy} onClick={() => demoLogin(address)} className="w-full rounded-lg bg-purple-100 px-3 py-2 text-purple-800 disabled:opacity-50">Войти: {label.toLowerCase()}</button>
                </div>)}
            </div>
        </section>
        {message && <p role="alert" className="rounded-lg bg-red-50 p-3 text-red-800">{message}</p>}
        {needsVerification && <button type="button" onClick={() => onVerify(email.trim())} className="text-purple-700 underline">Подтвердить почту</button>}
    </form>
}
