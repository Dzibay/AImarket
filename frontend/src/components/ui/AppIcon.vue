<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    class="icon"
    v-html="PATHS[name] || ''"
  />
</template>

<script setup>
defineProps({
  name: { type: String, required: true },
  size: { type: Number, default: 18 },
})

// Простые контурные иконки, одинаковой толщины; без внешних зависимостей.
const PATHS = {
  copy: '<rect x="9" y="9" width="11" height="11" rx="2.5"/><path d="M5 15V6.5A1.5 1.5 0 0 1 6.5 5H15"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  eye: '<path d="M2.5 12s3.5-6.5 9.5-6.5S21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/>',
  'eye-off': '<path d="M3 3l18 18"/><path d="M10.6 5.8A10 10 0 0 1 12 5.5c6 0 9.5 6.5 9.5 6.5a16 16 0 0 1-3.2 3.9"/><path d="M6.6 6.7A16 16 0 0 0 2.5 12S6 18.5 12 18.5a9.7 9.7 0 0 0 4-.9"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
  download: '<path d="M12 4v11"/><path d="M7.5 10.5L12 15l4.5-4.5"/><path d="M4 19h16"/>',
  refresh: '<path d="M20 11a8 8 0 0 0-14.6-3.5"/><path d="M4 4v4.5h4.5"/><path d="M4 13a8 8 0 0 0 14.6 3.5"/><path d="M20 20v-4.5h-4.5"/>',
  wallet: '<rect x="3" y="6" width="18" height="13" rx="2.5"/><path d="M3 10h18"/><path d="M15.5 15h2"/>',
  key: '<circle cx="8" cy="14" r="4"/><path d="M11 11l8-8"/><path d="M16 6l2.5 2.5"/><path d="M13.5 8.5L16 11"/>',
  plug: '<path d="M9 3v5"/><path d="M15 3v5"/><path d="M6 8h12v3a6 6 0 0 1-12 0z"/><path d="M12 17v4"/>',
  history: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
  help: '<circle cx="12" cy="12" r="8.5"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .9-1 1.7"/><path d="M12 17h.01"/>',
  chat: '<path d="M4.5 5.5h15a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H10l-4 3.2V17.5H4.5a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2z"/>',
  home: '<path d="M4 11l8-7 8 7"/><path d="M6 10v10h12V10"/>',
  'arrow-up': '<path d="M12 19V5"/><path d="M6 11l6-6 6 6"/>',
  'arrow-down': '<path d="M12 5v14"/><path d="M6 13l6 6 6-6"/>',
  chevron: '<path d="M8 10l4 4 4-4"/>',
  external: '<path d="M14 4h6v6"/><path d="M20 4l-9 9"/><path d="M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/>',
  terminal: '<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="M7 9.5l3 2.5-3 2.5"/><path d="M12.5 15h4.5"/>',
  alert: '<path d="M12 4l9 16H3z"/><path d="M12 10v4"/><path d="M12 17h.01"/>',
  spark: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/>',
  send: '<path d="M4 12l16-8-6 16-2.5-6.5z"/>',
  shield: '<path d="M12 3l7 3v5.5c0 4.3-3 7.6-7 9.5-4-1.9-7-5.2-7-9.5V6z"/><path d="M9.5 12l2 2 3.5-3.5"/>',
  lock: '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  windows: '<path d="M4 6l7-1v7H4z"/><path d="M12 5l8-1v8h-8z"/><path d="M4 13h7v6l-7-1z"/><path d="M12 13h8v7l-8-1z"/>',
  apple: '<path d="M15.5 3c0 1.6-1.2 3.2-3 3.3-.2-1.7 1.3-3.3 3-3.3z"/><path d="M17.8 17.5c-.8 1.8-2 3.5-3.4 3.5-1.2 0-1.6-.8-3-.8s-1.8.8-3 .8C7 21 5 17.6 5 14.3 5 11 7 9.2 9 9.2c1.2 0 2.2.8 2.9.8.7 0 1.9-1 3.3-.9 1.1 0 2.5.5 3.3 1.7-2.9 1.7-2.4 5.8.7 6.7z"/>',
  linux: '<circle cx="12" cy="8" r="4"/><path d="M8 12.5c-2 2.5-3 5-2.5 7.5h13c.5-2.5-.5-5-2.5-7.5"/><path d="M10 9h.01"/><path d="M14 9h.01"/>',
  logout: '<path d="M10 4H5.5A1.5 1.5 0 0 0 4 5.5v13A1.5 1.5 0 0 0 5.5 20H10"/><path d="M15 8l4 4-4 4"/><path d="M19 12H9"/>',
  tag: '<path d="M12.5 3.5l8 8-7.5 7.5-8-8V3.5z"/><path d="M16.5 8h.01"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="M3.5 7l8.5 6 8.5-6"/>',
  telegram: '<path d="M21 4L3 11l6 2 2 6 3-4 4.5 3z"/><path d="M9 13l9-7"/>',
}
</script>

<style scoped>
.icon { flex: 0 0 auto; display: inline-block; vertical-align: -0.2em; }
</style>
