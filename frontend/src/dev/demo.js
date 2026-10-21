// Демо-режим кабинета — только для `npm run dev`. В продакшен-сборку не попадает:
// модуль подключается динамически под `import.meta.env.DEV`.
//   ?demo=new     — новый пользователь: нулевой баланс, ключа нет
//   ?demo=active  — активный пользователь: баланс, расход, история, рефералы
//   ?demo=off     — выключить
const FLAG = 'aimarket-demo'
const DEMO_SESSION = 'demo-session'
const WEEKDAYS = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
const MODELS = ['claude-opus-5-5', 'gpt-6-astra', 'claude-sonnet-5-5', 'gemini-3.1-pro-preview', 'deepseek-v4-pro']

export function demoScenario() {
  try {
    return localStorage.getItem(FLAG) || ''
  } catch {
    return ''
  }
}

/** Читает ?demo=… из адреса и включает/выключает режим. Возвращает session для useSession. */
export function applyDemoFlag(setSession) {
  const params = new URLSearchParams(window.location.search)
  const value = params.get('demo')
  if (value == null) return
  if (value === 'off' || value === '0') {
    localStorage.removeItem(FLAG)
    setSession('')
  } else {
    localStorage.setItem(FLAG, value === 'new' ? 'new' : 'active')
    setSession(DEMO_SESSION)
    localStorage.removeItem('aimarket-paid-demo')
  }
  params.delete('demo')
  const query = params.toString()
  window.history.replaceState(null, '', window.location.pathname + (query ? `?${query}` : '') + window.location.hash)
}

function week(active) {
  const today = new Date()
  const monday = new Date(today)
  monday.setDate(today.getDate() - ((today.getDay() + 6) % 7))
  const spend = [2.41, 3.86, 1.12, 4.73, 2.95, 0.64, 1.88]
  return WEEKDAYS.map((name, i) => {
    const day = new Date(monday)
    day.setDate(monday.getDate() + i)
    const isToday = day.toDateString() === today.toDateString()
    const future = day > today && !isToday
    const dd = String(day.getDate()).padStart(2, '0')
    const mm = String(day.getMonth() + 1).padStart(2, '0')
    return {
      date: day.toISOString().slice(0, 10),
      label: `${dd}.${mm} ${name}`,
      is_today: isToday,
      usd: active && !future ? spend[i] : 0,
    }
  })
}

function profile(config, scenario) {
  const paid = scenario === 'active' || localStorage.getItem('aimarket-paid-demo') === '1'
  const ago = (min) => new Date(Date.now() - min * 60_000).toISOString()
  return {
    ...config,
    id: 4242,
    email: 'demo@market-aii.ru',
    email_enabled: true,
    balance_usd: paid ? (scenario === 'active' ? 37.42 : 50) : 0,
    blocked: false,
    blocked_reason: '',
    created_at: ago(60 * 24 * (paid && scenario === 'active' ? 23 : 0) + 3),
    key: paid
      ? { secret: 'sk-aim-demo-7f3c9e1b2a4d6f8e0c1b3a5d7e9f2c4a', spent_usd: scenario === 'active' ? 62.58 : 0 }
      : null,
    key_error: '',
    key_frozen: false,
    awaiting_supplier: false,
    spent_today_usd: scenario === 'active' ? 1.88 : 0,
    spent_month_usd: scenario === 'active' ? 48.31 : 0,
    spent_week_usd: week(scenario === 'active'),
    last_request_at: scenario === 'active' ? ago(4) : '',
    support_username: config.support_username || 'aimarket_support',
    referral: paid
      ? {
          unlocked: true,
          bonus_percent: 10,
          token: 'demo42',
          site_url: 'https://market-aii.ru/?ref=demo42',
          visits: 38,
          invited: 7,
          payers: 3,
          earned_usd: 12.5,
        }
      : { unlocked: false, bonus_percent: 10, token: '', site_url: '', visits: 0, invited: 0, payers: 0, earned_usd: 0 },
  }
}

function history(scenario, filter, offset, limit) {
  if (scenario !== 'active' && localStorage.getItem('aimarket-paid-demo') !== '1') return { items: [], has_more: false }
  const items = []
  let t = Date.now() - 4 * 60_000
  for (let i = 0; i < 40; i += 1) {
    if (i === 6 || i === 27) {
      items.push({ entry_type: 'income', created_at: new Date(t).toISOString(), label: 'Пополнение', note: 'ЮKassa', amount_usd: 50, amount_rub: 500 })
    } else {
      const p = 8000 + ((i * 7919) % 90000)
      const c = 600 + ((i * 3571) % 9000)
      items.push({
        entry_type: 'spend',
        created_at: new Date(t).toISOString(),
        model: MODELS[i % MODELS.length],
        prompt_tokens: p,
        completion_tokens: c,
        amount_usd: Math.round((p * 1.5 + c * 7.5) / 1e4) / 100,
      })
    }
    t -= (17 + ((i * 37) % 160)) * 60_000
  }
  const filtered = items.filter((r) => filter === 'all' || r.entry_type === filter)
  return { items: filtered.slice(offset, offset + limit), has_more: offset + limit < filtered.length }
}

const delay = (ms) => new Promise((r) => setTimeout(r, ms))

/** Возвращает ответ для демо или undefined — тогда запрос уходит на настоящий API. */
export async function demoResponse(path, options, realRequest) {
  const scenario = demoScenario()
  if (!scenario) return undefined
  const url = new URL(path, window.location.origin)
  const p = url.pathname
  const config = () => realRequest('/api/web/config').catch(() => ({ usd_price_rub: 10, min_topup_usd: 5, bonuses: [] }))

  if (p === '/api/web/me') {
    await delay(350)
    return profile(await config(), scenario)
  }
  if (p === '/api/web/history') {
    await delay(250)
    const q = url.searchParams
    return history(scenario, q.get('filter') || 'all', Number(q.get('offset') || 0), Number(q.get('limit') || 10))
  }
  if (p === '/api/web/topups') {
    await delay(500)
    return { pay_url: '/pay/return/4242/demo' }
  }
  if (p === '/api/web/payments/return') {
    await delay(900)
    localStorage.setItem('aimarket-paid-demo', '1')
    const prof = profile(await config(), scenario)
    return { status: 'paid', session: DEMO_SESSION, profile: prof, amount_usd: 50, bonus_usd: 0 }
  }
  if (p === '/api/web/keys/reissue' || p === '/api/web/keys/restore') {
    return { profile: profile(await config(), scenario) }
  }
  if (p === '/api/web/install') {
    const body = JSON.parse(options.body || '{}')
    const shell = body.os === 'windows' ? 'irm https://market-aii.ru/i/demo.ps1 | iex' : 'curl -fsSL https://market-aii.ru/i/demo.sh | sh'
    return { command: `${shell}  # демо: ${body.app || 'app'} · ${body.action || 'setup'}` }
  }
  if (p === '/api/web/support/unread') return { unread: 0 }
  if (p.startsWith('/api/web/support/')) return { messages: [], items: [], unread: 0 }
  return undefined
}
