const STORAGE_KEY = 'aimarket_referral'
const TOKEN_RE = /^[A-Za-z0-9_]{1,64}$/

export function normalizeReferralToken(raw) {
  const value = String(raw || '').trim()
  return TOKEN_RE.test(value) ? value : ''
}

export function captureReferralFromUrl(search = window.location.search) {
  const params = new URLSearchParams(search)
  const token = normalizeReferralToken(params.get('ref'))
  if (!token) return getReferralToken()
  try {
    localStorage.setItem(STORAGE_KEY, token)
  } catch {
    /* ignore quota / private mode */
  }
  return token
}

export function getReferralToken() {
  try {
    return normalizeReferralToken(localStorage.getItem(STORAGE_KEY) || '')
  } catch {
    return ''
  }
}

export function botUrlWithReferral(botUrl) {
  const token = getReferralToken()
  if (!token || !botUrl) return botUrl || ''
  try {
    const url = new URL(botUrl)
    url.searchParams.set('start', token)
    return url.toString()
  } catch {
    return botUrl
  }
}
