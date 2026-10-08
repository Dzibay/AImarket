<template>
  <div v-if="!hiddenOnAdmin" class="support-widget">
    <transition name="panel">
      <div v-if="open" class="panel" role="dialog" aria-label="Чат поддержки">
        <header class="panel-head">
          <div>
            <strong>Поддержка</strong>
            <p class="muted small">Обычно отвечаем в течение дня</p>
          </div>
          <button type="button" class="icon-btn" aria-label="Закрыть" @click="open = false">×</button>
        </header>

        <SupportChat v-if="isLoggedIn" compact class="panel-chat" />

        <div v-else class="guest">
          <p>Войдите в личный кабинет, чтобы написать в чат на сайте.</p>
          <div class="guest-actions">
            <RouterLink to="/login" class="btn sm" @click="open = false">Войти по ключу</RouterLink>
            <a v-if="telegramHref" class="btn quiet sm" :href="telegramHref" target="_blank" rel="noopener">
              Telegram
            </a>
          </div>
          <p v-if="!telegramHref" class="muted small">Контакты появятся после настройки поддержки.</p>
        </div>
      </div>
    </transition>

    <button
      type="button"
      class="fab"
      :aria-expanded="open"
      :aria-label="open ? 'Закрыть чат' : 'Открыть чат поддержки'"
      @click="toggle"
    >
      <span v-if="unread > 0 && !open" class="badge">{{ unread > 9 ? '9+' : unread }}</span>
      <AppIcon v-if="open" name="chevron" :size="22" class="close-icon" />
      <AppIcon v-else name="help" :size="22" />
    </button>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import AppIcon from './ui/AppIcon.vue'
import SupportChat from './SupportChat.vue'
import { useSession } from '../composables/useSession'
import { useSupportUnread } from '../composables/useSupportUnread'
import { useWebConfig } from '../composables/useWebConfig'

const open = ref(false)
const route = useRoute()
const { isLoggedIn } = useSession()
const { config, loadConfig } = useWebConfig()
const { unread, startPolling, stopPolling, refreshUnread } = useSupportUnread()

const hiddenOnAdmin = computed(() => {
  const path = String(route.path || '')
  return path.startsWith('/admin') || path === '/cabinet/support'
})

watch(
  () => route.path,
  () => {
    if (hiddenOnAdmin.value) open.value = false
  },
)
const telegramHref = computed(() => {
  const username = config.value?.support_username
  if (username) return `https://t.me/${username}`
  return config.value?.bot_url || ''
})

function toggle() {
  open.value = !open.value
}

watch(open, (value) => {
  if (value) refreshUnread()
})

watch(isLoggedIn, (value) => {
  if (value) startPolling()
  else {
    stopPolling()
    open.value = false
  }
})

onMounted(async () => {
  await loadConfig()
  if (isLoggedIn.value) startPolling()
})

onBeforeUnmount(stopPolling)
</script>

<style scoped>
.support-widget {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 40;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}
.fab {
  position: relative;
  width: 56px;
  height: 56px;
  border: 0;
  border-radius: 50%;
  background: var(--accent);
  color: var(--bg);
  cursor: pointer;
  box-shadow: 0 16px 36px rgba(28, 25, 21, 0.22);
  display: grid;
  place-items: center;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.fab:hover { transform: translateY(-2px); box-shadow: 0 20px 40px rgba(28, 25, 21, 0.26); }
.close-icon { transform: rotate(180deg); }
.badge {
  position: absolute;
  top: -2px;
  right: -2px;
  min-width: 20px;
  height: 20px;
  padding: 0 5px;
  border-radius: 999px;
  background: var(--danger);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: grid;
  place-items: center;
  box-shadow: 0 0 0 2px var(--bg);
}
.panel {
  width: min(380px, calc(100vw - 32px));
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: 0 24px 60px rgba(28, 25, 21, 0.18);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 14px 10px;
  border-bottom: 1px solid var(--border);
  background: var(--surface-soft);
}
.panel-head strong { display: block; font-size: 1rem; letter-spacing: -0.02em; }
.panel-head p { margin: 2px 0 0; }
.icon-btn {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--muted);
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
}
.icon-btn:hover { background: rgba(28, 25, 21, 0.06); color: var(--text); }
.panel-chat { border: 0; border-radius: 0; }
.guest {
  padding: 18px 16px 20px;
  display: grid;
  gap: 14px;
}
.guest p { margin: 0; }
.guest-actions { display: flex; flex-wrap: wrap; gap: 8px; }

.panel-enter-active, .panel-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.panel-enter-from, .panel-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.98);
}

@media (max-width: 480px) {
  .support-widget { right: 14px; bottom: 14px; }
  .panel { width: calc(100vw - 28px); }
}
</style>
