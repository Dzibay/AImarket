import { computed, ref } from 'vue'
import { webApi } from '../api/web'

const config = ref(null)
let loadPromise = null

/** Публичный конфиг сайта (/api/web/config), с кешем между страницами. */
export function useWebConfig() {
  const usdPriceRub = computed(() => Number(config.value?.usd_price_rub || 0))

  async function loadConfig() {
    if (config.value) return config.value
    if (!loadPromise) {
      loadPromise = webApi
        .config()
        .then((data) => {
          config.value = data
          return data
        })
        .catch(() => {
          config.value = { sales_open: false, usd_price_rub: 0, min_topup_usd: 10 }
          return config.value
        })
        .finally(() => {
          loadPromise = null
        })
    }
    return loadPromise
  }

  return { config, usdPriceRub, loadConfig }
}
