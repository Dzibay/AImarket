import { ref } from 'vue'
import { copyText } from '../utils/format'

const toasts = ref([])
let counter = 0

export function toast(text, kind = 'ok', ttl = 1800) {
  const id = ++counter
  toasts.value = [...toasts.value.slice(-2), { id, text, kind }]
  setTimeout(() => {
    toasts.value = toasts.value.filter((item) => item.id !== id)
  }, ttl)
}

/** Копирует в буфер и показывает уведомление. Возвращает true при успехе. */
export async function copyWithToast(value, label = 'Скопировано') {
  try {
    await copyText(value)
    toast(label)
    return true
  } catch {
    toast('Не удалось скопировать — выделите и скопируйте вручную', 'bad', 3000)
    return false
  }
}

export function useToast() {
  return { toasts, toast, copyWithToast }
}
