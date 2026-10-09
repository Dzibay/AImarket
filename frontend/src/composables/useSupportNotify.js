/** Тихий сигнал + мигание title при ответе поддержки. */

let audioCtx = null
let audioReady = false
let flashTimer = null
let savedTitle = ''
let unlockBound = false

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
  return String(title || '').replace(/^\(\d+\)\s+/, '').replace(/^💬\s+/, '')
}

function startTitleFlash(count) {
  stopTitleFlash(false)
  savedTitle = stripNotifyPrefix(document.title)
  let showAlert = true
  const tick = () => {
    document.title = showAlert
      ? `(${count}) Ответ поддержки`
      : savedTitle
    showAlert = !showAlert
  }
  tick()
  flashTimer = window.setInterval(tick, 1300)
}

function stopTitleFlash(restore = true) {
  if (flashTimer) {
    window.clearInterval(flashTimer)
    flashTimer = null
  }
  if (restore && savedTitle) {
    document.title = savedTitle
  }
  savedTitle = ''
}

/** Новый непрочитанный ответ: звук + мигание вкладки. */
export function notifySupportReply(count = 1) {
  playChime()
  startTitleFlash(Math.max(1, Number(count) || 1))
}

export function clearSupportNotify() {
  stopTitleFlash(true)
}
