// Получаем почту и функцию возврата к регистрации.
export default function EmailVerification({ email, onBack }) {
    return (
        <section className="mt-6 space-y-4">
            {/* Заголовок нового экрана. */}
            <h2 className="text-xl font-bold">Подтвердите почту</h2>

            {/* Показываем адрес из формы регистрации. */}
            <p className="text-gray-600">
                Адрес для подтверждения:
                <strong className="block break-all text-gray-900">
                    {email}
                </strong>
            </p>

            {/* Временно объясняем состояние прототипа. */}
            <p className="rounded-lg bg-purple-50 p-4 text-purple-800">
                Это предпросмотр экрана. Аккаунт ещё не создан, письмо не отправлено.
            </p>

            {/* Описываем будущий шаг пользователя. */}
            <p className="text-gray-600">
                После подключения регистрации здесь появится инструкция
                для подтверждения адреса.
            </p>

            {/* Позволяем вернуться и исправить адрес. */}
            <button
                type="button"
                onClick={onBack}
                className="rounded-lg bg-purple-600 px-6 py-3 text-white hover:bg-purple-700 cursor-pointer"
            >
                Вернуться к регистрации
            </button>
        </section>
    )
}