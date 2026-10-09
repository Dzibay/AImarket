<template>
  <div v-if="!hidden" class="support-widget">
    <transition name="panel">
      <div v-if="open" class="panel" role="dialog" aria-label="Чат поддержки">
        <header class="panel-head">
          <div>
            <strong>Чат поддержки</strong>
            <p class="muted small">{{ subtitle }}</p>
          </div>
          <button type="button" class="icon-btn" aria-label="Закрыть" @click="closeChat">×</button>
        </header>
        <SupportChat v-if="open" compact class="panel-chat" />
      </div>
    </transition>

    <button
      type="button"
      class="fab"
      :class="{ alert: unread > 0 && !open }"
      :aria-expanded="open"
      :aria-label="open ? 'Закрыть чат' : unread > 0 ? `Открыть чат, ${unread} новых` : 'Открыть чат поддержки'"
      @click="toggleChat"
    >
      <span v-if="unread > 0 && !open" class="badge">{{ unread > 9 ? '9+' : unread }}</span>
      <AppIcon v-if="open" name="chevron" :size="22" class="close-icon" />
      <AppIcon v-else name="chat" :size="22" />
    </button>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from './ui/AppIcon.vue'
import SupportChat from './SupportChat.vue'
import { useSession } from '../composables/useSession'
import {
  clearSupportNotify,
  setSupportAttention,
} from '../composables/useSupportNotify'
import { useSupportUnread } from '../composables/useSupportUnread'
import { useSupportWidget } from '../composables/useSupportWidget'

const route = useRoute()
const router = useRouter()
const { isLoggedIn } = useSession()
const { unread, startPolling, stopPolling, refreshUnread } = useSupportUnread()
const { open, closeChat, toggleChat, openChat } = useSupportWidget()

const hidden = computed(() => String(route.path || '').startsWith('/admin'))
let unreadPrimed = false

/** Чат на экране и вкладка активна — бейдж не нужен. */
function chatIsActivelyViewed() {
  return open.value && document.visibilityState === 'visible'
}

function syncAttention(count) {
  if (count <= 0 || chatIsActivelyViewed()) {
    clearSupportNotify()
    return
  }
  setSupportAttention(count)
}

const subtitle = computed(() =>
  isLoggedIn.value
    ? 'Ответим в течение нескольких минут'
    : 'Пишите без входа — ответим за пару минут',
)

function clearChatDeepLink() {
  const query = { ...route.query }
  let changed = false
  if (query.chat != null) {
    delete query.chat
    changed = true
  }
  const hash = route.hash === '#help-chat' || route.hash === '#chat' ? '' : route.hash
  if (hash !== route.hash) changed = true
  if (changed) router.replace({ path: route.path, query, hash })
}

watch(
  () => route.query.chat,
  (value) => {
    if (value === '1' || value === 'true') {
      openChat()
      clearChatDeepLink()
    }
  },
  { immediate: true },
)

watch(
  () => route.hash,
  (hash) => {
    if (hash === '#help-chat' || hash === '#chat') {
      openChat()
      clearChatDeepLink()
    }
  },
  { immediate: true },
)

watch(open, (value) => {
  if (value) {
    if (document.visibilityState === 'visible') clearSupportNotify()
    refreshUnread()
    return
  }
  syncAttention(unread.value)
})

watch(unread, (next) => {
  if (!unreadPrimed) {
    unreadPrimed = true
    syncAttention(next)
    return
  }
  syncAttention(next)
})

watch(isLoggedIn, () => {
  unreadPrimed = false
  startPolling()
})

function onVisibility() {
  syncAttention(unread.value)
}

onMounted(() => {
  startPolling()
  document.addEventListener('visibilitychange', onVisibility)
})

onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', onVisibility)
  clearSupportNotify()
  stopPolling()
})
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
.fab.alert {
  animation: fab-pulse 1.6s ease-in-out infinite;
}
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
  animation: badge-pop 0.35s ease;
}
@keyframes fab-pulse {
  0%, 100% { box-shadow: 0 16px 36px rgba(28, 25, 21, 0.22), 0 0 0 0 rgba(141, 43, 43, 0.35); }
  50% { box-shadow: 0 16px 36px rgba(28, 25, 21, 0.22), 0 0 0 10px rgba(141, 43, 43, 0); }
}
@keyframes badge-pop {
  from { transform: scale(0.6); opacity: 0.4; }
  to { transform: scale(1); opacity: 1; }
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
