import { useState } from 'react'
import InvitationModal from './InvitationModal'
// Демонстрационные профили. Контактов кандидатов здесь нет.
const demoCandidates = [
    {
        id: 1,
        name: 'Анна',
        specialization: 'Frontend-разработка',
        grade: 'Junior',
        stack: ['React', 'JavaScript', 'Git'],
        testScore: 90,
        fspId: '12345',
        hasFspAchievements: true,
    },
    {
        id: 2,
        name: 'Иван',
        specialization: 'Frontend-разработка',
        grade: 'Junior',
        stack: ['Vue', 'JavaScript', 'Git'],
        testScore: 85,
        fspId: null,
        hasFspAchievements: false,
    },
    {
        id: 3,
        name: 'Мария',
        specialization: 'Backend-разработка',
        grade: 'Middle',
        stack: ['Python', 'FastAPI', 'PostgreSQL'],
        testScore: 95,
        fspId: '67890',
        hasFspAchievements: true,
    },
    {
        id: 4,
        name: 'Алексей',
        specialization: 'Тестирование ПО',
        grade: 'Junior',
        stack: ['Python', 'Pytest', 'Git'],
        testScore: 80,
        fspId: null,
        hasFspAchievements: false,
    },
]

// Получаем требования из формы работодателя.
export default function EmployerCandidates({ needs }) {
    // Управляем дополнительным фильтром по достижениям ФСП.
    const [onlyFsp, setOnlyFsp] = useState(false)
    // null — окно закрыто; объект кандидата — окно открыто.
    const [selectedCandidate, setSelectedCandidate] = useState(null)

    // Храним созданные черновики до ухода с экрана.
    const [drafts, setDrafts] = useState([])
    // Разбиваем введённый стек по запятым и убираем повторы.
    const requiredStack = [...new Set(
        needs.stack
            .split(',')
            .map((item) => item.trim().toLowerCase())
            .filter(Boolean)
    )]

    // Формируем подборку из демонстрационных данных.
    const candidates = demoCandidates
        .filter((candidate) => {
            // Выбираем нужную категорию: специализацию и подтверждённый грейд.
            const categoryMatches =
                candidate.specialization === needs.specialization &&
                candidate.grade === needs.grade

            // Если фильтр выключен, наличие достижений не обязательно.
            const fspMatches = !onlyFsp || candidate.hasFspAchievements

            return categoryMatches && fspMatches
        })
        .map((candidate) => {
            // Находим технологии кандидата, которые запросила компания.
            const matchedStack = candidate.stack.filter((technology) =>
                requiredStack.includes(technology.toLowerCase())
            )

            // Демонстрационный рейтинг: тест 70%, достижения ФСП 30%.
            const rankScore =
                candidate.testScore * 0.7 +
                (candidate.hasFspAchievements ? 30 : 0)

            // Добавляем вычисленные поля к копии кандидата.
            return { ...candidate, matchedStack, rankScore }
        })
        .sort((first, second) => {
            // Сначала показываем больше совпадений по требуемому стеку.
            const stackDifference =
                second.matchedStack.length - first.matchedStack.length

            // При одинаковом числе совпадений сравниваем рейтинг.
            return stackDifference || second.rankScore - first.rankScore
        })

    return (
        <section className="mt-8 border-t border-gray-200 pt-6">
            <h2 className="text-xl font-bold">Подборка кандидатов</h2>

            {/* Показываем категорию, по которой выполнен поиск. */}
            <p className="mt-2 text-purple-800">
                {needs.specialization} · {needs.grade}
            </p>

            <p className="mt-2 text-sm text-gray-600">
                Демонстрационные профили и результаты тестов.
                Найдено: {candidates.length}.
            </p>

            {/* Уточняем подборку, сохраняя исходные требования. */}
            <label className="mt-4 flex items-center gap-2">
                <input
                    type="checkbox"
                    checked={onlyFsp}
                    onChange={(event) => setOnlyFsp(event.target.checked)}
                />
                Только с подтверждёнными достижениями ФСП
            </label>

            {/* Обрабатываем отсутствие подходящих профилей. */}
            {candidates.length === 0 && (
                <p className="mt-4 rounded-lg bg-gray-100 p-4">
                    По этим условиям кандидатов пока нет.
                    Попробуйте изменить требования или отключить фильтр ФСП.
                </p>
            )}

            <div className="mt-4 space-y-4">
                {candidates.map((candidate) => (
                    <article
                        key={candidate.id}
                        className="rounded-xl border border-gray-200 p-5"
                    >
                        <h3 className="text-lg font-bold">{candidate.name}</h3>

                        <p className="mt-1 text-gray-600">
                            {candidate.specialization} · {candidate.grade}
                        </p>

                        {/* Показываем стек кандидата. */}
                        <p className="mt-3">
                            Стек: {candidate.stack.join(', ')}
                        </p>

                        {/* Показываем подтверждения из демонстрационного профиля. */}
                        <div className="mt-3 flex flex-wrap gap-2">
              <span className="rounded-lg bg-purple-100 px-3 py-1 text-purple-800">
                Тест: {candidate.testScore}/100
              </span>

                            <span className="rounded-lg bg-gray-100 px-3 py-1">
                {candidate.hasFspAchievements
                    ? `Достижения ФСП · ID ${candidate.fspId}`
                    : 'Нет подтверждённых достижений ФСП'}
              </span>
                        </div>

                        {/* Объясняем попадание в подборку. */}
                        <p className="mt-3 text-sm text-gray-700">
                            Совпадают специализация и подтверждённый грейд.
                            {' '}
                            {candidate.matchedStack.length > 0
                                ? `Совпадения по стеку: ${candidate.matchedStack.join(', ')}.`
                                : 'Совпадений по требуемому стеку нет.'}
                        </p>
                        {/* Открываем приглашение конкретному кандидату. */}
                        <button
                            type="button"
                            onClick={() => setSelectedCandidate(candidate)}
                            className="mt-4 rounded-lg bg-purple-600 px-4 py-2 text-white hover:bg-purple-700 cursor-pointer"
                        >
                            Пригласить
                        </button>
                    </article>
                ))}
            </div>
            {/* Показываем созданные черновики. */}
            {drafts.length > 0 && (
                <div className="mt-6 space-y-3">
                    <h3 className="font-bold">Черновики приглашений</h3>

                    {drafts.map((draft) => (
                        <article key={draft.id} className="rounded-lg bg-purple-50 p-4">
                            <p className="font-bold">{draft.candidateName} · {draft.company}</p>

                            <p className="mt-2 text-purple-800">
                                {draft.salaryFrom.toLocaleString('ru-RU')}
                                {' — '}
                                {draft.salaryTo.toLocaleString('ru-RU')} ₽
                            </p>

                            <p className="mt-2 whitespace-pre-wrap">{draft.description}</p>
                            <p className="mt-2">Связь: {draft.contact}</p>
                            <p className="mt-2 text-sm text-gray-600">Черновик · не отправлен</p>
                        </article>
                    ))}
                </div>
            )}

            {/* Окно существует только пока выбран кандидат. */}
            {selectedCandidate && (
                <InvitationModal
                    candidate={selectedCandidate}
                    onClose={() => setSelectedCandidate(null)}
                    onCreate={(invitation) => {
                        // Добавляем черновик с уникальным идентификатором.
                        setDrafts((previous) => [
                            ...previous,
                            { ...invitation, id: crypto.randomUUID() },
                        ])

                        // Закрываем окно после создания.
                        setSelectedCandidate(null)
                    }}
                />
            )}
        </section>
    )
}