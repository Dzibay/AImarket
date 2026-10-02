<template>
  <div class="site">
    <SiteHeader />
    <main class="site-main">
      <div class="container wrap">
        <template v-if="loading && !profile">
          <h1 class="page-title">Личный кабинет</h1>
          <p class="page-lead">Загружаем данные…</p>
        </template>

        <template v-else-if="loadError && !profile">
          <h1 class="page-title">Личный кабинет</h1>
          <div class="notice bad">{{ loadError }}</div>
          <div class="actions">
            <button type="button" class="btn quiet" @click="load">Повторить</button>
            <RouterLink to="/login" class="btn">Войти заново</RouterLink>
          </div>
        </template>

        <template v-else-if="profile">
          <div class="head">
            <div>
              <h1 class="page-title">Личный кабинет</h1>
              <p class="page-lead">
                <template v-if="profile.email">{{ profile.email }} · </template>
                аккаунт с {{ shortDate(profile.created_at) }}
              </p>
            </div>
            <button type="button" class="btn quiet sm" :disabled="loading" @click="load">
              {{ loading ? 'Обновляем…' : 'Обновить' }}
            </button>
          </div>

          <nav class="section-nav" aria-label="Разделы кабинета">
            <a v-for="item in sections" :key="item.id" :href="`#${item.id}`" @click.prevent="scrollTo(item.id)">{{ item.label }}</a>
          </nav>

          <div v-if="profile.blocked" class="notice bad">
            Доступ заблокирован<template v-if="profile.blocked_reason">: {{ profile.blocked_reason }}</template>.
            Напишите в поддержку<template v-if="supportLabel"> — <a :href="supportHref" target="_blank" rel="noopener">{{ supportLabel }}</a></template>.
          </div>

          <section v-else-if="onboarding" class="card onboarding">
            <div class="onb-head">
              <h2 class="card-title">{{ onboarding.title }}</h2>
              <p class="muted">{{ onboarding.lead }}</p>
            </div>
            <ol class="onb-steps">
              <li v-for="step in onboarding.steps" :key="step.id" :class="{ done: step.done }">
                <span class="onb-mark">{{ step.done ? '✓' : step.index }}</span>
                <div>
                  <b>{{ step.title }}</b>
                  <p class="muted small">{{ step.text }}</p>
                  <button v-if="step.target && !step.done" type="button" class="btn sm" :class="{ quiet: !step.primary }" @click="scrollTo(step.target)">
                    {{ step.action }}
                  </button>
                </div>
              </li>
            </ol>
          </section>

          <section id="overview" class="anchor">
            <div class="stats">
              <div class="card stat">
                <span class="muted small">Баланс</span>
                <b>{{ usd(profile.balance_usd) }}</b>
                <span class="muted small">≈ {{ rub(profile.balance_usd * profile.usd_price_rub) }}</span>
              </div>
              <div class="card stat">
                <span class="muted small">Потрачено сегодня</span>
                <b>{{ usdSmart(profile.spent_today_usd) }}</b>
              </div>
              <div class="card stat">
                <span class="muted small">За месяц</span>
                <b>{{ usdSmart(profile.spent_month_usd) }}</b>
              </div>
              <div class="card stat">
                <span class="muted small">Последний запрос</span>
                <b class="date">{{ dateTime(profile.last_request_at) }}</b>
              </div>
            </div>
            <p v-if="lowBalance" class="notice">
              Баланс почти закончился: при нуле запросы начнут возвращать ошибку. Пополните заранее —
              <a href="#topup" @click.prevent="scrollTo('topup')">перейти к пополнению</a>.
            </p>
          </section>

          <section id="key" class="anchor">
            <h2 class="section-title">Ключ доступа</h2>
            <div class="grid">
              <div class="col">
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
                      Ключ выпускается — нажмите «Обновить» через минуту. Если он так и не появился, напишите в поддержку.
                    </template>
                    <template v-else>
                      Ключ появится автоматически после первого пополнения баланса — его сразу можно будет
                      вставить в приложение и использовать для входа на сайт.
                    </template>
                  </p>
                  <p v-if="profile.key_error" class="error-text">{{ keyErrorText(profile.key_error) }}</p>
                </div>
              </div>
              <div class="col">
                <div class="card soft usage">
                  <h2 class="card-title">Как расходуется баланс</h2>
                  <ul class="plain">
                    <li>Один ключ открывает все модели — модель выбирается в поле <code>model</code> запроса.</li>
                    <li>Списание идёт за токены по ценам поставщиков, сразу после каждого ответа.</li>
                    <li>Ключ действует, пока на балансе есть средства; при нуле запросы останавливаются.</li>
                    <li v-if="profile.key && profile.key.spent_usd != null">
                      Через этот ключ потрачено <b>{{ usdSmart(profile.key.spent_usd) }}</b>.
                    </li>
                  </ul>
                </div>
                <div v-if="profile.key" class="card reissue">
                  <h2 class="card-title">Перевыпуск ключа</h2>
                  <p class="muted small">
                    Если ключ попал к посторонним — выпустите новый. Старый сразу перестанет работать и для API,
                    и для входа на сайт, баланс сохранится. После перевыпуска обновите ключ в приложениях и
                    сохраните новый.
                  </p>
                  <p v-if="reissueError" class="error-text">{{ reissueError }}</p>
                  <button type="button" class="btn danger sm" :disabled="reissuing" @click="reissue">
                    {{ reissuing ? 'Выпускаем…' : 'Перевыпустить ключ' }}
                  </button>
                </div>
              </div>
            </div>
          </section>

          <section id="setup" class="anchor">
            <h2 class="section-title">Подключение</h2>
            <SetupGuide :secret="profile.key?.secret || ''" :base-url="profile.api_base_url" />
          </section>

          <section id="topup" class="anchor">
            <h2 class="section-title">Пополнение</h2>
            <div class="grid">
              <div class="col">
                <TopupForm v-if="!profile.blocked" mode="topup" :config="profile" />
                <div v-else class="card"><p class="muted">Пополнение недоступно: аккаунт заблокирован.</p></div>
              </div>
              <div class="col">
                <div class="card week">
                  <h2 class="card-title">Расход за 7 дней</h2>
                  <div class="chart">
                    <div
                      v-for="day in profile.spent_week_usd"
                      :key="day.date"
                      class="bar-wrap"
                      :title="`${day.label}: ${usdSmart(day.usd)}`"
                    >
                      <i :class="{ empty: !day.usd, today: day.is_today }" :style="{ height: barHeight(day.usd) }" />
                      <span>{{ day.label.slice(0, 5) }}</span>
                    </div>
                  </div>
                  <p class="muted small chart-note">
                    Всего за неделю: <b>{{ usdSmart(weekTotal) }}</b>.
                    <template v-if="weekTotal > 0 && profile.balance_usd > 0">
                      Такого темпа хватит примерно на {{ daysLeft }}.
                    </template>
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section id="history" class="anchor">
            <h2 class="section-title">История операций</h2>
            <section class="card history">
              <div class="history-head">
                <p class="muted small history-lead">
                  Пополнения — зелёным, списания за запросы — с названием модели и объёмом токенов (вход / выход).
                </p>
                <div class="filters">
                  <button
                    v-for="item in filters"
                    :key="item.id"
                    type="button"
                    :class="{ on: filter === item.id }"
                    @click="setFilter(item.id)"
                  >{{ item.label }}</button>
                </div>
              </div>
              <div class="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Когда</th>
                      <th>Операция</th>
                      <th class="num">Токены</th>
                      <th class="num">Сумма</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-if="historyLoading && !history.length">
                      <td colspan="4" class="empty">Загружаем…</td>
                    </tr>
                    <tr v-else-if="!history.length">
                      <td colspan="4" class="empty">
                        <template v-if="filter === 'spend'">Запросов ещё не было — подключите приложение и отправьте первый.</template>
                        <template v-else-if="filter === 'income'">Пополнений ещё не было.</template>
                        <template v-else>Пока пусто</template>
                      </td>
                    </tr>
                    <tr v-for="(row, index) in history" :key="index">
                      <td class="nowrap">{{ dateTime(row.created_at) }}</td>
                      <td>
                        <template v-if="row.entry_type === 'income'">
                          {{ row.label }}<span v-if="row.note" class="muted small"> · {{ row.note }}</span>
                        </template>
                        <template v-else>{{ row.model }}</template>
                      </td>
                      <td class="num muted small">
                        <template v-if="row.entry_type === 'spend' && (row.prompt_tokens || row.completion_tokens)">
                          {{ tokens(row.prompt_tokens) }} / {{ tokens(row.completion_tokens) }}
                        </template>
                        <template v-else>—</template>
                      </td>
                      <td class="num" :class="row.entry_type === 'income' ? 'plus' : 'minus'">
                        {{ row.entry_type === 'income' ? '+' : '−' }}{{ usdSmart(row.amount_usd) }}
                        <span v-if="row.entry_type === 'income' && row.amount_rub" class="muted small">· {{ rub(row.amount_rub) }}</span>
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
            </section>
          </section>

          <section id="help" class="anchor">
            <h2 class="section-title">Помощь</h2>
            <div class="grid help-grid">
              <div class="col">
                <div class="card faq">
                  <details v-for="item in faq" :key="item.q">
                    <summary>{{ item.q }}</summary>
                    <div class="faq-body" v-html="item.a" />
                  </details>
                </div>
              </div>
              <div class="col">
                <div class="card soft support">
                  <h2 class="card-title">Поддержка</h2>
                  <p class="muted small">
                    Не получается подключить приложение, не зачислился платёж или потерялся ключ — напишите нам.
                    Укажите почту, на которую оплачивали, и дату платежа: так мы найдём аккаунт быстрее.
                  </p>
                  <ul class="plain contacts">
                    <li v-if="profile.support_username">
                      Telegram: <a :href="`https://t.me/${profile.support_username}`" target="_blank" rel="noopener">@{{ profile.support_username }}</a>
                    </li>
                    <li v-if="profile.support_email">
                      Почта: <a :href="`mailto:${profile.support_email}`">{{ profile.support_email }}</a>
                    </li>
                    <li v-if="!profile.support_username && !profile.support_email" class="muted">Контакты поддержки скоро появятся.</li>
                  </ul>
                  <p v-if="profile.bot_url" class="muted small">
                    Есть и <a :href="profile.bot_url" target="_blank" rel="noopener">Telegram-бот</a> с теми же возможностями.
                    Учтите: аккаунты сайта и бота раздельные — баланс, пополненный здесь, в боте не отображается.
                  </p>
                  <p class="muted small docs">
                    Документы: <RouterLink to="/offer">оферта</RouterLink> · <RouterLink to="/privacy">политика</RouterLink> ·
                    <RouterLink to="/consent">согласие</RouterLink>
                  </p>
                </div>
              </div>
            </div>
          </section>
        </template>
      </div>
    </main>
    <SiteFooter />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import KeyCard from '../components/KeyCard.vue'
import SetupGuide from '../components/SetupGuide.vue'
import SiteFooter from '../components/SiteFooter.vue'
import SiteHeader from '../components/SiteHeader.vue'
import TopupForm from '../components/TopupForm.vue'
import { errorText, webApi } from '../api/web'
import { useSession } from '../composables/useSession'
import { dateTime, rub, tokens, usd, usdSmart } from '../utils/format'
import { useHead } from '../utils/useHead'

const PAGE = 10
const router = useRouter()
const { isLoggedIn } = useSession()

const profile = ref(null)
const loading = ref(false)
const loadError = ref('')
const reissuing = ref(false)
const reissueError = ref('')

const sections = [
  { id: 'overview', label: 'Обзор' },
  { id: 'key', label: 'Ключ' },
  { id: 'setup', label: 'Подключение' },
  { id: 'topup', label: 'Пополнение' },
  { id: 'history', label: 'История' },
  { id: 'help', label: 'Помощь' },
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
  if (!perDay) return ''
  const days = Math.floor((profile.value?.balance_usd || 0) / perDay)
  if (days < 1) return 'меньше дня'
  if (days > 365) return 'год и больше'
  return `${days} ${plural(days, 'день', 'дня', 'дней')}`
})
const lowBalance = computed(() => {
  const balance = Number(profile.value?.balance_usd || 0)
  return profile.value?.key && balance > 0 && balance < 1
})

const onboarding = computed(() => {
  const p = profile.value
  if (!p || p.last_request_at) return null
  const hasKey = Boolean(p.key)
  if (!hasKey && p.balance_usd <= 0) {
    return {
      title: 'Начните с пополнения',
      lead: 'Ключ доступа выпускается автоматически сразу после первой оплаты — затем останется вставить его в приложение.',
      steps: [
        { id: 'pay', index: 1, title: 'Пополните баланс', text: 'Любая сумма от минимальной. Оплата картой или СБП, зачисление мгновенное.', target: 'topup', action: 'К пополнению', primary: true },
        { id: 'key', index: 2, title: 'Получите ключ', text: 'Появится в разделе «Ключ доступа» и придёт на почту.' },
        { id: 'setup', index: 3, title: 'Подключите приложение', text: 'Готовые установщики для Cursor, Codex, Claude Code и других — в разделе «Подключение».', target: 'setup', action: 'Посмотреть инструкцию' },
      ],
    }
  }
  return {
    title: 'Три шага до первого запроса',
    lead: 'Запросов через ваш ключ ещё не было. Вот что нужно сделать, чтобы всё заработало.',
    steps: [
      { id: 'save', index: 1, title: 'Сохраните ключ', text: 'Это и пароль от кабинета, и API-ключ. Положите его в менеджер паролей или заметки.', target: 'key', action: 'Показать ключ', done: false, primary: true },
      { id: 'setup', index: 2, title: 'Подключите приложение', text: 'Выберите программу и систему — скачайте установщик, он сам пропишет ключ и адрес API.', target: 'setup', action: 'Открыть инструкцию' },
      { id: 'go', index: 3, title: 'Отправьте пробный запрос', text: 'Списание появится в истории операций через несколько секунд — значит, всё работает.', target: 'history', action: 'История' },
    ],
  }
})

const faq = computed(() => {
  const p = profile.value || {}
  const base = (p.api_base_url || 'https://router.cheap/v1').replace(/\/+$/, '')
  const support = supportLabel.value ? `<a href="${supportHref.value}" target="_blank" rel="noopener">${supportLabel.value}</a>` : 'поддержку'
  const minUsd = Number(p.min_topup_usd || 0)
  const tiers = Array.isArray(p.bonuses) ? p.bonuses : []
  const bonusLine = tiers.length
    ? `<p>Бонусы к пополнению: ${tiers.map((t) => `от ${usd(t.min_usd, 0)} — +${t.percent}%`).join(', ')}. Бонус зачисляется вместе с платежом и тратится как обычный баланс.</p>`
    : ''
  return [
    {
      q: 'Как списываются деньги?',
      a: `<p>Списание идёт в реальном времени: вы отправляете запрос → он уходит поставщику модели → поставщик возвращает ответ и количество токенов → стоимость списывается с баланса.</p>
          <p>Цены — официальные цены поставщиков (OpenAI, Anthropic и других) без наценки, вы платите только за токены. Каждое списание видно в истории операций с названием модели и объёмом токенов.</p>`,
    },
    {
      q: 'Какие модели доступны и как выбрать нужную?',
      a: `<p>Через один ключ доступны все поддерживаемые модели GPT, Claude, Grok, Gemini и другие. Модель указывается в поле <code>model</code> запроса или в настройках приложения, например <code>gpt-5.6-sol</code> или <code>claude-opus-5</code>.</p>
          <p>Актуальный список: <code>GET ${base}/models</code> с заголовком <code>Authorization: Bearer &lt;ваш ключ&gt;</code>. Установщики из раздела «Подключение» сами подставляют список моделей.</p>`,
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
  return `${Math.max(6, Math.round((amount / weekMax.value) * 110))}px`
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

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    profile.value = await webApi.me()
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
  await Promise.all([load(), fetchHistory(0)])
  const hash = window.location.hash.replace('#', '')
  if (hash && sections.some((item) => item.id === hash)) {
    requestAnimationFrame(() => scrollTo(hash))
  }
})
</script>

<style scoped>
.wrap { padding-top: 32px; padding-bottom: 72px; }
.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.head .page-lead { margin-bottom: 12px; }
.actions { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 16px; }
.notice { margin-bottom: 18px; }
.notice a { text-decoration: underline; text-underline-offset: 3px; }

.section-nav {
  position: sticky;
  top: 0;
  z-index: 5;
  display: flex;
  gap: 4px;
  overflow-x: auto;
  margin: 0 -24px 22px;
  padding: 10px 24px;
  background: rgba(244, 241, 234, 0.92);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
  scrollbar-width: none;
}
.section-nav::-webkit-scrollbar { display: none; }
.section-nav a {
  flex: 0 0 auto;
  padding: 7px 14px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 600;
  color: var(--muted-2);
  white-space: nowrap;
}
.section-nav a:hover { background: #fff; color: var(--text); }

.anchor { scroll-margin-top: 72px; margin-bottom: 36px; }
.section-title { margin: 0 0 14px; font-size: 1.35rem; letter-spacing: -0.03em; }
.card-title { margin: 0 0 10px; font-size: 1.15rem; letter-spacing: -0.03em; }

.onboarding { margin-bottom: 28px; padding: 24px; border-color: var(--border-strong); }
.onb-head p { margin: 0 0 16px; }
.onb-steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}
.onb-steps li { display: flex; gap: 12px; align-items: flex-start; }
.onb-steps li.done { opacity: 0.6; }
.onb-steps b { display: block; margin-bottom: 4px; }
.onb-steps p { margin: 0 0 10px; }
.onb-mark {
  flex: 0 0 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--accent);
  color: var(--bg);
  font-weight: 700;
  font-size: 14px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}
.stat { padding: 16px 18px; }
.stat span { display: block; }
.stat b { display: block; margin: 4px 0 2px; font-size: 26px; letter-spacing: -0.03em; overflow-wrap: anywhere; }
.stat b.date { font-size: 17px; margin-top: 8px; }

.grid {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
  gap: 20px;
}
.col { display: flex; flex-direction: column; gap: 20px; }
.reissue .btn { margin-top: 6px; }
.plain { margin: 0; padding-left: 18px; font-size: 15px; }
.plain li { margin-bottom: 6px; }
.usage code { font-size: 13px; background: #fff; border: 1px solid var(--border); padding: 1px 6px; border-radius: 6px; }

.chart {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  height: 150px;
  padding-top: 8px;
}
.bar-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  height: 100%;
}
.bar-wrap i {
  display: block;
  width: 100%;
  border-radius: 6px 6px 0 0;
  background: linear-gradient(180deg, #3a342c 0%, var(--accent) 100%);
}
.bar-wrap i.empty { background: #e7e0d6; }
.bar-wrap i.today:not(.empty) { background: linear-gradient(180deg, #7a7267 0%, #5c564c 100%); }
.bar-wrap span { font-size: 11px; color: var(--muted); }
.chart-note { margin: 12px 0 0; }

.history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.history-lead { margin: 0; flex: 1 1 320px; }
.filters { display: flex; gap: 6px; flex-wrap: wrap; }
.filters button {
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
.filters button.on { background: var(--accent); color: var(--bg); border-color: var(--accent); }
.table-wrap {
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: #fff;
}
table { width: 100%; border-collapse: collapse; min-width: 560px; }
th, td { text-align: left; padding: 11px 14px; border-bottom: 1px solid #eee6dc; vertical-align: middle; }
th {
  background: var(--surface-soft);
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
tbody tr:last-child td { border-bottom: 0; }
td.num, th.num { text-align: right; white-space: nowrap; }
td.nowrap { white-space: nowrap; }
td.empty { text-align: center; color: var(--muted); padding: 28px 14px; }
td.plus { color: var(--ok); font-weight: 600; }
td.minus { font-weight: 600; }
.more { display: flex; justify-content: center; margin-top: 14px; }

.faq { padding: 8px 24px; }
.faq details { border-bottom: 1px solid var(--border); padding: 14px 0; }
.faq details:last-child { border-bottom: 0; }
.faq summary { cursor: pointer; font-weight: 600; font-size: 15px; }
.faq-body { margin-top: 10px; font-size: 15px; color: var(--muted-2); }
.faq-body :deep(p) { margin: 0 0 8px; }
.faq-body :deep(ol), .faq-body :deep(ul) { margin: 0 0 8px; padding-left: 20px; }
.faq-body :deep(li) { margin-bottom: 4px; }
.faq-body :deep(code) { font-size: 13px; background: var(--surface-soft); border: 1px solid var(--border); padding: 1px 6px; border-radius: 6px; overflow-wrap: anywhere; }
.faq-body :deep(a), .support a, .notice a { text-decoration: underline; text-underline-offset: 3px; }
.contacts { list-style: none; padding: 0; margin: 10px 0 14px; font-size: 15px; }
.contacts li { margin-bottom: 6px; }
.support .docs { margin: 10px 0 0; }

@media (max-width: 960px) {
  .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .grid { grid-template-columns: 1fr; }
  .onb-steps { grid-template-columns: 1fr; }
}
@media (max-width: 520px) {
  .stats { grid-template-columns: 1fr; }
}
</style>
