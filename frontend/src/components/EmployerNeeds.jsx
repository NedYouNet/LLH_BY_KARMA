import { useCallback, useState } from 'react'
import { employer, reference, parseStack, errorMessage } from '../api'
import EmployerCandidates from './EmployerCandidates'
import { Field, buttonClass, secondaryClass, inputClass, ErrorNotice, ResourceState, useResource, listOptions } from './ui'
const empty = { title: '', specialization: '', grade: '', stack: '', description: '' }
export default function EmployerNeeds() {
    const loader = useCallback(() => Promise.all([employer.listNeeds(), reference.all()]), [])
    const resource = useResource(loader)
    const [form, setForm] = useState(empty)
    const [editing, setEditing] = useState(null)
    const [applied, setApplied] = useState(null)
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState('')
    const [notice, setNotice] = useState('')
    const rows = Array.isArray(resource.data?.[0]) ? resource.data[0] : resource.data?.[0]?.items || []
    const dictionaries = resource.data?.[1] || {}
    function edit(need) { setEditing(need.id); setForm({ title: need.title || '', specialization: need.specialization, grade: need.grade, stack: (need.stack || []).join(', '), description: need.description || '' }); setError(''); setNotice('') }
    async function submit(event) {
        event.preventDefault()
        if (busy) return
        if (!form.specialization || !form.grade || !parseStack(form.stack).length) { setError('Выберите специализацию, грейд и укажите технологии.'); return }
        setBusy(true); setError(''); setNotice('')
        try {
            const data = { title: form.title.trim() || null, specialization: form.specialization, grade: form.grade, stack: parseStack(form.stack), description: form.description.trim() || null }
            const saved = editing ? await employer.updateNeed(editing, data) : await employer.createNeed(data)
            setEditing(null); setForm(empty); setApplied(saved); resource.refresh(); setNotice('Потребность сохранена. Подборка рассчитывается сервером.')
        } catch (failure) { setError(errorMessage(failure)) }
        finally { setBusy(false) }
    }
    async function remove(id) {
        if (busy || !window.confirm('Удалить эту потребность компании?')) return
        setBusy(true); setError('')
        try { await employer.deleteNeed(id); if (applied?.id === id) setApplied(null); if (editing === id) { setEditing(null); setForm(empty) } resource.refresh() }
        catch (failure) { setError(errorMessage(failure)) }
        finally { setBusy(false) }
    }
    return <section className="mt-8 border-t border-gray-200 pt-6"><h2 className="text-xl font-bold">Кого ищет компания</h2><ResourceState resource={resource} /><ErrorNotice message={error} />{notice && <p role="status" className="mt-3">{notice}</p>}
        {!resource.loading && !resource.error && <>
            <div className="mt-4 space-y-3">{!rows.length && <p>Потребностей пока нет. Создайте первую.</p>}{rows.map(need => <article key={need.id} className="rounded-lg border p-4"><h3 className="font-bold">{need.title || `${need.specialization} · ${need.grade}`}</h3><p>{(need.stack || []).join(', ')}</p><p className="mt-2 whitespace-pre-wrap">{need.description}</p><div className="mt-3 flex flex-wrap gap-2"><button className={buttonClass} disabled={busy} onClick={() => setApplied(need)}>Подобрать кандидатов</button><button className={secondaryClass} disabled={busy} onClick={() => edit(need)}>Изменить</button><button className={secondaryClass} disabled={busy} onClick={() => remove(need.id)}>Удалить</button></div></article>)}</div>
            <form onSubmit={submit} className="mt-5 space-y-4"><h3 className="font-bold">{editing ? 'Изменение потребности' : 'Новая потребность'}</h3><fieldset disabled={busy} className="space-y-4">
                <Field label="Название" maxLength={200} value={form.title} onChange={value => setForm(current => ({ ...current, title: value }))} />
                {[['specialization', 'Специализация', dictionaries.specializations], ['grade', 'Требуемый грейд', dictionaries.grades]].map(([name, label, values]) => <label key={name} className="block">{label}<select required className={inputClass} value={form[name]} onChange={event => setForm(current => ({ ...current, [name]: event.target.value }))}><option value="">Выберите значение</option>{listOptions(values).map(item => <option key={item.code} value={item.code}>{item.name}</option>)}</select></label>)}
                <Field label="Требуемые технологии через запятую" required value={form.stack} onChange={value => setForm(current => ({ ...current, stack: value }))} />
                <Field label="Задачи и команда" multiline maxLength={5000} value={form.description} onChange={value => setForm(current => ({ ...current, description: value }))} />
                <button className={buttonClass}>{busy ? 'Сохраняем…' : 'Сохранить и подобрать кандидатов'}</button>{editing && <button type="button" className={`${secondaryClass} ml-2`} onClick={() => { setEditing(null); setForm(empty) }}>Отменить редактирование</button>}
            </fieldset></form>
        </>}
        {applied && <EmployerCandidates key={`${applied.id}:${applied.updated_at || ''}`} needs={applied} />}
    </section>
}
