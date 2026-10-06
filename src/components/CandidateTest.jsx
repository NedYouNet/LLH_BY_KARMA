// Подключаем редактор кода.
import Editor from '@monaco-editor/react'
import { useState, useEffect, useRef } from 'react'
// Подключаем состояние компонента.

// Получаем выбранное направление и функцию возврата к опросу.
export default function CandidateTest({ selection, onBack }) {
    // Храним текст решения и показываем начальную заготовку.
    const [code, setCode] = useState('def solve(numbers):\n    pass')

// Храним сообщение о загрузке, результате или ошибке.
    const [message, setMessage] = useState('')
    // Запоминаем, идёт ли сейчас загрузка или проверка.
    const [isRunning, setIsRunning] = useState(false)

    // Храним запущенный поток и таймер между обновлениями компонента.
    const workerRef = useRef(null)
    const timerRef = useRef(null)

    // При уходе с экрана останавливаем поток и убираем таймер.
    useEffect(() => {
        return () => {
            workerRef.current?.terminate()
            clearTimeout(timerRef.current)
        }
    }, [])
    // Пока проверяем только заполнение поля.
    function handleSubmit(event) {
        // Не перезагружаем страницу.
        event.preventDefault()

        // Не запускаем повторную проверку, пока предыдущая работает.
        if (workerRef.current) return

        // Проверяем, что код введён.
        if (!code.trim()) {
            setMessage('Введите решение.')
            return
        }

        // Показываем состояние загрузки.
        setIsRunning(true)
        setMessage('Загружаем Python… Первый запуск может занять некоторое время.')

        // Эта функция завершает проверку и освобождает ресурсы.
        function finish(text) {
            clearTimeout(timerRef.current)
            workerRef.current?.terminate()
            workerRef.current = null
            setIsRunning(false)
            setMessage(text)
        }

        try {
            // Создаём отдельный поток с нашим файлом.
            const worker = new Worker(
                `${import.meta.env.BASE_URL}python-worker.js`,
                { type: 'module' }
            )

            // Запоминаем поток, чтобы его можно было остановить.
            workerRef.current = worker

            // Ограничиваем ожидание загрузки Python одной минутой.
            timerRef.current = setTimeout(() => {
                finish('Python не загрузился за минуту. Проверьте интернет и повторите.')
            }, 60000)

            // Обрабатываем сообщения от потока.
            worker.onmessage = (workerEvent) => {
                const data = workerEvent.data

                if (data.type === 'ready') {
                    // Загрузка закончилась — убираем таймер загрузки.
                    clearTimeout(timerRef.current)

                    setMessage('Проверяем решение…')

                    // На выполнение учебного решения даём три секунды.
                    timerRef.current = setTimeout(() => {
                        finish('Выполнение остановлено: превышено время. Проверьте циклы.')
                    }, 3000)

                    // Отправляем текущий код в поток.
                    worker.postMessage({ code })
                } else if (data.type === 'result') {
                    // Показываем количество пройденных примеров.
                    finish(
                        `Пройдено проверок: ${data.passed} из ${data.total}. Это учебный результат, грейд не подтверждён.`
                    )
                } else if (data.type === 'error') {
                    // Показываем ошибку загрузки или выполнения.
                    finish(data.message)
                }
            }

            // Обрабатываем ошибку самого потока.
            worker.onerror = () => {
                finish('Не удалось запустить Python. Проверьте интернет и повторите.')
            }
        } catch {
            finish('Не удалось создать поток для запуска Python.')
        }
    }

    return (
        <section className="mt-8 border-t border-gray-200 pt-6">
            {/* Заголовок экрана. */}
            <h2 className="text-xl font-bold">Тестирование</h2>

            {/* Показываем направление, выбранное в опросе. */}
            <p className="mt-2 text-gray-600">
                {selection.specialization} · {selection.grade}
            </p>

            {/* Обозначаем, что это пример для разработки интерфейса. */}
            <p className="mt-4 rounded-lg bg-purple-50 p-3 text-purple-800">
                Учебный пример. Это задание не используется для подтверждения грейда.
            </p>

            {/* Отображаем условие задания. */}
            <div className="mt-4 rounded-lg border border-gray-200 p-4">
                <h3 className="font-bold">Сумма положительных чисел</h3>

                <p className="mt-2">
                    Напишите функцию solve(numbers), которая принимает список целых
                    чисел и возвращает сумму чисел больше нуля.
                </p>

                {/* pre сохраняет пробелы и переносы строк. */}
                <pre className="mt-3 overflow-x-auto rounded-lg bg-gray-100 p-3">
          {'Вход: [3, -2, 0, 5]\nРезультат: 8'}
        </pre>
            </div>

            {/* Подключаем обработчик формы. */}
            <form onSubmit={handleSubmit} className="mt-4 space-y-4">
                <div>
                    {/* Подпись над редактором. */}
                    <p className="mb-2">Решение на Python</p>

                    {/* Рамка вокруг редактора. */}
                    <div className="overflow-hidden rounded-lg border border-gray-300">
                        <Editor
                            // Высота области редактирования.
                            height="300px"

                            // Включаем подсветку синтаксиса Python.
                            language="python"

                            // Выбираем тёмное оформление.
                            theme="vs-dark"

                            // Передаём текущий код из состояния React.
                            value={code}

                            // Показываем сообщение во время загрузки редактора.
                            loading={<p className="p-4">Загружаем редактор…</p>}

                            // Monaco передаёт новый текст напрямую, без event.target.
                            onChange={(value) => {
                                // Если значение отсутствует, используем пустую строку.
                                setCode(value ?? '')

                                // Убираем предыдущее сообщение.
                                setMessage('')
                            }}

                            // Настраиваем внешний вид и отступы.
                            options={{
                                // Скрываем миниатюру всего кода справа.
                                minimap: { enabled: false },

                                // Устанавливаем размер текста.
                                fontSize: 14,

                                // Используем четыре пробела для отступа.
                                tabSize: 4,

                                // Вставляем пробелы при нажатии Tab.
                                insertSpaces: true,

                                // Не определяем размер отступа автоматически.
                                detectIndentation: false,

                                // Подстраиваем редактор под размер контейнера.
                                automaticLayout: true,

                                // Не переносим длинные строки.
                                wordWrap: 'off',

                                // Показываем горизонтальную полосу прокрутки при необходимости.
                                scrollbar: {
                                    horizontal: 'auto',
                                },

                                // Даём редактору доступное название.
                                ariaLabel: 'Решение на Python',
                            }}
                        />
                    </div>
                </div>

                <button
                    type="submit"
                    disabled={isRunning}
                    className="rounded-lg bg-purple-600 px-6 py-3 text-white hover:bg-purple-700 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {isRunning ? 'Выполняется…' : 'Проверить решение'}
                </button>

                {/* Отображаем сообщение о проверке. */}
                {/* Сохраняем переносы строк, чтобы ошибки Python было удобно читать. */}
                {message && (
                    <p
                        role="status"
                        className="whitespace-pre-wrap break-words rounded-lg bg-gray-100 p-3"
                    >
                        {message}
                    </p>
                )}
            </form>

            {/* Возвращаемся к выбору направления. */}
            <button
                type="button"
                onClick={onBack}
                className="mt-4 text-purple-700 underline cursor-pointer"
            >
                Вернуться к опросу
            </button>
        </section>
    )
}