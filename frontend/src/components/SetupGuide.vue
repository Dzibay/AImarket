<template>
  <section class="card guide">
    <div class="guide-head">
      <div>
        <h2 class="card-title">Подключение к приложению</h2>
        <p class="muted small">
          Выберите программу и систему — покажем короткие шаги и дадим готовый установщик.
          Ключ из кабинета вставляется в программу, адрес API у всех один.
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
          <label class="lang">
            <span class="muted small">Язык установщика</span>
            <select v-model="lang">
              <option value="ru">Русский</option>
              <option value="en">English</option>
            </select>
          </label>
        </div>

        <p v-if="app === 'cdesk'" class="note">
          Скрипт подключает сторонний сервис в Claude Desktop. Он не выходит из аккаунта и не меняет чаты —
          перед запуском сохраняется копия локальных чатов.
        </p>
        <p v-if="app === 'cursor'" class="note">
          Скрипт сохраняет копию настроек Cursor и меняет только ключ, адрес API и список моделей GPT и Grok.
          Чаты остаются. Claude через эту настройку не подключается.
        </p>

        <ol class="steps">
          <li v-for="(step, index) in steps" :key="index" v-html="step" />
        </ol>

        <div class="guide-actions">
          <a class="btn" :href="downloadUrl" download>Скачать установщик</a>
          <button v-if="secret" type="button" class="btn quiet" @click="copyKey">
            {{ copiedKey ? 'Ключ скопирован' : 'Скопировать мой ключ' }}
          </button>
          <span v-else class="muted small">Ключ появится после пополнения — тогда его можно будет скопировать здесь.</span>
        </div>
        <p class="muted small file">Файл: <code>{{ fileName }}</code></p>
      </div>
    </template>

    <div v-else-if="app === 'other'" class="steps-wrap">
      <h3>Другое приложение</h3>
      <p class="muted small">
        В настройках найдите пункт «провайдер», «OpenAI-compatible API» или «Custom endpoint» и вставьте значения ниже.
      </p>
      <dl class="kv">
        <dt>Провайдер</dt>
        <dd>OpenAI-compatible</dd>
        <dt>Base URL</dt>
        <dd>
          <code>{{ baseUrl }}</code>
          <button type="button" class="mini" @click="copyValue(baseUrl, 'base')">{{ copied === 'base' ? '✓' : 'копировать' }}</button>
        </dd>
        <dt>API key</dt>
        <dd>
          <template v-if="secret">
            Ваш ключ из раздела выше
            <button type="button" class="mini" @click="copyKey">{{ copiedKey ? '✓' : 'копировать' }}</button>
          </template>
          <span v-else class="muted">появится после пополнения</span>
        </dd>
        <dt>Модель</dt>
        <dd>
          <code>{{ DEFAULT_MODEL }}</code>
          <button type="button" class="mini" @click="copyValue(DEFAULT_MODEL, 'model')">{{ copied === 'model' ? '✓' : 'копировать' }}</button>
          <span class="muted small"> — или любая другая из списка моделей</span>
        </dd>
      </dl>
      <p class="note">
        Если поле просит полный адрес Chat Completions, укажите <code>{{ chatUrl }}</code>.
        Для Claude (Anthropic Messages API) адрес без <code>/v1</code>: <code>{{ anthropicUrl }}</code>.
        Список доступных моделей: <code>GET {{ modelsUrl }}</code>.
      </p>
    </div>

    <details v-if="app" class="network">
      <summary>Если соединение обрывается</summary>
      <p>
        Сбросы <code>ECONNRESET</code>, таймауты и обрыв потока обычно идут из сети. Запустите установщик снова и
        выберите пункт <code>3</code> — запасной адрес. Вручную:
      </p>
      <dl class="kv compact">
        <dt>OpenAI-совместимые программы</dt>
        <dd><code>{{ RESERVE_OPENAI }}</code></dd>
        <dt>Claude и Anthropic</dt>
        <dd><code>{{ RESERVE_CLAUDE }}</code></dd>
      </dl>
      <p class="muted small">
        Если не помогло, попробуйте VPN, который не рвёт поток. Одна программа может работать, а другая нет —
        протоколы разные.
      </p>
    </details>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { copyText } from '../utils/format'

const props = defineProps({
  secret: { type: String, default: '' },
  baseUrl: { type: String, default: 'https://router.cheap/v1' },
})

const DEFAULT_MODEL = 'gpt-5.6-sol'
const RESERVE_OPENAI = 'https://direct.router-cheap.com/v1'
const RESERVE_CLAUDE = 'https://direct.router-cheap.com'

// Совпадает со списком в боте (bot/app/guide.py) и с файлами в /downloads/setup.
const APPS = [
  { id: 'codex', title: 'Codex', file: 'codex', linux: true },
  { id: 'ccode', title: 'Claude Code', file: 'claude-code', linux: true },
  { id: 'cdesk', title: 'Claude Desktop', file: 'claude-desktop', linux: false },
  { id: 'ocode', title: 'OpenCode', file: 'opencode', linux: true },
  { id: 'hermes', title: 'Hermes', file: 'hermes', linux: true },
  { id: 'grok', title: 'Grok Build', file: 'grok-build', linux: true },
  { id: 'cursor', title: 'Cursor', file: 'cursor', linux: true },
  { id: 'other', title: 'Другое приложение', file: '', linux: false },
]
const OS = [
  { id: 'win', title: 'Windows', folder: 'windows' },
  { id: 'mac', title: 'macOS', folder: 'macos' },
  { id: 'lin', title: 'Linux', folder: 'linux' },
]

const app = ref('')
const os = ref(guessOs())
const lang = ref('ru')
const copiedKey = ref(false)
const copied = ref('')

const current = computed(() => APPS.find((item) => item.id === app.value) || null)
const systems = computed(() => (current.value?.linux ? OS : OS.slice(0, 2)))
const osTitle = computed(() => OS.find((item) => item.id === os.value)?.title || '')

const normalizedBase = computed(() => (props.baseUrl || 'https://router.cheap/v1').replace(/\/+$/, ''))
const chatUrl = computed(() => `${normalizedBase.value}/chat/completions`)
const modelsUrl = computed(() => `${normalizedBase.value}/models`)
const anthropicUrl = computed(() => normalizedBase.value.replace(/\/v1$/, ''))

const fileName = computed(() => {
  if (!current.value || !os.value) return ''
  if (os.value === 'lin') return `setup-aimarket-${current.value.file}-${lang.value}.sh`
  const folder = OS.find((item) => item.id === os.value)?.folder || 'windows'
  return `aimarket-${current.value.file}-${folder}-${lang.value}.zip`
})
const downloadUrl = computed(() => (fileName.value ? `/downloads/setup/${fileName.value}` : '#'))

const runCommand = computed(() => {
  if (os.value === 'win') return 'start.cmd'
  if (os.value === 'mac') return 'start.command'
  return `bash ${fileName.value}`
})

const steps = computed(() => {
  if (!current.value || !os.value) return []
  const title = current.value.title
  const list = [`Убедитесь, что <b>${title}</b> уже установлен на этом компьютере.`]
  if (app.value === 'cdesk') list.push('Полностью закройте Claude Desktop, включая фоновый процесс.')
  if (app.value === 'cursor') list.push('Полностью закройте Cursor, включая иконку в трее.')
  if (os.value === 'lin') list.push('Скачайте файл кнопкой ниже и не переименовывайте его.')
  else list.push('Скачайте архив кнопкой ниже и распакуйте его.')
  list.push(`Запустите <code>${runCommand.value}</code>.`)
  if (os.value === 'mac') list.push('Если macOS не даёт открыть файл — правый клик → «Открыть», затем подтвердите.')
  list.push('В меню установщика введите <code>1</code> — это подключение к API.')
  list.push('Когда попросят ключ — вставьте ваш ключ доступа (кнопка «Скопировать мой ключ» ниже).')
  list.push(`Перезапустите ${title} и отправьте пробный запрос. Списание появится в истории операций.`)
  return list
})

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
.lang { display: flex; align-items: center; gap: 8px; }
.lang select {
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  padding: 6px 10px;
  background: #fff;
  font: inherit;
  font-size: 14px;
}
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
.file { margin: 10px 0 0; }

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
