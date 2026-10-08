import { auth, candidate } from '../api'
import { useResource, ResourceState, secondaryClass } from './ui'
const load = async () => ({ me: await auth.me(), category: await candidate.category() })
export default function CandidateOverview({ onNavigate }) {
    const resource = useResource(load)
    const steps = [['profile_filled', 'Заполнить профиль', 'profile'], ['survey_completed', 'Заполнить анкету', 'survey'], ['test_passed', 'Подтвердить грейд тестом (для приоритета в подборе)', 'survey'], ['consents_given', 'Сохранить согласия', 'settings'], ['fsp_linked', 'Привязать ФСП (необязательно)', 'settings']]
    const category = resource.data?.category
    return <section className="mt-6 space-y-4"><h2 className="text-xl font-bold">Моя категория</h2><ResourceState resource={resource} />
        {!resource.loading && !resource.error && resource.data && <>
            <p>{category.category || 'Категория ещё не получена'}{category.grade_assigned_at ? ' · Грейд подтверждён тестом' : ' · Не подтверждён: заявлен кандидатом'}{category.test_score != null ? ` · ${category.test_score}/${category.test_max_score || 100}` : ''}</p>
            <p className="text-sm">ФСП влияет на подбор внутри категории. Тесты относятся к специализации и грейду, а не к отдельной вакансии.</p>
            <ul className="space-y-2">{steps.map(([key, title, screen]) => <li key={key} className="flex items-center justify-between gap-2"><span>{resource.data.me.onboarding?.[key] ? '✓' : '○'} {title}</span><button className={secondaryClass} onClick={() => onNavigate(screen)}>Открыть</button></li>)}</ul>
            <p>{resource.data.me.onboarding?.visible_to_employers ? 'Профиль доступен для подбора работодателями.' : 'Профиль пока не доступен для подбора. Проверьте профиль, анкету и согласия. По обновлённым правилам тест необязателен для появления в подборе.'}</p>
            <button className={secondaryClass} onClick={resource.refresh}>Обновить статус</button>
        </>}
    </section>
}
