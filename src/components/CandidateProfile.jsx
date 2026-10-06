// Подключаем состояние React.
import { useState, useEffect } from 'react'
// Читаем ранее сохранённый профиль.
function readSavedProfile() {
    try {
        // Получаем сохранённый текст из браузера.
        const saved = localStorage.getItem('candidateProfile')

        // Превращаем текст JSON в объект с полями профиля.
        const profile = saved ? JSON.parse(saved) : {}

        // Проверяем, что прочитали объект, а не другое значение.
        return profile && typeof profile === 'object' ? profile : {}
    } catch {
        // Если хранилище недоступно или данные повреждены, открываем пустую форму.
        return {}
    }
}
// Создаём компонент профиля кандидата.
export default function CandidateProfile() {
    // Читаем сохранённый профиль один раз при появлении компонента.
    const [savedProfile] = useState(readSavedProfile)

    // Берём сохранённое ФИО; если его нет, используем пустую строку.
    const [fullName, setFullName] = useState(
        () => typeof savedProfile.fullName === 'string' ? savedProfile.fullName : ''
    )

    // Восстанавливаем навыки.
    const [skills, setSkills] = useState(
        () => typeof savedProfile.skills === 'string' ? savedProfile.skills : ''
    )

    // Восстанавливаем телефон.
    const [phone, setPhone] = useState(
        () => typeof savedProfile.phone === 'string' ? savedProfile.phone : ''
    )

    // Восстанавливаем описание опыта.
    const [experience, setExperience] = useState(
        () => typeof savedProfile.experience === 'string' ? savedProfile.experience : ''
    )
    const [message, setMessage] = useState('')
    // Храним контактный телефон.
    const [resumeFile, setResumeFile] = useState(null)
    // Отдельно храним ошибку выбора файла.
    const [fileError, setFileError] = useState('')
    // Выполняем сохранение после изменения любого из четырёх полей.
    useEffect(() => {
        // Собираем текущие значения в один объект.
        const profile = { fullName, skills, phone, experience }

        try {
            // Превращаем объект в текст и сохраняем в браузере.
            localStorage.setItem('candidateProfile', JSON.stringify(profile))
        } catch {
            // Если браузер запретил сохранение, форма продолжит работать.
            console.warn('Не удалось сохранить черновик профиля.')
        }
    }, [fullName, skills, phone, experience]) // За изменениями этих значений следит React.
    // Проверяем заполнение профиля.
    function handleSubmit(event) {
        // Отменяем перезагрузку страницы.
        event.preventDefault()
        // Не принимаем пустое имя или строку из пробелов.
        if (!fullName.trim()) {
            setMessage('Введите ФИО.')
            return
        }
        // Проверяем, что навыки указаны.
        if (!skills.trim()) {
            setMessage('Укажите свои навыки.')
            return
        }
        // Пока только проверяем данные — сохранения на сервере нет.
        setMessage('Данные проверены. Сохранение на сервере ещё не подключено.')
    }
    // Обрабатываем выбор файла.
    function handleFileChange(event) {
        // Получаем первый выбранный файл.
        const file = event.target.files[0]
        // Очищаем предыдущие сообщения.
        setFileError('')
        setMessage('')
        // Если файл не выбран, очищаем состояние.
        if (!file) {
            setResumeFile(null)
            return
        }
        // Проверяем расширение без учёта регистра букв.
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            setFileError('Выберите файл в формате PDF.')
            setResumeFile(null)
            // Сбрасываем неправильный файл в самом поле.
            event.target.value = ''
            return
        }
        // Запоминаем выбранный PDF.
        setResumeFile(file)
    }
    return (
        // Отдельный блок профиля.
        <section className="mt-8 border-t border-gray-200 pt-6">
            {/* Заголовок раздела. */}
            <h2 className="text-xl font-bold">Профиль кандидата</h2>
            {/* Сообщаем, что это предварительная версия экрана. */}
            <p className="mt-2 text-gray-600">
                Пока заполняем форму без сохранения на сервере.
            </p>
            {/* Проверяем форму своим обработчиком. */}
            <form
                noValidate
                onSubmit={handleSubmit}
                className="mt-4 space-y-4"
            >
                {/* Поле ФИО с подписью. */}
                <label className="block">
                    <span className="mb-1 block">ФИО</span>
                    <input
                        type="text"
                        autoComplete="name"
                        value={fullName}
                        onChange={(event) => {
                            setFullName(event.target.value)
                            setMessage('')
                        }}
                        className="w-full rounded-lg border border-gray-300 p-3"
                    />
                </label>

                {/* Многострочное поле для навыков. */}
                <label className="block">
                    <span className="mb-1 block">Навыки</span>

                    <textarea
                        rows={5}
                        placeholder="Например: JavaScript, React, Git"
                        value={skills}
                        onChange={(event) => {
                            setSkills(event.target.value)
                            setMessage('')
                        }}
                        className="w-full rounded-lg border border-gray-300 p-3"
                    />
                </label>
                {/* Телефон необязателен в нашем текущем макете. */}
                <label className="block">
                    <span className="mb-1 block">Телефон</span>

                    <input
                        type="tel"
                        autoComplete="tel"
                        placeholder="+7..."
                        value={phone}
                        onChange={(event) => {
                            setPhone(event.target.value)
                            setMessage('')
                        }}
                        className="w-full rounded-lg border border-gray-300 p-3"
                    />
                </label>

                {/* Описание опыта, включая учебные проекты. */}
                <label className="block">
                    <span className="mb-1 block">Опыт и проекты</span>

                    <textarea
                        rows={5}
                        placeholder="Работа, задачи, учебные проекты"
                        value={experience}
                        onChange={(event) => {
                            setExperience(event.target.value)
                            setMessage('')
                        }}
                        className="w-full rounded-lg border border-gray-300 p-3"
                    />
                </label>

                {/* Поле выбора PDF-резюме. */}
                <label className="block">
                    <span className="mb-1 block">Резюме в PDF</span>

                    <input
                        type="file"
                        accept=".pdf,application/pdf"
                        onChange={handleFileChange}
                        className="block w-full text-sm file:mr-4 file:rounded-lg file:border-0 file:bg-purple-100 file:px-4 file:py-2 file:text-purple-800 file:cursor-pointer"
                    />
                </label>

                {/* Показываем имя выбранного файла. */}
                {resumeFile && (
                    <p className="text-gray-600">
                        Выбран файл: {resumeFile.name}. Отправка пока не подключена.
                    </p>
                )}

                {/* Показываем ошибку выбора файла. */}
                {fileError && (
                    <p role="alert" className="text-red-700">
                        {fileError}
                    </p>
                )}
                {/* Кнопка запускает проверку профиля. */}
                <button
                    type="submit"
                    className="rounded-lg bg-purple-600 px-6 py-3 text-white hover:bg-purple-700 cursor-pointer"
                >
                    Проверить профиль
                </button>

                {/* Показываем результат проверки. */}
                {message && <p role="status">{message}</p>}
            </form>
        </section>
    )
}