<template>
  <div class="site">
    <SiteHeader />
    <main class="site-main">
      <section class="container hero">
        <div class="hero-copy">
          <h1>Единый ключ к&nbsp;лучшим ИИ-моделям</h1>
          <p class="lead">
            Пополните баланс картой в рублях — и сразу получите API-ключ. Подключайте OpenAI-, Anthropic-
            и Google-совместимые приложения без абонентской платы: платите только за реальные запросы.
          </p>
          <div class="features">
            <article class="feature">
              <img src="/home-feature-key.jpg" alt="">
              <strong>Один ключ</strong>
              <span>Один ключ для Codex, Claude, Cursor и других программ.</span>
            </article>
            <article class="feature">
              <img src="/home-feature-pay.jpg" alt="">
              <strong>Оплата по факту</strong>
              <span>Списание только за реальные запросы к API.</span>
            </article>
            <article class="feature">
              <img src="/home-feature-models.jpg" alt="">
              <strong>Разные форматы</strong>
              <span>OpenAI Chat Completions, Claude Messages и другие протоколы.</span>
            </article>
          </div>
          <aside v-if="config?.bot_url" class="bot-card">
            <div class="bot-copy">
              <strong>Уведомления о балансе, история пользования, поддержка</strong>
              <span>Всё это — в Telegram-боте</span>
            </div>
            <a class="btn sm" :href="config.bot_url" target="_blank" rel="noopener">Открыть бота</a>
          </aside>
        </div>
        <div class="hero-form">
          <TopupForm mode="checkout" :config="config" />
        </div>
      </section>

      <section class="container block">
        <div class="block-head">
          <h2>Что именно вы покупаете</h2>
          <p class="muted">
            Не подписку и не «пакет токенов», а баланс в долларах, который расходуется только на ваши запросы.
          </p>
        </div>
        <div class="cards4">
          <article class="info">
            <span class="num">01</span>
            <h3>Баланс в долларах</h3>
            <p>
              Вы платите рублями по курсу <template v-if="price">{{ rub(price) }} за $1</template><template v-else>сайта</template>,
              а на счёт зачисляется сумма в $. Так же, как у самих поставщиков моделей — без двойной конвертации
              при каждом запросе.
            </p>
          </article>
          <article class="info">
            <span class="num">02</span>
            <h3>Тарифы поставщиков</h3>
            <p>
              Стоимость каждого запроса считается по ценам OpenAI, Anthropic, Google и других за токены.
              Мы не добавляем абонентскую плату: списывается ровно то, что стоил запрос.
            </p>
          </article>
          <article class="info">
            <span class="num">03</span>
            <h3>Один ключ на всё</h3>
            <p>
              После оплаты вы получаете один ключ. Он открывает личный кабинет и работает как API-ключ во всех
              совместимых приложениях — Cursor, Codex, Claude Code, OpenCode, Hermes и других.
            </p>
          </article>
          <article class="info">
            <span class="num">04</span>
            <h3>Баланс не сгорает</h3>
            <p>
              У баланса нет срока действия и минимального ежемесячного расхода. Пополняйте, когда удобно, —
              хоть раз в полгода.
            </p>
          </article>
        </div>
      </section>

      <section class="container how">
        <div class="how-copy">
          <h2>Как строится работа с сервисом</h2>
          <ol class="timeline">
            <li>
              <b>Пополняете баланс</b>
              <span>
                Вводите сумму в долларах или рублях, видите курс и точную сумму к оплате, оплачиваете картой через
                ЮKassa. Минимум — {{ usd(minUsd, 0) }}.
              </span>
            </li>
            <li>
              <b>Получаете ключ доступа</b>
              <span>
                Сразу после оплаты сайт покажет ключ, а на почту придёт письмо с ключом и кнопкой входа в кабинет.
                Сохраните ключ: он нужен и для входа, и для API.
              </span>
            </li>
            <li>
              <b>Подключаете приложения</b>
              <span>
                В настройках Cursor, Codex, Claude Code или другого клиента указываете наш адрес сервера и
                вставляете ключ. Готовые инструкции и установщики — в личном кабинете.
              </span>
            </li>
            <li>
              <b>Работаете и следите за расходом</b>
              <span>
                Каждый запрос списывается с баланса по тарифу модели. В кабинете видно остаток, расход по дням,
                историю запросов и пополнений.
              </span>
            </li>
            <li>
              <b>Пополняете, когда нужно</b>
              <span>
                Когда баланс подходит к концу, пополняете его из кабинета тем же ключом. Если ключ утёк —
                перевыпускаете его в один клик, баланс сохраняется.
              </span>
            </li>
          </ol>
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
      </section>

      <section class="container block faq">
        <div class="block-head">
          <h2>Частые вопросы</h2>
        </div>
        <div class="faq-list">
          <details>
            <summary>Почему ключ — это ещё и пароль?</summary>
            <p>
              Чтобы не плодить логины и пароли: у вас одна строка, которую вы и так храните для приложений.
              Любой, у кого есть ключ, может тратить баланс — поэтому относитесь к нему как к паролю и не
              передавайте третьим лицам.
            </p>
          </details>
          <details>
            <summary>Что будет, если я потеряю ключ?</summary>
            <p>
              Если вы ещё залогинены в кабинете — перевыпустите ключ там. Если нет — найдите письмо с кнопкой
              входа (она работает несколько дней) или напишите в поддержку, указав почту и сумму последней оплаты.
            </p>
          </details>
          <details>
            <summary>Как считается стоимость запроса?</summary>
            <p>
              По количеству токенов на вход и выход по тарифу конкретной модели у её поставщика. Списание
              происходит после ответа модели. Запросы с ошибкой на стороне поставщика тоже считаются
              обработанными — см. <RouterLink to="/offer">оферту</RouterLink>.
            </p>
          </details>
          <details>
            <summary>Какие приложения можно подключить?</summary>
            <p>
              Любые, где можно задать свой API-ключ и адрес сервера: Cursor, Codex, Claude Code, Claude Desktop,
              OpenCode, Hermes, Grok Build и другие. Поддерживаются форматы OpenAI Chat Completions, Claude
              Messages и Google Gemini.
            </p>
          </details>
          <details>
            <summary>Можно ли вернуть деньги?</summary>
            <p>
              Баланс — это предоплата права доступа, он не сгорает и не имеет срока. Возврат не предусмотрен,
              кроме случаев, прямо указанных в законе — подробности в <RouterLink to="/offer">оферте</RouterLink>.
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
import { RouterLink } from 'vue-router'
import SiteFooter from '../components/SiteFooter.vue'
import SiteHeader from '../components/SiteHeader.vue'
import TopupForm from '../components/TopupForm.vue'
import { webApi } from '../api/web'
import { rub, usd } from '../utils/format'
import { useHead } from '../utils/useHead'

const config = ref(null)
const price = computed(() => Number(config.value?.usd_price_rub || 0))
const minUsd = computed(() => Number(config.value?.min_topup_usd || 10))
const tiers = computed(() =>
  [...(config.value?.bonuses || [])]
    .map((tier) => ({ min_usd: Number(tier.min_usd), percent: Number(tier.percent) }))
    .filter((tier) => tier.min_usd > 0 && tier.percent > 0)
    .sort((a, b) => a.min_usd - b.min_usd),
)

onMounted(async () => {
  useHead('Aimarket — API к ИИ-моделям')
  let meta = document.querySelector('meta[name="description"]')
  if (!meta) {
    meta = document.createElement('meta')
    meta.name = 'description'
    document.head.append(meta)
  }
  meta.content = 'Aimarket — единый API-ключ к лучшим ИИ-моделям. Оплата по факту использования, пополнение в рублях.'
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
  padding-bottom: 56px;
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  gap: 40px;
  align-items: start;
}
h1 {
  margin: 8px 0 16px;
  font-size: clamp(2rem, 4vw, 3.1rem);
  line-height: 1.08;
  letter-spacing: -0.04em;
  max-width: 11ch;
}
.lead {
  margin: 0 0 28px;
  max-width: 42rem;
  color: var(--muted-2);
  font-size: 1.05rem;
}
.features {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}
.feature {
  padding: 14px 12px;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.45);
}
.feature img {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: block;
  margin-bottom: 10px;
}
.feature strong { display: block; margin-bottom: 4px; font-size: 0.95rem; }
.feature span { display: block; color: var(--muted); font-size: 0.88rem; line-height: 1.4; }

.bot-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-top: 4px;
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
.bot-copy span {
  color: var(--muted);
  font-size: 14px;
}
.bot-card .btn { flex: 0 0 auto; text-decoration: none; }

.hero-form { position: sticky; top: 16px; }

.block { padding-bottom: 64px; }
.block-head { max-width: 640px; margin-bottom: 24px; }
.block-head h2, .how h2 { margin: 0 0 8px; font-size: 1.7rem; letter-spacing: -0.03em; }
.block-head p { margin: 0; }

.cards4 {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}
.info {
  padding: 18px 18px 20px;
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
.info h3 { margin: 0 0 8px; font-size: 1.05rem; letter-spacing: -0.02em; }
.info p { margin: 0; color: var(--muted-2); font-size: 0.93rem; line-height: 1.5; }

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
  margin: 0;
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
.faq-list a { text-decoration: underline; text-underline-offset: 3px; }

.hero-visual img {
  width: 100%;
  border-radius: 24px;
  border: 1px solid var(--border);
  box-shadow: 0 24px 60px rgba(28, 25, 21, 0.12);
  display: block;
}

@media (max-width: 900px) {
  .hero { grid-template-columns: 1fr; padding-top: 16px; gap: 28px; }
  .hero-form { position: static; order: -1; }
  .features { grid-template-columns: 1fr; }
  h1 { max-width: none; }
  .how { grid-template-columns: 1fr; }
  .hero-visual { order: -1; }
  .cards4 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 560px) {
  .cards4 { grid-template-columns: 1fr; }
}
</style>
