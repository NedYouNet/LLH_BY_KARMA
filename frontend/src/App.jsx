import { useEffect, useState } from 'react'
import { auth, fspId, errorMessage, isLoggedIn } from './api'
import RoleSelector from './components/RoleSelector'
import RegistrationForm from './components/RegistrationForm'
import LoginForm from './components/LoginForm'
import EmailVerification from './components/EmailVerification'
import CandidateProfile from './components/CandidateProfile'
import CandidateQuestionnaire from './components/CandidateQuestionnaire'
import CandidateInvitations from './components/CandidateInvitations'
import EmployerProfile from './components/EmployerProfile'
import EmployerNeeds from './components/EmployerNeeds'
import CandidateSettings from './components/CandidateSettings'
import CandidateOverview from './components/CandidateOverview'
import FspIdLogin from './components/FspIdLogin'
import EmployerIntegrations from './components/EmployerIntegrations'
import './App.css'

const linkToken = new URLSearchParams(window.location.search).get('token') || ''
const invitationLink = window.location.pathname === '/candidate/invitations'
// Выполняем один раз при загрузке модуля, чтобы StrictMode не прочитал callback дважды.
let fspReturn = null
let fspReturnError = ''
if (window.location.pathname === '/auth/fsp-id') {
    try { fspReturn = fspId.completeLogin() }
    catch (error) { fspReturnError = errorMessage(error) }
    window.history.replaceState(null, '', '/')
}
let landingPending = true
function accountScreen(user) {
    const useLanding = landingPending
    landingPending = false
    if (user.role === 'employer') return 'company'
    if (useLanding && invitationLink) return 'invitations'
    return useLanding && fspReturn?.created ? 'survey' : 'overview'
}
const buttonClass = 'rounded-lg bg-purple-100 px-4 py-2 text-purple-800 hover:bg-purple-200 disabled:opacity-50'

export default function App() {
    const [account, setAccount] = useState(null)
    const [role, setRole] = useState('')
    const [screen, setScreen] = useState(linkToken ? 'verification' : 'login')
    const [pending, setPending] = useState({ email: '', devToken: '' })
    const [notice, setNotice] = useState(fspReturn ? 'Вход через FSP ID выполнен. Проверьте профиль и отдельно сохраните согласия в разделе «Согласия и ФСП».' : '')
    const [sessionError, setSessionError] = useState(fspReturnError)
    const [checking, setChecking] = useState(isLoggedIn)
    const [leaving, setLeaving] = useState(false)
    const [retry, setRetry] = useState(0)

    useEffect(() => {
        let active = true
        let generation = 0
        async function restore() {
            const attempt = ++generation
            if (!isLoggedIn()) {
                setAccount(null)
                setChecking(false)
                return
            }
            setChecking(true)
            setSessionError(fspReturnError)
            try {
                const result = await auth.me()
                if (active && attempt === generation) {
                    setAccount(result.user)
                    setScreen(accountScreen(result.user))
                }
            } catch (error) {
                if (active && attempt === generation) setSessionError(errorMessage(error))
            } finally {
                if (active && attempt === generation) setChecking(false)
            }
        }
        function reset() {
            ++generation
            setAccount(null)
            setScreen('login')
            setChecking(false)
            setSessionError('')
            setNotice('Сессия завершена. Войдите снова.')
        }
        function sync(event) {
            if (event.key === 'fsp.auth' || event.key === null) {
                if (isLoggedIn()) restore()
                else reset()
            }
        }
        window.addEventListener('fsp:logout', reset)
        window.addEventListener('storage', sync)
        restore()
        return () => {
            active = false
            window.removeEventListener('fsp:logout', reset)
            window.removeEventListener('storage', sync)
        }
    }, [retry])

    async function handleLogin() {
        const result = await auth.me()
        setAccount(result.user)
        setScreen(accountScreen(result.user))
        setNotice('')
        setSessionError('')
    }

    async function handleLogout() {
        if (leaving) return
        setLeaving(true)
        try { await auth.logout() }
        finally {
            setAccount(null)
            setScreen('login')
            setNotice('Вы вышли из аккаунта.')
            setLeaving(false)
        }
    }

    function handleRegistered(result) {
        setPending({ email: result.email, devToken: result.dev_verification_token || '' })
        setNotice(result.message || 'Аккаунт создан.')
        setScreen(result.verification_required ? 'verification' : 'login')
    }

    function verified(email) {
        setPending({ email, devToken: '' })
        setScreen('login')
        setNotice('Почта подтверждена. Теперь войдите в аккаунт.')
        const url = new URL(window.location.href)
        url.searchParams.delete('token')
        window.history.replaceState(null, '', url.pathname + url.search + url.hash)
    }

    return <main className="min-h-screen bg-gray-100 p-4 sm:p-8 flex items-center justify-center">
        <section className="w-full max-w-4xl rounded-2xl bg-white p-8 shadow-md">
            <h1 className="text-3xl font-bold text-purple-600">Карьерная платформа ФСП</h1>
            {checking ? <p className="mt-6" role="status">Проверяем сессию…</p> : <>
                {notice && <p role="status" className="mt-4 rounded-lg bg-purple-50 p-3">{notice}</p>}
                {sessionError && <div role="alert" className="mt-4 space-y-3 rounded-lg bg-red-50 p-3">
                    <p>{sessionError}</p>
                    <button className={buttonClass} onClick={() => setRetry(value => value + 1)}>Повторить подключение</button>
                </div>}
                {!account ? <>
                    <nav aria-label="Вход и регистрация" className="mt-6 flex gap-3">
                        <button className={buttonClass} aria-pressed={screen === 'login'} onClick={() => { setScreen('login'); setNotice('') }}>Вход</button>
                        <button className={buttonClass} aria-pressed={screen === 'registration'} onClick={() => { setScreen('registration'); setNotice('') }}>Регистрация</button>
                    </nav>
                    {screen === 'registration' && <>
                        <RoleSelector role={role} onRoleChange={setRole} />
                        {role && <RegistrationForm key={role} role={role} onRegistered={handleRegistered} />}
                    </>}
                    {screen === 'login' && <LoginForm key={pending.email} initialEmail={pending.email} onLoggedIn={handleLogin} onVerify={email => { setPending({ email, devToken: '' }); setScreen('verification') }} />}
                    {['login', 'registration'].includes(screen) && <FspIdLogin />}
                    {screen === 'verification' && <EmailVerification email={pending.email} devToken={pending.devToken} initialToken={linkToken} onVerified={verified} onBack={() => setScreen('login')} />}
                </> : <div key={account.id}>
                    <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
                        <p>{account.email} · {account.role === 'candidate' ? 'Кандидат' : 'Работодатель'}</p>
                        <button disabled={leaving} className={buttonClass} onClick={handleLogout}>{leaving ? 'Выходим…' : 'Выйти'}</button>
                    </div>
                    {account.role === 'candidate' && <>
                        <nav aria-label="Экраны кандидата" className="mt-6 flex flex-wrap gap-3">
                            {Object.entries({ overview: 'Моя категория', profile: 'Профиль', survey: 'Анкета и тест', invitations: 'Приглашения', settings: 'Согласия и ФСП' }).map(([key, label]) => <button key={key} className={buttonClass} aria-pressed={screen === key} onClick={() => setScreen(key)}>{label}</button>)}
                        </nav>
                        {screen === 'overview' && <CandidateOverview onNavigate={setScreen} />}
                        {screen === 'profile' && <CandidateProfile />}
                        {screen === 'survey' && <CandidateQuestionnaire />}
                        {screen === 'invitations' && <CandidateInvitations />}
                        {screen === 'settings' && <CandidateSettings />}
                    </>}
                    {account.role === 'employer' && <>
                        <nav aria-label="Экраны работодателя" className="mt-6 flex flex-wrap gap-3">
                            {Object.entries({ company: 'Компания', needs: 'Потребности и подбор', invitations: 'Приглашения', integrations: 'Интеграции' }).map(([key, label]) => <button key={key} className={buttonClass} aria-pressed={screen === key} onClick={() => setScreen(key)}>{label}</button>)}
                        </nav>
                        {screen === 'company' && <EmployerProfile />}
                        {screen === 'needs' && <EmployerNeeds />}
                        {screen === 'integrations' && <EmployerIntegrations />}
                        {screen === 'invitations' && <CandidateInvitations role="employer" />}
                    </>}
                </div>}
            </>}
        </section>
    </main>
}
