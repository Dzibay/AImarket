<template>
  <div class="site">
    <SiteHeader />
    <main class="site-main">
      <div class="container wrap">
        <div class="head">
          <div>
            <RouterLink to="/cabinet" class="back">← Личный кабинет</RouterLink>
            <h1 class="page-title">Поддержка</h1>
            <p class="page-lead">Чат с командой Aimarket. Ответ обычно в течение дня.</p>
          </div>
        </div>

        <template v-if="booting">
          <div class="card soft"><p class="muted">Проверяем сессию…</p></div>
        </template>
        <template v-else-if="!isLoggedIn">
          <div class="card soft">
            <p>Чтобы писать в чат, войдите по API-ключу.</p>
            <div class="actions">
              <RouterLink to="/login" class="btn">Войти</RouterLink>
              <a v-if="telegramHref" class="btn quiet" :href="telegramHref" target="_blank" rel="noopener">
                Telegram
              </a>
            </div>
          </div>
        </template>
        <SupportChat v-else :blocked="blocked" />

        <p v-if="isLoggedIn && telegramHref" class="alt muted small">
          Или напишите в Telegram:
          <a :href="telegramHref" target="_blank" rel="noopener">{{ telegramLabel }}</a>
        </p>
      </div>
    </main>
    <SiteFooter />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import SiteFooter from '../components/SiteFooter.vue'
import SiteHeader from '../components/SiteHeader.vue'
import SupportChat from '../components/SupportChat.vue'
import { webApi } from '../api/web'
import { useSession } from '../composables/useSession'
import { useWebConfig } from '../composables/useWebConfig'
import { useHead } from '../utils/useHead'

useHead({
  title: 'Поддержка — Aimarket',
  description: 'Чат поддержки Aimarket: вопросы по ключу, оплате и подключению.',
})

const router = useRouter()
const { isLoggedIn } = useSession()
const { config, loadConfig } = useWebConfig()
const booting = ref(true)
const blocked = ref(false)

const telegramHref = computed(() => {
  const username = config.value?.support_username
  if (username) return `https://t.me/${username}`
  return config.value?.bot_url || ''
})
const telegramLabel = computed(() => {
  if (config.value?.support_username) return `@${config.value.support_username}`
  return 'Telegram-бот'
})

onMounted(async () => {
  await loadConfig()
  if (!isLoggedIn.value) {
    booting.value = false
    return
  }
  try {
    const profile = await webApi.me()
    blocked.value = !!profile.blocked
  } catch {
    router.replace('/login')
    return
  }
  booting.value = false
})
</script>

<style scoped>
.wrap { padding: 12px 24px 48px; max-width: 760px; }
.head { margin-bottom: 18px; }
.back {
  display: inline-block;
  margin-bottom: 10px;
  color: var(--muted);
  font-size: 14px;
  text-decoration: underline;
  text-underline-offset: 3px;
}
.page-title {
  margin: 0 0 6px;
  font-size: clamp(1.6rem, 3vw, 2rem);
  letter-spacing: -0.03em;
}
.page-lead { margin: 0; color: var(--muted); }
.actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }
.alt { margin: 14px 0 0; }
.alt a { text-decoration: underline; text-underline-offset: 3px; }
</style>
