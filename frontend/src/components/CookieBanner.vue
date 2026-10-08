<template>
  <div v-if="visible" class="cookie-banner" role="dialog" aria-label="Согласие на cookies">
    <div class="cookie-banner-inner">
      <p>
        Используем cookies и системы аналитики. Используя сайт, вы соглашаетесь с этим в соответствии с
        <RouterLink to="/cookies">Политикой cookies</RouterLink>.
      </p>
      <button type="button" class="cookie-accept" @click="accept">ОК</button>
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
  left: 16px;
  bottom: calc(16px + env(safe-area-inset-bottom, 0px));
  z-index: 60;
  max-width: min(340px, calc(100vw - 32px));
  pointer-events: none;
}
.cookie-banner-inner {
  pointer-events: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px 18px 16px;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 12px 36px rgba(28, 25, 21, 0.16);
}
.cookie-banner-inner p {
  margin: 0;
  color: #333;
  font-size: 14px;
  line-height: 1.45;
}
.cookie-banner-inner a {
  color: inherit;
  text-decoration: underline;
  text-underline-offset: 2px;
  font-weight: 600;
}
.cookie-accept {
  appearance: none;
  border: 0;
  width: 100%;
  border-radius: 12px;
  padding: 12px 16px;
  font: inherit;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.04em;
  cursor: pointer;
  background: #2f9e44;
  color: #fff;
}
.cookie-accept:hover {
  background: #2b8a3e;
}
@media (max-width: 640px) {
  .cookie-banner {
    left: 12px;
    right: 12px;
    max-width: none;
  }
}
</style>
