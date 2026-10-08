import { useEffect, useState } from 'react'
import { candidate, reference, errorMessage } from '../api'
import CandidateTest from './CandidateTest'

const fieldClass = 'w-full rounded-lg border border-gray-300 bg-white p-3'
const buttonClass = 'rounded-lg bg-purple-600 px-6 py-3 text-white disabled:opacity-50'

function options(list) {
    const entries = Array.isArray(list) ? list : Object.entries(list || {}).map(([code, value]) => (
        typeof value === 'string' ? { code, name: value } : { ...value, code }
    ))
    return entries.map(item => typeof item === 'string'
        ? { code: item, name: item }
        : { code: String(item.code ?? item.value ?? item.id ?? ''), name: item.name || item.title_ru || item.label || item.short || item.code }
    ).filter(item => item.code)
}

export default function CandidateQuestionnaire() {
    const [lists, setLists] = useState({ industries: [], specializations: [], grades: [] })
    const [form, setForm] = useState({ industry: '', specialization: '', grade: '' })
    const [profileId, setProfileId] = useState(null)
    const [category, setCategory] = useState(null)
    const [loading, setLoading] = useState(true)
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState('')
    const [loadError, setLoadError] = useState('')
    const [reload, setReload] = useState(0)
    const [selection, setSelection] = useState(null)

    useEffect(() => {
        let active = true
        async function load() {
            setLoading(true)
            setLoadError('')
            try {
                const [data, profile, status] = await Promise.all([
                    reference.all(), candidate.getProfile(), candidate.category(),
                ])
                const nextLists = {
                    industries: options(data.industries),
                    specializations: options(data.specializations),
                    grades: options(data.grades),
                }
                if ([nextLists.specializations, nextLists.grades].some(list => !list.length)) {
                    throw new Error('Сервер вернул пустые справочники анкеты.')
                }
                if (active) {
                    setLists(nextLists)
                    setProfileId(profile.id)
                    setForm({ industry: profile.industry || '', specialization: profile.specialization || '', grade: profile.declared_grade || '' })
                    setCategory(status)
                }
            } catch (failure) {
                if (active) setLoadError(failure instanceof Error && !failure.code ? failure.message : errorMessage(failure))
            } finally { if (active) setLoading(false) }
        }
        load()
        return () => { active = false }
    }, [reload])

    function change(field, value) {
        setForm(current => ({ ...current, [field]: value }))
        setError('')
    }

    async function handleSubmit(event) {
        event.preventDefault()
        if (busy) return
        if (!form.specialization || !form.grade) {
            setError('Выберите IT-направление и предполагаемый грейд.')
            return
        }
        setBusy(true)
        setError('')
        try {
            const currentProfile = await candidate.getProfile()
            const profile = await candidate.submitSurvey({
                industry: form.industry || null, specialization: form.specialization, declared_grade: form.grade,
                experience_years: currentProfile.experience_years ?? 0,
                skills: Array.isArray(currentProfile.skills) ? currentProfile.skills : [],
            })
            setSelection({ ...form, candidateId: profile.id })
        } catch (failure) { setError(errorMessage(failure)) }
        finally { setBusy(false) }
    }

    function back() {
        setSelection(null)
        setError('')
        setReload(value => value + 1)
    }

    if (selection) return <CandidateTest selection={selection} onBack={back} />

    return <section className="mt-8 border-t border-gray-200 pt-6">
        <h2 className="text-xl font-bold">Направление и уровень</h2>
        <p className="mt-2 text-gray-600">Выберите IT-направление и предполагаемый уровень. Сфера бизнеса необязательна. Грейд подтверждается результатом серверного теста.</p>
        {loading && <p role="status" className="mt-4">Загружаем анкету…</p>}
        {loadError && <div role="alert" className="mt-4 space-y-3">
            <p className="text-red-700">{loadError}</p>
            <button type="button" className={buttonClass} onClick={() => setReload(value => value + 1)}>Повторить загрузку</button>
        </div>}
        {!loading && !loadError && <>
            {category?.category && <p className="mt-4 rounded-lg bg-purple-50 p-3 text-purple-800">
                Категория: {category.category}. Балл теста: {category.test_score ?? '—'}.
            </p>}
            {category?.active_attempt_id && <button type="button" className={`${buttonClass} mt-4`} onClick={() => setSelection({ ...form, candidateId: profileId, attemptId: category.active_attempt_id })}>
                Продолжить незавершённый тест
            </button>}
            <form noValidate onSubmit={handleSubmit} className="mt-4 space-y-4">
                <fieldset disabled={busy || Boolean(category?.active_attempt_id)} className="space-y-4">
                    {[
                        ['specialization', 'IT-направление', lists.specializations],
                        ['grade', 'Предполагаемый грейд', lists.grades],
                        ['industry', 'Предпочитаемая сфера бизнеса (необязательно)', lists.industries],
                    ].map(([field, label, items]) => <label key={field} className="block">
                        <span className="mb-1 block">{label}</span>
                        <select required={field !== 'industry'} className={fieldClass} value={form[field]} onChange={event => change(field, event.target.value)}>
                            <option value="">Выберите значение</option>
                            {items.map(item => <option key={item.code} value={item.code}>{item.name}</option>)}
                        </select>
                    </label>)}
                    <button type="submit" className={buttonClass}>{busy ? 'Сохраняем…' : 'Сохранить анкету и перейти к тесту'}</button>
                </fieldset>
                {error && <p role="alert" className="text-red-700">{error}</p>}
            </form>
        </>}
    </section>
}
