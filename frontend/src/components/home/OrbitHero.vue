<template>
  <section
    ref="root"
    class="orbit-hero"
    aria-labelledby="hero-title"
    @pointermove="onPointerMove"
    @pointerleave="onPointerLeave"
  >
    <!-- Фон: «аврора», сетка, свет за курсором и зерно -->
    <div class="bg" aria-hidden="true">
      <span class="aurora a1"></span>
      <span class="aurora a2"></span>
      <span class="aurora a3"></span>
      <span class="grid"></span>
      <span class="spot"></span>
      <span class="grain"></span>
    </div>

    <!-- Орбиты с моделями -->
    <div ref="stage" class="stage" aria-hidden="true">
      <svg class="rings" :viewBox="`0 0 ${size.w} ${size.h}`" preserveAspectRatio="none">
        <defs>
          <linearGradient id="ring-grad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#d9653b" stop-opacity="0.55" />
            <stop offset="0.5" stop-color="#b07be0" stop-opacity="0.35" />
            <stop offset="1" stop-color="#6f7cf0" stop-opacity="0.5" />
          </linearGradient>
        </defs>
        <g ref="ringsGroup">
          <ellipse
            v-for="(ring, i) in ringGeometry"
            :key="i"
            :cx="ring.cx"
            :cy="ring.cy"
            :rx="ring.rx"
            :ry="ring.ry"
            class="ring"
            :class="`ring-${i}`"
          />
        </g>
      </svg>

      <div class="core">
        <span class="core-glow"></span>
        <img src="/favicon-96x96.png" alt="" width="56" height="56">
      </div>

      <button
        v-for="(planet, i) in planets"
        :key="planet.key"
        :ref="(el) => (planetEls[i] = el)"
        type="button"
        tabindex="-1"
        class="planet"
        :class="[`kind-${planet.kind}`, { hot: hovered === i }]"
        @pointerenter="hover(i, $event)"
        @pointerleave="unhover(i)"
        @click="$emit('pick', planet)"
      >
        <span class="planet-logo" :style="{ '--tint': planet.tint }">
          <BrandLogo v-if="planet.kind === 'model'" :brand="planet.brand" :size="planet.big ? 24 : 20" />
          <svg v-else-if="planet.key === 'cursor'" width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M12 2.5 20.5 7.4v9.2L12 21.5l-8.5-4.9V7.4L12 2.5Z" fill="#1c1915" /><path d="M12 2.5v9.5l8.5-4.6M12 12 3.5 7.4M12 12v9.5" stroke="#fff" stroke-opacity=".55" stroke-width="1.1" /></svg>
          <svg v-else-if="planet.key === 'claude-code'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#d97757" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m5 7 5 5-5 5" /><path d="M13 17h6" /></svg>
          <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1c1915" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 5c-2 0-3 1-3 3v2c0 1-1 2-2 2 1 0 2 1 2 2v2c0 2 1 3 3 3" /><path d="M16 5c2 0 3 1 3 3v2c0 1 1 2 2 2-1 0-2 1-2 2v2c0 2-1 3-3 3" /></svg>
        </span>
        <span class="planet-name">{{ planet.label }}</span>
      </button>
    </div>

    <!-- Подсказка с ценой модели -->
    <Transition name="tip">
      <div v-if="tip" class="tip" :style="{ left: `${tip.x}px`, top: `${tip.y}px` }" role="tooltip">
        <template v-if="tip.planet.kind === 'model'">
          <span class="tip-model">{{ tip.planet.model }}</span>
          <span class="tip-row">
            <span class="tip-label">1M токенов на выходе</span>
          </span>
          <span class="tip-price">
            <s>{{ tip.was }}</s>
            <b>{{ tip.now }}</b>
            <i>−90%</i>
          </span>
        </template>
        <template v-else>
          <span class="tip-model">{{ tip.planet.label }}</span>
          <span class="tip-label">Укажите наш Base URL и ключ — и работайте со всеми моделями</span>
        </template>
      </div>
    </Transition>

    <!-- Текст и регистрация -->
    <div class="center">
      <div class="halo" aria-hidden="true"></div>
      <p class="kicker hero-in" style="--i: 0">
        Claude Opus 5.5 и GPT-6.1 уже доступны
      </p>
      <h1 id="hero-title" class="title">
        <span class="line">
          <span v-for="(word, i) in titleTop" :key="word" class="word" :style="{ '--i': i + 1 }">{{ word }}</span>
        </span>
        <span class="line">
          <span class="word grad-text" :style="{ '--i': titleTop.length + 1 }">в&nbsp;10&nbsp;раз дешевле</span>
        </span>
      </h1>
      <p class="lead hero-in" style="--i: 5">
        Claude, GPT, Gemini, Grok и ещё {{ modelCount - 4 }}+ моделей по одному API-ключу.
        Без зарубежной карты — платите российской картой и работайте в Cursor, Claude Code и Codex.
      </p>

      <div class="form-wrap hero-in" style="--i: 6">
        <SignupForm source="hero" cta="Получить доступ" />
      </div>

      <ul class="meta hero-in" style="--i: 7">
        <li>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12 5 5 9-10" /></svg>
          Регистрация за 10 секунд
        </li>
        <li>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12 5 5 9-10" /></svg>
          Пополнение от {{ minLabel }}
        </li>
        <li>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12 5 5 9-10" /></svg>
          Оригинальные модели, без подмен
        </li>
      </ul>

      <div class="proof hero-in" style="--i: 8">
        <span class="avatars" aria-hidden="true">
          <span v-for="a in avatars" :key="a.t" :style="{ background: a.bg }">{{ a.t }}</span>
        </span>
        <span class="proof-text">
          <span class="stars" aria-hidden="true">★★★★★</span>
          <b>4,9</b> · более <b>12 400</b> разработчиков уже экономят
        </span>
      </div>
    </div>

    <a href="#how" class="scroll-cue" aria-label="Листать ниже">
      <span class="mouse"><span></span></span>
    </a>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import BrandLogo from '../BrandLogo.vue'
import SignupForm from './SignupForm.vue'
import { families, findModel, ourRubPerMillion, referenceRubPerMillion } from '../../data/tokenPrices'
import { rub, usd } from '../../utils/format'

const props = defineProps({
  rate: { type: Number, default: 0 },
  minUsd: { type: Number, default: 10 },
})
defineEmits(['pick'])

const titleTop = ['Все', 'топовые', 'нейросети']
const modelCount = families.reduce((sum, family) => sum + family.models.length, 0)
const minLabel = computed(() => (props.rate > 0 ? rub(Math.ceil(props.minUsd * props.rate), 0) : usd(props.minUsd, 0)))

const avatars = [
  { t: 'АК', bg: 'linear-gradient(135deg,#f3b58a,#d9653b)' },
  { t: 'МС', bg: 'linear-gradient(135deg,#c9b2f2,#8b6be0)' },
  { t: 'ДЛ', bg: 'linear-gradient(135deg,#a9c8ff,#5b7ff0)' },
  { t: 'ЕВ', bg: 'linear-gradient(135deg,#a8dcc0,#3f9b6f)' },
  { t: 'ИП', bg: 'linear-gradient(135deg,#f5d58f,#d99a2b)' },
]

// Три кольца: внутреннее — флагманы, среднее — сильные альтернативы, внешнее — приложения и «рабочие лошадки».
const RINGS = [
  { kx: 0.33, ky: 0.37, speed: 0.11 },
  { kx: 0.42, ky: 0.45, speed: -0.075 },
  { kx: 0.51, ky: 0.53, speed: 0.05 },
]

const planets = [
  { key: 'claude', kind: 'model', brand: 'claude', label: 'Claude', model: 'claude-opus-5-5', ring: 0, big: true },
  { key: 'gpt', kind: 'model', brand: 'gpt', label: 'GPT', model: 'gpt-6-astra', ring: 0, big: true },
  { key: 'gemini', kind: 'model', brand: 'gemini', label: 'Gemini', model: 'gemini-3.1-pro-preview', ring: 0, big: true },
  { key: 'grok', kind: 'model', brand: 'grok', label: 'Grok', model: 'grok-4.7', ring: 1 },
  { key: 'deepseek', kind: 'model', brand: 'deepseek', label: 'DeepSeek', model: 'deepseek-v4-pro', ring: 1 },
  { key: 'kimi', kind: 'model', brand: 'china', label: 'Kimi', model: 'kimi-k3', ring: 1 },
  { key: 'qwen', kind: 'model', brand: 'china', label: 'Qwen', model: 'qwen3.8-max', ring: 1 },
  { key: 'cursor', kind: 'app', label: 'Cursor', ring: 2 },
  { key: 'glm', kind: 'model', brand: 'china', label: 'GLM', model: 'glm-5.3', ring: 2 },
  { key: 'claude-code', kind: 'app', label: 'Claude Code', ring: 2 },
  { key: 'minimax', kind: 'model', brand: 'china', label: 'MiniMax', model: 'minimax-m3', ring: 2 },
  { key: 'codex', kind: 'app', label: 'Codex', ring: 2 },
]
// Равномерно раскладываем планеты по своим кольцам, со сдвигом между кольцами.
const perRing = [0, 0, 0]
const ringTotals = [0, 0, 0]
for (const p of planets) ringTotals[p.ring] += 1
for (const p of planets) {
  const idx = perRing[p.ring]++
  p.phase = (idx / ringTotals[p.ring]) * Math.PI * 2 + p.ring * 0.9 - 0.5
}

const root = ref(null)
const stage = ref(null)
const ringsGroup = ref(null)
const planetEls = []
const size = reactive({ w: 1200, h: 800 })
const hovered = ref(-1)
const tip = ref(null)

const ringGeometry = computed(() => {
  const { cx, cy } = center()
  return RINGS.map((r) => ({ cx, cy, rx: size.w * r.kx * scaleX(), ry: size.h * r.ky * scaleY() }))
})

function isCompact() {
  return size.w < 760
}
// На узких экранах кольца не должны вылезать за пределы — сжимаем по X.
function scaleX() {
  if (isCompact()) return 0.95
  return Math.min(1, 1500 / size.w)
}
function scaleY() {
  return isCompact() ? 0.82 : 1
}
function center() {
  return { cx: size.w / 2, cy: size.h / 2 }
}

// --- Анимация ---
let raf = 0
let last = 0
let t = 0
let speed = 1
let visible = true
const mouse = { x: 0, y: 0, tx: 0, ty: 0 }
const reduced = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

function frame(now) {
  raf = requestAnimationFrame(frame)
  if (!visible) return
  const dt = Math.min(64, now - (last || now)) / 1000
  last = now
  const targetSpeed = hovered.value >= 0 ? 0.08 : 1
  speed += (targetSpeed - speed) * Math.min(1, dt * 4)
  if (!reduced) t += dt * speed

  mouse.x += (mouse.tx - mouse.x) * Math.min(1, dt * 3)
  mouse.y += (mouse.ty - mouse.y) * Math.min(1, dt * 3)

  const { cx, cy } = center()
  const sx = scaleX()
  const sy = scaleY()
  const compact = isCompact()
  for (let i = 0; i < planets.length; i++) {
    const el = planetEls[i]
    if (!el) continue
    const p = planets[i]
    const ring = RINGS[p.ring]
    const theta = p.phase + t * ring.speed * Math.PI
    const sin = Math.sin(theta)
    const depth = (sin + 1) / 2 // 0 — дальняя сторона (вверху), 1 — ближняя (внизу)
    const par = 14 + 34 * depth
    const x = cx + Math.cos(theta) * size.w * ring.kx * sx + mouse.x * par
    const y = cy + sin * size.h * ring.ky * sy + mouse.y * par * 0.7
    const scale = (compact ? 0.62 : 0.74) + 0.36 * depth
    const blur = (1 - depth) * 2.2
    el.style.transform = `translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0) translate(-50%, -50%) scale(${scale.toFixed(3)})`
    el.style.opacity = (0.5 + 0.5 * depth).toFixed(3)
    el.style.filter = hovered.value === i ? 'none' : `blur(${blur.toFixed(2)}px)`
    el.style.zIndex = String(Math.round(depth * 100))
  }
  if (ringsGroup.value) {
    ringsGroup.value.setAttribute('transform', `translate(${(mouse.x * 18).toFixed(1)} ${(mouse.y * 12).toFixed(1)})`)
  }
  if (root.value) {
    root.value.style.setProperty('--px', mouse.x.toFixed(3))
    root.value.style.setProperty('--py', mouse.y.toFixed(3))
  }
}

function measure() {
  if (!stage.value) return
  const rect = stage.value.getBoundingClientRect()
  size.w = Math.max(320, rect.width)
  size.h = Math.max(260, rect.height)
}

function onPointerMove(e) {
  if (e.pointerType === 'touch' || !root.value) return
  const rect = root.value.getBoundingClientRect()
  mouse.tx = ((e.clientX - rect.left) / rect.width - 0.5) * 2
  mouse.ty = ((e.clientY - rect.top) / rect.height - 0.5) * 2
  root.value.style.setProperty('--mx', `${e.clientX - rect.left}px`)
  root.value.style.setProperty('--my', `${e.clientY - rect.top}px`)
}
function onPointerLeave() {
  mouse.tx = 0
  mouse.ty = 0
  hovered.value = -1
  tip.value = null
}

function hover(i, e) {
  if (e.pointerType === 'touch') return
  hovered.value = i
  const planet = planets[i]
  const el = planetEls[i]
  if (!el || !root.value) return
  const box = el.getBoundingClientRect()
  const host = root.value.getBoundingClientRect()
  const data = { planet, x: box.left + box.width / 2 - host.left, y: box.top - host.top - 12 }
  if (planet.kind === 'model') {
    const model = findModel(planet.model)
    if (model && props.rate > 0) {
      data.was = rub(referenceRubPerMillion(model.output, props.rate), 0)
      data.now = rub(ourRubPerMillion(model.output, props.rate), 0)
    } else if (model) {
      data.was = usd(model.output * 10, 0)
      data.now = usd(model.output, 0)
    }
  }
  tip.value = data
}
function unhover(i) {
  if (hovered.value === i) {
    hovered.value = -1
    tip.value = null
  }
}

let resizeObserver = null
let io = null
function onVisibility() {
  visible = !document.hidden && intersecting
  last = 0
}
let intersecting = true

onMounted(() => {
  measure()
  resizeObserver = new ResizeObserver(measure)
  resizeObserver.observe(stage.value)
  io = new IntersectionObserver(([entry]) => {
    intersecting = entry.isIntersecting
    onVisibility()
  })
  io.observe(root.value)
  document.addEventListener('visibilitychange', onVisibility)
  raf = requestAnimationFrame(frame)
})
onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  resizeObserver?.disconnect()
  io?.disconnect()
  document.removeEventListener('visibilitychange', onVisibility)
})
</script>

<style scoped>
.orbit-hero {
  --px: 0;
  --py: 0;
  --mx: 50%;
  --my: 40%;
  position: relative;
  min-height: max(780px, 100svh);
  display: grid;
  place-items: center;
  padding: 110px 24px 96px;
  overflow: hidden;
  isolation: isolate;
}

/* ---------- Фон ---------- */
.bg { position: absolute; inset: 0; z-index: -2; pointer-events: none; }
.aurora {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.75;
  will-change: transform;
}
.a1 {
  width: 46vw; height: 46vw; left: -12vw; top: -14vw;
  background: radial-gradient(circle at 40% 40%, #ffcfae, rgba(255, 207, 174, 0) 70%);
  animation: drift1 22s ease-in-out infinite alternate;
}
.a2 {
  width: 42vw; height: 42vw; right: -10vw; top: -6vw;
  background: radial-gradient(circle at 50% 50%, #ddd0ff, rgba(221, 208, 255, 0) 70%);
  animation: drift2 26s ease-in-out infinite alternate;
}
.a3 {
  width: 60vw; height: 34vw; left: 20vw; bottom: -18vw;
  background: radial-gradient(circle at 50% 50%, #cfe2ff, rgba(207, 226, 255, 0) 70%);
  animation: drift3 30s ease-in-out infinite alternate;
}
@keyframes drift1 { to { transform: translate(8vw, 6vw) scale(1.15); } }
@keyframes drift2 { to { transform: translate(-6vw, 10vw) scale(0.9); } }
@keyframes drift3 { to { transform: translate(-10vw, -4vw) scale(1.1); } }
.grid {
  position: absolute;
  inset: -40px;
  background-image:
    linear-gradient(rgba(28, 25, 21, 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(28, 25, 21, 0.055) 1px, transparent 1px);
  background-size: 64px 64px;
  -webkit-mask-image: radial-gradient(ellipse 70% 60% at 50% 45%, #000 20%, transparent 75%);
  mask-image: radial-gradient(ellipse 70% 60% at 50% 45%, #000 20%, transparent 75%);
  transform: translate(calc(var(--px) * -10px), calc(var(--py) * -10px));
}
.spot {
  position: absolute;
  inset: 0;
  background: radial-gradient(520px circle at var(--mx) var(--my), rgba(255, 255, 255, 0.75), transparent 60%);
  transition: opacity 0.4s ease;
}
.grain {
  position: absolute;
  inset: 0;
  opacity: 0.22;
  mix-blend-mode: multiply;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 .1 0 0 0 0 .08 0 0 0 0 .05 0 0 0 .35 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

/* ---------- Орбиты ---------- */
.stage { position: absolute; inset: 0; z-index: -1; }
.rings { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; }
.ring {
  fill: none;
  stroke: url(#ring-grad);
  stroke-width: 1.2;
  vector-effect: non-scaling-stroke;
}
.ring-1 { stroke-dasharray: 2 7; stroke-width: 1.4; animation: dash 40s linear infinite; }
.ring-2 { stroke-opacity: 0.6; }
@keyframes dash { to { stroke-dashoffset: -600; } }

.core { display: none; }

.planet {
  position: absolute;
  left: 0;
  top: 0;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 7px 16px 7px 7px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.95);
  background: linear-gradient(160deg, rgba(255, 255, 255, 0.92), rgba(250, 246, 239, 0.78));
  box-shadow: inset 0 1px 0 #fff, 0 18px 40px -14px rgba(40, 28, 12, 0.35), 0 4px 10px -4px rgba(40, 28, 12, 0.12);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  color: var(--text);
  font: inherit;
  cursor: pointer;
  will-change: transform, opacity, filter;
  transition: box-shadow 0.3s ease, background 0.3s ease;
}
.planet-logo {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #fff;
  box-shadow: inset 0 0 0 1px rgba(28, 25, 21, 0.06), 0 4px 10px -4px rgba(40, 28, 12, 0.25);
}
.planet-name { font-size: 15px; font-weight: 600; letter-spacing: -0.02em; white-space: nowrap; }
.planet.kind-app .planet-name { font-family: var(--font-mono); font-size: 13.5px; font-weight: 600; letter-spacing: -0.03em; }
.planet:hover, .planet.hot {
  background: #fff;
  box-shadow: inset 0 1px 0 #fff, 0 0 0 4px rgba(232, 160, 74, 0.18), 0 24px 50px -14px rgba(40, 28, 12, 0.45);
}

/* ---------- Подсказка ---------- */
.tip {
  position: absolute;
  z-index: 20;
  transform: translate(-50%, -100%);
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 200px;
  max-width: 260px;
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(21, 18, 14, 0.92);
  color: #f6f1e8;
  box-shadow: 0 20px 50px -10px rgba(21, 18, 14, 0.5);
  backdrop-filter: blur(12px);
  pointer-events: none;
}
.tip::after {
  content: "";
  position: absolute;
  left: 50%;
  bottom: -6px;
  width: 12px;
  height: 12px;
  background: inherit;
  transform: translateX(-50%) rotate(45deg);
  border-radius: 2px;
}
.tip-model { font: 600 13px/1.3 var(--font-mono); }
.tip-label { color: rgba(246, 241, 232, 0.6); font-size: 12px; line-height: 1.4; }
.tip-price { display: flex; align-items: baseline; gap: 8px; }
.tip-price s { color: rgba(246, 241, 232, 0.45); font-size: 13px; }
.tip-price b { font-size: 20px; letter-spacing: -0.03em; }
.tip-price i {
  margin-left: auto;
  padding: 2px 8px;
  border-radius: 999px;
  background: linear-gradient(100deg, #e8a04a, #d9653b);
  color: #fff;
  font-size: 11px;
  font-style: normal;
  font-weight: 700;
}
.tip-enter-active, .tip-leave-active { transition: opacity 0.2s ease, transform 0.25s var(--ease-out); }
.tip-enter-from, .tip-leave-to { opacity: 0; transform: translate(-50%, calc(-100% + 6px)); }

/* ---------- Центр ---------- */
.center {
  position: relative;
  z-index: 5;
  max-width: 880px;
  text-align: center;
  pointer-events: none;
}
.center > * { pointer-events: auto; }
.center > .halo { pointer-events: none; }
.halo {
  position: absolute;
  z-index: -1;
  inset: -60px -120px;
  background: radial-gradient(ellipse 50% 50% at 50% 50%, rgba(246, 243, 236, 0.92) 35%, rgba(246, 243, 236, 0) 100%);
}
.title {
  margin: 0 0 22px;
  font-size: clamp(2.6rem, 6.4vw, 5.6rem);
  line-height: 0.98;
  font-weight: 680;
  letter-spacing: -0.055em;
}
.line { display: block; }
.word {
  display: inline-block;
  margin: 0 0.12em;
  animation: word-in 1.1s var(--ease-out) both;
  animation-delay: calc(var(--i) * 90ms + 100ms);
}
.word.grad-text {
  padding-bottom: 0.08em;
  animation: word-in 1.1s var(--ease-out) both, grad-pan 8s ease-in-out 1.2s infinite alternate;
  animation-delay: calc(var(--i) * 90ms + 100ms), 1.2s;
}
@keyframes word-in {
  from { opacity: 0; transform: translateY(0.45em) rotateX(-40deg); filter: blur(10px); }
  to { opacity: 1; transform: none; filter: none; }
}
.hero-in { animation: fade-up 1s var(--ease-out) both; animation-delay: calc(var(--i) * 90ms + 150ms); }
@keyframes fade-up {
  from { opacity: 0; transform: translateY(16px); filter: blur(6px); }
  to { opacity: 1; transform: none; filter: none; }
}
.lead {
  margin: 0 auto 32px;
  max-width: 40rem;
  color: var(--muted-2);
  font-size: clamp(1.02rem, 1.5vw, 1.2rem);
  line-height: 1.55;
  text-wrap: balance;
}
.form-wrap { margin: 0 auto; max-width: 540px; }
.meta {
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px 22px;
  margin: 20px 0 0;
  padding: 0;
  color: var(--muted-2);
  font-size: 14px;
}
.meta li { display: inline-flex; align-items: center; gap: 7px; }
.meta svg { color: #3f9b6f; }
.proof {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  margin-top: 26px;
  padding: 6px 16px 6px 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  font-size: 14px;
  color: var(--muted-2);
}
.avatars { display: inline-flex; }
.avatars span {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  margin-left: -8px;
  border-radius: 50%;
  border: 2px solid #fff;
  color: #fff;
  font-size: 10.5px;
  font-weight: 700;
}
.avatars span:first-child { margin-left: 0; }
.stars { color: #e8a04a; letter-spacing: 1px; margin-right: 6px; }
.proof b { color: var(--text); }

.scroll-cue {
  position: absolute;
  left: 50%;
  bottom: 26px;
  transform: translateX(-50%);
  opacity: 0.55;
  transition: opacity 0.2s ease;
}
.scroll-cue:hover { opacity: 1; }
.mouse {
  display: block;
  width: 24px;
  height: 38px;
  border: 1.5px solid var(--muted);
  border-radius: 14px;
  position: relative;
}
.mouse span {
  position: absolute;
  left: 50%;
  top: 7px;
  width: 3px;
  height: 7px;
  margin-left: -1.5px;
  border-radius: 2px;
  background: var(--muted);
  animation: wheel 1.8s ease-in-out infinite;
}
@keyframes wheel { 0% { opacity: 0; transform: translateY(-2px); } 40% { opacity: 1; } 100% { opacity: 0; transform: translateY(10px); } }

/* ---------- Адаптив ---------- */
@media (max-width: 1100px) {
  .planet-name { font-size: 14px; }
}
@media (max-width: 760px) {
  .orbit-hero {
    min-height: 0;
    display: flex;
    flex-direction: column;
    padding: 64px 16px 56px;
  }
  /* На телефоне орбита — отдельная «солнечная система» над заголовком */
  .stage {
    position: relative;
    inset: auto;
    width: calc(100% + 32px);
    height: 300px;
    margin: 0 -16px 4px;
    z-index: 0;
  }
  .core {
    position: absolute;
    left: 50%;
    top: 50%;
    display: grid;
    place-items: center;
    width: 76px;
    height: 76px;
    transform: translate(-50%, -50%);
    border-radius: 22px;
    background: #fff;
    box-shadow: var(--shadow-lg);
  }
  .core img { width: 48px; height: 48px; border-radius: 12px; }
  .core-glow {
    position: absolute;
    inset: -30px;
    z-index: -1;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(232, 160, 74, 0.45), transparent 65%);
    animation: pulse 3.5s ease-in-out infinite;
  }
  @keyframes pulse { 50% { transform: scale(1.15); opacity: 0.6; } }
  .planet { padding: 5px 12px 5px 5px; gap: 7px; }
  .planet-logo { width: 28px; height: 28px; }
  .planet-name { font-size: 13px; }
  .planet.kind-app { display: none; }
  .halo { display: none; }
  .title { font-size: clamp(2.3rem, 11vw, 3.2rem); }
  .lead { margin-bottom: 24px; font-size: 1rem; }
  .meta { flex-direction: column; align-items: center; gap: 6px; font-size: 13.5px; }
  .proof { font-size: 12.5px; text-align: left; }
  .scroll-cue { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .aurora, .ring-1, .word, .hero-in, .core-glow { animation: none !important; }
}
</style>
