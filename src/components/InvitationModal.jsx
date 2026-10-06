import { useState, useEffect, useRef } from 'react'

// Берём название компании и контакт из заполненного профиля.
function readCompany() {
    try {
        const saved = JSON.parse(localStorage.getItem('employerProfile') || '{}')

        return {
            company: typeof saved?.companyName === 'string' ? saved.companyName : '',
            contact: typeof saved?.contact === 'string' ? saved.contact : '',
        }
    } catch {
        return { company: '', contact: '' }
    }
}

export default function InvitationModal({ candidate, onClose, onCreate }) {
    // Ссылка на HTML-окно dialog.
    const dialogRef = useRef(null)

    // Храним поля приглашения.
    const [form, setForm] = useState(() => ({
        ...readCompany(),
        description: '',
        salaryFrom: '',
        salaryTo: '',
    }))

    // Храним ошибку заполнения.
    const [error, setError] = useState('')

    // Открываем модальное окно при появлении компонента.
    useEffect(() => {
        const dialog = dialogRef.current
        dialog.showModal()

        // Закрываем окно при удалении компонента.
        return () => dialog.close()
    }, [])

    // Обновляем поле по его имени.
    function handleChange(event) {
        const { name, value } = event.target

        setForm((previous) => ({ ...previous, [name]: value }))
        setError('')
    }

    function handleSubmit(event) {
        event.preventDefault()

        // Все текстовые поля обязательны.
        if (
            !form.company.trim() ||
            !form.description.trim() ||
            !form.contact.trim()
        ) {
            setError('Заполните компанию, описание предложения и способ связи.')
            return
        }

        // Проверяем, что обе границы зарплаты введены.
        if (!form.salaryFrom.trim() || !form.salaryTo.trim()) {
            setError('Укажите обе границы зарплаты.')
            return
        }

        // Превращаем значения полей в числа.
        const salaryFrom = Number(form.salaryFrom)
        const salaryTo = Number(form.salaryTo)

        // Принимаем только положительные целые суммы.
        if (
            !Number.isSafeInteger(salaryFrom) ||
            !Number.isSafeInteger(salaryTo) ||
            salaryFrom <= 0 ||
            salaryTo <= 0
        ) {
            setError('Зарплата должна быть положительным целым числом в рублях.')
            return
        }

        // Нижняя граница не может превышать верхнюю.
        if (salaryFrom > salaryTo) {
            setError('Зарплата «от» не может быть больше зарплаты «до».')
            return
        }

        // Передаём заполненное приглашение родительскому компоненту.
        onCreate({
            candidateId: candidate.id,
            candidateName: candidate.name,
            company: form.company.trim(),
            description: form.description.trim(),
            contact: form.contact.trim(),
            salaryFrom,
            salaryTo,
        })
    }

    return (
        <dialog
            ref={dialogRef}
            aria-labelledby="invitation-title"
            onCancel={(event) => {
                // Escape закрывает окно через нашу функцию.
                event.preventDefault()
                onClose()
            }}
            className="m-auto max-h-[90vh] w-[calc(100%-2rem)] max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-xl backdrop:bg-black/40"
        >
            <h2 id="invitation-title" className="text-xl font-bold">
                Приглашение: {candidate.name}
            </h2>

            <p className="mt-2 text-sm text-gray-600">
                Создаём черновик. Отправка на сервер пока не подключена.
            </p>

            <form noValidate onSubmit={handleSubmit} className="mt-4 space-y-4">
                <label className="block">
                    <span className="mb-1 block">Компания</span>
                    <input
                        autoFocus
                        type="text"
                        name="company"
                        value={form.company}
                        onChange={handleChange}
                        className="w-full rounded-lg border border-gray-300 p-3"
                    />
                </label>

                <label className="block">
                    <span className="mb-1 block">Описание предложения</span>
                    <textarea
                        name="description"
                        rows={5}
                        value={form.description}
                        onChange={handleChange}
                        placeholder="Задачи, команда и условия работы"
                        className="w-full rounded-lg border border-gray-300 p-3"
                    />
                </label>

                {/* Две границы обязательной зарплатной вилки. */}
                <div className="grid grid-cols-2 gap-3">
                    <label className="block">
                        <span className="mb-1 block">Зарплата от, ₽</span>
                        <input
                            type="number"
                            name="salaryFrom"
                            min="1"
                            step="1"
                            value={form.salaryFrom}
                            onChange={handleChange}
                            className="w-full rounded-lg border border-gray-300 p-3"
                        />
                    </label>

                    <label className="block">
                        <span className="mb-1 block">Зарплата до, ₽</span>
                        <input
                            type="number"
                            name="salaryTo"
                            min="1"
                            step="1"
                            value={form.salaryTo}
                            onChange={handleChange}
                            className="w-full rounded-lg border border-gray-300 p-3"
                        />
                    </label>
                </div>

                <label className="block">
                    <span className="mb-1 block">Связь с работодателем</span>
                    <input
                        type="text"
                        name="contact"
                        value={form.contact}
                        onChange={handleChange}
                        placeholder="Почта, телефон или Telegram"
                        className="w-full rounded-lg border border-gray-300 p-3"
                    />
                </label>

                {error && (
                    <p role="alert" className="text-red-700">{error}</p>
                )}

                <div className="flex flex-wrap gap-3">
                    <button
                        type="submit"
                        className="rounded-lg bg-purple-600 px-4 py-2 text-white hover:bg-purple-700 cursor-pointer"
                    >
                        Создать черновик
                    </button>

                    <button
                        type="button"
                        onClick={onClose}
                        className="rounded-lg bg-purple-100 px-4 py-2 text-purple-800 hover:bg-purple-200 cursor-pointer"
                    >
                        Отмена
                    </button>
                </div>
            </form>
        </dialog>
    )
}