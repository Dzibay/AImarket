/** Звук + бейдж на favicon + префикс в title при ответе поддержки. */

let audioCtx = null
let audioReady = false
let flashTimer = null
let savedTitle = ''
let unlockBound = false
/** @type {{ el: HTMLLinkElement, href: string, type: string, sizes: string }[]} */
let faviconSnapshots = []
let alerting = false
let alertCount = 0
let badgeObjectUrl = ''

function unlockAudio() {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext
    if (!Ctx) return
    if (!audioCtx) audioCtx = new Ctx()
    if (audioCtx.state === 'suspended') audioCtx.resume()
    audioReady = true
  } catch {
    /* браузер блокирует автозвук */
  }
}

/** Разрешить звук после первого клика/клавиши на сайте. */
export function armSupportNotifyAudio() {
  if (unlockBound || typeof window === 'undefined') return
  unlockBound = true
  const once = () => {
    unlockAudio()
    window.removeEventListener('pointerdown', once)
    window.removeEventListener('keydown', once)
  }
  window.addEventListener('pointerdown', once, { once: true, passive: true })
  window.addEventListener('keydown', once, { once: true })
}

function playChime() {
  try {
    unlockAudio()
    if (!audioCtx || !audioReady) return
    const t = audioCtx.currentTime
    const osc = audioCtx.createOscillator()
    const gain = audioCtx.createGain()
    osc.type = 'sine'
    osc.frequency.setValueAtTime(784, t)
    osc.frequency.setValueAtTime(1046.5, t + 0.09)
    gain.gain.setValueAtTime(0.0001, t)
    gain.gain.exponentialRampToValueAtTime(0.05, t + 0.02)
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.38)
    osc.connect(gain)
    gain.connect(audioCtx.destination)
    osc.start(t)
    osc.stop(t + 0.42)
  } catch {
    /* ignore */
  }
}

function stripNotifyPrefix(title) {
  return String(title || '')
    .replace(/^\(\d+\)\s+/, '')
    .replace(/^💬\s+/, '')
    .replace(/^Ответ поддержки\s*[·•|]\s*/i, '')
}

function listFaviconLinks() {
  return [...document.querySelectorAll("link[rel='icon'], link[rel='shortcut icon']")]
}

function snapshotFavicons() {
  if (faviconSnapshots.length) return
  const links = listFaviconLinks()
  if (!links.length) {
    const el = document.createElement('link')
    el.rel = 'icon'
    el.type = 'image/png'
    el.href = '/favicon-96x96.png'
    document.head.append(el)
    faviconSnapshots = [{ el, href: el.href, type: el.type || '', sizes: el.sizes?.value || '' }]
    return
  }
  faviconSnapshots = links.map((el) => ({
    el,
    href: el.getAttribute('href') || el.href,
    type: el.getAttribute('type') || '',
    sizes: el.getAttribute('sizes') || '',
  }))
}

function paintBadgedFavicon(count) {
  snapshotFavicons()
  const img = new Image()
  img.decoding = 'async'
  img.onload = () => {
    if (!alerting) return
    try {
      const size = 64
      const canvas = document.createElement('canvas')
      canvas.width = size
      canvas.height = size
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      ctx.clearRect(0, 0, size, size)
      ctx.drawImage(img, 0, 0, size, size)
      // Красный кружок с числом — справа снизу у иконки вкладки.
      const r = 15
      const cx = size - r - 1
      const cy = size - r - 1
      ctx.beginPath()
      ctx.arc(cx, cy, r, 0, Math.PI * 2)
      ctx.fillStyle = '#c43c3c'
      ctx.fill()
      ctx.lineWidth = 3
      ctx.strokeStyle = '#fff'
      ctx.stroke()
      const label = count > 9 ? '9+' : String(Math.max(1, count))
      ctx.fillStyle = '#fff'
      ctx.font = 'bold 24px system-ui,Segoe UI,sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(label, cx, cy + 1)

      canvas.toBlob((blob) => {
        if (!blob || !alerting) return
        if (badgeObjectUrl) URL.revokeObjectURL(badgeObjectUrl)
        badgeObjectUrl = URL.createObjectURL(blob)
        const href = badgeObjectUrl
        // Подменяем все favicon (png/svg/ico), иначе браузер может оставить SVG.
        for (const item of faviconSnapshots) {
          item.el.type = 'image/png'
          item.el.removeAttribute('sizes')
          item.el.href = href
        }
      }, 'image/png')
    } catch {
      /* ignore */
    }
  }
  img.onerror = () => {
    /* keep default icon */
  }
  img.src = '/favicon-96x96.png'
}

function restoreFavicon() {
  for (const item of faviconSnapshots) {
    if (!document.head.contains(item.el)) continue
    if (item.type) item.el.type = item.type
    else item.el.removeAttribute('type')
    if (item.sizes) item.el.setAttribute('sizes', item.sizes)
    else item.el.removeAttribute('sizes')
    item.el.href = item.href
  }
  if (badgeObjectUrl) {
    URL.revokeObjectURL(badgeObjectUrl)
    badgeObjectUrl = ''
  }
}

function applyTitle(count, flashOn) {
  const base = savedTitle || stripNotifyPrefix(document.title)
  if (!savedTitle) savedTitle = base
  document.title = flashOn
    ? `(${count}) Ответ поддержки`
    : `(${count}) ${base}`
}

function startTitleFlash(count) {
  if (flashTimer) {
    window.clearInterval(flashTimer)
    flashTimer = null
  }
  if (!savedTitle) savedTitle = stripNotifyPrefix(document.title)
  let flashOn = true
  applyTitle(count, flashOn)
  flashTimer = window.setInterval(() => {
    if (!alerting) return
    flashOn = !flashOn
    applyTitle(alertCount || count, flashOn)
  }, 1000)
}

/** Показать бейдж на вкладке (без звука) — для уже существующих unread. */
export function setSupportAttention(count = 1) {
  const n = Math.max(1, Number(count) || 1)
  alerting = true
  alertCount = n
  if (!savedTitle) savedTitle = stripNotifyPrefix(document.title)
  paintBadgedFavicon(n)
  startTitleFlash(n)
}

/** Новый непрочитанный ответ: звук + бейдж + мигание title. */
export function notifySupportReply(count = 1) {
  playChime()
  setSupportAttention(count)
}

export function clearSupportNotify() {
  alerting = false
  alertCount = 0
  if (flashTimer) {
    window.clearInterval(flashTimer)
    flashTimer = null
  }
  if (savedTitle) {
    document.title = savedTitle
    savedTitle = ''
  }
  restoreFavicon()
}

/** Активно ли оповещение (чтобы useHead не затирал title). */
export function isSupportNotifyActive() {
  return alerting
}

/** Подмешать префикс, если страница меняет title через useHead. */
export function decorateTitleDuringAlert(title) {
  if (!alerting) return title
  const base = stripNotifyPrefix(title)
  savedTitle = base
  return `(${alertCount || 1}) ${base}`
}
