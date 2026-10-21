<template>
  <footer class="footer">
    <div class="container footer-top">
      <div class="about">
        <RouterLink to="/" class="brand">
          <img src="/favicon-96x96.png" width="32" height="32" alt="">
          <span>Aimarket</span>
        </RouterLink>
        <p>Один API-ключ ко всем топовым нейросетям — на 90% дешевле официальных цен. Оплата в рублях картой РФ.</p>
      </div>

      <nav class="col" aria-label="Продукт">
        <span class="col-title">Продукт</span>
        <RouterLink :to="{ path: '/', hash: '#how' }">Как подключить</RouterLink>
        <RouterLink :to="{ path: '/', hash: '#savings' }">Калькулятор экономии</RouterLink>
        <RouterLink to="/prices">Цены</RouterLink>
        <RouterLink :to="{ path: '/', hash: '#pay' }">Пополнение</RouterLink>
      </nav>
      <nav class="col" aria-label="Помощь">
        <span class="col-title">Помощь</span>
        <RouterLink to="/help">Справка</RouterLink>
        <RouterLink :to="{ path: '/', hash: '#faq' }">Частые вопросы</RouterLink>
        <RouterLink to="/login">Личный кабинет</RouterLink>
      </nav>
      <nav class="col" aria-label="Документы">
        <span class="col-title">Документы</span>
        <RouterLink to="/offer">Публичная оферта</RouterLink>
        <RouterLink to="/privacy">Политика конфиденциальности</RouterLink>
        <RouterLink to="/consent">Согласие на обработку данных</RouterLink>
        <RouterLink to="/cookies">Cookies</RouterLink>
      </nav>
    </div>

    <div class="wordmark" aria-hidden="true">Aimarket</div>

    <div class="container footer-bottom">
      <span>© {{ year }} Aimarket</span>
      <span>Aimarket — независимый API-провайдер и не аффилирован с OpenAI, Anthropic или Google.</span>
    </div>
  </footer>
</template>

<script setup>
import { RouterLink } from 'vue-router'

const year = new Date().getFullYear()
</script>

<style scoped>
.footer {
  position: relative;
  margin-top: auto;
  padding-top: 72px;
  border-top: 1px solid var(--border);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0.15));
  overflow: hidden;
}
.footer-top {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) repeat(3, minmax(0, 1fr));
  gap: 40px;
}
.brand { display: inline-flex; align-items: center; gap: 10px; font-size: 18px; font-weight: 700; letter-spacing: -0.035em; }
.brand img { border-radius: 9px; box-shadow: 0 6px 16px rgba(28, 25, 21, 0.14); }
.about p { margin: 16px 0 18px; max-width: 36ch; color: var(--muted-2); font-size: 14.5px; line-height: 1.55; }
.status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid var(--border);
  font-size: 12.5px;
  font-weight: 600;
  color: var(--muted-2);
}
.status i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #3f9b6f;
  box-shadow: 0 0 0 0 rgba(63, 155, 111, 0.6);
  animation: ping 2s ease-out infinite;
}
@keyframes ping { to { box-shadow: 0 0 0 8px rgba(63, 155, 111, 0); } }
.col { display: flex; flex-direction: column; gap: 10px; }
.col-title { margin-bottom: 4px; font-size: 12px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); }
.col a { color: var(--muted-2); font-size: 14.5px; transition: color 0.2s ease; }
.col a:hover { color: var(--text); }

.wordmark {
  margin: 40px 0 -0.22em;
  text-align: center;
  font-size: clamp(5rem, 21vw, 20rem);
  font-weight: 750;
  line-height: 1;
  letter-spacing: -0.07em;
  background: linear-gradient(180deg, rgba(28, 25, 21, 0.09), rgba(28, 25, 21, 0));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  user-select: none;
  pointer-events: none;
}
.footer-bottom {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px 24px;
  padding-top: 18px;
  padding-bottom: 26px;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 12.5px;
}

@media (max-width: 900px) {
  .footer-top { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .about { grid-column: 1 / -1; }
}
@media (max-width: 560px) {
  .footer { padding-top: 52px; }
  .footer-top { grid-template-columns: 1fr 1fr; gap: 32px 20px; }
}
@media (prefers-reduced-motion: reduce) {
  .status i { animation: none; }
}
</style>
