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

        <section class="faq-block card soft">
          <h2>Частые вопросы</h2>
          <div class="faq-list">
            <details v-for="item in faqItems" :key="item.q">
              <summary>
                <span>{{ item.q }}</span>
                <AppIcon name="chevron" :size="16" class="chev" />
              </summary>
              <div class="faq-body" v-html="item.a" />
            </details>
          </div>
          <p class="faq-more muted small">
            Документы и справка также в разделе
            <RouterLink to="/help">«Справочный центр»</RouterLink>.
          </p>
        </section>

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
import AppIcon from '../components/ui/AppIcon.vue'
import { webApi } from '../api/web'
import { useSession } from '../composables/useSession'
import { siteFaqItems } from '../utils/siteFaq'
import { useHead } from '../utils/useHead'

useHead({
  title: 'Поддержка — Aimarket',
  description: 'Чат поддержки Aimarket: пишите без авторизации — ответим на вопросы по тарифам, оплате и подключению.',
})

const { isLoggedIn } = useSession()
const booting = ref(true)
const blocked = ref(false)
const faqItems = siteFaqItems()

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

.faq-block {
  margin-bottom: 16px;
  padding: 18px 20px 16px;
}
.faq-block h2 {
  margin: 0 0 10px;
  font-size: 16px;
  letter-spacing: -0.02em;
}
.faq-list details {
  border-bottom: 1px solid var(--border);
}
.faq-list details:last-child { border-bottom: 0; }
.faq-list summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
  cursor: pointer;
  list-style: none;
  font-weight: 650;
  font-size: 15px;
}
.faq-list summary::-webkit-details-marker { display: none; }
.faq-list .chev {
  color: var(--muted);
  transition: transform 0.18s ease;
  flex: 0 0 auto;
}
.faq-list details[open] .chev { transform: rotate(180deg); }
.faq-body {
  padding: 0 0 14px;
  font-size: 14.5px;
  color: var(--muted-2);
  line-height: 1.55;
}
.faq-body :deep(p) { margin: 0 0 8px; }
.faq-body :deep(ol),
.faq-body :deep(ul) { margin: 0 0 8px; padding-left: 20px; }
.faq-body :deep(li) { margin-bottom: 4px; }
.faq-body :deep(code) {
  font-size: 13px;
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 1px 6px;
  border-radius: 6px;
}
.faq-body :deep(a),
.faq-more a {
  text-decoration: underline;
  text-underline-offset: 3px;
}
.faq-more { margin: 10px 0 0; }
</style>
