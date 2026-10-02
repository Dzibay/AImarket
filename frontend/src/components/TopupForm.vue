<template>
  <form class="topup card" @submit.prevent="submit">
    <div class="head">
      <h2 class="title">{{ mode === 'checkout' ? 'Пополнить и получить ключ' : 'Пополнить баланс' }}</h2>
      <span v-if="price > 0" class="rate">1 $ = {{ rub(price) }}</span>
    </div>

    <div class="switch" role="tablist" aria-label="Валюта">
      <button
        type="button"
        role="tab"
        :class="{ on: currency === 'usd' }"
        :aria-selected="currency === 'usd'"
        @click="setCurrency('usd')"
      >В долларах</button>
      <button
        type="button"
        role="tab"
        :class="{ on: currency === 'rub' }"
        :aria-selected="currency === 'rub'"
        @click="setCurrency('rub')"
      >В рублях</button>
    </div>

    <label class="field">
      <span>{{ currency === 'usd' ? 'Сумма пополнения, $' : 'Сумма к оплате, ₽' }}</span>
      <div class="amount-wrap">
        <input
          class="input big"
          inputmode="decimal"
          autocomplete="off"
          :value="amount"
          :placeholder="currency === 'usd' ? formatMoneyInput(String(minUsd), 'usd') : formatMoneyInput(String(Math.ceil(minRub)), 'rub')"
          @input="onAmountInput"
          @blur="onAmountBlur"
        >
        <b class="unit">{{ currency === 'usd' ? '$' : '₽' }}</b>
      </div>
    </label>

    <div class="presets">
      <button
        v-for="preset in presets"
        :key="preset"
        type="button"
        :class="{ on: Math.abs(parsed - preset) < 1e-9 }"
        @click="setAmount(preset)"
      >{{ currency === 'usd' ? usd(preset, 0) : rub(preset, 0) }}</button>
    </div>

    <div class="summary">
      <div>
        <span class="muted small">К оплате</span>
        <b>{{ rub(rubAmount) }}</b>
      </div>
      <div>
        <span class="muted small">Зачислим на баланс</span>
        <b>{{ usd(usdAmount + bonus.amount) }}</b>
        <span v-if="bonus.amount > 0" class="bonus-line">
          {{ usd(usdAmount) }} + бонус {{ bonus.percent }}% ({{ usd(bonus.amount) }})
        </span>
      </div>
    </div>

    <p v-if="nextTier" class="small tier-hint">
      <template v-if="bonus.amount > 0">Пополните от {{ usd(nextTier.min_usd, 0) }} — бонус вырастет до {{ nextTier.percent }}%.</template>
      <template v-else>Пополните от {{ usd(nextTier.min_usd, 0) }} и получите бонус {{ nextTier.percent }}% к сумме.</template>
    </p>

    <label v-if="mode === 'checkout'" class="field">
      <span>Почта</span>
      <input
        v-model="email"
        class="input"
        type="email"
        autocomplete="email"
        placeholder="you@example.com"
        required
      >
    </label>

    <p v-if="validationError" class="error-text">{{ validationError }}</p>
    <p v-else-if="submitError" class="error-text">{{ submitError }}</p>

    <button type="submit" class="btn block" :disabled="!canSubmit || busy">
      {{ busy ? 'Открываем оплату…' : `Оплатить ${rub(rubAmount)}` }}
    </button>

    <p class="small muted fine">
      <template v-if="mode === 'checkout'">
        После оплаты вы получите ключ доступа к личному кабинету и к API. Ключ показывается на сайте
        <template v-if="emailEnabled"> и отправляется на указанную почту вместе с кнопкой входа в кабинет</template>.
        Нажимая «Оплатить», вы принимаете
        <RouterLink to="/offer">оферту</RouterLink>,
        <RouterLink to="/privacy">политику конфиденциальности</RouterLink> и
        <RouterLink to="/consent">согласие на обработку данных</RouterLink>.
        Минимальное пополнение — {{ usd(minUsd, 0) }}. Максимум за раз — {{ currency === 'usd' ? usd(10000, 0) : rub(100000, 0) }}.
      </template>
      <template v-else>
        Оплата через ЮKassa. Баланс зачислится автоматически после подтверждения платежа.
        Минимальное пополнение — {{ usd(minUsd, 0) }}. Максимум за раз — {{ currency === 'usd' ? usd(10000, 0) : rub(100000, 0) }}.
      </template>
    </p>
    <p v-if="mode === 'checkout'" class="small muted">
      Уже есть ключ? <RouterLink to="/login">Войдите</RouterLink>, чтобы пополнить существующий баланс.
    </p>
  </form>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { errorText, webApi } from '../api/web'
import { formatMoneyInput, parseMoneyInput, rub, usd } from '../utils/format'

const props = defineProps({
  mode: { type: String, default: 'checkout' },
  config: { type: Object, default: null },
})

const MAX_USD = 10_000
const MAX_RUB = 100_000

const currency = ref('usd')
const amount = ref('')
const email = ref('')
const busy = ref(false)
const submitError = ref('')

const price = computed(() => Number(props.config?.usd_price_rub || 0))
const minUsd = computed(() => Number(props.config?.min_topup_usd || 10))
const minRub = computed(() => Number(props.config?.min_topup_rub || 0))
const salesOpen = computed(() => props.config?.sales_open !== false && price.value > 0)

const emailEnabled = computed(() => Boolean(props.config?.email_enabled))

const USD_PRESETS = [10, 25, 50, 100, 500, 1000]

function usdPresetList(min) {
  const floor = Number(min) || 0
  let list = USD_PRESETS.filter((value) => value + 1e-9 >= floor && value <= MAX_USD + 1e-9)
  if (floor > 0 && !list.some((value) => Math.abs(value - floor) < 1e-9) && floor <= MAX_USD) {
    list = [Math.round(floor * 100) / 100, ...list].sort((a, b) => a - b)
  }
  return list.length ? list : (floor > 0 && floor <= MAX_USD ? [Math.round(floor * 100) / 100] : [...USD_PRESETS])
}

const presets = computed(() => {
  const usdList = usdPresetList(minUsd.value)
  if (currency.value === 'usd') return usdList
  if (!price.value) return []
  return usdList
    .map((value) => Math.ceil(value * price.value))
    .filter((value) => value <= MAX_RUB + 1e-9)
})

const parsed = computed(() => {
  const value = parseMoneyInput(amount.value, currency.value)
  return Number.isFinite(value) && value > 0 ? value : 0
})

// Та же арифметика, что в бэкенде: доллары → рубли вверх до копейки, рубли → доллары вниз до цента.
const usdAmount = computed(() => {
  if (!price.value || !parsed.value) return 0
  if (currency.value === 'usd') return Math.round(parsed.value * 100) / 100
  return Math.floor((parsed.value / price.value) * 100 + 1e-9) / 100
})
const rubAmount = computed(() => {
  if (!price.value || !parsed.value) return 0
  if (currency.value === 'rub') return Math.round(parsed.value * 100) / 100
  return Math.ceil(usdAmount.value * price.value * 100 - 1e-9) / 100
})

const tiers = computed(() =>
  [...(props.config?.bonuses || [])]
    .map((tier) => ({ min_usd: Number(tier.min_usd), percent: Number(tier.percent) }))
    .filter((tier) => tier.min_usd > 0 && tier.percent > 0)
    .sort((a, b) => a.min_usd - b.min_usd),
)

// Как в бэкенде: самый высокий подходящий порог, бонус округляется вниз до цента.
const bonus = computed(() => {
  let percent = 0
  for (const tier of tiers.value) if (usdAmount.value >= tier.min_usd) percent = tier.percent
  if (!percent) return { percent: 0, amount: 0 }
  return { percent, amount: Math.floor((usdAmount.value * percent) / 100 * 100 + 1e-9) / 100 }
})

const nextTier = computed(() => tiers.value.find((tier) => usdAmount.value < tier.min_usd) || null)

const validationError = computed(() => {
  if (!salesOpen.value) return 'Продажи временно закрыты. Попробуйте позже.'
  if (!parsed.value) return ''
  if (currency.value === 'usd' && parsed.value > MAX_USD) {
    return `Максимум за раз — ${usd(MAX_USD, 0)}.`
  }
  if (currency.value === 'rub' && parsed.value > MAX_RUB) {
    return `Максимум за раз — ${rub(MAX_RUB, 0)}.`
  }
  if (usdAmount.value < minUsd.value) {
    return `Минимальное пополнение — ${usd(minUsd.value, 0)} (${rub(minRub.value)}).`
  }
  return ''
})

const canSubmit = computed(() => {
  if (!salesOpen.value || !parsed.value || validationError.value) return false
  if (props.mode === 'checkout' && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.value.trim())) return false
  return true
})

watch(() => props.config, (config) => {
  if (!amount.value && config?.min_topup_usd) setAmount(Number(config.min_topup_usd))
}, { immediate: true })

function clampAmount(value) {
  const max = currency.value === 'usd' ? MAX_USD : MAX_RUB
  if (!Number.isFinite(value) || value <= 0) return value
  return Math.min(value, max)
}

function amountMax() {
  return currency.value === 'usd' ? MAX_USD : MAX_RUB
}

function setAmount(value) {
  const capped = clampAmount(Number(value))
  if (!Number.isFinite(capped) || capped <= 0) {
    amount.value = ''
    return
  }
  amount.value = formatMoneyInput(String(capped), currency.value, amountMax())
}

function onAmountInput(event) {
  const max = amountMax()
  const next = formatMoneyInput(event.target.value, currency.value, max)
  amount.value = next
  // Если ref уже был на максимуме, Vue не обновит DOM — принудительно синхронизируем.
  event.target.value = next
}

function onAmountBlur() {
  const value = parseMoneyInput(amount.value, currency.value)
  if (!Number.isFinite(value) || value <= 0) {
    amount.value = ''
    return
  }
  setAmount(Math.round(value * 100) / 100)
}

function setCurrency(next) {
  if (next === currency.value) return
  // Переносим текущую сумму в другую валюту, чтобы не сбивать человека.
  const carry = next === 'rub' ? rubAmount.value : usdAmount.value
  currency.value = next
  if (carry) setAmount(next === 'rub' ? Math.round(carry) : Math.round(carry * 100) / 100)
  else amount.value = ''
}

async function submit() {
  if (!canSubmit.value || busy.value) return
  busy.value = true
  submitError.value = ''
  const payload = currency.value === 'usd' ? { amount_usd: usdAmount.value } : { amount_rub: rubAmount.value }
  try {
    const result = props.mode === 'checkout'
      ? await webApi.checkout({ ...payload, email: email.value.trim() })
      : await webApi.topup(payload)
    if (typeof window.ym === 'function') {
      window.ym(113324421, 'reachGoal', props.mode === 'checkout' ? 'checkout_start' : 'topup_start', {
        amount_usd: result.amount_usd,
      })
    }
    window.location.href = result.pay_url
  } catch (error) {
    submitError.value = errorText(error)
    busy.value = false
  }
}
</script>

<style scoped>
.topup { padding: 24px; }
.head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.title { margin: 0; font-size: 1.25rem; letter-spacing: -0.03em; }
.rate {
  padding: 4px 12px;
  border-radius: 999px;
  background: var(--surface-soft);
  border: 1px solid var(--border);
  color: var(--muted);
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}
.switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  padding: 4px;
  margin-bottom: 16px;
  border-radius: 999px;
  background: var(--surface-soft);
  border: 1px solid var(--border);
}
.switch button {
  border: 0;
  border-radius: 999px;
  padding: 9px 12px;
  background: transparent;
  color: var(--muted);
  font: inherit;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}
.switch button.on { background: var(--accent); color: var(--bg); }
.amount-wrap { position: relative; }
.amount-wrap .input {
  padding-right: 44px;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.01em;
}
.unit {
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--muted);
  font-size: 20px;
}
.presets { display: flex; gap: 8px; flex-wrap: wrap; margin: -4px 0 16px; }
.presets button {
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  padding: 6px 14px;
  background: #fff;
  color: var(--text);
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.presets button.on { background: var(--accent); color: var(--bg); border-color: var(--accent); }
.summary {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding: 14px 16px;
  margin-bottom: 16px;
  border-radius: var(--radius-sm);
  background: var(--surface-soft);
  border: 1px solid var(--border);
}
.summary span { display: block; margin-bottom: 2px; }
.summary b { display: block; font-size: 20px; letter-spacing: -0.02em; }
.bonus-line { color: var(--ok); font-size: 12px; font-weight: 600; margin-top: 2px; }
.tier-hint {
  margin: -8px 0 14px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: var(--ok-soft);
  border: 1px solid #c7e3d4;
  color: #1f4d39;
}
.error-text { margin: 0 0 12px; }
.fine { margin: 14px 0 6px; }
.fine a, .small a { text-decoration: underline; text-underline-offset: 3px; }
@media (max-width: 480px) {
  .summary { grid-template-columns: 1fr; }
}
</style>
