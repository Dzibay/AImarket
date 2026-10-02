<template>
  <div class="site">
    <SiteHeader />
    <main class="site-main legal">
      <div v-if="data" class="narrow">
        <h1>{{ data.heading }}</h1>
        <p class="meta">{{ data.meta }}</p>
        <p v-for="(paragraph, index) in data.paragraphs" :key="index">{{ paragraph }}</p>
        <p class="meta">{{ data.footer }} Эта страница: {{ data.link }}</p>
      </div>
      <div v-else-if="error" class="narrow">
        <h1>Страница не найдена</h1>
      </div>
    </main>
    <SiteFooter />
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import SiteFooter from '../components/SiteFooter.vue'
import SiteHeader from '../components/SiteHeader.vue'
import { useHead } from '../utils/useHead'
import { fetchLegalPage } from '../api/site'

const props = defineProps({
  page: { type: String, required: true },
})

const data = ref(null)
const error = ref(false)

async function load() {
  error.value = false
  data.value = null
  try {
    data.value = await fetchLegalPage(props.page)
    useHead(`${data.value.title} — Aimarket`, true)
  } catch {
    error.value = true
    useHead('Страница не найдена — Aimarket', true)
  }
}

onMounted(load)
watch(() => props.page, load)
</script>

<style scoped>
.legal {
  font: 17px/1.55 Georgia, "Times New Roman", serif;
}
.legal .narrow {
  max-width: 720px;
  padding-top: 32px;
  padding-bottom: 72px;
}
h1 {
  font: 600 32px/1.15 "Segoe UI", sans-serif;
  letter-spacing: -0.03em;
  margin: 0 0 8px;
}
.meta {
  font: 14px/1.4 "Segoe UI", sans-serif;
  color: var(--muted);
  margin-bottom: 28px;
}
p {
  margin: 0 0 16px;
  white-space: pre-line;
}
</style>
