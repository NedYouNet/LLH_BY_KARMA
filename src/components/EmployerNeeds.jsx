// Подключаем состояние и сохранение черновика.
import { useState, useEffect } from 'react'
import EmployerCandidates from './EmployerCandidates'
// Специализации совпадают со списком в опросе кандидата.
const specializations = [
    'Frontend-разработка',
    'Backend-разработка',
    'Аналитика данных',
    'Тестирование ПО',
]

// Уровни специалистов.
const grades = ['Junior', 'Middle', 'Senior']

// Начальные значения формы.
const emptyNeeds = {
    specialization: '',
    grade: '',
    stack: '',
    description: '',
}

// Восстанавливаем ранее заполненную потребность.
function readSavedNeeds() {
    try {
        const saved = localStorage.getItem('employerNeeds')
        const data = saved ? JSON.parse(saved) : {}

        return {
            // Проверяем, что сохранённые значения есть в наших списках.
            specialization: specializations.includes(data?.specialization)
                ? data.specialization
                : '',
            grade: grades.includes(data?.grade) ? data.grade : '',

            // Текстовые поля восстанавливаем только из строк.
            stack: typeof data?.stack === 'string' ? data.stack : '',
            description: typeof data?.description === 'string'
                ? data.description
                : '',
        }
    } catch {
        return { ...emptyNeeds }
    }
}

export default function EmployerNeeds() {
    // Храним поля формы в одном объекте.
    const [needs, setNeeds] = useState(readSavedNeeds)

    // Храним сообщение о проверке.
    const [message, setMessage] = useState('')
    // Здесь храним требования, по которым уже выполнен подбор.
    const [appliedNeeds, setAppliedNeeds] = useState(null)
    // Сохраняем черновик после изменений.
    useEffect(() => {
        try {
            localStorage.setItem('employerNeeds', JSON.stringify(needs))
        } catch {
            console.warn('Не удалось сохранить потребность компании.')
        }
    }, [needs])

    // Обновляем поле по его атрибуту name.
    function handleChange(event) {
        const { name, value } = event.target

        setNeeds((previous) => ({
            ...previous,
            [name]: value,
        }))

        // Сбрасываем сообщение после редактирования.
        setMessage('')
    }

    // Проверяем заполнение формы.
    function handleSubmit(event) {
        event.preventDefault()

        if (!needs.specialization || !needs.grade) {
            setMessage('Выберите специализацию и грейд.')
            return
        }

        if (!needs.stack.trim()) {
            setMessage('Укажите требуемые технологии.')
            return
        }

        if (!needs.description.trim()) {
            setMessage('Опишите задачи и команду.')
            return
        }

        // Фиксируем требования для подборки.
        setAppliedNeeds({ ...needs })

        // Убираем прежнее сообщение.
        setMessage('')
    }

    return (
        <section className="mt-8 border-t border-gray-200 pt-6">
            <h2 className="text-xl font-bold">Кого ищет компания</h2>

            <p className="mt-2 text-gray-600">
                Укажите требования к специалисту и задачи вашей команды.
            </p>

            <form noValidate onSubmit={handleSubmit} className="mt-4 space-y-4">
                <label className="block">
                    <span className="mb-1 block">Специализация</span>

                    {/* Создаём список специализаций. */}
                    <select
                        name="specialization"
                        value={needs.specialization}
                        onChange={handleChange}
                        className="w-full rounded-lg border border-gray-300 bg-white p-3"
                    >
                        <option value="">Выберите специализацию</option>

                        {specializations.map((item) => (
                            <option key={item} value={item}>{item}</option>
                        ))}
                    </select>
                </label>

                <label className="block">
                    <span className="mb-1 block">Требуемый грейд</span>

                    <select
                        name="grade"
                        value={needs.grade}
                        onChange={handleChange}
                        className="w-full rounded-lg border border-gray-300 bg-white p-3"
                    >
                        <option value="">Выберите грейд</option>

                        {grades.map((item) => (
                            <option key={item} value={item}>{item}</option>
                        ))}
                    </select>
                </label>

                <label className="block">
                    <span className="mb-1 block">Требуемые технологии</span>

                    {/* Пока вводим стек текстом через запятую. */}
                    <input
                        type="text"
                        name="stack"
                        placeholder="Например: React, JavaScript, Git"
                        value={needs.stack}
                        onChange={handleChange}
                        className="w-full rounded-lg border border-gray-300 p-3"
                    />
                </label>

                <label className="block">
                    <span className="mb-1 block">Задачи и команда</span>

                    <textarea
                        name="description"
                        rows={5}
                        placeholder="Чем занимается команда и что предстоит делать специалисту"
                        value={needs.description}
                        onChange={handleChange}
                        className="w-full rounded-lg border border-gray-300 p-3"
                    />
                </label>

                {/* Запускаем проверку формы без отправки на сервер. */}
                <button
                    type="submit"
                    className="rounded-lg bg-purple-600 px-6 py-3 text-white hover:bg-purple-700 cursor-pointer"
                >
                    Подобрать кандидатов
                </button>

                {message && (
                    <p role="status" className="rounded-lg bg-gray-100 p-3 text-gray-800">
                        {message}
                    </p>
                )}
            </form>
            {/* Показываем подборку после успешной проверки требований. */}
            {appliedNeeds && (
                <EmployerCandidates needs={appliedNeeds} />
            )}
        </section>
    )
}