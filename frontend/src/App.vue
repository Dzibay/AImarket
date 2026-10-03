<template>
  <RouterView />
</template>

<script setup>
import { watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { captureReferralFromUrl } from './utils/referral'

const route = useRoute()
watch(
  () => route.fullPath,
  () => captureReferralFromUrl(window.location.search),
  { immediate: true },
)
</script>
