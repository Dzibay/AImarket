<template>
  <section class="card guide">
    <div class="guide-head">
      <div class="guide-head-top">
        <h2 class="card-title">Подключение к приложению</h2>
        <div
          v-if="current && current.id !== 'other' && !current.manual"
          class="segmented os-switch"
          role="tablist"
          aria-label="Система"
        >
          <button
            v-for="item in systems"
            :key="item.id"
            type="button"
            role="tab"
            :class="{ on: os === item.id }"
            :aria-selected="os === item.id"
            @click="os = item.id"
          ><AppIcon :name="item.icon" :size="14" />{{ item.title }}</button>
        </div>
      </div>
      <p class="muted small guide-head-lead">
        Для Codex, Claude Code и других — одна команда. Для Cursor — короткая инструкция в настройках приложения.
      </p>
    </div>

    <div class="tabs" role="tablist" aria-label="Программа">
      <button
        v-for="item in APPS"
        :key="item.id"
        type="button"
        role="tab"
        :class="{ on: app === item.id }"
        :aria-selected="app === item.id"
        @click="selectApp(item.id)"
      >{{ item.title }}</button>
    </div>

    <Transition name="fade" mode="out-in">
      <div v-if="current?.manual" key="manual-cursor" class="panel">
        <p class="muted small manual-lead">
          Автоустановщик для Cursor отключён — так стабильнее. Пропишите ключ и адрес в <b>Settings → Models → OpenAI API</b>.
        </p>
        <div class="fields three">
          <CopyField label="Base URL (Override)" :value="normalizedBase" toast="Адрес скопирован" />
          <CopyField v-if="secret" label="API-ключ" :value="secret" masked toast="Ключ скопирован" />
          <div v-else class="copy-placeholder">
            <span class="copy-label">API-ключ</span>
            <span class="muted small">появится после первого пополнения</span>
          </div>
          <CopyField label="Модель по умолчанию" :value="DEFAULT_MODEL" toast="Модель скопирована" />
        </div>
        <template v-if="secret">
          <ol class="steps">
            <li v-for="(step, index) in cursorSteps" :key="index">
              <span class="step-dot">{{ index + 1 }}</span>
              <span v-html="step" />
            </li>
          </ol>
          <div class="guide-actions">
            <button type="button" class="btn sm" @click="copyKey"><AppIcon name="key" :size="16" />Скопировать ключ</button>
          </div>
          <p class="note">{{ cursorNote }}</p>
        </template>
        <div v-else class="notice">
          Сначала пополните баланс — после первой оплаты выпустится ключ, и здесь появятся шаги.
        </div>
        <div v-if="secret" class="extras">
          <details class="extra">
            <summary><AppIcon name="help" :size="16" /><span>DeepSeek, GLM и другие модели</span><AppIcon name="chevron" :size="16" class="chev" /></summary>
            <div class="extra-body">
              <p>
                Нажмите <b>Add model</b> в Settings → Models и введите id <b>точно</b> как в
                <router-link to="/prices">каталоге</router-link>, например <code>deepseek-v4-pro</code>.
                Переключатель <b>Use OpenAI API Key</b> должен быть включён.
              </p>
            </div>
          </details>
          <details class="extra">
            <summary><AppIcon name="refresh" :size="16" /><span>Как отключить aimarket</span><AppIcon name="chevron" :size="16" class="chev" /></summary>
            <div class="extra-body">
              <p>
                Выключите <b>Use OpenAI API Key</b> и <b>Override OpenAI Base URL</b>, удалите ключ из поля,
                перезапустите Cursor и выберите встроенные модели Cursor.
              </p>
            </div>
          </details>
          <details class="extra">
            <summary><AppIcon name="alert" :size="16" /><span>Если «Model name is not valid»</span><AppIcon name="chevron" :size="16" class="chev" /></summary>
            <div class="extra-body">
              <p>
                Обычно выключен <b>Use OpenAI API Key</b> или модель добавлена дважды: для
                <code>{{ DEFAULT_MODEL }}</code> и других GPT/Grok используйте встроенный пункт в списке Models,
                а не custom с тем же id.
              </p>
            </div>
          </details>
        </div>
      </div>

      <div v-else-if="current && current.id !== 'other'" :key="`${app}-${os}`" class="panel">
        <div class="fields">
          <CopyField label="Base URL" :value="normalizedBase" toast="Адрес скопирован" />
          <CopyField v-if="secret" label="API-ключ" :value="secret" masked toast="Ключ скопирован" />
          <div v-else class="copy-placeholder">
            <span class="copy-label">API-ключ</span>
            <span class="muted small">появится после первого пополнения</span>
          </div>
        </div>

        <template v-if="secret">
          <ol class="steps">
            <li v-for="(step, index) in steps" :key="index">
              <span class="step-dot">{{ index + 1 }}</span>
              <span v-html="step" />
            </li>
          </ol>

          <CodeBlock
            ref="mainBlock"
            :label="terminalLabel"
            :icon="os === 'win' ? 'windows' : 'terminal'"
            :code="command"
            :error="commandError"
          />
          <div class="guide-actions">
            <button type="button" class="btn sm" :disabled="!command" @click="copyCommand">
              <AppIcon name="copy" :size="16" />Скопировать команду
            </button>
            <span class="muted small">Действует 15 минут. В ней ваш ключ — не пересылайте её.</span>
          </div>
          <p class="note">{{ [intro, closeHint].filter(Boolean).join(' ') }}</p>
        </template>
        <div v-else class="notice">
          Сначала пополните баланс — после первой оплаты выпустится ключ, и здесь появится команда для установки.
        </div>

        <div v-if="secret" class="extras">
          <details class="extra" :open="Boolean(commandError)">
            <summary><AppIcon name="download" :size="16" /><span>Без командной строки — через установщик</span><AppIcon name="chevron" :size="16" class="chev" /></summary>
            <div class="extra-body">
              <ol class="steps compact">
                <li v-for="(step, index) in archiveSteps" :key="index">
                  <span class="step-dot">{{ index + 1 }}</span>
                  <span v-html="step" />
                </li>
              </ol>
              <div class="guide-actions">
                <button type="button" class="btn quiet sm" @click="copyKey"><AppIcon name="key" :size="16" />Скопировать мой ключ</button>
                <a class="btn quiet sm" :href="downloadUrl" download><AppIcon name="download" :size="16" />Скачать установщик</a>
              </div>
            </div>
          </details>

          <details class="extra">
            <summary><AppIcon name="alert" :size="16" /><span>Если ответы обрываются</span><AppIcon name="chevron" :size="16" class="chev" /></summary>
            <div class="extra-body">
              <p>
                Ошибки <code>ECONNRESET</code>, таймауты и обрыв ответа обычно из-за сети. Настройте программу
                заново через запасной адрес — команда запускается так же, как первая.
              </p>
              <button v-if="extra.action !== 'setup-reserve'" type="button" class="btn quiet sm" @click="loadExtra('setup-reserve')">
                Получить команду с запасным адресом
              </button>
              <CodeBlock
                v-else
                :label="terminalLabel + ' · запасной адрес'"
                :icon="os === 'win' ? 'windows' : 'terminal'"
                :code="extra.command"
                :error="extra.error"
              />
              <p class="muted small">Не помогло — попробуйте другой VPN или выключите его.</p>
            </div>
          </details>

          <details v-if="current.restore" class="extra">
            <summary><AppIcon name="refresh" :size="16" /><span>Как отключить aimarket</span><AppIcon name="chevron" :size="16" class="chev" /></summary>
            <div class="extra-body">
              <p>Команда вернёт настройки {{ current.title }}, которые были до установки.</p>
              <button v-if="extra.action !== 'restore'" type="button" class="btn quiet sm" @click="loadExtra('restore')">
                Получить команду для отключения
              </button>
              <CodeBlock
                v-else
                :label="terminalLabel + ' · отключение'"
                :icon="os === 'win' ? 'windows' : 'terminal'"
                :code="extra.command"
                :error="extra.error"
              />
            </div>
          </details>
        </div>
      </div>

      <div v-else key="other" class="panel">
        <p class="muted small other-lead">
          В настройках программы найдите «OpenAI-compatible», «Custom provider» или «Custom endpoint» и заполните три поля.
        </p>
        <div class="fields three">
          <CopyField label="Адрес (Base URL)" :value="normalizedBase" toast="Адрес скопирован" />
          <CopyField v-if="secret" label="Ключ (API key)" :value="secret" masked toast="Ключ скопирован" />
          <div v-else class="copy-placeholder">
            <span class="copy-label">Ключ (API key)</span>
            <span class="muted small">появится после первого пополнения</span>
          </div>
          <CopyField label="Модель" :value="DEFAULT_MODEL" toast="Модель скопирована" />
        </div>
        <p class="muted small">Вместо <code>{{ DEFAULT_MODEL }}</code> подойдёт любая модель из каталога.</p>
        <div class="extras">
          <details class="extra">
            <summary><AppIcon name="help" :size="16" /><span>Если не подходит</span><AppIcon name="chevron" :size="16" class="chev" /></summary>
            <div class="extra-body">
              <dl class="kv">
                <dt>Поле просит полный адрес</dt>
                <dd><code>{{ chatUrl }}</code></dd>
                <dt>Модели Claude (Anthropic API)</dt>
                <dd><code>{{ anthropicUrl }}</code></dd>
                <dt>Ответы обрываются — запасной адрес</dt>
                <dd><code>{{ RESERVE_OPENAI }}</code>, для Claude — <code>{{ RESERVE_CLAUDE }}</code></dd>
              </dl>
            </div>
          </details>
        </div>
      </div>
    </Transition>
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { errorText, webApi } from '../api/web'
import { copyWithToast } from '../composables/useToast'
import AppIcon from './ui/AppIcon.vue'
import CodeBlock from './ui/CodeBlock.vue'
import CopyField from './ui/CopyField.vue'

const props = defineProps({
  secret: { type: String, default: '' },
  baseUrl: { type: String, default: 'https://router.cheap/v1' },
})

const DEFAULT_MODEL = 'gpt-6-astra'
const RESERVE_OPENAI = 'https://direct.router-cheap.com/v1'
const RESERVE_CLAUDE = 'https://direct.router-cheap.com'

// Совпадает со списком в боте (bot/app/guide.py) и в сборщике installer/build.py.
const APPS = [
  { id: 'cursor', title: 'Cursor', file: '', linux: false, restore: false, manual: true },
  { id: 'ccode', title: 'Claude Code', file: 'claude-code', linux: true, restore: true },
  { id: 'codex', title: 'Codex', file: 'codex', linux: true, restore: true },
  { id: 'cdesk', title: 'Claude Desktop', file: 'claude-desktop', linux: false, restore: true },
  { id: 'ocode', title: 'OpenCode', file: 'opencode', linux: true, restore: false },
  { id: 'hermes', title: 'Hermes', file: 'hermes', linux: true, restore: true },
  { id: 'grok', title: 'Grok Build', file: 'grok-build', linux: true, restore: true },
  { id: 'other', title: 'Другое', file: '', linux: false, restore: false },
]
const OS = [
  { id: 'win', title: 'Windows', folder: 'windows', icon: 'windows' },
  { id: 'mac', title: 'macOS', folder: 'macos', icon: 'apple' },
  { id: 'lin', title: 'Linux', folder: 'linux', icon: 'linux' },
]
const NOTES = {
  cdesk: 'Аккаунт и чаты Claude Desktop не трогаются, перед настройкой сохраняется их копия.',
}
const CLOSE_HINTS = {
  cdesk: 'Claude Desktop можно не закрывать — установщик предложит это сам.',
}
const cursorSteps = [
  'Откройте <b>Cursor → Settings → Models</b> (Ctrl + ,).',
  'В блоке <b>OpenAI API Key</b> вставьте ключ и включите <b>Use OpenAI API Key</b> (должно быть «Secret saved»).',
  'Включите <b>Override OpenAI Base URL</b> и вставьте адрес из поля выше.',
  `Для <code>${DEFAULT_MODEL}</code> и других GPT/Grok: <b>не добавляйте</b> их как custom — включите встроенную модель в списке Models.`,
  'Новый чат → выберите модель → пробный запрос. Списание появится в истории операций.',
]
const cursorNote = 'Claude и Gemini через этот Base URL в Cursor не работают — только GPT, Grok и добавленные OpenAI-compatible модели.'
// Сервер держит команду 15 минут; берём новую чуть раньше.
const COMMAND_TTL_MS = 14 * 60 * 1000
const APP_STORAGE = 'aimarket-guide-app'

const app = ref(rememberedApp())
const os = ref(guessOs())
const command = ref('')
const commandError = ref('')
const extra = reactive({ action: '', command: '', error: '' })
const mainBlock = ref(null)
let commandAt = 0
let commandRequest = 0

const current = computed(() => APPS.find((item) => item.id === app.value) || APPS[0])
const systems = computed(() => (current.value?.linux ? OS : OS.slice(0, 2)))
const normalizedBase = computed(() => (props.baseUrl || 'https://router.cheap/v1').replace(/\/+$/, ''))
const chatUrl = computed(() => `${normalizedBase.value}/chat/completions`)
const anthropicUrl = computed(() => normalizedBase.value.replace(/\/v1$/, ''))
const folder = computed(() => OS.find((item) => item.id === os.value)?.folder || '')
const canCommand = computed(() => Boolean(props.secret && current.value?.file && folder.value && !current.value?.manual))

const fileName = computed(() => {
  if (!current.value?.file) return ''
  if (os.value === 'lin') return `setup-aimarket-${current.value.file}.sh`
  return `aimarket-${current.value.file}-${folder.value}.zip`
})
const downloadUrl = computed(() => (fileName.value ? `/downloads/setup/${fileName.value}` : '#'))

const intro = computed(() => [`${current.value.title} должен быть уже установлен.`, NOTES[app.value]].filter(Boolean).join(' '))
const closeHint = computed(() => CLOSE_HINTS[app.value] || '')

const terminalLabel = computed(() => {
  if (os.value === 'win') return 'Win + R'
  if (os.value === 'mac') return 'Терминал · zsh'
  return 'Терминал · bash'
})
const terminalStep = computed(() => {
  if (os.value === 'win') return 'Нажмите <b>Win + R</b>, вставьте команду (<b>Ctrl + V</b>) и нажмите <b>Enter</b>.'
  if (os.value === 'mac') {
    return 'Откройте <b>Терминал</b> (<b>⌘ + Пробел</b>, наберите «Терминал»), вставьте команду (<b>⌘ + V</b>) и нажмите <b>Enter</b>.'
  }
  return 'Откройте терминал, вставьте команду (<b>Ctrl + Shift + V</b>) и нажмите <b>Enter</b>.'
})
const steps = computed(() => [
  'Скопируйте команду ниже — кнопкой или значком в её заголовке.',
  terminalStep.value,
  `Дождитесь надписи «Готово» и перезапустите ${current.value.title}. Списание за пробный запрос появится в истории операций.`,
])
const archiveSteps = computed(() => {
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
  if (command.value) await mainBlock.value?.copy()
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
  if (item?.manual && os.value === 'lin') os.value = 'win'
  try { localStorage.setItem(APP_STORAGE, id) } catch { /* ignore */ }
}

function rememberedApp() {
  try {
    const saved = localStorage.getItem(APP_STORAGE)
    if (saved && APPS.some((item) => item.id === saved)) return saved
  } catch { /* ignore */ }
  return APPS[0].id
}

function guessOs() {
  const ua = (navigator.userAgent || '').toLowerCase()
  if (ua.includes('mac os') || ua.includes('macintosh')) return 'mac'
  if (ua.includes('linux') && !ua.includes('android')) return 'lin'
  return 'win'
}

function copyKey() {
  return copyWithToast(props.secret, 'Ключ скопирован')
}
</script>

<style scoped>
.guide { padding: 22px 24px 20px; }
.guide-head { margin-bottom: 8px; }
.guide-head-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px 16px;
  flex-wrap: wrap;
}
.card-title { margin: 0; font-size: 1.2rem; letter-spacing: -0.03em; flex: 1 1 auto; min-width: 0; }
.guide-head-lead { margin: 6px 0 0; max-width: 52rem; }
.os-switch { flex: 0 0 auto; margin-left: auto; }
.tabs { margin: 6px -24px 0; padding: 0 24px; }
.panel { padding-top: 18px; }

.fields {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.3fr);
  gap: 10px;
  margin-bottom: 16px;
}
.fields.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.copy-placeholder {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 10px 14px;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-sm);
}
.copy-label {
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.steps { list-style: none; margin: 0 0 14px; padding: 0; display: grid; gap: 10px; font-size: 15px; }
.steps li { display: flex; gap: 12px; align-items: flex-start; line-height: 1.5; }
.steps.compact { font-size: 14px; gap: 8px; }
.steps.compact .step-dot { width: 22px; height: 22px; flex-basis: 22px; font-size: 11px; }
.steps :deep(code), .note code, .kv code, .extra-body code, .panel > p code {
  font-size: 13px;
  background: var(--surface-soft);
  border: 1px solid var(--border);
  padding: 1px 6px;
  border-radius: 6px;
  overflow-wrap: anywhere;
}
.guide-actions { display: flex; gap: 10px 14px; flex-wrap: wrap; align-items: center; margin-top: 12px; }
.note {
  margin: 14px 0 0;
  padding: 10px 14px;
  border-left: 3px solid var(--border-strong);
  background: var(--surface-soft);
  border-radius: 0 8px 8px 0;
  font-size: 13.5px;
  color: var(--muted-2);
}
.notice { margin-top: 4px; }
.other-lead { margin: 0 0 14px; }
.manual-lead { margin: 0 0 14px; }

.extras { margin-top: 18px; border-top: 1px solid var(--border); }
.extra { border-bottom: 1px solid var(--border); }
.extra summary {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 2px;
  cursor: pointer;
  list-style: none;
  font-size: 14px;
  font-weight: 600;
  color: var(--muted-2);
  transition: color 0.15s ease;
}
.extra summary::-webkit-details-marker { display: none; }
.extra summary:hover, .extra[open] summary { color: var(--text); }
.extra summary span { flex: 1; }
.extra .chev { transition: transform 0.18s ease; color: var(--muted); }
.extra[open] .chev { transform: rotate(180deg); }
.extra-body { padding: 2px 0 16px 28px; font-size: 14px; }
.extra-body p { margin: 0 0 10px; }
.extra-body .guide-actions { margin-top: 10px; }
.extra-body .btn { margin-bottom: 10px; }
.kv { display: grid; grid-template-columns: max-content 1fr; gap: 8px 18px; margin: 0; }
.kv dt { color: var(--muted); font-size: 13px; font-weight: 600; padding-top: 2px; }
.kv dd { margin: 0; overflow-wrap: anywhere; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.14s ease, transform 0.14s ease; }
.fade-enter-from { opacity: 0; transform: translateY(4px); }
.fade-leave-to { opacity: 0; }

@media (max-width: 760px) {
  .fields, .fields.three { grid-template-columns: 1fr; }
  .kv { grid-template-columns: 1fr; gap: 4px; }
  .kv dt { margin-top: 8px; }
  .extra-body { padding-left: 0; }
}
</style>
