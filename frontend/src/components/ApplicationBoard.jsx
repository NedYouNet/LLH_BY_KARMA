import { useCallback, useRef, useState } from 'react'
import { applications, errorMessage } from '../api'
import { useResource, ResourceState, Field, ErrorNotice, secondaryClass, date } from './ui'
import { VacancySummary, applicationLabels } from './WorkFields'
import CandidateCard from './CandidateCard'
export default function ApplicationBoard({ role }) {
    const owner = role === 'employer'
    const loader = useCallback(() => applications.list(), [])
    const resource = useResource(loader)
    const [comments, setComments] = useState({})
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState('')
    const lock = useRef(false)
    async function update(item, status) {
        if (lock.current) return
        lock.current = true; setBusy(true); setError('')
        try { if (owner) await applications.setStatus(item.id, status, comments[item.id]?.trim() || null); else await applications.withdraw(item.id); resource.refresh() }
        catch (e) { setError(errorMessage(e)) }
        finally { lock.current = false; setBusy(false) }
    }
    return <section className="mt-6 space-y-4"><h2 className="text-xl font-bold">{owner ? 'Отклики на вакансии' : 'Мои отклики'}</h2><button type="button" className={secondaryClass} disabled={busy} onClick={resource.refresh}>Обновить статусы и контакты</button><ResourceState resource={resource} /><ErrorNotice message={error} />
        {!resource.loading && !resource.error && <>{!resource.data?.length && <p>Откликов пока нет.</p>}{(resource.data || []).map(item => <article className="space-y-3 rounded-xl border p-5" key={item.id}><VacancySummary vacancy={item.vacancy} /><p className="font-bold">Статус: {applicationLabels[item.status] || item.status}</p><p>Отправлен: {date(item.created_at)}</p><p className="whitespace-pre-wrap">Письмо: {item.cover_letter || 'Не приложено'}</p>{item.employer_comment && <p className="whitespace-pre-wrap">Ответ работодателя: {item.employer_comment}</p>}
            {owner && item.candidate && <CandidateCard key={`${item.id}:${item.status}`} card={item.candidate} vacancy={item.vacancy} allowInvite={false} onChanged={resource.refresh} />}
            {['sent', 'viewed'].includes(item.status) && (owner ? <div className="space-y-2"><Field label="Комментарий кандидату" multiline maxLength={2000} value={comments[item.id] || ''} onChange={v => setComments(x => ({ ...x, [item.id]: v }))} /><div className="flex flex-wrap gap-2">{(item.status === 'sent' ? ['viewed', 'accepted', 'rejected'] : ['accepted', 'rejected']).map(s => <button type="button" key={s} className={secondaryClass} disabled={busy} onClick={() => update(item, s)}>{{ viewed: 'Отметить просмотренным', accepted: 'Принять', rejected: 'Отклонить' }[s]}</button>)}</div></div> : <button type="button" className={secondaryClass} disabled={busy} onClick={() => { if (window.confirm('Отозвать этот отклик?')) update(item) }}>Отозвать отклик</button>)}
        </article>)}</>}
    </section>
}
