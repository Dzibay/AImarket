<template>
  <header class="site-header" :class="{ scrolled, overlay: isHome, 'menu-open': menuOpen }">
    <div class="bar">
      <RouterLink to="/" class="brand" @click="menuOpen = false">
        <img src="/favicon-96x96.png" width="32" height="32" alt="">
        <span>Aimarket</span>
      </RouterLink>

      <nav v-if="!cabinetMenu" class="anchors" aria-label="Разделы">
        <RouterLink v-for="link in links" :key="link.hash" :to="{ path: '/', hash: link.hash }">{{ link.label }}</RouterLink>
      </nav>

      <div class="nav">
        <template v-if="isLoggedIn">
          <template v-if="cabinetMenu">
            <div class="cabinet-desktop nav-logged">
              <RouterLink to="/cabinet" class="ghost">Личный кабинет</RouterLink>
              <button type="button" class="link" @click="logout">Выйти</button>
            </div>
            <button
              type="button"
              class="menu-btn cabinet-mobile"
              :aria-expanded="cabinetMenuOpen"
              aria-controls="cabinet-mobile-nav"
              aria-label="Разделы кабинета"
              @click="$emit('cabinet-menu')"
            >
              <AppIcon :name="cabinetMenuOpen ? 'close' : 'menu'" :size="20" />
            </button>
          </template>
          <template v-else>
            <RouterLink to="/cabinet" class="cta cabinet-link">
              <span class="label-full">Личный кабинет</span>
              <span class="label-short">Кабинет</span>
            </RouterLink>
            <button type="button" class="link hide-sm" @click="logout">Выйти</button>
          </template>
        </template>
        <template v-else>
          <RouterLink to="/login" class="ghost hide-sm">Войти</RouterLink>
          <button type="button" class="cta" @click="getAccess">
            Получить доступ
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14" /><path d="m13 6 6 6-6 6" /></svg>
          </button>
        </template>

        <button
          v-if="!cabinetMenu"
          type="button"
          class="menu-btn site-mobile"
          :aria-expanded="menuOpen"
          aria-controls="site-mobile-nav"
          aria-label="Меню"
          @click="menuOpen = !menuOpen"
        >
          <AppIcon :name="menuOpen ? 'close' : 'menu'" :size="20" />
        </button>
      </div>
    </div>

    <Transition name="drop">
      <nav v-if="menuOpen && !cabinetMenu" id="site-mobile-nav" class="mobile-nav" aria-label="Меню">
        <RouterLink
          v-for="link in links"
          :key="link.hash"
          :to="{ path: '/', hash: link.hash }"
          @click="menuOpen = false"
        >{{ link.label }}<span aria-hidden="true">→</span></RouterLink>
        <RouterLink v-if="!isLoggedIn" to="/login" @click="menuOpen = false">Войти<span aria-hidden="true">→</span></RouterLink>
        <button v-else type="button" class="mobile-logout" @click="logout">Выйти</button>
      </nav>
    </Transition>
  </header>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AppIcon from './ui/AppIcon.vue'
import { useSession } from '../composables/useSession'

defineProps({
  cabinetMenu: { type: Boolean, default: false },
  cabinetMenuOpen: { type: Boolean, default: false },
})
defineEmits(['cabinet-menu'])

const links = [
  { hash: '#how', label: 'Как подключить' },
  { hash: '#savings', label: 'Экономия' },
  { hash: '#prices', label: 'Цены' },
  { hash: '#pay', label: 'Пополнение' },
  { hash: '#faq', label: 'FAQ' },
]

const route = useRoute()
const router = useRouter()
const { isLoggedIn, clearSession } = useSession()
const isHome = computed(() => route.name === 'home')
const scrolled = ref(false)
const menuOpen = ref(false)

watch(() => route.fullPath, () => { menuOpen.value = false })

function onScroll() {
  scrolled.value = window.scrollY > 24
}

function focusSignup() {
  const input = document.getElementById('signup-hero')
  if (!input) return false
  input.scrollIntoView({ behavior: 'smooth', block: 'center' })
  setTimeout(() => input.focus({ preventScroll: true }), 400)
  return true
}

async function getAccess() {
  menuOpen.value = false
  if (isHome.value && focusSignup()) return
  await router.push('/')
  await nextTick()
  setTimeout(focusSignup, 120)
}

function logout() {
  menuOpen.value = false
  clearSession()
  router.push('/')
}

onMounted(() => {
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
})
onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))
</script>

<style scoped>
.site-header {
  position: sticky;
  top: 0;
  z-index: 50;
  padding: 14px 16px 0;
  pointer-events: none;
}
/* На главной шапка плавает поверх первого экрана. */
.site-header.overlay { margin-bottom: -78px; }
.bar {
  pointer-events: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: min(1240px, 100%);
  height: 64px;
  margin: 0 auto;
  padding: 0 10px 0 16px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.75);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.8) inset, 0 10px 30px -20px rgba(60, 40, 15, 0.35);
  backdrop-filter: blur(18px) saturate(1.4);
  -webkit-backdrop-filter: blur(18px) saturate(1.4);
  transition: width 0.5s var(--ease-out), height 0.4s var(--ease-out), background 0.3s ease, box-shadow 0.3s ease;
}
.scrolled .bar {
  width: min(1060px, 100%);
  height: 56px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.8) inset, 0 18px 40px -20px rgba(60, 40, 15, 0.4);
}
.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex: 0 0 auto;
  font-weight: 700;
  letter-spacing: -0.035em;
  font-size: 18px;
}
.brand img { width: 32px; height: 32px; border-radius: 9px; box-shadow: 0 6px 16px rgba(28, 25, 21, 0.14); }

.anchors { display: flex; align-items: center; gap: 2px; }
.anchors a {
  padding: 8px 13px;
  border-radius: 999px;
  color: var(--muted-2);
  font-size: 14.5px;
  font-weight: 550;
  transition: background 0.2s ease, color 0.2s ease;
}
.anchors a:hover { background: rgba(28, 25, 21, 0.05); color: var(--text); }

.nav { display: flex; align-items: center; gap: 8px; flex: 0 0 auto; }
.nav-logged { display: flex; align-items: center; gap: 12px; }
.menu-btn.cabinet-mobile, .menu-btn.site-mobile { display: none; }
.cabinet-link { white-space: nowrap; }
.label-short { display: none; }
.link {
  background: none;
  border: 0;
  padding: 0 6px;
  font: inherit;
  font-size: 14px;
  color: var(--muted);
  cursor: pointer;
}
.link:hover { color: var(--text); }
.ghost {
  display: inline-flex;
  align-items: center;
  min-height: 42px;
  padding: 0 16px;
  border-radius: 999px;
  color: var(--text);
  font-size: 14.5px;
  font-weight: 600;
  transition: background 0.2s ease;
}
.ghost:hover { background: rgba(28, 25, 21, 0.05); }
.cta {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  padding: 0 18px;
  border: 0;
  border-radius: 999px;
  background: linear-gradient(180deg, #2b2620, var(--ink));
  color: #fff;
  font: inherit;
  font-size: 14.5px;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.18), 0 8px 20px -8px rgba(21, 18, 14, 0.6);
  transition: transform 0.2s var(--ease-out);
}
.cta svg { transition: transform 0.25s var(--ease-out); }
.cta:hover svg { transform: translateX(3px); }
.cta:active { transform: scale(0.97); }
.menu-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.8);
  color: var(--text);
  cursor: pointer;
}

.mobile-nav {
  pointer-events: auto;
  display: grid;
  width: min(1240px, 100%);
  margin: 8px auto 0;
  padding: 8px;
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(255, 255, 255, 0.95);
  box-shadow: var(--shadow-lg);
  backdrop-filter: blur(18px);
}
.mobile-nav a, .mobile-logout {
  display: flex;
  justify-content: space-between;
  padding: 15px 16px;
  border: 0;
  border-radius: 16px;
  background: none;
  color: var(--text);
  font: inherit;
  font-size: 17px;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
}
.mobile-nav a span { color: var(--muted); }
.mobile-nav a:hover, .mobile-logout:hover { background: rgba(28, 25, 21, 0.05); }
.drop-enter-active, .drop-leave-active { transition: opacity 0.25s ease, transform 0.35s var(--ease-out); }
.drop-enter-from, .drop-leave-to { opacity: 0; transform: translateY(-8px) scale(0.98); }

@media (max-width: 1040px) {
  .anchors { display: none; }
  .menu-btn.site-mobile { display: inline-flex; }
  .cabinet-desktop { display: none; }
  .menu-btn.cabinet-mobile { display: inline-flex; }
}
@media (max-width: 560px) {
  .site-header { padding: 10px 10px 0; }
  .site-header.overlay { margin-bottom: -70px; }
  .bar, .scrolled .bar { height: 58px; padding: 0 7px 0 12px; gap: 8px; }
  .brand { font-size: 17px; }
  .hide-sm { display: none; }
  .cta { min-height: 42px; padding: 0 14px; font-size: 14px; }
  .cta svg { display: none; }
  .label-full { display: none; }
  .label-short { display: inline; }
  .menu-btn { width: 42px; height: 42px; }
}
@media (max-width: 360px) {
  .brand span { display: none; }
}
</style>
