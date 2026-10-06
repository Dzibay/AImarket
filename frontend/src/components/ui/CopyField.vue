<template>
  <div class="copy-field" :class="{ secret: masked }">
    <div class="copy-body">
      <span class="copy-label">{{ label }}</span>
      <code class="copy-value" :class="{ hidden: masked && !revealed }" :title="masked && !revealed ? '' : value">
        {{ shown }}
      </code>
    </div>
    <div class="copy-actions">
      <button
        v-if="masked"
        type="button"
        class="icon-btn"
        :aria-label="revealed ? 'Скрыть' : 'Показать'"
        :title="revealed ? 'Скрыть' : 'Показать'"
        @click="revealed = !revealed"
      >
        <AppIcon :name="revealed ? 'eye-off' : 'eye'" />
      </button>
      <button
        type="button"
        class="icon-btn"
        :class="{ done: copied }"
        aria-label="Скопировать"
        :title="copied ? 'Скопировано' : 'Скопировать'"
        @click="copy"
      >
        <AppIcon :name="copied ? 'check' : 'copy'" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { copyWithToast } from '../../composables/useToast'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: String, default: '' },
  masked: { type: Boolean, default: false },
  revealByDefault: { type: Boolean, default: false },
  toast: { type: String, default: 'Скопировано' },
})

const revealed = ref(props.revealByDefault)
const copied = ref(false)

const shown = computed(() => {
  const value = props.value || ''
  if (!props.masked || revealed.value) return value
  if (value.length <= 12) return '••••••••••••'
  return `${value.slice(0, 7)}${'•'.repeat(14)}${value.slice(-4)}`
})

async function copy() {
  const ok = await copyWithToast(props.value, props.toast)
  if (!ok) {
    revealed.value = true
    return
  }
  copied.value = true
  setTimeout(() => { copied.value = false }, 1500)
}
</script>

<style scoped>
.copy-field {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 10px 10px 10px 14px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  background: #fff;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.copy-field:hover { border-color: #c4b9a9; }
.copy-field:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(28, 25, 21, 0.06); }
.copy-body { flex: 1 1 auto; min-width: 0; }
.copy-label {
  display: block;
  margin-bottom: 2px;
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.copy-value {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  user-select: all;
}
.copy-value.hidden { letter-spacing: 0.06em; color: var(--muted-2); user-select: none; }
.copy-actions { display: flex; gap: 2px; flex: 0 0 auto; }
</style>
