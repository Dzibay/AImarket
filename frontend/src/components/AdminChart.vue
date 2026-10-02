<template>
  <div class="admin-chart" :class="tone">
    <div class="chart-head">
      <div>
        <h3>{{ title }}</h3>
        <p v-if="subtitle" class="muted chart-sub">{{ subtitle }}</p>
      </div>
      <div v-if="totalLabel" class="chart-total">
        <span class="muted">Итого</span>
        <b>{{ totalLabel }}</b>
      </div>
    </div>

    <div class="chart-body">
      <div class="y-axis" aria-hidden="true">
        <span v-for="tick in ticks" :key="tick.ratio">{{ tick.label }}</span>
      </div>

      <div
        class="plot-wrap"
        @mouseleave="hover = null"
      >
        <div class="plot">
          <div class="grid" aria-hidden="true">
            <i v-for="tick in ticks" :key="'g-' + tick.ratio" />
          </div>
          <div class="bars">
            <button
              v-for="(bar, index) in bars"
              :key="bar.day + '-' + index"
              type="button"
              class="bar"
              :class="{ empty: bar.empty, on: hover === index }"
              :style="{ height: barHeight(bar) }"
              :aria-label="bar.title"
              @mouseenter="hover = index"
              @focus="hover = index"
              @blur="hover = null"
            >
              <span class="fill" />
            </button>
          </div>
          <div
            v-if="hoverBar"
            class="tooltip"
            :style="tooltipStyle"
          >
            <b>{{ hoverBar.dayLabel }}</b>
            <span>{{ hoverBar.display }}</span>
            <span v-if="hoverBar.detail" class="muted">{{ hoverBar.detail }}</span>
          </div>
        </div>

        <div class="x-axis">
          <span
            v-for="(bar, index) in bars"
            :key="'x-' + index"
            :class="{ show: bar.showLabel }"
          >{{ bar.showLabel ? bar.label : '' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  totalLabel: { type: String, default: '' },
  bars: { type: Array, default: () => [] },
  ticks: { type: Array, default: () => [] },
  /** revenue | spend | users */
  tone: { type: String, default: 'revenue' },
})

const hover = ref(null)
const plotHeight = 168

const hoverBar = computed(() => {
  if (hover.value == null) return null
  return props.bars[hover.value] || null
})

const tooltipStyle = computed(() => {
  const count = props.bars.length || 1
  const index = hover.value ?? 0
  const left = ((index + 0.5) / count) * 100
  const clamped = Math.min(92, Math.max(8, left))
  return { left: `${clamped}%` }
})

function barHeight(bar) {
  if (bar.empty || !bar.heightRatio) return '4px'
  return `${Math.max(6, Math.round(bar.heightRatio * plotHeight))}px`
}
</script>

<style scoped>
.admin-chart {
  --bar-top: #2f6b4f;
  --bar-bottom: #1f4d39;
  --bar-empty: #e7e0d6;
  --tip-bg: #1c1915;
  padding: 16px 16px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: #fff;
}
.admin-chart.spend {
  --bar-top: #c47a2c;
  --bar-bottom: #8a5314;
}
.admin-chart.users {
  --bar-top: #3d6ea5;
  --bar-bottom: #244a73;
}

.chart-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.chart-head h3 { margin: 0; font-size: 15px; font-weight: 600; }
.chart-sub { margin: 4px 0 0; font-size: 12px; }
.chart-total { text-align: right; }
.chart-total span { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; }
.chart-total b { font-size: 18px; letter-spacing: -0.03em; }

.chart-body {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  gap: 8px;
  align-items: stretch;
}
.y-axis {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 168px;
  padding-top: 2px;
  text-align: right;
  font-size: 11px;
  color: var(--muted);
  line-height: 1;
}

.plot-wrap { position: relative; min-width: 0; }
.plot {
  position: relative;
  height: 168px;
  border-bottom: 1px solid var(--border-strong);
}
.grid {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  pointer-events: none;
}
.grid i {
  display: block;
  height: 0;
  border-top: 1px dashed #e4ddd2;
}
.bars {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: flex-end;
  gap: 3px;
}
.bar {
  flex: 1 1 0;
  min-width: 0;
  max-width: 28px;
  margin: 0 auto;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: flex-end;
  height: 100%;
}
.bar .fill {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 5px 5px 0 0;
  background: linear-gradient(180deg, var(--bar-top) 0%, var(--bar-bottom) 100%);
  transition: opacity 0.12s ease, filter 0.12s ease;
}
.bar.empty .fill {
  background: var(--bar-empty);
  min-height: 4px;
}
.bar.on .fill,
.bar:hover .fill {
  filter: brightness(1.08);
  outline: 2px solid rgba(28, 25, 21, 0.12);
  outline-offset: 1px;
}

.x-axis {
  display: flex;
  gap: 3px;
  margin-top: 8px;
  min-height: 16px;
}
.x-axis span {
  flex: 1 1 0;
  min-width: 0;
  max-width: 28px;
  margin: 0 auto;
  font-size: 10px;
  color: var(--muted);
  text-align: center;
  overflow: hidden;
  white-space: nowrap;
}
.x-axis span:not(.show) { visibility: hidden; }

.tooltip {
  position: absolute;
  top: 8px;
  transform: translateX(-50%);
  z-index: 4;
  min-width: 120px;
  max-width: 200px;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--tip-bg);
  color: #f4f1ea;
  box-shadow: 0 10px 24px rgba(28, 25, 21, 0.22);
  pointer-events: none;
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 13px;
}
.tooltip b { font-size: 12px; font-weight: 600; opacity: 0.8; }
.tooltip .muted { color: #cfc6b8; font-size: 12px; }

@media (max-width: 640px) {
  .chart-body { grid-template-columns: 44px minmax(0, 1fr); }
  .y-axis { font-size: 10px; }
}
</style>
