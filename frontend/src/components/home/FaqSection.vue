<template>
  <section id="faq" class="faq container">
    <div class="faq-head">
      <p v-reveal class="kicker">FAQ</p>
      <h2 v-reveal="80" class="section-title">Частые<br>вопросы</h2>
      <p v-reveal="160" class="section-lead">
        Не нашли ответ? Напишите в чат справа внизу — отвечаем за несколько минут.
      </p>
    </div>

    <div class="faq-list">
      <div
        v-for="(item, i) in items"
        :key="item.q"
        v-reveal="i * 50"
        class="item"
        :class="{ open: open === i }"
      >
        <button
          :id="`faq-q-${i}`"
          type="button"
          class="q"
          :aria-expanded="open === i"
          :aria-controls="`faq-a-${i}`"
          @click="open = open === i ? -1 : i"
        >
          <span>{{ item.q }}</span>
          <i class="plus" aria-hidden="true"></i>
        </button>
        <div :id="`faq-a-${i}`" class="a" role="region" :aria-labelledby="`faq-q-${i}`">
          <div class="a-inner">
            <!-- eslint-disable-next-line vue/no-v-html -- статичный текст из этого файла -->
            <p v-html="item.a"></p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { rub } from '../../utils/format'

const props = defineProps({
  rate: { type: Number, default: 0 },
})

const open = ref(0)

const items = computed(() => [
  {
    q: 'Это официальный Claude или OpenAI?',
    a: 'Нет. Aimarket — сторонний API-провайдер. Мы даём вам собственный ключ, который работает через наш прокси-шлюз к тем же моделям Claude, GPT и Gemini. Вы получаете тот же результат, но платите рублями и через один ключ.',
  },
  {
    q: `Почему курс 1$ = ${rub(props.rate || 10, 0)} — это выгодно?`,
    a: 'Вы пополняете баланс в рублях, а списание идёт в долларах: 10% от официальной цены модели. Курс пополнения фиксирован сайтом и не зависит от курса ЦБ. Все тарифы — на странице <a href="/prices">«Цены»</a>.',
  },
  {
    q: 'Что я получу после регистрации и оплаты?',
    a: 'Три вещи: API-ключ, Base URL и доступ к личному кабинету. Ключ и адрес сервера появятся на экране и продублируются на почту. В кабинете — инструкции для Cursor, Claude Code и Codex, статистика расходов и история запросов.',
  },
  {
    q: 'Как подключить к Cursor?',
    a: 'Откройте настройки Cursor → Models → OpenAI API Key. Вставьте ваш ключ и укажите Base URL: <code>https://api.market-aii.ru</code>. Выберите модель — и работайте. Готовые инструкции для всех приложений — в личном кабинете.',
  },
  {
    q: 'Какие приложения поддерживаются?',
    a: 'Любые, где можно указать свой API-ключ и адрес сервера: Cursor, Claude Code, Codex, Claude Desktop, OpenCode, Hermes, Droid, Pi, Grok Build. Поддерживаются форматы OpenAI Chat Completions, Claude Messages и Google Gemini.',
  },
  {
    q: 'Безопасно ли это?',
    a: 'Ваш ключ хранится в зашифрованном виде. Мастер-ключи провайдеров не передаются и не логируются. Если ключ скомпрометирован — перевыпускаете в один клик.',
  },
  {
    q: 'Ключ не работает — что делать?',
    a: 'Проверьте, что вы указали правильный Base URL и что на балансе есть средства. Если не помогает — напишите в чат поддержки на сайте (кнопка справа внизу), ответим в течение дня.',
  },
  {
    q: 'Что если я потеряю ключ?',
    a: 'Если вы залогинены в кабинете — перевыпустите ключ там. Если нет — найдите письмо с кнопкой входа или напишите в поддержку, указав почту и сумму последней оплаты.',
  },
  {
    q: 'Можно ли вернуть деньги?',
    a: 'Возврат неиспользованного баланса — в течение 14 дней с момента оплаты, если баланс не был израсходован. Обращайтесь в поддержку через Telegram-бота. Деньги вернутся на ту же карту, которой оплачивали.',
  },
])
</script>

<style scoped>
.faq {
  display: grid;
  grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.4fr);
  gap: 64px;
  padding-top: 120px;
  padding-bottom: 80px;
  scroll-margin-top: 80px;
}
.faq-head { position: sticky; top: 110px; align-self: start; }
.faq-list { display: grid; gap: 10px; }
.item {
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.95);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.9) inset, 0 10px 30px -24px rgba(60, 40, 15, 0.4);
  transition: background 0.3s ease, box-shadow 0.3s ease;
}
.item.open { background: #fff; box-shadow: 0 1px 0 rgba(255, 255, 255, 0.9) inset, 0 24px 50px -30px rgba(60, 40, 15, 0.45); }
.q {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  width: 100%;
  padding: 20px 22px;
  border: 0;
  background: none;
  color: var(--text);
  font: inherit;
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.02em;
  text-align: left;
  cursor: pointer;
}
.plus {
  position: relative;
  flex: 0 0 auto;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(28, 25, 21, 0.06);
  transition: background 0.3s ease, transform 0.45s var(--ease-out);
}
.plus::before, .plus::after {
  content: "";
  position: absolute;
  left: 50%;
  top: 50%;
  width: 12px;
  height: 2px;
  margin: -1px 0 0 -6px;
  border-radius: 2px;
  background: currentColor;
}
.plus::after { transform: rotate(90deg); transition: transform 0.45s var(--ease-out); }
.open .plus { background: var(--ink); color: #fff; transform: rotate(180deg); }
.open .plus::after { transform: rotate(0deg); }
.a {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.45s var(--ease-out);
}
.open .a { grid-template-rows: 1fr; }
.a-inner { overflow: hidden; }
.a p {
  margin: 0;
  padding: 0 22px 22px;
  color: var(--muted-2);
  font-size: 15.5px;
  line-height: 1.6;
  max-width: 64ch;
  opacity: 0;
  transform: translateY(-6px);
  transition: opacity 0.3s ease, transform 0.45s var(--ease-out);
}
.open .a p { opacity: 1; transform: none; }
.a :deep(code) {
  padding: 2px 6px;
  border-radius: 6px;
  background: rgba(28, 25, 21, 0.06);
  font: 500 0.88em var(--font-mono);
}
.a :deep(a) { color: #c4572f; }

@media (max-width: 900px) {
  .faq { grid-template-columns: 1fr; gap: 32px; padding-top: 80px; }
  .faq-head { position: static; }
  .q { padding: 18px; font-size: 16px; }
  .a p { padding: 0 18px 18px; }
}
</style>
