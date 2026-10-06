// Официальные цены OpenRouter за 1 млн токенов, снимок от 6 октября 2026.
// Списание с баланса в USD: официальная × PRICE_FACTOR.
// На сайте USD — как в каталоге; в ₽ — тот же USD × usd_price_rub (скидка 90% = курс сервиса, не ×0.1).
export const PRICE_AS_OF = "6 октября 2026"
export const PRICE_SOURCE = "https://openrouter.ai/models"
export const PRICE_FACTOR = 0.1
/** Множитель «было» в ₽ относительно курса сервиса (≈ −90%). */
export const RUB_REFERENCE_RATE_MULT = 10

export const families = [
  {
    id: "gpt",
    name: "GPT",
    vendor: "OpenAI",
    models: [
      { id: "gpt-5.4", context: 1050000, input: 2.5, output: 15 },
      { id: "gpt-5.4-mini", context: 400000, input: 0.75, output: 4.5 },
      { id: "gpt-5.5", context: 1050000, input: 5, output: 30 },
      { id: "gpt-5.6-luna", context: 1050000, input: 0.2, output: 1.2 },
      { id: "gpt-5.6-sol", context: 1050000, input: 2, output: 10 },
      { id: "gpt-5.6-terra", context: 1050000, input: 2, output: 12 },
      { id: "gpt-6-astra", context: 1050000, input: 10, output: 50 },
      { id: "gpt-6-luna", context: 1050000, input: 0.1, output: 0.5 },
      { id: "gpt-6-sol", context: 1050000, input: 2, output: 10 },
      { id: "gpt-6.1-sol", context: 1050000, input: 2, output: 10 },
    ],
  },
  {
    id: "claude",
    name: "Claude",
    vendor: "Anthropic",
    models: [
      { id: "claude-fable-5", context: 1000000, input: 10, output: 50 },
      { id: "claude-fable-5-1", context: 1000000, input: 10, output: 50 },
      { id: "claude-haiku-4-5", context: 200000, input: 1, output: 5 },
      { id: "claude-opus-4-7", context: 1000000, input: 5, output: 25 },
      { id: "claude-opus-4-8", context: 1000000, input: 5, output: 25 },
      { id: "claude-opus-5", context: 1000000, input: 5, output: 25 },
      { id: "claude-opus-5-5", context: 1000000, input: 4, output: 20 },
      { id: "claude-sonnet-4-6", context: 1000000, input: 3, output: 15 },
      { id: "claude-sonnet-5", context: 1000000, input: 2, output: 10 },
      { id: "claude-sonnet-5-5", context: 1000000, input: 2, output: 10 },
    ],
  },
  {
    id: "gemini",
    name: "Gemini",
    vendor: "Google",
    models: [
      { id: "gemini-3.1-pro-preview", context: 1048576, input: 2, output: 12 },
      { id: "gemini-3.5-flash", context: 1048576, input: 1.5, output: 9 },
      { id: "gemini-3.6-flash", context: 1048576, input: 0.75, output: 3.75 },
      { id: "gemini-3.7-flash", context: 1048576, input: 0.75, output: 3.75 },
      { id: "gemini-3.8-flash", context: 1048576, input: 0.75, output: 3.75 },
    ],
  },
  {
    id: "grok",
    name: "Grok",
    vendor: "xAI",
    models: [
      { id: "grok-4.5", context: 500000, input: 2, output: 6 },
      { id: "grok-4.6", context: 500000, input: 2, output: 6 },
      { id: "grok-4.7", context: 500000, input: 2, output: 6 },
    ],
  },
  {
    id: "deepseek",
    name: "DeepSeek",
    vendor: "DeepSeek",
    models: [
      { id: "deepseek-v4-flash", context: 1048576, input: 0.012, output: 1.28 },
      { id: "deepseek-v4-flash-0731", context: 1048576, input: 0.0134, output: 1.28 },
      { id: "deepseek-v4-flash-vision-exp", context: 1048576, input: 0.2156, output: 0.6468 },
      { id: "deepseek-v4-pro", context: 1048576, input: 0.2088, output: 0.4176 },
      { id: "deepseek-v4-pro-0813", context: 1048576, input: 0.66, output: 1.98 },
      { id: "deepseek-v4.1-flash", context: 1048576, input: 0.021421, output: 1.32 },
    ],
  },
  {
    id: "kimi",
    name: "Kimi · Qwen",
    vendor: "Moonshot, Alibaba, Zhipu, Tencent, MiniMax",
    models: [
      { id: "kimi-k2.6", context: 262144, input: 0.95, output: 4 },
      { id: "kimi-k2.7-code", context: 262144, input: 0.6712, output: 3.35 },
      { id: "kimi-k3", context: 1048576, input: 0.95, output: 14 },
      { id: "qwen3.8-flash", context: 1000000, input: 0.15, output: 0.47 },
      { id: "qwen3.8-max", context: 1000000, input: 2, output: 6 },
      { id: "glm-5.1", context: 204800, input: 1.4, output: 4.4 },
      { id: "glm-5.2", context: 1048576, input: 0.152, output: 12 },
      { id: "glm-5.3", context: 1048576, input: 0.07, output: 7 },
      { id: "glm-5.3-flash", context: 1048576, input: 0.15, output: 0.5 },
      { id: "hy3", context: 262144, input: 0.132, output: 0.528 },
      { id: "hy4", context: 1048576, input: 0.834, output: 2.501 },
      { id: "minimax-m3", context: 1048576, input: 0.3, output: 1.2 },
      { id: "mimo-v2.5-pro", context: 1050000, input: 0.435, output: 0.87 },
    ],
  },
]

export const flagships = [
  { id: "gpt-6-astra", blurb: "Модель по умолчанию" },
  { id: "claude-opus-5-5", blurb: "Самый сильный Claude" },
  { id: "grok-4.7", blurb: "Флагман xAI" },
  { id: "gemini-3.1-pro-preview", blurb: "Флагман Google" },
  { id: "deepseek-v4-pro", blurb: "Сильная и дешёвая" },
  { id: "kimi-k3", blurb: "Длинный контекст" },
]

export function ourPrice(official) {
  return Math.round(Number(official) * PRICE_FACTOR * 1e6) / 1e6
}

/** Цена в ₽ за 1 млн: официальный USD × курс сервиса (usd_price_rub). */
export function ourRubPerMillion(officialUsd, usdRubRate) {
  const rate = Number(usdRubRate)
  if (!(rate > 0)) return Number.NaN
  return Math.round(Number(officialUsd) * rate * 1e6) / 1e6
}

/** Ориентир «было» в ₽: тот же USD × курс × RUB_REFERENCE_RATE_MULT. */
export function referenceRubPerMillion(officialUsd, usdRubRate) {
  const rate = Number(usdRubRate)
  if (!(rate > 0)) return Number.NaN
  return Math.round(Number(officialUsd) * rate * RUB_REFERENCE_RATE_MULT * 1e6) / 1e6
}

export function findModel(id) {
  for (const family of families) {
    const model = family.models.find((item) => item.id === id)
    if (model) return { ...model, family }
  }
  return null
}
