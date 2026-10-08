<template>
  <div class="site">
    <SiteHeader />
    <main class="site-main">
      <div class="narrow wrap">
        <h1 class="page-title">Вход в личный кабинет</h1>
        <p class="page-lead">
          Введите почту — пришлём письмо со ссылкой для входа. Аккаунт создастся автоматически, если его ещё нет.
        </p>

        <div v-if="linkState === 'checking'" class="card soft link-card">
          <p class="muted">Открываем кабинет по ссылке из письма…</p>
        </div>
        <div v-else-if="linkState === 'failed'" class="notice link-card">
          {{ linkError }} Запросите новое письмо ниже или войдите по ключу.
        </div>

        <form v-if="emailSent" class="card soft sent-card">
          <h2 class="card-title sm">Проверьте почту</h2>
          <p>
            Отправили ссылку на <b>{{ sentEmail }}</b>. Откройте письмо и нажмите «Войти в личный кабинет».
          </p>
          <p class="muted small">
            Письмо обычно приходит в течение минуты. Если его нет — загляните в «Спам».
            Ссылка действует несколько дней и одноразовая.
          </p>
          <button type="button" class="btn quiet sm" @click="resetEmailForm">Указать другую почту</button>
        </form>

        <form v-else class="card" @submit.prevent="submitEmail">
          <label class="field">
            <span>Электронная почта</span>
            <input
              v-model="email"
              class="input"
              type="email"
              autocomplete="email"
              placeholder="name@example.com"
              required
            >
          </label>
          <p v-if="error" class="error-text">{{ error }}</p>
          <button type="submit" class="btn block" :disabled="busy || !emailOk">
            {{ busy ? 'Отправляем…' : 'Получить ссылку для входа' }}
          </button>
          <p class="small muted hint">
            Если аккаунта ещё нет — создадим его и пришлём письмо. Ключ API появится после первого пополнения.
          </p>
        </form>

        <details class="key-alt">
          <summary>Войти по API-ключу</summary>
          <form class="card soft" @submit.prevent="submitKey">
            <label class="field">
              <span>Ключ доступа</span>
              <input
                v-model="key"
                class="input mono"
                autocomplete="off"
                spellcheck="false"
                placeholder="sk-…"
                required
              >
            </label>
            <p v-if="keyError" class="error-text">{{ keyError }}</p>
            <button type="submit" class="btn quiet block" :disabled="keyBusy || key.trim().length < 8">
              {{ keyBusy ? 'Проверяем…' : 'Войти по ключу' }}
            </button>
            <p class="small muted hint">
              Ключ начинается с <code>sk-</code>. Он выдаётся после оплаты и приходит на почту.
              <template v-if="support"> Если ключ утерян — {{ support }}.</template>
            </p>
          </form>
        </details>

        <p class="small muted foot">
          Ещё нет аккаунта и не хотите ждать письмо?
          <RouterLink to="/">Пополните баланс</RouterLink> на главной — ключ и вход появятся сразу после оплаты.
        </p>
      </div>
    </main>
    <SiteFooter />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import SiteFooter from '../components/SiteFooter.vue'
import SiteHeader from '../components/SiteHeader.vue'
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

const emailOk = computed(() => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.value.trim()))

async function loginByLink(token) {
  linkState.value = 'checking'
  try {
    const result = await webApi.loginByLink(token)
    setSession(result.session)
    await claimGuestSupportIfNeeded()
    router.replace('/cabinet')
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
    await webApi.loginByEmail(value)
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
.wrap { padding-top: 40px; padding-bottom: 72px; }
.link-card { margin-bottom: 16px; }
.sent-card p { margin: 0 0 10px; }
.sent-card .btn { margin-top: 6px; }
.hint { margin-top: 14px; }
.hint code { font-size: 13px; background: var(--surface-soft); padding: 1px 6px; border-radius: 6px; }
.small a { text-decoration: underline; text-underline-offset: 3px; }
.foot { margin-top: 18px; }
.key-alt {
  margin-top: 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: rgba(255, 255, 255, 0.45);
  overflow: hidden;
}
.key-alt summary {
  cursor: pointer;
  list-style: none;
  padding: 14px 18px;
  font-weight: 600;
  font-size: 14px;
  color: var(--muted-2);
}
.key-alt summary::-webkit-details-marker { display: none; }
.key-alt[open] summary { border-bottom: 1px solid var(--border); }
.key-alt .card {
  border: 0;
  border-radius: 0;
  box-shadow: none;
  background: transparent;
}
.mono { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 0.95rem; }
</style>
