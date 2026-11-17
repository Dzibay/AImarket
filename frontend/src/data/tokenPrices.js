// Каталог router.cheap, снимок от 17 ноября 2026 (scripts/pricing_snapshot.py).
// input/cache/output/price — колонка «Цена» в API-$: в них ведутся баланс и лимит ключа.
// В ₽ — API-$ × курс сервиса (usd_price_rub).
export const PRICE_AS_OF = "17 ноября 2026"
export const PRICE_SOURCE = "https://router.cheap/pricing"
/** Официальная цена в ₽ — по рыночному доллару ≈ курс сервиса × 10 (скидка 90%). */
export const RUB_REFERENCE_RATE_MULT = 10
export const DISCOUNT_PERCENT = 90

export const families = [
  {
    id: "gpt",
    name: "GPT",
    vendor: "OpenAI",
    models: [
      { id: "gpt-5.5", context: 272000, input: 5, cache: 0.5, output: 30 },
      { id: "gpt-5.6-luna", context: 1000000, input: 0.2, cache: 0.02, output: 1.2 },
      { id: "gpt-5.6-sol", context: 1000000, input: 5, cache: 0.5, output: 30 },
      { id: "gpt-5.6-terra", context: 1000000, input: 2, cache: 0.2, output: 12 },
      { id: "gpt-6-astra", context: 1050000, input: 10, cache: 1, output: 50 },
      { id: "gpt-6-luna", context: 1050000, input: 0.1, cache: 0.01, output: 0.5 },
      { id: "gpt-6-sol", context: 1050000, input: 2, cache: 0.2, output: 10 },
      { id: "gpt-6.1-sol", context: 1050000, input: 2, cache: 0.1, output: 10 },
      { id: "gpt-6.1-terra", context: 1050000, input: 1, cache: 0.05, output: 5 },
      { id: "gpt-6.2-astra", context: 1050000, input: 8, cache: 0.4, output: 40 },
    ],
  },
  {
    id: "claude",
    name: "Claude",
    vendor: "Anthropic",
    models: [
      { id: "claude-fable-5", context: 1000000, input: 10, cache: 1, output: 50 },
      { id: "claude-fable-5-1", context: 1000000, input: 10, cache: 0.25, output: 50 },
      { id: "claude-fable-5-2", context: 1000000, input: 8, cache: 0.2, output: 40 },
      { id: "claude-haiku-4-5", context: 200000, input: 1, cache: 0.1, output: 5 },
      { id: "claude-haiku-5-5", context: 1000000, input: 0.1, cache: 0.01, output: 0.5 },
      { id: "claude-opus-4-6", context: 1000000, input: 5, cache: 0.5, output: 25 },
      { id: "claude-opus-4-7", context: 1000000, input: 5, cache: 0.5, output: 25 },
      { id: "claude-opus-4-8", context: 1000000, input: 5, cache: 0.5, output: 25 },
      { id: "claude-opus-5", context: 1000000, input: 5, cache: 0.5, output: 25 },
      { id: "claude-opus-5-5", context: 1000000, input: 4, cache: 0.2, output: 20 },
      { id: "claude-sonnet-4-6", context: 1000000, input: 3, cache: 0.3, output: 15 },
      { id: "claude-sonnet-5", context: 1000000, input: 3, cache: 0.3, output: 15 },
      { id: "claude-sonnet-5-5", context: 1000000, input: 2, cache: 0.2, output: 10 },
    ],
  },
  {
    id: "gemini",
    name: "Gemini",
    vendor: "Google",
    models: [
      { id: "gemini-3.8-flash", context: 1048576, input: 3, cache: 0.3, output: 15 },
      { id: "gemini-4-argon", context: 1048576, input: 4, cache: 0.2, output: 20 },
      { id: "gemini-4-carbon", context: 1048576, input: 4, cache: 0.2, output: 20 },
      { id: "gemini-4-hydrogen", context: 1048576, input: 1.5, cache: 0.075, output: 7.5 },
    ],
  },
  {
    id: "grok",
    name: "Grok",
    vendor: "xAI",
    models: [
      { id: "grok-4.5", context: 500000, input: 2, cache: 0.5, output: 6 },
      { id: "grok-4.6", context: 500000, input: 2, cache: 0.5, output: 6 },
      { id: "grok-4.7", context: 500000, input: 2, cache: 0.5, output: 6 },
    ],
  },
  {
    id: "deepseek",
    name: "DeepSeek",
    vendor: "DeepSeek",
    models: [
      { id: "deepseek-v4-flash", context: 1000000, input: 0.3, cache: 0.006, output: 1.2 },
      { id: "deepseek-v4-flash-0731", context: 1000000, input: 0.3, cache: 0.006, output: 1.2 },
      { id: "deepseek-v4-flash-vision-exp", context: 1000000, input: 0.3, cache: 0.006, output: 1.2 },
      { id: "deepseek-v4-pro", context: 1000000, input: 1.32, cache: 0.044, output: 3.96 },
      { id: "deepseek-v4-pro-0813", context: 1000000, input: 1.32, cache: 0.044, output: 3.96 },
      { id: "deepseek-v4.1-flash", context: 1000000, input: 0.3, cache: 0.006, output: 1.2 },
      { id: "deepseek-v4.1-flash-1017", context: 1000000, input: 0.3, cache: 0.006, output: 1.2 },
    ],
  },
  {
    id: "kimi",
    name: "Kimi · Qwen · GLM",
    vendor: "Moonshot, Alibaba, Zhipu, Tencent, MiniMax, Xiaomi",
    models: [
      { id: "glm-5.2", context: 1000000, input: 1.4, cache: 0.26, output: 4.4 },
      { id: "glm-5.3", context: 1000000, input: 1.4, cache: 0.26, output: 4.4 },
      { id: "glm-5.3-flash", context: 1000000, input: 0.15, cache: 0.03, output: 0.5 },
      { id: "hy3", context: 256000, input: 0.132, cache: 0.033, output: 0.528 },
      { id: "kimi-k2.7-code", context: 256000, input: 0.95, cache: 0.19, output: 4 },
      { id: "kimi-k2.7-code-highspeed", context: 256000, input: 1.9, cache: 0.38, output: 8 },
      { id: "kimi-k3", context: 1048576, input: 3, cache: 0.3, output: 15 },
      { id: "kimi-k3.1-pro", context: 1048576, input: 2, cache: 0.2, output: 10 },
      { id: "mimo-v2.6-pro", context: 1000000, input: 0.435, cache: 0.0036, output: 0.87 },
      { id: "minimax-m3.1-flash", context: 1000000, input: 0.6, cache: 0.12, output: 2.4 },
      { id: "minimax-m3.1-flash-preview", context: 1000000, input: 0.6, cache: 0.12, output: 2.4 },
      { id: "qwen3.8-27b", context: 1000000, input: 0.5, cache: 0.1, output: 3 },
      { id: "qwen3.8-flash", context: 1000000, input: 0.15, cache: 0.016, output: 0.47 },
      { id: "qwen3.8-max", context: 1000000, input: 2, cache: 0.25, output: 6 },
    ],
  },
]

export const mediaFamilies = [
  {
    id: "image",
    name: "Изображения",
    endpoint: "/v1/images/generations",
    models: [
      { id: "gemini-nano-banana-2.1", vendor: "Google", brand: "gemini", unit: "request", price: 0.6 },
      { id: "gpt-image-2", vendor: "OpenAI", brand: "gpt", unit: "request", price: 0.5 },
      { id: "gpt-image-2.5", vendor: "OpenAI", brand: "gpt", unit: "request", price: 0.5 },
      { id: "gpt-image-2.5-flare", vendor: "OpenAI", brand: "gpt", unit: "request", price: 0.5 },
      { id: "gpt-image-2.5-flare-2k", vendor: "OpenAI", brand: "gpt", unit: "request", price: 3.75 },
      { id: "gpt-image-2.5-flare-4k", vendor: "OpenAI", brand: "gpt", unit: "request", price: 3.75 },
      { id: "gpt-image-2.5-sunburst", vendor: "OpenAI", brand: "gpt", unit: "request", price: 0.5 },
      { id: "gpt-image-2.5-sunburst-2k", vendor: "OpenAI", brand: "gpt", unit: "request", price: 3.75 },
      { id: "gpt-image-2.5-sunburst-4k", vendor: "OpenAI", brand: "gpt", unit: "request", price: 3.75 },
      { id: "gpt-image-2.6", vendor: "OpenAI", brand: "gpt", unit: "request", price: 0.5 },
      { id: "gpt-image-2.6-flare", vendor: "OpenAI", brand: "gpt", unit: "request", price: 0.5 },
      { id: "gpt-image-2.6-flare-4k", vendor: "OpenAI", brand: "gpt", unit: "request", price: 3.75 },
      { id: "gpt-image-2.6-sunburst", vendor: "OpenAI", brand: "gpt", unit: "request", price: 0.5 },
      { id: "gpt-image-2.6-sunburst-4k", vendor: "OpenAI", brand: "gpt", unit: "request", price: 3.75 },
      { id: "grok-imagine-image-2.0", vendor: "xAI", brand: "grok", unit: "request", price: 1.2 },
    ],
  },
  {
    id: "video",
    name: "Видео",
    endpoint: "/v1/videos",
    models: [
      { id: "gemini-omni-edit", vendor: "Google", brand: "gemini", unit: "request", price: 0.32 },
      { id: "gemini-omni-fast", vendor: "Google", brand: "gemini", unit: "request", price: 0.255 },
      { id: "grok-imagine-video-1.5", vendor: "xAI", brand: "grok", unit: "second", price: 0.036 },
      { id: "kling-3.0", vendor: "Kling", brand: "china", unit: "second", price: 0.175 },
      { id: "minimax-h3-768p", vendor: "MiniMax", brand: "china", unit: "second", price: 0.1 },
      { id: "seedance-2.0-fast", vendor: "ByteDance", brand: "china", unit: "second", price: 0.15 },
      { id: "seedance-2.0-mini", vendor: "ByteDance", brand: "china", unit: "second", price: 0.072 },
      { id: "seedance-2.5", vendor: "ByteDance", brand: "china", unit: "second", price: 0.27 },
      { id: "veo-3.1-lite", vendor: "Google", brand: "gemini", unit: "second", price: 0.12 },
      { id: "viduq3-turbo", vendor: "Vidu", brand: "china", unit: "second", price: 0.165 },
      { id: "wan-3.0", vendor: "Alibaba", brand: "china", unit: "second", price: 0.125 },
    ],
  },
  {
    id: "audio",
    name: "Озвучка",
    endpoint: "/v1/audio/speech",
    models: [
      { id: "chirp-3-hd", vendor: "Google", brand: "gemini", unit: "request", price: 0.0096 },
      { id: "grok-voice", vendor: "xAI", brand: "grok", unit: "request", price: 0.032 },
    ],
  },
]

export const flagships = [
  { id: "gpt-6-astra", blurb: "Модель по умолчанию" },
  { id: "claude-opus-5-5", blurb: "Самый сильный Claude" },
  { id: "grok-4.7", blurb: "Флагман xAI" },
  { id: "gemini-4-argon", blurb: "Флагман Google" },
  { id: "deepseek-v4-pro", blurb: "Сильная и дешёвая" },
  { id: "kimi-k3", blurb: "Длинный контекст" },
]

export const MEDIA_UNIT_LABELS = {
  image: { request: "за изображение" },
  video: { request: "за ролик", second: "за секунду" },
  audio: { request: "за запрос" },
}

export const textModelCount = families.reduce((sum, family) => sum + family.models.length, 0)
export const mediaModelCount = mediaFamilies.reduce((sum, family) => sum + family.models.length, 0)
export const modelCount = textModelCount + mediaModelCount

function round6(value) {
  return Math.round(value * 1e6) / 1e6
}

/** Наша цена в ₽: API-$ × курс сервиса (usd_price_rub). */
export function ourRubPerMillion(apiUsd, usdRubRate) {
  const rate = Number(usdRubRate)
  if (!(rate > 0)) return Number.NaN
  return round6(Number(apiUsd) * rate)
}

/** Официальная цена в ₽: тот же USD × курс сервиса × RUB_REFERENCE_RATE_MULT. */
export function referenceRubPerMillion(apiUsd, usdRubRate) {
  const rate = Number(usdRubRate)
  if (!(rate > 0)) return Number.NaN
  return round6(Number(apiUsd) * rate * RUB_REFERENCE_RATE_MULT)
}

export function findModel(id) {
  for (const family of families) {
    const model = family.models.find((item) => item.id === id)
    if (model) return { ...model, family }
  }
  return null
}
