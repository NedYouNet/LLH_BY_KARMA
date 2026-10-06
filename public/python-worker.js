// Загружаем Python для браузера.
import { loadPyodide } from 'https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs'

// Подготавливаем Python в отдельном потоке.
async function initialize() {
    try {
        const pyodide = await loadPyodide({
            // Для этой проверки вывод print нам не нужен.
            stdout: () => {},
            stderr: () => {},
        })

        // Принимаем код от страницы.
        self.onmessage = async (event) => {
            try {
                // Выполняем код, в котором кандидат объявляет функцию solve.
                await pyodide.runPythonAsync(event.data.code)

                // Примеры для проверки суммы положительных чисел.
                const tests = [
                    { input: [3, -2, 0, 5], expected: 8 },
                    { input: [-3, -1], expected: 0 },
                    { input: [], expected: 0 },
                    { input: [1, 2, 3], expected: 6 },
                    { input: [0, 0], expected: 0 },
                ]

                // Считаем количество пройденных проверок.
                let passed = 0

                for (const test of tests) {
                    // Вызываем функцию кандидата с очередным списком.
                    const result = await pyodide.runPythonAsync(
                        `solve(${JSON.stringify(test.input)})`
                    )

                    // Сравниваем ответ с ожидаемым числом.
                    if (typeof result === 'number' && result === test.expected) {
                        passed += 1
                    }

                    // Освобождаем Python-объект, если возвращено не обычное число.
                    if (result && typeof result.destroy === 'function') {
                        result.destroy()
                    }
                }

                // Передаём результат обратно странице.
                self.postMessage({
                    type: 'result',
                    passed,
                    total: tests.length,
                })
            } catch (error) {
                // Передаём ошибку Python, например неправильные отступы.
                self.postMessage({
                    type: 'error',
                    message: String(error.message || error).slice(0, 1500),
                })
            }
        }

        // Сообщаем странице, что Python готов.
        self.postMessage({ type: 'ready' })
    } catch {
        // Отдельно сообщаем об ошибке загрузки.
        self.postMessage({
            type: 'error',
            message: 'Не удалось загрузить Python. Проверьте интернет и повторите запуск.',
        })
    }
}

// Начинаем загрузку.
initialize()