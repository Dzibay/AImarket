import { ref } from 'vue'
import { webApi } from '../api/web'
import { getGuestSupportToken } from './useGuestSupport'
import { getSession } from './useSession'

const unread = ref(0)
let pollTimer = null
let inFlight = null

export function useSupportUnread() {
  async function refreshUnread() {
    if (inFlight) return inFlight
    inFlight = (async () => {
      try {
        if (getSession()) {
          const data = await webApi.supportUnread()
          unread.value = Number(data.unread || 0)
        } else {
          const token = getGuestSupportToken()
          if (!token) {
            unread.value = 0
            return 0
          }
          const data = await webApi.supportGuestUnread(token)
          unread.value = Number(data.unread || 0)
        }
        return unread.value
      } catch {
        return unread.value
      }
    })().finally(() => {
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
