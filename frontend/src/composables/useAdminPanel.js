import { computed, nextTick, onMounted, reactive, ref } from 'vue'

const TOKEN_KEY = 'aimarket-admin'

const LEDGER_KINDS = { topup: 'ЮKassa', credit: 'Админка', spend: 'Расход', adjust: 'Сверка' }

const REFERRAL_ERROR_MESSAGES = {
  exists: 'Такой токен уже есть.',
  format: 'Только латиница, цифры и _.',
  reserved: 'Нельзя начинать с paid_.',
  empty: 'Введите токен.',
  long: 'Не длиннее 64 символов.',
}

const GROUP_ERROR_MESSAGES = {
  exists: 'Такая группа уже есть.',
  format: 'Недопустимое название.',
  empty: 'Введите название.',
  long: 'Не длиннее 64 символов.',
}

export function rub(value) {
  return Number(value).toFixed(2) + ' ₽'
}

export function usd(value) {
  return '$' + Number(value).toFixed(2)
}

export function usd4(value) {
  return '$' + Number(value).toFixed(4)
}

export function shortDate(value) {
  if (!value) return '—'
  const moment = new Date(value)
  if (Number.isNaN(moment.getTime())) return '—'
  return moment.toLocaleDateString('ru-RU')
}

export function conversion(value, visits) {
  if (!visits) return '—'
  return Number(value || 0).toFixed(1).replace('.0', '') + '%'
}

export function person(row) {
  const name = row.first_name || ''
  let user = ''
  if (row.username) user = '@' + row.username
  else if (row.telegram_id) user = String(row.telegram_id)
  else user = row.email || 'сайт'
  return (name + ' ' + user).trim()
}

export function statusBadgeClass(status) {
  const value = String(status || '').toLowerCase()
  if (value === 'paid') return 'ok'
  if (value === 'pending' || value === 'оферта') return 'warn'
  if (value === 'failed' || value === 'rejected' || value === 'blocked') return 'bad'
  return 'neutral'
}

function referralErrorText(code) {
  return REFERRAL_ERROR_MESSAGES[code] || code || 'error'
}

function groupErrorText(code) {
  return GROUP_ERROR_MESSAGES[code] || code || 'error'
}

function aggregateReferralStats(items) {
  const stats = { visits: 0, offers_accepted: 0, payments: 0, payers: 0, topup_rub: 0, topup_usd: 0 }
  for (const item of items) {
    stats.visits += Number(item.visits || 0)
    stats.offers_accepted += Number(item.offers_accepted || 0)
    stats.payments += Number(item.payments || 0)
    stats.payers += Number(item.payers || 0)
    stats.topup_rub += Number(item.topup_rub || 0)
    stats.topup_usd += Number(item.topup_usd || 0)
  }
  stats.payment_conversion = stats.visits > 0
    ? Math.round(stats.payers / stats.visits * 1000) / 10
    : 0
  return stats
}

function buildChartBars(rows, field) {
  const max = Math.max(...rows.map((row) => Number(row[field]) || 0), 0)
  const step = rows.length > 40 ? 14 : rows.length > 14 ? 5 : 1
  return rows.map((row, index) => {
    const value = Number(row[field]) || 0
    return {
      day: row.day,
      value,
      empty: max === 0 || value === 0,
      height: max === 0 || value === 0 ? 4 : Math.max(6, Math.round(value / max * 140)),
      title: row.day + ': ' + (field === 'rub' ? rub(value) : usd4(value)),
      showLabel: index % step === 0,
      label: index % step === 0 ? row.day.slice(5) : '',
    }
  })
}

export function useAdminPanel() {
  const isLoggedIn = ref(false)
  const password = ref('')
  const loginError = ref('')

  const activeTab = ref('analytics')
  const period = ref(30)

  const settingsForm = reactive({
    public_base_url: '',
    usd_price_rub: '',
    min_topup_usd: '',
    offer_date: '',
    offer_email: '',
    support_username: '',
  })
  const bonusTiers = ref([])
  const mailEnabled = ref(false)

  function addBonusTier() {
    bonusTiers.value.push({ min_usd: '', percent: '' })
  }

  function removeBonusTier(index) {
    bonusTiers.value.splice(index, 1)
  }
  const rootKey = ref('')
  const rootHint = ref('')
  const supplierBalance = ref(null)
  const saveStatus = ref('')
  const saveStatusIsError = ref(false)

  const kpiCards = ref([])
  const revenueBars = ref([])
  const spendBars = ref([])
  const models = ref([])
  const spenders = ref([])
  const payers = ref([])
  const paymentStatuses = ref([])
  const recentRequests = ref([])

  const ledgerCheckCards = ref([])
  const ledgerItems = ref([])
  const ledgerForm = reactive({
    user_id: '',
    kind: 'credit',
    amount_usd: '',
    amount_rub: '',
    note: '',
  })
  const ledgerError = ref('')
  const ledgerUserOptions = ref([])

  const topups = ref([])

  const users = ref([])
  const userCredits = reactive({})

  const referralBot = ref('')
  const referralGroups = ref([])
  const referralItems = ref([])
  const referralExpandedIds = ref([])
  const referralExpandInitialized = ref(false)
  const referralModalOpen = ref(false)
  const referralToken = ref('')
  const referralGroupId = ref('')
  const referralError = ref('')
  const groupName = ref('')
  const groupError = ref('')
  const copiedReferralIds = ref({})

  const tabs = [
    { id: 'analytics', label: 'Аналитика' },
    { id: 'settings', label: 'Настройки' },
    { id: 'payments', label: 'Платежи' },
    { id: 'ledger', label: 'Транзакции' },
    { id: 'users', label: 'Пользователи' },
    { id: 'referrals', label: 'Рефералы' },
  ]

  const periodOptions = [
    { days: 7, label: '7 дней' },
    { days: 30, label: '30 дней' },
    { days: 90, label: '90 дней' },
  ]

  const ledgerKindOptions = [
    { value: 'credit', label: 'Админка' },
    { value: 'spend', label: 'Расход' },
    { value: 'adjust', label: 'Сверка' },
    { value: 'topup', label: 'ЮKassa' },
  ]

  const supplierDisplay = computed(() => {
    if (supplierBalance.value == null) return '—'
    return '$' + Number(supplierBalance.value).toFixed(2)
  })

  const referralRows = computed(() => {
    const rows = []
    if (!referralGroups.value.length && !referralItems.value.length) {
      return [{ type: 'empty' }]
    }

    const grouped = new Map(referralGroups.value.map((group) => [group.id, []]))
    const ungrouped = []
    for (const item of referralItems.value) {
      if (item.group_id && grouped.has(item.group_id)) grouped.get(item.group_id).push(item)
      else ungrouped.push(item)
    }

    for (const group of referralGroups.value) {
      const items = grouped.get(group.id) || []
      const expanded = referralExpandedIds.value.includes(group.id)
      rows.push({
        type: 'group',
        group,
        count: items.length,
        stats: aggregateReferralStats(items),
        expanded,
      })
      if (expanded) {
        for (const item of items) {
          rows.push({ type: 'token', item, groupId: group.id })
        }
      }
    }

    if (ungrouped.length) {
      rows.push({
        type: 'section',
        title: 'Без группы',
        stats: aggregateReferralStats(ungrouped),
      })
      for (const item of ungrouped) {
        rows.push({ type: 'token', item, groupId: null })
      }
    }

    return rows
  })

  function authHeaders() {
    return {
      Authorization: 'Bearer ' + sessionStorage.getItem(TOKEN_KEY),
      'Content-Type': 'application/json',
    }
  }

  async function api(path, options = {}) {
    const response = await fetch(path, {
      ...options,
      headers: { ...authHeaders(), ...options.headers },
    })
    if (response.status === 401) {
      sessionStorage.removeItem(TOKEN_KEY)
      showLogin()
      throw new Error('unauthorized')
    }
    const body = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(body.detail || 'error')
    return body
  }

  function showLogin() {
    isLoggedIn.value = false
  }

  function referralUrl(token) {
    if (!referralBot.value) return ''
    return 'https://t.me/' + referralBot.value + '?start=' + encodeURIComponent(token)
  }

  function referralTopupText(stats) {
    return rub(stats.topup_rub || 0) + ' · ' + usd(stats.topup_usd || 0)
  }

  function renderLedgerCheck(check) {
    const balanceDiff = Number(check.balance_diff_usd || 0)
    const payDiff = Number(check.payments_diff_usd || 0)
    const payDiffRub = Number(check.payments_diff_rub || 0)
    ledgerCheckCards.value = [
      { label: 'Балансы клиентов', value: usd4(check.balances_usd || 0), ok: true },
      { label: 'Журнал', value: usd4(check.ledger_net_usd || 0), ok: true },
      {
        label: 'Сверка балансов',
        value: check.balance_ok ? 'OK' : usd4(balanceDiff),
        ok: !!check.balance_ok,
      },
      {
        label: 'Оплачено',
        value: usd(check.payments_usd || 0) + ' · ' + rub(check.payments_rub || 0),
        ok: true,
      },
      {
        label: 'ЮKassa в журнале',
        value: usd(check.ledger_topup_usd || 0) + ' · ' + rub(check.ledger_topup_rub || 0),
        ok: true,
      },
      {
        label: 'Сверка платежей',
        value: check.payments_ok ? 'OK' : usd4(payDiff) + ' · ' + rub(payDiffRub),
        ok: !!check.payments_ok,
      },
    ]
  }

  function ledgerKindLabel(kind) {
    return LEDGER_KINDS[kind] || kind
  }

  function ledgerAmountText(item) {
    const value = Number(item.amount_usd)
    const sign = item.kind === 'spend' || value < 0 ? '−' : '+'
    let text = sign + '$' + Math.abs(value).toFixed(2)
    if (item.kind === 'topup' && item.amount_rub) {
      text += ' · ' + Number(item.amount_rub).toFixed(2) + ' ₽'
    }
    return text
  }

  function formatRecentAt(at) {
    return at.replace('T', ' ').slice(0, 16)
  }

  async function loadAnalytics() {
    const data = await api('/api/admin/analytics?days=' + period.value)
    const supplier = data.supplier_balance_usd == null ? '—' : usd(data.supplier_balance_usd)
    kpiCards.value = [
      ['Выручка сегодня', rub(data.revenue_today_rub)],
      ['Выручка за период', rub(data.revenue_rub)],
      ['Зачислено лимита', usd(data.revenue_usd)],
      ['Средний чек', rub(data.average_check_rub)],
      ['Оплат', String(data.payments_paid) + ' / ' + data.payments],
      ['Платящих', String(data.paying_users)],
      ['Расход сегодня', usd4(data.spend_today_usd)],
      ['Запросов сегодня', String(data.requests_today)],
      ['Пользователи', String(data.users)],
      ['Новые', String(data.users_new)],
      ['Оферта', String(data.users_accepted)],
      ['Ключи', String(data.keys_active)],
      ['Балансы', usd(data.customer_balance_usd)],
      ['Поставщик', supplier],
      ['Расход за период', usd4(data.spend_by_day.reduce((sum, row) => sum + row.usd, 0))],
      ['Запросов за период', String(data.spend_by_day.reduce((sum, row) => sum + row.requests, 0))],
    ].map(([label, value]) => ({ label, value }))

    revenueBars.value = buildChartBars(data.revenue_by_day, 'rub')
    spendBars.value = buildChartBars(data.spend_by_day, 'usd')
    models.value = data.models
    spenders.value = data.spenders
    payers.value = data.payers
    paymentStatuses.value = data.statuses
    recentRequests.value = data.recent
  }

  async function loadReferrals() {
    const data = await api('/api/admin/referrals')
    referralBot.value = data.bot_username || ''
    referralGroups.value = data.groups || []
    referralItems.value = data.items || []

    const groupIds = new Set(referralGroups.value.map((group) => group.id))
    referralExpandedIds.value = referralExpandedIds.value.filter((id) => groupIds.has(id))

    if (!referralExpandInitialized.value) {
      referralExpandedIds.value = referralGroups.value.map((group) => group.id)
      referralExpandInitialized.value = true
    }
  }

  async function load() {
    const settings = await api('/api/admin/settings')
    settingsForm.public_base_url = settings.public_base_url || ''
    settingsForm.usd_price_rub = settings.usd_price_rub || ''
    settingsForm.min_topup_usd = settings.min_topup_usd || ''
    bonusTiers.value = (settings.topup_bonuses || []).map((tier) => ({
      min_usd: String(tier.min_usd),
      percent: String(tier.percent),
    }))
    mailEnabled.value = Boolean(settings.mail_enabled)
    settingsForm.offer_date = settings.offer_date || ''
    settingsForm.offer_email = settings.offer_email || ''
    settingsForm.support_username = settings.support_username || ''
    rootKey.value = ''
    rootHint.value = settings.router_root_key_set
      ? 'Задан · …' + settings.router_root_key_hint
      : 'Ключ не задан'
    supplierBalance.value = settings.supplier_balance_usd

    const ledger = await api('/api/admin/ledger')
    renderLedgerCheck(ledger.check || {})
    ledgerItems.value = ledger.items

    const topupsData = await api('/api/admin/topups')
    topups.value = topupsData.items

    const selectedUser = ledgerForm.user_id
    const usersData = await api('/api/admin/users')
    ledgerUserOptions.value = usersData.items
    if (selectedUser) ledgerForm.user_id = selectedUser
    users.value = usersData.items

    await loadReferrals()
    await loadAnalytics()
    isLoggedIn.value = true
  }

  async function login() {
    loginError.value = ''
    const response = await fetch('/api/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: password.value }),
    })
    const body = await response.json().catch(() => ({}))
    if (!response.ok) {
      loginError.value = 'Неверный пароль'
      return
    }
    sessionStorage.setItem(TOKEN_KEY, body.token)
    password.value = ''
    await load()
  }

  function setTab(tab) {
    activeTab.value = tab
  }

  async function setPeriod(days) {
    period.value = days
    await loadAnalytics()
  }

  async function saveSettings() {
    saveStatus.value = ''
    saveStatusIsError.value = false
    try {
      await api('/api/admin/settings', {
        method: 'PUT',
        body: JSON.stringify({
          public_base_url: settingsForm.public_base_url,
          usd_price_rub: settingsForm.usd_price_rub,
          min_topup_usd: settingsForm.min_topup_usd,
          topup_bonuses: bonusTiers.value
            .map((tier) => ({
              min_usd: Number(String(tier.min_usd).replace(',', '.')),
              percent: Number(String(tier.percent).replace(',', '.')),
            }))
            .filter((tier) => tier.min_usd > 0 && tier.percent > 0),
          offer_date: settingsForm.offer_date,
          offer_email: settingsForm.offer_email,
          support_username: settingsForm.support_username,
          router_root_key: rootKey.value,
        }),
      })
      saveStatusIsError.value = false
      saveStatus.value = 'Сохранено'
      await load()
    } catch (error) {
      saveStatusIsError.value = true
      saveStatus.value = error.message
    }
  }

  async function addLedgerEntry() {
    ledgerError.value = ''
    const amount = Number(String(ledgerForm.amount_usd).replace(',', '.'))
    const rubles = Number(String(ledgerForm.amount_rub || '0').replace(',', '.')) || 0
    if (!ledgerForm.user_id || !amount) {
      ledgerError.value = 'Выберите клиента и сумму.'
      return
    }
    try {
      await api('/api/admin/ledger', {
        method: 'POST',
        body: JSON.stringify({
          user_id: Number(ledgerForm.user_id),
          kind: ledgerForm.kind,
          amount_usd: amount,
          amount_rub: rubles,
          note: ledgerForm.note,
        }),
      })
      ledgerForm.amount_usd = ''
      ledgerForm.amount_rub = ''
      ledgerForm.note = ''
      await load()
    } catch (error) {
      ledgerError.value = error.message === 'duplicate'
        ? 'Такая пометка уже есть.'
        : error.message
    }
  }

  async function deleteLedgerEntry(id) {
    if (!confirm('Удалить запись из журнала?')) return
    try {
      await api('/api/admin/ledger/' + id, { method: 'DELETE' })
      await load()
    } catch (error) {
      alert(error.message)
    }
  }

  async function creditUser(user) {
    const amount = Number(String(userCredits[user.id] || '').replace(',', '.'))
    if (!amount) return
    try {
      await api('/api/admin/users/' + user.id + '/credit', {
        method: 'POST',
        body: JSON.stringify({ amount_usd: amount }),
      })
      userCredits[user.id] = ''
      await load()
    } catch (error) {
      alert(error.message === 'supplier' ? 'Не хватает лимита у поставщика.' : error.message)
    }
  }

  async function unblockUser(user) {
    if (!confirm('Разблокировать ' + person(user) + '?')) return
    try {
      await api('/api/admin/users/' + user.id + '/unblock', { method: 'POST' })
      await load()
    } catch (error) {
      alert(error.message)
    }
  }

  async function blockUser(user) {
    const reason = prompt('Причина:', '') ?? ''
    if (reason === null) return
    if (!confirm('Заблокировать ' + person(user) + '?')) return
    try {
      await api('/api/admin/users/' + user.id + '/block', {
        method: 'POST',
        body: JSON.stringify({ reason: reason.trim() }),
      })
      await load()
    } catch (error) {
      alert(error.message)
    }
  }

  async function deleteUser(user) {
    if (!confirm('Удалить ' + person(user) + '?')) return
    try {
      await api('/api/admin/users/' + user.id, { method: 'DELETE' })
      await load()
    } catch (error) {
      alert(error.message)
    }
  }

  async function openReferralModal() {
    referralError.value = ''
    referralToken.value = ''
    referralGroupId.value = ''
    referralModalOpen.value = true
    await nextTick()
    document.getElementById('referral-token')?.focus()
  }

  function closeReferralModal() {
    referralModalOpen.value = false
    referralError.value = ''
  }

  async function createReferralGroup() {
    groupError.value = ''
    const name = groupName.value.trim()
    if (!name) {
      groupError.value = groupErrorText('empty')
      return
    }
    try {
      const created = await api('/api/admin/referral-groups', {
        method: 'POST',
        body: JSON.stringify({ name }),
      })
      groupName.value = ''
      if (created && created.id) {
        referralExpandedIds.value = [...referralExpandedIds.value, created.id]
      }
      await loadReferrals()
    } catch (error) {
      groupError.value = groupErrorText(error.message)
    }
  }

  async function createReferral() {
    referralError.value = ''
    const token = referralToken.value.trim()
    if (!token) {
      referralError.value = referralErrorText('empty')
      return
    }
    const payload = { token }
    if (referralGroupId.value) payload.group_id = Number(referralGroupId.value)
    try {
      await api('/api/admin/referrals', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      closeReferralModal()
      await loadReferrals()
    } catch (error) {
      referralError.value = referralErrorText(error.message)
    }
  }

  function toggleReferralGroup(groupId) {
    if (referralExpandedIds.value.includes(groupId)) {
      referralExpandedIds.value = referralExpandedIds.value.filter((id) => id !== groupId)
    } else {
      referralExpandedIds.value = [...referralExpandedIds.value, groupId]
    }
  }

  async function updateReferralGroup(item, event) {
    const select = event.target
    const next = select.value ? Number(select.value) : null
    const prev = item.group_id ?? null
    try {
      await api('/api/admin/referrals/' + item.id + '/group', {
        method: 'PUT',
        body: JSON.stringify({ group_id: next }),
      })
      await loadReferrals()
    } catch (error) {
      alert(error.message)
      select.value = prev ? String(prev) : ''
    }
  }

  async function deleteReferral(item) {
    if (!confirm('Удалить токен ' + item.token + '?')) return
    try {
      await api('/api/admin/referrals/' + item.id, { method: 'DELETE' })
      await loadReferrals()
    } catch (error) {
      alert(error.message)
    }
  }

  async function deleteReferralGroup(group) {
    if (!confirm('Удалить группу ' + group.name + '? Токены останутся без группы.')) return
    try {
      await api('/api/admin/referral-groups/' + group.id, { method: 'DELETE' })
      referralExpandedIds.value = referralExpandedIds.value.filter((id) => id !== group.id)
      await loadReferrals()
    } catch (error) {
      alert(error.message)
    }
  }

  async function copyReferralUrl(item) {
    const url = referralUrl(item.token)
    if (!url) return
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(url)
      } else {
        const area = document.createElement('textarea')
        area.value = url
        area.style.position = 'fixed'
        area.style.left = '-9999px'
        document.body.append(area)
        area.select()
        if (!document.execCommand('copy')) throw new Error('copy failed')
        area.remove()
      }
      copiedReferralIds.value = { ...copiedReferralIds.value, [item.id]: true }
      setTimeout(() => {
        const next = { ...copiedReferralIds.value }
        delete next[item.id]
        copiedReferralIds.value = next
      }, 1200)
    } catch {
      alert('Не удалось скопировать')
    }
  }

  function modelRequests(row) {
    return String(row.requests) + ' · ' + row.tokens
  }

  function payerAmount(row) {
    return rub(row.rub) + ' · ' + usd(row.usd)
  }

  function topupAmount(item) {
    return rub(item.amount_rub) + ' · ' + usd(item.amount_usd)
  }

  onMounted(() => {
    if (sessionStorage.getItem(TOKEN_KEY)) {
      load().catch(showLogin)
    }
  })

  return {
    isLoggedIn,
    password,
    loginError,
    activeTab,
    period,
    tabs,
    periodOptions,
    settingsForm,
    bonusTiers,
    mailEnabled,
    addBonusTier,
    removeBonusTier,
    rootKey,
    rootHint,
    supplierDisplay,
    saveStatus,
    saveStatusIsError,
    kpiCards,
    revenueBars,
    spendBars,
    models,
    spenders,
    payers,
    paymentStatuses,
    recentRequests,
    ledgerCheckCards,
    ledgerItems,
    ledgerForm,
    ledgerError,
    ledgerUserOptions,
    ledgerKindOptions,
    topups,
    users,
    userCredits,
    referralGroups,
    referralRows,
    referralModalOpen,
    referralToken,
    referralGroupId,
    referralError,
    groupName,
    groupError,
    copiedReferralIds,
    login,
    setTab,
    setPeriod,
    saveSettings,
    addLedgerEntry,
    deleteLedgerEntry,
    creditUser,
    unblockUser,
    blockUser,
    deleteUser,
    openReferralModal,
    closeReferralModal,
    createReferralGroup,
    createReferral,
    toggleReferralGroup,
    updateReferralGroup,
    deleteReferral,
    deleteReferralGroup,
    copyReferralUrl,
    referralUrl,
    referralTopupText,
    ledgerKindLabel,
    ledgerAmountText,
    formatRecentAt,
    modelRequests,
    payerAmount,
    topupAmount,
    person,
    rub,
    usd,
    usd4,
    shortDate,
    conversion,
    statusBadgeClass,
  }
}
