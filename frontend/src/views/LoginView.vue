<template>
  <div class="site login-page">
    <SiteHeader />
    <main class="site-main">
      <div class="login-aurora" aria-hidden="true"><i /><i /></div>
      <div class="container login-grid">
        <section class="login-art" aria-hidden="true">
          <div class="mini-orbit">
            <div class="ring r1">
              <span v-for="(b, i) in inner" :key="b" class="sat" :style="{ '--a': `${i * (360 / inner.length)}deg` }">
                <span class="sat-tile"><BrandLogo :brand="b" :size="20" /></span>
              </span>
            </div>
            <div class="ring r2">
              <span v-for="(b, i) in outer" :key="b" class="sat" :style="{ '--a': `${i * (360 / outer.length) + 30}deg` }">
                <span class="sat-tile"><BrandLogo :brand="b" :size="18" /></span>
              </span>
            </div>
            <div class="core"><img src="/favicon-96x96.png" width="44" height="44" alt=""></div>
          </div>
          <div class="art-copy">
            <p class="kicker">Один ключ ко всем ИИ</p>
            <h2>Claude, GPT, Gemini —<br><span class="grad-text">на 90% дешевле</span></h2>
            <ul class="art-list">
              <li>Без пароля — вход по ссылке из письма</li>
              <li>Оплата картой РФ или СБП</li>
              <li>Cursor, Claude Code, Codex — одной командой</li>
            </ul>
          </div>
        </section>

        <section class="login-panel">
          <div class="panel">
            <Transition name="swap" mode="out-in">
              <div v-if="linkState === 'checking'" key="checking" class="state">
                <span class="loader" aria-hidden="true" />
                <h1 class="panel-title">Открываем кабинет…</h1>
                <p class="panel-lead">Проверяем ссылку из письма.</p>
              </div>

              <div v-else-if="emailSent" key="sent" class="state sent">
                <div class="envelope" aria-hidden="true">
                  <span class="env-back" />
                  <span class="env-letter"><i /><i /><i /></span>
                  <span class="env-front" />
                  <span class="env-flap" />
                </div>
                <h1 class="panel-title">Проверьте почту</h1>
                <p class="panel-lead">
                  Отправили ссылку на <b>{{ sentEmail }}</b>. Откройте письмо и нажмите «Войти в личный кабинет».
                </p>
                <a v-if="mailbox" :href="mailbox.url" target="_blank" rel="noopener" class="btn block mail-btn">
                  Открыть {{ mailbox.name }}
                  <AppIcon name="external" :size="16" />
                </a>
                <p class="small muted hint">
                  Письмо обычно приходит в течение минуты. Если его нет — загляните в «Спам».
                  Ссылка одноразовая и действует несколько дней.
                </p>
                <button type="button" class="link-btn" @click="resetEmailForm">Указать другую почту</button>
              </div>

              <div v-else key="form" class="state">
                <h1 class="panel-title">Вход в кабинет</h1>
                <p class="panel-lead">Введите почту — пришлём ссылку для входа. Нет аккаунта? Создадим автоматически.</p>

                <div v-if="linkState === 'failed'" class="notice warn link-card">
                  {{ linkError }} Запросите новое письмо или войдите по ключу.
                </div>

                <form class="email-form" @submit.prevent="submitEmail">
                  <label class="field-glow" :class="{ ok: emailOk }">
                    <AppIcon name="mail" :size="18" />
                    <input
                      v-model="email"
                      type="email"
                      autocomplete="email"
                      placeholder="name@example.com"
                      aria-label="Электронная почта"
                      required
                    >
                  </label>
                  <p v-if="error" class="error-text">{{ error }}</p>
                  <button type="submit" class="btn block go" :disabled="busy || !emailOk">
                    {{ busy ? 'Отправляем…' : 'Получить ссылку для входа' }}
                    <svg v-if="!busy" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14" /><path d="m13 6 6 6-6 6" /></svg>
                  </button>
                </form>

                <div class="divider"><span>или</span></div>

                <details class="key-alt">
                  <summary><AppIcon name="key" :size="16" />Войти по API-ключу<AppIcon name="chevron" :size="16" class="chev" /></summary>
                  <form @submit.prevent="submitKey">
                    <input
                      v-model="key"
                      class="input mono"
                      autocomplete="off"
                      spellcheck="false"
                      placeholder="sk-…"
                      aria-label="Ключ доступа"
                      required
                    >
                    <p v-if="keyError" class="error-text">{{ keyError }}</p>
                    <button type="submit" class="btn quiet block" :disabled="keyBusy || key.trim().length < 8">
                      {{ keyBusy ? 'Проверяем…' : 'Войти по ключу' }}
                    </button>
                    <p class="small muted hint">
                      Ключ начинается с <code>sk-</code>, приходит на почту после оплаты.
                      <template v-if="support"> Если ключ утерян — {{ support }}.</template>
                    </p>
                  </form>
                </details>
              </div>
            </Transition>
          </div>
          <p class="small muted foot">
            Не хотите ждать письмо? <RouterLink :to="{ path: '/', hash: '#pay' }">Пополните баланс</RouterLink> на главной —
            ключ и вход появятся сразу после оплаты.
          </p>
        </section>
      </div>
    </main>
    <SiteFooter />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getReferralToken } from '../utils/referral'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import SiteFooter from '../components/SiteFooter.vue'
import SiteHeader from '../components/SiteHeader.vue'
import BrandLogo from '../components/BrandLogo.vue'
import AppIcon from '../components/ui/AppIcon.vue'
import { errorText, webApi } from '../api/web'
import { claimGuestSupportIfNeeded } from '../composables/useGuestSupport'
import { useSession } from '../composables/useSession'
import { useHead } from '../utils/useHead'

const router = useRouter()
const route = useRoute()
const { isLoggedIn, setSession } = useSession()

const email = ref('')
const busy = ref(false)
const error = ref('')
const emailSent = ref(false)
const sentEmail = ref('')

const key = ref('')
const keyBusy = ref(false)
const keyError = ref('')

const config = ref(null)
const linkState = ref('')
const linkError = ref('')

const support = computed(() => {
  if (config.value?.support_username) return `@${config.value.support_username}`
  return config.value?.support_email || ''
})

const inner = ['claude', 'gpt', 'gemini']
const outer = ['grok', 'deepseek', 'china', 'claude', 'gpt']

// Кнопка «Открыть почту» для популярных сервисов.
const MAILBOXES = [
  { test: /^(gmail|googlemail)\.com$/, name: 'Gmail', url: 'https://mail.google.com/mail/u/0/#inbox' },
  { test: /^(yandex\.(ru|com|by|kz|ua)|ya\.ru)$/, name: 'Яндекс Почту', url: 'https://mail.yandex.ru' },
  { test: /^(mail|bk|inbox|list|internet)\.ru$/, name: 'Почту Mail.ru', url: 'https://e.mail.ru/inbox' },
  { test: /^(outlook|hotmail|live)\.com$/, name: 'Outlook', url: 'https://outlook.live.com/mail/' },
  { test: /^(icloud|me)\.com$/, name: 'iCloud Почту', url: 'https://www.icloud.com/mail' },
  { test: /^rambler\.ru$/, name: 'Рамблер Почту', url: 'https://mail.rambler.ru' },
]
const mailbox = computed(() => {
  const domain = sentEmail.value.split('@')[1] || ''
  return MAILBOXES.find((item) => item.test.test(domain)) || null
})

const emailOk = computed(() => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.value.trim()))

function afterLoginPath() {
  const next = String(route.query.next || '').trim()
  if (next === 'chat') return '/help?chat=1'
  if (next === 'cabinet') return '/cabinet'
  return '/cabinet'
}

async function loginByLink(token) {
  linkState.value = 'checking'
  try {
    const result = await webApi.loginByLink(token)
    setSession(result.session)
    await claimGuestSupportIfNeeded()
    router.replace(afterLoginPath())
  } catch (err) {
    linkError.value = errorText(err)
    linkState.value = 'failed'
  }
}

function resetEmailForm() {
  emailSent.value = false
  sentEmail.value = ''
  error.value = ''
}

async function submitEmail() {
  if (busy.value || !emailOk.value) return
  busy.value = true
  error.value = ''
  try {
    const value = email.value.trim().toLowerCase()
    await webApi.loginByEmail(value, getReferralToken())
    sentEmail.value = value
    emailSent.value = true
  } catch (err) {
    error.value = errorText(err)
  } finally {
    busy.value = false
  }
}

async function submitKey() {
  if (keyBusy.value) return
  keyBusy.value = true
  keyError.value = ''
  try {
    const result = await webApi.login(key.value.trim())
    setSession(result.session)
    await claimGuestSupportIfNeeded()
    router.replace('/cabinet')
  } catch (err) {
    keyError.value = errorText(err)
  } finally {
    keyBusy.value = false
  }
}

onMounted(async () => {
  useHead('Вход — Aimarket', true)
  const linkToken = String(route.query.t || '')
  if (linkToken) {
    await loginByLink(linkToken)
    return
  }
  if (isLoggedIn.value) {
    router.replace('/cabinet')
    return
  }
  try {
    config.value = await webApi.config()
  } catch {
    config.value = null
  }
})
</script>

<style scoped>
.login-page .site-main { position: relative; isolation: isolate; overflow: hidden; }
.login-aurora { position: absolute; inset: -100px 0 0; z-index: -1; pointer-events: none; }
.login-aurora i { position: absolute; border-radius: 50%; filter: blur(100px); opacity: 0.5; animation: l-drift 16s ease-in-out infinite alternate; }
.login-aurora i:nth-child(1) { width: 560px; height: 460px; left: -140px; top: 60px; background: #f2b27a; }
.login-aurora i:nth-child(2) { width: 520px; height: 420px; right: -120px; top: 180px; background: #c9b2f0; animation-delay: -8s; }
@keyframes l-drift { to { transform: translate(70px, -40px) scale(1.1); } }

.login-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 480px);
  gap: 64px;
  align-items: center;
  min-height: calc(100svh - 90px);
  padding-top: 48px;
  padding-bottom: 72px;
}

/* Левая часть: мини-орбита */
.login-art { display: grid; justify-items: start; gap: 34px; }
.mini-orbit { position: relative; width: 340px; aspect-ratio: 1; margin-left: 10px; }
.ring { position: absolute; border-radius: 50%; border: 1px dashed rgba(28, 25, 21, 0.14); animation: l-rot 40s linear infinite; }
.r1 { inset: 22%; }
.r2 { inset: 0; animation-duration: 60s; animation-direction: reverse; }
.sat { position: absolute; left: 50%; top: 50%; width: 0; height: 0; transform: rotate(var(--a)) translateY(calc(var(--r) * -1)); }
.r1 .sat { --r: 95px; }
.r2 .sat { --r: 170px; }
.sat-tile {
  position: absolute;
  left: -22px;
  top: -22px;
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  background: #fff;
  border: 1px solid rgba(255, 255, 255, 0.95);
  box-shadow: 0 12px 26px -14px rgba(40, 28, 12, 0.5);
  color: var(--text);
  transform: rotate(calc(var(--a) * -1));
  animation: l-counter 40s linear infinite;
}
.r2 .sat-tile { width: 40px; height: 40px; left: -20px; top: -20px; animation-duration: 60s; animation-direction: reverse; }
@keyframes l-rot { to { transform: rotate(360deg); } }
@keyframes l-counter { from { rotate: 0deg; } to { rotate: -360deg; } }
.core {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 84px;
  height: 84px;
  margin: -42px 0 0 -42px;
  display: grid;
  place-items: center;
  border-radius: 26px;
  background: linear-gradient(160deg, #2b2620, #15120e);
  box-shadow: 0 0 0 8px rgba(255, 255, 255, 0.5), 0 0 60px rgba(217, 101, 59, 0.55), 0 20px 40px -16px rgba(21, 18, 14, 0.7);
}
.core img { border-radius: 12px; }
.art-copy h2 { margin: 0 0 18px; font-size: clamp(2rem, 3.6vw, 3rem); font-weight: 680; line-height: 1.04; letter-spacing: -0.055em; }
.art-copy .dot { width: 7px; height: 7px; border-radius: 50%; background: #3f9b6f; }
.art-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.art-list li { position: relative; padding-left: 28px; color: var(--muted-2); font-size: 15.5px; }
.art-list li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 3px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: linear-gradient(135deg, #d9653b, #b07be0);
  -webkit-mask: radial-gradient(circle, transparent 0 4px, #000 4.5px);
  mask: radial-gradient(circle, transparent 0 4px, #000 4.5px);
}

/* Правая часть: стеклянная карточка */
.panel {
  position: relative;
  padding: 36px 34px 30px;
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.95);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.9) inset, 0 40px 80px -40px rgba(60, 40, 15, 0.5);
  backdrop-filter: blur(20px) saturate(1.3);
  -webkit-backdrop-filter: blur(20px) saturate(1.3);
}
.panel-title { margin: 0 0 10px; font-size: clamp(1.8rem, 3vw, 2.3rem); font-weight: 680; letter-spacing: -0.05em; line-height: 1.05; }
.panel-lead { margin: 0 0 24px; color: var(--muted-2); font-size: 15.5px; line-height: 1.5; }
.link-card { margin-bottom: 16px; }
.email-form { display: grid; gap: 12px; }
.field-glow {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 18px;
  min-height: 58px;
  border-radius: 18px;
  background: #fff;
  border: 1px solid var(--border-strong);
  color: var(--muted);
  transition: border-color 0.2s ease, box-shadow 0.3s ease;
}
.field-glow:focus-within { border-color: #e0a27a; box-shadow: 0 0 0 4px rgba(217, 101, 59, 0.12), 0 12px 30px -16px rgba(217, 101, 59, 0.5); }
.field-glow.ok { color: #3f9b6f; }
.field-glow input { flex: 1; min-width: 0; border: 0; outline: 0; background: none; font: inherit; font-size: 17px; color: var(--text); }
.btn.go, .mail-btn { min-height: 56px; border-radius: 18px; font-size: 16px; gap: 10px; justify-content: center; }
.btn.go svg { transition: transform 0.25s var(--ease-out); }
.btn.go:hover svg { transform: translateX(3px); }
.divider { display: flex; align-items: center; gap: 12px; margin: 22px 0 14px; color: var(--muted); font-size: 12.5px; }
.divider::before, .divider::after { content: ""; flex: 1; height: 1px; background: rgba(28, 25, 21, 0.1); }
.key-alt { border-radius: 18px; background: rgba(255, 255, 255, 0.55); border: 1px solid rgba(28, 25, 21, 0.07); }
.key-alt summary { display: flex; align-items: center; gap: 10px; padding: 15px 18px; cursor: pointer; list-style: none; font-size: 14.5px; font-weight: 600; color: var(--muted-2); }
.key-alt summary::-webkit-details-marker { display: none; }
.key-alt .chev { margin-left: auto; transition: transform 0.3s var(--ease-out); }
.key-alt[open] .chev { transform: rotate(180deg); }
.key-alt form { display: grid; gap: 10px; padding: 0 18px 18px; }
.hint { margin: 14px 0 0; line-height: 1.5; }
.key-alt .hint { margin: 2px 0 0; }
.hint code { font-size: 12.5px; background: rgba(28, 25, 21, 0.06); padding: 1px 6px; border-radius: 6px; }
.mono { font-family: var(--font-mono); font-size: 0.95rem; }
.link-btn { margin-top: 14px; padding: 0; border: 0; background: none; color: #c4572f; font: inherit; font-size: 14px; font-weight: 600; cursor: pointer; }
.foot { margin: 16px 6px 0; text-align: center; }
.foot a, .small a { text-decoration: underline; text-underline-offset: 3px; }

.state { text-align: left; }
.loader {
  display: block;
  width: 44px;
  height: 44px;
  margin-bottom: 20px;
  border-radius: 50%;
  border: 3px solid rgba(28, 25, 21, 0.08);
  border-top-color: #d9653b;
  animation: l-rot 0.9s linear infinite;
}

/* Конверт */
.sent { text-align: center; }
.sent .panel-lead { margin-bottom: 20px; }
.envelope { position: relative; width: 120px; height: 84px; margin: 6px auto 26px; }
.env-back, .env-front, .env-flap { position: absolute; left: 0; right: 0; }
.env-back { inset: 0; border-radius: 12px; background: linear-gradient(160deg, #2b2620, #15120e); }
.env-front {
  bottom: 0;
  height: 100%;
  border-radius: 12px;
  background: linear-gradient(160deg, #3a332b, #1d1915);
  clip-path: polygon(0 30%, 50% 70%, 100% 30%, 100% 100%, 0 100%);
  z-index: 3;
}
.env-flap {
  top: 0;
  height: 60%;
  background: linear-gradient(180deg, #4a4037, #2b2620);
  clip-path: polygon(0 0, 100% 0, 50% 100%);
  transform-origin: top;
  z-index: 4;
  animation: l-flap 0.6s 0.2s var(--ease-out) both;
}
.env-letter {
  position: absolute;
  left: 12px;
  right: 12px;
  top: 10px;
  height: 70px;
  padding: 12px 12px 0;
  display: grid;
  align-content: start;
  gap: 7px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 6px 18px -8px rgba(0, 0, 0, 0.4);
  z-index: 2;
  animation: l-letter 0.8s 0.6s var(--ease-out) both;
}
.env-letter i { display: block; height: 5px; border-radius: 3px; background: rgba(28, 25, 21, 0.12); }
.env-letter i:first-child { width: 60%; background: linear-gradient(90deg, #d9653b, #b07be0); }
.env-letter i:last-child { width: 75%; }
@keyframes l-flap { from { transform: rotateX(0deg); } to { transform: rotateX(180deg); z-index: 1; } }
@keyframes l-letter { from { transform: translateY(20px); } to { transform: translateY(-38px); } }
.envelope::after {
  content: "";
  position: absolute;
  inset: -20px;
  z-index: -1;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(217, 101, 59, 0.35), transparent 65%);
  filter: blur(10px);
}

.swap-enter-active, .swap-leave-active { transition: opacity 0.3s ease, transform 0.4s var(--ease-out); }
.swap-enter-from { opacity: 0; transform: translateY(10px); }
.swap-leave-to { opacity: 0; transform: translateY(-10px); }

@media (max-width: 960px) {
  .login-grid { grid-template-columns: 1fr; gap: 28px; min-height: 0; padding-top: 32px; }
  .login-panel { order: -1; width: min(520px, 100%); margin: 0 auto; }
  .login-art { justify-items: center; text-align: center; }
  .art-list { justify-items: center; }
  .mini-orbit { display: none; }
}
@media (max-width: 560px) {
  .login-grid { padding-top: 22px; padding-bottom: 48px; }
  .panel { padding: 26px 18px 22px; border-radius: 24px; }
  .art-copy { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .ring, .sat-tile, .login-aurora i, .env-flap, .env-letter { animation: none; }
}
</style>
