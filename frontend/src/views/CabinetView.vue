<template>
  <div class="site">
    <SiteHeader />
    <main class="site-main">
      <div class="container wrap">
        <template v-if="loading && !profile">
          <div class="layout">
            <aside class="side"><div class="side-inner skeleton-nav"><span v-for="n in 6" :key="n" class="skeleton" /></div></aside>
            <div class="content">
              <div class="skeleton-hero skeleton" />
              <div class="stats"><div v-for="n in 3" :key="n" class="card stat"><span class="skeleton" style="width: 40%" /><span class="skeleton tall" style="width: 60%" /></div></div>
            </div>
          </div>
        </template>

        <template v-else-if="loadError && !profile">
          <h1 class="page-title">Личный кабинет</h1>
          <div class="notice bad">{{ loadError }}</div>
          <div class="actions">
            <button type="button" class="btn quiet" @click="load">Повторить</button>
            <RouterLink to="/login" class="btn">Войти заново</RouterLink>
          </div>
        </template>

        <div v-else-if="profile" class="layout">
          <aside class="side">
            <div class="side-inner">
              <nav class="side-nav" aria-label="Разделы кабинета">
                <a
                  v-for="item in sections"
                  :key="item.id"
                  :href="`#${item.id}`"
                  :class="{ on: active === item.id }"
                  @click.prevent="scrollTo(item.id)"
                >
                  <AppIcon :name="item.icon" :size="17" />
                  <span>{{ item.label }}</span>
                </a>
                <RouterLink to="/prices">
                  <AppIcon name="tag" :size="17" />
                  <span>Цены</span>
                </RouterLink>
              </nav>
              <div class="side-foot">
                <button type="button" class="side-link" :disabled="loading" @click="load">
                  <AppIcon name="refresh" :size="15" :class="{ spin: loading }" />
                  {{ loading ? 'Обновляем…' : 'Обновить данные' }}
                </button>
                <RouterLink to="/cabinet/support" class="side-link">
                  <AppIcon name="help" :size="15" />
                  Написать в поддержку
                  <span v-if="supportUnread > 0" class="nav-badge">{{ supportUnread > 9 ? '9+' : supportUnread }}</span>
                </RouterLink>
              </div>
            </div>
          </aside>

          <div class="content">
            <div class="head">
              <div>
                <h1 class="page-title">Личный кабинет</h1>
                <p class="page-lead">
                  <template v-if="profile.email">{{ profile.email }} · </template>
                  аккаунт с {{ shortDate(profile.created_at) }}
                </p>
              </div>
            </div>

            <div v-if="profile.blocked" class="notice bad">
              Доступ заблокирован<template v-if="profile.blocked_reason">: {{ profile.blocked_reason }}</template>.
              Напишите в <RouterLink to="/cabinet/support">чат поддержки</RouterLink><template v-if="supportLabel"> или {{ supportLabel }}</template>.
            </div>

            <section id="overview" class="anchor">
              <div class="hero card">
                <div class="hero-main">
                  <span class="hero-label">Баланс</span>
                  <b class="hero-balance">{{ usd(profile.balance_usd) }}</b>
                  <span class="hero-rub">≈ {{ rub(profile.balance_usd * profile.usd_price_rub) }} · 1 $ = {{ rub(profile.usd_price_rub) }}</span>
                  <div class="hero-chips">
                    <span class="chip" :class="status.kind"><i />{{ status.text }}</span>
                    <span v-if="daysLeft" class="chip">При текущем темпе хватит на {{ daysLeft }}</span>
                  </div>
                  <div class="hero-actions">
                    <button type="button" class="btn light" @click="scrollTo('topup')"><AppIcon name="wallet" :size="16" />Пополнить</button>
                    <button type="button" class="btn ghost" @click="scrollTo('setup')"><AppIcon name="plug" :size="16" />Подключить приложение</button>
                  </div>
                </div>
                <div class="hero-chart">
                  <div class="hero-chart-head">
                    <span>Расход за 7 дней</span>
                    <b>{{ usdSmart(weekTotal) }}</b>
                  </div>
                  <div class="chart">
                    <div
                      v-for="day in weekDays"
                      :key="day.date"
                      class="bar-wrap"
                      :title="`${day.label}: ${usdSmart(day.usd)}`"
                    >
                      <span class="bar-value">{{ day.usd ? usdSmart(day.usd) : '' }}</span>
                      <i :class="{ empty: !day.usd, today: day.is_today }" :style="{ height: barHeight(day.usd) }" />
                      <span class="bar-label">{{ day.label.slice(6) || day.label.slice(0, 5) }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div class="stats">
                <div class="card stat">
                  <span class="muted small">Потрачено сегодня</span>
                  <b>{{ usdSmart(profile.spent_today_usd) }}</b>
                </div>
                <div class="card stat">
                  <span class="muted small">За этот месяц</span>
                  <b>{{ usdSmart(profile.spent_month_usd) }}</b>
                </div>
                <div class="card stat">
                  <span class="muted small">Последний запрос</span>
                  <b class="date">{{ lastRequest }}</b>
                </div>
              </div>

              <p v-if="lowBalance" class="notice">
                Баланс почти закончился: при нуле запросы начнут возвращать ошибку.
                <a href="#topup" @click.prevent="scrollTo('topup')">Пополнить заранее</a>.
              </p>

              <section v-if="onboarding" class="card onboarding">
                <div class="onb-head">
                  <h2 class="card-title">{{ onboarding.title }}</h2>
                  <p class="muted small">{{ onboarding.lead }}</p>
                </div>
                <ol class="onb-steps">
                  <li v-for="step in onboarding.steps" :key="step.id">
                    <span class="step-dot">{{ step.index }}</span>
                    <div>
                      <b>{{ step.title }}</b>
                      <p class="muted small">{{ step.text }}</p>
                      <button v-if="step.target" type="button" class="btn sm" :class="{ quiet: !step.primary }" @click="scrollTo(step.target)">
                        {{ step.action }}
                      </button>
                    </div>
                  </li>
                </ol>
              </section>
            </section>

            <section id="key" class="anchor">
              <h2 class="section-title">Ключ доступа</h2>
              <KeyCard
                v-if="profile.key"
                :secret="profile.key.secret"
                :base-url="profile.api_base_url"
                title="Ваш ключ"
              />
              <div v-else class="card">
                <h2 class="card-title">Ключ доступа</h2>
                <p class="muted">
                  <template v-if="profile.balance_usd > 0">
                    Ключ выпускается — нажмите «Обновить данные» через минуту. Если он так и не появился, напишите в поддержку.
                  </template>
                  <template v-else>
                    Ключ появится автоматически после первого пополнения баланса — его сразу можно будет
                    вставить в приложение и использовать для входа на сайт.
                  </template>
                </p>
                <p v-if="profile.key_error" class="error-text">{{ keyErrorText(profile.key_error) }}</p>
              </div>

              <div v-if="profile.key" class="grid key-grid">
                <div class="card soft facts">
                  <h3 class="card-title sm">Как расходуется баланс</h3>
                  <ul class="plain">
                    <li><AppIcon name="spark" :size="15" />Один ключ открывает все модели — модель выбирается в поле <code>model</code>.</li>
                    <li><AppIcon name="send" :size="15" />Списание за токены — 10% от официальной цены, сразу после каждого ответа. <RouterLink to="/prices">Все цены</RouterLink>.</li>
                    <li><AppIcon name="wallet" :size="15" />При нулевом балансе запросы останавливаются, ключ остаётся вашим.</li>
                    <li v-if="profile.key.spent_usd != null"><AppIcon name="history" :size="15" />Через этот ключ потрачено <b>{{ usdSmart(profile.key.spent_usd) }}</b>.</li>
                  </ul>
                </div>
                <div class="card reissue">
                  <h3 class="card-title sm">Перевыпуск ключа</h3>
                  <p class="muted small">
                    Если ключ попал к посторонним — выпустите новый. Старый сразу перестанет работать и для API, и для
                    входа на сайт, баланс сохранится. После перевыпуска обновите ключ в приложениях.
                  </p>
                  <p v-if="reissueError" class="error-text">{{ reissueError }}</p>
                  <button type="button" class="btn danger sm" :disabled="reissuing" @click="reissue">
                    <AppIcon name="refresh" :size="15" />{{ reissuing ? 'Выпускаем…' : 'Перевыпустить ключ' }}
                  </button>
                </div>
              </div>
            </section>

            <section id="setup" class="anchor">
              <h2 class="section-title">Подключение</h2>
              <SetupGuide :secret="profile.key?.secret || ''" :base-url="profile.api_base_url" />
            </section>

            <section id="topup" class="anchor">
              <h2 class="section-title">Пополнение</h2>
              <div class="grid topup-grid">
                <TopupForm v-if="!profile.blocked" mode="topup" :config="profile" />
                <div v-else class="card"><p class="muted">Пополнение недоступно: аккаунт заблокирован.</p></div>
                <div class="col">
                  <div class="card soft bonus">
                    <h3 class="card-title sm">Бонусы к пополнению</h3>
                    <template v-if="tiers.length">
                      <ul class="tiers">
                        <li v-for="tier in tiers" :key="tier.min_usd">
                          <span>от {{ usd(tier.min_usd, 0) }}</span>
                          <b>+{{ tier.percent }}%</b>
                        </li>
                      </ul>
                      <p class="muted small">Бонус зачисляется вместе с платежом и тратится как обычный баланс.</p>
                    </template>
                    <p v-else class="muted small">Сейчас бонусных порогов нет — зачисляется ровно оплаченная сумма.</p>
                  </div>
                  <div class="card soft pay-facts">
                    <ul class="plain">
                      <li><AppIcon name="shield" :size="15" />Оплата через ЮKassa: карта или СБП, 3-D Secure.</li>
                      <li><AppIcon name="spark" :size="15" />Зачисление автоматическое, обычно в течение минуты.</li>
                      <li><AppIcon name="history" :size="15" />Все пополнения видны в истории операций.</li>
                    </ul>
                  </div>
                </div>
              </div>
            </section>

            <section id="history" class="anchor">
              <div class="section-head">
                <h2 class="section-title">История операций</h2>
                <div class="segmented" role="tablist" aria-label="Фильтр">
                  <button
                    v-for="item in filters"
                    :key="item.id"
                    type="button"
                    role="tab"
                    :class="{ on: filter === item.id }"
                    :aria-selected="filter === item.id"
                    @click="setFilter(item.id)"
                  >{{ item.label }}</button>
                </div>
              </div>
              <div class="card history">
                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Когда</th>
                        <th>Операция</th>
                        <th class="num">Токены (вход / выход)</th>
                        <th class="num">Сумма</th>
                      </tr>
                    </thead>
                    <tbody>
                      <template v-if="historyLoading && !history.length">
                        <tr v-for="n in 5" :key="n" class="skeleton-row">
                          <td><span class="skeleton" style="width: 90px" /></td>
                          <td><span class="skeleton" style="width: 160px" /></td>
                          <td class="num"><span class="skeleton" style="width: 80px" /></td>
                          <td class="num"><span class="skeleton" style="width: 60px" /></td>
                        </tr>
                      </template>
                      <tr v-else-if="!history.length">
                        <td colspan="4" class="empty">
                          <template v-if="filter === 'spend'">Запросов ещё не было — подключите приложение и отправьте первый.</template>
                          <template v-else-if="filter === 'income'">Пополнений ещё не было.</template>
                          <template v-else>Пока пусто</template>
                        </td>
                      </tr>
                      <tr v-for="(row, index) in history" :key="index">
                        <td class="nowrap muted">{{ dateTime(row.created_at) }}</td>
                        <td>
                          <span class="op">
                            <span class="op-icon" :class="row.entry_type === 'income' ? 'in' : 'out'">
                              <AppIcon :name="row.entry_type === 'income' ? 'arrow-down' : 'arrow-up'" :size="13" />
                            </span>
                            <template v-if="row.entry_type === 'income'">
                              <span>{{ row.label }}<span v-if="row.note" class="muted small"> · {{ row.note }}</span></span>
                            </template>
                            <code v-else class="model">{{ row.model }}</code>
                          </span>
                        </td>
                        <td class="num muted small">
                          <template v-if="row.entry_type === 'spend' && (row.prompt_tokens || row.completion_tokens)">
                            {{ tokens(row.prompt_tokens) }} / {{ tokens(row.completion_tokens) }}
                          </template>
                          <template v-else>—</template>
                        </td>
                        <td class="num" :class="row.entry_type === 'income' ? 'plus' : 'minus'">
                          {{ row.entry_type === 'income' ? '+' : '−' }}{{ usdSmart(row.amount_usd) }}
                          <span v-if="row.entry_type === 'income' && row.amount_rub" class="muted small rub">{{ rub(row.amount_rub) }}</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-if="hasMore" class="more">
                  <button type="button" class="btn quiet sm" :disabled="historyLoading" @click="loadMore">
                    {{ historyLoading ? 'Загружаем…' : 'Показать ещё' }}
                  </button>
                </div>
              </div>
            </section>

            <section id="help" class="anchor">
              <h2 class="section-title">Помощь</h2>
              <div class="grid help-grid">
                <div class="card faq">
                  <details v-for="item in faq" :key="item.q">
                    <summary><span>{{ item.q }}</span><AppIcon name="chevron" :size="16" class="chev" /></summary>
                    <div class="faq-body" v-html="item.a" />
                  </details>
                </div>
                <div class="card soft support">
                  <h3 class="card-title sm">Поддержка</h3>
                  <p class="muted small">
                    Не получается подключить приложение, не зачислился платёж или потерялся ключ — напишите в чат.
                    Укажите почту, на которую оплачивали, и дату платежа.
                  </p>
                  <div class="contacts">
                    <RouterLink to="/cabinet/support" class="contact">
                      <AppIcon name="help" :size="16" /><span>Открыть чат</span>
                      <span v-if="supportUnread > 0" class="nav-badge">{{ supportUnread > 9 ? '9+' : supportUnread }}</span>
                    </RouterLink>
                    <a v-if="profile.support_username" class="contact" :href="`https://t.me/${profile.support_username}`" target="_blank" rel="noopener">
                      <AppIcon name="telegram" :size="16" /><span>@{{ profile.support_username }}</span><AppIcon name="external" :size="14" class="ext" />
                    </a>
                    <a v-if="profile.support_email" class="contact" :href="`mailto:${profile.support_email}`">
                      <AppIcon name="mail" :size="16" /><span>{{ profile.support_email }}</span>
                    </a>
                  </div>
                  <p class="muted small docs">
                    <RouterLink to="/offer">Оферта</RouterLink> · <RouterLink to="/privacy">Политика</RouterLink> ·
                    <RouterLink to="/consent">Согласие</RouterLink>
                  </p>
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </main>
    <SiteFooter />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import KeyCard from '../components/KeyCard.vue'
import SetupGuide from '../components/SetupGuide.vue'
import SiteFooter from '../components/SiteFooter.vue'
import SiteHeader from '../components/SiteHeader.vue'
import TopupForm from '../components/TopupForm.vue'
import AppIcon from '../components/ui/AppIcon.vue'
import { errorText, webApi } from '../api/web'
import { useSession } from '../composables/useSession'
import { useSupportUnread } from '../composables/useSupportUnread'
import { toast } from '../composables/useToast'
import { dateTime, rub, tokens, usd, usdSmart } from '../utils/format'
import { useHead } from '../utils/useHead'

const PAGE = 10
const router = useRouter()
const { isLoggedIn } = useSession()
const { unread: supportUnread, refreshUnread } = useSupportUnread()

const profile = ref(null)
const loading = ref(false)
const loadError = ref('')
const reissuing = ref(false)
const reissueError = ref('')
const active = ref('overview')
let watching = false
let ticking = false

const sections = [
  { id: 'overview', label: 'Обзор', icon: 'home' },
  { id: 'key', label: 'Ключ', icon: 'key' },
  { id: 'setup', label: 'Подключение', icon: 'plug' },
  { id: 'topup', label: 'Пополнение', icon: 'wallet' },
  { id: 'history', label: 'История', icon: 'history' },
  { id: 'help', label: 'Помощь', icon: 'help' },
]

const filters = [
  { id: 'all', label: 'Все' },
  { id: 'income', label: 'Пополнения' },
  { id: 'spend', label: 'Расходы' },
]
const filter = ref('all')
const history = ref([])
const hasMore = ref(false)
const historyLoading = ref(false)

const supportLabel = computed(() => {
  if (profile.value?.support_username) return `@${profile.value.support_username}`
  return profile.value?.support_email || ''
})
const supportHref = computed(() => {
  if (profile.value?.support_username) return `https://t.me/${profile.value.support_username}`
  return profile.value?.support_email ? `mailto:${profile.value.support_email}` : '#'
})

const weekDays = computed(() => profile.value?.spent_week_usd || [])
const weekMax = computed(() => Math.max(0, ...weekDays.value.map((d) => Number(d.usd) || 0)))
const weekTotal = computed(() => weekDays.value.reduce((sum, d) => sum + (Number(d.usd) || 0), 0))
const daysLeft = computed(() => {
  const perDay = weekTotal.value / Math.max(1, weekDays.value.length)
  if (!perDay || !(profile.value?.balance_usd > 0)) return ''
  const days = Math.floor((profile.value?.balance_usd || 0) / perDay)
  if (days < 1) return 'меньше дня'
  if (days > 365) return 'год и больше'
  return `${days} ${plural(days, 'день', 'дня', 'дней')}`
})
const lowBalance = computed(() => {
  const balance = Number(profile.value?.balance_usd || 0)
  return profile.value?.key && balance > 0 && balance < 1
})
const status = computed(() => {
  const p = profile.value || {}
  if (p.blocked) return { kind: 'bad', text: 'Доступ заблокирован' }
  if (!p.key) return p.balance_usd > 0 ? { kind: 'warn', text: 'Ключ выпускается' } : { kind: 'warn', text: 'Ключ появится после пополнения' }
  if (p.balance_usd <= 0) return { kind: 'bad', text: 'Баланс исчерпан' }
  if (lowBalance.value) return { kind: 'warn', text: 'Баланс на исходе' }
  return { kind: 'ok', text: 'Ключ активен' }
})
const lastRequest = computed(() => {
  const value = profile.value?.last_request_at
  if (!value) return 'ещё не было'
  const diff = Date.now() - new Date(value).getTime()
  if (diff < 60_000) return 'только что'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} мин назад`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} ч назад`
  return dateTime(value)
})
const tiers = computed(() =>
  [...(profile.value?.bonuses || [])]
    .map((tier) => ({ min_usd: Number(tier.min_usd), percent: Number(tier.percent) }))
    .filter((tier) => tier.min_usd > 0 && tier.percent > 0)
    .sort((a, b) => a.min_usd - b.min_usd),
)

const onboarding = computed(() => {
  const p = profile.value
  if (!p || p.last_request_at || p.blocked) return null
  if (!p.key && p.balance_usd <= 0) {
    return {
      title: 'Начните с пополнения',
      lead: 'Ключ доступа выпускается автоматически сразу после первой оплаты — затем останется подключить приложение.',
      steps: [
        { id: 'pay', index: 1, title: 'Пополните баланс', text: 'Любая сумма от минимальной. Карта или СБП, зачисление мгновенное.', target: 'topup', action: 'К пополнению', primary: true },
        { id: 'key', index: 2, title: 'Получите ключ', text: 'Появится в разделе «Ключ доступа» и придёт на почту.' },
        { id: 'setup', index: 3, title: 'Подключите приложение', text: 'Codex и Claude Code — одной командой. Cursor — пошагово в Settings → Models.', target: 'setup', action: 'Посмотреть' },
      ],
    }
  }
  return {
    title: 'Три шага до первого запроса',
    lead: 'Запросов через ваш ключ ещё не было. Вот что нужно сделать, чтобы всё заработало.',
    steps: [
      { id: 'save', index: 1, title: 'Сохраните ключ', text: 'Это и пароль от кабинета, и API-ключ. Положите его в менеджер паролей.', target: 'key', action: 'Показать ключ', primary: true },
      { id: 'setup', index: 2, title: 'Подключите приложение', text: 'Выберите программу, скопируйте команду и вставьте её — остальное произойдёт само.', target: 'setup', action: 'Открыть инструкцию' },
      { id: 'go', index: 3, title: 'Отправьте пробный запрос', text: 'Списание появится в истории через несколько секунд — значит, всё работает.', target: 'history', action: 'История' },
    ],
  }
})

const faq = computed(() => {
  const p = profile.value || {}
  const base = (p.api_base_url || 'https://router.cheap/v1').replace(/\/+$/, '')
  const support = '<a href="/cabinet/support">чат поддержки</a>'
    + (supportLabel.value ? ` или <a href="${supportHref.value}" target="_blank" rel="noopener">${supportLabel.value}</a>` : '')
  const minUsd = Number(p.min_topup_usd || 0)
  const bonusLine = tiers.value.length
    ? `<p>Бонусы к пополнению: ${tiers.value.map((t) => `от ${usd(t.min_usd, 0)} — +${t.percent}%`).join(', ')}. Бонус зачисляется вместе с платежом и тратится как обычный баланс.</p>`
    : ''
  return [
    {
      q: 'Как списываются деньги?',
      a: `<p>Списание идёт в реальном времени: вы отправляете запрос → он уходит поставщику модели → поставщик возвращает ответ и количество токенов → стоимость списывается с баланса.</p>
          <p>Цена — 10% от официального тарифа модели на OpenRouter: отдельно за входные и выходные токены. Полная таблица — на странице <a href="/prices">«Цены»</a>. Каждое списание видно в истории операций с названием модели и объёмом токенов.</p>`,
    },
    {
      q: 'Какие модели доступны и как выбрать нужную?',
      a: `<p>Через один ключ доступны все поддерживаемые модели GPT, Claude, Grok, Gemini и другие. Модель указывается в поле <code>model</code> запроса или в настройках приложения, например <code>gpt-6-astra</code> или <code>claude-opus-5</code>.</p>
          <p>Актуальный список: <code>GET ${base}/models</code> с заголовком <code>Authorization: Bearer &lt;ваш ключ&gt;</code>. Команда из раздела «Подключение» сама выбирает подходящую модель — менять ничего не нужно.</p>`,
    },
    {
      q: 'Ключ не работает — что проверить?',
      a: `<ol>
            <li>Баланс больше нуля? При нуле запросы возвращают ошибку оплаты.</li>
            <li>Адрес API в приложении — именно <code>${base}</code> (для Claude — без <code>/v1</code>).</li>
            <li>Ключ скопирован целиком, без пробелов, и начинается с <code>sk-</code>.</li>
            <li>Вы не перевыпускали ключ? После перевыпуска старый перестаёт работать — обновите его в приложении.</li>
            <li>Соединение обрывается (ECONNRESET, таймауты) — попробуйте запасной адрес, он описан в разделе «Подключение».</li>
          </ol>
          <p>Если всё проверено — напишите в ${support}, приложите текст ошибки.</p>`,
    },
    {
      q: 'Как пополнить баланс?',
      a: `<p>В разделе «Пополнение» введите сумму в долларах или рублях — рядом сразу видны курс и сумма к зачислению. Оплата картой (Visa, MasterCard, МИР) или через СБП в ЮKassa, зачисление автоматическое в течение минуты.</p>
          ${minUsd ? `<p>Минимальная сумма одного пополнения — ${usd(minUsd, 0)}.</p>` : ''}${bonusLine}`,
    },
    {
      q: 'Потерял ключ. Как войти в кабинет?',
      a: `<p>Ключ есть в письме, которое пришло после оплаты. В том же письме кнопка «Войти в личный кабинет» — она работает несколько дней; войдите по ней и при необходимости перевыпустите ключ в разделе «Ключ доступа».</p>
          <p>Если письма нет и ссылка уже не действует — напишите в ${support}: укажите почту, дату и сумму платежа, мы восстановим доступ.</p>`,
    },
    {
      q: 'Безопасно ли это?',
      a: `<ul>
            <li>Платежи проходят через ЮKassa с защитой 3-D Secure; мы не видим и не храним данные карт.</li>
            <li>Мы не храним содержимое ваших запросов и ответов — только модель, объём токенов и сумму списания.</li>
            <li>Ключ можно перевыпустить в любой момент, старый сразу отзывается.</li>
            <li>Никому не передавайте ключ и ссылку для входа из письма: у кого они есть, тот распоряжается балансом.</li>
          </ul>`,
    },
    {
      q: 'Можно ли вернуть деньги?',
      a: `<p>Вы оплачиваете право доступа к сервису, которое предоставляется в момент зачисления баланса, поэтому по умолчанию средства не возвращаются (раздел 9 <a href="/offer">оферты</a>). Если произошла ошибка — например, двойной платёж — напишите в ${support}, разберём индивидуально.</p>`,
    },
  ]
})

function plural(n, one, few, many) {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return one
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few
  return many
}

function barHeight(value) {
  const amount = Number(value) || 0
  if (!amount || !weekMax.value) return '4px'
  return `${Math.max(6, Math.round((amount / weekMax.value) * 96))}px`
}

function shortDate(value) {
  if (!value) return '—'
  const moment = new Date(value)
  return Number.isNaN(moment.getTime()) ? '—' : moment.toLocaleDateString('ru-RU')
}

function keyErrorText(code) {
  return errorText({ code })
}

function scrollTo(id) {
  const node = document.getElementById(id)
  if (!node) return
  node.scrollIntoView({ behavior: 'smooth', block: 'start' })
  if (window.history?.replaceState) window.history.replaceState(null, '', `#${id}`)
}

// Подсветка раздела в меню: активен последний раздел, чей верх прошёл треть экрана.
function updateActive() {
  ticking = false
  const limit = window.innerHeight * 0.33
  let currentId = sections[0].id
  for (const item of sections) {
    const node = document.getElementById(item.id)
    if (node && node.getBoundingClientRect().top <= limit) currentId = item.id
  }
  if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2) {
    currentId = sections[sections.length - 1].id
  }
  active.value = currentId
}

function onScroll() {
  if (ticking) return
  ticking = true
  requestAnimationFrame(updateActive)
}

function watchSections() {
  if (watching) return
  watching = true
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('resize', onScroll)
  updateActive()
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    profile.value = await webApi.me()
    await nextTick()
    watchSections()
  } catch (error) {
    if (error.status === 401) {
      router.replace('/login')
      return
    }
    loadError.value = errorText(error)
  } finally {
    loading.value = false
  }
}

async function fetchHistory(offset) {
  historyLoading.value = true
  try {
    const data = await webApi.history(filter.value, offset, PAGE)
    history.value = offset === 0 ? data.items : [...history.value, ...data.items]
    hasMore.value = Boolean(data.has_more)
  } catch (error) {
    if (error.status === 401) router.replace('/login')
  } finally {
    historyLoading.value = false
  }
}

function setFilter(next) {
  if (filter.value === next) return
  filter.value = next
  history.value = []
  fetchHistory(0)
}

function loadMore() {
  fetchHistory(history.value.length)
}

async function reissue() {
  if (reissuing.value) return
  const ok = window.confirm(
    'Выпустить новый ключ? Старый ключ сразу перестанет работать — и для API, и для входа на сайт. ' +
    'Обязательно сохраните новый ключ.',
  )
  if (!ok) return
  reissuing.value = true
  reissueError.value = ''
  try {
    const result = await webApi.reissueKey()
    profile.value = result.profile
    toast('Новый ключ выпущен — сохраните его')
    scrollTo('key')
  } catch (error) {
    reissueError.value = errorText(error)
  } finally {
    reissuing.value = false
  }
}

onMounted(async () => {
  useHead('Личный кабинет — Aimarket', true)
  if (!isLoggedIn.value) {
    router.replace('/login')
    return
  }
  refreshUnread()
  await Promise.all([load(), fetchHistory(0)])
  const hash = window.location.hash.replace('#', '')
  if (hash && sections.some((item) => item.id === hash)) {
    requestAnimationFrame(() => scrollTo(hash))
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('resize', onScroll)
})
</script>

<style scoped>
.wrap { padding-top: 24px; padding-bottom: 72px; }
.layout {
  display: grid;
  grid-template-columns: 208px minmax(0, 1fr);
  gap: 32px;
  align-items: start;
}
.content { min-width: 0; }
.actions { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 16px; }
.notice { margin-bottom: 18px; }
.notice a { text-decoration: underline; text-underline-offset: 3px; }

/* Боковая навигация */
.side { position: sticky; top: 16px; }
.side-inner { display: flex; flex-direction: column; gap: 18px; }
.side-nav { display: flex; flex-direction: column; gap: 2px; }
.side-nav a {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 10px;
  color: var(--muted-2);
  font-size: 14px;
  font-weight: 600;
  transition: background 0.15s ease, color 0.15s ease;
}
.side-nav a .icon { color: var(--muted); transition: color 0.15s ease; }
.side-nav a:hover { background: rgba(255, 255, 255, 0.7); color: var(--text); }
.side-nav a.on { background: var(--accent); color: var(--bg); }
.side-nav a.on .icon, .side-nav a:hover .icon { color: inherit; }
.side-foot { display: flex; flex-direction: column; gap: 4px; padding: 0 12px; border-top: 1px solid var(--border-strong); padding-top: 14px; }
.side-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  border: 0;
  background: none;
  color: var(--muted);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
  text-align: left;
}
.side-link:hover { color: var(--text); }
.side-link:disabled { cursor: default; }
.nav-badge {
  margin-left: auto;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: var(--danger);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: inline-grid;
  place-items: center;
  line-height: 1;
}
.spin { animation: spin 0.9s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.head { margin-bottom: 18px; }
.head .page-lead { margin-bottom: 0; }
.anchor { scroll-margin-top: 20px; margin-bottom: 40px; }
.section-title { margin: 0 0 14px; font-size: 1.35rem; letter-spacing: -0.03em; }
.section-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }
.section-head .section-title { margin: 0; }
.card-title { margin: 0 0 10px; font-size: 1.15rem; letter-spacing: -0.03em; }
.card-title.sm { font-size: 1rem; }

/* Обзор */
.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
  gap: 24px;
  padding: 26px 28px;
  background: var(--accent);
  color: var(--bg);
  border-color: var(--accent);
  box-shadow: 0 20px 44px rgba(28, 25, 21, 0.22);
}
.hero-label { display: block; color: rgba(244, 241, 234, 0.6); font-size: 12px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }
.hero-balance { display: block; margin: 4px 0 2px; font-size: clamp(2rem, 4vw, 2.8rem); line-height: 1.05; letter-spacing: -0.04em; font-variant-numeric: tabular-nums; }
.hero-rub { display: block; color: rgba(244, 241, 234, 0.65); font-size: 14px; }
.hero-chips { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 16px; }
.chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 5px 11px;
  border-radius: 999px;
  background: rgba(244, 241, 234, 0.1);
  border: 1px solid rgba(244, 241, 234, 0.14);
  font-size: 12.5px;
  font-weight: 600;
}
.chip i { width: 7px; height: 7px; border-radius: 50%; background: rgba(244, 241, 234, 0.5); }
.chip.ok i { background: #6fcf97; box-shadow: 0 0 0 3px rgba(111, 207, 151, 0.2); }
.chip.warn i { background: #f2c94c; box-shadow: 0 0 0 3px rgba(242, 201, 76, 0.2); }
.chip.bad i { background: #eb7a7a; box-shadow: 0 0 0 3px rgba(235, 122, 122, 0.2); }
.hero-actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 20px; }
.btn.light { background: var(--bg); color: var(--text); box-shadow: none; min-height: 42px; padding: 0 18px; font-size: 14px; }
.btn.light:hover { background: #fff; }
.btn.ghost { background: transparent; color: var(--bg); border: 1px solid rgba(244, 241, 234, 0.3); box-shadow: none; min-height: 42px; padding: 0 18px; font-size: 14px; }
.btn.ghost:hover { background: rgba(244, 241, 234, 0.08); }

.hero-chart { display: flex; flex-direction: column; min-width: 0; }
.hero-chart-head { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; color: rgba(244, 241, 234, 0.65); font-size: 13px; }
.hero-chart-head b { color: var(--bg); font-size: 16px; }
.chart { display: flex; align-items: flex-end; gap: 8px; height: 140px; margin-top: auto; padding-top: 10px; }
.bar-wrap { flex: 1; min-width: 0; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; gap: 6px; height: 100%; }
.bar-wrap i { display: block; width: 100%; max-width: 44px; border-radius: 6px 6px 3px 3px; background: rgba(244, 241, 234, 0.32); transition: background 0.15s ease, transform 0.15s ease; }
.bar-wrap:hover i { background: rgba(244, 241, 234, 0.55); }
.bar-wrap i.empty { background: rgba(244, 241, 234, 0.1); }
.bar-wrap i.today:not(.empty) { background: var(--bg); }
.bar-value { font-size: 10.5px; color: rgba(244, 241, 234, 0.55); white-space: nowrap; opacity: 0; transition: opacity 0.15s ease; font-variant-numeric: tabular-nums; }
.bar-wrap:hover .bar-value { opacity: 1; }
.bar-label { font-size: 11px; color: rgba(244, 241, 234, 0.55); text-transform: lowercase; }

.stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 12px; }
.stat { padding: 14px 18px; box-shadow: none; }
.stat span { display: block; }
.stat b { display: block; margin-top: 4px; font-size: 22px; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.stat b.date { font-size: 16px; margin-top: 8px; }
.stats + .notice { margin-top: 14px; margin-bottom: 0; }

.onboarding { margin-top: 16px; padding: 22px 24px; border-color: var(--border-strong); }
.onb-head p { margin: 0 0 16px; }
.onb-steps { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.onb-steps li { display: flex; gap: 12px; align-items: flex-start; }
.onb-steps b { display: block; margin-bottom: 4px; font-size: 15px; }
.onb-steps p { margin: 0 0 10px; }

/* Ключ */
.grid { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr); gap: 16px; }
.key-grid { margin-top: 16px; }
.col { display: flex; flex-direction: column; gap: 16px; }
.plain { list-style: none; margin: 0; padding: 0; font-size: 14px; display: grid; gap: 9px; }
.plain li { display: flex; gap: 10px; align-items: flex-start; color: var(--muted-2); line-height: 1.45; }
.plain .icon { margin-top: 3px; color: var(--muted); }
.plain code { font-size: 12.5px; background: #fff; border: 1px solid var(--border); padding: 0 5px; border-radius: 5px; }
.plain a { text-decoration: underline; text-underline-offset: 3px; font-weight: 600; }
.reissue .btn { margin-top: 4px; }
.reissue p { margin: 0 0 10px; }

/* Пополнение */
.topup-grid { grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr); align-items: start; }
.tiers { list-style: none; margin: 0 0 10px; padding: 0; display: grid; gap: 6px; }
.tiers li { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; border-radius: 8px; background: #fff; border: 1px solid var(--border); font-size: 14px; }
.tiers b { color: var(--ok); }
.bonus p { margin: 0; }

/* История */
.history { padding: 0; overflow: hidden; box-shadow: none; }
.table-wrap { overflow: auto; }
table { width: 100%; border-collapse: collapse; min-width: 600px; }
th, td { text-align: left; padding: 11px 16px; border-bottom: 1px solid #eee6dc; vertical-align: middle; font-size: 14px; }
th { background: var(--surface-soft); color: var(--muted); font-size: 11.5px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
tbody tr:last-child td { border-bottom: 0; }
tbody tr:hover td { background: #fcfaf6; }
td.num, th.num { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
td.nowrap { white-space: nowrap; }
td.empty { text-align: center; color: var(--muted); padding: 32px 14px; }
td.plus { color: var(--ok); font-weight: 600; }
td.minus { font-weight: 600; }
td .rub { display: block; font-weight: 400; }
.op { display: inline-flex; align-items: center; gap: 10px; }
.op-icon { width: 24px; height: 24px; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; flex: 0 0 24px; }
.op-icon.in { background: var(--ok-soft); color: var(--ok); }
.op-icon.out { background: var(--surface-soft); color: var(--muted-2); border: 1px solid var(--border); }
.model { font-size: 13px; background: var(--surface-soft); border: 1px solid var(--border); padding: 1px 7px; border-radius: 6px; }
.more { display: flex; justify-content: center; padding: 12px; border-top: 1px solid var(--border); }
.skeleton-row td { padding-top: 15px; padding-bottom: 15px; }
.skeleton-row .num .skeleton { margin-left: auto; }

/* Помощь */
.help-grid { grid-template-columns: minmax(0, 1.3fr) minmax(0, 0.7fr); align-items: start; }
.faq { padding: 4px 22px; }
.faq details { border-bottom: 1px solid var(--border); }
.faq details:last-child { border-bottom: 0; }
.faq summary { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 0; cursor: pointer; list-style: none; font-weight: 600; font-size: 15px; }
.faq summary::-webkit-details-marker { display: none; }
.faq .chev { color: var(--muted); transition: transform 0.18s ease; flex: 0 0 auto; }
.faq details[open] .chev { transform: rotate(180deg); }
.faq-body { padding: 0 0 16px; font-size: 14.5px; color: var(--muted-2); }
.faq-body :deep(p) { margin: 0 0 8px; }
.faq-body :deep(ol), .faq-body :deep(ul) { margin: 0 0 8px; padding-left: 20px; }
.faq-body :deep(li) { margin-bottom: 4px; }
.faq-body :deep(code) { font-size: 13px; background: var(--surface-soft); border: 1px solid var(--border); padding: 1px 6px; border-radius: 6px; overflow-wrap: anywhere; }
.faq-body :deep(a), .notice a { text-decoration: underline; text-underline-offset: 3px; }
.contacts { display: flex; flex-direction: column; gap: 6px; margin: 12px 0; }
.contact { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 10px; background: #fff; border: 1px solid var(--border); font-size: 14px; font-weight: 600; transition: border-color 0.15s ease; }
.contact:hover { border-color: var(--border-strong); }
.contact span { flex: 1; overflow-wrap: anywhere; }
.contact .ext { color: var(--muted); }
.support p { margin: 0 0 8px; }
.support .docs { margin: 10px 0 0; }
.support .docs a { text-decoration: underline; text-underline-offset: 3px; }

/* Скелетоны при загрузке */
.skeleton { display: block; height: 12px; border-radius: 6px; background: linear-gradient(90deg, #ebe5da 0%, #f5f1ea 50%, #ebe5da 100%); background-size: 200% 100%; animation: shimmer 1.4s linear infinite; }
.skeleton.tall { height: 22px; margin-top: 10px; }
.skeleton-nav { gap: 10px; padding: 4px 12px; }
.skeleton-nav .skeleton { height: 16px; width: 70%; }
.skeleton-hero { height: 220px; border-radius: var(--radius); }
@keyframes shimmer { to { background-position: -200% 0; } }

@media (max-width: 1040px) {
  .layout { grid-template-columns: 1fr; gap: 0; }
  .side { position: sticky; top: 0; z-index: 5; margin: 0 -24px 18px; padding: 8px 24px; background: rgba(244, 241, 234, 0.92); backdrop-filter: blur(8px); border-bottom: 1px solid var(--border); }
  .side-inner { flex-direction: row; align-items: center; gap: 8px; }
  .side-nav { flex-direction: row; gap: 4px; overflow-x: auto; scrollbar-width: none; }
  .side-nav::-webkit-scrollbar { display: none; }
  .side-nav a { padding: 7px 12px; border-radius: 999px; white-space: nowrap; }
  .side-foot { display: none; }
  .anchor { scroll-margin-top: 64px; }
}
@media (max-width: 860px) {
  .hero { grid-template-columns: 1fr; }
  .grid, .topup-grid, .help-grid { grid-template-columns: 1fr; }
  .onb-steps { grid-template-columns: 1fr; }
}
@media (max-width: 560px) {
  .stats { grid-template-columns: 1fr; }
  .hero { padding: 22px 20px; }
}
</style>
