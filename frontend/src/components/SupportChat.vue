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
        <p v-if="item.body" class="text">{{ item.body }}</p>
        <div v-if="item.attachments?.length" class="shots">
          <SupportShot
            v-for="file in item.attachments"
            :key="file.id"
            :src="shotSrc(file.id)"
            :headers="shotHeaders"
            :alt="file.name || 'Скриншот'"
          />
        </div>
        <time class="when">{{ dateTime(item.created_at) }}</time>
      </div>
    </div>

    <form class="composer" @submit.prevent="send">
      <label v-if="emailNotifyAvailable" class="mail-pref">
        <input
          v-model="emailNotifyEnabled"
          type="checkbox"
          :disabled="emailNotifyBusy"
          @change="saveEmailNotify"
        >
        <span>Письма о ответах на почту</span>
      </label>
      <textarea
        ref="input"
        v-model="draft"
        class="input area"
        rows="2"
        maxlength="4000"
        :disabled="sending || blocked || !ready"
        :placeholder="blocked ? 'Доступ заблокирован' : 'Ваше сообщение…'"
        @keydown.enter.exact.prevent="send"
        @paste="onPaste"
      />
      <div v-if="pending.length" class="pending">
        <span v-for="item in pending" :key="item.id" class="pending-item">
          <img :src="item.url" alt="">
          <button type="button" class="pending-remove" aria-label="Убрать фото" @click="removePending(item.id)">×</button>
        </span>
      </div>
      <div class="composer-foot">
        <span v-if="error" class="error-text">{{ error }}</span>
        <span v-else class="muted small">Enter — отправить · можно вставить скриншот</span>
        <div class="composer-actions">
          <label class="attach" :class="{ off: sending || blocked || !ready || pending.length >= 4 }">
            Фото
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              multiple
              :disabled="sending || blocked || !ready || pending.length >= 4"
              @change="onPick"
            >
          </label>
          <button type="submit" class="btn sm" :disabled="sending || blocked || !ready || (!draft.trim() && !pending.length)">
            {{ sending ? 'Отправка…' : 'Отправить' }}
          </button>
        </div>
      </div>
    </form>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { errorText, webApi } from '../api/web'
import SupportShot from './SupportShot.vue'
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
const pending = ref([])
const loading = ref(false)
const sending = ref(false)
const ready = ref(false)
const error = ref('')
const emailNotifyAvailable = ref(false)
const emailNotifyEnabled = ref(true)
const emailNotifyBusy = ref(false)
const scroller = ref(null)
const input = ref(null)
let pollTimer = null
let pullSeq = 0
let pulling = false
let guestToken = ''
const { clearUnread, refreshUnread } = useSupportUnread()

const isGuest = computed(() => !isLoggedIn.value)
const shotHeaders = computed(() => {
  const session = getSession()
  return session ? { Authorization: `Bearer ${session}` } : {}
})

function shotSrc(id) {
  if (getSession()) return `/api/web/support/files/${id}`
  const token = guestToken || getGuestSupportToken()
  return `/api/web/support/guest/files/${id}?token=${encodeURIComponent(token)}`
}

function addPending(fileList) {
  const next = [...pending.value]
  for (const file of fileList) {
    if (next.length >= 4) {
      error.value = 'Не больше 4 изображений за раз.'
      break
    }
    if (!file || !String(file.type || '').startsWith('image/')) {
      error.value = 'Нужен файл JPEG, PNG, WEBP или GIF.'
      continue
    }
    if (file.size > 8 * 1024 * 1024) {
      error.value = 'Файл больше 8 МБ.'
      continue
    }
    next.push({
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      file,
      url: URL.createObjectURL(file),
    })
  }
  pending.value = next
}

function removePending(id) {
  const item = pending.value.find((row) => row.id === id)
  if (item?.url) URL.revokeObjectURL(item.url)
  pending.value = pending.value.filter((row) => row.id !== id)
}

function clearPending() {
  for (const item of pending.value) {
    if (item.url) URL.revokeObjectURL(item.url)
  }
  pending.value = []
}

function onPick(event) {
  addPending(event.target.files || [])
  event.target.value = ''
}

function onPaste(event) {
  const items = event.clipboardData?.items || []
  const files = []
  for (const item of items) {
    if (item.type && item.type.startsWith('image/')) {
      const file = item.getAsFile()
      if (file) files.push(file)
    }
  }
  if (!files.length) return
  event.preventDefault()
  addPending(files)
}

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

function applyEmailNotify(data) {
  if (emailNotifyBusy.value) return
  const prefs = data?.email_notify
  if (!prefs || isGuest.value) {
    emailNotifyAvailable.value = false
    return
  }
  emailNotifyAvailable.value = !!prefs.available
  emailNotifyEnabled.value = prefs.enabled !== false
}

async function fetchMessages(markSeen = true) {
  if (getSession()) return webApi.supportMessages(markSeen)
  return webApi.supportGuestMessages(guestToken || getGuestSupportToken(), markSeen)
}

async function saveEmailNotify() {
  if (!getSession() || emailNotifyBusy.value) return
  emailNotifyBusy.value = true
  const enabled = emailNotifyEnabled.value
  try {
    const data = await webApi.supportEmailNotify(enabled)
    applyEmailNotify(data)
  } catch (err) {
    emailNotifyEnabled.value = !enabled
    error.value = errorText(err)
  } finally {
    emailNotifyBusy.value = false
  }
}

async function postMessage(body, files = []) {
  if (files.length) {
    const form = new FormData()
    form.append('body', body)
    for (const file of files) form.append('files', file, file.name || 'image.png')
    if (getSession()) return webApi.supportSendMedia(form)
    form.append('token', guestToken || getGuestSupportToken())
    return webApi.supportGuestSendMedia(form)
  }
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
    applyEmailNotify(data)
    clearUnread()
    await scrollBottom()
  } catch (err) {
    if (!getSession() && (err?.code === 'guest-token' || err?.status === 404)) {
      try {
        guestToken = await resetGuestSupportToken()
        const data = await fetchMessages()
        messages.value = data.messages || []
        applyEmailNotify(data)
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
  const files = pending.value.map((item) => item.file)
  if ((!body && !files.length) || sending.value || !ready.value) return
  sending.value = true
  error.value = ''
  try {
    const data = await postMessage(body, files)
    messages.value = [...messages.value, data.message]
    draft.value = ''
    clearPending()
    await scrollBottom()
    input.value?.focus()
  } catch (err) {
    if (!getSession() && (err?.code === 'guest-token' || err?.status === 404)) {
      try {
        guestToken = await resetGuestSupportToken()
        const data = await postMessage(body, files)
        messages.value = [...messages.value, data.message]
        draft.value = ''
        clearPending()
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

function isNearBottom(threshold = 96) {
  const el = scroller.value
  if (!el) return true
  return el.scrollHeight - el.scrollTop - el.clientHeight <= threshold
}

async function scrollBottom({ force = true } = {}) {
  await nextTick()
  const el = scroller.value
  if (!el) return
  if (!force && !isNearBottom()) return
  el.scrollTop = el.scrollHeight
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
    applyEmailNotify(data)
    // Не перезаписываем массив без изменений — иначе Vue дергает DOM и «телепортирует» скролл.
    if (grew) {
      const stickToBottom = isNearBottom()
      messages.value = next
      if (markRead && stickToBottom) await scrollBottom({ force: true })
    }
    if (markRead) {
      clearUnread()
      clearSupportNotify()
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
  clearPending()
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
.mail-pref {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 12px;
  color: var(--muted);
  cursor: pointer;
  user-select: none;
}
.mail-pref input {
  width: 14px;
  height: 14px;
  margin: 0;
  accent-color: var(--accent);
  cursor: pointer;
}
.area {
  min-height: 64px;
  max-height: 140px;
  resize: vertical;
  line-height: 1.45;
}
.shots {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.pending {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.pending-item {
  position: relative;
  width: 64px;
  height: 64px;
}
.pending-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid var(--border);
}
.pending-remove {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 18px;
  height: 18px;
  border: 0;
  border-radius: 50%;
  background: #1c1917;
  color: #fff;
  line-height: 18px;
  padding: 0;
  cursor: pointer;
}
.composer-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.composer-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}
.attach {
  position: relative;
  display: inline-flex;
  align-items: center;
  height: 32px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 13px;
  cursor: pointer;
  background: #fff;
}
.attach.off {
  opacity: 0.5;
  pointer-events: none;
}
.attach input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}
</style>
