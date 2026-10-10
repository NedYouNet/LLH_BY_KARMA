import { useRef, useState } from 'react'
import { candidates, errorMessage, invitationUiStatus, INVITATION_STATUS_LABELS } from '../api'
import InvitationModal from './InvitationModal'
import { Reasons, ErrorNotice, buttonClass, secondaryClass, date } from './ui'

export default function CandidateCard({ card, vacancy, onChanged, allowInvite = true, disabled = false }) {
    const [detail, setDetail] = useState(null)
    const [busy, setBusy] = useState('')
    const [error, setError] = useState('')
    const [invite, setInvite] = useState(false)
    const lock = useRef(false)
    async function act(kind, operation) {
        if (lock.current || disabled) return
        lock.current = true; setBusy(kind); setError('')
        try { await operation() } catch (e) { setError(errorMessage(e)) }
        finally { lock.current = false; setBusy('') }
    }
    const visible = detail || card
    return <article className="space-y-3 rounded-xl border p-5">
        <h3 className="text-lg font-bold">{card.display_name}</h3>
        <p>{card.category || `${card.specialization || '—'} · ${card.grade || '—'}`}</p>
        <p>Навыки: {(card.skills || []).join(', ') || '—'}</p>
        <p>Опыт: {card.experience_years ?? '—'} лет · Тест: {card.test_score == null ? 'не пройден' : `${card.test_score}/${card.test_max_score || 100}`}</p>
        <p className={card.grade_verified ? 'text-green-800' : 'text-gray-600'}>{card.grade_status_label || (card.grade_verified ? 'Подтверждён тестом' : 'Грейд заявлен кандидатом')}</p>
        <p>{card.has_fsp ? 'Есть достижения ФСП' : 'Нет достижений ФСП'}{card.fsp_verification === 'demo' && ' · демо-данные'}{card.fsp_rank && ` · ${card.fsp_rank}`}</p>
        {card.match_score != null && <p className="font-bold text-purple-700">Соответствие условиям поиска: {card.match_score}/100</p>}
        <Reasons reasons={card.reasons} breakdown={card.breakdown} />
        {card.invitation_status && <p>Приглашение: {INVITATION_STATUS_LABELS[invitationUiStatus(card.invitation_status)] || card.invitation_status}</p>}
        <div className="flex flex-wrap gap-2">
            <button type="button" className={secondaryClass} disabled={Boolean(busy) || disabled} onClick={() => act('detail', async () => { setDetail(null); setDetail(await candidates.get(card.id, vacancy?.id)) })}>{busy === 'detail' ? 'Загружаем…' : detail ? 'Обновить карточку и контакты' : 'Открыть карточку'}</button>
            <button type="button" className={secondaryClass} disabled={Boolean(busy) || disabled} onClick={() => act('shortlist', async () => { if (card.in_shortlist) await candidates.removeFromShortlist(card.id); else await candidates.addToShortlist(card.id); onChanged?.() })}>{card.in_shortlist ? 'Убрать из избранного' : 'В избранное'}</button>
            {allowInvite && <button type="button" className={buttonClass} disabled={disabled || Boolean(busy) || ['sent', 'viewed', 'accepted'].includes(card.invitation_status)} onClick={() => setInvite(true)}>Пригласить</button>}
        </div>
        <ErrorNotice message={error} />
        {detail && <div className="space-y-2 border-t pt-3">
            <p className="whitespace-pre-wrap">{detail.about || 'Описание не заполнено'}</p>
            <p>Soft skills: {(detail.soft_skills || []).join(', ') || '—'}</p>
            <p>Командные роли: {(detail.team_roles || []).join(', ') || '—'}</p>
            <p>Последняя активность: {date(detail.last_activity_at)}</p>
            {(detail.fsp_achievements || []).map((a, i) => <p key={i}>{a.event} · {a.year || '—'} · {a.place ? `${a.place} место` : a.result || 'Участие'}{a.verification_status === 'demo' && ' · демо-данные'}{/^https?:\/\//i.test(a.source_url || '') && <a className="ml-2 text-purple-700 underline" href={a.source_url} target="_blank" rel="noopener noreferrer">Протокол</a>}</p>)}
        </div>}
        {visible.contacts ? <div><h4 className="font-bold">Контакты открыты</h4>{Object.entries({ full_name: 'ФИО', email: 'Почта', phone: 'Телефон', telegram: 'Telegram' }).map(([k, label]) => visible.contacts[k] && <p className="break-all" key={k}>{label}: {visible.contacts[k]}</p>)}</div> : detail && <p>{detail.contacts_hidden_reason || 'Контакты пока закрыты.'}</p>}
        {invite && <InvitationModal candidate={card} vacancy={vacancy} onClose={() => setInvite(false)} onCreate={() => { setInvite(false); onChanged?.() }} />}
    </article>
}
