<template>
  <section id="how" ref="root" class="term-section container">
    <div class="intro">
      <p v-reveal class="kicker">Как это работает</p>
      <h2 v-reveal="80" class="section-title">Подключение<br>за&nbsp;30&nbsp;секунд</h2>
      <p v-reveal="160" class="section-lead">
        Меняете две строки в настройках — и ваши инструменты работают через Aimarket.
        Тот же код, те же модели, счёт в 10 раз меньше.
      </p>

      <ol class="steps">
        <li
          v-for="(step, i) in steps"
          :key="step.title"
          v-reveal="200 + i * 80"
          class="step"
          :class="{ on: currentStep === i, done: currentStep > i }"
        >
          <span class="step-num">
            <svg v-if="currentStep > i" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12 5 5 9-10" /></svg>
            <template v-else>{{ i + 1 }}</template>
          </span>
          <div>
            <b>{{ step.title }}</b>
            <span>{{ step.text }}</span>
          </div>
          <span class="step-bar" aria-hidden="true"></span>
        </li>
      </ol>
    </div>

    <div v-reveal="120" class="window-wrap">
      <div class="window-glow" aria-hidden="true"></div>
      <div class="window" @pointermove="tilt" @pointerleave="untilt" :style="tiltStyle">
        <div class="bar">
          <span class="lights" aria-hidden="true"><i></i><i></i><i></i></span>
          <div class="tabs-row" role="tablist" aria-label="Пример подключения">
            <button
              v-for="(s, key) in scripts"
              :key="key"
              type="button"
              role="tab"
              :aria-selected="tab === key"
              :class="{ on: tab === key }"
              @click="switchTab(key)"
            >{{ s.label }}</button>
          </div>
        </div>

        <div class="screen" aria-live="off">
          <div
            v-for="(line, i) in shown"
            :key="`${tab}-${i}`"
            class="ln"
            :class="`t-${line.type}`"
          ><span v-if="line.type === 'cmd'" class="prompt">$</span>{{ line.text }}<span v-if="i === shown.length - 1 && typing" class="caret"></span></div>
          <div v-if="!shown.length" class="ln t-cmd"><span class="prompt">$</span><span class="caret"></span></div>
        </div>

        <div class="cost">
          <div class="cost-item">
            <span>Токены</span>
            <b class="mono-num">{{ tokens.toLocaleString('ru-RU') }}</b>
          </div>
          <div class="cost-item">
            <span>Напрямую</span>
            <b class="mono-num was">{{ rubLabel(costWas) }}</b>
          </div>
          <div class="cost-item now">
            <span>Через Aimarket</span>
            <b class="mono-num">{{ rubLabel(costNow) }}</b>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { rub } from '../../utils/format'

const props = defineProps({
  rate: { type: Number, default: 10 },
})

const steps = [
  { title: 'Зарегистрируйтесь и пополните', text: 'Почта и оплата российской картой — ключ появится сразу.' },
  { title: 'Укажите Base URL и ключ', text: 'В Cursor, Claude Code, Codex или в своём коде.' },
  { title: 'Работайте как обычно', text: 'Оригинальные модели, списание — 10% от официальной цены.' },
]

// Сценарии: step — какой шаг подсвечивать, tokens — сколько токенов «наработала» строка.
const scripts = {
  claude: {
    label: 'Claude Code',
    usdPerM: 20,
    lines: [
      { type: 'cmd', text: 'export ANTHROPIC_BASE_URL=https://api.market-aii.ru', step: 1 },
      { type: 'cmd', text: 'export ANTHROPIC_AUTH_TOKEN=sk-aim-••••••••3f9a', step: 1 },
      { type: 'cmd', text: 'claude', step: 1 },
      { type: 'brand', text: '✻ Claude Code · claude-opus-5-5 · через Aimarket', step: 2 },
      { type: 'user', text: '> Добавь вход по magic-link и покрой тестами', step: 2 },
      { type: 'tool', text: '⏺ Read   src/auth/  (12 файлов)', step: 2, tokens: 18400 },
      { type: 'tool', text: '⏺ Edit   src/auth/magic-link.ts  +86', step: 2, tokens: 9600 },
      { type: 'tool', text: '⏺ Edit   src/routes/login.vue  +41 −7', step: 2, tokens: 7200 },
      { type: 'tool', text: '⏺ Bash   npm test', step: 2, tokens: 3100 },
      { type: 'ok', text: '✓ 32 passed · 0 failed', step: 2, tokens: 1400 },
      { type: 'ok', text: '✓ Готово за 48 с', step: 3 },
    ],
  },
  codex: {
    label: 'Codex',
    usdPerM: 50,
    lines: [
      { type: 'cmd', text: 'export OPENAI_BASE_URL=https://api.market-aii.ru/v1', step: 1 },
      { type: 'cmd', text: 'export OPENAI_API_KEY=sk-aim-••••••••3f9a', step: 1 },
      { type: 'cmd', text: 'codex --model gpt-6-astra', step: 1 },
      { type: 'brand', text: '◎ Codex · gpt-6-astra · через Aimarket', step: 2 },
      { type: 'user', text: '> Найди утечку памяти в воркере очереди', step: 2 },
      { type: 'tool', text: '⏺ Search  worker/  «connection»', step: 2, tokens: 12800 },
      { type: 'tool', text: '⏺ Read    worker/queue.py', step: 2, tokens: 6900 },
      { type: 'tool', text: '⏺ Patch   worker/queue.py  +12 −4', step: 2, tokens: 5200 },
      { type: 'ok', text: '✓ Соединения закрываются в finally — утечки нет', step: 3, tokens: 900 },
    ],
  },
  python: {
    label: 'Python',
    usdPerM: 10,
    lines: [
      { type: 'code', text: 'from openai import OpenAI', step: 1 },
      { type: 'code', text: '', step: 1 },
      { type: 'code', text: 'client = OpenAI(', step: 1 },
      { type: 'code', text: '    base_url="https://api.market-aii.ru/v1",', step: 1 },
      { type: 'code', text: '    api_key="sk-aim-••••••••3f9a",', step: 1 },
      { type: 'code', text: ')', step: 1 },
      { type: 'code', text: 'r = client.chat.completions.create(', step: 2 },
      { type: 'code', text: '    model="claude-sonnet-5-5",', step: 2 },
      { type: 'code', text: '    messages=[{"role": "user", "content": "Сделай ревью PR"}],', step: 2 },
      { type: 'code', text: ')', step: 2 },
      { type: 'ok', text: '→ «Нашёл 3 замечания: гонка в кэше, N+1 запрос и…»', step: 3, tokens: 24000 },
    ],
  },
}

const root = ref(null)
const tab = ref('claude')
const shown = ref([])
const typing = ref(false)
const tokens = ref(0)
const currentStep = ref(0)

const script = computed(() => scripts[tab.value])
// Условная цена: смесь входа и выхода у выбранной модели.
const costWas = computed(() => (tokens.value / 1e6) * script.value.usdPerM * props.rate * 10)
const costNow = computed(() => (tokens.value / 1e6) * script.value.usdPerM * props.rate)
function rubLabel(value) {
  return rub(value, value < 100 ? 2 : 0)
}

let timer = 0
let run = 0
let started = false
const reduced = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
const sleep = (ms, id) => new Promise((resolve) => { timer = setTimeout(() => resolve(id === run), ms) })

async function play() {
  const id = ++run
  shown.value = []
  tokens.value = 0
  currentStep.value = 0
  if (!(await sleep(500, id))) return
  for (const line of script.value.lines) {
    currentStep.value = line.step
    const typed = line.type === 'cmd' || line.type === 'user' || line.type === 'code'
    if (typed && !reduced) {
      typing.value = true
      shown.value.push({ ...line, text: '' })
      const target = shown.value[shown.value.length - 1]
      const step = line.type === 'code' ? 3 : 2
      for (let c = 0; c < line.text.length; c += step) {
        target.text = line.text.slice(0, c + step)
        if (!(await sleep(line.type === 'code' ? 12 : 22, id))) return
      }
      target.text = line.text
      typing.value = false
      if (!(await sleep(line.type === 'code' ? 60 : 260, id))) return
    } else {
      if (!(await sleep(reduced ? 0 : 420, id))) return
      shown.value.push({ ...line })
      if (line.tokens) await countTokens(line.tokens, id)
    }
  }
  currentStep.value = 3
  if (!(await sleep(5200, id))) return
  play()
}

async function countTokens(amount, id) {
  const from = tokens.value
  const frames = reduced ? 1 : 18
  for (let f = 1; f <= frames; f++) {
    tokens.value = Math.round(from + (amount * f) / frames)
    if (!(await sleep(24, id))) return
  }
}

function switchTab(key) {
  if (tab.value === key) return
  tab.value = key
  play()
}

// Лёгкий 3D-наклон окна за курсором.
const rx = ref(0)
const ry = ref(0)
const tiltStyle = computed(() => ({ transform: `perspective(1400px) rotateX(${rx.value}deg) rotateY(${ry.value}deg)` }))
function tilt(e) {
  if (e.pointerType === 'touch' || reduced) return
  const rect = e.currentTarget.getBoundingClientRect()
  ry.value = ((e.clientX - rect.left) / rect.width - 0.5) * 6
  rx.value = -((e.clientY - rect.top) / rect.height - 0.5) * 5
}
function untilt() {
  rx.value = 0
  ry.value = 0
}

let io = null
onMounted(() => {
  io = new IntersectionObserver(([entry]) => {
    if (entry.isIntersecting && !started) {
      started = true
      play()
    }
  }, { threshold: 0.25 })
  io.observe(root.value)
})
onBeforeUnmount(() => {
  run++
  clearTimeout(timer)
  io?.disconnect()
})
</script>

<style scoped>
.term-section {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  gap: 64px;
  align-items: center;
  padding-top: 120px;
  padding-bottom: 120px;
  scroll-margin-top: 80px;
}
.steps { list-style: none; margin: 36px 0 0; padding: 0; display: grid; gap: 10px; }
.step {
  position: relative;
  display: flex;
  gap: 16px;
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid transparent;
  overflow: hidden;
  transition: background 0.4s ease, border-color 0.4s ease, box-shadow 0.4s ease;
}
.step.on {
  background: rgba(255, 255, 255, 0.75);
  border-color: rgba(255, 255, 255, 0.95);
  box-shadow: var(--shadow-lg);
}
.step-num {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--border-strong);
  background: #fff;
  font-size: 13px;
  font-weight: 700;
  transition: background 0.3s ease, color 0.3s ease, border-color 0.3s ease;
}
.step.on .step-num { background: var(--ink); color: #fff; border-color: var(--ink); }
.step.done .step-num { background: #3f9b6f; color: #fff; border-color: #3f9b6f; }
.step b { display: block; font-size: 1.02rem; letter-spacing: -0.02em; margin-bottom: 2px; }
.step span { color: var(--muted-2); font-size: 0.93rem; line-height: 1.45; }
.step-bar {
  position: absolute;
  left: 0;
  bottom: 0;
  height: 2px;
  width: 100%;
  background: var(--grad);
  transform: scaleX(0);
  transform-origin: left;
}
.step.on .step-bar { animation: bar 3.2s linear forwards; }
@keyframes bar { to { transform: scaleX(1); } }

.window-wrap { position: relative; }
.window-glow {
  position: absolute;
  inset: 8% -4% -6%;
  z-index: -1;
  border-radius: 40px;
  background: var(--grad);
  filter: blur(60px);
  opacity: 0.35;
}
.window {
  border-radius: 22px;
  background: linear-gradient(180deg, #1d1915 0%, #14110d 100%);
  color: #ece4d6;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08), 0 0 0 1px rgba(21, 18, 14, 0.9), 0 50px 100px -30px rgba(40, 28, 12, 0.6);
  overflow: hidden;
  transition: transform 0.4s var(--ease-out);
  will-change: transform;
}
.bar {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.02);
}
.lights { display: inline-flex; gap: 7px; }
.lights i { width: 11px; height: 11px; border-radius: 50%; background: #ff5f57; }
.lights i:nth-child(2) { background: #febc2e; }
.lights i:nth-child(3) { background: #28c840; }
.tabs-row { display: flex; gap: 4px; overflow-x: auto; scrollbar-width: none; }
.tabs-row button {
  border: 0;
  padding: 6px 12px;
  border-radius: 8px;
  background: transparent;
  color: rgba(236, 228, 214, 0.5);
  font: 500 12.5px/1 var(--font-mono);
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.2s ease, color 0.2s ease;
}
.tabs-row button:hover { color: #ece4d6; }
.tabs-row button.on { background: rgba(255, 255, 255, 0.09); color: #fff; }

.screen {
  height: 380px;
  padding: 20px 22px;
  overflow: hidden;
  font: 13.5px/1.75 var(--font-mono);
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}
.ln { white-space: pre-wrap; word-break: break-word; animation: ln-in 0.35s var(--ease-out); }
@keyframes ln-in { from { opacity: 0; transform: translateY(4px); } }
.prompt { color: #7ee2a8; margin-right: 10px; }
.t-cmd { color: #f3ece0; }
.t-brand { color: #f0a477; margin: 8px 0 4px; }
.t-user { color: #fff; font-weight: 600; margin-bottom: 4px; }
.t-tool { color: rgba(236, 228, 214, 0.7); }
.t-ok { color: #7ee2a8; }
.t-code { color: #c9d4ff; }
.caret {
  display: inline-block;
  width: 8px;
  height: 1.1em;
  margin-left: 2px;
  vertical-align: -0.18em;
  background: #f0a477;
  animation: blink 1s steps(1) infinite;
}
@keyframes blink { 50% { opacity: 0; } }

.cost {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-top: 1px solid rgba(255, 255, 255, 0.07);
  background: rgba(255, 255, 255, 0.025);
}
.cost-item { padding: 14px 18px; display: flex; flex-direction: column; gap: 2px; }
.cost-item + .cost-item { border-left: 1px solid rgba(255, 255, 255, 0.07); }
.cost-item span { font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: rgba(236, 228, 214, 0.45); }
.mono-num { font: 600 18px/1.2 var(--font-mono); font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }
.mono-num.was { color: rgba(236, 228, 214, 0.45); text-decoration: line-through; text-decoration-color: rgba(240, 120, 90, 0.7); }
.cost-item.now b {
  background: linear-gradient(100deg, #ffd08a, #f0a477 50%, #c9a8ff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

@media (max-width: 960px) {
  .term-section { grid-template-columns: 1fr; gap: 40px; padding-top: 80px; padding-bottom: 80px; }
}
@media (max-width: 560px) {
  .screen { height: 330px; padding: 16px; font-size: 11.5px; }
  .cost-item { padding: 12px; }
  .mono-num { font-size: 14px; }
  .cost-item span { font-size: 9.5px; }
}
</style>
