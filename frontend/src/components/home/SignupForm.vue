<template>
  <div class="signup" :class="[`size-${size}`, { sent }]">
    <Transition name="swap" mode="out-in">
      <form v-if="!sent" key="form" class="signup-form" @submit.prevent="submit">
        <label class="sr-only" :for="inputId">Электронная почта</label>
        <span class="mail-icon" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="3" /><path d="m4 7 8 6 8-6" /></svg>
        </span>
        <input
          :id="inputId"
          v-model="email"
          type="email"
          autocomplete="email"
          inputmode="email"
          placeholder="Ваша почта"
          required
        >
        <button type="submit" class="go" :disabled="busy">
          <span>{{ busy ? 'Отправляем…' : cta }}</span>
          <svg v-if="!busy" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14" /><path d="m13 6 6 6-6 6" /></svg>
        </button>
      </form>
      <div v-else key="sent" class="signup-done" role="status">
        <span class="done-icon" aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12 5 5 9-10" /></svg>
        </span>
        <div>
          <b>Аккаунт создан — проверьте почту</b>
          <span>Ссылка для входа отправлена на {{ sentTo }}. Письмо может попасть в «Спам».</span>
        </div>
      </div>
    </Transition>
    <p v-if="error" class="signup-error">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { errorText, webApi } from '../../api/web'
import { reachMetrikaGoal } from '../../utils/cookiesConsent'
import { getReferralToken } from '../../utils/referral'

const props = defineProps({
  size: { type: String, default: 'lg' },
  cta: { type: String, default: 'Получить доступ' },
  source: { type: String, default: 'hero' },
})

const inputId = `signup-${props.source}`
const email = ref('')
const busy = ref(false)
const sent = ref(false)
const sentTo = ref('')
const error = ref('')

async function submit() {
  const value = email.value.trim().toLowerCase()
  if (busy.value) return
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value)) {
    error.value = 'Введите корректную почту.'
    return
  }
  busy.value = true
  error.value = ''
  try {
    await webApi.loginByEmail(value, getReferralToken())
    reachMetrikaGoal('signup', { source: props.source })
    sentTo.value = value
    sent.value = true
  } catch (err) {
    error.value = errorText(err)
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.signup { width: 100%; max-width: 540px; margin: 0 auto; }
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}
.signup-form {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 7px 7px 18px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.95);
  box-shadow: var(--shadow-lg);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  transition: box-shadow 0.3s ease, transform 0.3s var(--ease-out);
}
/* Переливающаяся рамка при фокусе. */
.signup-form::before {
  content: "";
  position: absolute;
  inset: -2px;
  z-index: -1;
  border-radius: inherit;
  background: var(--grad);
  opacity: 0;
  filter: blur(10px);
  transition: opacity 0.35s ease;
}
.signup-form:focus-within::before { opacity: 0.55; }
.signup-form:focus-within { transform: translateY(-1px); }
.mail-icon { flex: 0 0 auto; display: grid; color: var(--muted); }
input {
  flex: 1 1 auto;
  min-width: 0;
  height: 48px;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--text);
  font: inherit;
  font-size: 16px;
}
input::placeholder { color: #9a9187; }
.go {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 52px;
  padding: 0 24px;
  border: 0;
  border-radius: 999px;
  background: linear-gradient(180deg, #2b2620 0%, var(--ink) 100%);
  color: #fff;
  font: inherit;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.18), 0 10px 24px -8px rgba(21, 18, 14, 0.55);
  transition: transform 0.2s var(--ease-out), box-shadow 0.2s ease;
}
.go:hover { transform: translateX(2px); }
.go:hover svg { transform: translateX(3px); }
.go svg { transition: transform 0.25s var(--ease-out); }
.go:disabled { opacity: 0.7; cursor: progress; }

.size-md .signup-form { padding: 5px 5px 5px 16px; }
.size-md input { height: 44px; font-size: 15px; }
.size-md .go { height: 46px; padding: 0 20px; }

.signup-done {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 20px 14px 14px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid #c7e3d4;
  box-shadow: var(--shadow-lg);
  text-align: left;
}
.done-icon {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3f9b6f, #2d6a4f);
  color: #fff;
  box-shadow: 0 8px 20px -6px rgba(45, 106, 79, 0.6);
}
.signup-done b { display: block; font-size: 15px; letter-spacing: -0.01em; }
.signup-done span { display: block; color: var(--muted-2); font-size: 13.5px; line-height: 1.4; overflow-wrap: anywhere; }
.signup-error { margin: 10px 0 0; color: var(--danger); font-size: 14px; text-align: center; }

.swap-enter-active, .swap-leave-active { transition: opacity 0.3s ease, transform 0.4s var(--ease-out); }
.swap-enter-from { opacity: 0; transform: translateY(8px) scale(0.98); }
.swap-leave-to { opacity: 0; transform: translateY(-6px) scale(0.98); }

@media (max-width: 520px) {
  .signup-form { flex-wrap: wrap; padding: 8px; border-radius: 26px; }
  .mail-icon { display: none; }
  input { flex-basis: 100%; height: 48px; padding: 0 12px; }
  .go { width: 100%; justify-content: center; border-radius: 20px; }
  .go:hover { transform: none; }
}
</style>
