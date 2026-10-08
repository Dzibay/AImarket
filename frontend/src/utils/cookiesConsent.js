const STORAGE_KEY = 'aimarket_cookies_accepted'
const METRIKA_ID = 113324421

export function hasCookiesConsent() {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export function acceptCookiesConsent() {
  try {
    localStorage.setItem(STORAGE_KEY, '1')
  } catch {
    /* private mode */
  }
  initMetrika()
}

export function initMetrika() {
  if (typeof window === 'undefined') return
  if (window.__aimarketMetrikaReady) return
  if (!hasCookiesConsent()) return

  const load = () => {
    if (typeof window.ym === 'function') {
      window.ym(METRIKA_ID, 'init', {
        ssr: true,
        webvisor: true,
        clickmap: true,
        ecommerce: 'dataLayer',
        referrer: document.referrer,
        url: location.href,
        accurateTrackBounce: true,
        trackLinks: true,
      })
      window.__aimarketMetrikaReady = true
      return
    }
    ;(function (m, e, t, r, i, k, a) {
      m[i] =
        m[i] ||
        function () {
          ;(m[i].a = m[i].a || []).push(arguments)
        }
      m[i].l = 1 * new Date()
      for (let j = 0; j < document.scripts.length; j++) {
        if (document.scripts[j].src === r) return
      }
      k = e.createElement(t)
      a = e.getElementsByTagName(t)[0]
      k.async = 1
      k.src = r
      a.parentNode.insertBefore(k, a)
    })(window, document, 'script', `https://mc.yandex.ru/metrika/tag.js?id=${METRIKA_ID}`, 'ym')

    window.ym(METRIKA_ID, 'init', {
      ssr: true,
      webvisor: true,
      clickmap: true,
      ecommerce: 'dataLayer',
      referrer: document.referrer,
      url: location.href,
      accurateTrackBounce: true,
      trackLinks: true,
    })
    window.__aimarketMetrikaReady = true
  }

  load()
}

export function reachMetrikaGoal(name, params) {
  if (!hasCookiesConsent()) return
  if (typeof window.ym !== 'function') return
  try {
    window.ym(METRIKA_ID, 'reachGoal', name, params)
  } catch {
    /* ignore */
  }
}
