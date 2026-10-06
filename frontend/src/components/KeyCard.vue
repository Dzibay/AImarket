<template>
  <section class="card key-card">
    <div class="key-head">
      <div class="key-title-wrap">
        <span class="key-icon"><AppIcon name="key" :size="18" /></span>
        <div>
          <h2 class="key-title">{{ title }}</h2>
          <p class="muted small key-sub">
            Один ключ — и вход в кабинет, и доступ к нейросетям. Никому его не передавайте.
          </p>
        </div>
      </div>
      <span v-if="highlight" class="badge warn">Сохраните прямо сейчас</span>
    </div>

    <div class="fields">
      <CopyField label="API-ключ" :value="secret" masked :reveal-by-default="revealByDefault" toast="Ключ скопирован" />
      <CopyField v-if="baseUrl" label="Base URL" :value="baseUrl" toast="Адрес скопирован" />
    </div>

    <div class="roles">
      <div class="role">
        <AppIcon name="lock" :size="16" />
        <div>
          <b>Пароль от кабинета</b>
          <span>Логина нет — на странице <RouterLink to="/login">входа</RouterLink> вставьте этот ключ.</span>
        </div>
      </div>
      <div class="role">
        <AppIcon name="plug" :size="16" />
        <div>
          <b>Ключ для приложений</b>
          <span>В Cursor, Codex, Claude Code — как <code>API key</code>, адрес сервера — <code>Base URL</code>.</span>
        </div>
      </div>
      <div class="role">
        <AppIcon name="shield" :size="16" />
        <div>
          <b>Храните надёжно</b>
          <span>Менеджер паролей или заметки. Потеряете — доступ только через поддержку.</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import AppIcon from './ui/AppIcon.vue'
import CopyField from './ui/CopyField.vue'

defineProps({
  secret: { type: String, required: true },
  baseUrl: { type: String, default: '' },
  title: { type: String, default: 'Ваш ключ доступа' },
  highlight: { type: Boolean, default: false },
  revealByDefault: { type: Boolean, default: false },
})
</script>

<style scoped>
.key-card { padding: 22px 24px 20px; }
.key-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.key-title-wrap { display: flex; gap: 12px; align-items: flex-start; }
.key-icon {
  flex: 0 0 38px;
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: var(--accent);
  color: var(--bg);
}
.key-title { margin: 0 0 2px; font-size: 1.2rem; letter-spacing: -0.03em; }
.key-sub { margin: 0; }
.fields {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
  gap: 10px;
}
.roles {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}
.role { display: flex; gap: 10px; align-items: flex-start; color: var(--muted-2); font-size: 13px; line-height: 1.45; }
.role .icon { margin-top: 2px; color: var(--muted); }
.role b { display: block; color: var(--text); font-size: 13.5px; margin-bottom: 2px; }
.role a { text-decoration: underline; text-underline-offset: 3px; }
.role code { font-size: 12px; background: var(--surface-soft); border: 1px solid var(--border); padding: 0 5px; border-radius: 5px; }
@media (max-width: 760px) {
  .fields, .roles { grid-template-columns: 1fr; }
}
</style>
