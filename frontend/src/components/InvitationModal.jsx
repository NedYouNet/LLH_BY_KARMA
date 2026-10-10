import { useEffect, useRef, useState } from 'react'
import { employer, invitations, errorMessage } from '../api'
import { buttonClass, secondaryClass, Field, ErrorNotice } from './ui'

export default function InvitationModal({ candidate, vacancy, onClose, onCreate }) {
    const dialogRef = useRef(null)
    const [company, setCompany] = useState(null)
    const [loading, setLoading] = useState(true)
    const [form, setForm] = useState({ position_title: vacancy?.title || '', message: '', salary_from: vacancy?.salary_from || '', salary_to: vacancy?.salary_to || '', salary_type: vacancy?.salary_type || 'gross', contact_method: '' })
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState('')
    useEffect(() => {
        const dialog = dialogRef.current
        dialog.showModal()
        let active = true
        employer.getProfile().then(profile => {
            if (active) { setCompany(profile); setForm(current => ({ ...current, contact_method: profile.contact || profile.contact_email || profile.contact_telegram || profile.contact_phone || '' })) }
        }).catch(failure => { if (active) setError(errorMessage(failure)) }).finally(() => { if (active) setLoading(false) })
        return () => { active = false; dialog.close() }
    }, [])
    async function submit(event) {
        event.preventDefault()
        if (busy || loading) return
        setError('')
        const from = Number(form.salary_from), to = Number(form.salary_to)
        if (!Number.isSafeInteger(from) || !Number.isSafeInteger(to) || from <= 0 || to < from || to > 10000000) { setError('Укажите целые суммы от 1 до 10 000 000 ₽. Верхняя граница не меньше нижней.'); return }
        if (!company?.company_name?.trim()) { setError('Сначала сохраните название компании в её профиле.'); return }
        setBusy(true)
        try {
            const result = await invitations.create({ candidate_id: candidate.id, vacancy_id: vacancy?.id, position_title: form.position_title.trim() || undefined, message: form.message.trim(), salary_from: from, salary_to: to, salary_type: form.salary_type, contact_method: form.contact_method.trim() || undefined })
            onCreate(result)
        } catch (failure) { setError(errorMessage(failure)) }
        finally { setBusy(false) }
    }
    const change = (name, value) => { setForm(current => ({ ...current, [name]: value })); setError('') }
    return <dialog ref={dialogRef} aria-labelledby="invitation-title" onCancel={event => { event.preventDefault(); if (!busy) onClose() }} className="m-auto max-h-[90vh] w-[calc(100%-2rem)] max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-xl backdrop:bg-black/40">
        <h2 id="invitation-title" className="text-xl font-bold">Приглашение: {candidate.display_name}</h2>
        {loading ? <p role="status">Загружаем профиль компании…</p> : <p className="mt-2 text-gray-600">{company?.company_name || 'Название компании не заполнено'}</p>}
        <form onSubmit={submit} className="mt-4 space-y-4"><fieldset disabled={busy || loading} className="space-y-4">
            <Field label="Должность" maxLength={200} value={form.position_title} onChange={value => change('position_title', value)} />
            <Field label="Описание предложения" multiline required minLength={3} maxLength={5000} value={form.message} onChange={value => change('message', value)} />
            <div className="grid grid-cols-2 gap-3">{[['salary_from', 'Зарплата от, ₽'], ['salary_to', 'Зарплата до, ₽']].map(([name, label]) => <Field key={name} label={label} type="number" required min={1} max={10000000} step={1} value={form[name]} onChange={value => change(name, value)} />)}</div>
            <label className="block">Сумма зарплаты<select value={form.salary_type} onChange={event => change('salary_type', event.target.value)} className="mt-1 w-full rounded-lg border p-3"><option value="gross">До вычета НДФЛ</option><option value="net">На руки</option></select></label>
            <Field label="Связь с работодателем" minLength={3} maxLength={255} required value={form.contact_method} onChange={value => change('contact_method', value)} />
            <button type="submit" className={buttonClass}>{busy ? 'Отправляем…' : 'Отправить приглашение'}</button>
        </fieldset><ErrorNotice message={error} /></form>
        <button type="button" disabled={busy} className={`${secondaryClass} mt-4`} onClick={onClose}>Отмена</button>
    </dialog>
}
