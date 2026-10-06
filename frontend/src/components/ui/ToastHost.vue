<template>
  <div class="toast-host" aria-live="polite">
    <TransitionGroup name="toast">
      <div v-for="item in toasts" :key="item.id" class="toast" :class="item.kind">
        <AppIcon :name="item.kind === 'bad' ? 'alert' : 'check'" :size="16" />
        <span>{{ item.text }}</span>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { useToast } from '../../composables/useToast'
import AppIcon from './AppIcon.vue'

const { toasts } = useToast()
</script>

<style scoped>
.toast-host {
  position: fixed;
  left: 50%;
  bottom: 24px;
  z-index: 100;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  transform: translateX(-50%);
  pointer-events: none;
}
.toast {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 999px;
  background: var(--accent);
  color: var(--bg);
  font-size: 14px;
  font-weight: 600;
  box-shadow: 0 14px 30px rgba(28, 25, 21, 0.22);
  white-space: nowrap;
}
.toast.bad { background: var(--danger); color: #fff; white-space: normal; max-width: min(90vw, 420px); }
.toast-enter-active, .toast-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(8px); }
</style>
