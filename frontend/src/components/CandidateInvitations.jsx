import { useState } from 'react'
import { invitations, invitationUiStatus, INVITATION_STATUS_LABELS, errorMessage } from '../api'
import { buttonClass, secondaryClass, Field, ErrorNotice, ResourceState, useResource, money, date, Reasons } from './ui'

export default function CandidateInvitations({ role = 'candidate' }) {
    const resource = useResource(invitations.list)
    const [opened, setOpened] = useState(null)
    const [replies, setReplies] = useState({})
    const [busy, setBusy] = useState(null)
    const [error, setError] = useState('')
    const [notice, setNotice] = useState('')
    const items = Array.isArray(resource.data) ? resource.data : resource.data?.items || []
    function update(item) {
        resource.setData(current => Array.isArray(current) ? current.map(row => row.id === item.id ? item : row) : { ...current, items: (current?.items || []).map(row => row.id === item.id ? item : row) })
    }
    async function open(id) {
        if (busy) return
        setBusy(id); setError('')
        try { update(await invitations.get(id)); setOpened(id) }
        catch (failure) { setError(errorMessage(failure)) }
        finally { setBusy(null) }
    }
    async function answer(id, status) {
        if (busy) return
        setBusy(id); setError(''); setNotice('')
        try {
            const item = role === 'candidate' ? await invitations.answer(id, status, replies[id]?.trim() || undefined) : await invitations.withdraw(id)
            update(item?.id ? item : await invitations.get(id))
            setNotice(role === 'candidate' ? 'Ответ сохранён и доступен работодателю.' : 'Приглашение отозвано.')
        } catch (failure) {
            setError(errorMessage(failure))
            if (failure.status === 409) resource.refresh()
        } finally { setBusy(null) }
    }
    async function changeContactAccess(item, granted) {
        if (busy) return
        setBusy(item.id); setError(''); setNotice('')
        try {
            const result = await invitations.setContactAccess(item.id, granted)
            update(result?.id ? result : await invitations.get(item.id))
            setNotice(granted ? 'Доступ к контактам открыт для этой компании.' : 'Доступ к контактам закрыт для этой компании.')
        } catch (failure) { setError(errorMessage(failure)) }
        finally { setBusy(null) }
    }
    return <section className="mt-6 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-xl font-bold">{role === 'candidate' ? 'Входящие приглашения' : 'Отправленные приглашения'}</h2><button type="button" className={secondaryClass} disabled={Boolean(busy)} onClick={resource.refresh}>Обновить</button></div>
        <ResourceState resource={resource} /><ErrorNotice message={error} />
        {notice && <p role="status">{notice}</p>}
        {!resource.loading && !resource.error && !items.length && <p>Пока приглашений нет.</p>}
        {!resource.loading && !resource.error && items.map(item => {
            const pending = invitationUiStatus(item.status) === 'pending'
            return <article key={item.id} className="rounded-xl border border-gray-200 p-5">
                <p className="text-sm text-gray-600">{role === 'candidate' ? item.company?.company_name : item.candidate?.display_name}</p>
                <h3 className="mt-1 text-lg font-bold">{item.position_title}</h3>
                <p className="mt-3 text-2xl font-bold text-purple-700">{money(item.salary_from)} — {money(item.salary_to)} ₽<span className="ml-2 text-sm font-normal">{item.salary_type_label || (item.salary_type === 'net' ? 'на руки' : 'до вычета НДФЛ')}</span></p>
                <p className={`mt-2 rounded p-2 ${pending ? 'bg-amber-50' : item.status === 'accepted' ? 'bg-green-50' : 'bg-gray-100'}`}>{INVITATION_STATUS_LABELS[invitationUiStatus(item.status)] || item.status}</p>
                <p className="mt-2 text-sm text-gray-600">Отправлено: {date(item.created_at)}</p>
                {opened !== item.id ? <button type="button" className={`${secondaryClass} mt-3`} disabled={Boolean(busy)} onClick={() => open(item.id)}>Открыть предложение</button> : <div className="mt-3 space-y-3">
                    <p className="whitespace-pre-wrap">{item.message}</p><p>Связь с работодателем: {item.contact_method}</p>
                    {item.company?.trust_level === 'inn_provided' && <p className="text-sm">ИНН компании указан</p>}
                    <Reasons reasons={item.match_reasons} />
                    {item.candidate_reply && <p>Ответ кандидата: {item.candidate_reply}</p>}
                    {pending && role === 'candidate' && <><Field label="Комментарий к ответу (необязательно)" multiline maxLength={2000} value={replies[item.id] || ''} disabled={Boolean(busy)} onChange={value => setReplies(current => ({ ...current, [item.id]: value }))} /><p className="text-sm text-gray-600">При принятии приглашения компания получит доступ к вашим контактам.</p><div className="flex gap-3"><button type="button" className={buttonClass} disabled={Boolean(busy)} onClick={() => answer(item.id, 'accepted')}>Принять</button><button type="button" className={secondaryClass} disabled={Boolean(busy)} onClick={() => answer(item.id, 'rejected')}>Отклонить</button></div></>}
                    {item.status === 'accepted' && role === 'candidate' && <label className="flex items-center gap-2"><input type="checkbox" checked={!item.contacts_revoked} disabled={Boolean(busy)} onChange={event => changeContactAccess(item, event.target.checked)} />Компания видит мои контакты</label>}
                    {item.status === 'accepted' && role === 'employer' && <p>{item.contacts_revoked ? 'Кандидат закрыл доступ к контактам.' : 'Кандидат разрешил доступ к контактам.'}</p>}
                    {pending && role === 'employer'  && <button type="button" className={secondaryClass} disabled={Boolean(busy)} onClick={() => answer(item.id)}>Отозвать приглашение</button>}
                    <button type="button" className="block text-purple-700 underline" onClick={() => setOpened(null)}>Свернуть</button>
                </div>}
            </article>
        })}
    </section>
}
