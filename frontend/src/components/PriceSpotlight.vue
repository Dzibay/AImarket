<template>
  <section class="container block prices">
    <div class="block-head">
      <p class="eyebrow">Цены</p>
      <h2>Флагманские модели — на 90% дешевле</h2>
      <p class="lead">
        За 1 млн токенов: USD — как в OpenRouter; ₽ — при курсе {{ rateLabel }}/$ со скидкой 90%.
      </p>
    </div>

    <div class="grid">
      <article v-for="item in cards" :key="item.id" class="model">
        <header>
          <span class="logo"><BrandLogo :brand="item.brand" :size="22" /></span>
          <span class="blurb">{{ item.blurb }}</span>
        </header>
        <h3>{{ item.id }}</h3>
        <dl>
          <div>
            <dt>Вход</dt>
            <dd class="usd-ref">{{ tokenUsd(item.input) }}</dd>
            <dd class="rub-pay">
              <b>{{ tokenRub(ourRubPerMillion(item.input, usdPriceRub)) }}</b>
              <s>{{ tokenRub(officialRubPerMillion(item.input, usdPriceRub)) }}</s>
            </dd>
          </div>
          <div>
            <dt>Выход</dt>
            <dd class="usd-ref">{{ tokenUsd(item.output) }}</dd>
            <dd class="rub-pay">
              <b>{{ tokenRub(ourRubPerMillion(item.output, usdPriceRub)) }}</b>
              <s>{{ tokenRub(officialRubPerMillion(item.output, usdPriceRub)) }}</s>
            </dd>
          </div>
        </dl>
      </article>
    </div>

    <RouterLink to="/prices" class="btn quiet more">Все цены — {{ count }} моделей</RouterLink>
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
  officialRubPerMillion,
  ourRubPerMillion,
} from '../data/tokenPrices'
import { rub, tokenRub, tokenUsd } from '../utils/format'

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
    output: model.output,
  }
})
</script>

<style scoped>
.prices { padding-top: 8px; }
.block-head { max-width: 640px; margin-bottom: 22px; }
.eyebrow {
  display: inline-block;
  margin: 0 0 12px;
  padding: 5px 12px;
  border-radius: 999px;
  background: var(--ok-soft);
  border: 1px solid #c7e3d4;
  color: #1f4d39;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.block-head h2 {
  margin: 0 0 8px;
  font-size: clamp(1.7rem, 3vw, 2.3rem);
  line-height: 1.1;
  letter-spacing: -0.035em;
}
.lead { margin: 0; color: var(--muted-2); }
.grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.model {
  padding: 18px 18px 16px;
  border-radius: var(--radius);
  background: #fff;
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
}
.model header { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 12px; }
.logo {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: var(--surface-soft);
  border: 1px solid var(--border);
  color: var(--text);
}
.blurb { color: var(--muted); font-size: 12px; font-weight: 600; }
.model h3 { margin: 0 0 14px; font-size: 1.05rem; letter-spacing: -0.03em; overflow-wrap: anywhere; }
dl { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 0; }
dt { color: var(--muted); font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; }
dd { margin: 2px 0 0; display: flex; flex-direction: column; }
dd.usd-ref { color: var(--muted-2); font-size: 13px; font-variant-numeric: tabular-nums; margin-bottom: 4px; }
dd.rub-pay b { font-size: 20px; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }
dd.rub-pay s { color: var(--muted); font-size: 13px; font-variant-numeric: tabular-nums; }
.more { margin-top: 18px; }
@media (max-width: 900px) { .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 560px) { .grid { grid-template-columns: 1fr; } }
</style>
