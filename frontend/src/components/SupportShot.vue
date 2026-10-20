<template>
  <a v-if="url" class="shot" :href="url" target="_blank" rel="noopener">
    <img :src="url" :alt="alt">
  </a>
  <span v-else-if="failed" class="shot-miss">Не удалось открыть изображение</span>
  <span v-else class="shot-miss">Загрузка…</span>
</template>

<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  src: { type: String, required: true },
  headers: { type: Object, default: () => ({}) },
  alt: { type: String, default: 'Скриншот' },
})

const url = ref('')
const failed = ref(false)
let objectUrl = ''
let seq = 0

async function load() {
  const current = ++seq
  failed.value = false
  if (objectUrl) URL.revokeObjectURL(objectUrl)
  objectUrl = ''
  url.value = ''
  try {
    const response = await fetch(props.src, {
      cache: 'no-store',
      headers: props.headers || {},
    })
    if (!response.ok) throw new Error('file')
    const blob = await response.blob()
    if (current !== seq) return
    objectUrl = URL.createObjectURL(blob)
    url.value = objectUrl
  } catch {
    if (current === seq) failed.value = true
  }
}

watch(() => props.src, load, { immediate: true })

onBeforeUnmount(() => {
  seq += 1
  if (objectUrl) URL.revokeObjectURL(objectUrl)
})
</script>

<style scoped>
.shot {
  display: block;
  max-width: 240px;
  border-radius: 10px;
  overflow: hidden;
  line-height: 0;
}
.shot img {
  display: block;
  width: 100%;
  height: auto;
  max-height: 220px;
  object-fit: cover;
}
.shot-miss {
  font-size: 12px;
  opacity: 0.7;
}
</style>
