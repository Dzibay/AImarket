<template>
  <div class="site">
    <SiteHeader />
    <main class="site-main">
      <div class="narrow wrap">
        <template v-if="state === 'loading'">
          <h1 class="page-title">Проверяем оплату…</h1>
          <p class="page-lead">Это займёт пару секунд.</p>
        </template>

        <template v-else-if="state === 'paid'">
          <h1 class="page-title">Оплата прошла</h1>
          <p class="page-lead">
            Зачислено <b>{{ usd(credited) }}</b><template v-if="bonusUsd > 0"> (из них бонус {{ usd(bonusUsd) }})</template>,
            баланс — <b>{{ usd(profile.balance_usd) }}</b>. Вы уже вошли в личный кабинет — осталось сохранить ключ.
            <template v-if="profile.email_enabled && profile.email">
              Копию ключа и кнопку входа мы отправили на {{ profile.email }}.
            </template>
          </p>
          <KeyCard
            v-if="profile.key"
            :secret="profile.key.secret"
            :base-url="profile.api_base_url"
            title="Ваш ключ доступа"
            highlight
            reveal-by-default
          />
          <div v-else class="notice">
            Платёж зачислен, но ключ ещё выпускается. Откройте личный кабинет через минуту — ключ появится там.
          </div>
          <div class="actions">
            <RouterLink to="/cabinet#setup" class="btn">Подключить приложение</RouterLink>
            <RouterLink to="/cabinet" class="btn quiet">В личный кабинет</RouterLink>
          </div>
          <p class="muted small">
            Для Cursor, Codex, Claude Code и других программ в кабинете есть готовая команда — вставьте её,
            и ключ с адресом API пропишутся сами.
          </p>
        </template>

        <template v-else-if="state === 'awaiting_supplier'">
          <h1 class="page-title">Оплата получена</h1>
          <p class="page-lead">
            Платёж прошёл в ЮKassa, зачисление на баланс займёт немного времени.
            Страница проверяет статус автоматически — обновите её через несколько минут или зайдите в кабинет позже.
          </p>
          <p v-if="error" class="notice">{{ error }}</p>
          <div class="card soft">
            <button type="button" class="btn quiet sm" :disabled="checking" @click="check">
              {{ checking ? 'Проверяем…' : 'Проверить сейчас' }}
            </button>
          </div>
        </template>

        <template v-else-if="state === 'pending'">
          <h1 class="page-title">Платёж ещё обрабатывается</h1>
          <p class="page-lead">
            Банк пока не подтвердил оплату. Обычно это занимает до минуты — страница проверяет статус
            автоматически.
          </p>
          <p v-if="error" class="notice">{{ error }}</p>
          <div class="card soft">
            <p class="muted small">Проверок: {{ attempts }}. Если платёж не подтвердится, деньги вернутся на карту.</p>
            <button type="button" class="btn quiet sm" :disabled="checking" @click="check">
              {{ checking ? 'Проверяем…' : 'Проверить сейчас' }}
            </button>
          </div>
        </template>

        <template v-else-if="state === 'failed'">
          <h1 class="page-title">Оплата не прошла</h1>
          <p class="page-lead">Платёж отклонён или отменён. Деньги не списаны либо вернутся на карту.</p>
          <RouterLink to="/" class="btn">Попробовать снова</RouterLink>
        </template>

        <template v-else>
          <h1 class="page-title">Ссылка недействительна</h1>
          <p class="page-lead">{{ error }}</p>
          <div class="actions">
            <RouterLink v-if="hasSession" to="/cabinet" class="btn">В личный кабинет</RouterLink>
            <RouterLink to="/login" class="btn" :class="{ quiet: hasSession }">Вход</RouterLink>
            <RouterLink to="/" class="btn quiet">На главную</RouterLink>
          </div>
        </template>
      </div>
    </main>
    <SiteFooter />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import KeyCard from '../components/KeyCard.vue'
import SiteFooter from '../components/SiteFooter.vue'
import SiteHeader from '../components/SiteHeader.vue'
import { errorText, webApi } from '../api/web'
import { claimGuestSupportIfNeeded } from '../composables/useGuestSupport'
import { getSession, useSession } from '../composables/useSession'
import { reachMetrikaGoal } from '../utils/cookiesConsent'
import { usd } from '../utils/format'
import { useHead } from '../utils/useHead'

const route = useRoute()
const { setSession } = useSession()
const hasSession = Boolean(getSession())

const state = ref('loading')
const profile = ref(null)
const error = ref('')
const attempts = ref(0)
const checking = ref(false)
const credited = ref(0)
const bonusUsd = ref(0)
let timer = null

const topup = Number(route.params.topup || route.query.topup || 0)
const rawToken = String(route.params.token || route.query.t || '')
let token = rawToken
try {
  token = decodeURIComponent(rawToken)
} catch {
  token = rawToken
}

async function check() {
  if (checking.value) return
  checking.value = true
  attempts.value += 1
  try {
    const result = await webApi.paymentReturn(topup, token)
    if (result.status === 'paid') {
      setSession(result.session)
      await claimGuestSupportIfNeeded()
      profile.value = result.profile
      bonusUsd.value = Number(result.bonus_usd || 0)
      credited.value = Number(result.amount_usd || 0) + bonusUsd.value
      state.value = 'paid'
      trackPaymentSuccess({
        amount_usd: Number(result.amount_usd || 0),
        bonus_usd: bonusUsd.value,
        topup_id: topup,
      })
      stop()
    } else if (result.status === 'awaiting_supplier') {
      state.value = 'awaiting_supplier'
      if (attempts.value < 24 && !timer) timer = setTimeout(() => { timer = null; check() }, 15000)
    } else if (result.status === 'pending') {
      state.value = 'pending'
      if (attempts.value < 12 && !timer) timer = setTimeout(() => { timer = null; check() }, 5000)
    } else {
      state.value = 'failed'
      stop()
    }
  } catch (err) {
    // Серверная 500 / сеть — даём повторить, платёж мог уже пройти по вебхуку.
    if (err?.status === 500 || err?.status === 502 || !err?.status) {
      error.value = errorText(err)
      state.value = 'pending'
      if (attempts.value < 6 && !timer) timer = setTimeout(() => { timer = null; check() }, 3000)
    } else {
      error.value = errorText(err)
      state.value = 'invalid'
      stop()
    }
  } finally {
    checking.value = false
  }
}

function stop() {
  if (timer) clearTimeout(timer)
  timer = null
}

/** Цель Метрики: оплата подтверждена. Один раз на topup (защита от F5). */
function trackPaymentSuccess(params) {
  const key = `ym_payment_success_${params.topup_id}`
  try {
    if (sessionStorage.getItem(key)) return
    sessionStorage.setItem(key, '1')
  } catch {
    /* private mode — всё равно отправим */
  }
  reachMetrikaGoal('payment_success', params)
}

onMounted(() => {
  useHead('Оплата — Aimarket', true)
  if (!topup || !token) {
    error.value = 'В ссылке нет данных о платеже.'
    state.value = 'invalid'
    return
  }
  check()
})

onBeforeUnmount(stop)
</script>

<style scoped>
.wrap { padding-top: 40px; padding-bottom: 72px; }
.actions { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 20px; }
.card.soft .btn { margin-top: 8px; }
</style>
