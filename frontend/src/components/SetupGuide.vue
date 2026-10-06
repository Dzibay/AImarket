<template>
  <section class="card guide">
    <div class="guide-head">
      <div>
        <h2 class="card-title">Подключение к приложению</h2>
        <p class="muted small">
          Выберите программу и систему, скопируйте команду и вставьте её — всё настроится само.
        </p>
      </div>
    </div>

    <div class="pick">
      <span class="pick-label">1. Программа</span>
      <div class="chips">
        <button
          v-for="item in APPS"
          :key="item.id"
          type="button"
          class="chip"
          :class="{ on: app === item.id }"
          @click="selectApp(item.id)"
        >{{ item.title }}</button>
      </div>
    </div>

    <template v-if="app && app !== 'other'">
      <div class="pick">
        <span class="pick-label">2. Система</span>
        <div class="chips">
          <button
            v-for="item in systems"
            :key="item.id"
            type="button"
            class="chip"
            :class="{ on: os === item.id }"
            @click="os = item.id"
          >{{ item.title }}</button>
        </div>
      </div>

      <div v-if="os" class="steps-wrap">
        <div class="steps-head">
          <h3>{{ current.title }} — {{ osTitle }}</h3>
        </div>

        <p class="note">{{ intro }}</p>

        <template v-if="secret">
          <ol class="steps">
            <li v-for="(step, index) in steps" :key="index" v-html="step" />
          </ol>

          <div class="command">
            <code v-if="command">{{ command }}</code>
            <span v-else-if="commandError" class="muted small">
              {{ commandError }}<br>Установите через архив — раздел «Без командной строки» ниже.
            </span>
            <span v-else class="muted small">Готовим команду…</span>
          </div>
          <div class="guide-actions">
            <button type="button" class="btn" :disabled="!command" @click="copyCommand">
              {{ copied === 'command' ? 'Команда скопирована' : 'Скопировать команду' }}
            </button>
            <span class="muted small">Действует 15 минут. В ней ваш ключ — не пересылайте её.</span>
          </div>
          <p v-if="closeHint" class="muted small hint">{{ closeHint }}</p>
        </template>
        <p v-else class="muted small">
          Сначала пополните баланс — после первой оплаты выпустится ключ, и здесь появится команда для установки.
        </p>

        <details v-if="secret" class="network" :open="Boolean(commandError)">
          <summary>Без командной строки</summary>
          <ol class="steps">
            <li v-for="(step, index) in archiveSteps" :key="index" v-html="step" />
          </ol>
          <div class="guide-actions">
            <button type="button" class="btn quiet" @click="copyKey">
              {{ copiedKey ? 'Ключ скопирован' : 'Скопировать мой ключ' }}
            </button>
            <a class="btn quiet" :href="downloadUrl" download>Скачать установщик</a>
          </div>
        </details>

        <details v-if="canCommand" class="network">
          <summary>Если ответы обрываются</summary>
          <p>
            Ошибки <code>ECONNRESET</code>, таймауты и обрыв ответа обычно из-за сети.
            Настройте программу заново через запасной адрес — команда запускается так же, как первая.
          </p>
          <div class="guide-actions spaced">
            <button type="button" class="btn quiet" @click="loadExtra('setup-reserve')">Команда с запасным адресом</button>
          </div>
          <template v-if="extra.action === 'setup-reserve'">
            <div v-if="extra.command || extra.error" class="command">
              <code v-if="extra.command">{{ extra.command }}</code>
              <span v-else class="muted small">{{ extra.error }}</span>
            </div>
            <div v-if="extra.command" class="guide-actions">
              <button type="button" class="btn quiet" @click="copyValue(extra.command, 'extra')">
                {{ copied === 'extra' ? 'Скопировано' : 'Скопировать' }}
              </button>
            </div>
          </template>
          <p class="muted small">Не помогло — попробуйте другой VPN или выключите его.</p>
        </details>

        <details v-if="canCommand && current.restore" class="network">
          <summary>Как отключить aimarket</summary>
          <p>Эта команда вернёт настройки {{ current.title }}, которые были до установки.</p>
          <div class="guide-actions spaced">
            <button type="button" class="btn quiet" @click="loadExtra('restore')">Команда для отключения</button>
          </div>
          <template v-if="extra.action === 'restore'">
            <div v-if="extra.command || extra.error" class="command">
              <code v-if="extra.command">{{ extra.command }}</code>
              <span v-else class="muted small">{{ extra.error }}</span>
            </div>
            <div v-if="extra.command" class="guide-actions">
              <button type="button" class="btn quiet" @click="copyValue(extra.command, 'extra')">
                {{ copied === 'extra' ? 'Скопировано' : 'Скопировать' }}
              </button>
            </div>
          </template>
        </details>
      </div>
    </template>

    <div v-else-if="app === 'other'" class="steps-wrap">
      <h3>Другое приложение</h3>
      <p class="muted small">
        В настройках программы найдите «OpenAI-compatible», «Custom provider» или «Custom endpoint» и заполните три поля.
      </p>
      <dl class="kv">
        <dt>Адрес (Base URL)</dt>
        <dd>
          <code>{{ baseUrl }}</code>
          <button type="button" class="mini" @click="copyValue(baseUrl, 'base')">{{ copied === 'base' ? '✓' : 'копировать' }}</button>
        </dd>
        <dt>Ключ (API key)</dt>
        <dd>
          <template v-if="secret">
            ваш ключ
            <button type="button" class="mini" @click="copyKey">{{ copiedKey ? '✓' : 'копировать' }}</button>
          </template>
          <span v-else class="muted">появится после первого пополнения</span>
        </dd>
        <dt>Модель</dt>
        <dd>
          <code>{{ DEFAULT_MODEL }}</code>
          <button type="button" class="mini" @click="copyValue(DEFAULT_MODEL, 'model')">{{ copied === 'model' ? '✓' : 'копировать' }}</button>
          <span class="muted small"> — или любая другая из каталога</span>
        </dd>
      </dl>
      <details class="network">
        <summary>Если не подходит</summary>
        <dl class="kv compact">
          <dt>Поле просит полный адрес</dt>
          <dd><code>{{ chatUrl }}</code></dd>
          <dt>Модели Claude (Anthropic API)</dt>
          <dd><code>{{ anthropicUrl }}</code></dd>
          <dt>Ответы обрываются — запасной адрес</dt>
          <dd><code>{{ RESERVE_OPENAI }}</code>, для Claude — <code>{{ RESERVE_CLAUDE }}</code></dd>
        </dl>
      </details>
    </div>
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { errorText, webApi } from '../api/web'
import { copyText } from '../utils/format'

const props = defineProps({
  secret: { type: String, default: '' },
  baseUrl: { type: String, default: 'https://router.cheap/v1' },
})

const DEFAULT_MODEL = 'gpt-6-astra'
const RESERVE_OPENAI = 'https://direct.router-cheap.com/v1'
const RESERVE_CLAUDE = 'https://direct.router-cheap.com'

// Совпадает со списком в боте (bot/app/guide.py) и в сборщике installer/build.py.
const APPS = [
  { id: 'codex', title: 'Codex', file: 'codex', linux: true, restore: true },
  { id: 'ccode', title: 'Claude Code', file: 'claude-code', linux: true, restore: true },
  { id: 'cdesk', title: 'Claude Desktop', file: 'claude-desktop', linux: false, restore: true },
  { id: 'ocode', title: 'OpenCode', file: 'opencode', linux: true, restore: false },
  { id: 'hermes', title: 'Hermes', file: 'hermes', linux: true, restore: true },
  { id: 'grok', title: 'Grok Build', file: 'grok-build', linux: true, restore: true },
  { id: 'cursor', title: 'Cursor', file: 'cursor', linux: true, restore: true },
  { id: 'other', title: 'Другое приложение', file: '', linux: false, restore: false },
]
const OS = [
  { id: 'win', title: 'Windows', folder: 'windows' },
  { id: 'mac', title: 'macOS', folder: 'macos' },
  { id: 'lin', title: 'Linux', folder: 'linux' },
]
// Сервер держит команду 15 минут; берём новую чуть раньше.
const COMMAND_TTL_MS = 14 * 60 * 1000

const app = ref('')
const os = ref(guessOs())
const copiedKey = ref(false)
const copied = ref('')
const command = ref('')
const commandError = ref('')
const extra = reactive({ action: '', command: '', error: '' })
let commandAt = 0
let commandRequest = 0

const current = computed(() => APPS.find((item) => item.id === app.value) || null)
const systems = computed(() => (current.value?.linux ? OS : OS.slice(0, 2)))
const osTitle = computed(() => OS.find((item) => item.id === os.value)?.title || '')

const normalizedBase = computed(() => (props.baseUrl || 'https://router.cheap/v1').replace(/\/+$/, ''))
const chatUrl = computed(() => `${normalizedBase.value}/chat/completions`)
const anthropicUrl = computed(() => normalizedBase.value.replace(/\/v1$/, ''))

const folder = computed(() => OS.find((item) => item.id === os.value)?.folder || '')
const canCommand = computed(() => Boolean(props.secret && current.value?.file && folder.value))

const fileName = computed(() => {
  if (!current.value || !os.value) return ''
  if (os.value === 'lin') return `setup-aimarket-${current.value.file}.sh`
  return `aimarket-${current.value.file}-${folder.value}.zip`
})
const downloadUrl = computed(() => (fileName.value ? `/downloads/setup/${fileName.value}` : '#'))

const NOTES = {
  cursor: 'Чаты и настройки Cursor сохранятся. Подключаются модели GPT и Grok — Claude в Cursor так не работает.',
  cdesk: 'Аккаунт и чаты Claude Desktop не трогаются, перед настройкой сохраняется их копия.',
}
const CLOSE_HINTS = {
  cursor: 'Cursor можно не закрывать — установщик предложит это сам. Только не запускайте команду в терминале внутри Cursor.',
  cdesk: 'Claude Desktop можно не закрывать — установщик предложит это сам.',
}

const intro = computed(() => [`${current.value?.title} должен быть уже установлен.`, NOTES[app.value]].filter(Boolean).join(' '))
const closeHint = computed(() => CLOSE_HINTS[app.value] || '')

const terminalStep = computed(() => {
  if (os.value === 'win') return 'Нажмите <b>Win + R</b>, вставьте команду (<b>Ctrl + V</b>) и нажмите <b>Enter</b>.'
  if (os.value === 'mac') {
    return 'Откройте <b>Терминал</b> (<b>⌘ + Пробел</b>, наберите «Терминал»), вставьте команду (<b>⌘ + V</b>) и нажмите <b>Enter</b>.'
  }
  return 'Откройте терминал, вставьте команду (<b>Ctrl + Shift + V</b>) и нажмите <b>Enter</b>.'
})

const steps = computed(() => {
  if (!current.value || !os.value) return []
  return [
    'Нажмите «Скопировать команду» под этим списком.',
    terminalStep.value,
    `Дождитесь надписи «Готово» и перезапустите ${current.value.title}. Списание за пробный запрос появится в истории операций.`,
  ]
})

const archiveSteps = computed(() => {
  if (!current.value || !os.value) return []
  const run = os.value === 'lin'
    ? `Запустите в терминале <code>bash ${fileName.value}</code> из папки с файлом.`
    : `Распакуйте архив и откройте файл <code>${os.value === 'win' ? 'start.cmd' : 'start.command'}</code>.`
  const list = ['Нажмите «Скопировать мой ключ».', 'Нажмите «Скачать установщик».', run]
  if (os.value === 'mac') list.push('Если macOS не открывает файл: правый клик по нему → «Открыть» → «Открыть».')
  list.push(`Установщик покажет найденный ключ — нажмите <b>Enter</b>. Потом перезапустите ${current.value.title}.`)
  return list
})

watch([app, os, () => props.secret], () => {
  extra.action = ''
  extra.command = ''
  extra.error = ''
  loadCommand()
}, { immediate: true })

async function fetchCommand(action) {
  const result = await webApi.installCommand(current.value.file, folder.value, action)
  return result.command
}

async function loadCommand() {
  command.value = ''
  commandError.value = ''
  if (!canCommand.value) return
  const request = ++commandRequest
  try {
    const value = await fetchCommand('setup')
    if (request !== commandRequest) return
    command.value = value
    commandAt = Date.now()
  } catch (error) {
    if (request === commandRequest) commandError.value = errorText(error)
  }
}

async function copyCommand() {
  if (Date.now() - commandAt > COMMAND_TTL_MS) await loadCommand()
  if (command.value) await copyValue(command.value, 'command')
}

async function loadExtra(action) {
  extra.action = action
  extra.command = ''
  extra.error = ''
  try {
    extra.command = await fetchCommand(action)
  } catch (error) {
    extra.error = errorText(error)
  }
}

function selectApp(id) {
  app.value = id
  const item = APPS.find((entry) => entry.id === id)
  if (item && !item.linux && os.value === 'lin') os.value = 'win'
}

function guessOs() {
  const ua = (navigator.userAgent || '').toLowerCase()
  if (ua.includes('mac os') || ua.includes('macintosh')) return 'mac'
  if (ua.includes('linux') && !ua.includes('android')) return 'lin'
  return 'win'
}

async function copyKey() {
  try {
    await copyText(props.secret)
    copiedKey.value = true
    setTimeout(() => { copiedKey.value = false }, 1500)
  } catch {
    /* ignore */
  }
}

async function copyValue(value, id) {
  try {
    await copyText(value)
    copied.value = id
    setTimeout(() => { copied.value = '' }, 1500)
  } catch {
    /* ignore */
  }
}
</script>

<style scoped>
.guide { padding: 24px; }
.guide-head { margin-bottom: 16px; }
.card-title { margin: 0 0 6px; font-size: 1.15rem; letter-spacing: -0.03em; }
.guide-head p { margin: 0; }

.pick { margin-bottom: 14px; }
.pick-label {
  display: block;
  margin-bottom: 8px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip {
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  padding: 8px 16px;
  background: #fff;
  color: var(--text);
  font: inherit;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}
.chip:hover { background: var(--surface-soft); }
.chip.on { background: var(--accent); color: var(--bg); border-color: var(--accent); }

.steps-wrap {
  margin-top: 8px;
  padding: 18px 20px;
  border-radius: var(--radius-sm);
  background: var(--surface-soft);
  border: 1px solid var(--border-strong);
}
.steps-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.steps-wrap h3 { margin: 0; font-size: 1.05rem; letter-spacing: -0.02em; }
.steps { margin: 10px 0 16px; padding-left: 22px; font-size: 15px; }
.steps li { margin-bottom: 8px; }
.steps :deep(code), .kv code, .note code, .network code {
  font-size: 13px;
  background: #fff;
  border: 1px solid var(--border);
  padding: 1px 6px;
  border-radius: 6px;
  overflow-wrap: anywhere;
}
.guide-actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
.guide-actions.spaced { margin: 10px 0; }
.command {
  margin: 0 0 12px;
  padding: 12px 14px;
  border-radius: 8px;
  border: 1px solid var(--border-strong);
  background: #fff;
}
.command code {
  display: block;
  padding: 0;
  border: 0;
  background: none;
  font-size: 13px;
  line-height: 1.5;
  overflow-wrap: anywhere;
  user-select: all;
}
.network .steps { margin-top: 10px; }
.hint { margin: 10px 0 0; }

.note {
  margin: 10px 0;
  padding: 10px 14px;
  border-left: 3px solid var(--border-strong);
  background: #fff;
  border-radius: 0 8px 8px 0;
  font-size: 14px;
  color: var(--muted-2);
}
.kv { display: grid; grid-template-columns: max-content 1fr; gap: 8px 18px; margin: 12px 0; font-size: 15px; }
.kv dt { color: var(--muted); font-size: 13px; font-weight: 600; padding-top: 2px; }
.kv dd { margin: 0; overflow-wrap: anywhere; }
.kv.compact { font-size: 14px; }
.mini {
  margin-left: 6px;
  border: 0;
  background: none;
  padding: 0;
  color: var(--muted);
  font: inherit;
  font-size: 12px;
  text-decoration: underline;
  cursor: pointer;
}

.network { margin-top: 16px; font-size: 14px; }
.network summary { cursor: pointer; font-weight: 600; }
.network p { margin: 10px 0 0; }

@media (max-width: 520px) {
  .kv { grid-template-columns: 1fr; gap: 4px; }
  .kv dt { margin-top: 8px; }
}
</style>
