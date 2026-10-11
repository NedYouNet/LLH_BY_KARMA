import { fspId } from '../api'
import { useResource, secondaryClass, ErrorNotice } from './ui'
export default function FspIdLogin() {
    const resource = useResource(fspId.config)
    if (resource.loading) return <p className="mt-4 text-sm" role="status">Проверяем доступность FSP ID…</p>
    if (resource.error) return <div className="mt-4 text-sm"><ErrorNotice message={`FSP ID пока недоступен: ${resource.error}`} /><button type="button" className={`${secondaryClass} mt-2`} onClick={resource.refresh}>Повторить проверку FSP ID</button></div>
    if (!resource.data?.enabled) return null
    return <div className="mt-5 space-y-3 border-t pt-4">
        <button type="button" onClick={fspId.start} className="w-full rounded-lg bg-purple-700 p-3 text-white">Войти через FSP ID</button>
        {resource.data.mode === 'mock' && <details className="rounded bg-purple-50 p-3 text-sm"><summary className="cursor-pointer">FSP ID: демонстрационная имитация входа</summary><p className="mt-2">После перехода используйте один из демо-аккаунтов:</p><ul className="mt-2 space-y-2">{(resource.data.demo_accounts || []).map(item => <li key={item.email}>{item.name} · {item.email}{item.password && ` · пароль: ${item.password}`}{item.fsp_id && ` · ID: ${item.fsp_id}`}</li>)}</ul><p className="mt-2">После входа отдельно сохраните согласия на обработку и публикацию данных.</p></details>}
    </div>
}
