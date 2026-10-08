import { useCallback, useState } from 'react'
import { candidates, invitationUiStatus, INVITATION_STATUS_LABELS, errorMessage } from '../api'
import InvitationModal from './InvitationModal'
import { Field, buttonClass, secondaryClass, ErrorNotice, ResourceState, useResource, Reasons } from './ui'

export default function EmployerCandidates({ needs }) {
    const [filters, setFilters] = useState({ only_fsp: false, only_verified: false, min_test_score: '', text: '' })
    const [query, setQuery] = useState(filters)
    const [page, setPage] = useState(1)
    const loader = useCallback(() => candidates.search({ needs_id: needs.id, ...query, page, page_size: 10 }), [needs.id, query, page])
    const resource = useResource(loader)
    const [selected, setSelected] = useState(null)
    const [detail, setDetail] = useState(null)
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState('')
    const [notice, setNotice] = useState('')
    async function open(id) {
        if (busy) return
        setBusy(true); setError(''); setDetail(null)
        try { setDetail(await candidates.get(id)) }
        catch (failure) { setError(errorMessage(failure)) }
        finally { setBusy(false) }
    }
    async function shortlist(card) {
        if (busy) return
        setBusy(true); setError('')
        try { if (card.in_shortlist) await candidates.removeFromShortlist(card.id); else await candidates.addToShortlist(card.id); resource.refresh() }
        catch (failure) { setError(errorMessage(failure)) }
        finally { setBusy(false) }
    }
    return <section className="mt-8 border-t pt-6 space-y-4"><h2 className="text-xl font-bold">Подборка кандидатов</h2><p className="text-purple-800">{needs.title || needs.specialization} · {needs.grade}</p>
        <form onSubmit={event => { event.preventDefault(); setPage(1); setQuery({ ...filters }); setDetail(null) }} className="space-y-3">
            <label className="flex items-center gap-2"><input type="checkbox" checked={filters.only_fsp} onChange={event => setFilters(current => ({ ...current, only_fsp: event.target.checked }))} />Только с достижениями ФСП</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={filters.only_verified} onChange={event => setFilters(current => ({ ...current, only_verified: event.target.checked }))} />Только подтверждённые</label>
            <Field label="Минимальный балл теста" type="number" min={0} max={100} value={filters.min_test_score} onChange={value => setFilters(current => ({ ...current, min_test_score: value }))} />
            <Field label="Поиск по тексту" value={filters.text} onChange={value => setFilters(current => ({ ...current, text: value }))} />
            <button className={secondaryClass}>Применить фильтры</button>
        </form>
        <button className={secondaryClass} disabled={busy} onClick={() => { resource.refresh(); setDetail(null) }}>Обновить подборку и доступ к контактам</button>
        <ResourceState resource={resource} /><ErrorNotice message={error} />{notice && <p role="status">{notice}</p>}
        {!resource.loading && !resource.error && resource.data && <>
            <p>Найдено: {resource.data.total}</p><div className="flex flex-wrap gap-2">{(resource.data.categories || []).map(item => <button type="button" key={`${item.specialization}:${item.grade}`} onClick={() => { setPage(1); setDetail(null); setQuery(current => ({ ...current, specialization: item.specialization, grade: item.grade })) }} className="rounded bg-purple-50 p-2 text-sm">{item.category}: {item.count}{item.verified != null && ` · Подтверждены: ${item.verified}`}{item.unverified != null && ` · Без подтверждения: ${item.unverified}`} · ФСП: {item.with_fsp}</button>)}</div>
            {!resource.data.items?.length && <p>По этим условиям кандидатов пока нет.</p>}
            {(resource.data.items || []).map(card => <article key={card.id} className="rounded-xl border p-5"><h3 className="text-lg font-bold">{card.display_name}</h3><p>{card.category || `${card.specialization} · ${card.grade}`}</p><p className="mt-2">Навыки: {(card.skills || []).join(', ')}</p><p>Тест: {card.test_score ?? '—'}/{card.test_max_score || 100} · Опыт: {card.experience_years} лет</p><p className={`mt-2 inline-block rounded px-3 py-1 text-sm ${card.grade_verified ? 'bg-green-50 text-green-800' : 'bg-gray-100 text-gray-700'}`}>{card.grade_status_label || (card.grade_verified ? 'Подтверждён тестом' : 'Не подтверждён: заявлен кандидатом')}</p>
                <p className="mt-2">{card.has_fsp ? `Достижения ФСП${card.fsp_verification === 'demo' ? ' · демо-данные' : card.fsp_verification === 'verified' ? ' · проверено реестром' : ''}` : 'Нет достижений ФСП'}{card.fsp_rank && ` · ${card.fsp_rank}`}</p>
                <p className="mt-2 font-bold text-purple-700">Соответствие: {card.match_score ?? '—'}/100</p><Reasons reasons={card.reasons} breakdown={card.breakdown} />
                {card.invitation_status && <p className="mt-3">Приглашение: {INVITATION_STATUS_LABELS[invitationUiStatus(card.invitation_status)] || card.invitation_status}</p>}
                <div className="mt-4 flex flex-wrap gap-2"><button className={secondaryClass} disabled={busy} onClick={() => open(card.id)}>Открыть карточку</button><button className={buttonClass} disabled={busy || ['sent', 'viewed', 'accepted'].includes(card.invitation_status)} onClick={() => setSelected(card)}>Пригласить</button><button className={secondaryClass} disabled={busy} onClick={() => shortlist(card)}>{card.in_shortlist ? 'Убрать из избранного' : 'В избранное'}</button></div>
                {detail?.id === card.id && <div className="mt-4 space-y-2 rounded-lg bg-gray-50 p-4"><p className="whitespace-pre-wrap">{detail.about || 'Описание не заполнено'}</p><p>Дополнительные навыки: {(detail.soft_skills || []).join(', ') || '—'}</p>
                    {detail.contacts ? <div><h4 className="font-bold">Контакты открыты</h4>{[['full_name', 'ФИО'], ['email', 'Почта'], ['phone', 'Телефон'], ['telegram', 'Telegram']].map(([name, label]) => detail.contacts[name] ? <p key={name} className="break-all">{label}: {detail.contacts[name]}</p> : null)}</div> : <p>{detail.contacts_hidden_reason || 'Контакты откроются, когда кандидат примет приглашение.'}</p>}
                    {(detail.fsp_achievements || []).map((item, index) => <p key={index}>{item.event} · {item.year || '—'} · {item.place ? `${item.place} место` : item.result || 'Участие'}{item.verification_status === 'demo' || item.source === 'fsp_registry_demo' ? ' · демо-данные' : ''}{/^https?:\/\//i.test(item.source_url || '') && <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="ml-2 text-purple-700 underline">Протокол</a>}</p>)}
                </div>}
            </article>)}
            <div className="flex items-center gap-3"><button className={secondaryClass} disabled={page <= 1} onClick={() => { setDetail(null); setPage(value => value - 1) }}>Назад</button><span>Страница {page}</span><button className={secondaryClass} disabled={page * (resource.data.size || 10) >= resource.data.total} onClick={() => { setDetail(null); setPage(value => value + 1) }}>Далее</button></div>
        </>}
        {selected && <InvitationModal candidate={selected} onClose={() => setSelected(null)} onCreate={() => { setSelected(null); setNotice('Приглашение отправлено кандидату.'); resource.refresh() }} />}
    </section>
}
