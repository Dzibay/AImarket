<template>
  <div class="admin-page">
    <main>
      <div class="site-head">
        <h1>Aimarket</h1>
        <div class="links">
          <RouterLink to="/privacy">Политика</RouterLink>
          <RouterLink to="/consent">Согласие</RouterLink>
          <RouterLink to="/offer">Оферта</RouterLink>
          <button v-if="isLoggedIn" type="button" class="quiet sm logout" @click="logout">Выйти</button>
        </div>
      </div>

      <section v-if="authPhase === 'checking'" class="panel login-panel boot">
        <h2>Загрузка…</h2>
        <p class="muted">Проверяем сессию и подтягиваем данные.</p>
      </section>

      <section v-else-if="authPhase === 'guest'" class="panel login-panel">
        <h2>Вход</h2>
        <p v-if="bootError" class="error">{{ bootError }}</p>
        <label for="password">Пароль</label>
        <input
          id="password"
          v-model="password"
          type="password"
          autocomplete="current-password"
          :disabled="loggingIn"
          @keydown.enter="login"
        >
        <div class="row">
          <button type="button" :disabled="loggingIn || !password" @click="login">
            {{ loggingIn ? 'Входим…' : 'Войти' }}
          </button>
          <span v-if="loginError" class="error">{{ loginError }}</span>
        </div>
      </section>

      <div v-else>
        <nav class="tabs">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            type="button"
            :class="{ on: activeTab === tab.id }"
            @click="setTab(tab.id)"
          >
            {{ tab.label }}
          </button>
        </nav>

        <section v-show="activeTab === 'analytics'" class="panel">
          <div class="panel-head">
            <h2>Аналитика</h2>
            <div class="periods">
              <button
                v-for="opt in periodOptions"
                :key="opt.days"
                type="button"
                :class="{ on: period === opt.days }"
                @click="setPeriod(opt.days)"
              >
                {{ opt.label }}
              </button>
            </div>
          </div>

          <div v-for="group in kpiGroups" :key="group.title" class="kpi-group">
            <h3 class="kpi-title">{{ group.title }}</h3>
            <div class="cards">
              <div v-for="card in group.cards" :key="card.label" class="card">
                <span>{{ card.label }}</span>
                <b>{{ card.value }}</b>
              </div>
            </div>
          </div>

          <div class="charts">
            <AdminChart
              title="Приток пользователей"
              tone="users"
              :subtitle="usersChart.subtitle"
              :total-label="usersChart.totalLabel"
              :bars="usersChart.bars"
              :ticks="usersChart.ticks"
            />
            <AdminChart
              title="Выручка по дням"
              tone="revenue"
              :subtitle="revenueChart.subtitle"
              :total-label="revenueChart.totalLabel"
              :bars="revenueChart.bars"
              :ticks="revenueChart.ticks"
            />
            <AdminChart
              title="Расход клиентов"
              tone="spend"
              :subtitle="spendChart.subtitle"
              :total-label="spendChart.totalLabel"
              :bars="spendChart.bars"
              :ticks="spendChart.ticks"
            />
          </div>

          <div class="split block">
            <div>
              <h3>Модели</h3>
              <div class="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Модель</th>
                      <th class="num">Расход</th>
                      <th class="num">Запросы</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-if="!models.length" class="empty">
                      <td colspan="3">Пока пусто</td>
                    </tr>
                    <tr v-for="row in models" :key="row.model">
                      <td>{{ row.model }}</td>
                      <td class="num">{{ usd4(row.usd) }}</td>
                      <td class="num">{{ modelRequests(row) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            <div>
              <h3>Кто сколько потратил</h3>
              <div class="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Клиент</th>
                      <th class="num">Расход</th>
                      <th class="num">Запросы</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-if="!spenders.length" class="empty">
                      <td colspan="3">Пока пусто</td>
                    </tr>
                    <tr v-for="row in spenders" :key="row.name + row.usd">
                      <td>{{ row.name }}</td>
                      <td class="num">{{ usd4(row.usd) }}</td>
                      <td class="num">{{ row.requests }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          <div class="split block">
            <div>
              <h3>Кто сколько оплатил</h3>
              <div class="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Клиент</th>
                      <th class="num">Оплата</th>
                      <th class="num">Платежи</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-if="!payers.length" class="empty">
                      <td colspan="3">Пока пусто</td>
                    </tr>
                    <tr v-for="row in payers" :key="row.name + row.rub">
                      <td>{{ row.name }}</td>
                      <td class="num">{{ payerAmount(row) }}</td>
                      <td class="num">{{ row.payments }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            <div>
              <h3>Статусы платежей</h3>
              <div class="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Статус</th>
                      <th class="num">Штук</th>
                      <th class="num">Сумма</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-if="!paymentStatuses.length" class="empty">
                      <td colspan="3">Пока пусто</td>
                    </tr>
                    <tr v-for="row in paymentStatuses" :key="row.status">
                      <td>
                        <span class="badge" :class="statusBadgeClass(row.status)">{{ row.status }}</span>
                      </td>
                      <td class="num">{{ row.count }}</td>
                      <td class="num">{{ rub(row.rub) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          <div class="block">
            <h3>Последние запросы</h3>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Когда</th>
                    <th>Клиент</th>
                    <th>Модель</th>
                    <th class="num">Токены</th>
                    <th class="num">Расход</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="!recentRequests.length" class="empty">
                    <td colspan="5">Пока пусто</td>
                  </tr>
                  <tr v-for="(row, index) in recentRequests" :key="index">
                    <td>{{ formatRecentAt(row.at) }}</td>
                    <td>{{ row.name }}</td>
                    <td>{{ row.model }}</td>
                    <td class="num">{{ row.tokens }}</td>
                    <td class="num">{{ usd4(row.usd) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section v-show="activeTab === 'settings'" class="panel">
          <div class="panel-head">
            <h2>Настройки</h2>
            <div class="stat-line">Поставщик: <strong>{{ supplierDisplay }}</strong></div>
          </div>
          <div class="settings-grid">
            <div class="settings-block wide">
              <h3>Router.cheap</h3>
              <label for="root">Корневой API-ключ</label>
              <input
                id="root"
                v-model="rootKey"
                type="password"
                placeholder="Не менять — оставить пустым"
                autocomplete="off"
              >
              <p class="muted">{{ rootHint }}</p>
            </div>
            <div class="settings-block">
              <h3>Сайт</h3>
              <label for="base">Публичный адрес</label>
              <input id="base" v-model="settingsForm.public_base_url" placeholder="https://example.com">
            </div>
            <div class="settings-block">
              <h3>Цена</h3>
              <label for="price">₽ за $1 лимита</label>
              <input id="price" v-model="settingsForm.usd_price_rub" inputmode="decimal" placeholder="100">
              <label for="min-topup">Минимальное пополнение, $</label>
              <input id="min-topup" v-model="settingsForm.min_topup_usd" inputmode="decimal" placeholder="10">
            </div>
            <div class="settings-block wide">
              <h3>Бонусы к пополнению</h3>
              <p class="muted">
                Применяется самый высокий подходящий порог. Бонус зачисляется сверх оплаченной суммы
                и показывается на сайте и в боте до оплаты.
              </p>
              <div v-for="(tier, index) in bonusTiers" :key="index" class="bonus-row">
                <label>От, $</label>
                <input v-model="tier.min_usd" inputmode="decimal" placeholder="100">
                <label>Бонус, %</label>
                <input v-model="tier.percent" inputmode="decimal" placeholder="10">
                <button type="button" class="danger sm" @click="removeBonusTier(index)">Убрать</button>
              </div>
              <button type="button" class="quiet sm" @click="addBonusTier">Добавить порог</button>
            </div>
            <div class="settings-block">
              <h3>Почта</h3>
              <p class="muted">
                SMTP задаётся в <code>.env</code> в корне проекта, затем перезапустите backend:
                <code>docker compose up -d --build backend</code>.
                <span v-if="mailEnabled" class="badge ok">настроено</span>
                <span v-else class="badge warn">не настроено — письма не уходят</span>
              </p>
              <p v-if="!mailEnabled && mailMissing.length" class="muted small mail-hint">
                Не хватает: {{ mailMissing.join(', ') }}.
                Нужны как минимум <code>SMTP_HOST</code> и <code>SMTP_USER</code>
                (или <code>SMTP_FROM</code>, если совпадает с разрешённым отправителем).
              </p>
            </div>
            <div class="settings-block">
              <h3>Документы</h3>
              <label for="offer-date">Дата редакции</label>
              <input id="offer-date" v-model="settingsForm.offer_date" type="date">
              <label for="offer-email">Почта</label>
              <input id="offer-email" v-model="settingsForm.offer_email" type="email" placeholder="support@example.com">
            </div>
            <div class="settings-block">
              <h3>Поддержка</h3>
              <label for="support-username">Telegram</label>
              <input id="support-username" v-model="settingsForm.support_username" placeholder="support_username">
            </div>
          </div>
          <div class="row">
            <button type="button" @click="saveSettings">Сохранить</button>
            <span v-if="saveStatus" :class="saveStatusIsError ? 'error' : 'ok-text'">{{ saveStatus }}</span>
          </div>
        </section>

        <section v-show="activeTab === 'payments'" class="panel">
          <div class="panel-head"><h2>Платежи</h2></div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Когда</th>
                  <th>Клиент</th>
                  <th class="num">Сумма</th>
                  <th>Статус</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!topups.length" class="empty">
                  <td colspan="4">Пока пусто</td>
                </tr>
                <tr v-for="item in topups" :key="item.id">
                  <td class="nowrap">{{ formatRecentAt(item.created_at) }}</td>
                  <td>{{ person(item) }}</td>
                  <td class="num">{{ topupAmount(item) }}</td>
                  <td>
                    <span :class="['badge', statusBadgeClass(item.status)]">{{ item.status || '—' }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section v-show="activeTab === 'ledger'" class="panel">
          <div class="panel-head"><h2>Транзакции</h2></div>
          <div class="cards">
            <div
              v-for="card in ledgerCheckCards"
              :key="card.label"
              class="card"
              :class="{ bad: !card.ok }"
            >
              <span>{{ card.label }}</span>
              <b>{{ card.value }}</b>
            </div>
          </div>
          <div class="block">
            <h3>Новая запись</h3>
            <div class="ledger-form">
              <div class="field">
                <label for="ledger-user">Клиент</label>
                <select id="ledger-user" v-model="ledgerForm.user_id">
                  <option value="">Выберите клиента</option>
                  <option v-for="item in ledgerUserOptions" :key="item.id" :value="String(item.id)">
                    {{ person(item) }}
                  </option>
                </select>
              </div>
              <div class="field">
                <label for="ledger-kind">Тип</label>
                <select id="ledger-kind" v-model="ledgerForm.kind">
                  <option v-for="opt in ledgerKindOptions" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>
              </div>
              <div class="field">
                <label for="ledger-usd">Сумма $</label>
                <input id="ledger-usd" v-model="ledgerForm.amount_usd" inputmode="decimal" placeholder="10">
              </div>
              <div class="field">
                <label for="ledger-rub">Сумма ₽</label>
                <input id="ledger-rub" v-model="ledgerForm.amount_rub" inputmode="decimal" placeholder="0">
              </div>
              <div class="field">
                <label for="ledger-note">Пометка</label>
                <input id="ledger-note" v-model="ledgerForm.note" placeholder="Необязательно">
              </div>
              <button type="button" @click="addLedgerEntry">Добавить</button>
            </div>
            <p v-if="ledgerError" class="error">{{ ledgerError }}</p>
          </div>
          <div class="block">
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Когда</th>
                    <th>Клиент</th>
                    <th>Операция</th>
                    <th class="num">Сумма</th>
                    <th class="actions"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="!ledgerItems.length" class="empty">
                    <td colspan="5">Пока пусто</td>
                  </tr>
                  <tr v-for="item in ledgerItems" :key="item.id">
                    <td>{{ formatRecentAt(item.created_at) }}</td>
                    <td>{{ person(item) }}</td>
                    <td>{{ ledgerKindLabel(item.kind) }}{{ item.note ? ' · ' + item.note : '' }}</td>
                    <td class="num">{{ ledgerAmountText(item) }}</td>
                    <td class="actions">
                      <button type="button" class="danger sm" @click="deleteLedgerEntry(item.id)">Удалить</button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section v-show="activeTab === 'support'" class="panel">
          <div class="panel-head">
            <h2>Поддержка</h2>
            <label class="support-filter">
              <input
                v-model="supportFilterWaiting"
                type="checkbox"
                @change="loadSupportThreads"
              >
              Только ждут ответа
              <span v-if="supportWaiting" class="badge warn">{{ supportWaiting }}</span>
            </label>
          </div>
          <div class="support-layout">
            <div class="support-list">
              <button
                v-for="item in supportThreads"
                :key="item.thread_key"
                type="button"
                class="support-item"
                :class="{ on: supportActiveId === item.thread_key, waiting: item.waiting }"
                @click="openSupportThread(item.thread_key)"
              >
                <span class="support-item-top">
                  <b>{{ supportPerson(item) }}</b>
                  <span v-if="item.waiting" class="badge warn">{{ item.pending }}</span>
                </span>
                <span class="muted small">{{ supportPreview(item.last_body) }}</span>
                <span class="muted small">{{ formatRecentAt(item.last_at) }}</span>
              </button>
              <p v-if="!supportThreads.length" class="muted small empty-hint">Диалогов пока нет</p>
            </div>
            <div class="support-chat-pane">
              <template v-if="supportActiveId && supportUser">
                <div class="support-chat-head">
                  <div>
                    <strong>{{ supportPerson(supportUser) }}</strong>
                    <p class="muted small">
                      <template v-if="supportUser.kind === 'guest'">гость · </template>#{{ supportUser.id }}
                      <template v-if="supportUser.blocked"> · заблокирован</template>
                    </p>
                  </div>
                </div>
                <div class="admin-support-thread">
                  <p v-if="supportLoading && !supportMessages.length" class="muted small">Загрузка…</p>
                  <div
                    v-for="msg in supportMessages"
                    :key="msg.id"
                    class="support-bubble"
                    :class="msg.author === 'staff' ? 'staff' : 'user'"
                  >
                    <p>{{ msg.body }}</p>
                    <time>{{ formatRecentAt(msg.created_at) }}</time>
                  </div>
                </div>
                <form class="support-composer" @submit.prevent="sendSupportReply">
                  <textarea
                    v-model="supportDraft"
                    rows="3"
                    maxlength="4000"
                    placeholder="Ответ поддержки…"
                    :disabled="supportSending"
                    @keydown.enter.exact.prevent="sendSupportReply"
                  />
                  <div class="row">
                    <button type="submit" :disabled="supportSending || !supportDraft.trim()">
                      {{ supportSending ? 'Отправка…' : 'Ответить' }}
                    </button>
                    <span v-if="supportError" class="error">{{ supportError }}</span>
                  </div>
                </form>
              </template>
              <p v-else class="muted support-placeholder">Выберите диалог слева</p>
            </div>
          </div>
        </section>

        <section v-show="activeTab === 'users'" class="panel">
          <div class="panel-head"><h2>Пользователи</h2></div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Клиент</th>
                  <th class="num">Баланс</th>
                  <th>Ключ</th>
                  <th>Начислить</th>
                  <th>Доступ</th>
                  <th class="actions"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!users.length" class="empty">
                  <td colspan="6">Пока пусто</td>
                </tr>
                <tr v-for="item in users" :key="item.id">
                  <td>
                    <span>{{ person(item) }}</span>
                    <span v-if="!item.offer_accepted" class="badge warn">оферта</span>
                    <span v-if="item.blocked" class="badge bad">blocked</span>
                  </td>
                  <td class="num">{{ usd(item.balance_usd) }}</td>
                  <td>{{ item.key_prefix ? item.key_prefix + '…' : '—' }}</td>
                  <td class="compact">
                    <input v-model="userCredits[item.id]" placeholder="$">
                    <button type="button" class="sm" title="Начислить" @click="creditUser(item)">+</button>
                  </td>
                  <td>
                    <button
                      v-if="item.blocked"
                      type="button"
                      class="sm"
                      @click="unblockUser(item)"
                    >
                      Разблок.
                    </button>
                    <button
                      v-else
                      type="button"
                      class="danger sm"
                      @click="blockUser(item)"
                    >
                      Блок
                    </button>
                  </td>
                  <td class="actions">
                    <button type="button" class="danger sm" @click="deleteUser(item)">Удалить</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section v-show="activeTab === 'referrals'" class="panel tab-referrals">
          <div class="panel-head">
            <h2>Рефералы</h2>
            <button type="button" @click="openReferralModal">Создать токен</button>
          </div>
          <div class="inline-form referral-toolbar">
            <input
              v-model="groupName"
              placeholder="Название группы"
              maxlength="64"
              @keydown.enter="createReferralGroup"
            >
            <button type="button" class="quiet sm" @click="createReferralGroup">Создать группу</button>
            <span v-if="groupError" class="error">{{ groupError }}</span>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Токен / группа</th>
                  <th class="num">Переходы</th>
                  <th class="num">Оферта</th>
                  <th class="num">Оплат</th>
                  <th class="num">CR</th>
                  <th class="num">Сумма</th>
                  <th class="referral-copy"></th>
                  <th class="referral-created">Создан</th>
                  <th class="referral-group">Группа</th>
                  <th class="referral-delete"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="referralRows.length === 1 && referralRows[0].type === 'empty'" class="empty">
                  <td colspan="10">Пока нет групп и токенов</td>
                </tr>
                <template v-for="(row, index) in referralRows" :key="index">
                  <tr
                    v-if="row.type === 'group'"
                    class="referral-group-row"
                    @click="toggleReferralGroup(row.group.id)"
                  >
                    <td>
                      <span class="referral-name">
                        <span class="referral-toggle">{{ row.expanded ? '▾' : '▸' }}</span>
                        <span>{{ row.group.name }}</span>
                        <span class="referral-count">{{ row.count }}</span>
                      </span>
                    </td>
                    <td class="num">{{ row.stats.visits }}</td>
                    <td class="num">{{ row.stats.offers_accepted }}</td>
                    <td class="num">{{ row.stats.payments }}</td>
                    <td class="num">{{ conversion(row.stats.payment_conversion, row.stats.visits) }}</td>
                    <td class="num">{{ referralTopupText(row.stats) }}</td>
                    <td class="referral-copy"></td>
                    <td class="referral-created">{{ shortDate(row.group.created_at) }}</td>
                    <td class="referral-group"></td>
                    <td class="referral-delete">
                      <button
                        type="button"
                        class="danger sm"
                        @click.stop="deleteReferralGroup(row.group)"
                      >
                        Удалить
                      </button>
                    </td>
                  </tr>
                  <tr v-else-if="row.type === 'section'" class="referral-section-row">
                    <td>{{ row.title }}</td>
                    <td class="num">{{ row.stats.visits }}</td>
                    <td class="num">{{ row.stats.offers_accepted }}</td>
                    <td class="num">{{ row.stats.payments }}</td>
                    <td class="num">{{ conversion(row.stats.payment_conversion, row.stats.visits) }}</td>
                    <td class="num">{{ referralTopupText(row.stats) }}</td>
                    <td class="referral-copy"></td>
                    <td class="referral-created"></td>
                    <td class="referral-group"></td>
                    <td class="referral-delete"></td>
                  </tr>
                  <tr v-else-if="row.type === 'token'" class="referral-token-row">
                    <td>
                      <code>{{ row.item.token }}</code>
                      <span v-if="row.item.system" class="badge ok referral-system">сайт</span>
                    </td>
                    <td class="num">{{ row.item.visits || 0 }}</td>
                    <td class="num">{{ row.item.offers_accepted || 0 }}</td>
                    <td class="num">{{ row.item.payments || 0 }}</td>
                    <td class="num">{{ conversion(row.item.payment_conversion, row.item.visits) }}</td>
                    <td class="num">{{ referralTopupText(row.item) }}</td>
                    <td class="referral-copy">
                      <div class="referral-copy-actions">
                        <button
                          v-if="referralSiteUrl(row.item.token)"
                          type="button"
                          class="quiet sm icon-btn"
                          title="Скопировать ссылку на сайт"
                          aria-label="Скопировать ссылку на сайт"
                          @click.stop="copyReferralUrl(row.item, 'site')"
                        >
                          <svg v-if="!copiedReferralIds[`${row.item.id}:site`]" viewBox="0 0 24 24" aria-hidden="true">
                            <path fill="currentColor" d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm7.4 9h-3.1a15 15 0 0 0-1.3-5.2A8.05 8.05 0 0 1 19.4 11ZM12 4c.9 0 2.2 1.8 2.9 5H9.1C9.8 5.8 11.1 4 12 4ZM4.6 13h3.1c.2 1.9.7 3.7 1.3 5.2A8.05 8.05 0 0 1 4.6 13Zm3.1-2H4.6a8.05 8.05 0 0 1 4.4-5.2A15 15 0 0 0 7.7 11Zm1.4 2h5.8c-.3 1.8-.9 3.5-1.6 4.7-.4.7-.9 1.3-1.3 1.3s-.9-.6-1.3-1.3c-.7-1.2-1.3-2.9-1.6-4.7Zm5.8-2H9.1c.3-1.8.9-3.5 1.6-4.7.4-.7.9-1.3 1.3-1.3s.9.6 1.3 1.3c.7 1.2 1.3 2.9 1.6 4.7Zm.7 7.2c.6-1.5 1.1-3.3 1.3-5.2h3.1a8.05 8.05 0 0 1-4.4 5.2Z"/>
                          </svg>
                          <span v-else aria-hidden="true">✓</span>
                        </button>
                        <button
                          v-if="referralTelegramUrl(row.item.token)"
                          type="button"
                          class="quiet sm icon-btn"
                          title="Скопировать ссылку в Telegram"
                          aria-label="Скопировать ссылку в Telegram"
                          @click.stop="copyReferralUrl(row.item, 'tg')"
                        >
                          <svg v-if="!copiedReferralIds[`${row.item.id}:tg`]" viewBox="0 0 24 24" aria-hidden="true">
                            <path fill="currentColor" d="M21.7 4.3c.3-.9-.4-1.5-1.2-1.2L2.9 9.8c-.9.3-.9 1.1-.2 1.4l4.7 1.5 1.8 5.6c.2.7 1.1.9 1.6.4l2.6-2.5 4.9 3.6c.7.5 1.6.1 1.8-.7l2.8-14.8ZM8.9 12.7l8.5-5.3c.3-.2.7.2.4.5l-7 6.7-.3 3.1-1.6-5Z"/>
                          </svg>
                          <span v-else aria-hidden="true">✓</span>
                        </button>
                      </div>
                    </td>
                    <td class="referral-created">{{ shortDate(row.item.created_at) }}</td>
                    <td class="referral-group">
                      <select
                        :value="row.item.group_id ? String(row.item.group_id) : ''"
                        @change="updateReferralGroup(row.item, $event)"
                        @click.stop
                      >
                        <option value="">Без группы</option>
                        <option v-for="group in referralGroups" :key="group.id" :value="String(group.id)">
                          {{ group.name }}
                        </option>
                      </select>
                    </td>
                    <td class="referral-delete">
                      <button
                        v-if="!row.item.system"
                        type="button"
                        class="danger sm"
                        @click.stop="deleteReferral(row.item)"
                      >Удалить</button>
                      <span v-else class="muted small">системный</span>
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <div
        v-if="referralModalOpen"
        class="modal"
        aria-hidden="false"
      >
        <div class="modal-backdrop" @click="closeReferralModal" />
        <div class="modal-box">
          <h2>Новая ссылка</h2>
          <label for="referral-token">Токен</label>
          <input
            id="referral-token"
            v-model="referralToken"
            placeholder="partner_moscow"
            autocomplete="off"
            maxlength="64"
            @keydown.enter="createReferral"
          >
          <label for="referral-group">Группа</label>
          <select id="referral-group" v-model="referralGroupId">
            <option value="">Без группы</option>
            <option v-for="group in referralGroups" :key="group.id" :value="String(group.id)">
              {{ group.name }}
            </option>
          </select>
          <div class="row">
            <button type="button" @click="createReferral">Создать</button>
            <button type="button" class="quiet" @click="closeReferralModal">Отмена</button>
          </div>
          <p v-if="referralError" class="error">{{ referralError }}</p>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import AdminChart from '../components/AdminChart.vue'
import { useAdminPanel } from '../composables/useAdminPanel'
import { useHead } from '../utils/useHead'

const {
  authPhase,
  isLoggedIn,
  password,
  loginError,
  bootError,
  loggingIn,
  activeTab,
  period,
  tabs,
  periodOptions,
  settingsForm,
  bonusTiers,
  mailEnabled,
  mailMissing,
  addBonusTier,
  removeBonusTier,
  rootKey,
  rootHint,
  supplierDisplay,
  saveStatus,
  saveStatusIsError,
  kpiGroups,
  revenueChart,
  spendChart,
  usersChart,
  models,
  spenders,
  payers,
  paymentStatuses,
  recentRequests,
  ledgerCheckCards,
  ledgerItems,
  ledgerForm,
  ledgerError,
  ledgerUserOptions,
  ledgerKindOptions,
  topups,
  users,
  userCredits,
  supportThreads,
  supportWaiting,
  supportFilterWaiting,
  supportActiveId,
  supportUser,
  supportMessages,
  supportDraft,
  supportError,
  supportSending,
  supportLoading,
  loadSupportThreads,
  openSupportThread,
  sendSupportReply,
  supportPerson,
  supportPreview,
  referralGroups,
  referralRows,
  referralModalOpen,
  referralToken,
  referralGroupId,
  referralError,
  groupName,
  groupError,
  copiedReferralIds,
  login,
  logout,
  setTab,
  setPeriod,
  saveSettings,
  addLedgerEntry,
  deleteLedgerEntry,
  creditUser,
  unblockUser,
  blockUser,
  deleteUser,
  openReferralModal,
  closeReferralModal,
  createReferralGroup,
  createReferral,
  toggleReferralGroup,
  updateReferralGroup,
  deleteReferral,
  deleteReferralGroup,
  copyReferralUrl,
  referralTelegramUrl,
  referralSiteUrl,
  referralTopupText,
  ledgerKindLabel,
  ledgerAmountText,
  formatRecentAt,
  modelRequests,
  payerAmount,
  topupAmount,
  person,
  rub,
  usd,
  usd4,
  shortDate,
  conversion,
  statusBadgeClass,
} = useAdminPanel()

onMounted(() => {
  useHead('Админка — Aimarket', true)
})
</script>

<style scoped>
.admin-page {
  --bg: #f4f1ea;
  --surface: #fff;
  --surface-soft: #faf7f2;
  --border: #e4ddd2;
  --border-strong: #d9d0c3;
  --text: #1c1915;
  --muted: #6b645b;
  --accent: #1c1915;
  --danger: #8d2b2b;
  --danger-soft: #f8ecec;
  --ok: #2d6a4f;
  --ok-soft: #e8f3ed;
  --warn: #9a6700;
  --warn-soft: #faf3dd;
  --shadow: 0 10px 30px rgba(28, 25, 21, 0.06);
  --radius: 14px;
  --radius-sm: 10px;
  color-scheme: light;
  min-height: 100vh;
  background: var(--bg);
  color: var(--text);
  font: 15px/1.5 "Segoe UI", system-ui, sans-serif;
}
.admin-page *, .admin-page *::before, .admin-page *::after { box-sizing: border-box; }
.admin-page a { color: inherit; text-decoration: none; }
.admin-page a:hover { text-decoration: underline; }
.admin-page main { max-width: 1240px; margin: 0 auto; padding: 24px 20px 64px; }
.admin-page h1, .admin-page h2, .admin-page h3 { margin: 0; letter-spacing: -0.03em; }
.admin-page h1 { font-size: 28px; }
.admin-page h2 { font-size: 20px; }
.admin-page h3 { font-size: 15px; font-weight: 600; }
.admin-page .error { color: var(--danger); font-size: 13px; }
.admin-page .muted { color: var(--muted); font-size: 13px; }
.admin-page .ok-text { color: var(--ok); font-size: 13px; }
.admin-page code { font: 13px/1.45 ui-monospace, SFMono-Regular, Consolas, monospace; }

.admin-page .site-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.admin-page .site-head .links { display: flex; gap: 14px; align-items: center; flex-wrap: wrap; color: var(--muted); font-size: 13px; }
.admin-page .site-head .logout { margin-left: 4px; }
.admin-page .login-panel.boot { text-align: center; padding: 48px 24px; }
.admin-page .login-panel.boot h2 { margin-bottom: 8px; }

.admin-page .panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 22px 24px 24px;
}
.admin-page .panel + .panel, .admin-page .panel-head + .panel-body { margin-top: 16px; }
.admin-page .panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}
.admin-page .panel-head h2 { margin: 0; }

.admin-page .login-panel { max-width: 420px; margin: 12vh auto 0; }

.admin-page label {
  display: block;
  margin: 14px 0 6px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}
.admin-page label:first-child { margin-top: 0; }
.admin-page input, .admin-page select, .admin-page textarea {
  width: 100%;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  font: inherit;
  background: #fff;
  color: var(--text);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.admin-page input:focus, .admin-page select:focus, .admin-page textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(28, 25, 21, 0.08);
}
.admin-page textarea { min-height: 88px; resize: vertical; }

.admin-page button {
  appearance: none;
  border: 0;
  border-radius: var(--radius-sm);
  padding: 9px 14px;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  background: var(--accent);
  color: #fff;
  transition: transform 0.12s ease, opacity 0.12s ease, background 0.12s ease;
}
.admin-page button:hover { transform: translateY(-1px); }
.admin-page button:active { transform: translateY(0); }
.admin-page button:disabled { opacity: 0.45; cursor: not-allowed; transform: none; }
.admin-page button.quiet { background: var(--surface-soft); color: var(--text); border: 1px solid var(--border); }
.admin-page button.danger { background: var(--danger); }
.admin-page button.sm { padding: 6px 10px; font-size: 13px; border-radius: 8px; }

.admin-page .row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-top: 16px; }

.admin-page .tabs {
  display: flex;
  gap: 8px;
  flex-wrap: nowrap;
  overflow-x: auto;
  padding-bottom: 4px;
  margin-bottom: 18px;
  scrollbar-width: thin;
}
.admin-page .tabs button {
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
  white-space: nowrap;
  flex: 0 0 auto;
}
.admin-page .tabs button.on {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

.admin-page .periods { display: flex; gap: 8px; flex-wrap: wrap; }
.admin-page .periods button {
  background: var(--surface-soft);
  color: var(--text);
  border: 1px solid var(--border);
}
.admin-page .periods button.on { background: var(--accent); color: #fff; border-color: var(--accent); }

.admin-page .cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 12px;
}
.admin-page .card {
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 14px 16px;
  min-width: 0;
}
.admin-page .card span { display: block; color: var(--muted); font-size: 12px; margin-bottom: 6px; }
.admin-page .card b { display: block; font-size: 22px; letter-spacing: -0.03em; overflow-wrap: anywhere; }
.admin-page .card.bad { border-color: #e3b4b4; background: var(--danger-soft); }

.admin-page .block { margin-top: 24px; }
.admin-page .block:first-child { margin-top: 0; }
.admin-page .block > h2, .admin-page .block > h3 { margin-bottom: 12px; }

.admin-page .table-wrap {
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: #fff;
}
.admin-page table { width: 100%; border-collapse: collapse; min-width: 520px; }
.admin-page th, .admin-page td {
  text-align: left;
  padding: 11px 14px;
  border-bottom: 1px solid #eee6dc;
  vertical-align: middle;
}
.admin-page th {
  background: var(--surface-soft);
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.admin-page tbody tr:last-child td { border-bottom: 0; }
.admin-page tbody tr:hover td { background: rgba(250, 247, 242, 0.65); }
.admin-page td.num, .admin-page th.num { text-align: right; white-space: nowrap; }
.admin-page td.nowrap { white-space: nowrap; }
.admin-page td.actions, .admin-page th.actions { width: 1%; white-space: nowrap; }
.admin-page td.actions { display: flex; gap: 6px; justify-content: flex-end; flex-wrap: wrap; }
.admin-page .inline-form { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 14px; }
.admin-page .inline-form input, .admin-page .inline-form select { width: auto; min-width: 160px; flex: 1 1 160px; max-width: 280px; }
.admin-page .referral-toolbar { margin-bottom: 14px; }
.admin-page .tab-referrals td.referral-copy,
.admin-page .tab-referrals td.referral-delete,
.admin-page .tab-referrals td.referral-group { width: 1%; white-space: nowrap; text-align: center; vertical-align: middle; }
.admin-page .referral-copy-actions { display: inline-flex; gap: 4px; align-items: center; justify-content: center; }
.admin-page button.icon-btn {
  width: 30px;
  height: 30px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  line-height: 1;
}
.admin-page button.icon-btn svg { width: 15px; height: 15px; display: block; }
.admin-page button.icon-btn span { font-size: 13px; font-weight: 700; color: var(--accent); }
.admin-page .referral-system { margin-left: 8px; vertical-align: middle; }
.admin-page .tab-referrals td.referral-created { white-space: nowrap; vertical-align: middle; }
.admin-page .tab-referrals td.referral-group select { width: auto; min-width: 120px; max-width: 160px; padding: 6px 8px; font-size: 13px; }
.admin-page .tab-referrals td.num { white-space: nowrap; vertical-align: middle; }
.admin-page .tab-referrals td:first-child { vertical-align: middle; }
.admin-page tr.referral-group-row td { background: var(--surface-soft); font-weight: 600; cursor: pointer; }
.admin-page tr.referral-group-row:hover td { background: #f3eee6; }
.admin-page tr.referral-section-row td { background: #faf7f2; color: var(--muted); font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.admin-page tr.referral-token-row td:first-child { padding-left: 28px; }
.admin-page .referral-toggle { display: inline-block; width: 16px; margin-right: 8px; color: var(--muted); }
.admin-page .referral-name { display: inline-flex; align-items: center; gap: 8px; }
.admin-page .referral-count { font-size: 11px; font-weight: 600; color: var(--muted); background: #fff; border: 1px solid var(--border); border-radius: 999px; padding: 2px 8px; }
.admin-page td select { width: 100%; min-width: 120px; max-width: 200px; padding: 6px 8px; font-size: 13px; }
.admin-page td.compact input { width: 72px; margin-right: 8px; }
.admin-page td .badge { margin-left: 8px; }
.admin-page .empty td { text-align: center; color: var(--muted); padding: 28px 14px; }

.admin-page .badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  text-transform: lowercase;
  border: 1px solid transparent;
}
.admin-page .badge.ok { background: var(--ok-soft); color: var(--ok); border-color: #c7e3d4; }
.admin-page .badge.warn { background: var(--warn-soft); color: var(--warn); border-color: #ecdca8; }
.admin-page .badge.neutral { background: var(--surface-soft); color: var(--muted); border-color: var(--border); }
.admin-page .badge.bad { background: var(--danger-soft); color: var(--danger); border-color: #e3b4b4; }

.admin-page .settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}
.admin-page .settings-block {
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 16px 18px 18px;
}
.admin-page .settings-block.wide { grid-column: 1 / -1; }
.admin-page .bonus-row {
  display: grid;
  grid-template-columns: auto minmax(90px, 140px) auto minmax(90px, 140px) auto;
  gap: 8px 10px;
  align-items: center;
  margin-bottom: 10px;
}
.admin-page .bonus-row label { margin: 0; }
.admin-page .bonus-row input { width: 100%; }
.admin-page .mail-hint { margin-top: 8px; }
.admin-page .mail-hint code { font-size: 12px; background: var(--surface-soft); padding: 1px 5px; border-radius: 4px; }
@media (max-width: 640px) {
  .admin-page .bonus-row { grid-template-columns: 1fr 1fr; }
  .admin-page .bonus-row button { grid-column: 1 / -1; }
}
.admin-page .stat-line {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 999px;
  background: var(--surface-soft);
  border: 1px solid var(--border);
  font-size: 13px;
  color: var(--muted);
}
.admin-page .stat-line strong { color: var(--text); }

.admin-page .ledger-form {
  display: grid;
  grid-template-columns: minmax(180px, 1.4fr) repeat(4, minmax(110px, 1fr)) auto;
  gap: 10px;
  align-items: end;
}
.admin-page .ledger-form label { margin: 0 0 6px; }
.admin-page .ledger-form .field { min-width: 0; }
.admin-page .ledger-form button { height: 42px; }

.admin-page .kpi-group { margin-bottom: 18px; }
.admin-page .kpi-title {
  margin: 0 0 10px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.admin-page .charts {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
  margin: 8px 0 22px;
}
@media (min-width: 1100px) {
  .admin-page .charts { grid-template-columns: 1fr; }
}

.admin-page .chart-scroll { overflow-x: auto; margin-top: 4px; padding-bottom: 4px; }
.admin-page .chart, .admin-page .axis { display: flex; align-items: flex-end; gap: 4px; min-width: 100%; }
.admin-page .chart { height: 160px; padding-top: 8px; }
.admin-page .chart i {
  flex: 1 0 10px;
  background: linear-gradient(180deg, #3a342c 0%, var(--accent) 100%);
  border-radius: 6px 6px 0 0;
  min-height: 0;
  display: block;
}
.admin-page .chart i.empty { background: #e7e0d6; min-height: 4px; }
.admin-page .chart.alt i:not(.empty) { background: linear-gradient(180deg, #7a7267 0%, #5c564c 100%); }
.admin-page .axis { margin-top: 8px; }
.admin-page .axis b { flex: 1 0 10px; font-weight: 400; font-size: 11px; color: var(--muted); text-align: center; }

.admin-page .split { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }

.admin-page .support-filter {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  cursor: pointer;
}
.admin-page .support-layout {
  display: grid;
  grid-template-columns: minmax(220px, 0.9fr) minmax(0, 1.4fr);
  gap: 14px;
  min-height: 480px;
}
.admin-page .support-list {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  overflow: auto;
  max-height: 640px;
  background: var(--surface-soft);
}
.admin-page .support-item {
  width: 100%;
  display: grid;
  gap: 4px;
  padding: 12px;
  border: 0;
  border-radius: 0;
  border-bottom: 1px solid var(--border);
  background: transparent;
  color: var(--text);
  text-align: left;
  font: inherit;
  font-weight: 400;
  cursor: pointer;
  transform: none;
}
.admin-page .support-item:hover,
.admin-page .support-item:active {
  transform: none;
  background: #fff;
  color: var(--text);
}
.admin-page .support-item.on {
  background: #fff;
  color: var(--text);
  box-shadow: inset 3px 0 0 var(--accent);
}
.admin-page .support-item .muted { color: var(--muted); }
.admin-page .support-item-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.admin-page .support-item-top b {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.admin-page .empty-hint { padding: 18px 12px; margin: 0; }
.admin-page .support-chat-pane {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  min-height: 480px;
  background: #fff;
  overflow: hidden;
}
.admin-page .support-chat-head {
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  background: var(--surface-soft);
}
.admin-page .support-chat-head p { margin: 2px 0 0; }
.admin-page .admin-support-thread {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: var(--surface-soft);
}
.admin-page .support-bubble {
  max-width: 85%;
  padding: 8px 10px;
  border-radius: 12px;
  display: grid;
  gap: 3px;
}
.admin-page .support-bubble p {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 14px;
}
.admin-page .support-bubble time { font-size: 11px; color: var(--muted); }
.admin-page .support-bubble.user {
  align-self: flex-start;
  background: #fff;
  border: 1px solid var(--border);
}
.admin-page .support-bubble.staff {
  align-self: flex-end;
  background: var(--accent);
  color: #fff;
}
.admin-page .support-bubble.staff time { color: rgba(255, 255, 255, 0.7); }
.admin-page .support-composer {
  border-top: 1px solid var(--border);
  padding: 12px;
  display: grid;
  gap: 8px;
}
.admin-page .support-composer textarea {
  width: 100%;
  min-height: 72px;
  resize: vertical;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  font: inherit;
}
.admin-page .support-placeholder {
  margin: auto;
  padding: 24px;
  text-align: center;
}
@media (max-width: 900px) {
  .admin-page .support-layout { grid-template-columns: 1fr; }
  .admin-page .support-list { max-height: 240px; }
}

.admin-page .modal {
  position: fixed;
  inset: 0;
  z-index: 30;
  display: grid;
  place-items: center;
  padding: 18px;
}
.admin-page .modal-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(28, 25, 21, 0.45);
  backdrop-filter: blur(2px);
}
.admin-page .modal-box {
  position: relative;
  width: min(420px, 100%);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 22px 22px 20px;
  box-shadow: 0 24px 60px rgba(28, 25, 21, 0.18);
}
.admin-page .modal-box h2 { margin-bottom: 16px; }

@media (max-width: 960px) {
  .admin-page .settings-grid, .admin-page .split { grid-template-columns: 1fr; }
  .admin-page .ledger-form { grid-template-columns: 1fr 1fr; }
  .admin-page .ledger-form button { grid-column: 1 / -1; width: 100%; }
}
@media (max-width: 640px) {
  .admin-page main { padding: 16px 14px 48px; }
  .admin-page .panel { padding: 18px 16px; }
  .admin-page .ledger-form { grid-template-columns: 1fr; }
}
</style>
