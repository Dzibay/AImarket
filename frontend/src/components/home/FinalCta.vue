<template>
  <section class="final container">
    <div v-reveal class="final-card">
      <div class="glow" aria-hidden="true"></div>
      <div class="logos" aria-hidden="true">
        <span v-for="(b, i) in brands" :key="b" class="logo" :style="{ '--i': i }"><BrandLogo :brand="b" :size="22" /></span>
      </div>
      <h2 class="final-title">Хватит переплачивать<br><span class="grad-text">в 10 раз</span></h2>
      <p class="final-lead">Регистрация за 10 секунд. Ключ и инструкции — сразу после пополнения.</p>
      <SignupForm size="lg" source="final" cta="Получить доступ" />
      <p class="final-fine">Без подписок · Оплата картой РФ · Возврат 14 дней</p>
    </div>
  </section>
</template>

<script setup>
import BrandLogo from '../BrandLogo.vue'
import SignupForm from './SignupForm.vue'

const brands = ['claude', 'gpt', 'gemini', 'grok', 'deepseek', 'china']
</script>

<style scoped>
.final { padding-top: 40px; padding-bottom: 120px; }
.final-card {
  position: relative;
  padding: 80px 32px 70px;
  border-radius: 44px;
  text-align: center;
  background:
    radial-gradient(70% 90% at 50% 0%, rgba(255, 255, 255, 0.95), rgba(255, 255, 255, 0.55));
  border: 1px solid rgba(255, 255, 255, 0.95);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  isolation: isolate;
}
.glow {
  position: absolute;
  left: 50%;
  bottom: -60%;
  z-index: -1;
  width: 120%;
  aspect-ratio: 2;
  transform: translateX(-50%);
  border-radius: 50%;
  background: conic-gradient(from 180deg, #d9653b, #e8a04a, #b07be0, #6f7cf0, #d9653b);
  filter: blur(90px);
  opacity: 0.38;
  animation: breathe 8s ease-in-out infinite alternate;
}
@keyframes breathe { to { opacity: 0.55; transform: translateX(-50%) scale(1.08); } }
.logos { display: flex; justify-content: center; gap: 10px; margin-bottom: 30px; }
.logo {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: 15px;
  background: #fff;
  border: 1px solid var(--border);
  box-shadow: 0 10px 24px -14px rgba(40, 28, 12, 0.45);
  color: var(--text);
  animation: bob 3.2s ease-in-out calc(var(--i) * -0.5s) infinite alternate;
}
@keyframes bob { to { transform: translateY(-8px); } }
.final-title {
  margin: 0 0 16px;
  font-size: clamp(2.4rem, 6vw, 4.6rem);
  font-weight: 680;
  line-height: 1;
  letter-spacing: -0.055em;
}
.final-lead { margin: 0 auto 32px; max-width: 46ch; color: var(--muted-2); font-size: 18px; }
.final-fine { margin: 18px 0 0; color: var(--muted); font-size: 13.5px; }
@media (max-width: 600px) {
  .final { padding-bottom: 72px; }
  .final-card { padding: 56px 16px 48px; border-radius: 30px; }
  .logo { width: 40px; height: 40px; border-radius: 12px; }
  .logos { gap: 6px; }
}
@media (prefers-reduced-motion: reduce) {
  .glow, .logo { animation: none; }
}
</style>
