export function rub(value, digits = 2) {
  return Number(value || 0).toLocaleString('ru-RU', { minimumFractionDigits: digits, maximumFractionDigits: digits }) + ' ₽'
}

export function usd(value, digits = 2) {
  return '$' + Number(value || 0).toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

export function usdSmart(value) {
  const amount = Number(value || 0)
  return usd(amount, amount !== 0 && Math.abs(amount) < 0.01 ? 4 : 2)
}

export function dateTime(value) {
  if (!value) return '—'
  const moment = new Date(value)
  if (Number.isNaN(moment.getTime())) return '—'
  return moment.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export function tokens(value) {
  return Number(value || 0).toLocaleString('ru-RU')
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
