// Подключаем состояние и сохранение при изменении данных.
import { useState, useEffect } from 'react'

// Начальные значения полей.
const emptyProfile = {
    companyName: '',
    description: '',
    industry: '',
    contact: '',
}

// Читаем сохранённый черновик компании.
function readSavedProfile() {
    try {
        const saved = localStorage.getItem('employerProfile')
        const data = saved ? JSON.parse(saved) : {}

        // Восстанавливаем только текстовые поля, которые есть в нашей форме.
        return Object.fromEntries(
            Object.keys(emptyProfile).map((key) => [
                key,
                typeof data?.[key] === 'string' ? data[key] : '',
            ])
        )
    } catch {
        // При ошибке открываем пустую форму.
        return { ...emptyProfile }
    }
}

export default function EmployerProfile() {
    // Храним все поля компании в одном объекте.
    const [profile, setProfile] = useState(readSavedProfile)

    // Храним результат проверки формы.
    const [message, setMessage] = useState('')

    // Сохраняем черновик при изменении профиля.
    useEffect(() => {
        try {
            localStorage.setItem('employerProfile', JSON.stringify(profile))
        } catch {
            console.warn('Не удалось сохранить черновик компании.')
        }
    }, [profile])

    // Общий обработчик для всех полей формы.
    function handleChange(event) {
        // name определяет поле, value содержит введённый текст.
        const { name, value } = event.target

        // Копируем прежний профиль и меняем нужное поле.
        setProfile((previous) => ({
            ...previous,
            [name]: value,
        }))

        // Убираем сообщение после редактирования.
        setMessage('')
    }

    // Проверяем заполнение формы.
    function handleSubmit(event) {
        // Предотвращаем перезагрузку страницы.
        event.preventDefault()

        if (!profile.companyName.trim()) {
            setMessage('Введите название компании.')
            return
        }

        if (!profile.description.trim()) {
            setMessage('Добавьте описание компании.')
            return
        }

        if (!profile.industry.trim()) {
            setMessage('Укажите направление деятельности.')
            return
        }

        if (!profile.contact.trim()) {
            setMessage('Укажите способ связи с компанией.')
            return
        }

        // Проверка пока выполняется без отправки на сервер.
        setMessage('Поля заполнены. Черновик хранится в браузере; отправка на сервер ещё не подключена.')
    }

    return (
        <section className="mt-6">
            {/* Заголовок профиля. */}
            <h2 className="text-xl font-bold">Профиль компании</h2>

            <p className="mt-2 text-gray-600">
                Расскажите о компании и укажите, как с вами связаться.
            </p>

            {/* Все поля используют один обработчик handleChange. */}
            <form noValidate onSubmit={handleSubmit} className="mt-4 space-y-4">
                <label className="block">
                    <span className="mb-1 block">Название компании</span>

                    <input
                        type="text"
                        name="companyName"
                        autoComplete="organization"
                        placeholder="Например: ТехноКоманда"
                        value={profile.companyName}
                        onChange={handleChange}
                        className="w-full rounded-lg border border-gray-300 p-3"
                    />
                </label>

                <label className="block">
                    <span className="mb-1 block">Описание компании</span>

                    <textarea
                        name="description"
                        rows={5}
                        placeholder="Что вы создаёте, кто ваши клиенты и как устроена команда"
                        value={profile.description}
                        onChange={handleChange}
                        className="w-full rounded-lg border border-gray-300 p-3"
                    />
                </label>

                <label className="block">
                    <span className="mb-1 block">Направление деятельности</span>

                    <input
                        type="text"
                        name="industry"
                        placeholder="Например: разработка ПО для банков"
                        value={profile.industry}
                        onChange={handleChange}
                        className="w-full rounded-lg border border-gray-300 p-3"
                    />
                </label>

                <label className="block">
                    <span className="mb-1 block">Способ связи</span>

                    <input
                        type="text"
                        name="contact"
                        placeholder="Рабочая почта, телефон или Telegram"
                        value={profile.contact}
                        onChange={handleChange}
                        className="w-full rounded-lg border border-gray-300 p-3"
                    />
                </label>

                {/* Запускаем проверку обязательных полей. */}
                <button
                    type="submit"
                    className="rounded-lg bg-purple-600 px-6 py-3 text-white hover:bg-purple-700 cursor-pointer"
                >
                    Проверить профиль
                </button>

                {/* Показываем результат проверки. */}
                {message && (
                    <p role="status" className="rounded-lg bg-gray-100 p-3 text-gray-800">
                        {message}
                    </p>
                )}
            </form>
        </section>
    )
}