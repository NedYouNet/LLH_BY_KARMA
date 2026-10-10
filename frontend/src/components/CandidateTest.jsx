import Editor from '@monaco-editor/react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { candidate, testing, errorMessage } from '../api'

const buttonClass = 'rounded-lg bg-purple-600 px-6 py-3 text-white disabled:opacity-50'
const gradeNames = { intern: 'Intern', junior: 'Junior', middle: 'Middle', senior: 'Senior' }

function draftKey(selection, id) {
    return `fsp.test.answers:${selection.candidateId}:${id}`
}

function initialAnswers(attempt, selection) {
    let saved = {}
    try { saved = JSON.parse(sessionStorage.getItem(draftKey(selection, attempt.id))) || {} } catch { /* нет сохранённого черновика */ }
    return Object.fromEntries(attempt.items.map(item => {
        const draft = typeof saved[item.id] === 'string' ? saved[item.id] : ''
        const untouchedStarter = item.kind === 'code' && item.code?.starter_code
            && draft.trim() === item.code.starter_code.trim()
        return [item.id, untouchedStarter ? '' : draft]
    }))
}

function pythonLiteral(value) {
    if (value === null) return 'None'
    if (typeof value === 'boolean') return value ? 'True' : 'False'
    if (Array.isArray(value)) return `[${value.map(pythonLiteral).join(', ')}]`
    if (typeof value === 'object') {
        return `{${Object.entries(value).map(([key, item]) => `${JSON.stringify(key)}: ${pythonLiteral(item)}`).join(', ')}}`
    }
    return JSON.stringify(value)
}

function taskText(item) {
    if (item.kind !== 'code') return item.text
    // Пример показываем в отдельном блоке вызова, без дублирования аргументов в условии.
    return item.text.replace(/\n\nПример входных аргументов этого варианта:[\s\S]*?\nНапишите функцию Python с указанной сигнатурой\. input\(\) и print\(\) не нужны\.$/, '')
}

function argumentNames(code) {
    const signature = code?.signature || ''
    const parameters = signature.slice(signature.indexOf('(') + 1, signature.lastIndexOf(')'))
    return parameters.split(',').map(value => value.trim().split(':')[0].split('=')[0].trim()).filter(Boolean)
}

export default function CandidateTest({ selection, onBack }) {
    const [attempt, setAttempt] = useState(null)
    const [answers, setAnswers] = useState({})
    const [result, setResult] = useState(null)
    const [category, setCategory] = useState(null)
    const [loading, setLoading] = useState(true)
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState('')
    const [retry, setRetry] = useState(0)
    const [remaining, setRemaining] = useState(0)
    const [checks, setChecks] = useState({})
    const [checking, setChecking] = useState(null)
    const checkingRef = useRef(false)
    const answersRef = useRef({})
    const busyRef = useRef(false)
    const endRef = useRef(0)
    const autoSentRef = useRef(false)
    const submitRef = useRef(null)

    const installAttempt = useCallback(async data => {
        if (data.finished_at || data.passed != null) {
            setResult(await testing.result(data.id))
            setAttempt(data)
            try { sessionStorage.removeItem(draftKey(selection, data.id)) } catch { /* хранилище недоступно */ }
            return
        }
        const draft = initialAnswers(data, selection)
        answersRef.current = draft
        setAnswers(draft)
        setChecks(Object.fromEntries(data.items.filter(item => item.kind === 'code').map(item => [item.id,
            { used: item.code?.checks_used || 0, limit: item.code?.check_limit || 10 },
        ])))
        const seconds = Math.max(0, Number(data.seconds_left) || 0)
        endRef.current = performance.now() + seconds * 1000
        autoSentRef.current = false
        setRemaining(seconds)
        setAttempt(data)
    }, [selection])

    useEffect(() => {
        let active = true
        async function load() {
            setLoading(true)
            setError('')
            try {
                if (selection.attemptId) {
                    const data = await testing.get(selection.attemptId)
                    if (active) await installAttempt(data)
                } else {
                    const status = await candidate.category()
                    if (!active) return
                    setCategory(status)
                    if (status.active_attempt_id) {
                        const data = await testing.get(status.active_attempt_id)
                        if (active) await installAttempt(data)
                    }
                }
            } catch (failure) { if (active) setError(errorMessage(failure)) }
            finally { if (active) setLoading(false) }
        }
        load()
        return () => { active = false }
    }, [selection, retry, installAttempt])

    useEffect(() => {
        if (!attempt || result) return
        try { sessionStorage.setItem(draftKey(selection, attempt.id), JSON.stringify(answers)) } catch { /* черновик останется в памяти */ }
    }, [attempt, answers, result, selection])

    async function start() {
        if (busyRef.current) return
        busyRef.current = true
        setBusy(true)
        setError('')
        try {
            let data
            try { data = await testing.start(selection.specialization, selection.grade) }
            catch (failure) {
                if (failure.code !== 'ATTEMPT_IN_PROGRESS' || !failure.data?.attempt_id) throw failure
                data = await testing.get(failure.data.attempt_id)
            }
            await installAttempt(data)
        } catch (failure) { setError(errorMessage(failure)) }
        finally { busyRef.current = false; setBusy(false) }
    }

    const submit = useCallback(async () => {
        if (!attempt || result || busyRef.current) return
        busyRef.current = true
        setBusy(true)
        setError('')
        try {
            let response
            try { response = await testing.submit(attempt.id, answersRef.current) }
            catch (failure) {
                // Если первая отправка уже дошла до сервера, получаем готовый результат.
                if (failure.status !== 409) throw failure
                try { response = await testing.result(attempt.id) } catch { throw failure }
            }
            setResult(response)
            try { sessionStorage.removeItem(draftKey(selection, attempt.id)) } catch { /* хранилище недоступно */ }
        } catch (failure) { setError(errorMessage(failure)) }
        finally { busyRef.current = false; setBusy(false) }
    }, [attempt, result, selection])

    useEffect(() => { submitRef.current = submit }, [submit])

    useEffect(() => {
        if (!attempt || result || loading) return
        function tick() {
            const seconds = Math.max(0, Math.ceil((endRef.current - performance.now()) / 1000))
            setRemaining(seconds)
            if (seconds === 0 && !autoSentRef.current) {
                autoSentRef.current = true
                submitRef.current?.()
            }
        }
        tick()
        const timer = setInterval(tick, 1000)
        return () => clearInterval(timer)
    }, [attempt, result, loading])

    function changeAnswer(id, value) {
        const next = { ...answersRef.current, [id]: value }
        answersRef.current = next
        setAnswers(next)
        setError('')
        setChecks(previous => ({ ...previous, [id]: { ...previous[id], result: null, error: '' } }))
    }

    async function checkCode(item) {
        const current = checks[item.id] || { used: 0, limit: 10 }
        const code = answersRef.current[item.id] || ''
        if (checkingRef.current || busyRef.current || !code.trim() || current.used >= current.limit || remaining <= 0) return
        checkingRef.current = true
        setChecking(item.id)
        setChecks(previous => ({ ...previous, [item.id]: { ...current, result: null, error: '' } }))
        try {
            const response = await testing.check(attempt.id, item.id, code)
            setChecks(previous => ({ ...previous, [item.id]: {
                used: response.checks_used, limit: response.check_limit, result: response, error: '',
            } }))
        } catch (failure) {
            setChecks(previous => ({ ...previous, [item.id]: {
                ...previous[item.id], used: failure.data?.checks_used ?? previous[item.id]?.used ?? 0,
                error: failure.status === 404 ? 'Проверка на тестах недоступна. Проверьте обновление бэкенда.' : errorMessage(failure),
            } }))
        } finally {
            checkingRef.current = false
            setChecking(null)
        }
    }

    const target = category?.targets?.find(item => item.grade === selection.grade)
    const locked = busy || remaining === 0
    const time = `${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, '0')}`

    return <section className="mt-8 border-t border-gray-200 pt-6">
        <h2 className="text-xl font-bold">Тестирование</h2>
        <p className="mt-2 text-gray-600">{attempt?.specialization || selection.specialization} · {gradeNames[attempt?.target_grade || selection.grade] || selection.grade}</p>
        {loading && <p role="status" className="mt-4">Загружаем тест…</p>}
        {error && <div role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-red-800">
            <p>{error}</p>
            {!attempt && <button type="button" disabled={busy} onClick={() => setRetry(value => value + 1)} className="mt-2 underline">Повторить загрузку</button>}
        </div>}
        {!loading && !attempt && category && <div className="mt-4 space-y-3">
            <p>Таймер запустится после нажатия «Начать тест». Ответы проверяет сервер.</p>
            {target?.allowed === false && <p className="text-red-700">{target.reason || 'Сейчас тест на этот грейд недоступен.'}</p>}
            <button type="button" disabled={busy || target?.allowed === false} onClick={start} className={buttonClass}>{busy ? 'Начинаем…' : 'Начать тест'}</button>
        </div>}
        {!loading && attempt && !result && <>
            <p className="sticky top-0 z-10 mt-4 rounded-lg bg-purple-50 p-3 text-purple-800">Осталось: {time}. Ответы сохраняются в этой вкладке. По окончании времени они отправятся автоматически.</p>
            <form onSubmit={event => { event.preventDefault(); submit() }} className="mt-4 space-y-4">
                <fieldset disabled={locked} className="space-y-4">
                    {attempt.items.map((item, index) => <div key={item.id} className="rounded-lg border border-gray-200 p-4">
                        <h3 className="font-bold">Задание {index + 1} · {item.difficulty ? ({ easy: 'Лёгкая', medium: 'Средняя', hard: 'Сложная' }[item.difficulty] || item.skill) : item.skill}{item.max_score != null && <span className="ml-2 text-sm font-medium text-purple-700">до {item.max_score} баллов</span>}</h3>
                        {item.base_weight != null && <p className="mt-1 text-sm text-gray-600">{item.base_weight} баллов пропорционально пройденным тестам + {item.bonus_weight} баллов, если пройдены все тесты.</p>}
                        <p className="mt-2 whitespace-pre-wrap">{taskText(item)}</p>
                        {item.kind === 'single' && <div className="mt-3 space-y-2">
                            {(item.options || []).map((option, optionIndex) => <label key={optionIndex} className="flex items-start gap-2">
                                <input type="radio" name={item.id} value={option} checked={answers[item.id] === option} onChange={() => changeAnswer(item.id, option)} className="mt-1" />
                                <span>{option}</span>
                            </label>)}
                        </div>}
                        {item.kind === 'input' && <label className="mt-3 block">Ваш ответ
                            <input value={answers[item.id] || ''} onChange={event => changeAnswer(item.id, event.target.value)} className="mt-1 w-full rounded-lg border p-3" />
                        </label>}
                        {item.kind === 'code' && <div className="mt-3 space-y-3">
                            <div className="flex flex-wrap items-center gap-2">
                                <span className="rounded-full bg-purple-100 px-3 py-1 text-sm font-medium text-purple-800">Язык программирования: Python</span>
                            </div>
                            <p className="text-sm text-gray-600">Имя функции: <code>{item.code?.function_name || 'solve'}</code>. Параметры: <code>{argumentNames(item.code).join(', ') || 'нет'}</code>.</p>
                            {(item.code?.examples || []).map((example, exampleIndex) => <div key={exampleIndex} className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                                <p className="font-medium">{(item.code.examples.length > 1) ? `Пример ${exampleIndex + 1}` : 'Пример'}</p>
                                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                                    <div><p className="text-sm text-gray-600">Аргументы</p>
                                        <pre className="mt-1 overflow-x-auto rounded-lg bg-white p-3"><code>{(example.args || []).map((value, position) => `${argumentNames(item.code)[position] || `arg${position + 1}`} = ${pythonLiteral(value)}`).join('\n')}</code></pre>
                                    </div>
                                    <div><p className="text-sm text-gray-600">Ожидаемый ответ</p>
                                        <pre className="mt-1 overflow-x-auto rounded-lg bg-white p-3"><code>{pythonLiteral(example.expected)}</code></pre>
                                    </div>
                                </div>
                            </div>)}
                            <p className="text-sm text-gray-600">Ответ возвращается через return. input() и print() не нужны.</p>
                            <div className="overflow-hidden rounded-lg border">
                                <Editor height="300px" language="python" theme="vs-dark" value={answers[item.id] || ''} onChange={value => changeAnswer(item.id, value ?? '')} loading={<p className="p-4">Загружаем редактор…</p>} options={{ readOnly: locked || checking !== null, minimap: { enabled: false }, fontSize: 14, tabSize: 4, automaticLayout: true, ariaLabel: `Решение задания ${index + 1}` }} />
                            </div>
                            <div className="flex flex-wrap items-center gap-3">
                                <button type="button" onClick={() => checkCode(item)} disabled={locked || checking !== null || !(answers[item.id] || '').trim() || (checks[item.id]?.used || 0) >= (checks[item.id]?.limit || 10)} className="rounded-lg border border-purple-600 px-4 py-2 font-medium text-purple-700 disabled:cursor-not-allowed disabled:opacity-50">{checking === item.id ? 'Проверяем…' : 'Проверить на тестах'}</button>
                                <span className="text-sm text-gray-600">Проверок осталось: {Math.max(0, (checks[item.id]?.limit || 10) - (checks[item.id]?.used || 0))} из {checks[item.id]?.limit || 10}</span>
                            </div>
                            <div aria-live="polite">
                                {checks[item.id]?.result && <div className={`rounded-lg p-3 ${checks[item.id].result.passed === checks[item.id].result.total ? 'bg-green-50 text-green-800' : 'bg-amber-50 text-amber-900'}`}>
                                    <p className="font-medium">Пройдено {checks[item.id].result.passed} из {checks[item.id].result.total} тестов</p>
                                    {item.base_weight != null && <p className="mt-1">Предварительный балл: {(item.base_weight * (checks[item.id].result.total ? checks[item.id].result.passed / checks[item.id].result.total : 0) + (checks[item.id].result.total > 0 && checks[item.id].result.passed === checks[item.id].result.total ? item.bonus_weight : 0)).toFixed(2).replace(/\.?0+$/, '')} из {item.max_score}.</p>}
                                    {checks[item.id].result.messages.map((message, messageIndex) => <p key={messageIndex} className="mt-1 text-sm">{message}</p>)}
                                </div>}
                                {checks[item.id]?.error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-red-800">{checks[item.id].error}</p>}
                            </div>
                            <p className="text-xs text-gray-500">Проверка не завершает тест. Окончательные ответы отправляются кнопкой внизу страницы.</p>
                        </div>}
                        {!['single', 'input', 'code'].includes(item.kind) && <p className="mt-3 text-red-700">Неизвестный тип задания: {item.kind}. Сообщите бэкендеру.</p>}
                    </div>)}
                </fieldset>
                <button type="submit" disabled={busy || checking !== null} className={buttonClass}>{busy ? 'Отправляем ответы…' : remaining === 0 ? 'Повторить отправку ответов' : 'Завершить и отправить ответы'}</button>
            </form>
        </>}
        {result && <div className="mt-4 space-y-3 rounded-lg bg-purple-50 p-4">
            <h3 className="text-lg font-bold">Результат теста</h3>
            {(result.items || []).filter(item => item.max_score != null).map((item, index) => <p key={item.id}>Задание {index + 1}: {item.score} из {item.max_score} баллов{item.total != null ? ` · тестов пройдено: ${item.passed || 0}/${item.total}` : ''}.</p>)}
            <p>Балл: {result.score}. {result.passed ? 'Тест пройден.' : 'Тест не пройден.'}</p>
            <p>{result.decision?.message}</p>
            <p>Текущий грейд: {gradeNames[result.decision?.grade_after] || result.decision?.grade_after || 'Ещё не подтверждён'}</p>
            {Object.entries(result.by_skill || {}).map(([skill, score]) => <p key={skill}>{skill}: {score}</p>)}
        </div>}
        <button type="button" disabled={busy} onClick={onBack} className="mt-4 text-purple-700 underline disabled:opacity-50">Вернуться к анкете</button>
    </section>
}
