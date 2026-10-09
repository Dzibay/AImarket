<template>
  <div class="site">
    <SiteHeader />
    <main class="site-main">
      <div class="container wrap">
        <h1 class="page-title">Цены на токены</h1>
        <p class="service-rate">
          Курс сервисного доллара при пополнении:
          <strong>1&nbsp;$&nbsp;=&nbsp;{{ rateLabel }}</strong>
        </p>

        <div class="toolbar">
          <label class="search">
            <span class="sr">Найти модель</span>
            <input v-model="query" class="input" type="search" placeholder="Найти модель, например claude или gpt-6" autocomplete="off">
          </label>
          <div class="segmented families" role="tablist" aria-label="Семейство">
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
            >{{ family.name }}</button>
          </div>
        </div>

        <p v-if="!shown.length" class="empty card">Ничего не нашлось. Проверьте написание или сбросьте фильтр.</p>

        <section v-for="group in shown" :key="group.id" class="card group">
          <header class="group-head">
            <span class="logo"><BrandLogo :brand="group.id === 'kimi' ? 'china' : group.id" :size="28" /></span>
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
                <tr v-for="model in group.models" :id="model.id" :key="model.id" :class="{ hit: model.id === highlight }">
                  <td><code>{{ model.id }}</code></td>
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
.wrap { padding-top: 36px; padding-bottom: 72px; }
.page-title { margin-bottom: 10px; }
.service-rate {
  margin: 0 0 22px;
  max-width: 520px;
  color: var(--muted-2);
  font-size: 1rem;
}
.service-rate strong {
  color: var(--text);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.toolbar { display: flex; flex-direction: column; gap: 12px; margin-bottom: 18px; }
.search .input { max-width: 460px; }
.families { flex-wrap: wrap; }
.families em { margin-left: 4px; font-style: normal; color: var(--muted); font-weight: 600; }
.families button.on em { color: inherit; }
.group { padding: 8px 8px 4px; margin-bottom: 16px; }
.group-head { display: flex; align-items: center; gap: 12px; padding: 12px 12px 10px; }
.logo {
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: var(--surface-soft);
  border: 1px solid var(--border);
  color: var(--text);
}
.group-head h2 { margin: 0; font-size: 1.15rem; letter-spacing: -0.03em; }
.group-head p { margin: 0; color: var(--muted); font-size: 13px; }
.table-wrap { overflow: auto; }
table { width: 100%; border-collapse: collapse; min-width: 980px; }
.price-usd { font-size: 15px; font-variant-numeric: tabular-nums; color: var(--muted-2); }
th, td { text-align: left; padding: 12px 14px; border-top: 1px solid var(--border); vertical-align: middle; }
th {
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
td.num, th.num { text-align: right; }
td code { font-size: 13.5px; font-weight: 600; background: none; }
tr.hit td { background: var(--warn-soft); }
.empty { padding: 28px; color: var(--muted); text-align: center; }
.footnote { margin: 8px 0 0; color: var(--muted); font-size: 13px; max-width: 760px; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
.price-cell { display: inline-flex; flex-direction: column; align-items: flex-end; gap: 1px; }
.price-cell b { font-size: 15px; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }
.price-cell s { color: var(--muted); font-size: 12px; font-variant-numeric: tabular-nums; }
@media (max-width: 720px) {
  .families { width: 100%; overflow-x: auto; flex-wrap: nowrap; }
}
</style>
