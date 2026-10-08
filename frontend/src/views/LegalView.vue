<template>
  <div class="docs-page">
    <header class="docs-top">
      <RouterLink to="/" class="brand">
        <img src="/favicon-96x96.png" width="32" height="32" alt="">
        <span>Aimarket</span>
      </RouterLink>
      <nav class="top-nav">
        <RouterLink to="/prices" class="nav-text">Цены</RouterLink>
        <template v-if="isLoggedIn">
          <RouterLink to="/cabinet" class="btn quiet sm">Личный кабинет</RouterLink>
          <button type="button" class="nav-text linkish" @click="logout">Выйти</button>
        </template>
        <RouterLink v-else to="/login" class="btn quiet sm">Вход</RouterLink>
      </nav>
    </header>

    <div class="docs-shell">
      <aside class="docs-side" :class="{ open: navOpen }">
        <div class="side-head">
          <h2>Документы</h2>
          <button type="button" class="side-close" aria-label="Закрыть" @click="navOpen = false">
            <AppIcon name="arrow-left" :size="18" />
          </button>
        </div>
        <nav class="docs-nav" aria-label="Документы">
          <RouterLink
            v-for="item in navItems"
            :key="item.to"
            :to="item.to"
            class="docs-nav-item"
            :class="{ on: item.page === page }"
            @click="navOpen = false"
          >
            <span class="nav-icon"><AppIcon :name="item.icon" :size="16" /></span>
            <span>{{ item.label }}</span>
          </RouterLink>
        </nav>
        <RouterLink to="/support" class="help-card" @click="navOpen = false">
          <span class="help-icon"><AppIcon name="headset" :size="18" /></span>
          <span class="help-text">
            <b>Нужна помощь?</b>
            <small>Напишите в поддержку</small>
          </span>
          <AppIcon name="chevron-right" :size="16" />
        </RouterLink>
      </aside>

      <main class="docs-main">
        <div v-if="data" class="doc-card">
          <RouterLink to="/docs" class="back-link desktop-back">
            <AppIcon name="arrow-left" :size="15" />
            Назад к документам
          </RouterLink>
          <button type="button" class="back-link mobile-back" @click="navOpen = true">
            <AppIcon name="arrow-left" :size="15" />
            Назад к документам
          </button>

          <div class="doc-head">
            <div class="doc-head-text">
              <span class="doc-badge">Документ</span>
              <h1>{{ data.heading }}</h1>
              <p class="doc-meta">
                <AppIcon name="calendar" :size="14" />
                <span>{{ revisionText }}</span>
                <span v-if="emailText" class="meta-sep">·</span>
                <a v-if="emailText" :href="`mailto:${emailText}`">{{ emailText }}</a>
              </p>
            </div>
            <button type="button" class="download-btn" @click="download">
              <AppIcon name="download" :size="16" />
              Скачать
            </button>
          </div>

          <div v-if="summaryText" class="doc-summary">
            <span class="summary-icon">
              <AppIcon :name="pageIcon" :size="20" />
            </span>
            <div>
              <b>{{ summaryTitle }}</b>
              <p>{{ summaryText }}</p>
            </div>
          </div>

          <div class="doc-body">
            <template v-for="(block, index) in contentBlocks" :key="index">
              <p v-if="block.type === 'lead'" class="lead">{{ block.text }}</p>

              <section v-else-if="block.type === 'section'" class="section">
                <div class="section-title">
                  <span class="section-num">{{ block.num }}</span>
                  <h2>{{ block.title }}</h2>
                </div>
              </section>

              <div v-else-if="block.type === 'subsection'" class="subsection">
                <p>
                  <strong>{{ block.num }}</strong>
                  {{ block.text }}
                </p>
                <ul v-if="block.bullets?.length">
                  <li v-for="(bullet, bi) in block.bullets" :key="bi">{{ bullet }}</li>
                </ul>
              </div>

              <p v-else-if="block.type === 'p'" class="plain">{{ block.text }}</p>

              <ul v-else-if="block.type === 'list'" class="plain-list">
                <li v-for="(bullet, bi) in block.items" :key="bi">{{ bullet }}</li>
              </ul>
            </template>
          </div>

          <p v-if="data.footer" class="doc-footer">{{ data.footer }}</p>
        </div>

        <div v-else-if="error" class="doc-card">
          <h1>Страница не найдена</h1>
          <p class="plain">Документ недоступен. Выберите другой в списке слева.</p>
        </div>
        <div v-else class="doc-card loading">
          <p class="plain">Загрузка…</p>
        </div>
      </main>
    </div>

    <div v-if="navOpen" class="nav-backdrop" @click="navOpen = false" />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import AppIcon from '../components/ui/AppIcon.vue'
import { fetchLegalPage } from '../api/site'
import { useSession } from '../composables/useSession'
import { useHead } from '../utils/useHead'

const props = defineProps({
  page: { type: String, required: true },
})

const router = useRouter()
const { isLoggedIn, clearSession } = useSession()

const data = ref(null)
const error = ref(false)
const navOpen = ref(false)

const navItems = [
  { page: 'cookies', to: '/cookies', label: 'Политика в отношении cookies', icon: 'cookie' },
  { page: 'offer', to: '/offer', label: 'Публичная оферта', icon: 'file' },
  { page: 'privacy', to: '/privacy', label: 'Политика конфиденциальности', icon: 'shield' },
  { page: 'consent', to: '/consent', label: 'Согласие на обработку данных', icon: 'lock' },
  { page: 'support', to: '/support', label: 'Справочный центр', icon: 'help' },
]

const pageIcon = computed(() => {
  const map = { cookies: 'cookie', offer: 'file', privacy: 'shield', consent: 'lock' }
  return map[props.page] || 'file'
})

const summaryTitle = computed(() => {
  const map = {
    cookies: 'О политике',
    privacy: 'О политике',
    offer: 'Об оферте',
    consent: 'О согласии',
  }
  return map[props.page] || 'О документе'
})

const revisionText = computed(() => {
  const meta = data.value?.meta || ''
  const part = meta.split('·')[0]?.trim()
  return part || 'Редакция не указана'
})

const emailText = computed(() => {
  const meta = data.value?.meta || ''
  const parts = meta.split('·').map((p) => p.trim())
  const email = parts.find((p) => p.includes('@'))
  return email || ''
})

const summaryText = computed(() => {
  const paras = data.value?.paragraphs || []
  for (const p of paras) {
    const t = String(p || '').trim()
    if (!t) continue
    if (t === data.value?.heading) continue
    if (/^[А-ЯA-Z0-9\s.«»"“”\-—()]{8,80}$/.test(t) && t === t.toUpperCase()) continue
    if (/^\d+\./.test(t)) continue
    if (t.startsWith('(') && t.length < 120) continue
    return t
  }
  return ''
})

const contentBlocks = computed(() => parseBlocks(data.value?.paragraphs || [], data.value?.heading || '', summaryText.value))

function parseBlocks(paragraphs, heading, summary) {
  const blocks = []
  let i = 0
  const skip = new Set()
  if (heading) skip.add(heading.trim())
  if (summary) skip.add(summary.trim())

  while (i < paragraphs.length) {
    const raw = String(paragraphs[i] || '').trim()
    if (!raw || skip.has(raw)) {
      i += 1
      continue
    }
    if (/^[А-ЯA-Z0-9\s.«»"“”\-—()]{8,90}$/.test(raw) && raw === raw.toUpperCase()) {
      i += 1
      continue
    }
    if (raw.startsWith('(') && raw.length < 120 && !/^\d/.test(raw)) {
      i += 1
      continue
    }

    const section = raw.match(/^(\d+)\.\s+(.+)$/)
    if (section && !/^\d+\.\d+/.test(raw) && section[2].length < 90 && !section[2].includes('. ')) {
      blocks.push({ type: 'section', num: section[1], title: titleCase(section[2]) })
      i += 1
      continue
    }

    const sub = raw.match(/^(\d+\.\d+)\.\s+([\s\S]+)$/)
    if (sub) {
      const lines = raw.split('\n').map((l) => l.trim()).filter(Boolean)
      const first = lines[0].replace(/^\d+\.\d+\.\s+/, '')
      const bullets = []
      for (let j = 1; j < lines.length; j += 1) {
        if (lines[j].startsWith('•') || lines[j].startsWith('·')) {
          bullets.push(lines[j].replace(/^[•·]\s*/, ''))
        }
      }
      // also pull following pure-bullet paragraphs
      let k = i + 1
      while (k < paragraphs.length) {
        const next = String(paragraphs[k] || '').trim()
        if (!next) break
        if (next.startsWith('•') || next.startsWith('·') || next.split('\n').every((l) => !l.trim() || l.trim().startsWith('•') || l.trim().startsWith('·'))) {
          next.split('\n').forEach((l) => {
            const t = l.trim()
            if (t.startsWith('•') || t.startsWith('·')) bullets.push(t.replace(/^[•·]\s*/, ''))
          })
          k += 1
          continue
        }
        break
      }
      blocks.push({ type: 'subsection', num: `${sub[1]}.`, text: first, bullets })
      i = k
      continue
    }

    if (raw.startsWith('•') || raw.startsWith('·') || raw.includes('\n•')) {
      const items = raw.split('\n').map((l) => l.trim()).filter((l) => l.startsWith('•') || l.startsWith('·')).map((l) => l.replace(/^[•·]\s*/, ''))
      if (items.length) {
        blocks.push({ type: 'list', items })
        i += 1
        continue
      }
    }

    if (!/^\d+\./.test(raw) && blocks.length === 0) {
      blocks.push({ type: 'lead', text: raw })
      i += 1
      continue
    }

    blocks.push({ type: 'p', text: raw })
    i += 1
  }
  return blocks
}

function titleCase(value) {
  const t = String(value || '').trim()
  if (t === t.toUpperCase() && /[А-ЯA-Z]/.test(t)) {
    return t.charAt(0) + t.slice(1).toLowerCase()
  }
  return t
}

async function load() {
  if (props.page === 'support') {
    router.replace('/support')
    return
  }
  error.value = false
  data.value = null
  try {
    data.value = await fetchLegalPage(props.page)
    useHead(`${data.value.title} — Aimarket`, true)
  } catch {
    error.value = true
    useHead('Страница не найдена — Aimarket', true)
  }
}

function download() {
  if (!data.value) return
  const lines = [data.value.heading, data.value.meta, '', ...(data.value.paragraphs || []), '', data.value.footer || '']
  const blob = new Blob([lines.join('\n\n')], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.page || 'document'}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

function logout() {
  clearSession()
  router.push('/')
}

watch(() => props.page, load, { immediate: true })
</script>

<style scoped>
.docs-page {
  --docs-soft: #f3ebe4;
  --docs-soft-2: #f7f1eb;
  --docs-line: rgba(28, 25, 21, 0.08);
  min-height: 100vh;
  background:
    radial-gradient(ellipse 80% 50% at 10% 0%, rgba(243, 235, 228, 0.9), transparent 55%),
    var(--bg);
  color: var(--text);
}
.docs-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 28px 8px;
  max-width: 1280px;
  margin: 0 auto;
}
.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  letter-spacing: -0.03em;
  font-size: 18px;
}
.brand img {
  width: 32px;
  height: 32px;
  border-radius: 9px;
}
.top-nav {
  display: flex;
  align-items: center;
  gap: 14px;
}
.nav-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--muted-2);
  background: none;
  border: 0;
  padding: 0;
  font: inherit;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.linkish {
  color: var(--muted);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.docs-shell {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 20px;
  max-width: 1280px;
  margin: 0 auto;
  padding: 8px 28px 48px;
  align-items: start;
}

.docs-side {
  position: sticky;
  top: 16px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-height: calc(100vh - 120px);
  padding: 8px 4px 0;
}
.side-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 0 10px;
}
.side-head h2 {
  margin: 0;
  font-size: 22px;
  letter-spacing: -0.03em;
}
.side-close {
  display: none;
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 10px;
  background: var(--docs-soft);
  color: var(--text);
  cursor: pointer;
  place-items: center;
}
.docs-nav {
  display: grid;
  gap: 4px;
}
.docs-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  border-radius: 12px;
  color: var(--muted-2);
  font-size: 14px;
  font-weight: 550;
  line-height: 1.3;
}
.docs-nav-item:hover { background: rgba(255, 255, 255, 0.55); color: var(--text); }
.docs-nav-item.on {
  background: var(--docs-soft);
  color: var(--text);
  font-weight: 650;
}
.nav-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: rgba(255, 255, 255, 0.7);
  color: var(--muted-2);
  flex: 0 0 auto;
}
.docs-nav-item.on .nav-icon {
  background: #fff;
  color: var(--text);
}

.help-card {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid var(--docs-line);
  color: var(--text);
}
.help-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: var(--docs-soft);
  flex: 0 0 auto;
}
.help-text {
  display: grid;
  gap: 2px;
  min-width: 0;
  flex: 1;
}
.help-text b { font-size: 13px; }
.help-text small { color: var(--muted); font-size: 12px; }

.docs-main { min-width: 0; }
.doc-card {
  background: #fff;
  border: 1px solid var(--docs-line);
  border-radius: 22px;
  padding: 28px 32px 36px;
  box-shadow: 0 18px 40px rgba(28, 25, 21, 0.05);
}
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 16px;
  padding: 0;
  border: 0;
  background: none;
  color: var(--muted);
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.mobile-back { display: none; }
.doc-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 22px;
}
.doc-badge {
  display: inline-flex;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--docs-soft);
  color: var(--muted-2);
  font-size: 12px;
  font-weight: 650;
  margin-bottom: 10px;
}
.doc-head h1 {
  margin: 0 0 10px;
  font-size: clamp(26px, 3vw, 34px);
  letter-spacing: -0.035em;
  line-height: 1.15;
}
.doc-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px 8px;
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}
.doc-meta a { color: inherit; text-decoration: underline; text-underline-offset: 2px; }
.meta-sep { opacity: 0.5; }
.download-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
  min-height: 40px;
  padding: 0 14px;
  border-radius: 12px;
  border: 1px solid var(--border-strong);
  background: #fff;
  color: var(--text);
  font: inherit;
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
}
.download-btn:hover { background: var(--docs-soft-2); }

.doc-summary {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  padding: 16px 18px;
  border-radius: 16px;
  background: var(--docs-soft-2);
  margin-bottom: 22px;
}
.summary-icon {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: #fff;
  color: var(--text);
  flex: 0 0 auto;
  box-shadow: 0 4px 14px rgba(28, 25, 21, 0.06);
}
.doc-summary b {
  display: block;
  margin-bottom: 4px;
  font-size: 14px;
}
.doc-summary p {
  margin: 0;
  color: var(--muted-2);
  font-size: 14px;
  line-height: 1.5;
}

.doc-body {
  display: grid;
  gap: 16px;
  color: #3d3832;
  font-size: 15px;
  line-height: 1.65;
}
.lead {
  margin: 0;
  font-size: 15px;
  color: var(--muted-2);
}
.section { margin-top: 8px; }
.section-title {
  display: flex;
  align-items: center;
  gap: 12px;
}
.section-num {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--docs-soft);
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
  flex: 0 0 auto;
}
.section-title h2 {
  margin: 0;
  font-size: 18px;
  letter-spacing: -0.02em;
}
.subsection {
  padding-left: 8px;
}
.subsection p { margin: 0; white-space: pre-line; }
.subsection strong {
  margin-right: 4px;
  color: var(--text);
}
.subsection ul,
.plain-list {
  margin: 10px 0 0;
  padding-left: 20px;
}
.subsection li,
.plain-list li {
  margin: 0 0 6px;
}
.plain {
  margin: 0;
  white-space: pre-line;
}
.doc-footer {
  margin: 28px 0 0;
  padding-top: 18px;
  border-top: 1px solid var(--docs-line);
  color: var(--muted);
  font-size: 13px;
}
.nav-backdrop { display: none; }

@media (max-width: 960px) {
  .docs-top { padding: 14px 16px 6px; }
  .docs-shell {
    grid-template-columns: 1fr;
    padding: 8px 16px 40px;
  }
  .docs-side {
    position: fixed;
    inset: 0 auto 0 0;
    width: min(320px, 88vw);
    z-index: 40;
    background: #faf7f2;
    padding: 18px 14px 20px;
    transform: translateX(-105%);
    transition: transform 0.2s ease;
    box-shadow: 18px 0 40px rgba(28, 25, 21, 0.12);
    min-height: 100vh;
  }
  .docs-side.open { transform: translateX(0); }
  .side-close { display: grid; }
  .desktop-back { display: none; }
  .mobile-back { display: inline-flex; }
  .doc-card { padding: 22px 18px 28px; border-radius: 18px; }
  .doc-head { flex-direction: column; }
  .download-btn { align-self: flex-start; }
  .nav-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 35;
    background: rgba(28, 25, 21, 0.28);
  }
}
</style>
