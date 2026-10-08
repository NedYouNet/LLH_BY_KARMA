/**
 * api.js — клиент бэкенда FSP Talent для фронтенда (React + Vite).
 *
 * Положить в src/api.js. Импортировать нужное:
 *   import { auth, candidate, employer, invitations, ApiError } from './api'
 *
 * Что он делает сам, чтобы компонентам не думать:
 *   - подставляет адрес API и заголовок Authorization: Bearer <токен>;
 *   - хранит токены в localStorage и переживает перезагрузку страницы;
 *   - когда access-токен истёк (живёт 15 минут), сам обновляет его и повторяет запрос;
 *   - обновляет токен ОДИН раз, даже если истёк сразу у пяти запросов и даже в нескольких вкладках
 *     (refresh-токен у нас одноразовый: повторное использование сервер считает кражей и выкидывает из аккаунта);
 *   - превращает ошибки сервера в ApiError: { status, code, message, fields, retryAfter };
 *   - если сессию восстановить нельзя — чистит токены и шлёт событие 'fsp:logout' (показать экран входа).
 *
 * Адрес API:
 *   - по умолчанию '/api' — для этого в vite.config.js добавьте прокси:
 *       server: { proxy: { '/api': 'http://localhost:8000' } }
 *   - или задайте VITE_API_URL в файле .env фронтенда, например VITE_API_URL=https://api.fsp-talent.ru/api
 */

const API_URL = (import.meta.env?.VITE_API_URL || '/api').replace(/\/$/, '')
const STORAGE_KEY = 'fsp.auth'

// ============================================================================
//                                ОШИБКИ
// ============================================================================

/** Ошибка API. В catch: if (e instanceof ApiError && e.code === 'EMAIL_TAKEN') ... */
export class ApiError extends Error {
    constructor(status, data = {}) {
        const raw = data && typeof data === 'object' ? data : {}
        const detail = raw.detail
        const payload = detail && typeof detail === 'object' && !Array.isArray(detail)
            ? { ...raw, ...detail }
            : raw
        const fields = { ...(payload.fields || {}) }

        if (Array.isArray(detail)) {
            for (const issue of detail) {
                const path = (issue.loc || []).filter(part => !['body', 'query', 'path'].includes(part)).join('.')
                fields[path || 'form'] = issue.msg || 'Некорректное значение'
            }
        }

        const fieldMessage = Object.entries(fields)
            .map(([field, message]) => `${field}: ${Array.isArray(message) ? message.join('; ') : message}`)
            .join('\n')
        const message = payload.message
            || (typeof detail === 'string' ? detail : '')
            || (status === 422 ? 'Проверьте поля формы.' : 'Ошибка сервера')

        super(fieldMessage ? `${message}\n${fieldMessage}` : message)
        this.name = 'ApiError'
        this.status = status
        this.code = payload.code || (status === 422 ? 'VALIDATION_ERROR' : 'UNKNOWN')
        this.fields = fields
        this.retryAfter = payload.retry_after ?? null
        this.data = payload
    }
}

// ============================================================================
//                                ТОКЕНЫ
// ============================================================================

function readSession() {
    try {
        return JSON.parse(localStorage.getItem(STORAGE_KEY)) || null
    } catch {
        return null
    }
}

function saveSession(tokens) {
    const session = {
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        role: tokens.role,
    }
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
        memoryOnly = false
    } catch {
        memoryOnly = true
        // приватный режим браузера: работаем без сохранения между перезагрузками
    }
    memorySession = session
    return session
}

function clearSession() {
    memorySession = null
    try {
        localStorage.removeItem(STORAGE_KEY)
    } catch {
        /* ничего */
    }
}

let memorySession = readSession()
let memoryOnly = false

function currentSession() {
    if (memoryOnly) return memorySession
    // localStorage может обновить другая вкладка — читаем свежую версию
    try {
        memorySession = JSON.parse(localStorage.getItem(STORAGE_KEY)) || null
    } catch {
        // Если хранилище недоступно, используем сессию в памяти.
    }
    return memorySession
}

/** Залогинен ли пользователь (есть ли сохранённая сессия). */
export function isLoggedIn() {
    return Boolean(currentSession()?.refreshToken)
}

/** Роль текущего пользователя: 'candidate' | 'employer' | null. */
export function currentRole() {
    return currentSession()?.role || null
}

function notifyLogout(reason) {
    clearSession()
    window.dispatchEvent(new CustomEvent('fsp:logout', { detail: { reason } }))
}

// --- Обновление токена: строго один запрос на обновление за раз ---
let refreshPromise = null

async function refreshTokens(staleAccessToken) {
    if (refreshPromise) return refreshPromise // кто-то в этой вкладке уже обновляет — ждём его

    const doRefresh = async () => {
        const session = currentSession()
        // Пока мы ждали, другая вкладка уже обновила токен — просто берём новый
        if (session?.accessToken && session.accessToken !== staleAccessToken) return session
        if (!session?.refreshToken) throw new ApiError(401, { code: 'NOT_AUTHENTICATED', message: 'Войдите в аккаунт' })

        const res = await fetch(`${API_URL}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: session.refreshToken }),
        })
        const data = await res.json().catch(() => ({}))
        if (!res.ok) {
            notifyLogout(data.code || 'SESSION_EXPIRED')
            throw new ApiError(res.status, data)
        }
        return saveSession(data)
    }

    // Web Locks API: блокировка общая для всех вкладок сайта — две вкладки не обновят токен одновременно
    const locked = navigator.locks?.request
        ? () => navigator.locks.request('fsp-token-refresh', doRefresh)
        : doRefresh

    refreshPromise = locked().finally(() => {
        refreshPromise = null
    })
    return refreshPromise
}

// ============================================================================
//                            БАЗОВЫЙ ЗАПРОС
// ============================================================================

function buildUrl(path, query) {
    const url = `${API_URL}${path}`
    if (!query) return url
    const params = new URLSearchParams()
    for (const [key, value] of Object.entries(query)) {
        if (value === undefined || value === null || value === '') continue
        if (Array.isArray(value)) value.forEach((v) => params.append(key, v))
        else params.append(key, String(value))
    }
    const qs = params.toString()
    return qs ? `${url}?${qs}` : url
}

/**
 * Универсальный запрос. Обычно вызывать не нужно — используйте функции ниже.
 * @param {string} method  'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
 * @param {string} path    путь без /api, например '/candidate/profile'
 * @param {object} [opts]  { body, query, formData, auth = true, raw = false }
 */
export async function request(method, path, opts = {}) {
    const { body, query, formData, auth: withAuth = true, raw = false } = opts

    const send = async () => {
        const headers = {}
        if (withAuth) {
            const token = currentSession()?.accessToken
            if (token) headers.Authorization = `Bearer ${token}`
        }
        let payload
        if (formData) payload = formData // браузер сам поставит multipart-заголовок
        else if (body !== undefined) {
            headers['Content-Type'] = 'application/json'
            payload = JSON.stringify(body)
        }
        try {
            return await fetch(buildUrl(path, query), { method, headers, body: payload })
        } catch {
            throw new ApiError(0, { code: 'NETWORK_ERROR', message: 'Нет связи с сервером. Проверьте интернет.' })
        }
    }

    const usedToken = currentSession()?.accessToken
    let res = await send()

    // Истёк access-токен -> обновляем один раз и повторяем запрос
    if (res.status === 401 && withAuth && usedToken) {
        const data = await res.clone().json().catch(() => ({}))
        if (data.code === 'TOKEN_EXPIRED' || data.code === 'INVALID_TOKEN') {
            await refreshTokens(usedToken)
            res = await send()
        }
    }

    if (res.status === 204) return null
    if (raw && res.ok) return res // для файлов (PDF)

    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
        if (res.status === 401 && withAuth) notifyLogout(data.code)
        throw new ApiError(res.status, data)
    }
    return data
}

// ============================================================================
//                         ПЕРЕВОДЫ ДЛЯ ИНТЕРФЕЙСА
// ============================================================================

/** 'Кандидат' -> 'candidate', 'Работодатель' -> 'employer'. */
export function roleToApi(uiRole) {
    return { Кандидат: 'candidate', Работодатель: 'employer' }[uiRole] || uiRole
}

/** Статус приглашения с сервера -> статус интерфейса (pending | accepted | rejected | withdrawn). */
export function invitationUiStatus(status) {
    return { sent: 'pending', viewed: 'pending', accepted: 'accepted', declined: 'rejected', withdrawn: 'withdrawn' }[status] || status
}

export const INVITATION_STATUS_LABELS = {
    pending: 'Ожидает ответа',
    accepted: 'Принято',
    rejected: 'Отклонено',
    withdrawn: 'Отозвано работодателем',
}

/** 'React, JavaScript,  git' -> ['React', 'JavaScript', 'git'] (без пустых и повторов). */
export function parseStack(text) {
    return [...new Set(String(text || '').split(',').map((s) => s.trim()).filter(Boolean))]
}

/** Сообщение для пользователя из любой ошибки. */
export function errorMessage(error) {
    if (error instanceof ApiError) {
        if (error.status === 429 && error.retryAfter) {
            const minutes = Math.ceil(error.retryAfter / 60)
            return `${error.message}. Повторите через ${minutes} мин.`
        }
        return error.message
    }
    return 'Что-то пошло не так. Попробуйте ещё раз.'
}

// ============================================================================
//                              ЭНДПОИНТЫ
// ============================================================================

export const auth = {
    /** { email, password, role: 'candidate'|'employer', full_name?, company_name?, consent_processing? } */
    register: (data) => request('POST', '/auth/register', { body: data, auth: false }),
    verifyEmail: (token) => request('POST', '/auth/verify-email', { body: { token }, auth: false }),
    resendVerification: (email) => request('POST', '/auth/resend-verification', { body: { email }, auth: false }),

    /** Вход: сохраняет токены. Возвращает { role, ... }. */
    async login(email, password) {
        const tokens = await request('POST', '/auth/login', { body: { email, password }, auth: false })
        saveSession(tokens)
        return tokens
    },

    /** Выход: отзывает сессию на сервере и чистит токены. allDevices=true — выйти везде. */
    async logout(allDevices = false) {
        const refresh = currentSession()?.refreshToken
        try {
            await request('POST', '/auth/logout', { body: allDevices ? undefined : { refresh_token: refresh } })
        } catch {
            /* даже если сервер недоступен — выходим локально */
        }
        clearSession()
    },

    /** Кто я: { user, candidate_profile_id, employer_profile_id, onboarding } */
    me: () => request('GET', '/auth/me'),
}

export const fspId = {
    /** { enabled, mode, login_url, demo_accounts? } — показывать ли кнопку и подсказку с демо-аккаунтами */
    config: () => request('GET', '/auth/fsp-id/config', { auth: false }),
    start: () => window.location.assign(`${API_URL}/auth/fsp-id/login`),
    completeLogin() {
        if (window.location.pathname !== '/auth/fsp-id') return null
        if (!window.location.hash.includes('access_token=') && !window.location.hash.includes('error=')) return null
        const params = new URLSearchParams(window.location.hash.slice(1))
        window.history.replaceState(null, '', window.location.pathname)  // убираем токены из адресной строки
        if (params.get('error')) {
            throw new ApiError(400, { code: params.get('error'), message: params.get('message') || 'Вход через FSP ID не удался' })
        }
        if (!params.get('access_token') || !params.get('refresh_token') || !['candidate', 'employer'].includes(params.get('role'))) {
            throw new ApiError(400, { code: 'FSP_ID_INVALID_CALLBACK', message: 'FSP ID вернул неполные данные входа. Попробуйте войти снова.' })
        }
        saveSession({
            access_token: params.get('access_token'),
            refresh_token: params.get('refresh_token'),
            role: params.get('role'),
        })
        return {
            role: params.get('role'),
            created: params.get('created') === 'true',
            linked_existing: params.get('linked_existing') === 'true',
            fsp_linked: params.get('fsp_linked') === 'true',
        }
    },
}

export const reference = {
    /** { grades, specializations, industries, work_formats, team_roles, skills, soft_skills, survey } */
    all: () => request('GET', '/reference', { auth: false }),
}

export const candidate = {
    getProfile: () => request('GET', '/candidate/profile'),
    /** Только изменившиеся поля: { full_name, phone, telegram, about, skills: [], experience_years, ... } */
    updateProfile: (data) => request('PATCH', '/candidate/profile', { body: data }),
    /** PDF-резюме. apply=false — только распознать для предзаполнения формы. */
    parseResume: (file, apply = false) => {
        const formData = new FormData()
        formData.append('file', file)
        return request('POST', '/candidate/resume/parse', { formData, query: { apply } })
    },
    /** { industry, specialization, declared_grade, skills?, experience_years?, work_format? } */
    submitSurvey: (data) => request('POST', '/candidate/survey', { body: data }),
    /** Категория, грейд, next_grade_change_at, targets[] (на какой грейд можно сдавать), history */
    category: () => request('GET', '/candidate/category'),
    setConsents: (consentProcessing, consentPublication) =>
        request('PUT', '/candidate/consents', {
            body: { consent_processing: consentProcessing, consent_publication: consentPublication },
        }),
    /** { show_full_name, show_city, show_about, show_fsp_achievements } */
    setPrivacy: (privacy) => request('PUT', '/candidate/privacy', { body: privacy }),
    linkFsp: (fspId) => request('POST', '/candidate/fsp', { body: { fsp_id: fspId } }),
    unlinkFsp: () => request('DELETE', '/candidate/fsp'),
    contactAccessLog: () => request('GET', '/candidate/contact-access-log'),
    exportData: () => request('GET', '/candidate/export'),
    deleteAccount: async (password) => {
        await request('DELETE', '/candidate/account', { body: { password } })
        clearSession()
    },
    /** Скачать PDF-профиль: открывает диалог сохранения файла. */
    async downloadProfilePdf(filename = 'profile.pdf') {
        const res = await request('GET', '/candidate/profile/pdf', { raw: true })
        const url = URL.createObjectURL(await res.blob())
        const link = Object.assign(document.createElement('a'), { href: url, download: filename })
        link.click()
        URL.revokeObjectURL(url)
    },
}

export const testing = {
    /** Начать тест. Ошибки 409: SURVEY_REQUIRED, ATTEMPT_IN_PROGRESS (data.attempt_id), GRADE_COOLDOWN, RETRY_COOLDOWN */
    start: (specialization, targetGrade) =>
        request('POST', '/testing/attempts', { body: { specialization, target_grade: targetGrade } }),
    /** Задания и таймер (seconds_left). items[].kind: 'single' | 'input' | 'code' */
    get: (attemptId) => request('GET', `/testing/attempts/${attemptId}`),
    /** answers: { q1: 'текст варианта', q2: '42', q3: 'def solve(...)...' } -> результат и решение по грейду */
    submit: (attemptId, answers) => request('POST', `/testing/attempts/${attemptId}/submit`, { body: { answers } }),
    result: (attemptId) => request('GET', `/testing/attempts/${attemptId}/result`),
    history: () => request('GET', '/testing/attempts'),
}

export const employer = {
    getProfile: () => request('GET', '/employer/profile'),
    /** { company_name, description, industry, contact, website, city, inn } — только изменившиеся */
    updateProfile: (data) => request('PATCH', '/employer/profile', { body: data }),

    listNeeds: () => request('GET', '/employer/needs'),
    getNeed: (id) => request('GET', `/employer/needs/${id}`),
    /** { title?, specialization, grade, stack: [], description? } */
    createNeed: (data) => request('POST', '/employer/needs', { body: data }),
    updateNeed: (id, data) => request('PUT', `/employer/needs/${id}`, { body: data }),
    deleteNeed: (id) => request('DELETE', `/employer/needs/${id}`),

    /** Интеграция с ATS: { enabled, webhook_url, secret (только сразу после настройки!), recent_deliveries } */
    atsConfig: () => request('GET', '/employer/integrations/ats'),
    configureAts: (webhookUrl, rotateSecret = false) =>
        request('PUT', '/employer/integrations/ats', { body: { webhook_url: webhookUrl, rotate_secret: rotateSecret } }),
    testAts: () => request('POST', '/employer/integrations/ats/test'),
    disableAts: () => request('DELETE', '/employer/integrations/ats'),
}

export const candidates = {
    /**
     * Подборка. Пример: candidates.search({ needs_id: 3, only_fsp: true, page: 1 })
     * Фильтры: needs_id, specialization, grade (строка или массив), stack (массив), only_fsp, min_test_score,
     * text, page, page_size. Ответ: { total, page, size, categories: [...], items: [карточки] }
     */
    search: (filters = {}) =>
        request('GET', '/candidates', {
            query: { ...filters, stack: Array.isArray(filters.stack) ? filters.stack.join(',') : filters.stack },
        }),
    categories: () => request('GET', '/candidates/categories'),
    /** Карточка кандидата. contacts = null, пока он не принял ваше приглашение. */
    get: (id, vacancyId) => request('GET', `/candidates/${id}`, { query: { vacancy_id: vacancyId } }),
    shortlist: () => request('GET', '/shortlist'),
    addToShortlist: (candidateId, note) => request('POST', '/shortlist', { body: { candidate_id: candidateId, note } }),
    removeFromShortlist: (candidateId) => request('DELETE', `/shortlist/${candidateId}`),
}

export const invitations = {
    /**
     * { candidate_id, message, salary_from, salary_to, contact_method?, position_title?, vacancy_id? }
     * Ошибки: 422 (fields.salary_to и т.п.), 409 INVITATION_EXISTS, 400 COMPANY_PROFILE_INCOMPLETE
     */
    create: (data) => request('POST', '/invitations', { body: data }),
    /** Свои: кандидат — входящие, работодатель — отправленные. status — необязательный фильтр. */
    list: (status) => request('GET', '/invitations', { query: { status } }),
    /** Открыть (у кандидата статус станет viewed). */
    get: (id) => request('GET', `/invitations/${id}`),
    /** Кандидат отвечает: 'accepted' | 'rejected'. Повторный ответ -> 409. */
    answer: (id, status, reply) => request('PATCH', `/invitations/${id}/answer`, { body: { status, reply } }),
    withdraw: (id) => request('POST', `/invitations/${id}/withdraw`),
    /** Кандидат после принятия: закрыть контакты от компании (granted=false) или открыть снова (true) */
    setContactAccess: (id, granted) => request('PUT', `/invitations/${id}/contact-access`, { body: { granted } }),
}

export const vacancies = {
    list: (filters = {}) => request('GET', '/vacancies', { query: filters }),
    mine: () => request('GET', '/vacancies/mine'),
    get: (id) => request('GET', `/vacancies/${id}`),
    create: (data) => request('POST', '/vacancies', { body: data }),
    update: (id, data) => request('PATCH', `/vacancies/${id}`, { body: data }),
    close: (id) => request('PATCH', `/vacancies/${id}`, { body: { status: 'closed' } }),
    matches: (id, page = 1) => request('GET', `/vacancies/${id}/matches`, { query: { page } }),
    assessmentPreview: (id) => request('GET', `/vacancies/${id}/assessment-preview`),
    apply: (id, coverLetter) => request('POST', `/vacancies/${id}/apply`, { body: { cover_letter: coverLetter } }),
}

export const applications = {
    /** Кандидат — свои отклики; работодатель — отклики на свои вакансии (можно фильтр vacancyId). */
    list: (vacancyId) => request('GET', '/applications', { query: { vacancy_id: vacancyId } }),
    /** Работодатель: 'viewed' | 'accepted' | 'rejected' */
    setStatus: (id, status, comment) => request('PATCH', `/applications/${id}`, { body: { status, comment } }),
    withdraw: (id) => request('POST', `/applications/${id}/withdraw`),
}

export const shortTasks = {
    feed: () => request('GET', '/short-tasks/feed'),
    submit: (taskId, answer) => request('POST', `/short-tasks/${taskId}/submit`, { body: { answer } }),
    create: (data) => request('POST', '/short-tasks', { body: data }),
    mine: () => request('GET', '/short-tasks/mine'),
    submissions: (taskId) => request('GET', `/short-tasks/${taskId}/submissions`),
    review: (submissionId, score, feedback) =>
        request('POST', `/short-tasks/submissions/${submissionId}/review`, { body: { score, feedback } }),
}
