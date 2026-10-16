const STORAGE_KEY = 'aimarket_referral'
const VISITOR_KEY = 'aimarket_referral_visitor'
const CLICKED_KEY = 'aimarket_referral_clicked'
const TOKEN_RE = /^[A-Za-z0-9_]{1,64}$/

export function normalizeReferralToken(raw) {
  const value = String(raw || '').trim()
  return TOKEN_RE.test(value) ? value : ''
}

function visitorId() {
  try {
    let id = localStorage.getItem(VISITOR_KEY) || ''
    if (!id) {
      id = (crypto.randomUUID && crypto.randomUUID()) || `v_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`
      localStorage.setItem(VISITOR_KEY, id)
    }
    return id
  } catch {
    return ''
  }
}

function alreadyClicked(token) {
  try {
    return localStorage.getItem(CLICKED_KEY) === token
  } catch {
    return false
  }
}

function markClicked(token) {
  try {
    localStorage.setItem(CLICKED_KEY, token)
  } catch {
    /* ignore */
  }
}

async function reportVisit(token) {
  if (!token || alreadyClicked(token)) return
  markClicked(token)
  try {
    await fetch('/api/web/referral/visit', {
      method: 'POST',
      cache: 'no-store',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, visitor: visitorId() }),
    })
  } catch {
    /* сеть — токен в localStorage всё равно сохранён для атрибуции при оплате */
  }
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
  reportVisit(token)
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
