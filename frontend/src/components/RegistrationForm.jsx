import { useState } from 'react'
import { auth, errorMessage, roleToApi } from '../api'

export default function RegistrationForm({ role, onRegistered }) {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [consent, setConsent] = useState(false)
    const [message, setMessage] = useState('')
    const [busy, setBusy] = useState(false)

    async function handleSubmit(event) {
        event.preventDefault()
        if (busy) return
        if (!consent) { setMessage('Подтвердите согласие на обработку персональных данных.'); return }
        setBusy(true)
        setMessage('')
        try {
            const result = await auth.register({
                email: email.trim(), password, role: roleToApi(role), consent_processing: consent,
            })
            setPassword('')
            onRegistered(result)
        } catch (error) { setMessage(errorMessage(error)) }
        finally { setBusy(false) }
    }

    return <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <fieldset disabled={busy} className="space-y-4">
            <label className="block">Электронная почта
                <input type="email" required autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} className="mt-1 w-full rounded-lg border p-3" />
            </label>
            <label className="block">Пароль
                <input type="password" required minLength={8} maxLength={128} autoComplete="new-password" value={password} onChange={e => setPassword(e.target.value)} className="mt-1 w-full rounded-lg border p-3" />
                <span className="text-sm text-gray-600">От 8 до 128 символов</span>
            </label>
            <label className="flex items-start gap-2">
                <input type="checkbox" required checked={consent} onChange={e => setConsent(e.target.checked)} className="mt-1" />
                <span>Даю согласие на обработку персональных данных</span>
            </label>
            <button type="submit" className="w-full rounded-lg bg-purple-600 p-3 text-white disabled:opacity-50">{busy ? 'Создаём аккаунт…' : 'Зарегистрироваться'}</button>
        </fieldset>
        {message && <p role="alert" className="rounded-lg bg-red-50 p-3 text-red-800">{message}</p>}
    </form>
}
