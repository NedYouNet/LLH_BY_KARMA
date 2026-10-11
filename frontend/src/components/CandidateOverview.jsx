import { auth, candidate, testing } from '../api'
import { useResource, ResourceState, secondaryClass, date } from './ui'

const load = async () => {
    const [me, category] = await Promise.all([
        auth.me(),
        candidate.category(),
    ])
    return { me, category }
}

const loadHistory = () => testing.history()

const grades = {
    intern: 'Intern',
    junior: 'Junior',
    middle: 'Middle',
    senior: 'Senior',
}

const specs = {
    backend: 'Бэкенд',
    frontend: 'Фронтенд',
    data_science: 'Аналитика данных',
    qa: 'Тестирование',
    devops: 'DevOps',
}

const statuses = {
    in_progress: 'Не завершён',
    completed: 'Завершён',
    expired: 'Время истекло',
}

const steps = [
    ['profile_filled', 'Заполнить профиль', 'profile'],
    ['survey_completed', 'Заполнить анкету', 'survey'],
    [
        'test_passed',
        'Подтвердить грейд тестом (для приоритета в подборе)',
        'survey',
    ],
    ['consents_given', 'Сохранить согласия', 'settings'],
    ['fsp_linked', 'Привязать ФСП (необязательно)', 'settings'],
]

export default function CandidateOverview({ onNavigate }) {
    const resource = useResource(load)
    const attempts = useResource(loadHistory)
    const category = resource.data?.category
    const history = Array.isArray(attempts.data) ? attempts.data : []

    return (
        <section className="mt-6 space-y-4">
            <h2 className="text-xl font-bold">Моя категория</h2>

            <ResourceState resource={resource} />

            {!resource.loading && !resource.error && category && (
                <>
                    <p>
                        {category.category || 'Категория ещё не получена'}
                        {' · '}
                        {category.grade_assigned_at
                            ? 'Грейд подтверждён тестом'
                            : 'Грейд заявлен кандидатом, пока не подтверждён'}
                    </p>

                    {category.test_score != null && (
                        <p>Балл теста: {category.test_score}/100</p>
                    )}

                    <p className="text-sm">
                        ФСП влияет на подбор внутри категории. Тесты относятся
                        к специализации и грейду.
                    </p>

                    <ul className="space-y-2">
                        {steps.map(([key, title, screen]) => (
                            <li
                                key={key}
                                className="flex flex-wrap items-center justify-between gap-2"
                            >
                                <span>
                                    {resource.data.me.onboarding?.[key]
                                        ? '✓'
                                        : '○'}{' '}
                                    {title}
                                </span>
                                <button
                                    type="button"
                                    className={secondaryClass}
                                    onClick={() => onNavigate(screen)}
                                >
                                    Открыть
                                </button>
                            </li>
                        ))}
                    </ul>

                    <p>
                        {resource.data.me.onboarding?.visible_to_employers
                            ? 'Профиль доступен для подбора работодателями.'
                            : 'Профиль пока не доступен для подбора. Проверьте профиль, анкету и согласия.'}
                    </p>

                    <div className="space-y-2 rounded-lg bg-purple-50 p-4">
                        <h3 className="font-bold">Смена грейда</h3>

                        <p>
                            {category.can_change_grade_now
                                ? 'Сейчас смена грейда доступна по результату теста.'
                                : category.next_grade_change_at
                                    ? `Следующая смена грейда доступна с ${date(category.next_grade_change_at)}.`
                                    : 'Доступность теста на каждый уровень указана ниже.'}
                        </p>

                        {category.grade_assigned_at && (
                            <p>
                                Грейд подтверждён:{' '}
                                {date(category.grade_assigned_at)}.
                            </p>
                        )}

                        <ul className="space-y-1">
                            {(category.targets || []).map(target => (
                                <li key={target.grade}>
                                    {grades[target.grade] || target.grade}:{' '}
                                    {target.allowed
                                        ? 'тест доступен'
                                        : 'тест недоступен'}
                                    {target.reason
                                        ? ` — ${target.reason}`
                                        : ''}
                                </li>
                            ))}
                        </ul>

                        {category.active_attempt_id && (
                            <p>
                                Есть незавершённый тест. Продолжите его в
                                разделе «Анкета и тест».
                            </p>
                        )}

                        <button
                            type="button"
                            className={secondaryClass}
                            onClick={() => onNavigate('survey')}
                        >
                            Перейти к анкете и тесту
                        </button>
                    </div>

                    <div className="space-y-2">
                        <h3 className="font-bold">
                            История изменения грейда
                        </h3>

                        {!category.history?.length && (
                            <p>Изменений грейда пока нет.</p>
                        )}

                        {(category.history || []).map((entry, index) => (
                            <div
                                key={index}
                                className="rounded-lg border p-3"
                            >
                                <p>
                                    {date(entry.changed_at)} ·{' '}
                                    {specs[entry.specialization] ||
                                        entry.specialization}
                                </p>
                                <p>
                                    {grades[entry.old_grade] ||
                                        entry.old_grade ||
                                        'Не подтверждён'}
                                    {' → '}
                                    {grades[entry.new_grade] ||
                                        entry.new_grade}
                                </p>
                                <p className="whitespace-pre-wrap">
                                    {entry.reason}
                                </p>
                            </div>
                        ))}
                    </div>
                </>
            )}

            <div className="space-y-2">
                <h3 className="font-bold">История тестов</h3>

                <ResourceState resource={attempts} />

                {!attempts.loading && !attempts.error && (
                    <>
                        {!history.length && <p>Попыток пока нет.</p>}

                        {history.map(attempt => (
                            <div
                                key={attempt.id}
                                className="space-y-1 rounded-lg border p-3"
                            >
                                <p className="font-medium">
                                    {specs[attempt.specialization] ||
                                        attempt.specialization}
                                    {' · '}
                                    {grades[attempt.target_grade] ||
                                        attempt.target_grade}
                                </p>

                                <p>
                                    {statuses[attempt.status] ||
                                        attempt.status}
                                    {attempt.score != null
                                        ? ` · ${attempt.score}/100`
                                        : ''}
                                    {attempt.passed == null
                                        ? ''
                                        : attempt.passed
                                            ? ' · Тест пройден'
                                            : ' · Грейд не подтверждён этой попыткой'}
                                </p>

                                <p className="text-sm">
                                    Начало: {date(attempt.started_at)}
                                    {attempt.finished_at
                                        ? ` · Завершение: ${date(attempt.finished_at)}`
                                        : ''}
                                </p>
                            </div>
                        ))}
                    </>
                )}
            </div>

            <button
                type="button"
                className={secondaryClass}
                onClick={() => {
                    resource.refresh()
                    attempts.refresh()
                }}
            >
                Обновить статус и историю
            </button>
        </section>
    )
}