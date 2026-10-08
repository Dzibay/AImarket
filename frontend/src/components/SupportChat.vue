<template>
  <div class="support-chat" :class="{ compact }">
    <div ref="scroller" class="thread" role="log" aria-live="polite">
      <p v-if="loading && !messages.length" class="muted small center">Загружаем переписку…</p>
      <div v-else-if="!messages.length" class="empty">
        <p class="muted">Напишите вопрос — ответим в этом чате, обычно в течение дня.</p>
        <p class="muted small">Укажите почту оплаты и суть проблемы: ключ, платёж, подключение.</p>
      </div>
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
        :disabled="sending || blocked"
        :placeholder="blocked ? 'Доступ заблокирован' : 'Ваше сообщение…'"
        @keydown.enter.exact.prevent="send"
      />
      <div class="composer-foot">
        <span v-if="error" class="error-text">{{ error }}</span>
        <span v-else class="muted small">Enter — отправить · Shift+Enter — новая строка</span>
        <button type="submit" class="btn sm" :disabled="sending || blocked || !draft.trim()">
          {{ sending ? 'Отправка…' : 'Отправить' }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { errorText, webApi } from '../api/web'
import { useSupportUnread } from '../composables/useSupportUnread'
import { dateTime } from '../utils/format'

defineProps({
  compact: { type: Boolean, default: false },
  blocked: { type: Boolean, default: false },
})

const messages = ref([])
const draft = ref('')
const loading = ref(false)
const sending = ref(false)
const error = ref('')
const scroller = ref(null)
const input = ref(null)
let pollTimer = null
const { clearUnread, refreshUnread } = useSupportUnread()

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await webApi.supportMessages()
    messages.value = data.messages || []
    clearUnread()
    await scrollBottom()
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

async function send() {
  const body = draft.value.trim()
  if (!body || sending.value) return
  sending.value = true
  error.value = ''
  try {
    const data = await webApi.supportSend(body)
    messages.value = [...messages.value, data.message]
    draft.value = ''
    await scrollBottom()
    input.value?.focus()
  } catch (err) {
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

function startPoll() {
  stopPoll()
  pollTimer = setInterval(async () => {
    if (document.visibilityState !== 'visible' || sending.value) return
    try {
      const data = await webApi.supportMessages()
      const next = data.messages || []
      const grew = next.length !== messages.value.length
        || (next.at(-1)?.id !== messages.value.at(-1)?.id)
      messages.value = next
      clearUnread()
      if (grew) await scrollBottom()
    } catch {
      /* тихо — сеть могла моргнуть */
    }
  }, 12000)
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

watch(messages, () => scrollBottom())

onMounted(async () => {
  await load()
  startPoll()
  input.value?.focus()
})

onBeforeUnmount(() => {
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
