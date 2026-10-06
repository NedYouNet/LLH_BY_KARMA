// Подключаем состояние и выполнение действий после изменения состояния.
import { useState, useEffect } from 'react'
import CandidateQuestionnaire from './components/CandidateQuestionnaire'
// Подключаем наши компоненты.
import RoleSelector from './components/RoleSelector'
import RegistrationForm from './components/RegistrationForm'
import CandidateProfile from './components/CandidateProfile'
import EmailVerification from './components/EmailVerification'
// Подключаем стили приложения.
import './App.css'
import CandidateInvitations from './components/CandidateInvitations'
import EmployerProfile from './components/EmployerProfile'
import EmployerNeeds from './components/EmployerNeeds'

export default function App() {
    // Восстанавливаем выбранную роль при открытии приложения.
    const [role, setRole] = useState(() => {
        try {
            // Читаем сохранённое значение.
            const savedRole = localStorage.getItem('selectedRole')

            // Разрешаем только роли, которые есть в приложении.
            return ['Кандидат', 'Работодатель'].includes(savedRole)
                ? savedRole
                : ''
        } catch {
            // Если чтение не удалось, начинаем без выбранной роли.
            return ''
        }
    })

    // Запоминаем, какой экран сейчас открыт.
    const [screen, setScreen] = useState('registration')
    // Храним адрес, который покажем на экране подтверждения.
    const [pendingEmail, setPendingEmail] = useState('')
    // Сохраняем выбранную роль при её изменении.
    useEffect(() => {
        try {
            localStorage.setItem('selectedRole', role)
        } catch {
            console.warn('Не удалось сохранить выбранную роль.')
        }
    }, [role])

    // Эта функция вызывается при выборе роли.
    function handleRoleChange(nextRole) {
        // Устанавливаем новую роль.
        setRole(nextRole)

        // Возвращаемся на экран регистрации.
        setScreen('registration')
    }
    // Вызывается, когда форма регистрации прошла проверку.
    function handleRegistrationValidated(email) {
        // Запоминаем адрес из формы.
        setPendingEmail(email)

        // Переключаем приложение на экран подтверждения.
        setScreen('verification')
    }
    return (
        // Создаём фон страницы и размещаем содержимое по центру.
        <main className="min-h-screen bg-gray-100 p-8 flex items-center justify-center">
            {/* Создаём белую карточку приложения. */}
            <section className="w-full max-w-xl rounded-2xl bg-white p-8 shadow-md">
                {/* Показываем название платформы. */}
                <h1 className="text-3xl font-bold text-purple-600">
                    Карьерная платформа ФСП
                </h1>

                {/* Передаём выбор роли в отдельный компонент. */}
                <RoleSelector
                    role={role}
                    onRoleChange={handleRoleChange}
                />

                {/* Переключение экранов пока доступно для кандидата. */}
                {role === 'Кандидат' && (
                    <nav aria-label="Экраны кандидата" className="mt-6 flex flex-wrap gap-3">
                        {/* Кнопка открывает форму регистрации. */}
                        <button
                            type="button"
                            onClick={() => setScreen('registration')}
                            aria-pressed={screen === 'registration'}
                            className={`rounded-lg px-4 py-2 cursor-pointer ${
                                screen === 'registration'
                                    ? 'bg-purple-600 text-white'
                                    : 'bg-purple-100 text-purple-800 hover:bg-purple-200'
                            }`}
                        >
                            Регистрация
                        </button>

                        {/* Кнопка открывает черновик профиля. */}
                        <button
                            type="button"
                            onClick={() => setScreen('profile')}
                            aria-pressed={screen === 'profile'}
                            className={`rounded-lg px-4 py-2 cursor-pointer ${
                                screen === 'profile'
                                    ? 'bg-purple-600 text-white'
                                    : 'bg-purple-100 text-purple-800 hover:bg-purple-200'
                            }`}
                        >
                            Предпросмотр профиля
                        </button>
                        {/* Открываем входящие приглашения. */}
                        <button
                            type="button"
                            onClick={() => setScreen('invitations')}
                            aria-pressed={screen === 'invitations'}
                            className={`rounded-lg px-4 py-2 cursor-pointer ${
                                screen === 'invitations'
                                    ? 'bg-purple-600 text-white'
                                    : 'bg-purple-100 text-purple-800 hover:bg-purple-200'
                            }`}
                        >
                            Приглашения
                        </button>
                    </nav>
                )}
                {/* Переключение экранов работодателя. */}
                {role === 'Работодатель' && (
                    <nav aria-label="Экраны работодателя" className="mt-6 flex flex-wrap gap-3">
                        <button
                            type="button"
                            onClick={() => setScreen('registration')}
                            aria-pressed={screen === 'registration'}
                            className={`rounded-lg px-4 py-2 cursor-pointer ${
                                screen === 'registration'
                                    ? 'bg-purple-600 text-white'
                                    : 'bg-purple-100 text-purple-800 hover:bg-purple-200'
                            }`}
                        >
                            Регистрация
                        </button>

                        <button
                            type="button"
                            onClick={() => setScreen('company')}
                            aria-pressed={screen === 'company'}
                            className={`rounded-lg px-4 py-2 cursor-pointer ${
                                screen === 'company'
                                    ? 'bg-purple-600 text-white'
                                    : 'bg-purple-100 text-purple-800 hover:bg-purple-200'
                            }`}
                        >
                            Предпросмотр компании
                        </button>
                    </nav>
                )}
                {/* Показываем регистрацию только на её экране. */}
                {role && screen === 'registration' && (
                    <RegistrationForm
                        key={role}
                        role={role}
                        onValidated={handleRegistrationValidated}
                    />
                )}

                {/* После проверки формы показываем экран подтверждения. */}
                {role && screen === 'verification' && (
                    <EmailVerification
                        email={pendingEmail}
                        onBack={() => setScreen('registration')}
                    />
                )}

                {/* Показываем профиль только на экране профиля кандидата. */}
                {role === 'Кандидат' && screen === 'profile' && (
                    <>
                        {/* Сначала показываем поля профиля. */}
                        <CandidateProfile />

                        {/* Ниже показываем опрос перед тестированием. */}
                        <CandidateQuestionnaire />
                    </>
                )}
                {/* Показываем приглашения только на соответствующем экране кандидата. */}
                {role === 'Кандидат' && screen === 'invitations' && (
                    <CandidateInvitations />
                )}

                {role === 'Работодатель' && screen === 'company' && (
                    <>
                        {/* Сначала информация о компании. */}
                        <EmployerProfile />

                        {/* Ниже требования к специалисту. */}
                        <EmployerNeeds />
                    </>
                )}
            </section>
        </main>
    )
}