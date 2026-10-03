<template>
  <section class="models-hero" aria-labelledby="models-hero-title">
    <div class="glow glow-a" aria-hidden="true"></div>
    <div class="glow glow-b" aria-hidden="true"></div>
    <div class="glow glow-c" aria-hidden="true"></div>

    <div class="container head">
      <p class="eyebrow">Доступ к лучшим AI моделям</p>
      <h1 id="models-hero-title">Все ведущие ИИ со скидкой 90%</h1>
      <p class="lead">
        Подключайте и используйте топовые модели — от ChatGPT до Claude.
        <br class="br-wide">
        Гибкие тарифы, простая оплата, мгновенный доступ.
      </p>
    </div>

    <p class="sr-only" aria-live="polite">{{ liveMessage }}</p>

    <div
      class="stage-wrap"
      role="region"
      aria-roledescription="карусель"
      aria-label="Семейства моделей"
      tabindex="0"
      @keydown.left.prevent="prev"
      @keydown.right.prevent="next"
    >
      <div
        class="stage"
        @pointerdown="onPointerDown"
        @pointerup="onPointerUp"
        @pointercancel="onPointerCancel"
      >
        <article
          v-for="(family, i) in families"
          :key="family.id"
          class="card"
          :class="{ 'is-active': i === active }"
          :style="cardStyle(i)"
          :data-depth="Math.abs(offsetOf(i))"
          :data-side="offsetOf(i) > 0 ? 'right' : 'left'"
          :aria-hidden="i !== active"
          @click="onCardClick(i)"
        >
          <div class="card-main">
            <div class="card-top">
              <div class="brand">
                <span class="brand-logo"><BrandLogo :brand="family.id" :size="family.id === 'claude' ? 50 : 46" /></span>
                <span class="brand-text">
                  <span class="brand-name" :class="{ long: family.name.length > 8 }">{{ family.name }}</span>
                  <span class="brand-vendor">{{ family.vendor }}</span>
                </span>
              </div>

              <ul class="featured">
                <li v-for="model in family.featured" :key="model.name">
                  <span class="mini"><BrandLogo :brand="family.id" :size="15" /></span>
                  <span class="model" :title="model.name">{{ model.name }}</span>
                  <span class="tag">{{ model.tag }}</span>
                </li>
              </ul>
            </div>

            <div class="card-mid">
              <p class="desc">{{ family.description }}</p>
              <button type="button" class="btn choose" @click.stop="choose(family)">
                Выбрать <span class="arrow-glyph" aria-hidden="true">→</span>
              </button>
            </div>

            <div class="all">
              <span class="all-label">Все модели семейства · {{ family.models.length }}</span>
              <ul class="chips">
                <li v-for="model in family.models" :key="model">{{ model }}</li>
              </ul>
            </div>
          </div>
        </article>
      </div>
    </div>

    <div class="controls">
      <button type="button" class="nav-btn" aria-label="Предыдущее семейство" @click="prev">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 6l-6 6 6 6" /></svg>
      </button>
      <div class="dots" role="tablist" aria-label="Выбор семейства">
        <button
          v-for="(family, i) in families"
          :key="family.id"
          type="button"
          class="dot"
          :class="{ active: i === active }"
          role="tab"
          :aria-selected="i === active"
          :aria-label="family.name"
          @click="go(i)"
        />
      </div>
      <button type="button" class="nav-btn" aria-label="Следующее семейство" @click="next">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6" /></svg>
      </button>
    </div>

    <div class="container">
      <ul class="perks">
        <li>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z" /></svg>
          <span class="perk-text"><b>Мгновенный доступ</b><span>После оплаты</span></span>
        </li>
        <li>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l7 3v6c0 4.5-3 7.8-7 9-4-1.2-7-4.5-7-9V6l7-3z" /></svg>
          <span class="perk-text"><b>Безопасная оплата</b><span>Любой картой</span></span>
        </li>
        <li>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3.5l2.6 5.4 5.9.8-4.3 4.1 1.1 5.9L12 16.9l-5.3 2.8 1.1-5.9-4.3-4.1 5.9-.8L12 3.5z" /></svg>
          <span class="perk-text"><b>Гибкие тарифы</b><span>Под любые задачи</span></span>
        </li>
        <li>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 13a8 8 0 0 1 16 0" /><rect x="3" y="13" width="4" height="6" rx="1.5" /><rect x="17" y="13" width="4" height="6" rx="1.5" /><path d="M19 19v1a2 2 0 0 1-2 2h-4" /></svg>
          <span class="perk-text"><b>Поддержка 24/7</b><span>Всегда на связи</span></span>
        </li>
      </ul>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import BrandLogo from './BrandLogo.vue'

const emit = defineEmits(['choose'])

// Порядок подобран под макет: слева GPT, в центре Claude, справа Grok и DeepSeek.
const families = [
  {
    id: 'gemini',
    name: 'Gemini',
    vendor: 'Google',
    description:
      'Gemini — мультимодальные модели Google с огромным контекстом. Flash-версии отвечают почти мгновенно, Pro — для сложных задач.',
    featured: [
      { name: 'gemini-3.1-pro-preview', tag: 'Самая мощная' },
      { name: 'gemini-3.8-flash', tag: 'Быстрая' },
      { name: 'gemini-3.7-flash', tag: 'Стабильная' },
    ],
    models: [
      'gemini-3.1-pro-preview',
      'gemini-3.5-flash',
      'gemini-3.6-flash',
      'gemini-3.7-flash',
      'gemini-3.8-flash',
    ],
  },
  {
    id: 'gpt',
    name: 'GPT',
    vendor: 'OpenAI',
    description:
      'GPT — универсальные модели OpenAI для текста, кода и агентов. Линейка gpt-image генерирует и редактирует изображения.',
    featured: [
      { name: 'gpt-6.1-sol', tag: 'Самая мощная' },
      { name: 'gpt-5.5', tag: 'Лучший баланс' },
      { name: 'gpt-5.4-mini', tag: 'Быстрая' },
      { name: 'gpt-image-2.5', tag: 'Изображения' },
    ],
    models: [
      'gpt-5.4',
      'gpt-5.4-mini',
      'gpt-5.5',
      'gpt-5.6-luna',
      'gpt-5.6-sol',
      'gpt-5.6-terra',
      'gpt-6-astra',
      'gpt-6-luna',
      'gpt-6-sol',
      'gpt-6.1-sol',
      'gpt-image-2',
      'gpt-image-2.5',
      'gpt-image-2.5-flare',
      'gpt-image-2.5-sunburst',
    ],
  },
  {
    id: 'claude',
    name: 'Claude',
    vendor: 'Anthropic',
    description:
      'Claude — безопасный, надёжный и интеллектуальный ИИ, который отлично справляется с анализом, письмом и кодом.',
    featured: [
      { name: 'claude-sonnet-5-5', tag: 'Лучший баланс' },
      { name: 'claude-opus-5-5', tag: 'Самая мощная' },
      { name: 'claude-haiku-4-5', tag: 'Быстрая' },
      { name: 'claude-fable-5-1', tag: 'Новая' },
    ],
    models: [
      'claude-fable-5',
      'claude-fable-5-1',
      'claude-haiku-4-5',
      'claude-opus-4-7',
      'claude-opus-4-8',
      'claude-opus-5',
      'claude-opus-5-5',
      'claude-sonnet-4-6',
      'claude-sonnet-5',
      'claude-sonnet-5-5',
    ],
  },
  {
    id: 'grok',
    name: 'Grok',
    vendor: 'xAI',
    description:
      'Grok — модели xAI с актуальными знаниями и свободным стилем ответов. Хороши для исследований, поиска и кода.',
    featured: [
      { name: 'grok-4.7', tag: 'Самая мощная' },
      { name: 'grok-4.6', tag: 'Лучший баланс' },
      { name: 'grok-4.5', tag: 'Быстрая' },
    ],
    models: ['grok-4.5', 'grok-4.6', 'grok-4.7'],
  },
  {
    id: 'deepseek',
    name: 'DeepSeek',
    vendor: 'DeepSeek',
    description:
      'DeepSeek — открытые модели с отличным соотношением цены и качества. Pro — для рассуждений, Flash — для скорости.',
    featured: [
      { name: 'deepseek-v4-pro', tag: 'Самая мощная' },
      { name: 'deepseek-v4.1-flash', tag: 'Быстрая' },
      { name: 'deepseek-v4-flash-vision-exp', tag: 'Vision' },
    ],
    models: [
      'deepseek-v4-flash',
      'deepseek-v4-flash-0731',
      'deepseek-v4-flash-vision-exp',
      'deepseek-v4-pro',
      'deepseek-v4-pro-0813',
      'deepseek-v4.1-flash',
    ],
  },
  {
    id: 'china',
    name: 'Kimi · Qwen',
    vendor: 'GLM, MiniMax и другие',
    description:
      'Сильные китайские модели: Kimi для кода и агентов, Qwen и GLM — универсальные, Hunyuan и MiniMax — для длинного контекста.',
    featured: [
      { name: 'kimi-k3', tag: 'Новая' },
      { name: 'qwen3.8-max', tag: 'Самая мощная' },
      { name: 'glm-5.3-flash', tag: 'Быстрая' },
      { name: 'minimax-m3', tag: 'Длинный контекст' },
    ],
    models: [
      'kimi-k2.6',
      'kimi-k2.7-code',
      'kimi-k2.7-code-highspeed',
      'kimi-k3',
      'qwen3.8-flash',
      'qwen3.8-max',
      'glm-5.1',
      'glm-5.2',
      'glm-5.3',
      'glm-5.3-flash',
      'hy3',
      'hy4',
      'minimax-m3',
      'mimo-v2.5-pro',
    ],
  },
]

const count = families.length
const active = ref(families.findIndex((f) => f.id === 'claude'))
const liveMessage = computed(() => {
  const family = families[active.value]
  return family ? `Семейство ${family.name}, ${active.value + 1} из ${count}` : ''
})

// Смещение карточки относительно активной по кольцу: -3..3 для шести карточек.
function offsetOf(i) {
  let d = i - active.value
  if (d > count / 2) d -= count
  if (d < -count / 2) d += count
  return d
}

// Сдвиг по X (в % ширины карточки), глубина и поворот для соседей 0, ±1, ±2, скрытых.
const X = [0, 75, 162, 220]
const Z = [0, -300, -620, -900]
const R = [0, 48, 52, 55]
const OPACITY = [1, 0.95, 0.85, 0]

function cardStyle(i) {
  const d = offsetOf(i)
  const a = Math.min(Math.abs(d), 3)
  const s = Math.sign(d)
  const hidden = a > 2
  return {
    '--x': `${s * X[a]}%`,
    '--z': `${Z[a]}px`,
    '--r': `${-s * R[a]}deg`,
    opacity: OPACITY[a],
    zIndex: 10 - a,
    pointerEvents: hidden ? 'none' : 'auto',
  }
}

function go(i) {
  active.value = ((i % count) + count) % count
}
function next() {
  go(active.value + 1)
}
function prev() {
  go(active.value - 1)
}
function choose(family) {
  emit('choose', family)
}

// Клик по боковой карточке переключает на неё; свайп — листает.
let pointerStartX = null
let swiped = false
function onPointerDown(e) {
  pointerStartX = e.clientX
  swiped = false
}
function onPointerUp(e) {
  if (pointerStartX === null) return
  const dx = e.clientX - pointerStartX
  pointerStartX = null
  if (Math.abs(dx) > 40) {
    swiped = true
    dx < 0 ? next() : prev()
  }
}
function onPointerCancel() {
  pointerStartX = null
}
function onCardClick(i) {
  if (swiped) {
    swiped = false
    return
  }
  if (i !== active.value) go(i)
}
</script>

<style scoped>
.models-hero {
  position: relative;
  overflow-x: clip;
  padding: 36px 0 0;
  isolation: isolate;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* Мягкие световые пятна фона */
.glow {
  position: absolute;
  z-index: -1;
  border-radius: 50%;
  pointer-events: none;
  filter: blur(70px);
}
.glow-a { left: -220px; top: 120px; width: 760px; height: 460px; background: rgba(255, 255, 255, 0.9); }
.glow-b { right: -240px; top: 40px; width: 820px; height: 500px; background: rgba(255, 255, 255, 0.8); }
.glow-c { left: 50%; top: 430px; width: 1000px; height: 320px; transform: translateX(-50%); background: rgba(226, 213, 194, 0.55); }

.head { text-align: center; }
.eyebrow {
  margin: 0 0 10px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--muted);
}
h1 {
  margin: 0 0 14px;
  font-size: clamp(2.1rem, 4.6vw, 3.3rem);
  line-height: 1.08;
  font-weight: 600;
  letter-spacing: -0.035em;
}
.lead {
  margin: 0 auto;
  max-width: 42rem;
  color: var(--muted-2);
  font-size: 1.05rem;
  line-height: 1.5;
}

/* ---- 3D-сцена ---- */
.stage-wrap {
  --card-w: 540px;
  --card-h: 400px;
  --featured-min: 116px;
  --desc-min: 62px;
  --kx: 1;
  --kz: 1;
  margin-top: 44px;
  overflow-x: clip;
  perspective: 2400px;
  perspective-origin: 50% 42%;
  outline: none;
  user-select: none;
  -webkit-user-select: none;
  touch-action: pan-x pinch-zoom;
}
.stage-wrap:focus-visible .card.is-active {
  box-shadow: 0 40px 90px rgba(28, 25, 21, 0.18), 0 0 0 3px rgba(28, 25, 21, 0.12);
}
.stage {
  position: relative;
  transform-style: preserve-3d;
  height: var(--card-h);
}
.card {
  position: absolute;
  top: 0;
  left: 50%;
  width: var(--card-w);
  height: var(--card-h);
  margin-left: calc(var(--card-w) / -2);
  padding: 24px 26px;
  border-radius: 26px;
  background: linear-gradient(150deg, #ffffff 0%, #fcfaf5 50%, #f2ede4 100%);
  border: 1px solid rgba(255, 255, 255, 0.95);
  box-shadow: 0 30px 70px rgba(28, 25, 21, 0.14), inset 0 1px 0 rgba(255, 255, 255, 0.9);
  transform: translateX(calc(var(--x) * var(--kx))) translateZ(calc(var(--z) * var(--kz))) rotateY(var(--r));
  transition: transform 0.65s cubic-bezier(0.22, 0.61, 0.36, 1), opacity 0.5s ease, box-shadow 0.4s ease;
  backface-visibility: hidden;
  will-change: transform, opacity;
  cursor: pointer;
  box-sizing: border-box;
  overflow: hidden;
}
/* Активная карточка — в потоке, фиксированная высота как у остальных */
.card.is-active {
  position: relative;
  cursor: default;
  box-shadow: 0 40px 90px rgba(28, 25, 21, 0.18), inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.card-main {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  min-height: var(--featured-min);
}
.card-mid {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  min-height: var(--desc-min);
}
.brand {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}
.brand-logo {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  width: 56px;
  height: 56px;
  color: var(--text);
}
.brand-text { display: flex; flex-direction: column; min-width: 0; }
.brand-name {
  font-size: 2.4rem;
  font-weight: 600;
  line-height: 1;
  letter-spacing: -0.04em;
}
.brand-name.long { font-size: 1.75rem; line-height: 1.05; }
.brand-vendor { margin-top: 6px; font-size: 13px; color: var(--muted); }

.featured {
  flex: 0 1 auto;
  max-width: 58%;
  min-width: 0;
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  align-content: start;
  gap: 9px;
}
.featured li {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px 10px;
}
.mini {
  display: grid;
  place-items: center;
  width: 18px;
  height: 18px;
  color: var(--text);
  flex: 0 0 auto;
}
.model {
  font: 600 13px/1.2 ui-monospace, SFMono-Regular, Consolas, monospace;
  letter-spacing: -0.01em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}
.tag {
  padding: 3px 9px;
  border-radius: 999px;
  background: #f1e8da;
  color: #6b5a44;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.3;
}

.desc {
  flex: 1 1 auto;
  min-width: 0;
  margin: 0;
  padding-right: 8px;
  font-size: 13.5px;
  line-height: 1.5;
  color: var(--muted-2);
}
.choose {
  flex: 0 0 auto;
  min-height: 46px;
  padding: 0 22px;
  font-size: 15px;
}
.arrow-glyph { font-size: 17px; line-height: 1; }

.all {
  flex: 0 0 auto;
  margin-top: auto;
  display: flex;
  flex-direction: column;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}
.all-label {
  display: block;
  margin-bottom: 7px;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}
.chips {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 6px;
  max-height: 84px;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: thin;
}
.chips li {
  padding: 2px 7px;
  border-radius: 7px;
  border: 1px solid var(--border);
  background: rgba(28, 25, 21, 0.04);
  color: var(--muted-2);
  font: 500 11px/1.4 ui-monospace, SFMono-Regular, Consolas, monospace;
}

/* Боковые карточки: только логотип и короткий список, контент приглушён */
.card:not(.is-active) .card-main {
  gap: 22px;
  opacity: 0.55;
}
.card:not(.is-active) .card-top {
  flex-direction: column;
  min-height: 0;
  gap: 22px;
}
.card:not(.is-active) .card-mid,
.card:not(.is-active) .all { display: none; }
.card:not(.is-active) .featured { max-width: 100%; gap: 14px; }
/* Карточки справа прижимают контент к внешнему краю — он не прячется под центральной */
.card[data-side="right"]:not(.is-active) .card-top { align-items: flex-end; text-align: right; }
.card[data-side="right"]:not(.is-active) .brand { flex-direction: row-reverse; }
.card[data-side="right"]:not(.is-active) .featured li { direction: rtl; }

/* ---- Управление ---- */
.controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 28px;
  margin-top: 30px;
}
.nav-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid var(--border-strong);
  background: rgba(255, 255, 255, 0.7);
  color: var(--text);
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: background 0.15s ease, transform 0.15s ease;
}
.nav-btn:hover { background: #fff; transform: translateY(-1px); }
.dots { display: flex; align-items: center; gap: 8px; }
.dot {
  width: 8px;
  height: 8px;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: rgba(28, 25, 21, 0.18);
  cursor: pointer;
  transition: width 0.3s ease, background 0.3s ease;
}
.dot.active { width: 26px; background: var(--text); }

/* ---- Преимущества ---- */
.perks {
  list-style: none;
  margin: 44px 0 0;
  padding: 26px 0 40px;
  border-top: 1px solid var(--border);
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.perks li {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 4px 12px;
  color: var(--text);
}
.perks li + li { border-left: 1px solid var(--border); }
.perks svg { flex: 0 0 auto; }
.perk-text { display: flex; flex-direction: column; gap: 2px; }
.perk-text b { font-size: 13px; letter-spacing: -0.01em; }
.perk-text span { font-size: 12px; color: var(--muted); }

/* ---- Адаптив ---- */
@media (max-width: 1100px) {
  .stage-wrap {
    --card-w: 500px;
    --card-h: 390px;
  }
}
@media (max-width: 900px) {
  .perks { grid-template-columns: repeat(2, minmax(0, 1fr)); row-gap: 14px; }
  .perks li:nth-child(3) { border-left: 0; }
}
@media (max-width: 760px) {
  .br-wide { display: none; }
  .stage-wrap {
    --card-w: min(calc(100vw - 48px), 420px);
    --card-h: auto;
    --featured-min: 0;
    --desc-min: 0;
    margin-top: 32px;
    perspective: none;
    overflow-x: clip;
    padding: 0 24px;
  }
  .stage {
    transform-style: flat;
    width: 100%;
    max-width: var(--card-w);
    height: auto;
    margin: 0 auto;
  }
  .card {
    position: relative;
    top: auto;
    left: auto;
    margin-left: 0;
    width: 100%;
    padding: 22px 20px;
    border-radius: 22px;
    height: auto;
    min-height: 0;
    overflow: visible;
    transform: none !important;
    opacity: 1 !important;
    pointer-events: auto !important;
    cursor: default;
  }
  /* На телефоне — одна карточка по центру, без 3D */
  .card:not(.is-active) {
    display: none;
  }
  .card.is-active {
    box-shadow: 0 24px 60px rgba(28, 25, 21, 0.14);
  }
  .card.is-active .card-main {
    height: auto;
    gap: 16px;
    opacity: 1;
  }
  .card.is-active .card-top,
  .card.is-active .card-mid {
    flex-direction: column;
    align-items: stretch;
    min-height: 0;
    gap: 16px;
  }
  .card.is-active .featured { max-width: none; }
  .card.is-active .desc { padding-right: 0; }
  .card.is-active .choose { width: 100%; }
  .brand-name { font-size: 2rem; }
  .brand-logo { width: 46px; height: 46px; }
  .featured li {
    display: grid;
    grid-template-columns: 18px minmax(0, 1fr) auto;
    align-items: center;
    gap: 8px 10px;
    white-space: normal;
  }
  .model {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .tag { justify-self: start; }
  .chips {
    flex: none;
    max-height: 120px;
    overflow-y: auto;
  }
  .controls { margin-top: 22px; gap: 18px; }
  .perks { grid-template-columns: 1fr; margin-top: 32px; padding-bottom: 32px; }
  .perks li { justify-content: flex-start; padding: 6px 0; }
  .perks li + li { border-left: 0; }
}

@media (prefers-reduced-motion: reduce) {
  .card { transition: opacity 0.2s ease; }
  .dot { transition: none; }
}
</style>
