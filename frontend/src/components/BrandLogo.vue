<template>
  <!-- OpenAI -->
  <svg v-if="brand === 'gpt'" :width="size" :height="size" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7475-7.0729zm-9.022 12.6081a4.4755 4.4755 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1686a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4944zm-9.6607-4.1254a4.4708 4.4708 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 4.4992 0 0 1-6.1408-1.6464zM2.3408 7.8956a4.485 4.485 0 0 1 2.3655-1.9728V11.6a.7664.7664 0 0 0 .3879.6765l5.8144 3.3543-2.0201 1.1685a.0757.0757 0 0 1-.071 0l-4.8303-2.7865A4.504 4.504 0 0 1 2.3408 7.872zm16.5963 3.8558L13.1038 8.364 15.1192 7.2a.0757.0757 0 0 1 .071 0l4.8303 2.7913a4.4944 4.4944 0 0 1-.6765 8.1042v-5.6772a.79.79 0 0 0-.407-.667zm2.0107-3.0231l-.142-.0852-4.7735-2.7818a.7759.7759 0 0 0-.7854 0L9.409 9.2297V6.8974a.0662.0662 0 0 1 .0284-.0615l4.8303-2.7866a4.4992 4.4992 0 0 1 6.6802 4.66zM8.3065 12.863l-2.02-1.1638a.0804.0804 0 0 1-.038-.0567V6.0742a4.4992 4.4992 0 0 1 7.3757-3.4537l-.142.0805L8.704 5.459a.7948.7948 0 0 0-.3927.6813zm1.0976-2.3654l2.602-1.4998 2.6069 1.4998v2.9994l-2.5974 1.4997-2.6067-1.4997Z" />
  </svg>

  <!-- Anthropic / Claude -->
  <svg v-else-if="brand === 'claude'" :width="size" :height="size" viewBox="0 0 24 24" aria-hidden="true">
    <g fill="none" stroke="#d97757" stroke-width="2.7" stroke-linecap="round" transform="translate(12 12)">
      <line v-for="ray in claudeRays" :key="ray.a" x1="0" :y1="-ray.r0" x2="0" :y2="-ray.r1" :transform="`rotate(${ray.a})`" />
    </g>
  </svg>

  <!-- Google Gemini -->
  <svg v-else-if="brand === 'gemini'" :width="size" :height="size" viewBox="0 0 24 24" aria-hidden="true">
    <defs>
      <linearGradient id="aim-gemini-grad" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#4285f4" />
        <stop offset=".55" stop-color="#9b72cb" />
        <stop offset="1" stop-color="#d96570" />
      </linearGradient>
    </defs>
    <path fill="url(#aim-gemini-grad)" d="M12 0C12 6.627 17.373 12 24 12 17.373 12 12 17.373 12 24 12 17.373 6.627 12 0 12 6.627 12 12 6.627 12 0Z" />
  </svg>

  <!-- DeepSeek -->
  <svg v-else-if="brand === 'deepseek'" :width="size" :height="size" viewBox="0 0 24 24" aria-hidden="true">
    <path fill="#4d6bfe" d="M2.5 12.6c0-4.6 4.1-7.7 9.1-7.7 3.4 0 6.2 1.4 7.7 3.6l2.2-1.2-.6 3.5c.4 1.1.4 2.3 0 3.4-1 2.6-3.9 4.4-7.5 4.4-1.9 0-3.6-.4-5-1.2L6 19.6l.3-3.2C4 15.4 2.5 14.1 2.5 12.6Z" />
    <circle cx="7.6" cy="11.4" r="1.05" fill="#fff" />
  </svg>

  <!-- xAI / Grok -->
  <svg v-else-if="brand === 'grok'" :width="size" :height="size" viewBox="0 0 24 24" aria-hidden="true">
    <g fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round">
      <path d="M4.5 4.5l15 15" />
      <path d="M19.5 4.5l-6 6" />
      <path d="M10.5 13.5l-6 6" />
    </g>
  </svg>

  <!-- Chinese labs (Kimi, Qwen, GLM, Hunyuan, MiniMax) -->
  <svg v-else :width="size" :height="size" viewBox="0 0 24 24" aria-hidden="true">
    <rect x="2.5" y="2.5" width="8.5" height="8.5" rx="2.6" fill="#1c1915" />
    <rect x="13" y="2.5" width="8.5" height="8.5" rx="2.6" fill="#6f4df0" />
    <rect x="2.5" y="13" width="8.5" height="8.5" rx="2.6" fill="#2f6fed" />
    <rect x="13" y="13" width="8.5" height="8.5" rx="2.6" fill="#e5473c" />
  </svg>
</template>

<script setup>
defineProps({
  brand: { type: String, required: true },
  size: { type: [Number, String], default: 24 },
})

// Лучи «солнышка» Claude: слегка разной длины, чтобы знак выглядел живым.
const claudeRays = [
  { a: 0, r0: 2.2, r1: 10.2 },
  { a: 45, r0: 2.2, r1: 8.6 },
  { a: 90, r0: 2.2, r1: 10.2 },
  { a: 135, r0: 2.2, r1: 8.6 },
  { a: 180, r0: 2.2, r1: 10.2 },
  { a: 225, r0: 2.2, r1: 8.6 },
  { a: 270, r0: 2.2, r1: 10.2 },
  { a: 315, r0: 2.2, r1: 8.6 },
]
</script>
