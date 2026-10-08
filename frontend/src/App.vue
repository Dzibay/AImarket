<template>
  <RouterView />
  <ToastHost />
  <SupportWidget />
  <CookieBanner />
</template>

<script setup>
import { watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import CookieBanner from './components/CookieBanner.vue'
import SupportWidget from './components/SupportWidget.vue'
import ToastHost from './components/ui/ToastHost.vue'
import { captureReferralFromUrl } from './utils/referral'

const route = useRoute()
watch(
  () => route.fullPath,
  () => captureReferralFromUrl(window.location.search),
  { immediate: true },
)
</script>
