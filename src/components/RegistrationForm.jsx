// Подключаем состояние React.
import { useState, useEffect } from 'react'

// Получаем выбранную роль от App.
// onValidated — функция, которую вызовем после проверки формы.
export default function RegistrationForm({ role, onValidated }) {
    // Данные формы храним внутри этого компонента.
    // При открытии формы читаем сохранённую почту для выбранной роли.
    const [email, setEmail] = useState(() => {
        try {
            // Для кандидата и работодателя храним почту отдельно.
            return localStorage.getItem(`registrationEmail:${role}`) || ''
        } catch {
            // Если хранилище недоступно, показываем пустое поле.
            return ''
        }
    })
    const [password, setPassword] = useState('')
    const [consent, setConsent] = useState(false)

    // Сообщение о результате проверки.
    const [message, setMessage] = useState('')
    // Сохраняем почту при изменении поля.
    useEffect(() => {
        try {
            // Записываем текущую почту под ключом выбранной роли.
            localStorage.setItem(`registrationEmail:${role}`, email)
        } catch {
            // Форма продолжит работать, даже если сохранение недоступно.
            console.warn('Не удалось сохранить почту.')
        }
    }, [email, role]) // Запускаем этот блок при изменении почты или роли.
    // Обрабатываем отправку формы.
    function handleSubmit(event) {
        // Предотвращаем перезагрузку страницы.
        event.preventDefault()

        // Убираем пробелы по краям почты.
        const cleanEmail = email.trim()

        // Проверяем формат: текст до @ и домен с точкой после @.
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

        // Проверяем заполнение почты.
        if (!cleanEmail) {
            setMessage('Введите электронную почту.')
            return
        }

        // Проверяем формат почты.
        if (!emailPattern.test(cleanEmail)) {
            setMessage('Укажите почту в формате name@mail.ru.')
            return
        }

        // Проверяем заполнение пароля.
        if (!password) {
            setMessage('Введите пароль.')
            return
        }

        // Проверяем учебное ограничение длины.
        if (password.length < 8) {
            setMessage('Пароль должен содержать минимум 8 символов.')
            return
        }

        // Проверяем согласие.
        if (!consent) {
            setMessage('Подтвердите согласие на обработку персональных данных.')
            return
        }

        // Убираем пробелы по краям почты.
        setEmail(cleanEmail)

    // Очищаем прежнее сообщение.
        setMessage('')

    // Передаём проверенную почту родительскому компоненту App.
        onValidated(cleanEmail)
    }

    return (
        // Используем собственные проверки вместо подсказок браузера.
        <form
            noValidate
            onSubmit={handleSubmit}
            className="mt-6 space-y-4"
        >
            {/* Подпись и поле почты. */}
            <label className="block">
                <span className="mb-1 block">Электронная почта</span>

                {/* Сохраняем текст поля и убираем старое сообщение. */}
                <input
                    type="email"
                    autoComplete="email"
                    required
                    placeholder="name@mail.ru"
                    value={email}
                    onChange={(event) => {
                        setEmail(event.target.value)
                        setMessage('')
                    }}
                    className="w-full rounded-lg border border-gray-300 p-3"
                />
            </label>

            {/* Подпись и поле пароля. */}
            <label className="block">
                <span className="mb-1 block">Пароль</span>

                {/* Скрываем символы и сохраняем введённый пароль. */}
                <input
                    type="password"
                    autoComplete="new-password"
                    required
                    minLength={8}
                    placeholder="Минимум 8 символов"
                    value={password}
                    onChange={(event) => {
                        setPassword(event.target.value)
                        setMessage('')
                    }}
                    className="w-full rounded-lg border border-gray-300 p-3"
                />
            </label>

            {/* Галочка согласия с учебным текстом. */}
            <label className="flex items-start gap-2">
                <input
                    type="checkbox"
                    required
                    checked={consent}
                    onChange={(event) => {
                        setConsent(event.target.checked)
                        setMessage('')
                    }}
                    className="mt-1"
                />

                <span>Даю согласие на обработку персональных данных</span>
            </label>

            {/* Отправка формы вызывает handleSubmit. */}
            <button
                type="submit"
                className="w-full rounded-lg bg-purple-600 px-6 py-3 text-white hover:bg-purple-700 cursor-pointer"
            >
                Проверить форму
            </button>

            {/* Показываем сообщение после проверки. */}
            {message && (
                <p
                    role="status"
                    className="rounded-lg bg-gray-100 p-3 text-gray-800"
                >
                    {message}
                </p>
            )}
        </form>
    )
}