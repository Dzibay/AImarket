<template>
  <header class="site-header">
    <div class="container inner">
      <RouterLink to="/" class="brand">
        <img src="/favicon-96x96.png" width="36" height="36" alt="">
        <span>Aimarket</span>
      </RouterLink>
      <nav class="nav">
        <template v-if="isLoggedIn">
          <RouterLink to="/cabinet" class="btn quiet sm">Личный кабинет</RouterLink>
          <button type="button" class="link" @click="logout">Выйти</button>
        </template>
        <RouterLink v-else to="/login" class="btn auth-btn sm">Вход/Регистрация</RouterLink>
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
  min-height: 42px;
  padding: 0 18px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 650;
  letter-spacing: -0.01em;
  box-shadow: 0 10px 22px rgba(28, 25, 21, 0.14);
}
.auth-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 28px rgba(28, 25, 21, 0.18);
}
</style>
