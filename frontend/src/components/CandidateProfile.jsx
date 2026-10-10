import { useEffect, useState } from 'react'
import { candidate, errorMessage } from '../api'

const emptyForm = { fullName: '', skills: '', phone: '', experience: '', years: '', telegram: '', city: '', contactEmail: '', softSkills: '', teamRoles: '', workFormat: '', desiredSalary: '' }

function fromProfile(profile) {
    return {
        fullName: profile.full_name || '',
        skills: Array.isArray(profile.skills) ? profile.skills.join(', ') : '',
        phone: profile.phone || '',
        experience: profile.about || '',
        years: profile.experience_years == null ? '' : String(profile.experience_years),
        telegram: profile.telegram || '',
        city: profile.city || '',
        contactEmail: profile.contact_email || profile.email || '',
        softSkills: (profile.soft_skills || []).join(', '),
        teamRoles: (profile.team_roles || []).join(', '),
        workFormat: profile.work_format || '',
        desiredSalary: profile.desired_salary_from == null ? '' : String(profile.desired_salary_from),
    }
}

function toProfile(form) {
    return {
        full_name: form.fullName.trim(),
        skills: [...new Set(form.skills.split(/[,;\n]/).map(value => value.trim()).filter(Boolean))],
        phone: form.phone.trim() || null,
        about: form.experience.trim() || null,
        experience_years: form.years === '' ? 0 : Number(form.years),
        telegram: form.telegram.trim() || null,
        city: form.city.trim() || null,
        contact_email: form.contactEmail.trim() || null,
        soft_skills: [...new Set(form.softSkills.split(/[,;\n]/).map(x => x.trim()).filter(Boolean))],
        team_roles: [...new Set(form.teamRoles.split(/[,;\n]/).map(x => x.trim()).filter(Boolean))],
        work_format: form.workFormat || null,
        desired_salary_from: form.desiredSalary === '' ? null : Number(form.desiredSalary),
    }
}

export default function CandidateProfile() {
    const [form, setForm] = useState(emptyForm)
    const [original, setOriginal] = useState(null)
    const [loading, setLoading] = useState(true)
    const [loadError, setLoadError] = useState('')
    const [retry, setRetry] = useState(0)
    const [busy, setBusy] = useState('')
    const [message, setMessage] = useState('')
    const [saveError, setSaveError] = useState('')
    const [resumeFile, setResumeFile] = useState(null)
    const [fileError, setFileError] = useState('')

    useEffect(() => {
        let active = true
        async function load() {
            setLoading(true)
            setLoadError('')
            try {
                const profile = await candidate.getProfile()
                if (active) {
                    const fields = fromProfile(profile)
                    setForm(fields)
                    setOriginal(toProfile(fields))
                }
            } catch (error) {
                if (active) setLoadError(errorMessage(error))
            } finally {
                if (active) setLoading(false)
            }
        }
        load()
        return () => { active = false }
    }, [retry])

    function change(field, value) {
        setForm(current => ({ ...current, [field]: value }))
        setMessage('')
        setSaveError('')
    }

    async function handleSubmit(event) {
        event.preventDefault()
        if (busy || loading || loadError || !original) return
        const data = toProfile(form)
        setMessage('')
        setSaveError('')
        if (!data.full_name) { setSaveError('Введите ФИО.'); return }
        if (data.full_name.length > 200) { setSaveError('ФИО: максимум 200 символов.'); return }
        if (!Number.isFinite(data.experience_years) || data.experience_years < 0 || data.experience_years > 60) { setSaveError('Опыт: от 0 до 60 лет.'); return }
        if (data.desired_salary_from != null && (!Number.isSafeInteger(data.desired_salary_from) || data.desired_salary_from <= 0 || data.desired_salary_from > 10000000)) { setSaveError('Желаемая зарплата: целое число от 1 до 10 000 000 ₽.'); return }
        if (data.contact_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.contact_email)) { setSaveError('Проверьте контактную почту.'); return }
        if (!data.skills.length) { setSaveError('Укажите свои навыки.'); return }
        if ((data.phone || '').length > 50) { setSaveError('Телефон: максимум 50 символов.'); return }
        if ((data.about || '').length > 5000) { setSaveError('Опыт и проекты: максимум 5000 символов.'); return }
        // Обновляем только поля этой формы, которые действительно изменились.
        const patch = Object.fromEntries(Object.entries(data).filter(([key, value]) => JSON.stringify(value) !== JSON.stringify(original[key])))
        if (!Object.keys(patch).length) { setMessage('Изменений нет. Профиль уже сохранён.'); return }
        setBusy('save')
        try {
            const profile = await candidate.updateProfile(patch)
            const fields = fromProfile(profile)
            setForm(fields)
            setOriginal(toProfile(fields))
            setMessage('Профиль сохранён на сервере.')
        } catch (error) {
            setSaveError(errorMessage(error))
        } finally { setBusy('') }
    }

    function handleFileChange(event) {
        const file = event.target.files?.[0] || null
        setFileError('')
        setMessage('')
        setResumeFile(null)
        if (file && !file.name.toLowerCase().endsWith('.pdf')) {
            setFileError('Выберите файл в формате PDF.')
            event.target.value = ''
            return
        }
        setResumeFile(file)
    }

    async function parseResume() {
        if (!resumeFile || busy || loading || loadError) return
        setBusy('resume')
        setFileError('')
        setMessage('')
        setSaveError('')
        try {
            // Распознаём без записи в профиль: пользователь проверит поля перед сохранением.
            const result = await candidate.parseResume(resumeFile, false)
            const parsed = fromProfile(result.fields || {})
            const filled = Object.entries(parsed).filter(([key, value]) => !form[key].trim() && value.trim())
            if (filled.length) {
                setForm(current => ({ ...current, ...Object.fromEntries(filled) }))
                setMessage('Пустые поля заполнены из резюме. Проверьте их и нажмите «Сохранить профиль».')
            } else {
                setMessage('Резюме обработано. Подходящих данных для пустых полей не найдено; заполненные поля оставлены без изменений.')
            }
        } catch (error) {
            setFileError(errorMessage(error))
        } finally { setBusy('') }
    }

    return <section className="mt-8 border-t border-gray-200 pt-6">
        <h2 className="text-xl font-bold">Профиль кандидата</h2>
        <p className="mt-2 text-gray-600">Данные загружаются из вашего аккаунта. После изменений нажмите «Сохранить профиль».</p>
        {loading && <p role="status" className="mt-4">Загружаем профиль…</p>}
        {loadError && <div role="alert" className="mt-4 space-y-3 rounded-lg bg-red-50 p-3 text-red-800">
            <p>{loadError}</p>
            <button type="button" onClick={() => setRetry(value => value + 1)} className="rounded-lg bg-purple-100 px-4 py-2 text-purple-800">Повторить загрузку</button>
        </div>}
        {!loading && !loadError && original && <form noValidate onSubmit={handleSubmit} className="mt-4 space-y-4">
            <fieldset disabled={Boolean(busy)} className="space-y-4">
                <label className="block">
                    <span className="mb-1 block">ФИО</span>
                    <input type="text" autoComplete="name" required maxLength={200} value={form.fullName} onChange={event => change('fullName', event.target.value)} className="w-full rounded-lg border border-gray-300 p-3" />
                </label>
                <label className="block">
                    <span className="mb-1 block">Навыки</span>
                    <textarea rows={5} required placeholder="Например: JavaScript, React, Git" value={form.skills} onChange={event => change('skills', event.target.value)} className="w-full rounded-lg border border-gray-300 p-3" />
                    <span className="text-sm text-gray-600">Перечислите через запятую или с новой строки.</span>
                </label>
                <label className="block">
                    <span className="mb-1 block">Телефон</span>
                    <input type="tel" autoComplete="tel" maxLength={50} placeholder="+7…" value={form.phone} onChange={event => change('phone', event.target.value)} className="w-full rounded-lg border border-gray-300 p-3" />
                </label>
                <label className="block">Опыт в годах
                    <input type="number" min="0" max="60" step="0.5" value={form.years} onChange={event => change('years', event.target.value)} className="mt-1 w-full rounded-lg border p-3" />
                </label>
                {Object.entries({ contactEmail: 'Контактная почта', softSkills: 'Soft skills через запятую', teamRoles: 'Командные роли через запятую', telegram: 'Telegram', city: 'Город' }).map(([key, title]) => <label key={key} className="block">{title}<input type={key === 'contactEmail' ? 'email' : 'text'} maxLength={key === 'softSkills' || key === 'teamRoles' ? 2000 : 100} value={form[key]} onChange={event => change(key, event.target.value)} className="mt-1 w-full rounded-lg border p-3" /></label>)}
                <label className="block">
                    <span className="mb-1 block">Опыт и проекты</span>
                    <textarea rows={5} maxLength={5000} placeholder="Работа, задачи, учебные проекты" value={form.experience} onChange={event => change('experience', event.target.value)} className="w-full rounded-lg border border-gray-300 p-3" />
                </label>
                <label className="block">Формат работы<select className="mt-1 w-full rounded-lg border p-3" value={form.workFormat} onChange={e => change('workFormat', e.target.value)}><option value="">Не выбран</option><option value="remote">Удалённо</option><option value="office">В офисе</option><option value="hybrid">Гибрид</option></select></label>
                <label className="block">Желаемая зарплата от, ₽<input className="mt-1 w-full rounded-lg border p-3" type="number" min={1} max={10000000} step={1} value={form.desiredSalary} onChange={e => change('desiredSalary', e.target.value)} /></label>
                <label className="block">
                    <span className="mb-1 block">Резюме в PDF</span>
                    <input type="file" accept=".pdf,application/pdf" onChange={handleFileChange} className="block w-full text-sm file:mr-4 file:rounded-lg file:border-0 file:bg-purple-100 file:px-4 file:py-2 file:text-purple-800 file:cursor-pointer" />
                </label>
                {resumeFile && <div className="space-y-2">
                    <p className="text-gray-600">Выбран файл: {resumeFile.name}</p>
                    <button type="button" onClick={parseResume} className="rounded-lg bg-purple-100 px-4 py-2 text-purple-800">{busy === 'resume' ? 'Распознаём резюме…' : 'Заполнить пустые поля из PDF'}</button>
                </div>}
                <button type="submit" className="rounded-lg bg-purple-600 px-6 py-3 text-white hover:bg-purple-700 cursor-pointer disabled:opacity-50">{busy === 'save' ? 'Сохраняем…' : 'Сохранить профиль'}</button>
            </fieldset>
            {busy === 'resume' && <p role="status">Распознаём резюме… Это может занять около 20 секунд.</p>}
            {fileError && <p role="alert" className="text-red-700">{fileError}</p>}
            {saveError && <p role="alert" className="text-red-700">{saveError}</p>}
            {message && <p role="status">{message}</p>}
        </form>}
    </section>
}
