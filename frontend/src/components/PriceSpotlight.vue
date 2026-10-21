<template>
  <section id="prices" class="prices container">
    <div class="head">
      <p v-reveal class="kicker">Цены</p>
      <h2 v-reveal="80" class="section-title">Флагманы — <span class="grad-text">на 90% дешевле</span></h2>
      <p v-reveal="160" class="section-lead">
        Цена за 1 млн токенов в рублях при курсе пополнения {{ rateLabel }}/$. Зачёркнуто — сколько это стоит напрямую.
      </p>
    </div>

    <div class="grid">
      <article
        v-for="(item, i) in cards"
        :key="item.id"
        v-reveal="(i % 3) * 90"
        class="model"
        @pointermove="glow"
      >
        <header>
          <span class="logo"><BrandLogo :brand="item.brand" :size="22" /></span>
          <span class="blurb">{{ item.blurb }}</span>
          <span class="off">−90%</span>
        </header>
        <h3>{{ item.id }}</h3>
        <dl>
          <div>
            <dt>Вход</dt>
            <dd class="rub-pay">
              <b>{{ tokenRub(ourRubPerMillion(item.input, usdPriceRub)) }}</b>
              <s>{{ tokenRub(referenceRubPerMillion(item.input, usdPriceRub)) }}</s>
            </dd>
          </div>
          <div>
            <dt>Кэш</dt>
            <dd v-if="item.cache != null" class="rub-pay">
              <b>{{ tokenRub(ourRubPerMillion(item.cache, usdPriceRub)) }}</b>
              <s>{{ tokenRub(referenceRubPerMillion(item.cache, usdPriceRub)) }}</s>
            </dd>
            <dd v-else class="rub-pay muted">—</dd>
          </div>
          <div>
            <dt>Выход</dt>
            <dd class="rub-pay">
              <b>{{ tokenRub(ourRubPerMillion(item.output, usdPriceRub)) }}</b>
              <s>{{ tokenRub(referenceRubPerMillion(item.output, usdPriceRub)) }}</s>
            </dd>
          </div>
        </dl>
      </article>
    </div>

    <div class="more-wrap">
      <RouterLink to="/prices" class="more">
        Все цены — {{ count }} моделей
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14" /><path d="m13 6 6 6-6 6" /></svg>
      </RouterLink>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import BrandLogo from './BrandLogo.vue'
import {
  families,
  findModel,
  flagships,
  ourRubPerMillion,
  referenceRubPerMillion,
} from '../data/tokenPrices'
import { rub, tokenRub } from '../utils/format'

const props = defineProps({
  usdPriceRub: { type: Number, default: 0 },
})

const rateLabel = computed(() => (props.usdPriceRub > 0 ? rub(props.usdPriceRub) : '…'))

const count = families.reduce((sum, family) => sum + family.models.length, 0)
const cards = flagships.map((item) => {
  const model = findModel(item.id)
  return {
    ...item,
    brand: model.family.id === 'kimi' ? 'china' : model.family.id,
    input: model.input,
    cache: model.cache,
    output: model.output,
  }
})

// Подсветка карточки за курсором.
function glow(event) {
  const el = event.currentTarget
  const r = el.getBoundingClientRect()
  el.style.setProperty('--gx', `${event.clientX - r.left}px`)
  el.style.setProperty('--gy', `${event.clientY - r.top}px`)
}
</script>

<style scoped>
.prices { padding-top: 120px; padding-bottom: 60px; scroll-margin-top: 80px; }
.head { display: flex; flex-direction: column; align-items: center; text-align: center; margin-bottom: 48px; }
.head .section-lead { margin: 0 auto; }
.grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}
.model {
  --gx: 50%;
  --gy: 0%;
  position: relative;
  padding: 22px 22px 20px;
  border-radius: 26px;
  background:
    radial-gradient(260px circle at var(--gx) var(--gy), rgba(232, 160, 74, 0.16), transparent 70%),
    rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.95);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.9) inset, 0 18px 40px -24px rgba(60, 40, 15, 0.35);
  backdrop-filter: blur(12px);
  transition: transform 0.4s var(--ease-out), box-shadow 0.4s ease;
}
.model::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1px;
  background: radial-gradient(220px circle at var(--gx) var(--gy), rgba(217, 101, 59, 0.7), transparent 70%);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}
.model:hover { transform: translateY(-4px); box-shadow: 0 1px 0 rgba(255, 255, 255, 0.9) inset, 0 28px 60px -28px rgba(60, 40, 15, 0.45); }
.model:hover::before { opacity: 1; }
.model header { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.logo {
  width: 40px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: #fff;
  border: 1px solid var(--border);
  box-shadow: 0 4px 10px -6px rgba(40, 28, 12, 0.3);
  color: var(--text);
}
.blurb { flex: 1; color: var(--muted); font-size: 12.5px; font-weight: 600; }
.off {
  padding: 4px 9px;
  border-radius: 999px;
  background: var(--ink);
  color: #fff;
  font-size: 11.5px;
  font-weight: 700;
}
.model h3 { margin: 0 0 18px; font: 600 1.05rem/1.2 var(--font-mono); letter-spacing: -0.03em; overflow-wrap: anywhere; }
dl { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin: 0; padding-top: 16px; border-top: 1px dashed var(--border-strong); }
dt { color: var(--muted); font-size: 11.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; }
dd { margin: 4px 0 0; display: flex; flex-direction: column; }
dd.rub-pay b { font-size: 19px; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }
dd.rub-pay s { color: var(--muted); font-size: 12px; font-variant-numeric: tabular-nums; }
dd.rub-pay.muted { color: var(--muted); font-size: 19px; }
.more-wrap { display: flex; justify-content: center; margin-top: 28px; }
.more {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid var(--border-strong);
  color: var(--text);
  font-weight: 600;
  text-decoration: none;
  transition: background 0.2s ease, gap 0.25s var(--ease-out);
}
.more:hover { background: #fff; gap: 12px; }
@media (max-width: 900px) {
  .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .prices { padding-top: 80px; }
}
@media (max-width: 560px) {
  .grid { grid-template-columns: 1fr; }
}
</style>
