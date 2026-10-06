<template>
  <header class="site-header">
    <div class="container inner">
      <RouterLink to="/" class="brand">
        <img src="/favicon-96x96.png" width="36" height="36" alt="">
        <span>Aimarket</span>
      </RouterLink>
      <nav class="nav">
        <RouterLink to="/prices" class="nav-link">Цены</RouterLink>
        <template v-if="isLoggedIn">
          <RouterLink to="/cabinet" class="btn quiet sm">Личный кабинет</RouterLink>
          <button type="button" class="link" @click="logout">Выйти</button>
        </template>
        <RouterLink v-else to="/login" class="btn quiet sm">Войти по ключу</RouterLink>
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
.site-header { padding: 18px 0 8px; }
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
.nav { display: flex; align-items: center; gap: 14px; }
.nav-link { font-size: 14px; font-weight: 600; color: var(--muted-2); }
.nav-link.router-link-active { color: var(--text); }
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
</style>
