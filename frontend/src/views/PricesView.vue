<template>
  <div class="site prices-page">
    <SiteHeader />
    <main class="site-main">
      <div class="pr-aurora" aria-hidden="true"><i /><i /><i /></div>
      <div class="container wrap">
        <header class="pr-hero">
          <p class="kicker">Прайс-лист · {{ total }} {{ plural(total, 'модель', 'модели', 'моделей') }}</p>
          <h1 class="pr-title">Цены за 1 млн токенов —<br><span class="grad-text">в 10 раз ниже официальных</span></h1>
          <p class="pr-lead">
            Баланс в долларах, списывается 10% от тарифа провайдера. Нажмите на модель — посчитаем стоимость
            вашей нагрузки.
          </p>
          <div class="pr-stats">
            <span class="pr-stat"><b>−90%</b><small>к цене провайдера</small></span>
            <span class="pr-stat"><b>1&nbsp;$&nbsp;=&nbsp;{{ rateLabel }}</b><small>курс при пополнении</small></span>
            <span class="pr-stat"><b>{{ families.length }}</b><small>семейств моделей</small></span>
          </div>
        </header>

        <div class="toolbar">
          <label class="search-glow">
            <AppIcon name="search" :size="18" />
            <span class="sr">Найти модель</span>
            <input v-model="query" type="search" placeholder="Найти модель: claude, gpt-6, gemini…" autocomplete="off">
            <span v-if="query" class="found">{{ foundCount }}</span>
          </label>
          <div class="families" role="tablist" aria-label="Семейство">
            <button type="button" role="tab" :class="{ on: familyId === 'all' }" :aria-selected="familyId === 'all'" @click="familyId = 'all'">
              Все <em>{{ total }}</em>
            </button>
            <button
              v-for="family in families"
              :key="family.id"
              type="button"
              role="tab"
              :class="{ on: familyId === family.id }"
              :aria-selected="familyId === family.id"
              @click="familyId = family.id"
            >
              <BrandLogo :brand="family.id === 'kimi' ? 'china' : family.id" :size="14" />{{ family.name }}
            </button>
          </div>
        </div>

        <p v-if="!shown.length" class="empty glass">Ничего не нашлось. Проверьте написание или сбросьте фильтр.</p>

        <section v-for="group in shown" :key="group.id" class="glass group">
          <span class="group-glow" aria-hidden="true" />
          <header class="group-head">
            <span class="logo"><BrandLogo :brand="group.id === 'kimi' ? 'china' : group.id" :size="26" /></span>
            <div>
              <h2>{{ group.name }}</h2>
              <p>{{ group.vendor }} · {{ group.models.length }} {{ plural(group.models.length, 'модель', 'модели', 'моделей') }}</p>
            </div>
          </header>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Модель</th>
                  <th>Контекст</th>
                  <th class="num">Вход, USD</th>
                  <th class="num">Вход, ₽</th>
                  <th class="num">Кэш, USD</th>
                  <th class="num">Кэш, ₽</th>
                  <th class="num">Выход, USD</th>
                  <th class="num">Выход, ₽</th>
                </tr>
              </thead>
              <tbody>
                <template v-for="model in group.models" :key="model.id">
                  <tr
                    :id="model.id"
                    class="row"
                    :class="{ hit: model.id === highlight, open: model.id === openId }"
                    tabindex="0"
                    :aria-expanded="model.id === openId"
                    @click="toggle(model.id)"
                    @keydown.enter.prevent="toggle(model.id)"
                  >
                    <td><span class="model-id"><code>{{ model.id }}</code><span class="calc-tag">Рассчитать</span></span></td>
                    <td class="muted">{{ contextSize(model.context) }}</td>
                    <td class="num"><span class="price-usd">{{ tokenUsd(model.input) }}</span></td>
                    <td class="num">
                      <span class="price-cell"><b>{{ tokenRub(ourRubPerMillion(model.input, usdPriceRub)) }}</b><s>{{ tokenRub(referenceRubPerMillion(model.input, usdPriceRub)) }}</s></span>
                    </td>
                    <td class="num"><span class="price-usd">{{ cacheUsd(model.cache) }}</span></td>
                    <td class="num">
                      <span v-if="model.cache != null" class="price-cell"><b>{{ tokenRub(ourRubPerMillion(model.cache, usdPriceRub)) }}</b><s>{{ tokenRub(referenceRubPerMillion(model.cache, usdPriceRub)) }}</s></span>
                      <span v-else class="price-usd">—</span>
                    </td>
                    <td class="num"><span class="price-usd">{{ tokenUsd(model.output) }}</span></td>
                    <td class="num">
                      <span class="price-cell"><b>{{ tokenRub(ourRubPerMillion(model.output, usdPriceRub)) }}</b><s>{{ tokenRub(referenceRubPerMillion(model.output, usdPriceRub)) }}</s></span>
                    </td>
                  </tr>
                  <tr v-if="model.id === openId" class="calc-row">
                    <td colspan="8">
                      <div class="calc">
                        <div class="calc-inputs">
                          <label>
                            <span>Входящие токены в месяц <b>{{ volumeLabel(calcIn) }}</b></span>
                            <input v-model.number="calcIn" type="range" min="0" :max="VOLUMES.length - 1" step="1">
                          </label>
                          <label>
                            <span>Исходящие токены в месяц <b>{{ volumeLabel(calcOut) }}</b></span>
                            <input v-model.number="calcOut" type="range" min="0" :max="VOLUMES.length - 1" step="1">
                          </label>
                        </div>
                        <div class="calc-result">
                          <span class="calc-ref"><small>У провайдера</small><s>{{ rub(calcCost(model).ref, 0) }}</s></span>
                          <span class="calc-our"><small>У нас</small><b>{{ rub(calcCost(model).our, 0) }}</b></span>
                          <span class="calc-save">экономия {{ rub(calcCost(model).ref - calcCost(model).our, 0) }}</span>
                          <RouterLink :to="{ path: '/', hash: '#pay' }" class="btn sm">Пополнить баланс</RouterLink>
                        </div>
                      </div>
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
        </section>

        <p class="footnote">
          Баланс ведётся в долларах; с баланса списывается 10% от USD-тарифа в таблице
          (вход, кэш промпта и выход — по отдельности).
          Рубли — пересчёт для удобства при пополнении, курс как на главной ({{ rateLabel }}/$).
          Источник каталога: router.cheap/pricing, снимок {{ priceAsOf }}. Цены могут меняться.
          Модели генерации изображений в таблицу не входят.
        </p>
      </div>
    </main>
    <SiteFooter />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import BrandLogo from '../components/BrandLogo.vue'
import SiteFooter from '../components/SiteFooter.vue'
import SiteHeader from '../components/SiteHeader.vue'
import AppIcon from '../components/ui/AppIcon.vue'
import { useWebConfig } from '../composables/useWebConfig'
import {
  PRICE_AS_OF,
  families,
  ourRubPerMillion,
  referenceRubPerMillion,
} from '../data/tokenPrices'
import { contextSize, rub, tokenRub, tokenUsd } from '../utils/format'
import { useHead } from '../utils/useHead'

const { usdPriceRub, loadConfig } = useWebConfig()
const rateLabel = computed(() => (usdPriceRub.value > 0 ? rub(usdPriceRub.value) : '…'))
const priceAsOf = PRICE_AS_OF

function cacheUsd(value) {
  return value == null ? '—' : tokenUsd(value)
}

const query = ref('')
const familyId = ref('all')
const highlight = ref('')
const openId = ref('')

// Мини-калькулятор: объёмы токенов в месяц (шкала ползунка).
const VOLUMES = [0, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500]
const calcIn = ref(5)
const calcOut = ref(3)

function volumeLabel(index) {
  const m = VOLUMES[index]
  if (!m) return '0'
  return m < 1 ? `${m * 1000} тыс.` : `${m} млн`
}

function calcCost(model) {
  const rate = usdPriceRub.value
  const inM = VOLUMES[calcIn.value]
  const outM = VOLUMES[calcOut.value]
  return {
    our: inM * ourRubPerMillion(model.input, rate) + outM * ourRubPerMillion(model.output, rate),
    ref: inM * referenceRubPerMillion(model.input, rate) + outM * referenceRubPerMillion(model.output, rate),
  }
}

function toggle(id) {
  openId.value = openId.value === id ? '' : id
}

const total = families.reduce((sum, family) => sum + family.models.length, 0)

const shown = computed(() => {
  const needle = query.value.trim().toLowerCase()
  return families
    .filter((family) => familyId.value === 'all' || family.id === familyId.value)
    .map((family) => ({
      ...family,
      models: family.models.filter((model) => !needle || model.id.includes(needle) || family.name.toLowerCase().includes(needle)),
    }))
    .filter((family) => family.models.length)
})
const foundCount = computed(() => shown.value.reduce((sum, family) => sum + family.models.length, 0))

function plural(n, one, few, many) {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return one
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few
  return many
}

onMounted(async () => {
  useHead('Цены на токены — Aimarket')
  await loadConfig()
  const id = window.location.hash.replace('#', '')
  if (!id) return
  highlight.value = id
  requestAnimationFrame(() => {
    document.getElementById(id)?.scrollIntoView({ block: 'center' })
  })
})
</script>

<style scoped>
.prices-page .site-main { position: relative; isolation: isolate; overflow-x: clip; }
.pr-aurora { position: absolute; inset: -100px 0 auto; height: 900px; z-index: -1; pointer-events: none; }
.pr-aurora i { position: absolute; border-radius: 50%; filter: blur(110px); opacity: 0.45; animation: pr-drift 18s ease-in-out infinite alternate; }
.pr-aurora i:nth-child(1) { width: 560px; height: 440px; left: -140px; top: 60px; background: #f2b27a; }
.pr-aurora i:nth-child(2) { width: 520px; height: 420px; right: -120px; top: 40px; background: #c9b2f0; animation-delay: -7s; }
.pr-aurora i:nth-child(3) { width: 420px; height: 340px; left: 40%; top: 360px; background: #f6d3a8; animation-delay: -12s; }
@keyframes pr-drift { to { transform: translate(60px, -40px) scale(1.1); } }

.wrap { padding-top: 56px; padding-bottom: 80px; }
.pr-hero { max-width: 820px; margin-bottom: 34px; }
.pr-title { margin: 0 0 16px; font-size: clamp(2.2rem, 5vw, 3.8rem); font-weight: 680; letter-spacing: -0.06em; line-height: 1.02; }
.pr-lead { margin: 0 0 26px; max-width: 620px; color: var(--muted-2); font-size: 17px; line-height: 1.55; }
.pr-stats { display: flex; flex-wrap: wrap; gap: 10px; }
.pr-stat {
  display: grid;
  gap: 2px;
  padding: 12px 20px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.95);
  box-shadow: 0 14px 30px -22px rgba(60, 40, 15, 0.5);
}
.pr-stat:first-child { background: linear-gradient(160deg, #2b2620, #15120e); border-color: transparent; color: #fff; }
.pr-stat:first-child b { background: linear-gradient(90deg, #ffb487, #d6b8ff); -webkit-background-clip: text; background-clip: text; color: transparent; }
.pr-stat:first-child small { color: rgba(255, 255, 255, 0.55); }
.pr-stat b { font-size: 21px; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }
.pr-stat small { color: var(--muted); font-size: 12.5px; }

/* Липкая панель поиска и фильтров */
.toolbar {
  position: sticky;
  top: 78px;
  z-index: 20;
  display: grid;
  gap: 10px;
  margin: 0 -10px 20px;
  padding: 10px;
  border-radius: 24px;
  background: rgba(250, 247, 242, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 20px 40px -32px rgba(60, 40, 15, 0.6);
  backdrop-filter: blur(18px) saturate(1.3);
  -webkit-backdrop-filter: blur(18px) saturate(1.3);
}
.search-glow {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 18px;
  min-height: 54px;
  border-radius: 16px;
  background: #fff;
  border: 1px solid var(--border-strong);
  color: var(--muted);
  transition: border-color 0.2s ease, box-shadow 0.3s ease;
}
.search-glow:focus-within { border-color: #e0a27a; box-shadow: 0 0 0 4px rgba(217, 101, 59, 0.12), 0 12px 30px -16px rgba(217, 101, 59, 0.5); }
.search-glow input { flex: 1; min-width: 0; border: 0; outline: 0; background: none; font: inherit; font-size: 16.5px; color: var(--text); }
.found { padding: 3px 10px; border-radius: 999px; background: rgba(217, 101, 59, 0.1); color: #c4572f; font-size: 13px; font-weight: 700; }
.families { display: flex; flex-wrap: wrap; gap: 6px; }
.families button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid rgba(28, 25, 21, 0.08);
  background: rgba(255, 255, 255, 0.7);
  color: var(--muted-2);
  font: inherit;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease, transform 0.2s var(--ease-out);
}
.families button:hover { transform: translateY(-1px); color: var(--text); }
.families button.on { background: linear-gradient(160deg, #2b2620, #15120e); color: #fff; border-color: transparent; }
.families em { font-style: normal; color: var(--muted); font-weight: 600; }
.families button.on em { color: rgba(255, 255, 255, 0.6); }

/* Карточки семейств */
.glass {
  position: relative;
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.95);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.9) inset, 0 30px 60px -44px rgba(60, 40, 15, 0.55);
  backdrop-filter: blur(16px) saturate(1.2);
  -webkit-backdrop-filter: blur(16px) saturate(1.2);
}
.group { padding: 10px 10px 6px; margin-bottom: 18px; overflow: hidden; scroll-margin-top: 220px; }
.group-glow {
  position: absolute;
  top: -120px;
  left: -80px;
  width: 320px;
  height: 240px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(242, 178, 122, 0.45), transparent 70%);
  opacity: 0;
  transition: opacity 0.5s ease;
  pointer-events: none;
}
.group:hover .group-glow { opacity: 1; }
.group-head { position: relative; display: flex; align-items: center; gap: 14px; padding: 14px 14px 12px; }
.logo {
  width: 48px;
  height: 48px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 15px;
  background: #fff;
  border: 1px solid rgba(255, 255, 255, 0.95);
  box-shadow: 0 12px 24px -16px rgba(40, 28, 12, 0.6);
  color: var(--text);
}
.group-head h2 { margin: 0; font-size: 1.25rem; letter-spacing: -0.035em; }
.group-head p { margin: 0; color: var(--muted); font-size: 13px; }
.table-wrap { position: relative; overflow: auto; }
table { width: 100%; border-collapse: collapse; min-width: 980px; }
th, td { text-align: left; padding: 12px 14px; border-top: 1px solid rgba(28, 25, 21, 0.07); vertical-align: middle; }
th { color: var(--muted); font-size: 11.5px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
td.num, th.num { text-align: right; }
.row { cursor: pointer; transition: background 0.2s ease; }
.row:hover td, .row:focus-visible td { background: rgba(255, 255, 255, 0.75); }
.row:focus-visible { outline: none; }
.row.open td { background: rgba(255, 255, 255, 0.9); }
.row.hit td { background: var(--warn-soft); }
.model-id { display: inline-flex; align-items: center; gap: 10px; }
td code { font-size: 13.5px; font-weight: 600; background: none; }
.calc-tag {
  padding: 3px 9px;
  border-radius: 999px;
  background: linear-gradient(135deg, #d9653b, #b07be0);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  opacity: 0;
  transform: translateX(-4px);
  transition: opacity 0.2s ease, transform 0.25s var(--ease-out);
}
.row:hover .calc-tag, .row.open .calc-tag, .row:focus-visible .calc-tag { opacity: 1; transform: none; }
.price-usd { font-size: 15px; font-variant-numeric: tabular-nums; color: var(--muted-2); }
.price-cell { display: inline-flex; flex-direction: column; align-items: flex-end; gap: 1px; }
.price-cell b { font-size: 15px; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }
.price-cell s { color: var(--muted); font-size: 12px; font-variant-numeric: tabular-nums; }

/* Мини-калькулятор */
.calc-row td { padding: 0 8px 12px; border-top: 0; background: rgba(255, 255, 255, 0.9); }
.calc {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 28px;
  align-items: center;
  padding: 20px 22px;
  border-radius: 20px;
  background: linear-gradient(160deg, #241e18, #15120e);
  color: #fff;
  animation: pr-open 0.35s var(--ease-out) both;
}
@keyframes pr-open { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: none; } }
.calc-inputs { display: grid; gap: 14px; }
.calc-inputs label { display: grid; gap: 8px; }
.calc-inputs span { display: flex; justify-content: space-between; gap: 12px; color: rgba(255, 255, 255, 0.65); font-size: 13.5px; }
.calc-inputs b { color: #fff; font-variant-numeric: tabular-nums; }
.calc-inputs input { width: 100%; accent-color: #e08a5a; }
.calc-result { display: grid; grid-template-columns: auto auto; gap: 6px 26px; align-items: end; }
.calc-result small { display: block; color: rgba(255, 255, 255, 0.5); font-size: 12px; }
.calc-ref s { color: rgba(255, 255, 255, 0.5); font-size: 18px; font-variant-numeric: tabular-nums; }
.calc-our b { font-size: 30px; letter-spacing: -0.04em; font-variant-numeric: tabular-nums; background: linear-gradient(90deg, #ffb487, #d6b8ff); -webkit-background-clip: text; background-clip: text; color: transparent; }
.calc-save { grid-column: 1 / -1; color: #8fdcb4; font-size: 13.5px; font-weight: 600; }
.calc-result .btn { grid-column: 1 / -1; justify-content: center; }

.empty { padding: 28px; color: var(--muted); text-align: center; }
.footnote { margin: 12px 0 0; color: var(--muted); font-size: 13px; max-width: 760px; line-height: 1.55; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }

@media (max-width: 720px) {
  .wrap { padding-top: 32px; }
  .toolbar { top: 66px; margin: 0 -6px 16px; padding: 8px; border-radius: 20px; }
  .families { flex-wrap: nowrap; overflow-x: auto; scrollbar-width: none; }
  .families button { flex: none; }
  .pr-stats { flex-wrap: nowrap; gap: 8px; }
  .pr-stat { flex: 1 1 0; min-width: 0; padding: 10px 12px; }
  .pr-stat b { font-size: 16px; }
  .pr-stat small { font-size: 11px; }
  .calc { grid-template-columns: 1fr; position: sticky; left: 0; width: min(calc(100vw - 60px), 520px); }
}
@media (prefers-reduced-motion: reduce) {
  .pr-aurora i, .calc { animation: none; }
}
</style>
