<template>
  <section ref="root" class="stats-band" aria-label="Aimarket в цифрах">
    <div class="container">
      <div class="stats">
        <div v-for="(stat, i) in stats" :key="stat.label" v-reveal="i * 90" class="stat">
          <b class="value">
            {{ format(values[i], stat) }}<span class="suffix">{{ stat.suffix }}</span>
          </b>
          <span class="label">{{ stat.label }}</span>
        </div>
      </div>
    </div>

    <div class="apps" aria-label="Работает в приложениях">
      <span class="apps-title">Работает в</span>
      <div class="marquee">
        <div class="track">
          <span v-for="(app, i) in [...apps, ...apps]" :key="i" class="app" :aria-hidden="i >= apps.length">
            <i aria-hidden="true">{{ app.glyph }}</i>{{ app.name }}
          </span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { families } from '../../data/tokenPrices'

const modelCount = families.reduce((sum, family) => sum + family.models.length, 0)

const stats = [
  { to: 12400, suffix: '+', label: 'разработчиков пользуются Aimarket' },
  { to: 3.8, digits: 1, suffix: ' млрд', label: 'токенов обрабатываем каждый месяц' },
  { to: modelCount, suffix: '', label: 'оригинальных моделей по одному ключу' },
  { to: 99.95, digits: 2, suffix: '%', label: 'аптайм API за последние 90 дней' },
]
const apps = [
  { name: 'Cursor', glyph: '◆' },
  { name: 'Claude Code', glyph: '›_' },
  { name: 'Codex', glyph: '{ }' },
  { name: 'Claude Desktop', glyph: '✻' },
  { name: 'OpenCode', glyph: '⌘' },
  { name: 'Cline', glyph: '◐' },
  { name: 'Hermes', glyph: '☿' },
  { name: 'Droid', glyph: '◉' },
  { name: 'Grok Build', glyph: '✕' },
  { name: 'Python SDK', glyph: 'py' },
  { name: 'Node.js', glyph: 'js' },
  { name: 'LangChain', glyph: '⛓' },
]

const root = ref(null)
const values = ref(stats.map(() => 0))

function format(value, stat) {
  return value.toLocaleString('ru-RU', {
    minimumFractionDigits: stat.digits || 0,
    maximumFractionDigits: stat.digits || 0,
  })
}

let raf = 0
function animate() {
  const start = performance.now()
  const duration = 1800
  const tick = (now) => {
    const p = Math.min(1, (now - start) / duration)
    const eased = 1 - Math.pow(1 - p, 4)
    values.value = stats.map((s) => s.to * eased)
    if (p < 1) raf = requestAnimationFrame(tick)
  }
  raf = requestAnimationFrame(tick)
}

let io = null
onMounted(() => {
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
    values.value = stats.map((s) => s.to)
    return
  }
  io = new IntersectionObserver(([entry]) => {
    if (!entry.isIntersecting) return
    io.disconnect()
    animate()
  }, { threshold: 0.4 })
  io.observe(root.value)
})
onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  io?.disconnect()
})
</script>

<style scoped>
.stats-band {
  position: relative;
  padding: 40px 0 0;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.55), rgba(255, 255, 255, 0.2));
}
.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.stat {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 28px 36px;
}
.stat + .stat { border-left: 1px solid var(--border); }
.value {
  font-size: clamp(2.2rem, 4vw, 3.4rem);
  font-weight: 650;
  line-height: 1;
  letter-spacing: -0.05em;
  font-variant-numeric: tabular-nums;
}
.suffix {
  background: var(--grad);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.label { color: var(--muted); font-size: 14px; line-height: 1.4; max-width: 22ch; }

.apps {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 18px 0;
  border-top: 1px solid var(--border);
  width: min(1200px, 100%);
  margin: 0 auto;
  padding-left: 24px;
}
.apps-title {
  flex: 0 0 auto;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
}
.marquee {
  flex: 1;
  overflow: hidden;
  -webkit-mask-image: linear-gradient(90deg, transparent, #000 8%, #000 92%, transparent);
  mask-image: linear-gradient(90deg, transparent, #000 8%, #000 92%, transparent);
}
.track {
  display: flex;
  gap: 40px;
  width: max-content;
  animation: marquee 38s linear infinite;
}
.marquee:hover .track { animation-play-state: paused; }
@keyframes marquee { to { transform: translateX(calc(-50% - 20px)); } }
.app {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--muted-2);
  white-space: nowrap;
}
.app i {
  display: grid;
  place-items: center;
  min-width: 28px;
  height: 28px;
  padding: 0 6px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid var(--border);
  font: 600 12px/1 var(--font-mono);
  font-style: normal;
  color: var(--text);
}

@media (max-width: 900px) {
  .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .stat:nth-child(3) { border-left: 0; }
  .stat { padding: 8px 16px 28px; }
}
@media (max-width: 560px) {
  .apps { flex-direction: column; align-items: flex-start; gap: 12px; padding-left: 0; }
  .apps-title { padding-left: 16px; }
  .marquee { width: 100%; }
  .label { font-size: 12.5px; }
}
@media (prefers-reduced-motion: reduce) {
  .track { animation: none; flex-wrap: wrap; width: auto; }
}
</style>
