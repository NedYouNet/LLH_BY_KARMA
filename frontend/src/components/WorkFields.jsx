import { inputClass, listOptions, money } from './ui'
export const applicationLabels = { sent: 'Отправлен', viewed: 'Просмотрен', accepted: 'Принят', rejected: 'Отклонён', withdrawn: 'Отозван' }
export const workLabels = { remote: 'Удалённо', office: 'В офисе', hybrid: 'Гибрид' }
export function SelectField({ label, value, onChange, options, empty = 'Все', required = false }) {
    return <label className="block">{label}<select className={inputClass} value={value || ''} required={required} onChange={e => onChange(e.target.value)}><option value="">{empty}</option>{listOptions(options).map(x => <option key={x.code} value={x.code}>{x.name}</option>)}</select></label>
}
export function VacancySummary({ vacancy: v }) {
    return <div className="space-y-2"><h3 className="text-lg font-bold">{v.title}</h3><p>{v.company?.company_name} · {v.category || `${v.specialization} · ${v.grade}`}</p><p className="font-bold text-purple-700">{money(v.salary_from)}–{money(v.salary_to)} ₽ · {v.salary_type_label || (v.salary_type === 'net' ? 'на руки' : 'до вычета НДФЛ')}</p><p>{workLabels[v.work_format] || 'Формат не указан'}{v.city && ` · ${v.city}`}</p><p>Технологии: {(v.skills || []).join(', ') || '—'}</p><p className="whitespace-pre-wrap">{v.description}</p>{v.team_description && <p className="whitespace-pre-wrap">Команда: {v.team_description}</p>}</div>
}
