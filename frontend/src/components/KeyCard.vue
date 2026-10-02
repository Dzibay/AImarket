<template>
  <section class="card key-card">
    <div class="key-head">
      <h2 class="key-title">{{ title }}</h2>
      <span v-if="highlight" class="badge warn">Сохраните прямо сейчас</span>
    </div>

    <div class="secret-row">
      <code class="secret" :class="{ hidden: !revealed }">{{ revealed ? secret : masked }}</code>
      <div class="secret-actions">
        <button type="button" class="btn quiet sm" @click="revealed = !revealed">
          {{ revealed ? 'Скрыть' : 'Показать' }}
        </button>
        <button type="button" class="btn sm" @click="copy">{{ copied ? 'Скопировано' : 'Скопировать' }}</button>
      </div>
    </div>

    <div class="explain">
      <p class="lead-line">
        <b>Этот ключ — ваш единственный доступ к сервису.</b> Он работает сразу в двух ролях:
      </p>
      <ol>
        <li>
          <b>Пароль для входа на сайт.</b> Логина и пароля у вас нет — чтобы попасть в личный кабинет,
          вставьте этот ключ на странице <RouterLink to="/login">«Войти по ключу»</RouterLink>.
        </li>
        <li>
          <b>API-ключ для нейросетей.</b> Укажите его в Cursor, Codex, Claude Code или любом другом
          приложении как <code>API key</code>, а в поле адреса сервера (<code>Base URL</code>) —
          <code class="base">{{ baseUrl }}</code>
          <button type="button" class="mini" @click="copyBase">{{ copiedBase ? '✓' : 'копировать' }}</button>
        </li>
      </ol>
      <p class="warn-line">
        Сохраните ключ в менеджере паролей или заметках. Если ключ потеряется, вы не сможете войти в
        кабинет — восстановить доступ можно будет только через поддержку. Никому не передавайте ключ:
        любой, у кого он есть, сможет тратить ваш баланс.
      </p>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { copyText } from '../utils/format'

const props = defineProps({
  secret: { type: String, required: true },
  baseUrl: { type: String, default: '' },
  title: { type: String, default: 'Ваш ключ доступа' },
  highlight: { type: Boolean, default: false },
  revealByDefault: { type: Boolean, default: false },
})

const revealed = ref(props.revealByDefault)
const copied = ref(false)
const copiedBase = ref(false)

const masked = computed(() => {
  const value = props.secret || ''
  if (value.length <= 12) return '••••••••••••'
  return `${value.slice(0, 7)}${'•'.repeat(Math.min(24, value.length - 11))}${value.slice(-4)}`
})

async function copy() {
  try {
    await copyText(props.secret)
    copied.value = true
    setTimeout(() => { copied.value = false }, 1500)
  } catch {
    revealed.value = true
  }
}

async function copyBase() {
  try {
    await copyText(props.baseUrl)
    copiedBase.value = true
    setTimeout(() => { copiedBase.value = false }, 1500)
  } catch {
    /* ignore */
  }
}
</script>

<style scoped>
.key-card { padding: 24px; }
.key-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.key-title { margin: 0; font-size: 1.25rem; letter-spacing: -0.03em; }
.secret-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  background: var(--surface-soft);
  border: 1px solid var(--border-strong);
}
.secret {
  flex: 1 1 260px;
  min-width: 0;
  overflow-wrap: anywhere;
  font-size: 15px;
  font-weight: 600;
}
.secret.hidden { letter-spacing: 0.08em; color: var(--muted); }
.secret-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.explain { margin-top: 18px; font-size: 15px; }
.lead-line { margin: 0 0 10px; }
.explain ol { margin: 0 0 14px; padding-left: 22px; }
.explain li { margin-bottom: 10px; }
.explain li + li { margin-top: 10px; }
.explain a { text-decoration: underline; text-underline-offset: 3px; }
.explain code { font-size: 13px; background: var(--surface-soft); padding: 1px 6px; border-radius: 6px; }
.explain code.base { overflow-wrap: anywhere; }
.mini {
  margin-left: 6px;
  border: 0;
  background: none;
  padding: 0;
  color: var(--muted);
  font: inherit;
  font-size: 12px;
  text-decoration: underline;
  cursor: pointer;
}
.warn-line {
  margin: 0;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  background: var(--warn-soft);
  border: 1px solid #ecdca8;
  color: #5c4300;
  font-size: 14px;
}
</style>
