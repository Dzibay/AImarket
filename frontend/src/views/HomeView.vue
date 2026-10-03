<template>
  <div class="site">
    <SiteHeader />
    <main class="site-main">
      <ModelsHero @choose="scrollToTopup" />

      <section class="container hero">
        <div class="hero-how">
          <p class="eyebrow">Как это работает</p>
          <h2>Пополнить баланс — просто</h2>
          <p class="lead">
            Несколько простых шагов, и вы сможете начать использовать все возможности платформы.
          </p>

          <ol class="steps">
            <li class="step">
              <span class="step-icon" aria-hidden="true">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="6" width="18" height="13" rx="2.5" /><path d="M3 10h18" /><path d="M7 15h3" /></svg>
              </span>
              <span class="step-num">Шаг 1</span>
              <b>Пополните баланс</b>
              <span class="step-text">
                Сумма в долларах или рублях, курс и точная сумма к оплате — сразу в форме.
                Оплата картой через ЮKassa. Минимум — {{ usd(minUsd, 0) }}.
              </span>
            </li>
            <li class="step">
              <span class="step-icon" aria-hidden="true">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.1 0l2.8-2.8a5 5 0 0 0-7.1-7.1L11.5 4.4" /><path d="M14 11a5 5 0 0 0-7.1 0l-2.8 2.8a5 5 0 0 0 7.1 7.1l1.3-1.3" /></svg>
              </span>
              <span class="step-num">Шаг 2</span>
              <b>Получите ключ и Base URL</b>
              <span class="step-text">
                Сайт покажет ключ сразу после оплаты, на почту придёт письмо с ключом и входом в кабинет.
              </span>
            </li>
            <li class="step">
              <span class="step-icon" aria-hidden="true">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M8 7l-5 5 5 5" /><path d="M16 7l5 5-5 5" /><path d="M14 4l-4 16" /></svg>
              </span>
              <span class="step-num">Шаг 3</span>
              <b>Подключите приложения</b>
              <span class="step-text">
                В Cursor, Codex, Claude Code или другом клиенте указываете наш адрес сервера и ключ.
                Готовые инструкции — в личном кабинете.
              </span>
            </li>
            <li class="step">
              <span class="step-icon" aria-hidden="true">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" /></svg>
              </span>
              <span class="step-num">Шаг 4</span>
              <b>Работайте и следите за расходом</b>
              <span class="step-text">
                Каждый запрос списывается по тарифу модели. В кабинете — остаток, расход по дням и история.
              </span>
            </li>
          </ol>

          <aside v-if="config?.bot_url" class="bot-card">
            <div class="bot-copy">
              <strong>Уведомления о балансе, история, поддержка</strong>
              <span>Всё это — в Telegram-боте</span>
            </div>
            <a class="btn sm" :href="botUrl" target="_blank" rel="noopener">Открыть бота</a>
          </aside>
        </div>

        <div id="topup" class="hero-form">
          <TopupForm mode="checkout" :config="config" />
        </div>
      </section>

      <section class="container block save">
        <p class="save-eyebrow">Тарифы и лимиты</p>
        <h2 class="save-title">Если вы тратите на API {{ usd(100, 0) }} в месяц</h2>
        <p class="save-lead">
          Этого достаточно, чтобы получить доступ ко всем возможностям платформы.
        </p>

        <div class="save-grid">
          <article class="save-card was">
            <div class="save-media">
              <img src="/save-icon-was.jpg" alt="" loading="lazy">
            </div>
            <div class="save-body">
              <span class="label">Было</span>
              <b class="save-value">{{ usd(100, 0) }} ≈ {{ rub(spendWas, 0) }}</b>
              <span class="save-sub">в месяц у других провайдеров</span>
            </div>
          </article>
          <article class="save-card now">
            <div class="save-media">
              <img src="/save-icon-now.jpg" alt="" loading="lazy">
            </div>
            <div class="save-body">
              <span class="label">Стало</span>
              <b class="save-value">{{ usd(100, 0) }} = {{ rub(spendNow, 0) }}</b>
              <span class="save-sub">в месяц в Aimarket</span>
            </div>
          </article>
          <article class="save-card result">
            <div class="save-media">
              <img src="/save-icon-result.jpg" alt="" loading="lazy">
              <span class="save-pill">−{{ savePct }}%</span>
            </div>
            <div class="save-body">
              <span class="label">Итог</span>
              <b class="save-value">Экономия {{ rub(spendSave, 0) }}</b>
              <span class="save-sub">ежемесячно при том же доступе к моделям</span>
            </div>
          </article>
        </div>

        <div class="save-footer">
          <p class="save-note">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 10v6" /><path d="M12 7h.01" /></svg>
            <span>
              Нет ограничений: можно пополнить хоть на {{ usd(1000, 0) }} в токены.
              <template v-if="bonusFrom1000">
                При пополнении от {{ usd(bonusFrom1000.min_usd, 0) }} даём
                +{{ bonusFrom1000.percent }}% дополнительно — на балансе будет
                {{ usd(bonusFrom1000.min_usd * (1 + bonusFrom1000.percent / 100), 0) }}.
              </template>
            </span>
          </p>
          <button type="button" class="btn save-cta" @click="scrollToTopup">
            Пополнить баланс <span class="arrow-glyph" aria-hidden="true">→</span>
          </button>
        </div>
      </section>

      <section class="container block catch">
        <p class="save-eyebrow">В чём подвох?</p>
        <h2 class="save-title catch-title">Подвоха нет — есть простая экономика</h2>
        <p class="save-lead">
          Мы не используем «китайские копии», не подменяем модели и не работаем по серым схемам.
          Вы получаете прямой доступ к оригинальным нейросетям Anthropic, OpenAI, Google и других.
        </p>

        <div class="catch-grid">
          <article class="catch-main">
            <div class="catch-main-body">
              <span class="label">Прозрачность</span>
              <h3>Секрет цены прост</h3>
              <p>
                Крупные компании покупают корпоративные квоты на API, и часть токенов по условиям
                контрактов просто сгорает. Мы выкупаем эти «остатки» оптом и монетизируем то,
                что иначе было бы потеряно.
              </p>
              <p class="catch-accent">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 10v6" /><path d="M12 7h.01" /></svg>
                <span>Поэтому мы отдаём их вам по цене 10% от официального тарифа.</span>
              </p>
            </div>
            <div class="catch-main-media" aria-hidden="true">
              <img src="/catch-main.jpg" alt="" loading="lazy">
            </div>
          </article>

          <ul class="catch-features">
            <li class="catch-feature">
              <span class="catch-feature-img" aria-hidden="true"><img src="/catch-original.jpg" alt="" loading="lazy"></span>
              <div>
                <b>Оригинальные модели</b>
                <span>Opus, Sonnet, GPT, Gemini — без подмен</span>
              </div>
            </li>
            <li class="catch-feature">
              <span class="catch-feature-img" aria-hidden="true"><img src="/catch-speed.jpg" alt="" loading="lazy"></span>
              <div>
                <b>Высокая скорость ответа</b>
                <span>Собственные быстрые эндпоинты</span>
              </div>
            </li>
            <li class="catch-feature">
              <span class="catch-feature-img" aria-hidden="true"><img src="/catch-stats.jpg" alt="" loading="lazy"></span>
              <div>
                <b>Прозрачная статистика</b>
                <span>Расходы и история запросов в кабинете</span>
              </div>
            </li>
          </ul>
        </div>

        <button type="button" class="btn block-cta" @click="scrollToTopup">
          Пополнить баланс <span class="arrow-glyph" aria-hidden="true">→</span>
        </button>
      </section>

      <section class="container block">
        <div class="block-head">
          <h2>После оплаты вы получите</h2>
          <p class="muted">Всё нужное для старта — сразу, без ожидания модерации.</p>
        </div>
        <div class="cards5">
          <article class="info">
            <span class="num">01</span>
            <h3>API-ключ</h3>
            <p>Сразу на экране и дублируется на почту.</p>
          </article>
          <article class="info">
            <span class="num">02</span>
            <h3>Base URL</h3>
            <p>Для подключения к Cursor, Claude Code и другим приложениям.</p>
          </article>
          <article class="info">
            <span class="num">03</span>
            <h3>Личный кабинет</h3>
            <p>Статистика расходов, история запросов, пополнение баланса.</p>
          </article>
          <article class="info">
            <span class="num">04</span>
            <h3>Инструкции</h3>
            <p>Готовые шаги для Cursor, Claude Code и Codex.</p>
          </article>
          <article class="info">
            <span class="num">05</span>
            <h3>Поддержка</h3>
            <p>Поможем с подключением и использованием ключа.</p>
          </article>
        </div>
        <button type="button" class="btn block-cta" @click="scrollToTopup">Пополнить баланс</button>
      </section>

      <section v-if="tiers.length" class="container block">
        <div class="block-head">
          <h2>Бонусы к пополнению</h2>
          <p class="muted">Чем больше сумма, тем больше зачислим сверху. Бонус виден в форме до оплаты.</p>
        </div>
        <div class="tiers">
          <article v-for="tier in tiers" :key="tier.min_usd" class="tier">
            <b>+{{ tier.percent }}%</b>
            <span>при пополнении от {{ usd(tier.min_usd, 0) }}</span>
            <small class="muted">{{ usd(tier.min_usd, 0) }} → {{ usd(tier.min_usd * (1 + tier.percent / 100)) }} на балансе</small>
          </article>
        </div>
        <button type="button" class="btn quiet block-cta" @click="scrollToTopup">Пополнить баланс</button>
      </section>

      <section class="container block faq">
        <div class="block-head">
          <h2>Частые вопросы</h2>
        </div>
        <div class="faq-list">
          <details>
            <summary>Это официальный Claude или OpenAI?</summary>
            <p>
              Нет. Aimarket — сторонний API-провайдер. Мы даём вам собственный ключ, который работает через
              наш прокси-шлюз к тем же моделям Claude, GPT и Gemini. Вы получаете тот же результат, но
              платите рублями и через один ключ.
            </p>
          </details>
          <details>
            <summary>Почему курс 1$ = {{ rub(price || 10, 0) }} — это выгодно?</summary>
            <p>
              Вы пополняете баланс в рублях, а списание идёт в долларах по тарифам самих провайдеров.
              Курс пополнения фиксирован сайтом и не зависит от курса ЦБ. Вы заранее видите, сколько
              долларов зачислится на баланс.
            </p>
          </details>
          <details>
            <summary>Что я получу сразу после оплаты?</summary>
            <p>
              Три вещи: API-ключ, Base URL и доступ к личному кабинету. Ключ и адрес сервера появятся на
              экране и продублируются на почту. В кабинете — инструкции для Cursor, Claude Code и Codex,
              статистика расходов и история запросов.
            </p>
          </details>
          <details>
            <summary>Как подключить к Cursor?</summary>
            <p>
              Откройте настройки Cursor → Models → OpenAI API Key. Вставьте ваш ключ и укажите Base URL:
              <code>https://api.market-aii.ru</code>. Выберите модель — и работайте. Готовые инструкции
              для всех приложений — в личном кабинете.
            </p>
          </details>
          <details>
            <summary>Какие приложения поддерживаются?</summary>
            <p>
              Любые, где можно указать свой API-ключ и адрес сервера: Cursor, Claude Code, Codex,
              Claude Desktop, OpenCode, Hermes, Droid, Pi, Grok Build. Поддерживаются форматы
              OpenAI Chat Completions, Claude Messages и Google Gemini.
            </p>
          </details>
          <details>
            <summary>Безопасно ли это?</summary>
            <p>
              Ваш ключ хранится в зашифрованном виде. Мастер-ключи провайдеров не передаются и не
              логируются. Если ключ скомпрометирован — перевыпускаете в один клик.
            </p>
          </details>
          <details>
            <summary>Ключ не работает — что делать?</summary>
            <p>
              Проверьте, что вы указали правильный Base URL и что на балансе есть средства. Если не
              помогает — напишите в Telegram-бот, поддержка ответит в течение дня.
            </p>
          </details>
          <details>
            <summary>Что если я потеряю ключ?</summary>
            <p>
              Если вы залогинены в кабинете — перевыпустите ключ там. Если нет — найдите письмо с кнопкой
              входа или напишите в поддержку, указав почту и сумму последней оплаты.
            </p>
          </details>
          <details>
            <summary>Можно ли вернуть деньги?</summary>
            <p>
              Возврат неиспользованного баланса — в течение 14 дней с момента оплаты, если баланс не был
              израсходован. Обращайтесь в поддержку через Telegram-бота. Деньги вернутся на ту же карту,
              которой оплачивали.
            </p>
          </details>
        </div>
      </section>
    </main>
    <SiteFooter />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import ModelsHero from '../components/ModelsHero.vue'
import SiteFooter from '../components/SiteFooter.vue'
import SiteHeader from '../components/SiteHeader.vue'
import TopupForm from '../components/TopupForm.vue'
import { webApi } from '../api/web'
import { rub, usd } from '../utils/format'
import { botUrlWithReferral } from '../utils/referral'
import { useHead } from '../utils/useHead'

const config = ref(null)
const botUrl = computed(() => botUrlWithReferral(config.value?.bot_url || ''))
const price = computed(() => Number(config.value?.usd_price_rub || 0))
const minUsd = computed(() => Number(config.value?.min_topup_usd || 10))
const tiers = computed(() =>
  [...(config.value?.bonuses || [])]
    .map((tier) => ({ min_usd: Number(tier.min_usd), percent: Number(tier.percent) }))
    .filter((tier) => tier.min_usd > 0 && tier.percent > 0)
    .sort((a, b) => a.min_usd - b.min_usd),
)
const bonusFrom1000 = computed(() =>
  [...tiers.value].reverse().find((tier) => tier.min_usd >= 1000)
  || tiers.value.find((tier) => tier.min_usd >= 500)
  || null,
)

// Скидка 90% → «было» ≈ в 10 раз дороже нашего курса пополнения.
const rate = computed(() => price.value || 10)
const spendNow = computed(() => Math.round(100 * rate.value))
const spendWas = computed(() => Math.round(100 * rate.value * 10))
const spendSave = computed(() => spendWas.value - spendNow.value)
const savePct = computed(() => (spendWas.value ? Math.round((spendSave.value / spendWas.value) * 100) : 0))

function scrollToTopup() {
  const el = document.getElementById('topup')
  if (!el) return
  el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  const input = el.querySelector('input')
  if (input) setTimeout(() => input.focus({ preventScroll: true }), 350)
}

onMounted(async () => {
  useHead('Aimarket — токены со скидкой 90%')
  let meta = document.querySelector('meta[name="description"]')
  if (!meta) {
    meta = document.createElement('meta')
    meta.name = 'description'
    document.head.append(meta)
  }
  meta.content = 'Aimarket — один ключ ко всем ИИ со скидкой 90%. Пополнение в рублях, Cursor, Claude Code, Codex.'
  try {
    config.value = await webApi.config()
  } catch {
    config.value = { sales_open: false, usd_price_rub: 0, min_topup_usd: 10 }
  }
})
</script>

<style scoped>
.hero {
  padding-top: 56px;
  padding-bottom: 56px;
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(360px, 0.8fr);
  gap: 48px;
  align-items: start;
}
.hero-how .eyebrow {
  display: inline-block;
  margin: 0 0 14px;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.6);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
}
.hero-how h2 {
  margin: 0 0 10px;
  font-size: clamp(1.8rem, 3vw, 2.4rem);
  line-height: 1.1;
  letter-spacing: -0.035em;
}
.hero-how .lead {
  margin: 0 0 26px;
  max-width: 40rem;
  color: var(--muted-2);
  font-size: 1rem;
  line-height: 1.5;
}

.steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.step {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 20px 20px 22px;
  border-radius: 20px;
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.6);
  box-shadow: 0 10px 30px rgba(28, 25, 21, 0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}
.step:hover {
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.85);
  box-shadow: 0 16px 40px rgba(28, 25, 21, 0.08);
}
.step-icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  margin-bottom: 14px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid var(--border);
  color: var(--text);
}
.step-num {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 6px;
}
.step b {
  font-size: 1rem;
  letter-spacing: -0.02em;
  line-height: 1.3;
  margin-bottom: 8px;
}
.step-text {
  color: var(--muted-2);
  font-size: 0.9rem;
  line-height: 1.5;
}

.bot-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-top: 22px;
  padding: 16px 18px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  background: #fff;
  box-shadow: var(--shadow);
}
.bot-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1 1 220px;
}
.bot-copy strong {
  font-size: 15px;
  letter-spacing: -0.02em;
  line-height: 1.35;
}
.bot-copy span { color: var(--muted); font-size: 14px; }
.bot-card .btn { flex: 0 0 auto; text-decoration: none; }

.hero-form {
  position: sticky;
  top: 16px;
  scroll-margin-top: 20px;
}
.hero-form :deep(.card) {
  border-radius: 24px;
  box-shadow: 0 30px 70px rgba(28, 25, 21, 0.12);
}

.catch-title { max-width: 22ch; }
.catch-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(0, 1fr);
  gap: 18px;
  align-items: stretch;
}
.catch-main {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 42%);
  border-radius: 24px;
  border: 1px solid var(--border);
  background: #fff;
  box-shadow: 0 10px 30px rgba(28, 25, 21, 0.05);
  overflow: hidden;
}
.catch-main-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 26px 26px 28px;
  min-width: 0;
}
.catch-main-body .label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
}
.catch-main-body h3 {
  margin: 0;
  font-size: 1.35rem;
  letter-spacing: -0.02em;
  line-height: 1.2;
}
.catch-main-body p {
  margin: 0;
  color: var(--muted-2);
  font-size: 0.95rem;
  line-height: 1.55;
}
.catch-accent {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 6px !important;
  padding: 12px 14px;
  border-radius: 14px;
  background: var(--ok-soft);
  border: 1px solid #c7e3d4;
  color: #1f4d39 !important;
  font-weight: 600;
  font-size: 0.92rem !important;
}
.catch-accent svg { flex: 0 0 auto; margin-top: 2px; color: #2d6a4f; }
.catch-main-media {
  position: relative;
  min-height: 240px;
  background: #f1ece3;
}
.catch-main-media img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: 70% 50%;
}

.catch-features {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 12px;
  align-content: stretch;
}
.catch-feature {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 18px 12px 12px;
  border-radius: 20px;
  border: 1px solid var(--border);
  background: #fff;
  box-shadow: 0 10px 30px rgba(28, 25, 21, 0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.catch-feature:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 40px rgba(28, 25, 21, 0.09);
}
.catch-feature-img {
  flex: 0 0 auto;
  width: 76px;
  height: 76px;
  border-radius: 16px;
  overflow: hidden;
  background: #f4efe6;
}
.catch-feature-img img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transform: scale(1.12);
}
.catch-feature > div {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.catch-feature b {
  font-size: 1rem;
  letter-spacing: -0.01em;
  line-height: 1.3;
}
.catch-feature span {
  color: var(--muted);
  font-size: 0.88rem;
  line-height: 1.4;
}

.block { padding-bottom: 64px; }
.block-head { max-width: 640px; margin-bottom: 24px; }
.block-head h2 { margin: 0 0 8px; font-size: 1.7rem; letter-spacing: -0.03em; }
.block-head p { margin: 0; }
.block-cta { margin-top: 22px; }

.save {
  position: relative;
}
.save-eyebrow {
  display: inline-block;
  margin: 0 0 14px;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.6);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
}
.save-title {
  margin: 0 0 10px;
  max-width: 16ch;
  font-size: clamp(1.8rem, 3vw, 2.4rem);
  line-height: 1.1;
  letter-spacing: -0.035em;
}
.save-lead {
  margin: 0 0 28px;
  max-width: 36rem;
  color: var(--muted-2);
  font-size: 1rem;
  line-height: 1.5;
}

.save-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
  margin-bottom: 26px;
}
.save-card {
  display: flex;
  flex-direction: column;
  border-radius: 24px;
  border: 1px solid var(--border);
  background: #fff;
  box-shadow: 0 10px 30px rgba(28, 25, 21, 0.05);
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.save-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 18px 44px rgba(28, 25, 21, 0.1);
}
.save-media {
  position: relative;
  aspect-ratio: 16 / 10;
  background: #f1ece3;
}
.save-media img {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 100%;
  object-fit: cover;
  object-position: center;
  transition: transform 0.4s ease;
}
.save-card.was .save-media img { object-position: 50% 65%; }
.save-card:hover .save-media img { transform: scale(1.04); }
.save-pill {
  position: absolute;
  top: 14px;
  right: 14px;
  padding: 6px 12px;
  border-radius: 999px;
  background: #1f4d39;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.01em;
  box-shadow: 0 6px 16px rgba(31, 77, 57, 0.25);
}
.save-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 18px 22px 22px;
  min-width: 0;
}
.save-card .label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
}
.save-value {
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.2;
}
.save-sub {
  color: var(--muted-2);
  font-size: 0.9rem;
  line-height: 1.45;
}
.save-card.was .save-value { color: var(--muted-2); text-decoration: line-through; text-decoration-thickness: 2px; text-decoration-color: rgba(28, 25, 21, 0.35); }
.save-card.result {
  border-color: #c7e3d4;
  background: var(--ok-soft);
}
.save-card.result .save-media { background: #e3f3ea; }
.save-card.result .save-value { color: #1f4d39; }
.save-card.result .save-sub { color: #2d6a4f; }
.save-card.result .label { color: #2d6a4f; }

.save-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}
.save-note {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin: 0;
  max-width: 46rem;
  color: var(--muted-2);
  font-size: 0.92rem;
  line-height: 1.5;
}
.save-note svg {
  flex: 0 0 auto;
  margin-top: 2px;
  color: var(--muted);
}
.save-cta .arrow-glyph,
.block-cta .arrow-glyph {
  font-size: 17px;
  line-height: 1;
}

.cards5 {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}
.info {
  padding: 18px 16px 20px;
  border: 1px solid var(--border);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.55);
}
.info .num {
  display: inline-block;
  margin-bottom: 12px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--muted);
}
.info h3 { margin: 0 0 8px; font-size: 1.02rem; letter-spacing: -0.02em; }
.info p { margin: 0; color: var(--muted-2); font-size: 0.9rem; line-height: 1.45; }

.tiers {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
}
.tier {
  padding: 20px;
  border-radius: 18px;
  background: var(--accent);
  color: var(--bg);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.tier b { font-size: 2rem; letter-spacing: -0.04em; line-height: 1; }
.tier span { font-weight: 600; }
.tier small { color: rgba(244, 241, 234, 0.7); font-size: 12px; }

.faq-list { display: grid; gap: 10px; max-width: 820px; }
.faq-list details {
  border: 1px solid var(--border);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.55);
  padding: 0 18px;
}
.faq-list summary {
  cursor: pointer;
  padding: 14px 0;
  font-weight: 600;
  list-style: none;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.faq-list summary::-webkit-details-marker { display: none; }
.faq-list summary::after { content: "+"; color: var(--muted); font-weight: 400; }
.faq-list details[open] summary::after { content: "−"; }
.faq-list p { margin: 0 0 16px; color: var(--muted-2); font-size: 0.95rem; line-height: 1.55; }
.faq-list code {
  font-size: 0.9em;
  padding: 1px 6px;
  border-radius: 6px;
  background: var(--surface-soft);
  border: 1px solid var(--border);
}

@media (max-width: 1100px) {
  .cards5 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 900px) {
  .hero { grid-template-columns: 1fr; padding-top: 32px; gap: 28px; }
  .hero-form { position: static; order: -1; }
  .hero-how .bot-card { margin-top: 20px; }
  .hero-how h2 { font-size: 1.7rem; }
  .save-grid { grid-template-columns: 1fr; gap: 10px; margin-bottom: 20px; }
  .save-title { max-width: none; font-size: clamp(1.55rem, 5vw, 1.85rem); }
  .save-lead { margin-bottom: 20px; font-size: 0.95rem; }
  .save-card {
    flex-direction: row;
    align-items: stretch;
  }
  .save-card:hover {
    transform: none;
    box-shadow: 0 10px 30px rgba(28, 25, 21, 0.05);
  }
  .save-media {
    flex: 0 0 108px;
    width: 108px;
    aspect-ratio: auto;
    align-self: stretch;
    min-height: 108px;
  }
  .save-card:hover .save-media img { transform: none; }
  .save-card.was .save-media img { object-position: 58% 68%; }
  .save-card.now .save-media img { object-position: 50% 42%; }
  .save-card.result .save-media img { object-position: 50% 50%; }
  .save-body {
    flex: 1;
    justify-content: center;
    padding: 16px 18px 16px 14px;
  }
  .save-value { font-size: 1.12rem; }
  .save-sub { font-size: 0.84rem; }
  .save-pill {
    top: 8px;
    right: 8px;
    padding: 4px 9px;
    font-size: 11px;
  }
  .save-footer { flex-direction: column; align-items: stretch; gap: 16px; }
  .save-cta { width: 100%; }
  .catch-grid { grid-template-columns: 1fr; }
  .catch-title { max-width: none; }
}
@media (max-width: 560px) {
  .cards5 { grid-template-columns: 1fr; }
  .steps { grid-template-columns: 1fr; }
  .save-media { flex-basis: 92px; width: 92px; min-height: 92px; }
  .save-body { padding: 14px 16px 14px 12px; gap: 4px; }
  .save-value { font-size: 1.02rem; }
  .save-sub { font-size: 0.8rem; line-height: 1.35; }
  .catch-main { grid-template-columns: 1fr; }
  .catch-main-media { min-height: 0; aspect-ratio: 16 / 9; order: -1; }
  .catch-main-media img { object-position: 60% 50%; }
  .catch-main-body { padding: 20px 20px 22px; }
  .catch-feature-img { width: 64px; height: 64px; }
}
</style>
