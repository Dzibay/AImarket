/** Сколько знаков после запятой показывать: 0, если копеек/центов нет. */
function fractionDigits(value, max = 2) {
  const amount = Number(value || 0)
  if (!Number.isFinite(amount)) return 0
  const cents = Math.round(Math.abs(amount) * 100)
  return cents % 100 === 0 ? 0 : max
}

/**
 * Рубли: пробел как разделитель тысяч, запятая — копейки (ru-RU).
 * Пример: 10 000 ₽ или 10 000,50 ₽
 */
export function rub(value, digits) {
  const amount = Number(value || 0)
  const places = digits == null ? fractionDigits(amount) : digits
  return amount.toLocaleString('ru-RU', {
    minimumFractionDigits: places,
    maximumFractionDigits: places,
  }) + ' ₽'
}

/**
 * Доллары: запятая как разделитель тысяч, точка — центы (en-US).
 * Пример: $10,000 или $10,000.50
 */
export function usd(value, digits) {
  const amount = Number(value || 0)
  const places = digits == null ? fractionDigits(amount) : digits
  return '$' + amount.toLocaleString('en-US', {
    minimumFractionDigits: places,
    maximumFractionDigits: places,
  })
}

export function usdSmart(value) {
  const amount = Number(value || 0)
  if (amount !== 0 && Math.abs(amount) < 0.01) return usd(amount, 4)
  return usd(amount)
}

export function dateTime(value) {
  if (!value) return '—'
  const moment = new Date(value)
  if (Number.isNaN(moment.getTime())) return '—'
  return moment.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function tokens(value) {
  return Number(value || 0).toLocaleString('ru-RU')
}

/** Цена за 1 млн токенов: $10, $0.75, $0.00134. */
export function tokenUsd(value) {
  const amount = Number(value)
  if (!Number.isFinite(amount)) return '—'
  const abs = Math.abs(amount)
  const digits = abs >= 1 ? 2 : abs >= 0.1 ? 4 : 6
  return '$' + amount.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: digits })
}

/** Рубли за 1 млн токенов (мелкие суммы — больше знаков). */
export function tokenRub(value) {
  const amount = Number(value)
  if (!Number.isFinite(amount)) return '—'
  const abs = Math.abs(amount)
  const digits = abs >= 100 ? 0 : abs >= 1 ? 2 : abs >= 0.01 ? 4 : 6
  return amount.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: digits }) + ' ₽'
}

/** Длина контекста: 1,05 млн или 262 тыс. */
export function contextSize(value) {
  const tokensCount = Number(value) || 0
  if (tokensCount >= 1_000_000) {
    return `${(tokensCount / 1_000_000).toLocaleString('ru-RU', { maximumFractionDigits: 2 })} млн`
  }
  return `${Math.round(tokensCount / 1000).toLocaleString('ru-RU')} тыс.`
}

/**
 * Разбор суммы из поля ввода.
 * USD: «10,000.50» — запятые тысяч, точка дробная.
 * RUB: «10 000,50» — пробелы тысяч, запятая дробная.
 */
export function parseMoneyInput(raw, currency = 'usd') {
  let text = String(raw || '').replace(/\s/g, '').replace(/[^\d.,]/g, '')
  if (!text || text === '.' || text === ',') return NaN

  if (currency === 'usd') {
    text = text.replace(/,/g, '')
  } else {
    // Рубли: точка как тысяч (если вставили) убираем, запятая → десятичная.
    text = text.replace(/\./g, '').replace(',', '.')
  }

  const parts = text.split('.')
  const normalized = parts.length > 2
    ? parts[0] + '.' + parts.slice(1).join('')
    : text
  const value = Number(normalized)
  return Number.isFinite(value) ? value : NaN
}

/**
 * Красивый ввод суммы: рубли — «10 000,5», доллары — «10,000.5».
 * Сохраняет незакрытую дробную часть при наборе.
 * Если передан max — лишние цифры отбрасываются, больше лимита набрать нельзя.
 */
export function formatMoneyInput(raw, currency, max = Infinity) {
  const text = String(raw || '')
  const compact = text.replace(/\s/g, '')
  let hasTrailingSep = currency === 'usd' ? /\.$/.test(compact) : /,$/.test(compact)
  const cleaned = compact.replace(/[^\d.,]/g, '')
  if (!cleaned) return ''

  let intRaw
  let frac = ''
  let hasFrac = false

  if (currency === 'usd') {
    const dot = cleaned.indexOf('.')
    intRaw = (dot >= 0 ? cleaned.slice(0, dot) : cleaned).replace(/,/g, '')
    if (dot >= 0) {
      hasFrac = true
      frac = cleaned.slice(dot + 1).replace(/[^\d]/g, '').slice(0, 2)
    }
  } else {
    const comma = cleaned.indexOf(',')
    intRaw = (comma >= 0 ? cleaned.slice(0, comma) : cleaned).replace(/[.,]/g, '')
    if (comma >= 0) {
      hasFrac = true
      frac = cleaned.slice(comma + 1).replace(/[^\d]/g, '').slice(0, 2)
    }
  }

  let digits = (intRaw || '0').replace(/^0+(?=\d)/, '') || '0'
  let intNum = Number(digits)
  if (!Number.isFinite(intNum)) return ''

  if (Number.isFinite(max) && max > 0 && intNum > Math.floor(max)) {
    intNum = Math.floor(max)
  }
  // Дробная часть не должна выталкивать сумму за max (например 10000.99 при max=10000).
  if (Number.isFinite(max) && max > 0 && (hasFrac || hasTrailingSep)) {
    const withFrac = Number(`${intNum}.${frac || '0'}`)
    if (Number.isFinite(withFrac) && withFrac > max) {
      const capped = Math.round(max * 100) / 100
      intNum = Math.floor(capped)
      const cents = Math.round((capped - intNum) * 100)
      if (cents > 0) {
        hasFrac = true
        hasTrailingSep = false
        frac = String(cents).padStart(2, '0').replace(/0+$/, '')
      } else {
        hasFrac = false
        hasTrailingSep = false
        frac = ''
      }
    }
  }

  const intFormatted = currency === 'usd'
    ? intNum.toLocaleString('en-US', { maximumFractionDigits: 0 })
    : intNum.toLocaleString('ru-RU', { maximumFractionDigits: 0 })

  if (hasFrac || hasTrailingSep) {
    return intFormatted + (currency === 'usd' ? '.' : ',') + frac
  }
  return intFormatted
}

export async function copyText(text) {
  if (!text) return false
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return true
  }
  const area = document.createElement('textarea')
  area.value = text
  area.style.position = 'fixed'
  area.style.left = '-9999px'
  document.body.append(area)
  area.select()
  const ok = document.execCommand('copy')
  area.remove()
  return ok
}
