<template>
  <footer class="footer">
    <div class="container footer-inner">
      <span>© Aimarket</span>
      <nav class="footer-links" aria-label="Документы">
        <RouterLink to="/prices">Цены</RouterLink>
        <RouterLink to="/privacy">Политика конфиденциальности</RouterLink>
        <RouterLink to="/cookies">Cookies</RouterLink>
        <RouterLink to="/consent">Согласие на обработку данных</RouterLink>
        <RouterLink to="/offer">Публичная оферта</RouterLink>
      </nav>
    </div>
  </footer>
</template>

<script setup>
import { RouterLink } from 'vue-router'
</script>

<style scoped>
.footer {
  border-top: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.35);
}
.footer-inner {
  padding-top: 22px;
  padding-bottom: 28px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px 24px;
  align-items: center;
  justify-content: space-between;
  color: var(--muted);
  font-size: 0.92rem;
}
.footer-links { display: flex; flex-wrap: wrap; gap: 10px 18px; }
.footer-links a { text-decoration: underline; text-underline-offset: 3px; }
</style>
