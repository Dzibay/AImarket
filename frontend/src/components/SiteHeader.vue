<template>
  <header class="site-header">
    <div class="inner">
      <RouterLink to="/" class="brand">
        <img src="/favicon-96x96.png" width="36" height="36" alt="">
        <span>Aimarket</span>
      </RouterLink>
      <nav class="nav">
        <template v-if="isLoggedIn">
          <RouterLink to="/cabinet" class="btn quiet sm">Личный кабинет</RouterLink>
          <button type="button" class="link" @click="logout">Выйти</button>
        </template>
        <RouterLink v-else to="/login" class="auth-btn">Вход/Регистрация</RouterLink>
      </nav>
    </div>
  </header>
</template>

<script setup>
import { RouterLink, useRouter } from 'vue-router'
import { useSession } from '../composables/useSession'

const router = useRouter()
const { isLoggedIn, clearSession } = useSession()

function logout() {
  clearSession()
  router.push('/')
}
</script>

<style scoped>
.site-header {
  position: sticky;
  top: 0;
  z-index: 50;
  padding: 14px 0;
  background: rgba(244, 241, 234, 0.96);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(28, 25, 21, 0.06);
}
.inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: min(1280px, 100%);
  margin: 0 auto;
  padding: 0 28px;
}
.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  letter-spacing: -0.03em;
  font-size: 18px;
}
.brand img {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(28, 25, 21, 0.08);
}
.nav { display: flex; align-items: center; gap: 12px; }
.link {
  background: none;
  border: 0;
  padding: 0;
  font: inherit;
  font-size: 14px;
  color: var(--muted);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
}
.auth-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid rgba(28, 25, 21, 0.12);
  background: rgba(255, 255, 255, 0.72);
  color: var(--text);
  font: inherit;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.01em;
  box-shadow: none;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.auth-btn:hover {
  background: #fff;
  border-color: rgba(28, 25, 21, 0.2);
}
@media (max-width: 960px) {
  .inner { padding: 0 16px; }
}
</style>
