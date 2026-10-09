<template>
  <div class="support-chat" :class="{ compact }">
    <div ref="scroller" class="thread" role="log" aria-live="polite">
      <p v-if="loading && !messages.length" class="muted small center">Загружаем переписку…</p>
      <template v-else-if="!messages.length">
        <div v-if="isGuest" class="bubble theirs welcome">
          <p class="text">{{ emptyTitle }}</p>
          <p class="text hint">{{ emptyHint }}</p>
        </div>
        <div v-else class="empty">
          <p class="muted">{{ emptyTitle }}</p>
          <p class="muted small">{{ emptyHint }}</p>
        </div>
      </template>
      <div
        v-for="item in messages"
        :key="item.id"
        class="bubble"
        :class="item.author === 'user' ? 'mine' : 'theirs'"
      >
        <p class="text">{{ item.body }}</p>
        <time class="when">{{ dateTime(item.created_at) }}</time>
      </div>
    </div>

    <form class="composer" @submit.prevent="send">
      <textarea
        ref="input"
        v-model="draft"
        class="input area"
        rows="2"
        maxlength="4000"
        :disabled="sending || blocked || !ready"
        :placeholder="blocked ? 'Доступ заблокирован' : 'Ваше сообщение…'"
        @keydown.enter.exact.prevent="send"
      />
      <div class="composer-foot">
        <span v-if="error" class="error-text">{{ error }}</span>
        <span v-else class="muted small">Enter — отправить · Shift+Enter — новая строка</span>
        <button type="submit" class="btn sm" :disabled="sending || blocked || !ready || !draft.trim()">
          {{ sending ? 'Отправка…' : 'Отправить' }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { errorText, webApi } from '../api/web'
import {
  claimGuestSupportIfNeeded,
  ensureGuestSupportToken,
  getGuestSupportToken,
  resetGuestSupportToken,
} from '../composables/useGuestSupport'
import { getSession, useSession } from '../composables/useSession'
import { clearSupportNotify } from '../composables/useSupportNotify'
import { useSupportUnread } from '../composables/useSupportUnread'
import { dateTime } from '../utils/format'

defineProps({
  compact: { type: Boolean, default: false },
  blocked: { type: Boolean, default: false },
})

const { isLoggedIn } = useSession()
const messages = ref([])
const draft = ref('')
const loading = ref(false)
const sending = ref(false)
const ready = ref(false)
const error = ref('')
const scroller = ref(null)
const input = ref(null)
let pollTimer = null
let pullSeq = 0
let pulling = false
let guestToken = ''
const { clearUnread, refreshUnread } = useSupportUnread()

const isGuest = computed(() => !isLoggedIn.value)

const emptyTitle = computed(() =>
  isGuest.value
    ? 'Здравствуйте! Пишите без авторизации — ответим в течение пары минут.'
    : 'Напишите вопрос — ответим в этом чате.',
)
const emptyHint = computed(() =>
  isGuest.value
    ? 'Спросите про тарифы, оплату или подключение приложений.'
    : 'Кратко опишите проблему: ключ, платёж или подключение приложения.',
)

async function ensureAccess() {
  if (getSession()) {
    await claimGuestSupportIfNeeded()
    guestToken = ''
    ready.value = true
    return
  }
  guestToken = await ensureGuestSupportToken()
  ready.value = Boolean(guestToken)
}

async function fetchMessages(markSeen = true) {
  if (getSession()) return webApi.supportMessages(markSeen)
  return webApi.supportGuestMessages(guestToken || getGuestSupportToken(), markSeen)
}

async function postMessage(body) {
  if (getSession()) return webApi.supportSend(body)
  return webApi.supportGuestSend(guestToken || getGuestSupportToken(), body)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    await ensureAccess()
    const data = await fetchMessages()
    messages.value = data.messages || []
    clearUnread()
    await scrollBottom()
  } catch (err) {
    if (!getSession() && (err?.code === 'guest-token' || err?.status === 404)) {
      try {
        guestToken = await resetGuestSupportToken()
        const data = await fetchMessages()
        messages.value = data.messages || []
        clearUnread()
        await scrollBottom()
        return
      } catch (retryErr) {
        error.value = errorText(retryErr)
        return
      }
    }
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

async function send() {
  const body = draft.value.trim()
  if (!body || sending.value || !ready.value) return
  sending.value = true
  error.value = ''
  try {
    const data = await postMessage(body)
    messages.value = [...messages.value, data.message]
    draft.value = ''
    await scrollBottom()
    input.value?.focus()
  } catch (err) {
    if (!getSession() && (err?.code === 'guest-token' || err?.status === 404)) {
      try {
        guestToken = await resetGuestSupportToken()
        const data = await postMessage(body)
        messages.value = [...messages.value, data.message]
        draft.value = ''
        await scrollBottom()
        return
      } catch (retryErr) {
        error.value = errorText(retryErr)
        return
      }
    }
    error.value = errorText(err)
  } finally {
    sending.value = false
  }
}

async function scrollBottom() {
  await nextTick()
  const el = scroller.value
  if (el) el.scrollTop = el.scrollHeight
}

async function pullMessages({ markRead = false } = {}) {
  if (sending.value || !ready.value || pulling) return
  const seq = ++pullSeq
  pulling = true
  try {
    const data = await fetchMessages(markRead)
    if (seq !== pullSeq) return
    const next = data.messages || []
    const lastId = messages.value.at(-1)?.id
    const nextLastId = next.at(-1)?.id
    const grew = next.length !== messages.value.length || nextLastId !== lastId
    messages.value = next
    if (markRead) {
      clearUnread()
      clearSupportNotify()
      if (grew) await scrollBottom()
    } else if (grew) {
      // Вкладка в фоне — не помечаем прочитанным, чтобы сработали бейдж и unread.
      await refreshUnread()
    }
  } catch {
    /* тихо */
  } finally {
    if (seq === pullSeq) pulling = false
  }
}

function startPoll() {
  stopPoll()
  const tick = () => {
    const viewing = document.visibilityState === 'visible'
    pullMessages({ markRead: viewing })
  }
  // Сразу после открытия и дальше чаще — иначе ответ «висит», пока чат открыт.
  tick()
  pollTimer = setInterval(tick, 4000)
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  pullSeq += 1
  pulling = false
}

async function onVisibility() {
  if (!ready.value) return
  if (document.visibilityState === 'visible') {
    await pullMessages({ markRead: true })
  }
}

watch(messages, () => {
  if (document.visibilityState === 'visible') scrollBottom()
})

onMounted(async () => {
  await load()
  startPoll()
  document.addEventListener('visibilitychange', onVisibility)
  input.value?.focus()
})

onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', onVisibility)
  stopPoll()
  refreshUnread()
})

defineExpose({ load, refresh: load })
</script>

<style scoped>
.support-chat {
  display: flex;
  flex-direction: column;
  min-height: 420px;
  height: min(70vh, 640px);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow);
}
.support-chat.compact {
  min-height: 360px;
  height: 420px;
  box-shadow: none;
}
.thread {
  flex: 1;
  overflow-y: auto;
  padding: 18px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background:
    radial-gradient(ellipse 80% 50% at 10% 0%, rgba(255, 255, 255, 0.7), transparent 55%),
    var(--surface-soft);
}
.center { text-align: center; margin: auto; }
.empty {
  margin: auto;
  max-width: 320px;
  text-align: center;
  display: grid;
  gap: 6px;
}
.welcome { max-width: min(92%, 340px); }
.welcome .hint {
  margin-top: 6px;
  opacity: 0.72;
  font-size: 0.88rem;
}
.bubble {
  max-width: min(86%, 420px);
  padding: 10px 12px 8px;
  border-radius: 14px;
  display: grid;
  gap: 4px;
}
.bubble.mine {
  align-self: flex-end;
  background: var(--accent);
  color: var(--bg);
  border-bottom-right-radius: 4px;
}
.bubble.theirs {
  align-self: flex-start;
  background: #fff;
  border: 1px solid var(--border);
  border-bottom-left-radius: 4px;
}
.text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.95rem;
  line-height: 1.45;
}
.when {
  font-size: 11px;
  opacity: 0.65;
}
.bubble.mine .when { text-align: right; }
.composer {
  border-top: 1px solid var(--border);
  padding: 12px;
  background: #fff;
  display: grid;
  gap: 8px;
}
.area {
  min-height: 64px;
  max-height: 140px;
  resize: vertical;
  line-height: 1.45;
}
.composer-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
