<template>
  <section id="pay" class="pay">
    <div class="pay-bg" aria-hidden="true">
      <span class="orb o1"></span>
      <span class="orb o2"></span>
      <span class="grid-lines"></span>
    </div>

    <div class="container pay-inner">
      <div class="pay-copy">
        <p v-reveal class="kicker kicker-dark">Пополнение</p>
        <h2 v-reveal="80" class="pay-title">Ключ — через минуту<br>после <span class="grad-text">оплаты</span></h2>
        <p v-reveal="160" class="pay-lead">
          Уже знаете, сколько нужно? Пополните баланс сразу — аккаунт создастся сам,
          а ключ появится на экране и придёт на почту.
        </p>

        <ul class="gets">
          <li v-for="(item, i) in gets" :key="item.title" v-reveal="120 + i * 70">
            <span class="get-num">{{ String(i + 1).padStart(2, '0') }}</span>
            <div>
              <b>{{ item.title }}</b>
              <span>{{ item.text }}</span>
            </div>
          </li>
        </ul>

        <div v-if="tiers.length" v-reveal="200" class="bonus">
          <span class="bonus-title">Бонусы к пополнению</span>
          <div class="bonus-track">
            <div v-for="tier in tiers" :key="tier.min_usd" class="bonus-step">
              <b>+{{ tier.percent }}%</b>
              <span>от {{ usd(tier.min_usd, 0) }}</span>
            </div>
          </div>
        </div>

        <a v-if="botUrl" v-reveal="240" class="bot" :href="botUrl" target="_blank" rel="noopener">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21.9 4.3 18.7 19.4c-.2 1-.9 1.3-1.7.8l-4.8-3.6-2.3 2.2c-.3.3-.5.5-1 .5l.3-4.9 8.9-8c.4-.3-.1-.5-.6-.2l-11 6.9-4.7-1.5c-1-.3-1-1 .2-1.5l18.5-7.1c.9-.3 1.6.2 1.4 1.3z" /></svg>
          Баланс, уведомления и поддержка — в Telegram-боте
          <span aria-hidden="true">→</span>
        </a>
      </div>

      <div v-reveal="120" class="pay-form-wrap">
        <div class="ring" aria-hidden="true"></div>
        <div id="topup" class="pay-form">
          <TopupForm mode="checkout" :config="config" />
          <div class="secure">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2" /><path d="M8 11V7a4 4 0 0 1 8 0v4" /></svg>
            Платёж защищён ЮKassa · Возврат неиспользованного баланса 14 дней
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import TopupForm from '../TopupForm.vue'
import { usd } from '../../utils/format'

defineProps({
  config: { type: Object, default: null },
  tiers: { type: Array, default: () => [] },
  botUrl: { type: String, default: '' },
})

const gets = [
  { title: 'API-ключ', text: 'Сразу на экране и дублируется на почту.' },
  { title: 'Base URL', text: 'Для Cursor, Claude Code, Codex и любых SDK.' },
  { title: 'Личный кабинет', text: 'Расход по дням, история запросов, инструкции.' },
  { title: 'Поддержка', text: 'Чат справа внизу — отвечаем за несколько минут.' },
]
</script>

<style scoped>
.pay {
  position: relative;
  margin: 80px 12px;
  padding: 110px 0;
  border-radius: 44px;
  background: linear-gradient(180deg, #1b1713 0%, #110e0b 100%);
  color: #f6f1e8;
  overflow: hidden;
  isolation: isolate;
  scroll-margin-top: 70px;
}
.pay-bg { position: absolute; inset: 0; z-index: -1; pointer-events: none; }
.orb { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.55; }
.o1 { width: 560px; height: 560px; left: -160px; top: -200px; background: #d9653b; animation: drift 16s ease-in-out infinite alternate; }
.o2 { width: 620px; height: 620px; right: -200px; bottom: -260px; background: #6f5cf0; opacity: 0.45; animation: drift 19s ease-in-out infinite alternate-reverse; }
@keyframes drift { to { transform: translate(80px, 60px) scale(1.1); } }
.grid-lines {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
  background-size: 64px 64px;
  -webkit-mask-image: radial-gradient(ellipse at 50% 40%, #000 20%, transparent 75%);
  mask-image: radial-gradient(ellipse at 50% 40%, #000 20%, transparent 75%);
}

.pay-inner {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 480px);
  gap: 64px;
  align-items: center;
}
.kicker-dark { background: rgba(255, 255, 255, 0.08); border-color: rgba(255, 255, 255, 0.14); color: #f6f1e8; }
.pay-title {
  margin: 0 0 18px;
  font-size: clamp(2.2rem, 4.4vw, 3.6rem);
  font-weight: 650;
  line-height: 1.02;
  letter-spacing: -0.05em;
}
.pay-lead { margin: 0 0 34px; max-width: 48ch; color: rgba(246, 241, 232, 0.7); font-size: 17px; line-height: 1.55; }

.gets { list-style: none; margin: 0 0 30px; padding: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.gets li {
  display: flex;
  gap: 14px;
  padding: 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.09);
}
.get-num { font: 600 12px/1.6 var(--font-mono); color: #f0a477; }
.gets b { display: block; margin-bottom: 2px; font-size: 15px; }
.gets span { display: block; color: rgba(246, 241, 232, 0.6); font-size: 13.5px; line-height: 1.4; }

.bonus { margin-bottom: 26px; }
.bonus-title { display: block; margin-bottom: 12px; font-size: 12px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: rgba(246, 241, 232, 0.55); }
.bonus-track {
  position: relative;
  display: flex;
  gap: 8px;
}
.bonus-step {
  flex: 1;
  position: relative;
  padding: 14px 14px 12px;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.09), rgba(255, 255, 255, 0.03));
  border: 1px solid rgba(255, 255, 255, 0.1);
}
.bonus-step:last-child { border-color: rgba(240, 164, 119, 0.5); box-shadow: 0 0 30px -10px rgba(240, 164, 119, 0.6); }
.bonus-step b {
  display: block;
  font-size: 1.5rem;
  letter-spacing: -0.04em;
  background: linear-gradient(100deg, #ffe1a8, #f0a477 50%, #d7b8ff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.bonus-step span { color: rgba(246, 241, 232, 0.6); font-size: 13px; }

.bot {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: rgba(246, 241, 232, 0.8);
  font-size: 14.5px;
  font-weight: 600;
  text-decoration: none;
}
.bot svg { color: #5fb4ff; }
.bot:hover { color: #fff; }

/* Форма с переливающейся рамкой. */
.pay-form-wrap { position: relative; border-radius: 30px; padding: 2px; }
.ring {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: conic-gradient(from var(--angle, 0deg), #d9653b, #e8a04a, #b07be0, #6f7cf0, #d9653b);
  animation: spin 6s linear infinite;
}
.ring::after {
  content: "";
  position: absolute;
  inset: 10%;
  z-index: -1;
  border-radius: inherit;
  background: inherit;
  filter: blur(50px);
  opacity: 0.7;
}
@property --angle { syntax: "<angle>"; initial-value: 0deg; inherits: false; }
@keyframes spin { to { --angle: 360deg; } }
.pay-form {
  position: relative;
  border-radius: 28px;
  background: #fbf8f3;
  color: var(--text);
  overflow: hidden;
}
.pay-form :deep(.topup) {
  border: 0;
  box-shadow: none;
  background: transparent;
  padding: 28px 28px 10px;
}
.pay-form :deep(.title) { font-size: 1.45rem; letter-spacing: -0.04em; }
.pay-form :deep(.btn) { width: 100%; justify-content: center; min-height: 54px; border-radius: 16px; font-size: 16px; }
.pay-form :deep(input) { font-size: 1.3rem; }
.secure {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 28px 18px;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 12.5px;
}

@media (max-width: 1000px) {
  .pay-inner { grid-template-columns: 1fr; gap: 44px; }
  .pay-form-wrap { max-width: 520px; width: 100%; margin: 0 auto; }
}
@media (max-width: 600px) {
  .pay { margin: 40px 6px; padding: 72px 0; border-radius: 30px; }
  .gets { grid-template-columns: 1fr; }
  .bonus-track { flex-wrap: wrap; }
  .bonus-step { flex: 1 1 calc(50% - 4px); }
  .pay-form :deep(.topup) { padding: 22px 18px 8px; }
  .secure { padding: 12px 18px 16px; }
}
@media (prefers-reduced-motion: reduce) {
  .orb, .ring { animation: none; }
}
</style>
