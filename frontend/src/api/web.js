import { clearSession, getSession } from '../composables/useSession'

export class ApiError extends Error {
  constructor(code, status) {
    super(code)
    this.code = code
    this.status = status
  }
}

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  const session = getSession()
  if (session) headers.Authorization = `Bearer ${session}`
  const response = await fetch(path, { ...options, headers })
  const body = await response.json().catch(() => ({}))
  if (response.status === 401 && session && !path.endsWith('/login')) {
    clearSession()
  }
  if (!response.ok) throw new ApiError(body.detail || 'error', response.status)
  return body
}

export const webApi = {
  config: () => request('/api/web/config'),
  checkout: (payload) => request('/api/web/checkout', { method: 'POST', body: JSON.stringify(payload) }),
  paymentReturn: (topup, token) =>
    request('/api/web/payments/return', { method: 'POST', body: JSON.stringify({ topup, token }) }),
  login: (key) => request('/api/web/login', { method: 'POST', body: JSON.stringify({ key }) }),
  loginByLink: (token) => request('/api/web/login/link', { method: 'POST', body: JSON.stringify({ token }) }),
  me: () => request('/api/web/me'),
  history: (filter, offset, limit) =>
    request(`/api/web/history?filter=${encodeURIComponent(filter)}&offset=${offset}&limit=${limit}`),
  topup: (payload) => request('/api/web/topups', { method: 'POST', body: JSON.stringify(payload) }),
  checkTopup: (id) => request(`/api/web/topups/${id}/check`, { method: 'POST' }),
  reissueKey: () => request('/api/web/keys/reissue', { method: 'POST' }),
  installCommand: (app, os, action = 'setup') =>
    request('/api/web/install', { method: 'POST', body: JSON.stringify({ app, os, action }) }),
  supportMessages: () => request('/api/web/support/messages'),
  supportUnread: () => request('/api/web/support/unread'),
  supportSend: (body) => request('/api/web/support/messages', { method: 'POST', body: JSON.stringify({ body }) }),
}

export const ERRORS = {
  'sales-closed': 'Продажи временно закрыты. Попробуйте позже.',
  'min-topup': 'Сумма меньше минимальной.',
  email: 'Введите корректную почту.',
  amount: 'Слишком большая или некорректная сумма.',
  yookassa: 'Платёжный сервис недоступен. Попробуйте через минуту.',
  key: 'Ключ не найден. Проверьте, что скопировали его целиком.',
  blocked: 'Доступ заблокирован. Напишите в поддержку.',
  token: 'Ссылка возврата недействительна.',
  expired: 'Ссылка устарела или уже заменена новой. Войдите по ключу.',
  topup: 'Платёж не найден.',
  supplier: 'Временно не хватает лимита у поставщика. Напишите в поддержку.',
  'no-key': 'Ключ ещё не выпущен.',
  empty: 'На балансе нет средств.',
  long: 'Слишком длинное сообщение.',
  message: 'Введите текст сообщения.',
  unauthorized: 'Сессия истекла. Войдите снова.',
}

export function errorText(error) {
  const code = error?.code || error?.message
  if (typeof code === 'string' && ERRORS[code]) return ERRORS[code]
  if (error?.status === 500) return 'Временная ошибка сервера. Обновите страницу или войдите по ключу из письма.'
  return 'Что-то пошло не так. Попробуйте ещё раз.'
}
