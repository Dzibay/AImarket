<template>
  <div class="code-block" :class="{ busy: loading, failed: Boolean(error) }">
    <div class="code-head">
      <span class="code-label">
        <AppIcon v-if="icon" :name="icon" :size="15" />
        {{ label }}
      </span>
      <button
        v-if="code"
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
    <pre v-if="code" class="code-body" @click="selectAll"><code ref="codeEl">{{ code }}</code></pre>
    <div v-else-if="error" class="code-empty bad">{{ error }}</div>
    <div v-else class="code-empty">
      <span class="skeleton" style="width: 72%" />
      <span class="skeleton" style="width: 48%" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { copyWithToast } from '../../composables/useToast'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  label: { type: String, default: '' },
  icon: { type: String, default: '' },
  code: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  toast: { type: String, default: 'Команда скопирована' },
})

const emit = defineEmits(['copied'])
const copied = ref(false)
const codeEl = ref(null)

async function copy() {
  if (!(await copyWithToast(props.code, props.toast))) return
  copied.value = true
  emit('copied')
  setTimeout(() => { copied.value = false }, 1500)
}

function selectAll() {
  const node = codeEl.value
  if (!node || !window.getSelection) return
  const range = document.createRange()
  range.selectNodeContents(node)
  const selection = window.getSelection()
  selection.removeAllRanges()
  selection.addRange(range)
}

defineExpose({ copy })
</script>

<style scoped>
.code-block {
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  background: #fff;
  overflow: hidden;
}
.code-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 6px 6px 14px;
  border-bottom: 1px solid var(--border);
  background: var(--surface-soft);
}
.code-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--muted);
  font: 600 12px/1.4 ui-monospace, SFMono-Regular, Consolas, monospace;
  letter-spacing: 0.02em;
}
.code-body {
  margin: 0;
  padding: 14px 16px;
  font: 13.5px/1.6 ui-monospace, SFMono-Regular, Consolas, monospace;
  color: var(--text);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  cursor: text;
}
.code-empty { display: grid; gap: 10px; padding: 16px; min-height: 58px; font-size: 14px; color: var(--muted); }
.code-empty.bad { color: var(--danger); }
.skeleton {
  display: block;
  height: 12px;
  border-radius: 6px;
  background: linear-gradient(90deg, #efe9df 0%, #f7f3ec 50%, #efe9df 100%);
  background-size: 200% 100%;
  animation: shimmer 1.4s linear infinite;
}
@keyframes shimmer { to { background-position: -200% 0; } }
@media (prefers-reduced-motion: reduce) { .skeleton { animation: none; } }
</style>
