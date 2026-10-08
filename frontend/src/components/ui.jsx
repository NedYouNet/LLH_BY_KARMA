import { useEffect, useState } from 'react'
import { errorMessage } from '../api'

export const inputClass = 'mt-1 w-full rounded-lg border border-gray-300 bg-white p-3'
export const buttonClass = 'rounded-lg bg-purple-600 px-4 py-2 text-white hover:bg-purple-700 disabled:opacity-50'
export const secondaryClass = 'rounded-lg bg-purple-100 px-4 py-2 text-purple-800 disabled:opacity-50'
export const money = value => new Intl.NumberFormat('ru-RU').format(value ?? 0)
export const date = value => value ? new Date(value).toLocaleString('ru-RU') : '—'
export function listOptions(list) {
    const items = Array.isArray(list) ? list : Object.entries(list || {}).map(([code, value]) => typeof value === 'string' ? { code, name: value } : { ...value, code })
    return items.map(item => typeof item === 'string' ? { code: item, name: item } : { code: String(item.code ?? item.value ?? item.id ?? ''), name: item.name || item.title_ru || item.label || item.short || item.code }).filter(item => item.code)
}
export function useResource(loader) {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [revision, setRevision] = useState(0)
    useEffect(() => {
        let active = true
        setLoading(true)
        setError('')
        Promise.resolve().then(loader).then(value => { if (active) setData(value) }).catch(failure => { if (active) setError(errorMessage(failure)) }).finally(() => { if (active) setLoading(false) })
        return () => { active = false }
    }, [loader, revision])
    return { data, setData, loading, error, refresh: () => setRevision(value => value + 1) }
}
export function ResourceState({ resource }) {
    if (resource.loading) return <p role="status" className="mt-4">Загружаем данные…</p>
    if (resource.error) return <div className="mt-4 space-y-2"><ErrorNotice message={resource.error} /><button type="button" className={secondaryClass} onClick={resource.refresh}>Повторить загрузку</button></div>
    return null
}
export function ErrorNotice({ message }) {
    return message ? <p role="alert" className="mt-3 whitespace-pre-wrap rounded-lg bg-red-50 p-3 text-red-800">{message}</p> : null
}
export function Field({ label, value, onChange, type = 'text', multiline = false, ...props }) {
    return <label className="block"><span>{label}</span>{multiline ? <textarea rows={4} value={value ?? ''} onChange={event => onChange(event.target.value)} className={inputClass} {...props} /> : <input type={type} value={value ?? ''} onChange={event => onChange(event.target.value)} className={inputClass} {...props} />}</label>
}
export function Reasons({ reasons = [], breakdown }) {
    const labels = { test: 'Тест', skills: 'Навыки', fsp: 'ФСП', experience: 'Опыт', activity: 'Активность', text: 'Описание', strengths: 'Сильные стороны' }
    return <div className="mt-3 space-y-2">
        {reasons.map((reason, index) => <p key={index} className={`rounded-lg p-2 text-sm ${reason.positive ? 'bg-green-50 text-green-800' : 'bg-amber-50 text-amber-900'}`}>{reason.label}{reason.missing?.length ? ` · Не хватает: ${reason.missing.join(', ')}` : ''}</p>)}
        {breakdown && <details><summary className="cursor-pointer text-sm text-purple-700">Вклад в оценку соответствия</summary>{Object.entries(breakdown).map(([key, raw]) => {
            const value = typeof raw === 'number' ? raw : raw?.contribution ?? raw?.score
            return typeof value === 'number' ? <div key={key} className="mt-2 text-sm"><p>{labels[key] || key}: {value.toFixed(1)}</p><div className="h-2 rounded bg-gray-100"><div className="h-2 rounded bg-purple-500" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} /></div></div> : null
        })}</details>}
    </div>
}
