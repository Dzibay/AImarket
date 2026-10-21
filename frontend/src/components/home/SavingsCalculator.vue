<template>
  <section id="savings" class="calc-section container">
    <div class="head">
      <p v-reveal class="kicker">Калькулятор экономии</p>
      <h2 v-reveal="80" class="section-title">Посчитайте, сколько<br>вы <span class="grad-text">переплачиваете</span></h2>
      <p v-reveal="160" class="section-lead">
        Двигайте ползунок: сколько вы тратите или готовы тратить на ИИ по официальным ценам в месяц.
      </p>
    </div>

    <div v-reveal="120" class="calc">
      <div class="calc-left">
        <div class="spend">
          <span class="spend-label">Бюджет по официальным ценам</span>
          <b class="spend-value">{{ usd(spendUsd, 0) }}<small>/мес</small></b>
        </div>

        <div class="slider" :style="{ '--p': `${sliderPct}%` }">
          <input
            v-model.number="pos"
            type="range"
            min="0"
            max="1000"
            step="1"
            aria-label="Бюджет в долларах в месяц"
          >
          <div class="ticks" aria-hidden="true">
            <button v-for="tick in ticks" :key="tick" type="button" tabindex="-1" @click="setSpend(tick)">{{ usd(tick, 0) }}</button>
          </div>
        </div>

        <div class="bars">
          <div class="bar-row">
            <div class="bar-meta">
              <span>Напрямую у OpenAI, Anthropic, Google</span>
              <b class="was">{{ rub(display.was, 0) }}</b>
            </div>
            <div class="bar"><span class="fill fill-was" style="width: 100%"></span></div>
          </div>
          <div class="bar-row">
            <div class="bar-meta">
              <span>В Aimarket — те же модели</span>
              <b>{{ rub(display.now, 0) }}</b>
            </div>
            <div class="bar"><span class="fill fill-now" :style="{ width: '10%' }"></span></div>
          </div>
        </div>

        <div class="models">
          <span class="models-label">Это примерно</span>
          <div class="model-tabs" role="tablist" aria-label="Модель">
            <button
              v-for="m in models"
              :key="m.id"
              type="button"
              role="tab"
              :aria-selected="model === m.id"
              :class="{ on: model === m.id }"
              @click="model = m.id"
            >
              <BrandLogo :brand="m.brand" :size="16" />{{ m.name }}
            </button>
          </div>
          <p class="models-note">
            <b>{{ tokensLabel }}</b> токенов {{ currentModel.name }} в месяц — около
            <b>{{ sessionsLabel }}</b> сессий агентного кодинга.
          </p>
        </div>
      </div>

      <div class="calc-right">
        <div class="save-card">
          <span class="save-label">Ваша экономия за год</span>
          <b class="save-value">{{ rub(display.year, 0) }}</b>
          <span class="save-sub">или {{ rub(display.month, 0) }} каждый месяц</span>
          <div class="save-pill">−90% к счёту</div>
          <div class="save-cta">
            <SignupForm size="md" source="calculator" cta="Начать экономить" />
          </div>
          <p class="save-fine">Курс пополнения: 1 $ = {{ rub(rateValue) }}. Без подписок и скрытых комиссий.</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import BrandLogo from '../BrandLogo.vue'
import SignupForm from './SignupForm.vue'
import { findModel } from '../../data/tokenPrices'
import { rub, usd } from '../../utils/format'

const props = defineProps({
  rate: { type: Number, default: 0 },
})

const MIN = 10
const MAX = 3000
const ticks = [10, 50, 200, 1000, 3000]
// Логарифмическая шкала: маленькие суммы двигаются точно, большие — быстро.
const pos = ref(toPos(200))
function toPos(value) {
  return Math.round((Math.log(value / MIN) / Math.log(MAX / MIN)) * 1000)
}
function fromPos(p) {
  const raw = MIN * Math.pow(MAX / MIN, p / 1000)
  const step = raw < 100 ? 5 : raw < 1000 ? 10 : 50
  return Math.round(raw / step) * step
}
function setSpend(value) {
  pos.value = toPos(value)
}
const spendUsd = computed(() => fromPos(pos.value))
const sliderPct = computed(() => pos.value / 10)

const rateValue = computed(() => props.rate || 10)
const was = computed(() => spendUsd.value * rateValue.value * 10)
const now = computed(() => spendUsd.value * rateValue.value)

const models = [
  { id: 'claude-opus-5-5', name: 'Claude Opus 5.5', brand: 'claude' },
  { id: 'gpt-6-astra', name: 'GPT-6 Astra', brand: 'gpt' },
  { id: 'gemini-3.1-pro-preview', name: 'Gemini 3.1 Pro', brand: 'gemini' },
  { id: 'deepseek-v4-pro', name: 'DeepSeek V4 Pro', brand: 'deepseek' },
]
const model = ref(models[0].id)
const currentModel = computed(() => models.find((m) => m.id === model.value))
// Смесь 80% вход / 20% выход — типично для агентов, которые много читают код.
const tokensPerMonth = computed(() => {
  const m = findModel(model.value)
  if (!m) return 0
  const blended = m.input * 0.8 + m.output * 0.2
  return (spendUsd.value / blended) * 1e6
})
const tokensLabel = computed(() => {
  const t = tokensPerMonth.value
  if (t >= 1e9) return `${(t / 1e9).toLocaleString('ru-RU', { maximumFractionDigits: 1 })} млрд`
  return `${Math.round(t / 1e6).toLocaleString('ru-RU')} млн`
})
// Одна агентная сессия ≈ 400 тыс. токенов.
const sessionsLabel = computed(() => Math.max(1, Math.round(tokensPerMonth.value / 4e5)).toLocaleString('ru-RU'))

// Плавная «прокрутка» чисел к новым значениям.
const display = reactive({ was: 0, now: 0, month: 0, year: 0 })
let raf = 0
function tweenTo() {
  cancelAnimationFrame(raf)
  const from = { ...display }
  const to = { was: was.value, now: now.value, month: was.value - now.value, year: (was.value - now.value) * 12 }
  const start = performance.now()
  const tick = (t) => {
    const p = Math.min(1, (t - start) / 450)
    const e = 1 - Math.pow(1 - p, 3)
    for (const key of Object.keys(to)) display[key] = from[key] + (to[key] - from[key]) * e
    if (p < 1) raf = requestAnimationFrame(tick)
  }
  raf = requestAnimationFrame(tick)
}
watch([was, now], tweenTo, { immediate: true })
onBeforeUnmount(() => cancelAnimationFrame(raf))
</script>

<style scoped>
.calc-section { padding-top: 120px; padding-bottom: 120px; scroll-margin-top: 80px; }
.head { text-align: center; display: flex; flex-direction: column; align-items: center; margin-bottom: 48px; }
.head .section-lead { margin: 0 auto; }

.calc {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
  gap: 12px;
  padding: 12px;
  border-radius: 36px;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.9);
  box-shadow: var(--shadow-lg);
  backdrop-filter: blur(16px);
}
.calc-left { padding: 28px 28px 24px; }
.spend { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.spend-label { color: var(--muted); font-size: 14px; font-weight: 600; }
.spend-value {
  font-size: clamp(2.4rem, 5vw, 3.6rem);
  font-weight: 680;
  letter-spacing: -0.05em;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.spend-value small { font-size: 0.4em; color: var(--muted); font-weight: 500; letter-spacing: -0.01em; margin-left: 4px; }

.slider { margin: 26px 0 34px; }
.slider input {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 10px;
  border-radius: 999px;
  background: linear-gradient(90deg, #e8a04a, #d9653b var(--p), rgba(28, 25, 21, 0.08) var(--p));
  outline: none;
  cursor: pointer;
}
.slider input::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #fff;
  border: 0;
  box-shadow: 0 0 0 6px rgba(217, 101, 59, 0.16), 0 6px 16px rgba(40, 28, 12, 0.3);
  transition: transform 0.2s var(--ease-out);
}
.slider input::-webkit-slider-thumb:hover { transform: scale(1.12); }
.slider input::-moz-range-thumb {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #fff;
  border: 0;
  box-shadow: 0 0 0 6px rgba(217, 101, 59, 0.16), 0 6px 16px rgba(40, 28, 12, 0.3);
}
.slider input:focus-visible::-webkit-slider-thumb { box-shadow: 0 0 0 6px rgba(217, 101, 59, 0.35), 0 6px 16px rgba(40, 28, 12, 0.3); }
.ticks { display: flex; justify-content: space-between; margin-top: 12px; }
.ticks button {
  border: 0;
  background: none;
  padding: 2px 0;
  color: var(--muted);
  font: inherit;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
}
.ticks button:hover { color: var(--text); }

.bars { display: grid; gap: 18px; }
.bar-meta { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; margin-bottom: 8px; }
.bar-meta span { color: var(--muted-2); font-size: 14px; }
.bar-meta b { font-size: 1.35rem; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; white-space: nowrap; }
.bar-meta b.was { color: var(--muted); text-decoration: line-through; text-decoration-thickness: 2px; text-decoration-color: rgba(217, 101, 59, 0.6); }
.bar { height: 14px; border-radius: 999px; background: rgba(28, 25, 21, 0.06); overflow: hidden; }
.fill { display: block; height: 100%; border-radius: inherit; }
.fill-was { background: repeating-linear-gradient(-45deg, #cfc6b8 0 8px, #ddd5c8 8px 16px); }
.fill-now { background: var(--grad); min-width: 30px; box-shadow: 0 0 18px rgba(232, 160, 74, 0.6); }

.models { margin-top: 32px; padding-top: 22px; border-top: 1px solid var(--border); }
.models-label { display: block; margin-bottom: 10px; color: var(--muted); font-size: 13px; font-weight: 600; }
.model-tabs { display: flex; flex-wrap: wrap; gap: 6px; }
.model-tabs button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 12px;
  border-radius: 999px;
  border: 1px solid var(--border-strong);
  background: rgba(255, 255, 255, 0.7);
  color: var(--text);
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease, border-color 0.2s ease;
}
.model-tabs button.on { background: var(--ink); color: #fff; border-color: var(--ink); }
.model-tabs button.on :deep(svg) { color: #fff; }
.models-note { margin: 14px 0 0; color: var(--muted-2); font-size: 15px; line-height: 1.5; }
.models-note b { color: var(--text); }

.calc-right { display: flex; }
.save-card {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 36px 32px;
  border-radius: 26px;
  background:
    radial-gradient(120% 80% at 100% 0%, rgba(176, 123, 224, 0.28), transparent 60%),
    radial-gradient(120% 90% at 0% 100%, rgba(232, 160, 74, 0.32), transparent 60%),
    linear-gradient(180deg, #1d1915, #14110d);
  color: #f6f1e8;
  overflow: hidden;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1);
}
.save-label { font-size: 13px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: rgba(246, 241, 232, 0.6); }
.save-value {
  margin: 10px 0 6px;
  font-size: clamp(2.6rem, 5vw, 4rem);
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.055em;
  font-variant-numeric: tabular-nums;
  background: linear-gradient(100deg, #ffe1a8, #f0a477 45%, #d7b8ff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.save-sub { color: rgba(246, 241, 232, 0.7); font-size: 15px; }
.save-pill {
  position: absolute;
  top: 24px;
  right: 24px;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.14);
  font-size: 12px;
  font-weight: 700;
}
.save-cta { margin-top: 28px; }
.save-cta :deep(.signup-form) { background: rgba(255, 255, 255, 0.96); }
.save-cta :deep(.go) { background: var(--grad); background-size: 140% 100%; }
.save-cta :deep(.signup-done) { color: var(--text); }
.save-fine { margin: 14px 0 0; color: rgba(246, 241, 232, 0.5); font-size: 12.5px; }

@media (max-width: 960px) {
  .calc { grid-template-columns: 1fr; border-radius: 28px; }
  .calc-left { padding: 20px 14px 10px; }
  .calc-section { padding-top: 80px; padding-bottom: 80px; }
}
@media (max-width: 560px) {
  .save-card { padding: 28px 20px; }
  .save-pill { position: static; align-self: flex-start; margin-top: 14px; }
  .bar-meta { flex-direction: column; gap: 2px; }
  .ticks button { font-size: 11px; }
}
</style>
