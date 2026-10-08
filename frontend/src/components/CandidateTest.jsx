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
    return Object.fromEntries(attempt.items.map(item => [item.id,
        typeof saved[item.id] === 'string' ? saved[item.id] : item.code?.starter_code || '',
    ]))
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
                        <h3 className="font-bold">Задание {index + 1} · {item.skill}</h3>
                        <p className="mt-2 whitespace-pre-wrap">{item.text}</p>
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
                            {item.code?.signature && <pre className="overflow-x-auto rounded-lg bg-gray-100 p-3">{item.code.signature}</pre>}
                            {(item.code?.examples || []).map((example, exampleIndex) => <pre key={exampleIndex} className="overflow-x-auto rounded-lg bg-gray-100 p-3">{`Аргументы: ${JSON.stringify(example.args)}\nРезультат: ${JSON.stringify(example.expected)}`}</pre>)}
                            <div className="overflow-hidden rounded-lg border">
                                <Editor height="300px" language={item.code?.language || 'python'} theme="vs-dark" value={answers[item.id] || ''} onChange={value => changeAnswer(item.id, value ?? '')} loading={<p className="p-4">Загружаем редактор…</p>} options={{ readOnly: locked, minimap: { enabled: false }, fontSize: 14, tabSize: 4, automaticLayout: true, ariaLabel: `Решение задания ${index + 1}` }} />
                            </div>
                        </div>}
                        {!['single', 'input', 'code'].includes(item.kind) && <p className="mt-3 text-red-700">Неизвестный тип задания: {item.kind}. Сообщите бэкендеру.</p>}
                    </div>)}
                </fieldset>
                <button type="submit" disabled={busy} className={buttonClass}>{busy ? 'Отправляем ответы…' : remaining === 0 ? 'Повторить отправку ответов' : 'Завершить и отправить ответы'}</button>
            </form>
        </>}
        {result && <div className="mt-4 space-y-3 rounded-lg bg-purple-50 p-4">
            <h3 className="text-lg font-bold">Результат теста</h3>
            <p>Балл: {result.score}. {result.passed ? 'Тест пройден.' : 'Тест не пройден.'}</p>
            <p>{result.decision?.message}</p>
            <p>Текущий грейд: {gradeNames[result.decision?.grade_after] || result.decision?.grade_after || 'Ещё не подтверждён'}</p>
            {Object.entries(result.by_skill || {}).map(([skill, score]) => <p key={skill}>{skill}: {score}</p>)}
        </div>}
        <button type="button" disabled={busy} onClick={onBack} className="mt-4 text-purple-700 underline disabled:opacity-50">Вернуться к анкете</button>
    </section>
}
