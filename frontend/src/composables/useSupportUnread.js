import { ref } from 'vue'
import { webApi } from '../api/web'
import { getSession } from './useSession'

const unread = ref(0)
let pollTimer = null
let inFlight = null

export function useSupportUnread() {
  async function refreshUnread() {
    if (!getSession()) {
      unread.value = 0
      return 0
    }
    if (inFlight) return inFlight
    inFlight = webApi
      .supportUnread()
      .then((data) => {
        unread.value = Number(data.unread || 0)
        return unread.value
      })
      .catch(() => unread.value)
      .finally(() => {
        inFlight = null
      })
    return inFlight
  }

  function clearUnread() {
    unread.value = 0
  }

  function startPolling(ms = 45000) {
    stopPolling()
    refreshUnread()
    pollTimer = setInterval(() => {
      if (document.visibilityState === 'visible') refreshUnread()
    }, ms)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  return { unread, refreshUnread, clearUnread, startPolling, stopPolling }
}
