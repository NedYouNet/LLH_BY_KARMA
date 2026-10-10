import { useCallback, useRef, useState } from 'react'
import { vacancies, reference, parseStack, errorMessage } from '../api'
import { Field, ResourceState, useResource, ErrorNotice, buttonClass, secondaryClass } from './ui'
import { SelectField, VacancySummary, applicationLabels } from './WorkFields'
import CandidateCard from './CandidateCard'
const loadReference = () => reference.all()
const empty = { title: '', description: '', team_description: '', specialization: '', grade: '', skills: '', salary_from: '', salary_to: '', salary_type: 'gross', work_format: '', city: '' }
const initialFilters = { q: '', specialization: '', grade: '', work_format: '', salary_min: '' }
export default function VacancyBoard({ role }) {
    const owner = role === 'employer'
    const dictionaries = useResource(loadReference)
    const [filters, setFilters] = useState(initialFilters)
    const [query, setQuery] = useState(initialFilters)
    const [page, setPage] = useState(1)
    const loader = useCallback(() => owner ? vacancies.mine() : vacancies.list({ ...query, page, size: 10 }), [owner, query, page])
    const resource = useResource(loader)
    const [form, setForm] = useState(empty)
    const [editing, setEditing] = useState(null)
    const [letters, setLetters] = useState({})
    const [matches, setMatches] = useState(null)
    const [busy, setBusy] = useState('')
    const [error, setError] = useState('')
    const [notice, setNotice] = useState('')
    const lock = useRef(false)
    const rows = owner ? resource.data || [] : resource.data?.items || []
    async function act(key, operation) {
        if (lock.current) return
        lock.current = true; setBusy(key); setError(''); setNotice('')
        try { await operation() } catch (e) { setError(errorMessage(e)) }
        finally { lock.current = false; setBusy('') }
    }
    const change = (k, v) => setForm(old => ({ ...old, [k]: v }))
    function edit(v) { setEditing(v.id); setForm({ ...empty, ...Object.fromEntries(Object.keys(empty).map(k => [k, k === 'skills' ? (v.skills || []).join(', ') : v[k] ?? empty[k]])) }); setError(''); setNotice('') }
    function save(event) {
        event.preventDefault()
        const from = Number(form.salary_from), to = Number(form.salary_to)
        if (!Number.isSafeInteger(from) || !Number.isSafeInteger(to) || from < 1 || to < from || to > 10000000) { setError('Проверьте вилку зарплаты: целые суммы от 1 до 10 000 000 ₽, верхняя граница не меньше нижней.'); return }
        act('save', async () => {
            const payload = { ...form, title: form.title.trim(), description: form.description.trim(), team_description: form.team_description.trim() || null, skills: parseStack(form.skills), salary_from: from, salary_to: to, work_format: form.work_format || null, city: form.city.trim() || null }
            if (editing) await vacancies.update(editing, payload); else await vacancies.create(payload)
            setEditing(null); setForm(empty); resource.refresh(); setMatches(null); setNotice('Вакансия сохранена.')
        })
    }
    async function showMatches(v, nextPage = 1) { await act(`matches:${v.id}`, async () => { const data = await vacancies.matches(v.id, nextPage); setMatches({ vacancy: v, data }) }) }
    return <section className="mt-6 space-y-4">
        <h2 className="text-xl font-bold">{owner ? 'Мои вакансии' : 'Вакансии'}</h2>
        <ResourceState resource={dictionaries} />
        {!owner && <form className="space-y-3" onSubmit={e => { e.preventDefault(); setPage(1); setQuery({ ...filters }) }}>
            <Field label="Поиск вакансий" value={filters.q} onChange={v => setFilters(x => ({ ...x, q: v }))} />
            {['specialization', 'grade', 'work_format'].map(k => <SelectField key={k} label={{ specialization: 'Специализация', grade: 'Грейд', work_format: 'Формат работы' }[k]} value={filters[k]} onChange={v => setFilters(x => ({ ...x, [k]: v }))} options={dictionaries.data?.[{ specialization: 'specializations', grade: 'grades', work_format: 'work_formats' }[k]]} />)}
            <Field label="Зарплата не ниже, ₽" type="number" min={1} max={10000000} value={filters.salary_min} onChange={v => setFilters(x => ({ ...x, salary_min: v }))} />
            <button className={secondaryClass}>Найти</button><button type="button" className={`${secondaryClass} ml-2`} onClick={() => { setFilters(initialFilters); setQuery(initialFilters); setPage(1) }}>Сбросить</button>
        </form>}
        {owner && <form onSubmit={save} className="space-y-3 rounded-lg bg-purple-50 p-4"><h3 className="font-bold">{editing ? 'Редактировать вакансию' : 'Новая вакансия'}</h3><fieldset disabled={Boolean(busy)} className="space-y-3">
            <Field label="Название" required minLength={3} maxLength={200} value={form.title} onChange={v => change('title', v)} />
            <Field label="Описание работы" multiline required minLength={10} maxLength={10000} value={form.description} onChange={v => change('description', v)} />
            <Field label="О команде" multiline maxLength={5000} value={form.team_description} onChange={v => change('team_description', v)} />
            {['specialization', 'grade', 'work_format'].map(k => <SelectField key={k} required={k !== 'work_format'} empty="Выберите" label={{ specialization: 'Специализация', grade: 'Грейд', work_format: 'Формат работы' }[k]} value={form[k]} onChange={v => change(k, v)} options={dictionaries.data?.[{ specialization: 'specializations', grade: 'grades', work_format: 'work_formats' }[k]]} />)}
            <Field label="Технологии через запятую" value={form.skills} onChange={v => change('skills', v)} />
            <Field label="Город" maxLength={100} value={form.city} onChange={v => change('city', v)} />
            <div className="grid gap-3 sm:grid-cols-2">{['salary_from', 'salary_to'].map(k => <Field key={k} label={k === 'salary_from' ? 'Зарплата от, ₽' : 'Зарплата до, ₽'} type="number" required min={1} max={10000000} step={1} value={form[k]} onChange={v => change(k, v)} />)}</div>
            <SelectField label="Зарплата" required empty="Выберите" value={form.salary_type} onChange={v => change('salary_type', v)} options={{ gross: 'До вычета НДФЛ', net: 'На руки' }} />
            <button className={buttonClass}>{busy === 'save' ? 'Сохраняем…' : editing ? 'Сохранить изменения' : 'Опубликовать'}</button>{editing && <button type="button" className={`${secondaryClass} ml-2`} onClick={() => { setEditing(null); setForm(empty) }}>Отмена</button>}
        </fieldset></form>}
        <ErrorNotice message={error} />{notice && <p role="status">{notice}</p>}
        <button type="button" className={secondaryClass} disabled={Boolean(busy)} onClick={() => { setMatches(null); resource.refresh() }}>Обновить</button>
        <ResourceState resource={resource} />
        {!resource.loading && !resource.error && <>{!rows.length && <p>Вакансий пока нет.</p>}{rows.map(v => <article key={v.id} className="space-y-3 rounded-xl border p-5"><VacancySummary vacancy={v} />
            {owner ? <><p>{v.status === 'active' ? 'Опубликована' : 'Закрыта'} · Откликов: {v.applications_count ?? 0}</p><div className="flex flex-wrap gap-2"><button type="button" className={secondaryClass} disabled={Boolean(busy)} onClick={() => edit(v)}>Редактировать</button><button type="button" className={secondaryClass} disabled={Boolean(busy)} onClick={() => showMatches(v)}>Подобрать кандидатов</button><button type="button" className={secondaryClass} disabled={Boolean(busy)} onClick={() => act(`status:${v.id}`, async () => { await vacancies.update(v.id, { status: v.status === 'active' ? 'closed' : 'active' }); resource.refresh() })}>{v.status === 'active' ? 'Закрыть вакансию' : 'Открыть снова'}</button></div></> : <>
                {v.my_application_status && <p>Ваш отклик: {applicationLabels[v.my_application_status] || v.my_application_status}</p>}
                {(!v.my_application_status || v.my_application_status === 'withdrawn') && <form className="space-y-2" onSubmit={e => { e.preventDefault(); act(`apply:${v.id}`, async () => { await vacancies.apply(v.id, letters[v.id]?.trim() || null); setLetters(x => ({ ...x, [v.id]: '' })); resource.refresh(); setNotice('Отклик отправлен. Его статус доступен в разделе «Отклики».') }) }}><p className="text-sm">После отклика этой компании станут доступны ваши контакты.</p><Field label="Сопроводительное письмо (необязательно)" multiline maxLength={5000} value={letters[v.id] || ''} onChange={text => setLetters(x => ({ ...x, [v.id]: text }))} /><button className={buttonClass} disabled={Boolean(busy)}>Откликнуться</button></form>}
            </>}
        </article>)}</>}
        {!owner && !resource.loading && !resource.error && <div className="flex items-center gap-3"><button type="button" className={secondaryClass} disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Назад</button><span>Страница {page}</span><button type="button" className={secondaryClass} disabled={page * 10 >= (resource.data?.total || 0)} onClick={() => setPage(p => p + 1)}>Далее</button></div>}
        {matches && <section className="space-y-3 border-t pt-4"><h3 className="font-bold">Кандидаты под вакансию «{matches.vacancy.title}»</h3><p>Найдено: {matches.data.total}</p>{matches.data.items.map(c => <CandidateCard key={`${matches.vacancy.id}:${c.id}:${matches.data.page}`} card={c} vacancy={matches.vacancy} onChanged={() => showMatches(matches.vacancy, matches.data.page)} />)}<div className="flex gap-2"><button type="button" className={secondaryClass} disabled={Boolean(busy) || matches.data.page <= 1} onClick={() => showMatches(matches.vacancy, matches.data.page - 1)}>Назад</button><span>Страница {matches.data.page}</span><button type="button" className={secondaryClass} disabled={Boolean(busy) || matches.data.page * matches.data.size >= matches.data.total} onClick={() => showMatches(matches.vacancy, matches.data.page + 1)}>Далее</button></div></section>}
    </section>
}
