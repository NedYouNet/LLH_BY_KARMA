// Получаем выбранную роль и функцию её изменения из App.
export default function RoleSelector({ role, onRoleChange }) {
    // Возвращаем блок выбора роли.
    return (
        // section объединяет пояснение, кнопки и выбранную роль.
        <section>
            {/* Пояснение над кнопками. */}
            <p className="mt-3 mb-6 text-gray-600">
                Выберите свою роль
            </p>

            {/* Располагаем кнопки в ряд с промежутком. */}
            <div className="flex flex-wrap gap-4">
                {/* Передаём в App выбранную роль кандидата. */}
                <button
                    type="button"
                    className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 cursor-pointer"
                    onClick={() => onRoleChange('Кандидат')}
                >
                    Я ищу работу
                </button>

                {/* Передаём в App выбранную роль работодателя. */}
                <button
                    type="button"
                    className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 cursor-pointer"
                    onClick={() => onRoleChange('Работодатель')}
                >
                    Я ищу специалистов
                </button>
            </div>

            {/* Отображаем текущую роль, полученную из App. */}
            {role && (
                <p className="mt-6 rounded-lg bg-purple-50 p-4 text-purple-800">
                    Выбрана роль: {role}
                </p>
            )}
        </section>
    )
}