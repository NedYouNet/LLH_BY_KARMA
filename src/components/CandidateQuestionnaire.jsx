// Подключаем состояние и автоматическое сохранение.
import { useState, useEffect } from 'react'
import CandidateTest from './CandidateTest'
// Список отраслей для нашего прототипа.
const industries = [
    'Информационные технологии',
    'Финансы и банковские услуги',
    'Розничная торговля и электронная коммерция',
    'Другое',
]

// Основные специализации для MVP.
const specializations = [
    'Frontend-разработка',
    'Backend-разработка',
    'Аналитика данных',
    'Тестирование ПО',
]

// Уровни, которые кандидат может выбрать перед тестом.
const grades = ['Junior', 'Middle', 'Senior']

// Читаем предыдущий выбор из браузера.
function readSavedQuestionnaire() {
    try {
        // Получаем сохранённый текст.
        const saved = localStorage.getItem('candidateQuestionnaire')

        // Превращаем его в объект.
        const data = saved ? JSON.parse(saved) : {}

        // Используем только объект с данными.
        return data && typeof data === 'object' ? data : {}
    } catch {
        // При ошибке открываем пустой опрос.
        return {}
    }
}

export default function CandidateQuestionnaire() {
    // Читаем сохранённые данные один раз при открытии компонента.
    const [saved] = useState(readSavedQuestionnaire)

    // Восстанавливаем отрасль, если она есть в нашем списке.
    const [industry, setIndustry] = useState(
        () => industries.includes(saved.industry) ? saved.industry : ''
    )

    // Восстанавливаем специализацию.
    const [specialization, setSpecialization] = useState(
        () => specializations.includes(saved.specialization)
            ? saved.specialization
            : ''
    )

    // Восстанавливаем предполагаемый уровень.
    const [grade, setGrade] = useState(
        () => grades.includes(saved.grade) ? saved.grade : ''
    )

    // Храним сообщение о результате проверки.
    const [message, setMessage] = useState('')

    // Сохраняем выбор после изменения любого поля.
    useEffect(() => {
        try {
            // Собираем ответы и превращаем объект в текст.
            const answers = JSON.stringify({ industry, specialization, grade })

            // Записываем ответы в браузер.
            localStorage.setItem('candidateQuestionnaire', answers)
        } catch {
            console.warn('Не удалось сохранить ответы опроса.')
        }
    }, [industry, specialization, grade])
    // null означает, что тест ещё не открыт.
    // При переходе сюда запишем выбранное направление.
    const [testSelection, setTestSelection] = useState(null)
    // Проверяем заполнение при нажатии кнопки.
    function handleSubmit(event) {
        // Предотвращаем перезагрузку страницы.
        event.preventDefault()

        // Проверяем, что выбраны все три значения.
        if (!industry || !specialization || !grade) {
            setMessage('Выберите отрасль, специализацию и предполагаемый грейд.')
            return
        }

        // Запоминаем выбранные параметры и открываем экран теста.
        setTestSelection({ industry, specialization, grade })
    }
    // Если направление для теста выбрано, показываем тест вместо опроса.
    if (testSelection) {
        return (
            <CandidateTest
                selection={testSelection}
                onBack={() => setTestSelection(null)}
            />
        )
    }
    return (
        <section className="mt-8 border-t border-gray-200 pt-6">
            {/* Название нового раздела. */}
            <h2 className="text-xl font-bold">Направление и уровень</h2>

            {/* Объясняем, что выбранный уровень ещё не подтверждён. */}
            <p className="mt-2 text-gray-600">
                Выберите интересующую отрасль, специализацию и свой предполагаемый
                уровень. Подтверждённая категория появится после тестирования.
            </p>

            {/* Проверку выполняет наша функция handleSubmit. */}
            <form noValidate onSubmit={handleSubmit} className="mt-4 space-y-4">
                <label className="block">
                    <span className="mb-1 block">В какой отрасли хотите работать?</span>

                    {/* select создаёт выпадающий список. */}
                    <select
                        value={industry}
                        onChange={(event) => {
                            setIndustry(event.target.value)
                            setMessage('')
                        }}
                        className="w-full rounded-lg border border-gray-300 bg-white p-3"
                    >
                        <option value="">Выберите отрасль</option>

                        {/* Для каждой отрасли создаём отдельный пункт списка. */}
                        {industries.map((item) => (
                            <option key={item} value={item}>{item}</option>
                        ))}
                    </select>
                </label>

                <label className="block">
                    <span className="mb-1 block">Ваша специализация</span>

                    <select
                        value={specialization}
                        onChange={(event) => {
                            setSpecialization(event.target.value)
                            setMessage('')
                        }}
                        className="w-full rounded-lg border border-gray-300 bg-white p-3"
                    >
                        <option value="">Выберите специализацию</option>

                        {specializations.map((item) => (
                            <option key={item} value={item}>{item}</option>
                        ))}
                    </select>
                </label>

                <label className="block">
                    <span className="mb-1 block">Предполагаемый грейд</span>

                    <select
                        value={grade}
                        onChange={(event) => {
                            setGrade(event.target.value)
                            setMessage('')
                        }}
                        className="w-full rounded-lg border border-gray-300 bg-white p-3"
                    >
                        <option value="">Выберите грейд</option>

                        {grades.map((item) => (
                            <option key={item} value={item}>{item}</option>
                        ))}
                    </select>
                </label>

                {/* Показываем текущий выбор, не называя его подтверждённым. */}
                {specialization && grade && (
                    <p className="rounded-lg bg-purple-50 p-3 text-purple-800">
                        Ваш выбор: {specialization}, {grade}.
                        Статус: уровень не подтверждён тестом.
                    </p>
                )}

                <button
                    type="submit"
                    className="rounded-lg bg-purple-600 px-6 py-3 text-white hover:bg-purple-700 cursor-pointer"
                >
                    Перейти к учебному тесту
                </button>

                {/* Здесь появляется результат проверки формы. */}
                {message && (
                    <p role="status" className="rounded-lg bg-gray-100 p-3 text-gray-800">
                        {message}
                    </p>
                )}
            </form>
        </section>
    )
}