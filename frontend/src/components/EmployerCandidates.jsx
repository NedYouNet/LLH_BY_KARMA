import { useCallback, useState } from 'react'
import { candidates, reference, parseStack } from '../api'
import CandidateCard from './CandidateCard'
import { Field, secondaryClass, inputClass, ResourceState, useResource, listOptions } from './ui'

const defaults = needs => ({ specialization: needs?.specialization || '', grade: needs?.grade || '', stack: (needs?.stack || []).join(', '), only_fsp: false, only_verified: false, min_test_score: '', text: needs?.description?.slice(0, 2000) || '' })
const loadReference = () => reference.all()
export default function EmployerCandidates({ needs }) {
    const [filters, setFilters] = useState(() => defaults(needs))
    const [query, setQuery] = useState(() => defaults(needs))
    const [page, setPage] = useState(1)
    const [mode, setMode] = useState('search')
    const dictionaries = useResource(loadReference)
    const loader = useCallback(async () => {
        if (mode === 'shortlist') {
            const saved = await candidates.shortlist()
            return { total: saved.length, page: 1, size: saved.length, categories: [], items: saved.map(x => ({ ...x.candidate, in_shortlist: true })), mode: 'shortlist' }
        }
        const data = await candidates.search({ ...query, stack: parseStack(query.stack), page, page_size: 10 })
        return { ...data, criteria: query, mode: 'search' }
    }, [query, page, mode])
    const resource = useResource(loader)
    const change = (name, value) => setFilters(old => ({ ...old, [name]: value }))
    function apply(event) { event.preventDefault(); setQuery({ ...filters }); setPage(1); setMode('search') }
    function reset() { const next = defaults(null); setFilters(next); setQuery(next); setPage(1); setMode('search') }
    const shownPage = resource.data?.page || 1
    const shown = resource.data?.criteria || query
    return <section className="mt-6 space-y-4">
        <h2 className="text-xl font-bold">{needs ? `Подбор под потребность «${needs.title || needs.specialization}»` : 'Поиск кандидатов'}</h2>
        <p>Подбор и оценку соответствия рассчитывает сервер. Можно уточнять условия и сохранять кандидатов в избранное.</p>
        <div className="flex gap-2"><button type="button" className={secondaryClass} aria-pressed={mode === 'search'} onClick={() => setMode('search')}>Вся база</button><button type="button" className={secondaryClass} aria-pressed={mode === 'shortlist'} onClick={() => setMode('shortlist')}>Избранное</button></div>
        <ResourceState resource={dictionaries} />
        {mode === 'search' && <form onSubmit={apply} className="space-y-3 rounded-lg bg-purple-50 p-4">
            <div className="grid gap-3 sm:grid-cols-2">{[['specialization', 'Специализация', dictionaries.data?.specializations], ['grade', 'Грейд', dictionaries.data?.grades]].map(([name, label, values]) => <label key={name}>{label}<select className={inputClass} value={filters[name]} onChange={e => change(name, e.target.value)}><option value="">Все</option>{listOptions(values).map(x => <option key={x.code} value={x.code}>{x.name}</option>)}</select></label>)}</div>
            <Field label="Технологии через запятую" value={filters.stack} onChange={v => change('stack', v)} />
            <Field label="Описание задачи или команды" multiline maxLength={2000} value={filters.text} onChange={v => change('text', v)} />
            <Field label="Минимальный балл теста" type="number" min={0} max={100} value={filters.min_test_score} onChange={v => change('min_test_score', v)} />
            {[['only_fsp', 'Только с достижениями ФСП'], ['only_verified', 'Только с подтверждённым грейдом']].map(([name, label]) => <label className="flex gap-2" key={name}><input type="checkbox" checked={filters[name]} onChange={e => change(name, e.target.checked)} />{label}</label>)}
            <div className="flex gap-2"><button type="submit" className={secondaryClass}>Применить</button><button type="button" className={secondaryClass} onClick={reset}>Сбросить</button></div>
        </form>}
        <button type="button" className={secondaryClass} disabled={resource.loading} onClick={resource.refresh}>Обновить результаты и доступ к контактам</button>
        <ResourceState resource={resource} />
        {resource.data && <div className="space-y-4" aria-busy={resource.loading}>
            {(resource.loading || resource.error) && <p>Показаны предыдущие результаты. Новые условия ещё не применены к выдаче.</p>}
            {resource.data.mode === 'search' && <p className="text-sm">Условия выдачи: {shown.specialization || 'все специализации'} · {shown.grade || 'все грейды'} · стек: {shown.stack || 'не задан'}{shown.only_fsp && ' · с ФСП'}{shown.only_verified && ' · подтверждённые'}{shown.min_test_score !== '' && ` · тест от ${shown.min_test_score}`}{shown.text && ` · описание: ${shown.text}`}</p>}
            <p>Найдено: {resource.data.total}</p>
            <div className="flex flex-wrap gap-2">{(resource.data.categories || []).map(x => <button type="button" key={`${x.specialization}:${x.grade}`} className={secondaryClass} disabled={resource.loading} onClick={() => { const next = { ...query, specialization: x.specialization, grade: x.grade }; setFilters(next); setQuery(next); setPage(1) }}>{x.category}: {x.count} · подтверждены: {x.verified} · ФСП: {x.with_fsp}</button>)}</div>
            {!resource.data.items?.length && <p>Кандидатов по этим условиям пока нет.</p>}
            {(resource.data.items || []).map(card => <CandidateCard key={`${resource.data.mode}:${resource.data.page}:${card.id}:${resource.loading}`} card={resource.loading || resource.error ? { ...card, contacts: null } : card} disabled={resource.loading || Boolean(resource.error)} onChanged={resource.refresh} />)}
            {mode === 'search' && <div className="flex items-center gap-3"><button type="button" className={secondaryClass} disabled={resource.loading || Boolean(resource.error) || shownPage <= 1} onClick={() => setPage(shownPage - 1)}>Назад</button><span>Страница {shownPage}</span><button type="button" className={secondaryClass} disabled={resource.loading || Boolean(resource.error) || shownPage * (resource.data.size || 10) >= resource.data.total} onClick={() => setPage(shownPage + 1)}>Далее</button></div>}
        </div>}
    </section>
}
