<template>
  <div class="site">
    <SiteHeader />
    <main class="site-main">
      <div class="container wrap">
        <div class="head">
          <div>
            <RouterLink v-if="isLoggedIn" to="/cabinet" class="back">← Личный кабинет</RouterLink>
            <RouterLink v-else to="/" class="back">← На главную</RouterLink>
            <h1 class="page-title">Поддержка</h1>
            <p class="page-lead">{{ lead }}</p>
          </div>
        </div>

        <template v-if="booting">
          <div class="card soft"><p class="muted">Открываем чат…</p></div>
        </template>
        <SupportChat v-else :blocked="blocked" />
      </div>
    </main>
    <SiteFooter />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import SiteFooter from '../components/SiteFooter.vue'
import SiteHeader from '../components/SiteHeader.vue'
import SupportChat from '../components/SupportChat.vue'
import { webApi } from '../api/web'
import { useSession } from '../composables/useSession'
import { useHead } from '../utils/useHead'

useHead({
  title: 'Поддержка — Aimarket',
  description: 'Чат поддержки Aimarket: пишите без авторизации — ответим на вопросы по тарифам, оплате и подключению.',
})

const { isLoggedIn } = useSession()
const booting = ref(true)
const blocked = ref(false)

const lead = computed(() =>
  isLoggedIn.value
    ? 'Чат с командой Aimarket. Ответ в течение нескольких минут.'
    : 'Пишите без авторизации — ответим в течение пары минут. Диалог сохранится в этом браузере.',
)

onMounted(async () => {
  if (isLoggedIn.value) {
    try {
      const profile = await webApi.me()
      blocked.value = !!profile.blocked
    } catch {
      blocked.value = false
    }
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
</style>
