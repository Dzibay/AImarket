<template>
  <div v-if="visible" class="cookie-banner" role="dialog" aria-label="Согласие на cookies">
    <div class="cookie-banner-inner">
      <p>
        Мы используем cookies для работы сайта и аналитики (Яндекс.Метрика).
        Подробнее в
        <RouterLink to="/cookies">политике cookies</RouterLink>.
      </p>
      <button type="button" class="cookie-accept" @click="accept">Принять</button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { acceptCookiesConsent, hasCookiesConsent, initMetrika } from '../utils/cookiesConsent'

const visible = ref(false)
const route = useRoute()

function sync() {
  if (route.path.startsWith('/admin')) {
    visible.value = false
    return
  }
  if (hasCookiesConsent()) {
    visible.value = false
    initMetrika()
    return
  }
  visible.value = true
}

watch(() => route.path, sync, { immediate: true })

function accept() {
  acceptCookiesConsent()
  visible.value = false
}
</script>

<style scoped>
.cookie-banner {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 60;
  padding: 14px 16px calc(14px + env(safe-area-inset-bottom, 0px));
  pointer-events: none;
}
.cookie-banner-inner {
  pointer-events: auto;
  max-width: 920px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px 18px;
  padding: 14px 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius, 14px);
  background: rgba(255, 252, 247, 0.96);
  box-shadow: 0 16px 40px rgba(28, 25, 21, 0.14);
  backdrop-filter: blur(8px);
}
.cookie-banner-inner p {
  margin: 0;
  color: var(--text);
  font-size: 14px;
  line-height: 1.45;
}
.cookie-banner-inner a {
  color: inherit;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.cookie-accept {
  flex: 0 0 auto;
  appearance: none;
  border: 0;
  border-radius: 10px;
  padding: 10px 16px;
  font: inherit;
  font-weight: 650;
  cursor: pointer;
  background: var(--accent, #1c1915);
  color: #fff;
}
.cookie-accept:hover {
  opacity: 0.92;
}
@media (max-width: 640px) {
  .cookie-banner-inner {
    flex-direction: column;
    align-items: stretch;
  }
  .cookie-accept {
    width: 100%;
  }
}
</style>
