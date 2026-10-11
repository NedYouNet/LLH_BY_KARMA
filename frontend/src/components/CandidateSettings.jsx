import { useEffect, useState } from 'react'
import { candidate, errorMessage } from '../api'
import {
    buttonClass,
    secondaryClass,
    Field,
    useResource,
    ResourceState,
    ErrorNotice,
    date,
} from './ui'

const privacyFields = {
    show_full_name: 'Показывать ФИО в поиске',
    show_city: 'Показывать город',
    show_about: 'Показывать описание профиля',
    show_fsp_achievements: 'Показывать достижения ФСП',
}

export default function CandidateSettings() {
    const resource = useResource(candidate.getProfile)

    const [consents, setConsents] = useState({
        consent_processing: false,
        consent_publication: false,
    })
    const [privacy, setPrivacy] = useState({})
    const [fspId, setFspId] = useState('')
    const [password, setPassword] = useState('')
    const [log, setLog] = useState(null)
    const [busy, setBusy] = useState('')
    const [error, setError] = useState('')
    const [notice, setNotice] = useState('')

    useEffect(() => {
        if (!resource.data) return

        setConsents({
            consent_processing: Boolean(resource.data.consent_processing),
            consent_publication: Boolean(resource.data.consent_publication),
        })

        setPrivacy(
            Object.fromEntries(
                Object.keys(privacyFields).map(key => [
                    key,
                    Boolean(resource.data.privacy?.[key]),
                ])
            )
        )

        setFspId(resource.data.fsp_id || '')
    }, [resource.data])

    async function action(name, operation, changesProfile = false) {
        if (busy || resource.loading) return

        setBusy(name)
        setError('')
        setNotice('')

        try {
            const result = await operation()

            if (changesProfile) {
                try {
                    resource.setData(await candidate.getProfile())
                } catch (failure) {
                    setError(
                        `Изменение сохранено, но не удалось обновить профиль: ${
                            errorMessage(failure)
                        }. Обновите страницу для проверки.`
                    )
                    return result
                }
            }

            setNotice('Готово.')
            return result
        } catch (failure) {
            setError(errorMessage(failure))
        } finally {
            setBusy('')
        }
    }

    async function exportData() {
        const data = await candidate.exportData()
        const url = URL.createObjectURL(
            new Blob([JSON.stringify(data, null, 2)], {
                type: 'application/json',
            })
        )

        const link = Object.assign(document.createElement('a'), {
            href: url,
            download: 'my-data.json',
        })

        link.click()
        setTimeout(() => URL.revokeObjectURL(url), 1000)
    }

    async function loadAccessLog() {
        const data = await candidate.contactAccessLog()
        const rows = Array.isArray(data)
            ? data
            : data.items || data.entries || data.logs || data.accesses

        if (!Array.isArray(rows)) {
            throw new Error(
                'Не удалось прочитать журнал: формат ответа сервера отличается от ожидаемого. Передайте этот текст бэкендеру.'
            )
        }

        setLog(rows)
    }

    return (
        <section className="mt-6 space-y-5">
            <h2 className="text-xl font-bold">
                Согласия, ФСП и мои данные
            </h2>

            <ResourceState resource={resource} />
            <ErrorNotice message={error} />

            {notice && <p role="status">{notice}</p>}

            {!resource.loading && !resource.error && resource.data && (
                <fieldset disabled={Boolean(busy)} className="space-y-6">
                    <form
                        className="space-y-3"
                        onSubmit={event => {
                            event.preventDefault()
                            action(
                                'consents',
                                () =>
                                    candidate.setConsents(
                                        consents.consent_processing,
                                        consents.consent_publication
                                    ),
                                true
                            )
                        }}
                    >
                        <h3 className="font-semibold">Согласия</h3>

                        <p className="text-sm text-gray-600">
                            Для появления в подборе нужны согласия на обработку
                            и публикацию данных. Контакты компании получают
                            после принятия приглашения.
                        </p>

                        {Object.entries({
                            consent_processing:
                                'Согласен на обработку персональных данных',
                            consent_publication:
                                'Согласен на публикацию профиля для работодателей',
                        }).map(([key, label]) => (
                            <label key={key} className="flex gap-2">
                                <input
                                    type="checkbox"
                                    checked={consents[key]}
                                    onChange={event =>
                                        setConsents(current => ({
                                            ...current,
                                            [key]: event.target.checked,
                                        }))
                                    }
                                />
                                {label}
                            </label>
                        ))}

                        <button type="submit" className={buttonClass}>
                            Сохранить согласия
                        </button>
                    </form>

                    <form
                        className="space-y-3"
                        onSubmit={event => {
                            event.preventDefault()
                            action(
                                'privacy',
                                () => candidate.setPrivacy(privacy),
                                true
                            )
                        }}
                    >
                        <h3 className="font-semibold">Видимость профиля</h3>

                        {Object.entries(privacyFields).map(([key, label]) => (
                            <label key={key} className="flex gap-2">
                                <input
                                    type="checkbox"
                                    checked={Boolean(privacy[key])}
                                    onChange={event =>
                                        setPrivacy(current => ({
                                            ...current,
                                            [key]: event.target.checked,
                                        }))
                                    }
                                />
                                {label}
                            </label>
                        ))}

                        <button type="submit" className={buttonClass}>
                            Сохранить видимость
                        </button>
                    </form>

                    <form
                        className="space-y-3"
                        onSubmit={event => {
                            event.preventDefault()
                            action(
                                'fsp',
                                () => candidate.linkFsp(fspId.trim()),
                                true
                            )
                        }}
                    >
                        <h3 className="font-semibold">ФСП — необязательно</h3>

                        <p className="text-sm">
                            Можно пользоваться платформой без ФСП. Достижения
                            учитываются при подборе внутри категории; грейд
                            подтверждается тестом.
                        </p>

                        <Field
                            label="ID ФСП"
                            required
                            pattern="[0-9]{6}"
                            maxLength={6}
                            value={fspId}
                            onChange={setFspId}
                        />

                        <button type="submit" className={buttonClass}>
                            Привязать ФСП
                        </button>

                        {resource.data.fsp_id && (
                            <button
                                type="button"
                                className={`${secondaryClass} ml-2`}
                                onClick={() =>
                                    action('unlink', candidate.unlinkFsp, true)
                                }
                            >
                                Отвязать ФСП
                            </button>
                        )}

                        {!resource.data.fsp_id && (
                            <p>
                                ФСП не привязана — это обычный профиль кандидата.
                            </p>
                        )}

                        {resource.data.fsp_rank && (
                            <p>
                                Спортивный разряд: {resource.data.fsp_rank}
                            </p>
                        )}

                        {(resource.data.fsp_achievements || []).map(
                            (item, index) => (
                                <p
                                    key={index}
                                    className="rounded bg-purple-50 p-3"
                                >
                                    {item.event} · {item.discipline} · {item.year}
                                    {' · '}
                                    {item.place
                                        ? `Место: ${item.place}`
                                        : item.result}

                                    {item.verification_status === 'demo' ||
                                    item.source === 'fsp_registry_demo'
                                        ? ' · Демо-данные'
                                        : item.verified
                                            ? ' · Подтверждено'
                                            : ''}

                                    {/^https?:\/\//i.test(
                                        item.source_url || ''
                                    ) && (
                                        <a
                                            href={item.source_url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="ml-2 text-purple-700 underline"
                                        >
                                            Протокол
                                        </a>
                                    )}
                                </p>
                            )
                        )}
                    </form>

                    <div className="space-y-3">
                        <h3 className="font-semibold">Управление данными</h3>

                        <div className="flex flex-wrap gap-2">
                            <button
                                type="button"
                                className={secondaryClass}
                                onClick={() =>
                                    action('pdf', () =>
                                        candidate.downloadProfilePdf()
                                    )
                                }
                            >
                                Скачать профиль в PDF
                            </button>

                            <button
                                type="button"
                                className={secondaryClass}
                                onClick={() => action('export', exportData)}
                            >
                                Выгрузить мои данные
                            </button>

                            <button
                                type="button"
                                className={secondaryClass}
                                onClick={() => action('log', loadAccessLog)}
                            >
                                Кто смотрел мои контакты
                            </button>
                        </div>

                        {log &&
                            (log.length ? (
                                <ul className="space-y-2">
                                    {log.map((item, index) => (
                                        <li
                                            key={item.id || index}
                                            className="rounded border p-3"
                                        >
                                            {item.company_name ||
                                                item.employer?.company_name ||
                                                item.company?.company_name ||
                                                'Работодатель'}
                                            {' · '}
                                            {date(
                                                item.accessed_at ||
                                                item.created_at
                                            )}
                                            {item.reason &&
                                                ` · ${item.reason}`}
                                        </li>
                                    ))}
                                </ul>
                            ) : (
                                <p>Просмотров контактов пока нет.</p>
                            ))}
                    </div>

                    <details className="rounded border border-red-200 p-3">
                        <summary className="cursor-pointer text-red-700">
                            Удаление аккаунта
                        </summary>

                        <form
                            className="mt-3 space-y-3"
                            onSubmit={event => {
                                event.preventDefault()

                                if (
                                    window.confirm(
                                        'Удалить аккаунт и персональные данные? Это действие нельзя отменить.'
                                    )
                                ) {
                                    action('delete', () =>
                                        candidate.deleteAccount(password)
                                    )
                                }
                            }}
                        >
                            <p>
                                Удаление нельзя отменить. Введите пароль
                                для подтверждения.
                            </p>

                            <Field
                                label="Пароль"
                                type="password"
                                autoComplete="current-password"
                                required
                                value={password}
                                onChange={setPassword}
                            />

                            <button
                                type="submit"
                                className="rounded bg-red-600 px-4 py-2 text-white"
                            >
                                Удалить аккаунт
                            </button>
                        </form>
                    </details>
                </fieldset>
            )}
        </section>
    )
}