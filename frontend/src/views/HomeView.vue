<template>
  <div class="site">
    <SiteHeader />
    <main class="site-main">
      <section class="container hero">
        <div class="hero-copy">
          <p class="eyebrow">Aimarket</p>
          <h1>Токены со скидкой 90%</h1>
          <p class="lead">
            Один ключ доступа ко всем ИИ. Чтобы попробовать — пополните баланс
            за {{ rub(minRub, 0) }} на {{ usd(minUsd, 0) }}. Подключайтесь через Cursor, Codex,
            Claude Code или другой клиент.
          </p>
          <p class="hook">От экономии 90% вас отделяют два шага.</p>
          <p class="lead soft">
            Если тратите в месяц {{ usd(100, 0) }} и более на Claude, представьте:
            эти {{ rub(spendWas) }} вы уменьшаете до {{ rub(spendNow) }}.
          </p>
          <button type="button" class="btn" @click="scrollToTopup">Пополнить баланс</button>

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
        <div class="block-head">
          <h2>Если вы тратите на API {{ usd(100, 0) }} в месяц</h2>
        </div>
        <div class="save-grid">
          <article class="save-card was">
            <span class="label">Было</span>
            <b>{{ usd(100, 0) }} ≈ {{ rub(spendWas, 0) }} в месяц</b>
          </article>
          <article class="save-card now">
            <span class="label">Стало</span>
            <b>{{ usd(100, 0) }} = {{ rub(spendNow, 0) }} в месяц</b>
          </article>
          <article class="save-card result">
            <span class="label">Итог</span>
            <b>Экономите минимум {{ rub(spendSave, 0) }} ежемесячно</b>
            <span>при том же доступе к моделям</span>
          </article>
        </div>
        <p class="save-note">
          А ещё у нас нет ограничений: можно пополнить хоть на {{ usd(1000, 0) }} в токены.
          <template v-if="bonusFrom1000">
            Кстати, при пополнении от {{ usd(bonusFrom1000.min_usd, 0) }} даём
            +{{ bonusFrom1000.percent }}% дополнительно — на балансе будет
            {{ usd(bonusFrom1000.min_usd * (1 + bonusFrom1000.percent / 100), 0) }}.
          </template>
        </p>
        <button type="button" class="btn" @click="scrollToTopup">Пополнить баланс</button>
      </section>

      <section class="container block catch">
        <div class="block-head">
          <h2>В чём подвох?</h2>
          <p class="muted">
            Мы не используем «китайские копии», не подменяем модели и не используем серые схемы.
            Вы получаете прямой доступ к оригинальным нейросетям (Anthropic, OpenAI и др.).
          </p>
        </div>
        <div class="catch-body">
          <article class="info">
            <h3>Секрет цены прост</h3>
            <p>
              Мы агрегируем корпоративные квоты и неиспользованные API-токены, которые по условиям
              контрактов просто сгорают у крупных компаний. Выкупаем эти «остатки» оптом и монетизируем
              то, что иначе было бы потеряно.
            </p>
            <p class="catch-accent">
              Именно поэтому мы можем отдавать их вам по цене 10% от официального тарифа.
            </p>
          </article>
          <ul class="checks">
            <li>Оригинальные модели (Opus, Sonnet, Haiku, GPT‑4o)</li>
            <li>Высокая скорость ответа (собственные быстрые эндпоинты)</li>
            <li>Прозрачная статистика расходов</li>
          </ul>
        </div>
        <button type="button" class="btn block-cta" @click="scrollToTopup">Пополнить баланс</button>
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

      <section class="container how">
        <div class="how-copy">
          <h2>Как это работает</h2>
          <ol class="timeline">
            <li>
              <b>Пополняете баланс</b>
              <span>
                Сумма в долларах или рублях, курс и точная сумма к оплате — сразу в форме.
                Оплата картой через ЮKassa. Минимум — {{ usd(minUsd, 0) }}.
              </span>
            </li>
            <li>
              <b>Получаете ключ и Base URL</b>
              <span>
                Сайт покажет ключ сразу после оплаты, на почту придёт письмо с ключом и входом в кабинет.
              </span>
            </li>
            <li>
              <b>Подключаете приложения</b>
              <span>
                В Cursor, Codex, Claude Code или другом клиенте указываете наш адрес сервера и ключ.
                Готовые инструкции — в личном кабинете.
              </span>
            </li>
            <li>
              <b>Работаете и следите за расходом</b>
              <span>
                Каждый запрос списывается по тарифу модели. В кабинете — остаток, расход по дням и история.
              </span>
            </li>
          </ol>
          <button type="button" class="btn" @click="scrollToTopup">Пополнить баланс</button>
        </div>
        <div class="hero-visual">
          <img src="/home-hero.jpg" alt="Схема подключения Aimarket к ИИ-моделям">
        </div>
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
const minRub = computed(() => {
  const fromConfig = Number(config.value?.min_topup_rub || 0)
  if (fromConfig > 0) return fromConfig
  return Math.ceil(minUsd.value * (price.value || 10))
})
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
  padding-top: 28px;
  padding-bottom: 40px;
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  gap: 40px;
  align-items: start;
}
.eyebrow {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}
h1 {
  margin: 0 0 16px;
  font-size: clamp(2rem, 4vw, 3.1rem);
  line-height: 1.08;
  letter-spacing: -0.04em;
  max-width: 12ch;
}
.lead {
  margin: 0 0 14px;
  max-width: 38rem;
  color: var(--muted-2);
  font-size: 1.05rem;
}
.lead.soft { margin-bottom: 22px; }
.hook {
  margin: 0 0 10px;
  font-size: 1.15rem;
  font-weight: 700;
  letter-spacing: -0.02em;
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

.catch-body {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
  gap: 14px;
  align-items: stretch;
}
.catch-body .info h3 { margin: 0 0 10px; }
.catch-accent {
  margin: 12px 0 0 !important;
  color: var(--text) !important;
  font-weight: 600;
}
.checks {
  list-style: none;
  margin: 0;
  padding: 18px 18px 20px;
  border: 1px solid var(--border);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.55);
  display: grid;
  gap: 12px;
  align-content: start;
}
.checks li {
  position: relative;
  padding-left: 22px;
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.4;
}
.checks li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0.35em;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--ok);
  box-shadow: inset 0 0 0 3px var(--ok-soft);
}

.block { padding-bottom: 64px; }
.block-head { max-width: 640px; margin-bottom: 24px; }
.block-head h2, .how h2 { margin: 0 0 8px; font-size: 1.7rem; letter-spacing: -0.03em; }
.block-head p { margin: 0; }
.block-cta { margin-top: 22px; }

.save-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.save-card {
  padding: 18px 18px 20px;
  border-radius: 18px;
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.55);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.save-card .label {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
}
.save-card b {
  font-size: 1.15rem;
  letter-spacing: -0.02em;
  line-height: 1.3;
}
.save-card span { color: var(--muted-2); font-size: 0.9rem; }
.save-card.result {
  background: var(--ok-soft);
  border-color: #c7e3d4;
}
.save-card.result b { color: #1f4d39; }
.save-note {
  margin: 0 0 18px;
  max-width: 46rem;
  color: var(--muted-2);
  font-size: 0.98rem;
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

.how {
  padding-bottom: 64px;
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
  gap: 40px;
  align-items: center;
}
.how h2 { margin-bottom: 18px; }
.timeline {
  list-style: none;
  margin: 0 0 20px;
  padding: 0;
  counter-reset: step;
}
.timeline li {
  position: relative;
  padding: 0 0 20px 44px;
  counter-increment: step;
}
.timeline li::before {
  content: counter(step);
  position: absolute;
  left: 0;
  top: 0;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--accent);
  color: var(--bg);
  font-size: 13px;
  font-weight: 700;
  display: grid;
  place-items: center;
}
.timeline li:not(:last-child)::after {
  content: "";
  position: absolute;
  left: 14px;
  top: 32px;
  bottom: 2px;
  width: 2px;
  background: var(--border-strong);
}
.timeline b { display: block; margin-bottom: 4px; }
.timeline span { color: var(--muted-2); font-size: 0.95rem; line-height: 1.5; }

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

.hero-visual img {
  width: 100%;
  border-radius: 24px;
  border: 1px solid var(--border);
  box-shadow: 0 24px 60px rgba(28, 25, 21, 0.12);
  display: block;
}

@media (max-width: 1100px) {
  .cards5 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 900px) {
  .hero { grid-template-columns: 1fr; padding-top: 16px; gap: 28px; }
  .hero-form { position: static; order: -1; }
  h1 { max-width: none; }
  .how { grid-template-columns: 1fr; }
  .hero-visual { order: -1; }
  .save-grid { grid-template-columns: 1fr; }
  .catch-body { grid-template-columns: 1fr; }
}
@media (max-width: 560px) {
  .cards5 { grid-template-columns: 1fr; }
}
</style>
