<template>
  <div class="site home">
    <SiteHeader />
    <main class="site-main">
      <OrbitHero :rate="price" :min-usd="minUsd" @pick="focusSignup" />
      <StatsBand />
      <TerminalDemo :rate="rate" />
      <SavingsCalculator :rate="price" />
      <WhySection />
      <PriceSpotlight :usd-price-rub="price" />
      <PaySection :config="config" :tiers="tiers" :bot-url="config?.bot_url ? botUrl : ''" />
      <FaqSection :rate="price" />
      <FinalCta />
    </main>
    <SiteFooter />
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import PriceSpotlight from '../components/PriceSpotlight.vue'
import SiteFooter from '../components/SiteFooter.vue'
import SiteHeader from '../components/SiteHeader.vue'
import FaqSection from '../components/home/FaqSection.vue'
import FinalCta from '../components/home/FinalCta.vue'
import OrbitHero from '../components/home/OrbitHero.vue'
import PaySection from '../components/home/PaySection.vue'
import SavingsCalculator from '../components/home/SavingsCalculator.vue'
import StatsBand from '../components/home/StatsBand.vue'
import TerminalDemo from '../components/home/TerminalDemo.vue'
import WhySection from '../components/home/WhySection.vue'
import { useWebConfig } from '../composables/useWebConfig'
import { botUrlWithReferral } from '../utils/referral'
import { useHead } from '../utils/useHead'

const { config, loadConfig } = useWebConfig()
const botUrl = computed(() => botUrlWithReferral(config.value?.bot_url || ''))
const price = computed(() => Number(config.value?.usd_price_rub || 0))
const minUsd = computed(() => Number(config.value?.min_topup_usd || 10))
const tiers = computed(() =>
  [...(config.value?.bonuses || [])]
    .map((tier) => ({ min_usd: Number(tier.min_usd), percent: Number(tier.percent) }))
    .filter((tier) => tier.min_usd > 0 && tier.percent > 0)
    .sort((a, b) => a.min_usd - b.min_usd),
)
const rate = computed(() => price.value || 10)

function focusSignup() {
  const input = document.getElementById('signup-hero')
  if (!input) return
  input.scrollIntoView({ behavior: 'smooth', block: 'center' })
  setTimeout(() => input.focus({ preventScroll: true }), 350)
}

onMounted(async () => {
  useHead('Aimarket — токены со скидкой 90%')
  let meta = document.querySelector('meta[name="description"]')
  if (!meta) {
    meta = document.createElement('meta')
    meta.name = 'description'
    document.head.append(meta)
  }
  meta.content = 'Aimarket — один ключ ко всем ИИ со скидкой 90%. Пополнение в рублях, Cursor, Claude Code, Codex.'
  await loadConfig()
})
</script>

<style scoped>
.home { overflow-x: clip; }
.home .site-main { padding: 0; }
</style>
