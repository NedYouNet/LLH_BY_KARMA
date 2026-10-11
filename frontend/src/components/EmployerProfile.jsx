import { useEffect, useState } from 'react'
import { employer, errorMessage } from '../api'
import { Field, buttonClass, ErrorNotice, ResourceState, useResource } from './ui'

const fields = [
    ['company_name', 'Название компании', 200], ['description', 'Описание компании', 5000],
    ['industry', 'Направление деятельности', 255], ['contact', 'Способ связи', 255],
    ['inn', 'ИНН (необязательно)', 12], ['website', 'Сайт', 255], ['city', 'Город', 100],
    ['contact_name', 'Контактное лицо', 200], ['contact_email', 'Рабочая почта', 255],
    ['contact_phone', 'Рабочий телефон', 50], ['contact_telegram', 'Telegram', 100],
]
const toForm = profile => Object.fromEntries(fields.map(([key]) => [key, profile?.[key] || '']))
export default function EmployerProfile() {
    const resource = useResource(employer.getProfile)
    const [form, setForm] = useState(toForm(null))
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState('')
    const [notice, setNotice] = useState('')
    useEffect(() => { if (resource.data) setForm(toForm(resource.data)) }, [resource.data])
    async function submit(event) {
        event.preventDefault()
        if (busy) return
        setError(''); setNotice('')
        if (!form.company_name.trim()) { setError('Введите название компании.'); return }
        if (form.inn && !/^\d{10}(\d{2})?$/.test(form.inn)) { setError('ИНН должен содержать 10 или 12 цифр.'); return }
        const patch = Object.fromEntries(fields.map(([key]) => [key, form[key].trim() || null]).filter(([key, value]) => value !== (resource.data[key] || null)))
        if (!Object.keys(patch).length) { setNotice('Изменений нет.'); return }
        setBusy(true)
        try { resource.setData(await employer.updateProfile(patch)); setNotice('Профиль компании сохранён на сервере.') }
        catch (failure) { setError(errorMessage(failure)) }
        finally { setBusy(false) }
    }
    return <section className="mt-6"><h2 className="text-xl font-bold">Профиль компании</h2><p className="mt-2 text-gray-600">Расскажите о компании и укажите, как с вами связаться.</p><ResourceState resource={resource} />
        {!resource.loading && !resource.error && resource.data && <form onSubmit={submit} className="mt-4 space-y-4"><fieldset disabled={busy} className="space-y-4">
            {fields.map(([name, label, max]) => <Field key={name} label={label} maxLength={max} required={name === 'company_name'} multiline={name === 'description'} type={name === 'contact_email' ? 'email' : 'text'} value={form[name]} onChange={value => { setForm(current => ({ ...current, [name]: value })); setNotice(''); setError('') }} />)}
            <button className={buttonClass}>{busy ? 'Сохраняем…' : 'Сохранить профиль компании'}</button>
        </fieldset><ErrorNotice message={error} />{notice && <p role="status">{notice}</p>}{resource.data.trust_level === 'inn_provided' && <p className="text-sm text-gray-600">ИНН указан. Это не подтверждение проверки компании.</p>}</form>}
    </section>
}
