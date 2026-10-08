import { useEffect, useState } from 'react'
import { employer, errorMessage } from '../api'
import { useResource, ResourceState, ErrorNotice, Field, buttonClass, secondaryClass, date } from './ui'
export default function EmployerIntegrations() {
    const resource = useResource(employer.atsConfig)
    const [url, setUrl] = useState('')
    const [secret, setSecret] = useState('')
    const [busy, setBusy] = useState('')
    const [error, setError] = useState('')
    const [notice, setNotice] = useState('')
    useEffect(() => { if (resource.data) setUrl(resource.data.webhook_url || '') }, [resource.data])
    async function action(name, operation) {
        if (busy) return
        setBusy(name); setError(''); setNotice(''); setSecret('')
        try {
            const result = await operation()
            if (result?.secret) setSecret(result.secret)
            if (name === 'test') setNotice(result?.ok ? `Проверка успешна${result.status_code ? ` (${result.status_code})` : ''}.` : `Проверка не прошла: ${result?.error || result?.status_code || 'сервер не подтвердил доставку'}`)
            else setNotice(name === 'disable' ? 'Интеграция отключена.' : 'Интеграция сохранена.')
            resource.refresh()
        } catch (failure) { setError(errorMessage(failure)) }
        finally { setBusy('') }
    }
    function save(event) {
        event.preventDefault()
        let parsed
        try { parsed = new URL(url.trim()) } catch { setError('Введите полный HTTPS-адрес вебхука.'); return }
        if (parsed.protocol !== 'https:' || parsed.username || parsed.password) { setError('Используйте HTTPS-адрес без логина и пароля в URL.'); return }
        action('save', () => employer.configureAts(url.trim()))
    }
    return <section className="mt-6 space-y-4"><h2 className="text-xl font-bold">Интеграция с ATS</h2><p>Укажите адрес вебхука вашей системы подбора. Проверка отправляет тестовый запрос на этот адрес.</p><ResourceState resource={resource} /><ErrorNotice message={error} />{notice && <p role="status">{notice}</p>}
        {secret && <div className="rounded border border-amber-300 bg-amber-50 p-4"><p>Сохраните секрет сейчас. После закрытия этого экрана он больше не будет показан.</p><code className="mt-2 block break-all select-all">{secret}</code><button type="button" className={`${secondaryClass} mt-3`} onClick={() => setSecret('')}>Секрет сохранён, скрыть</button></div>}
        {!resource.loading && !resource.error && resource.data && <>
            <p>{resource.data.enabled ? 'Включена' : 'Отключена'}</p>
            <form onSubmit={save} className="space-y-3"><fieldset disabled={Boolean(busy)} className="space-y-3"><Field label="HTTPS-адрес вебхука" type="url" required maxLength={2000} value={url} onChange={setUrl} /><button className={buttonClass}>Сохранить интеграцию</button></fieldset></form>
            <div className="flex flex-wrap gap-2"><button type="button" className={secondaryClass} disabled={Boolean(busy) || !resource.data.enabled} onClick={() => action('test', employer.testAts)}>Отправить тестовый запрос</button><button type="button" className={secondaryClass} disabled={Boolean(busy) || !resource.data.enabled} onClick={() => { if (window.confirm('Сменить секрет? Затем обновите его в вашей ATS.')) action('rotate', () => employer.configureAts(resource.data.webhook_url, true)) }}>Сменить секрет</button><button type="button" className={secondaryClass} disabled={Boolean(busy) || !resource.data.enabled} onClick={() => { if (window.confirm('Отключить интеграцию с ATS?')) action('disable', employer.disableAts) }}>Отключить</button></div>
            <h3 className="font-semibold">Последние доставки</h3>{!resource.data.recent_deliveries?.length && <p>Доставок пока нет.</p>}
            <ul className="space-y-2">{(resource.data.recent_deliveries || []).map((item, index) => <li key={item.id || index} className="rounded border p-3">{date(item.created_at || item.delivered_at)} · {item.event || item.event_type || 'Событие'} · {item.status_code ?? item.status ?? (item.ok === true ? 'Успешно' : 'Результат не указан')}{item.error && ` · ${item.error}`}</li>)}</ul>
        </>}
    </section>
}
