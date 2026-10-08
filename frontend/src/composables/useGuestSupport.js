import { webApi } from '../api/web'
import { getSession } from './useSession'

const STORAGE_KEY = 'aimarket-support-guest'

export function getGuestSupportToken() {
  try {
    return localStorage.getItem(STORAGE_KEY) || ''
  } catch {
    return ''
  }
}

export function setGuestSupportToken(token) {
  try {
    if (token) localStorage.setItem(STORAGE_KEY, token)
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* private mode */
  }
}

export function clearGuestSupportToken() {
  setGuestSupportToken('')
}

/** Берёт токен из localStorage или создаёт новый на сервере. */
export async function ensureGuestSupportToken() {
  const existing = getGuestSupportToken()
  const data = await webApi.supportGuestSession(existing)
  const token = data.token || ''
  if (token) setGuestSupportToken(token)
  return token
}

export async function resetGuestSupportToken() {
  setGuestSupportToken('')
  return ensureGuestSupportToken()
}

/**
 * После входа переносит гостевой диалог в чат пользователя и очищает токен.
 * Безопасно вызывать многократно: без токена или без сессии — no-op.
 */
export async function claimGuestSupportIfNeeded() {
  if (!getSession()) return 0
  const token = getGuestSupportToken()
  if (!token) return 0
  try {
    const data = await webApi.supportClaim(token)
    clearGuestSupportToken()
    return Number(data.merged || 0)
  } catch {
    // Токен уже недействителен / чужой — всё равно убираем из браузера.
    clearGuestSupportToken()
    return 0
  }
}
