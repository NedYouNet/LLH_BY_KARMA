// Подключаем состояние для изменения статусов.
import { useState } from 'react'

// Демонстрационные предложения для разработки интерфейса.
const demoInvitations = [
    {
        id: 1,
        company: 'Пример: ТехноКоманда',
        title: 'Junior Frontend-разработчик',
        description: 'Разработка интерфейсов на React. Работа с наставником.',
        salaryFrom: 70000,
        salaryTo: 100000,
        contact: 'hr@example.com',
        status: 'pending',
    },
    {
        id: 2,
        company: 'Пример: ВебСтудия',
        title: 'Frontend-разработчик',
        description: 'Создание личных кабинетов и работа с REST API.',
        salaryFrom: 90000,
        salaryTo: 130000,
        contact: 'team@example.com',
        status: 'pending',
    },
]

// Подписи статусов, которые видит кандидат.
const statusLabels = {
    pending: 'Ожидает ответа',
    accepted: 'Принято',
    rejected: 'Отклонено',
}

// Форматируем числа: 100000 превращается в 100 000.
const numberFormat = new Intl.NumberFormat('ru-RU')

export default function CandidateInvitations() {
    // Храним приглашения и их текущие статусы.
    const [invitations, setInvitations] = useState(demoInvitations)

    // Меняем статус одного приглашения.
    function handleAnswer(id, nextStatus) {
        // Используем предыдущий список, чтобы обновить его корректно.
        setInvitations((previous) =>
            // Перебираем приглашения и создаём обновлённый список.
            previous.map((invitation) => {
                // Остальные приглашения и уже обработанные ответы оставляем как есть.
                if (invitation.id !== id || invitation.status !== 'pending') {
                    return invitation
                }

                // Копируем приглашение и меняем только статус.
                return { ...invitation, status: nextStatus }
            })
        )
    }

    return (
        <section className="mt-6">
            {/* Заголовок раздела. */}
            <h2 className="text-xl font-bold">Входящие приглашения</h2>

            {/* Обозначаем демонстрационные данные. */}
            <p className="mt-2 text-gray-600">
                Учебные предложения. Ответы меняются только в интерфейсе
                и не отправляются работодателям.
            </p>

            {/* Показываем сообщение, если приглашений нет. */}
            {invitations.length === 0 && (
                <p className="mt-4 rounded-lg bg-gray-100 p-4">
                    Пока приглашений нет.
                </p>
            )}

            <div className="mt-4 space-y-4">
                {/* Создаём карточку для каждого приглашения. */}
                {invitations.map((invitation) => (
                    <article
                        key={invitation.id}
                        className="rounded-xl border border-gray-200 p-5"
                    >
                        {/* Компания и название предложения. */}
                        <p className="text-sm text-gray-600">{invitation.company}</p>
                        <h3 className="mt-1 text-lg font-bold">{invitation.title}</h3>

                        {/* Зарплатная вилка обязательно видна до ответа. */}
                        <p className="mt-3 text-2xl font-bold text-purple-700">
                            {numberFormat.format(invitation.salaryFrom)}
                            {' — '}
                            {numberFormat.format(invitation.salaryTo)} ₽
                        </p>

                        {/* Условия предложения. */}
                        <p className="mt-3 text-gray-700">{invitation.description}</p>

                        {/* Способ связи с работодателем — обязательное поле по ТЗ. */}
                        <p className="mt-3 break-all text-sm text-gray-600">
                            Связь с работодателем: {invitation.contact}
                        </p>

                        {/* Показываем актуальный статус. */}
                        <p role="status" className="mt-3 font-medium">
                            Статус: {statusLabels[invitation.status]}
                        </p>

                        {/* Отвечать можно только на необработанное приглашение. */}
                        {invitation.status === 'pending' && (
                            <div className="mt-4 flex flex-wrap gap-3">
                                <button
                                    type="button"
                                    onClick={() => handleAnswer(invitation.id, 'accepted')}
                                    className="rounded-lg bg-purple-600 px-4 py-2 text-white hover:bg-purple-700 cursor-pointer"
                                >
                                    Принять
                                </button>

                                <button
                                    type="button"
                                    onClick={() => handleAnswer(invitation.id, 'rejected')}
                                    className="rounded-lg bg-purple-100 px-4 py-2 text-purple-800 hover:bg-purple-200 cursor-pointer"
                                >
                                    Отклонить
                                </button>
                            </div>
                        )}
                    </article>
                ))}
            </div>
        </section>
    )
}