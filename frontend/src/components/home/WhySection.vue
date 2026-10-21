<template>
  <section id="why" class="why container">
    <div class="head">
      <p v-reveal class="kicker">Почему Aimarket</p>
      <h2 v-reveal="80" class="section-title">Без иностранной карты.<br><span class="grad-text">Без переплат.</span></h2>
      <p v-reveal="160" class="section-lead">
        Те же модели, что у OpenAI, Anthropic и Google, — только платите вы рублями и в 10 раз меньше.
      </p>
    </div>

    <div v-reveal="100" class="compare">
      <div class="col col-old">
        <span class="col-title">Напрямую у провайдеров</span>
        <ul>
          <li v-for="item in oldWay" :key="item"><i class="x" aria-hidden="true">✕</i>{{ item }}</li>
        </ul>
      </div>
      <div class="vs" aria-hidden="true">vs</div>
      <div class="col col-new">
        <span class="col-title"><img src="/favicon-96x96.png" alt="" class="mark">Aimarket</span>
        <ul>
          <li v-for="item in newWay" :key="item"><i class="ok" aria-hidden="true">✓</i>{{ item }}</li>
        </ul>
      </div>
    </div>

    <div class="bento">
      <article v-reveal class="tile tile-secret">
        <span class="tile-kicker">В чём подвох?</span>
        <h3>Подвоха нет — есть простая экономика</h3>
        <p>
          Крупные компании покупают корпоративные квоты на API, и часть токенов по условиям контрактов
          просто сгорает. Мы выкупаем эти «остатки» оптом и отдаём вам по 10% от официального тарифа.
        </p>
        <div class="flow" aria-hidden="true">
          <span class="node">Корпоративная квота</span>
          <span class="pipe"><i></i></span>
          <span class="node">Aimarket</span>
          <span class="pipe"><i></i></span>
          <span class="node node-you">Вы · −90%</span>
        </div>
      </article>

      <article v-reveal="80" class="tile tile-orig">
        <span class="tile-icon" aria-hidden="true">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 4 6v6c0 4.5 3.4 8.2 8 9 4.6-.8 8-4.5 8-9V6z" /><path d="m9 12 2 2 4-4" /></svg>
        </span>
        <h3>Оригинальные модели</h3>
        <p>Opus, GPT, Gemini — без «китайских копий» и подмен. Ответы такие же, как у первоисточника.</p>
      </article>

      <article v-reveal="160" class="tile tile-key">
        <span class="tile-icon" aria-hidden="true">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="15" r="4" /><path d="m10.8 12.2 8.2-8.2" /><path d="m16 7 3 3" /><path d="m14 9 2 2" /></svg>
        </span>
        <h3>Один ключ — все модели</h3>
        <p>Форматы OpenAI, Claude Messages и Gemini. Меняйте модель одной строкой.</p>
        <code class="snippet">model: "claude-opus-5-5"</code>
      </article>

      <article v-reveal="80" class="tile tile-speed">
        <span class="tile-icon" aria-hidden="true">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2 4 14h7l-1 8 9-12h-7z" /></svg>
        </span>
        <h3>Быстрые эндпоинты</h3>
        <p>Собственные серверы и стриминг без задержек.</p>
        <div class="latency" aria-hidden="true">
          <span v-for="n in 18" :key="n" :style="{ '--h': `${30 + ((n * 37) % 60)}%`, '--d': `${n * 0.07}s` }"></span>
        </div>
      </article>

      <article v-reveal="160" class="tile tile-stats">
        <span class="tile-icon" aria-hidden="true">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20V10" /><path d="M10 20V4" /><path d="M16 20v-7" /><path d="M22 20H2" /></svg>
        </span>
        <h3>Прозрачный расход</h3>
        <p>Остаток, расход по дням и история каждого запроса — в личном кабинете и Telegram-боте.</p>
      </article>

      <article v-reveal="240" class="tile tile-pay">
        <span class="tile-icon" aria-hidden="true">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="6" width="18" height="13" rx="2.5" /><path d="M3 10h18" /><path d="M7 15h3" /></svg>
        </span>
        <h3>Оплата картой РФ</h3>
        <p>Через ЮKassa, в рублях. Без подписок: платите только за токены.</p>
      </article>
    </div>
  </section>
</template>

<script setup>
const oldWay = [
  'Нужна иностранная карта',
  'Подписка в долларах — от 2 000 ₽ в месяц',
  'Отдельный ключ и счёт у каждого провайдера',
  'Полная цена за каждый токен',
]
const newWay = [
  'Оплата российской картой в рублях',
  'Без подписок — платите за использование',
  'Один ключ к 40+ моделям',
  '10% от официальной цены',
]
</script>

<style scoped>
.why { padding-top: 120px; padding-bottom: 60px; scroll-margin-top: 80px; }
.head { display: flex; flex-direction: column; align-items: center; text-align: center; margin-bottom: 48px; }
.head .section-lead { margin: 0 auto; }

.compare {
  position: relative;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: stretch;
  gap: 0;
  margin-bottom: 16px;
}
.col { padding: 30px 32px; border-radius: 28px; }
.col-title { display: flex; align-items: center; gap: 8px; margin-bottom: 18px; font-size: 13px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; }
.mark { width: 22px; height: 22px; border-radius: 6px; }
.col ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 14px; }
.col li { display: flex; align-items: center; gap: 12px; font-size: 16px; }
.col i {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  font-size: 12px;
  font-style: normal;
  font-weight: 800;
}
.col-old { background: rgba(255, 255, 255, 0.45); border: 1px dashed var(--border-strong); color: var(--muted-2); }
.col-old .col-title { color: var(--muted); }
.col-old li { text-decoration: line-through; text-decoration-color: rgba(28, 25, 21, 0.25); }
.col-old .x { background: rgba(28, 25, 21, 0.07); color: var(--muted); }
.col-new {
  position: relative;
  background:
    radial-gradient(120% 100% at 100% 0%, rgba(176, 123, 224, 0.3), transparent 55%),
    radial-gradient(120% 100% at 0% 100%, rgba(232, 160, 74, 0.32), transparent 55%),
    linear-gradient(180deg, #1d1915, #14110d);
  color: #f6f1e8;
  box-shadow: var(--shadow-lg);
}
.col-new .col-title { color: rgba(246, 241, 232, 0.75); }
.col-new .ok { background: var(--grad); color: #fff; }
.vs {
  align-self: center;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  margin: 0 -14px;
  border-radius: 50%;
  background: #fff;
  border: 1px solid var(--border);
  box-shadow: var(--shadow-lg);
  font-weight: 700;
  font-style: italic;
  color: var(--muted);
}

.bento {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  grid-auto-rows: minmax(190px, auto);
  grid-auto-flow: dense;
  gap: 16px;
}
.tile {
  position: relative;
  padding: 26px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.66);
  border: 1px solid rgba(255, 255, 255, 0.95);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.9) inset, 0 18px 40px -26px rgba(60, 40, 15, 0.35);
  backdrop-filter: blur(12px);
  overflow: hidden;
}
.tile h3 { margin: 0 0 8px; font-size: 1.2rem; letter-spacing: -0.03em; }
.tile p { margin: 0; color: var(--muted-2); font-size: 15px; line-height: 1.5; }
.tile-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  margin-bottom: 18px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid var(--border);
  box-shadow: 0 6px 14px -8px rgba(40, 28, 12, 0.35);
  color: #c4572f;
}
.tile-secret { grid-column: span 2; grid-row: span 2; display: flex; flex-direction: column; padding: 34px; }
.tile-secret h3 { font-size: clamp(1.5rem, 2.4vw, 2rem); letter-spacing: -0.04em; line-height: 1.1; margin-bottom: 14px; }
.tile-secret p { font-size: 16px; max-width: 46ch; }
.tile-kicker { margin-bottom: 14px; font-size: 12px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #c4572f; }
.flow { margin-top: auto; padding-top: 30px; display: flex; align-items: center; flex-wrap: wrap; gap: 0; }
.node {
  padding: 10px 14px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid var(--border);
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  box-shadow: 0 6px 14px -10px rgba(40, 28, 12, 0.4);
}
.node-you { background: var(--ink); color: #fff; border-color: var(--ink); }
.pipe { position: relative; flex: 1 1 28px; min-width: 28px; height: 2px; background: var(--border-strong); overflow: hidden; }
.pipe i {
  position: absolute;
  inset: 0;
  width: 40%;
  background: var(--grad);
  animation: pipe 1.8s linear infinite;
}
@keyframes pipe { from { transform: translateX(-100%); } to { transform: translateX(250%); } }
.tile-key { grid-column: span 2; }
.snippet {
  display: inline-block;
  margin-top: 14px;
  padding: 8px 12px;
  border-radius: 10px;
  background: var(--ink);
  color: #f0c58a;
  font: 500 13px/1 var(--font-mono);
}
.latency { display: flex; align-items: flex-end; gap: 4px; height: 40px; margin-top: 16px; }
.latency span {
  flex: 1;
  height: var(--h);
  border-radius: 3px;
  background: var(--grad);
  opacity: 0.75;
  transform-origin: bottom;
  animation: bar 1.6s ease-in-out var(--d) infinite alternate;
}
@keyframes bar { from { transform: scaleY(0.45); } to { transform: scaleY(1); } }
.tile-pay, .tile-stats { grid-column: span 2; }

@media (max-width: 960px) {
  .bento { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .tile-secret { grid-row: auto; }
  .why { padding-top: 80px; }
}
@media (max-width: 720px) {
  .compare { grid-template-columns: 1fr; }
  .vs { justify-self: center; margin: -14px 0; }
  .col { padding: 24px 22px; }
}
@media (max-width: 560px) {
  .bento { grid-template-columns: 1fr; }
  .tile-secret, .tile-key, .tile-pay, .tile-stats { grid-column: auto; }
  .tile-secret { padding: 26px; }
  .flow { gap: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .pipe i, .latency span { animation: none; }
}
</style>
