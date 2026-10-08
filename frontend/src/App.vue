<template>
  <RouterView />
  <ToastHost />
  <SupportWidget />
</template>

<script setup>
import { watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
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
