<template>
  <div class="site">
    <SiteHeader />
    <main class="site-main">
      <div class="narrow wrap">
        <h1 class="page-title">Вход в личный кабинет</h1>
        <p class="page-lead">
          Вместо логина и пароля у вас один ключ доступа — тот самый, который вы получили после оплаты и
          используете для запросов к нейросетям. Вставьте его целиком.
        </p>
        <div v-if="linkState === 'checking'" class="card soft link-card">
          <p class="muted">Открываем кабинет по ссылке из письма…</p>
        </div>
        <div v-else-if="linkState === 'failed'" class="notice link-card">
          {{ linkError }} Ниже можно войти по ключу вручную.
        </div>
        <form class="card" @submit.prevent="submit">
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
          <p v-if="error" class="error-text">{{ error }}</p>
          <button type="submit" class="btn block" :disabled="busy || key.trim().length < 8">
            {{ busy ? 'Проверяем…' : 'Войти' }}
          </button>
          <p class="small muted hint">
            Ключ начинается с <code>sk-</code>. Он был показан на экране сразу после оплаты и отправлен на почту.
            Если ключ утерян, напишите в поддержку<template v-if="support"> — {{ support }}</template>.
          </p>
          <p class="small muted">
            Ещё нет ключа? <RouterLink to="/">Пополните баланс</RouterLink> — ключ выдаётся сразу после оплаты.
          </p>
        </form>
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
const key = ref('')
const busy = ref(false)
const error = ref('')
const config = ref(null)
const linkState = ref('')
const linkError = ref('')

const support = computed(() => {
  if (config.value?.support_username) return `@${config.value.support_username}`
  return config.value?.support_email || ''
})

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

async function submit() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    const result = await webApi.login(key.value.trim())
    setSession(result.session)
    await claimGuestSupportIfNeeded()
    router.replace('/cabinet')
  } catch (err) {
    error.value = errorText(err)
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.wrap { padding-top: 40px; padding-bottom: 72px; }
.link-card { margin-bottom: 16px; }
.hint { margin-top: 14px; }
.hint code { font-size: 13px; background: var(--surface-soft); padding: 1px 6px; border-radius: 6px; }
.small a { text-decoration: underline; text-underline-offset: 3px; }
</style>
