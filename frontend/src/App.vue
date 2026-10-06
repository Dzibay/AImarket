<template>
  <RouterView />
  <ToastHost />
</template>

<script setup>
import { watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import ToastHost from './components/ui/ToastHost.vue'
import { captureReferralFromUrl } from './utils/referral'

const route = useRoute()
watch(
  () => route.fullPath,
  () => captureReferralFromUrl(window.location.search),
  { immediate: true },
)
</script>
