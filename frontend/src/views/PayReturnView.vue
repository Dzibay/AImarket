<template>
  <div class="site pay-page">
    <SiteHeader />
    <main class="site-main">
      <div class="pay-aurora" :class="state" aria-hidden="true"><i /><i /><i /></div>
      <canvas ref="confettiCanvas" class="confetti" aria-hidden="true" />
      <div class="container pay-wrap">
        <Transition name="swap" mode="out-in">
          <section v-if="state === 'loading'" key="loading" class="panel status-panel">
            <span class="orb loading" aria-hidden="true"><span class="loader" /></span>
            <h1 class="title">Проверяем оплату…</h1>
            <p class="lead">Это займёт пару секунд.</p>
          </section>

          <section v-else-if="state === 'paid'" key="paid" class="paid">
            <div class="paid-head">
              <span class="orb ok" aria-hidden="true">
                <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path class="tick" d="m5 12.5 4.5 4.5L19 7.5" /></svg>
              </span>
              <p class="kicker">Оплата прошла</p>
              <h1 class="title big">Готово! <span class="grad-text">Ключ ваш</span></h1>
              <p class="lead">
                Вы уже вошли в личный кабинет — осталось сохранить ключ и подключить приложение.
                <template v-if="profile.email_enabled && profile.email">
                  Копию ключа и кнопку входа отправили на <b>{{ profile.email }}</b>.
                </template>
              </p>
              <div class="chips">
                <span class="chip"><small>Зачислено</small><b>{{ usd(credited) }}</b></span>
                <span v-if="bonusUsd > 0" class="chip bonus"><small>Бонус</small><b>+{{ usd(bonusUsd) }}</b></span>
                <span class="chip dark"><small>Баланс</small><b>{{ usd(profile.balance_usd) }}</b></span>
              </div>
            </div>

            <div class="key-frame">
              <span class="key-ring" aria-hidden="true" />
              <div class="key-inner">
                <KeyCard
                  v-if="profile.key"
                  :secret="profile.key.secret"
                  :base-url="profile.api_base_url"
                  title="Ваш ключ доступа"
                  highlight
                  reveal-by-default
                />
                <div v-else class="notice">
                  Платёж зачислен, но ключ ещё выпускается. Откройте личный кабинет через минуту — ключ появится там.
                </div>
              </div>
            </div>

            <ol class="next">
              <li>
                <span class="n">1</span>
                <b>Сохраните ключ</b>
                <small>Скопируйте его в менеджер паролей — он же приходит на почту.</small>
              </li>
              <li>
                <span class="n">2</span>
                <b>Подключите приложение</b>
                <small>Cursor, Claude Code, Codex — готовая команда в кабинете.</small>
              </li>
              <li>
                <span class="n">3</span>
                <b>Работайте</b>
                <small>Все модели по одному ключу, списание только за токены.</small>
              </li>
            </ol>

            <div class="actions center">
              <RouterLink to="/cabinet#setup" class="btn go">
                Подключить приложение
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14" /><path d="m13 6 6 6-6 6" /></svg>
              </RouterLink>
              <RouterLink to="/cabinet" class="btn quiet go">В личный кабинет</RouterLink>
            </div>
          </section>

          <section v-else-if="state === 'awaiting_supplier'" key="awaiting" class="panel status-panel">
            <span class="orb wait" aria-hidden="true"><AppIcon name="history" :size="30" /></span>
            <h1 class="title">Оплата получена</h1>
            <p class="lead">
              Платёж прошёл в ЮKassa. Ключ доступа пока не выпущен — временная проблема с поставщиком API.
              Вы уже можете войти в личный кабинет
              <template v-if="profile?.email_enabled && profile?.email"> — ссылку для входа отправили на {{ profile.email }}</template>.
              Напишите в поддержку из кабинета, мы зачислим баланс и выпустим ключ.
            </p>
            <p v-if="error" class="notice">{{ error }}</p>
            <div class="actions center">
              <RouterLink to="/cabinet" class="btn">В личный кабинет</RouterLink>
              <RouterLink to="/cabinet#support" class="btn quiet">Написать в поддержку</RouterLink>
            </div>
            <div class="recheck">
              <p class="muted small">Страница проверяет статус автоматически — как только баланс зачислится, ключ появится в кабинете.</p>
              <button type="button" class="btn quiet sm" :disabled="checking" @click="check">
                {{ checking ? 'Проверяем…' : 'Проверить сейчас' }}
              </button>
            </div>
          </section>

          <section v-else-if="state === 'pending'" key="pending" class="panel status-panel">
            <span class="orb wait pulse" aria-hidden="true"><AppIcon name="history" :size="30" /></span>
            <h1 class="title">Платёж ещё обрабатывается</h1>
            <p class="lead">
              Банк пока не подтвердил оплату. Обычно это занимает до минуты — страница проверяет статус
              автоматически.
            </p>
            <p v-if="error" class="notice">{{ error }}</p>
            <div class="recheck">
              <p class="muted small">Проверок: {{ attempts }}. Если платёж не подтвердится, деньги вернутся на карту.</p>
              <button type="button" class="btn quiet sm" :disabled="checking" @click="check">
                {{ checking ? 'Проверяем…' : 'Проверить сейчас' }}
              </button>
            </div>
          </section>

          <section v-else-if="state === 'failed'" key="failed" class="panel status-panel">
            <span class="orb bad" aria-hidden="true"><AppIcon name="close" :size="30" /></span>
            <h1 class="title">Оплата не прошла</h1>
            <p class="lead">Платёж отклонён или отменён. Деньги не списаны либо вернутся на карту.</p>
            <div class="actions center">
              <RouterLink :to="{ path: '/', hash: '#pay' }" class="btn">Попробовать снова</RouterLink>
              <RouterLink v-if="hasSession" to="/cabinet#support" class="btn quiet">Написать в поддержку</RouterLink>
            </div>
          </section>

          <section v-else key="invalid" class="panel status-panel">
            <span class="orb muted-orb" aria-hidden="true"><AppIcon name="alert" :size="30" /></span>
            <h1 class="title">Ссылка недействительна</h1>
            <p class="lead">{{ error }}</p>
            <div class="actions center">
              <RouterLink v-if="hasSession" to="/cabinet" class="btn">В личный кабинет</RouterLink>
              <RouterLink to="/login" class="btn" :class="{ quiet: hasSession }">Вход</RouterLink>
              <RouterLink to="/" class="btn quiet">На главную</RouterLink>
            </div>
          </section>
        </Transition>
      </div>
    </main>
    <SiteFooter />
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import KeyCard from '../components/KeyCard.vue'
import SiteFooter from '../components/SiteFooter.vue'
import SiteHeader from '../components/SiteHeader.vue'
import AppIcon from '../components/ui/AppIcon.vue'
import { errorText, webApi } from '../api/web'
import { claimGuestSupportIfNeeded } from '../composables/useGuestSupport'
import { getSession, useSession } from '../composables/useSession'
import { reachMetrikaGoal } from '../utils/cookiesConsent'
import { usd } from '../utils/format'
import { useHead } from '../utils/useHead'

const route = useRoute()
const { setSession } = useSession()
const hasSession = Boolean(getSession())

const state = ref('loading')
const profile = ref(null)
const error = ref('')
const attempts = ref(0)
const checking = ref(false)
const credited = ref(0)
const bonusUsd = ref(0)
let timer = null
const confettiCanvas = ref(null)
let confettiFrame = 0

const topup = Number(route.params.topup || route.query.topup || 0)
const rawToken = String(route.params.token || route.query.t || '')
let token = rawToken
try {
  token = decodeURIComponent(rawToken)
} catch {
  token = rawToken
}

async function check() {
  if (checking.value) return
  checking.value = true
  attempts.value += 1
  try {
    const result = await webApi.paymentReturn(topup, token)
    if (result.status === 'paid') {
      setSession(result.session)
      await claimGuestSupportIfNeeded()
      profile.value = result.profile
      bonusUsd.value = Number(result.bonus_usd || 0)
      credited.value = Number(result.amount_usd || 0) + bonusUsd.value
      state.value = 'paid'
      const firstTime = trackPaymentSuccess({
        amount_usd: Number(result.amount_usd || 0),
        bonus_usd: bonusUsd.value,
        topup_id: topup,
      })
      stop()
      // Залп — когда экран «Оплата прошла» уже проявился (переход out-in).
      if (firstTime) nextTick(() => setTimeout(launchConfetti, 450))
    } else if (result.status === 'awaiting_supplier') {
      if (result.session) {
        setSession(result.session)
        await claimGuestSupportIfNeeded()
        profile.value = result.profile
      }
      state.value = 'awaiting_supplier'
      if (attempts.value < 24 && !timer) timer = setTimeout(() => { timer = null; check() }, 15000)
    } else if (result.status === 'pending') {
      state.value = 'pending'
      if (attempts.value < 12 && !timer) timer = setTimeout(() => { timer = null; check() }, 5000)
    } else {
      state.value = 'failed'
      stop()
    }
  } catch (err) {
    // Серверная 500 / сеть — даём повторить, платёж мог уже пройти по вебхуку.
    if (err?.status === 500 || err?.status === 502 || !err?.status) {
      error.value = errorText(err)
      state.value = 'pending'
      if (attempts.value < 6 && !timer) timer = setTimeout(() => { timer = null; check() }, 3000)
    } else {
      error.value = errorText(err)
      state.value = 'invalid'
      stop()
    }
  } finally {
    checking.value = false
  }
}

function stop() {
  if (timer) clearTimeout(timer)
  timer = null
}

/** Цель Метрики: оплата подтверждена. Один раз на topup (защита от F5). */
function trackPaymentSuccess(params) {
  const key = `ym_payment_success_${params.topup_id}`
  try {
    if (sessionStorage.getItem(key)) return false
    sessionStorage.setItem(key, '1')
  } catch {
    /* private mode — всё равно отправим */
  }
  reachMetrikaGoal('payment_success', params)
  return true
}

/** Конфетти на canvas: два залпа из нижних углов, ~3.5 с, без зависимостей. */
function launchConfetti() {
  const canvas = confettiCanvas.value
  if (!canvas || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const w = window.innerWidth
  const h = window.innerHeight
  canvas.width = w * dpr
  canvas.height = h * dpr
  ctx.scale(dpr, dpr)

  const colors = ['#d9653b', '#f2b27a', '#b07be0', '#6e8cf0', '#4fbf8a', '#ffd36e']
  const count = w < 700 ? 90 : 160
  const parts = []
  for (let i = 0; i < count; i += 1) {
    const left = i % 2 === 0
    const angle = (left ? -60 : -120) + (Math.random() - 0.5) * 50
    const speed = (w < 700 ? 11 : 15) + Math.random() * 9
    const rad = (angle * Math.PI) / 180
    parts.push({
      x: left ? -10 : w + 10,
      y: h * 0.85,
      vx: Math.cos(rad) * speed,
      vy: Math.sin(rad) * speed,
      size: 6 + Math.random() * 6,
      color: colors[i % colors.length],
      rot: Math.random() * Math.PI,
      vr: (Math.random() - 0.5) * 0.3,
      tilt: Math.random() * Math.PI,
      shape: i % 3,
    })
  }

  const start = performance.now()
  const frame = (now) => {
    const t = now - start
    ctx.clearRect(0, 0, w, h)
    const fade = t > 2600 ? Math.max(0, 1 - (t - 2600) / 900) : 1
    for (const p of parts) {
      p.vx *= 0.985
      p.vy = p.vy * 0.985 + 0.32
      p.x += p.vx
      p.y += p.vy
      p.rot += p.vr
      p.tilt += 0.12
      ctx.save()
      ctx.globalAlpha = fade
      ctx.translate(p.x, p.y)
      ctx.rotate(p.rot)
      ctx.scale(1, Math.cos(p.tilt))
      ctx.fillStyle = p.color
      if (p.shape === 0) {
        ctx.beginPath()
        ctx.arc(0, 0, p.size / 2, 0, Math.PI * 2)
        ctx.fill()
      } else {
        ctx.fillRect(-p.size / 2, -p.size / 4, p.size, p.shape === 1 ? p.size / 2 : p.size / 3)
      }
      ctx.restore()
    }
    if (fade > 0) confettiFrame = requestAnimationFrame(frame)
    else ctx.clearRect(0, 0, w, h)
  }
  confettiFrame = requestAnimationFrame(frame)
}

onMounted(() => {
  useHead('Оплата — Aimarket', true)
  if (!topup || !token) {
    error.value = 'В ссылке нет данных о платеже.'
    state.value = 'invalid'
    return
  }
  check()
})

onBeforeUnmount(() => {
  stop()
  cancelAnimationFrame(confettiFrame)
})
</script>

<style scoped>
.pay-page .site-main { position: relative; isolation: isolate; overflow: hidden; }
.pay-aurora { position: absolute; inset: -100px 0 0; z-index: -1; pointer-events: none; }
.pay-aurora i { position: absolute; border-radius: 50%; filter: blur(110px); opacity: 0.45; animation: p-drift 16s ease-in-out infinite alternate; transition: background 1s ease; }
.pay-aurora i:nth-child(1) { width: 560px; height: 460px; left: -120px; top: 40px; background: #f2b27a; }
.pay-aurora i:nth-child(2) { width: 520px; height: 440px; right: -120px; top: 120px; background: #c9b2f0; animation-delay: -6s; }
.pay-aurora i:nth-child(3) { width: 420px; height: 360px; left: 38%; top: 420px; background: #f6d3a8; animation-delay: -11s; }
.pay-aurora.paid i:nth-child(3) { background: #a8e0c2; }
.pay-aurora.failed i:nth-child(1) { background: #f0a6a0; }
@keyframes p-drift { to { transform: translate(60px, -40px) scale(1.1); } }

.confetti { position: fixed; inset: 0; width: 100%; height: 100%; pointer-events: none; z-index: 60; }

.pay-wrap { max-width: 860px; padding-top: 56px; padding-bottom: 88px; min-height: calc(100svh - 90px); }

.panel {
  max-width: 620px;
  margin: 40px auto 0;
  padding: 44px 40px 36px;
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.95);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.9) inset, 0 40px 80px -40px rgba(60, 40, 15, 0.5);
  backdrop-filter: blur(20px) saturate(1.3);
  -webkit-backdrop-filter: blur(20px) saturate(1.3);
  text-align: center;
}
.title { margin: 0 0 12px; font-size: clamp(1.9rem, 3.4vw, 2.6rem); font-weight: 680; letter-spacing: -0.05em; line-height: 1.05; }
.title.big { font-size: clamp(2.4rem, 5.4vw, 4rem); letter-spacing: -0.06em; }
.lead { margin: 0 auto; max-width: 560px; color: var(--muted-2); font-size: 16px; line-height: 1.55; }
.notice { margin-top: 18px; text-align: left; }

.orb {
  position: relative;
  display: grid;
  place-items: center;
  width: 76px;
  height: 76px;
  margin: 0 auto 22px;
  border-radius: 50%;
  color: #fff;
  background: linear-gradient(160deg, #2b2620, #15120e);
  box-shadow: 0 0 0 8px rgba(255, 255, 255, 0.6), 0 20px 40px -18px rgba(21, 18, 14, 0.8);
}
.orb.ok { width: 92px; height: 92px; background: linear-gradient(140deg, #4fbf8a, #2f8f63); box-shadow: 0 0 0 10px rgba(79, 191, 138, 0.16), 0 0 70px rgba(79, 191, 138, 0.55), 0 22px 40px -18px rgba(30, 90, 60, 0.8); animation: p-pop 0.7s var(--ease-out) both; }
.orb.ok::after { content: ""; position: absolute; inset: -10px; border-radius: 50%; border: 2px solid rgba(79, 191, 138, 0.5); animation: p-wave 2.4s 0.5s ease-out infinite; }
.tick { stroke-dasharray: 24; stroke-dashoffset: 24; animation: p-tick 0.5s 0.45s var(--ease-out) forwards; }
.orb.wait { color: #f6c79a; }
.orb.pulse::after { content: ""; position: absolute; inset: -8px; border-radius: 50%; border: 2px solid rgba(217, 101, 59, 0.45); animation: p-wave 1.8s ease-out infinite; }
.orb.bad { background: linear-gradient(140deg, #e0705f, #b84535); box-shadow: 0 0 0 8px rgba(224, 112, 95, 0.14), 0 20px 40px -18px rgba(120, 40, 30, 0.7); }
.orb.muted-orb { background: linear-gradient(160deg, #8a8178, #5d564f); }
.orb.loading { background: rgba(255, 255, 255, 0.8); }
.loader { width: 38px; height: 38px; border-radius: 50%; border: 3px solid rgba(28, 25, 21, 0.08); border-top-color: #d9653b; animation: p-rot 0.9s linear infinite; }
@keyframes p-rot { to { transform: rotate(360deg); } }
@keyframes p-pop { from { transform: scale(0.4); opacity: 0; } 60% { transform: scale(1.08); opacity: 1; } to { transform: scale(1); } }
@keyframes p-tick { to { stroke-dashoffset: 0; } }
@keyframes p-wave { from { transform: scale(1); opacity: 1; } to { transform: scale(1.5); opacity: 0; } }

/* Оплачено */
.paid { text-align: center; }
.paid-head { margin-bottom: 34px; }
.paid-head .kicker { justify-content: center; }
.chips { display: flex; justify-content: center; flex-wrap: wrap; gap: 10px; margin-top: 24px; }
.chip {
  display: grid;
  gap: 2px;
  min-width: 130px;
  padding: 12px 20px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.95);
  box-shadow: 0 14px 30px -20px rgba(60, 40, 15, 0.5);
  animation: p-rise 0.6s var(--ease-out) both;
}
.chip:nth-child(2) { animation-delay: 0.1s; }
.chip:nth-child(3) { animation-delay: 0.2s; }
.chip small { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }
.chip b { font-size: 22px; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }
.chip.bonus b { color: #2f8f63; }
.chip.dark { background: linear-gradient(160deg, #2b2620, #15120e); border-color: transparent; color: #fff; }
.chip.dark small { color: rgba(255, 255, 255, 0.55); }
.chip.dark b { background: linear-gradient(90deg, #ffb487, #d6b8ff); -webkit-background-clip: text; background-clip: text; color: transparent; }
@keyframes p-rise { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }

@property --pay-angle { syntax: "<angle>"; initial-value: 0deg; inherits: false; }
.key-frame { position: relative; padding: 2px; border-radius: 28px; text-align: left; animation: p-rise 0.8s 0.35s var(--ease-out) both; }
.key-ring {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: conic-gradient(from var(--pay-angle), #d9653b, #f2b27a, #b07be0, #6e8cf0, #d9653b);
  animation: p-spin 6s linear infinite;
}
.key-ring::after { content: ""; position: absolute; inset: 10px; border-radius: inherit; background: inherit; filter: blur(30px); opacity: 0.45; z-index: -1; }
@keyframes p-spin { to { --pay-angle: 360deg; } }
.key-inner { position: relative; padding: 8px; border-radius: 26px; background: rgba(255, 255, 255, 0.92); }
.key-inner :deep(.card) { border: 0; box-shadow: none; background: transparent; margin: 0; }
.key-inner .notice { margin: 12px; }

.next { list-style: none; margin: 30px 0 0; padding: 0; display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; text-align: left; }
.next li {
  display: grid;
  gap: 4px;
  padding: 18px 18px 20px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid rgba(255, 255, 255, 0.95);
  box-shadow: 0 14px 30px -24px rgba(60, 40, 15, 0.5);
  animation: p-rise 0.6s var(--ease-out) both;
}
.next li:nth-child(1) { animation-delay: 0.55s; }
.next li:nth-child(2) { animation-delay: 0.65s; }
.next li:nth-child(3) { animation-delay: 0.75s; }
.next .n {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  margin-bottom: 8px;
  border-radius: 9px;
  background: linear-gradient(135deg, #d9653b, #b07be0);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
}
.next b { font-size: 15.5px; }
.next small { color: var(--muted-2); font-size: 13.5px; line-height: 1.45; }

.actions { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 26px; }
.actions.center { justify-content: center; }
.btn.go { min-height: 54px; padding: 0 26px; border-radius: 18px; font-size: 16px; gap: 10px; }
.btn.go svg { transition: transform 0.25s var(--ease-out); }
.btn.go:hover svg { transform: translateX(3px); }

.recheck { margin-top: 26px; padding-top: 20px; border-top: 1px solid rgba(28, 25, 21, 0.08); }
.recheck p { margin: 0 0 10px; }

.swap-enter-active, .swap-leave-active { transition: opacity 0.3s ease, transform 0.4s var(--ease-out); }
.swap-enter-from { opacity: 0; transform: translateY(12px); }
.swap-leave-to { opacity: 0; transform: translateY(-12px); }

@media (max-width: 760px) {
  .pay-wrap { padding-top: 32px; padding-bottom: 56px; }
  .panel { margin-top: 12px; padding: 32px 20px 26px; border-radius: 24px; }
  .next { grid-template-columns: 1fr; }
  .actions .btn { flex: 1 1 100%; justify-content: center; }
  .chip { min-width: 0; flex: 1 1 30%; padding: 10px 12px; }
  .chip b { font-size: 18px; }
}
@media (prefers-reduced-motion: reduce) {
  .pay-aurora i, .orb, .orb::after, .tick, .chip, .key-frame, .key-ring, .next li { animation: none !important; }
  .tick { stroke-dashoffset: 0; }
}
</style>
