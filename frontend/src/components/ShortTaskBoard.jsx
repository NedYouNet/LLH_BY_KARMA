import { useCallback, useRef, useState } from 'react'
import { shortTasks, reference, request, errorMessage } from '../api'
import { useResource, ResourceState, Field, ErrorNotice, buttonClass, secondaryClass, date } from './ui'
import { SelectField } from './WorkFields'
const loadReference = () => reference.all()
const empty = { title: '', description: '', kind: 'approach', specialization: '', grade: '', deadline_at: '' }
export default function ShortTaskBoard({ role }) {
    const owner = role === 'employer'
    const loader = useCallback(() => owner ? shortTasks.mine() : shortTasks.feed(), [owner])
    const resource = useResource(loader)
    const dictionaries = useResource(loadReference)
    const [form, setForm] = useState(empty)
    const [answers, setAnswers] = useState({})
    const [reviews, setReviews] = useState({})
    const [editingReviews, setEditingReviews] = useState({})
    const [selected, setSelected] = useState(null)
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState('')
    const [notice, setNotice] = useState('')
    const lock = useRef(false)
    async function act(operation) {
        if (lock.current) return
        lock.current = true; setBusy(true); setError(''); setNotice('')
        try { await operation() } catch (e) { setError(errorMessage(e)) }
        finally { lock.current = false; setBusy(false) }
    }
    const change = (k, v) => setForm(x => ({ ...x, [k]: v }))
    function loadAnswers(task) { act(async () => { setSelected(null); setSelected({ task, rows: await shortTasks.submissions(task.id) }) }) }
    function create(e) {
        e.preventDefault()
        if (form.deadline_at && (!Number.isFinite(new Date(form.deadline_at).getTime()) || new Date(form.deadline_at) <= new Date())) { setError('Срок должен быть в будущем.'); return }
        act(async () => { await shortTasks.create({ ...form, title: form.title.trim(), description: form.description.trim(), grade: form.grade || null, deadline_at: form.deadline_at ? new Date(form.deadline_at).toISOString() : null }); setForm(empty); resource.refresh(); setNotice('Задание опубликовано.') })
    }
    function review(s) {
        const values = reviews[s.id] || { score: s.employer_score == null ? '' : String(s.employer_score), feedback: s.employer_feedback || '' }
        const score = Number(values.score)
        if (values.score === '' || !Number.isFinite(score) || score < 0 || score > 10) { setError('Укажите оценку от 0 до 10.'); return }
        act(async () => { await shortTasks.review(s.id, score, values.feedback.trim() || null); const rows = await shortTasks.submissions(selected.task.id); setSelected(x => ({ ...x, rows })); resource.refresh(); setEditingReviews(x => ({ ...x, [s.id]: false }))
            setNotice('Оценка сохранена.') })
    }
    function sendAnswer(task) {
        const answer = (answers[task.id] || '').trim()
        if (answer.length < 5) { setError('Ответ должен содержать минимум 5 символов без крайних пробелов.'); return }
        act(async () => { await shortTasks.submit(task.id, answer); setAnswers(x => ({ ...x, [task.id]: '' })); resource.refresh(); setNotice('Ответ отправлен.') })
    }
    return <section className="mt-6 space-y-4"><h2 className="text-xl font-bold">Короткие задания</h2><p>{owner ? 'Публикуйте задачи для выбранной специализации и оценивайте ответы.' : 'Задания под вашу подтверждённую категорию. Ответ отправляется работодателю, код здесь не запускается.'}</p>
        {owner && <><ResourceState resource={dictionaries} /><form onSubmit={create} className="space-y-3 rounded-lg bg-purple-50 p-4"><fieldset disabled={busy} className="space-y-3"><Field label="Название" required minLength={3} maxLength={200} value={form.title} onChange={v => change('title', v)} /><Field label="Условие" multiline required minLength={10} maxLength={10000} value={form.description} onChange={v => change('description', v)} /><SelectField label="Тип ответа" required empty="Выберите" value={form.kind} onChange={v => change('kind', v)} options={{ approach: 'Предложить подход', solution: 'Решить задачу' }} /><SelectField label="Специализация" required empty="Выберите" value={form.specialization} onChange={v => change('specialization', v)} options={dictionaries.data?.specializations} /><SelectField label="Грейд" value={form.grade} onChange={v => change('grade', v)} options={dictionaries.data?.grades} /><Field label="Срок ответа (необязательно)" type="datetime-local" value={form.deadline_at} onChange={v => change('deadline_at', v)} /><button className={buttonClass}>Опубликовать задание</button></fieldset></form></>}
        <ErrorNotice message={error} />{notice && <p role="status">{notice}</p>}<button type="button" className={secondaryClass} disabled={busy} onClick={() => { setSelected(null); resource.refresh() }}>Обновить</button><ResourceState resource={resource} />
        {!resource.loading && !resource.error && <>{!resource.data?.length && <p>{owner ? 'Заданий пока нет.' : 'Сейчас заданий для вашей категории нет. Проверьте категорию и зайдите позже.'}</p>}{(resource.data || []).map(task => <article key={task.id} className="space-y-3 rounded-xl border p-5"><h3 className="font-bold">{task.title}</h3><p>{task.company?.company_name} · {task.specialization} · {task.grade || 'все грейды'}</p><p>{task.kind === 'solution' ? 'Решение' : 'Описание подхода'} · Срок: {task.deadline_at ? date(task.deadline_at) : 'не ограничен'}</p><p className="whitespace-pre-wrap">{task.description}</p>
            {owner ? <><p>{task.is_active ? 'Активно' : 'Закрыто'} · Ответов: {task.submissions_count ?? 0}</p><button type="button" className={secondaryClass} disabled={busy} onClick={() => loadAnswers(task)}>Посмотреть ответы</button>{task.is_active && <button type="button" className={`${secondaryClass} ml-2`} disabled={busy} onClick={() => { if (window.confirm('Закрыть приём ответов?')) act(async () => { await request('POST', `/short-tasks/${task.id}/close`); resource.refresh() }) }}>Закрыть задание</button>}</> : task.my_submission_status ? <p>{task.my_submission_status === 'reviewed' ? 'Работодатель оценил ответ.' : 'Ответ отправлен работодателю.'}</p> : <form className="space-y-2" onSubmit={e => { e.preventDefault(); sendAnswer(task) }}><Field label="Ваш ответ" multiline required minLength={5} maxLength={20000} value={answers[task.id] || ''} onChange={v => setAnswers(x => ({ ...x, [task.id]: v }))} /><button className={buttonClass} disabled={busy}>Отправить ответ</button></form>}
        </article>)}</>}
        {selected && <section className="space-y-3 border-t pt-4"><h3 className="font-bold">Ответы на «{selected.task.title}»</h3><ErrorNotice message={error} />
            {notice && (
                <p role="status" className="font-semibold text-green-700">
                    {notice}
                </p>
            )}{!selected.rows.length && <p>Ответов пока нет.</p>}{selected.rows.map(s => { const values = reviews[s.id] || { score: s.employer_score == null ? '' : String(s.employer_score), feedback: s.employer_feedback || '' }; return <article key={s.id} className="space-y-2 rounded-lg border p-4"><h4 className="font-bold">{s.candidate?.display_name || 'Кандидат'}</h4><p>Отправлен: {date(s.created_at)} · {s.status === 'reviewed' ? 'Оценён' : 'Ожидает оценки'}</p><pre className="whitespace-pre-wrap break-words font-sans">{s.answer}</pre>{s.status === 'reviewed' && (
            <p className="font-semibold text-green-700">
                Сохранённая оценка: {s.employer_score ?? 'не указана'} / 10
                {s.employer_feedback && ` · Комментарий: ${s.employer_feedback}`}
            </p>
        )}{s.status === 'reviewed' && !editingReviews[s.id] ? (
                <button
                    type="button"
                    className={secondaryClass}
                    disabled={busy}
                    onClick={() => {
                        setReviews(x => ({
                            ...x,
                            [s.id]: {
                                score: s.employer_score == null ? '' : String(s.employer_score),
                                feedback: s.employer_feedback || '',
                            },
                        }))
                        setEditingReviews(x => ({ ...x, [s.id]: true }))
                    }}
                >
                    Изменить оценку
                </button>
            ) : (
                <form className="space-y-2" onSubmit={e => {
                    e.preventDefault()
                    review(s)
                }}><Field label="Оценка от 0 до 10" type="number" required min={0} max={10} step={0.1} value={values.score} onChange={v => setReviews(x => ({ ...x, [s.id]: { ...values, score: v } }))} /><Field label="Комментарий" multiline maxLength={2000} value={values.feedback} onChange={v => setReviews(x => ({ ...x, [s.id]: { ...values, feedback: v } }))} /><button className={buttonClass} disabled={busy}>Сохранить оценку</button></form>
            )}</article> })}</section>}
    </section>
}
