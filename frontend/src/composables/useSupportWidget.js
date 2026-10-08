import { ref } from 'vue'

const open = ref(false)

export function useSupportWidget() {
  function openChat() {
    open.value = true
  }

  function closeChat() {
    open.value = false
  }

  function toggleChat() {
    open.value = !open.value
  }

  return {
    open,
    openChat,
    closeChat,
    toggleChat,
  }
}
