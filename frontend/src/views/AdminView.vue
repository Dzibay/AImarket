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
              <label for="price">Курс для клиентов, ₽/$</label>
              <input id="price" v-model="settingsForm.usd_price_rub" inputmode="decimal" placeholder="100">
              <label for="supplier-price">Курс поставщика, ₽/$</label>
              <input
                id="supplier-price"
                v-model="settingsForm.supplier_usd_price_rub"
                inputmode="decimal"
                placeholder="как у клиентов"
              >
              <p class="muted small">Если пусто — для финансов берётся клиентский курс.</p>
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
              <label for="support-username">Telegram (публичный контакт)</label>
              <input id="support-username" v-model="settingsForm.support_username" placeholder="support_username">
              <label for="support-chat-id">ID группы с темами (чат поддержки)</label>
              <input
                id="support-chat-id"
                v-model="settingsForm.support_telegram_chat_id"
                inputmode="numeric"
                placeholder="-1001234567890"
              >
              <p class="muted small">
                Супергруппа с включёнными Topics. Добавьте туда бота как админа.
                Сообщения с сайта создают темы; ответы в теме уходят пользователю на сайте.
              </p>
            </div>
          </div>
          <div class="row">
            <button type="button" @click="saveSettings">Сохранить</button>
            <span v-if="saveStatus" :class="saveStatusIsError ? 'error' : 'ok-text'">{{ saveStatus }}</span>
          </div>
        </section>

        <section v-show="activeTab === 'finance'" class="panel tab-finance">
          <div class="panel-head finance-head">
            <div>
              <h2>Финансы</h2>
              <p class="muted finance-sub">Счета, расходы, выводы и доступная сумма</p>
            </div>
            <button type="button" class="quiet sm" :disabled="financeSaving" @click="loadFinance">Обновить</button>
          </div>

          <div
            v-if="financeSummary?.supplier_needs_topup"
            class="finance-alert"
          >
            Нужно пополнить баланс поставщика на
            <b>{{ usd(financeSummary.supplier_shortfall_usd) }}</b>
            <span class="muted">
              (≈ {{ rub(financeSummary.supplier_shortfall_rub) }} по курсу поставщика
              {{ Number(financeSummary.supplier_rate || 0).toFixed(2) }} ₽/$).
              Обязательства клиентам {{ usd(financeSummary.customer_liability_usd) }},
              у поставщика {{ usd(financeSummary.supplier_balance_usd) }}.
            </span>
          </div>

          <div v-if="financeSummary" class="finance-kpis">
            <div class="finance-kpi emphasis" :class="financeSummary.available_rub >= 0 ? 'ok' : 'bad'">
              <span>Доступно к выводу</span>
              <b>{{ rub(financeSummary.available_rub) }}</b>
              <small>касса − обязательства клиентам</small>
            </div>
            <div class="finance-kpi">
              <span>Касса по счетам</span>
              <b>{{ rub(financeSummary.cash_rub) }}</b>
            </div>
            <div class="finance-kpi">
              <span>Обязательства клиентам</span>
              <b>{{ usd(financeSummary.customer_liability_usd) }}</b>
              <small>{{ rub(financeSummary.customer_liability_rub) }} · курс клиентов</small>
            </div>
            <div class="finance-kpi" :class="{ bad: financeSummary.supplier_needs_topup }">
              <span>Поставщик</span>
              <b>{{ usd(financeSummary.supplier_balance_usd) }}</b>
              <small>курс {{ Number(financeSummary.supplier_rate || 0).toFixed(2) }} ₽/$</small>
            </div>
            <div class="finance-kpi">
              <span>Расходы</span>
              <b>{{ rub(financeSummary.expenses_total_rub) }}</b>
            </div>
            <div class="finance-kpi">
              <span>Выводы</span>
              <b>{{ rub(financeSummary.withdrawals_total_rub) }}</b>
            </div>
          </div>

          <div class="finance-filters">
            <button type="button" class="quiet sm" :class="{ on: financeSection === 'expenses' }" @click="financeSection = 'expenses'">Расходы</button>
            <button type="button" class="quiet sm" :class="{ on: financeSection === 'withdrawals' }" @click="financeSection = 'withdrawals'">Выводы</button>
            <button type="button" class="quiet sm" :class="{ on: financeSection === 'accounts' }" @click="financeSection = 'accounts'">Счета</button>
            <button type="button" class="quiet sm" :class="{ on: financeSection === 'categories' }" @click="financeSection = 'categories'">Категории</button>
            <button type="button" class="quiet sm" :class="{ on: financeSection === 'operations' }" @click="financeSection = 'operations'">Операции</button>
          </div>
          <p v-if="financeError" class="error">{{ financeError }}</p>

          <div v-show="financeSection === 'expenses'" class="finance-card wide">
            <div class="finance-card-head">
              <h3>Расходы</h3>
              <button type="button" class="sm" :disabled="financeSaving" @click="openFinanceModal('expense')">
                <AppIcon name="plus" :size="14" />
                Добавить
              </button>
            </div>
            <div class="table-wrap">
              <table class="finance-table">
                <thead>
                  <tr>
                    <th>Дата</th>
                    <th>Счёт</th>
                    <th>Категория</th>
                    <th>Комментарий</th>
                    <th class="num">Сумма</th>
                    <th class="actions"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="!financeExpenses.length" class="empty"><td colspan="6">Пока нет расходов</td></tr>
                  <tr v-for="item in financeExpenses" :key="item.id">
                    <td class="nowrap muted">{{ financeDateOnly(item.occurred_at) }}</td>
                    <td>{{ item.account_name }}</td>
                    <td>
                      <span
                        v-if="item.category_name"
                        class="cat-chip"
                        :style="{ background: item.category_color || '#eee' }"
                      >{{ item.category_name }}</span>
                      <span v-else class="muted">—</span>
                    </td>
                    <td class="finance-note-cell">{{ item.note || '—' }}</td>
                    <td class="num">{{ rub(item.amount_rub) }}</td>
                    <td class="actions">
                      <button type="button" class="quiet sm" @click="startEditExpense(item)">Изм.</button>
                      <button type="button" class="icon-btn danger-ghost" title="Удалить" @click="deleteFinanceOperation(item.id, 'расход')">
                        <AppIcon name="trash" :size="15" />
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div v-show="financeSection === 'withdrawals'" class="finance-card wide">
            <div class="finance-card-head">
              <h3>Выводы</h3>
              <button type="button" class="sm" :disabled="financeSaving" @click="openFinanceModal('withdrawal')">
                <AppIcon name="plus" :size="14" />
                Добавить
              </button>
            </div>
            <div class="table-wrap">
              <table class="finance-table">
                <thead>
                  <tr><th>Дата</th><th>Счёт</th><th>Категория</th><th>Комментарий</th><th class="num">Сумма</th><th class="actions"></th></tr>
                </thead>
                <tbody>
                  <tr v-if="!financeWithdrawals.length" class="empty"><td colspan="6">Пока нет выводов</td></tr>
                  <tr v-for="item in financeWithdrawals" :key="item.id">
                    <td class="nowrap muted">{{ financeDateOnly(item.occurred_at) }}</td>
                    <td>{{ item.account_name }}</td>
                    <td>
                      <span v-if="item.category_name" class="cat-chip" :style="{ background: item.category_color || '#eee' }">{{ item.category_name }}</span>
                      <span v-else class="muted">—</span>
                    </td>
                    <td class="finance-note-cell">{{ item.note || '—' }}</td>
                    <td class="num">{{ rub(item.amount_rub) }}</td>
                    <td class="actions">
                      <button type="button" class="icon-btn danger-ghost" @click="deleteFinanceOperation(item.id, 'вывод')">
                        <AppIcon name="trash" :size="15" />
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div v-show="financeSection === 'accounts'" class="finance-card wide">
            <div class="finance-card-head">
              <h3>Счета</h3>
              <div class="finance-card-actions">
                <button type="button" class="quiet sm" :disabled="financeSaving || !financeAccounts.length" @click="openFinanceModal('deposit')">Пополнить</button>
                <button type="button" class="quiet sm" :disabled="financeSaving || financeAccounts.length < 2" @click="openFinanceModal('transfer')">Перевод</button>
                <button type="button" class="sm" :disabled="financeSaving" @click="openFinanceModal('account')">
                  <AppIcon name="plus" :size="14" />
                  Счёт
                </button>
              </div>
            </div>
            <p class="muted small">Для счёта ЮKassa при создании подтянутся все прошлые оплаты.</p>
            <div class="table-wrap" style="margin-top:12px">
              <table class="finance-table">
                <thead>
                  <tr><th>Счёт</th><th>Провайдер</th><th class="num">Баланс</th><th></th><th class="actions"></th></tr>
                </thead>
                <tbody>
                  <tr v-if="!financeAccounts.length" class="empty"><td colspan="5">Создайте хотя бы один счёт</td></tr>
                  <tr v-for="a in financeAccounts" :key="a.id">
                    <td>
                      <b>{{ a.name }}</b>
                      <span v-if="a.is_default" class="badge ok">дефолт</span>
                    </td>
                    <td>{{ a.provider_label || '—' }}</td>
                    <td class="num">{{ rub(a.balance_rub) }}</td>
                    <td>
                      <button v-if="!a.is_default" type="button" class="quiet sm" @click="setDefaultFinanceAccount(a)">Сделать дефолтным</button>
                    </td>
                    <td class="actions">
                      <button type="button" class="icon-btn danger-ghost" @click="deleteFinanceAccount(a)">
                        <AppIcon name="trash" :size="15" />
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div v-show="financeSection === 'categories'" class="finance-card wide">
            <div class="finance-card-head">
              <h3>Категории</h3>
              <button type="button" class="sm" :disabled="financeSaving" @click="openFinanceModal('category')">
                <AppIcon name="plus" :size="14" />
                Добавить
              </button>
            </div>
            <div class="table-wrap">
              <table class="finance-table">
                <thead>
                  <tr><th>Тип</th><th>Название</th><th>Цвет</th><th class="actions"></th></tr>
                </thead>
                <tbody>
                  <tr v-for="c in (financeSummary?.categories || [])" :key="c.id">
                    <td>{{ c.kind === 'expense' ? 'Расход' : 'Вывод' }}</td>
                    <td><input v-model="c.name" @change="saveFinanceCategory(c)"></td>
                    <td><input v-model="c.color" type="color" @change="saveFinanceCategory(c)"></td>
                    <td class="actions">
                      <button type="button" class="icon-btn danger-ghost" @click="archiveFinanceCategory(c)">
                        <AppIcon name="trash" :size="15" />
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div v-show="financeSection === 'operations'" class="finance-card wide">
            <h3>Все операции</h3>
            <div class="table-wrap">
              <table class="finance-table">
                <thead>
                  <tr><th>Дата</th><th>Тип</th><th>Счёт</th><th>Категория / куда</th><th>Комментарий</th><th class="num">Сумма</th></tr>
                </thead>
                <tbody>
                  <tr v-if="!financeOperations.length" class="empty"><td colspan="6">Пока пусто</td></tr>
                  <tr v-for="item in financeOperations" :key="item.id">
                    <td class="nowrap muted">{{ financeDateOnly(item.occurred_at) }}</td>
                    <td><span class="kind-badge" :class="financeKindClass(item.kind)">{{ item.kind_label }}</span></td>
                    <td>{{ item.account_name }}</td>
                    <td>
                      <span v-if="item.kind === 'transfer'">→ {{ item.counterparty_name }}</span>
                      <span v-else-if="item.category_name" class="cat-chip" :style="{ background: item.category_color || '#eee' }">{{ item.category_name }}</span>
                      <span v-else class="muted">—</span>
                    </td>
                    <td class="finance-note-cell">{{ item.note || '—' }}</td>
                    <td class="num">{{ rub(item.amount_rub) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
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

        <section v-show="activeTab === 'ledger'" class="panel tab-ledger">
          <div class="panel-head ledger-head">
            <div>
              <h2>Транзакции</h2>
              <p class="muted ledger-sub">История операций и сверка платежей</p>
            </div>
            <span class="stat-line">Всего: <strong>{{ ledgerItems.length }}</strong></span>
          </div>

          <div class="ledger-checks">
            <div
              v-for="card in ledgerCheckCards"
              :key="card.label"
              class="ledger-check"
              :class="card.tone || (card.ok ? 'neutral' : 'bad')"
            >
              <span class="ledger-check-label">{{ card.label }}</span>
              <b class="ledger-check-value">{{ card.value }}</b>
              <small v-if="card.hint" class="ledger-check-hint">{{ card.hint }}</small>
            </div>
          </div>

          <div class="ledger-list">
            <div class="ledger-list-head">
              <h3>Список транзакций</h3>
              <div class="ledger-list-tools">
                <label class="ledger-search">
                  <AppIcon name="search" :size="15" />
                  <input
                    v-model="ledgerSearch"
                    type="search"
                    placeholder="Поиск по клиенту или операции…"
                  >
                </label>
                <button type="button" class="sm" @click="openLedgerModal">
                  <AppIcon name="plus" :size="14" />
                  Добавить
                </button>
              </div>
            </div>
            <div class="table-wrap ledger-table-wrap">
              <table class="ledger-table">
                <thead>
                  <tr>
                    <th>Дата</th>
                    <th>Клиент</th>
                    <th>Операция</th>
                    <th class="num">Сумма</th>
                    <th class="actions" aria-label="Действия"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="!filteredLedgerItems.length" class="empty">
                    <td colspan="5">{{ ledgerItems.length ? 'Ничего не найдено' : 'Пока пусто' }}</td>
                  </tr>
                  <tr v-for="item in filteredLedgerItems" :key="item.id">
                    <td class="nowrap muted ledger-when">{{ financeDateOnly(item.created_at) }}</td>
                    <td>
                      <div class="user-cell compact">
                        <span
                          class="user-channel"
                          :class="item.telegram_id ? 'tg' : 'web'"
                          :title="item.telegram_id ? 'Telegram' : 'Сайт'"
                        >
                          <AppIcon :name="item.telegram_id ? 'telegram' : 'mail'" :size="13" />
                        </span>
                        <span class="user-name">{{ person(item) }}</span>
                      </div>
                    </td>
                    <td>
                      <div class="ledger-op">
                        <span class="kind-badge" :class="ledgerKindClass(item.kind)">
                          {{ ledgerKindLabel(item.kind) }}
                        </span>
                        <span v-if="ledgerNoteText(item)" class="ledger-note" :title="ledgerNoteText(item)">
                          {{ ledgerNoteText(item) }}
                        </span>
                      </div>
                    </td>
                    <td class="num">
                      <div class="ledger-amt" :class="ledgerAmountClass(item)">
                        <span class="ledger-usd">{{ ledgerAmountUsd(item) }}</span>
                        <span v-if="ledgerAmountRub(item)" class="ledger-rub">{{ ledgerAmountRub(item) }}</span>
                      </div>
                    </td>
                    <td class="actions">
                      <button
                        type="button"
                        class="icon-btn danger-ghost"
                        title="Удалить"
                        aria-label="Удалить"
                        @click="deleteLedgerEntry(item.id)"
                      >
                        <AppIcon name="trash" :size="15" />
                      </button>
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

        <section v-show="activeTab === 'users'" class="panel tab-users">
          <div class="panel-head users-head">
            <div>
              <h2>Пользователи</h2>
              <p class="muted users-sub">Клиенты Telegram и сайта</p>
            </div>
            <div class="users-toolbar">
              <label class="users-search">
                <AppIcon name="search" :size="15" />
                <input
                  v-model="usersSearch"
                  type="search"
                  placeholder="Поиск по клиенту, email или ID…"
                >
              </label>
              <span class="stat-line">Всего: <strong>{{ users.length }}</strong></span>
            </div>
          </div>
          <div class="table-wrap users-table-wrap">
            <table class="users-table">
              <thead>
                <tr>
                  <th>Клиент</th>
                  <th class="num">Баланс</th>
                  <th>Ключ</th>
                  <th>Баланс ±</th>
                  <th>Доступ</th>
                  <th class="actions" aria-label="Действия"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!filteredUsers.length" class="empty">
                  <td colspan="6">{{ users.length ? 'Ничего не найдено' : 'Пока пусто' }}</td>
                </tr>
                <tr
                  v-for="item in filteredUsers"
                  :key="item.id"
                  :class="{ paid: item.has_paid, blocked: item.blocked }"
                >
                  <td>
                    <div class="user-cell">
                      <span
                        class="user-channel"
                        :class="item.channel === 'telegram' ? 'tg' : 'web'"
                        :title="item.channel === 'telegram' ? 'Telegram' : 'Сайт'"
                      >
                        <AppIcon :name="item.channel === 'telegram' ? 'telegram' : 'mail'" :size="14" />
                      </span>
                      <div class="user-meta">
                        <span class="user-name">{{ person(item) }}</span>
                        <span class="user-badges">
                          <span v-if="item.has_paid" class="badge ok">оплата</span>
                          <span v-if="!item.offer_accepted" class="badge warn">оферта</span>
                          <span v-if="item.blocked" class="badge bad">блок</span>
                        </span>
                      </div>
                    </div>
                  </td>
                  <td class="num balance">{{ usd(item.balance_usd) }}</td>
                  <td class="key-cell">
                    <code v-if="item.key_prefix">{{ item.key_prefix }}…</code>
                    <span v-else class="muted">—</span>
                  </td>
                  <td class="compact">
                    <button
                      type="button"
                      class="quiet sm credit-open"
                      :class="{ busy: userCreditBusy[item.id] }"
                      :disabled="!!userCreditBusy[item.id]"
                      :title="userCreditBusy[item.id] ? 'Сохраняем…' : 'Начислить / списать'"
                      @click="openCreditModal(item)"
                    >
                      <span v-if="userCreditBusy[item.id]" class="credit-spinner" aria-hidden="true" />
                      <template v-else>
                        <AppIcon name="plus" :size="13" />
                        ±$
                      </template>
                    </button>
                  </td>
                  <td>
                    <div class="access-cell">
                      <span class="access-status" :class="item.blocked ? 'off' : 'on'">
                        {{ item.blocked ? 'Заблок.' : 'Активен' }}
                      </span>
                      <button
                        v-if="item.blocked"
                        type="button"
                        class="quiet sm"
                        @click="unblockUser(item)"
                      >
                        Разблок.
                      </button>
                      <button
                        v-else
                        type="button"
                        class="quiet sm access-block"
                        @click="blockUser(item)"
                      >
                        Блок
                      </button>
                    </div>
                  </td>
                  <td class="actions">
                    <button
                      type="button"
                      class="icon-btn danger-ghost"
                      title="Удалить"
                      aria-label="Удалить"
                      @click="deleteUser(item)"
                    >
                      <AppIcon name="trash" :size="15" />
                    </button>
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

      <div v-if="ledgerModalOpen" class="modal" aria-hidden="false">
        <div class="modal-backdrop" @click="closeLedgerModal" />
        <div class="modal-box modal-wide">
          <h2>Новая запись</h2>
          <label for="ledger-user">Клиент</label>
          <select id="ledger-user" v-model="ledgerForm.user_id">
            <option value="">Выберите клиента</option>
            <option v-for="item in ledgerUserOptions" :key="item.id" :value="String(item.id)">
              {{ person(item) }}
            </option>
          </select>
          <label for="ledger-kind">Тип</label>
          <select id="ledger-kind" v-model="ledgerForm.kind">
            <option v-for="opt in ledgerKindOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
          <div class="modal-grid">
            <div>
              <label for="ledger-usd">Сумма $</label>
              <input id="ledger-usd" v-model="ledgerForm.amount_usd" inputmode="decimal" placeholder="10">
            </div>
            <div>
              <label for="ledger-rub">Сумма ₽</label>
              <input id="ledger-rub" v-model="ledgerForm.amount_rub" inputmode="decimal" placeholder="0">
            </div>
          </div>
          <label for="ledger-date">Дата</label>
          <input id="ledger-date" v-model="ledgerForm.occurred_at" type="date">
          <label for="ledger-note">Пометка</label>
          <input id="ledger-note" v-model="ledgerForm.note" placeholder="Необязательно">
          <div class="row">
            <button type="button" @click="addLedgerEntry">Добавить</button>
            <button type="button" class="quiet" @click="closeLedgerModal">Отмена</button>
          </div>
          <p v-if="ledgerError" class="error">{{ ledgerError }}</p>
        </div>
      </div>

      <div v-if="creditModal.open" class="modal" aria-hidden="false">
        <div class="modal-backdrop" @click="closeCreditModal" />
        <div class="modal-box">
          <h2>Баланс</h2>
          <p v-if="creditModal.user" class="muted modal-sub">{{ person(creditModal.user) }} · {{ usd(creditModal.user.balance_usd) }}</p>
          <label for="credit-amount">Сумма $ (+ начислить / − списать)</label>
          <input
            id="credit-amount"
            v-model="creditModal.amount"
            inputmode="decimal"
            placeholder="+10 / −5"
            :disabled="creditModal.user && !!userCreditBusy[creditModal.user.id]"
            @keydown.enter.prevent="submitCreditModal"
          >
          <label for="credit-date">Дата</label>
          <input id="credit-date" v-model="creditModal.date" type="date">
          <div class="row">
            <button
              type="button"
              :disabled="creditModal.user && !!userCreditBusy[creditModal.user.id]"
              @click="submitCreditModal"
            >
              {{ creditModal.user && userCreditBusy[creditModal.user.id] ? 'Сохраняем…' : 'Применить' }}
            </button>
            <button type="button" class="quiet" @click="closeCreditModal">Отмена</button>
          </div>
          <p v-if="creditModal.error" class="error">{{ creditModal.error }}</p>
        </div>
      </div>

      <div v-if="financeModal" class="modal" aria-hidden="false">
        <div class="modal-backdrop" @click="closeFinanceModal" />
        <div class="modal-box modal-wide">
          <template v-if="financeModal === 'expense'">
            <h2>Новый расход</h2>
            <label>Счёт</label>
            <select v-model="financeExpenseForm.account_id">
              <option v-for="a in financeAccounts" :key="a.id" :value="String(a.id)">{{ a.name }}</option>
            </select>
            <label>Категория</label>
            <select v-model="financeExpenseForm.category_id">
              <option value="">Без категории</option>
              <option v-for="c in financeExpenseCategories" :key="c.id" :value="String(c.id)">{{ c.name }}</option>
            </select>
            <div class="modal-grid">
              <div>
                <label>Сумма ₽</label>
                <input v-model="financeExpenseForm.amount_rub" inputmode="decimal" placeholder="1000">
              </div>
              <div>
                <label>Дата</label>
                <input v-model="financeExpenseForm.occurred_at" type="date">
              </div>
            </div>
            <label>Комментарий</label>
            <input v-model="financeExpenseForm.note" placeholder="Пополнение поставщика / комиссия…">
            <div class="row">
              <button type="button" :disabled="financeSaving" @click="addFinanceExpense">Добавить</button>
              <button type="button" class="quiet" @click="closeFinanceModal">Отмена</button>
            </div>
          </template>

          <template v-else-if="financeModal === 'expense-edit' && financeEditExpense">
            <h2>Редактирование расхода #{{ financeEditExpense.id }}</h2>
            <label>Счёт</label>
            <select v-model="financeEditExpense.account_id">
              <option v-for="a in financeAccounts" :key="a.id" :value="String(a.id)">{{ a.name }}</option>
            </select>
            <label>Категория</label>
            <select v-model="financeEditExpense.category_id">
              <option value="">Без категории</option>
              <option v-for="c in financeExpenseCategories" :key="c.id" :value="String(c.id)">{{ c.name }}</option>
            </select>
            <div class="modal-grid">
              <div>
                <label>Сумма ₽</label>
                <input v-model="financeEditExpense.amount_rub" inputmode="decimal">
              </div>
              <div>
                <label>Дата</label>
                <input v-model="financeEditExpense.occurred_at" type="date">
              </div>
            </div>
            <label>Комментарий</label>
            <input v-model="financeEditExpense.note">
            <div class="row">
              <button type="button" :disabled="financeSaving" @click="saveFinanceExpenseEdit">Сохранить</button>
              <button type="button" class="quiet" @click="closeFinanceModal">Отмена</button>
            </div>
          </template>

          <template v-else-if="financeModal === 'withdrawal'">
            <h2>Новый вывод</h2>
            <label>Счёт</label>
            <select v-model="financeWithdrawalForm.account_id">
              <option v-for="a in financeAccounts" :key="a.id" :value="String(a.id)">{{ a.name }}</option>
            </select>
            <label>Категория</label>
            <select v-model="financeWithdrawalForm.category_id">
              <option value="">Без категории</option>
              <option v-for="c in financeWithdrawalCategories" :key="c.id" :value="String(c.id)">{{ c.name }}</option>
            </select>
            <div class="modal-grid">
              <div>
                <label>Сумма ₽</label>
                <input v-model="financeWithdrawalForm.amount_rub" inputmode="decimal">
              </div>
              <div>
                <label>Дата</label>
                <input v-model="financeWithdrawalForm.occurred_at" type="date">
              </div>
            </div>
            <label>Комментарий</label>
            <input v-model="financeWithdrawalForm.note">
            <div class="row">
              <button type="button" :disabled="financeSaving" @click="addFinanceWithdrawal">Добавить</button>
              <button type="button" class="quiet" @click="closeFinanceModal">Отмена</button>
            </div>
          </template>

          <template v-else-if="financeModal === 'account'">
            <h2>Новый счёт</h2>
            <label>Название</label>
            <input v-model="financeAccountForm.name" placeholder="ЮKassa / Тинькофф">
            <label>Провайдер</label>
            <select v-model="financeAccountForm.provider_key">
              <option value="">Обычный счёт</option>
              <option v-for="p in financeProviders" :key="p.value" :value="p.value">{{ p.label }}</option>
            </select>
            <label class="support-filter modal-check">
              <input v-model="financeAccountForm.is_default" type="checkbox">
              Дефолт для расходов
            </label>
            <label>Комментарий</label>
            <input v-model="financeAccountForm.note">
            <div class="row">
              <button type="button" :disabled="financeSaving" @click="addFinanceAccount">Создать</button>
              <button type="button" class="quiet" @click="closeFinanceModal">Отмена</button>
            </div>
          </template>

          <template v-else-if="financeModal === 'deposit'">
            <h2>Пополнение счёта</h2>
            <label>Счёт</label>
            <select v-model="financeDepositForm.account_id">
              <option v-for="a in financeAccounts" :key="a.id" :value="String(a.id)">{{ a.name }}</option>
            </select>
            <div class="modal-grid">
              <div>
                <label>Сумма ₽</label>
                <input v-model="financeDepositForm.amount_rub" inputmode="decimal" placeholder="1000">
              </div>
              <div>
                <label>Дата</label>
                <input v-model="financeDepositForm.occurred_at" type="date">
              </div>
            </div>
            <label>Комментарий</label>
            <input v-model="financeDepositForm.note">
            <div class="row">
              <button type="button" :disabled="financeSaving" @click="addFinanceDeposit">Пополнить</button>
              <button type="button" class="quiet" @click="closeFinanceModal">Отмена</button>
            </div>
          </template>

          <template v-else-if="financeModal === 'transfer'">
            <h2>Перевод между счетами</h2>
            <label>Откуда</label>
            <select v-model="financeTransferForm.account_id">
              <option disabled value="">Откуда</option>
              <option v-for="a in financeAccounts" :key="'f'+a.id" :value="String(a.id)">{{ a.name }}</option>
            </select>
            <label>Куда</label>
            <select v-model="financeTransferForm.counterparty_account_id">
              <option disabled value="">Куда</option>
              <option v-for="a in financeAccounts" :key="'t'+a.id" :value="String(a.id)">{{ a.name }}</option>
            </select>
            <div class="modal-grid">
              <div>
                <label>Сумма ₽</label>
                <input v-model="financeTransferForm.amount_rub" inputmode="decimal" placeholder="1000">
              </div>
              <div>
                <label>Дата</label>
                <input v-model="financeTransferForm.occurred_at" type="date">
              </div>
            </div>
            <label>Комментарий</label>
            <input v-model="financeTransferForm.note">
            <div class="row">
              <button type="button" :disabled="financeSaving" @click="addFinanceTransfer">Перевести</button>
              <button type="button" class="quiet" @click="closeFinanceModal">Отмена</button>
            </div>
          </template>

          <template v-else-if="financeModal === 'category'">
            <h2>Новая категория</h2>
            <label>Тип</label>
            <select v-model="financeCategoryForm.kind">
              <option value="expense">Расход</option>
              <option value="withdrawal">Вывод</option>
            </select>
            <label>Название</label>
            <input v-model="financeCategoryForm.name">
            <label>Цвет</label>
            <input v-model="financeCategoryForm.color" type="color">
            <div class="row">
              <button type="button" :disabled="financeSaving" @click="addFinanceCategory">Добавить</button>
              <button type="button" class="quiet" @click="closeFinanceModal">Отмена</button>
            </div>
          </template>

          <p v-if="financeError" class="error">{{ financeError }}</p>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import AdminChart from '../components/AdminChart.vue'
import AppIcon from '../components/ui/AppIcon.vue'
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
  filteredLedgerItems,
  ledgerSearch,
  ledgerForm,
  ledgerError,
  ledgerUserOptions,
  ledgerKindOptions,
  financeSummary,
  financeSection,
  financeError,
  financeSaving,
  financeModal,
  financeExpenseForm,
  financeWithdrawalForm,
  financeAccountForm,
  financeDepositForm,
  financeTransferForm,
  financeCategoryForm,
  financeEditExpense,
  financeAccounts,
  financeExpenseCategories,
  financeWithdrawalCategories,
  financeExpenses,
  financeWithdrawals,
  financeOperations,
  financeProviders,
  creditModal,
  openFinanceModal,
  closeFinanceModal,
  financeDateOnly,
  loadFinance,
  addFinanceExpense,
  saveFinanceExpenseEdit,
  startEditExpense,
  addFinanceWithdrawal,
  deleteFinanceOperation,
  addFinanceAccount,
  setDefaultFinanceAccount,
  deleteFinanceAccount,
  addFinanceDeposit,
  addFinanceTransfer,
  addFinanceCategory,
  saveFinanceCategory,
  archiveFinanceCategory,
  financeKindClass,
  openCreditModal,
  closeCreditModal,
  submitCreditModal,
  topups,
  users,
  filteredUsers,
  usersSearch,
  userCreditBusy,
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
  ledgerModalOpen,
  openLedgerModal,
  closeLedgerModal,
  addLedgerEntry,
  deleteLedgerEntry,
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
  ledgerKindClass,
  ledgerAmountClass,
  ledgerAmountUsd,
  ledgerAmountRub,
  ledgerAmountText,
  ledgerNoteText,
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
.admin-page td.actions, .admin-page th.actions {
  width: 1%;
  white-space: nowrap;
  text-align: right;
  vertical-align: middle;
}
.admin-page td.actions .actions-inner {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  justify-content: flex-end;
}
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

.admin-page .tab-ledger .ledger-head {
  align-items: flex-start;
  margin-bottom: 20px;
}
.admin-page .ledger-sub { margin: 4px 0 0; }
.admin-page .ledger-checks {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}
.admin-page .ledger-check {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  padding: 14px 14px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-soft);
}
.admin-page .ledger-check.ok {
  background: var(--ok-soft);
  border-color: #c7e3d4;
}
.admin-page .ledger-check.bad {
  background: var(--danger-soft);
  border-color: #e3b4b4;
}
.admin-page .ledger-check-label {
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}
.admin-page .ledger-check-value {
  font-size: 18px;
  font-weight: 650;
  letter-spacing: -0.03em;
  line-height: 1.25;
  overflow-wrap: anywhere;
}
.admin-page .ledger-check.ok .ledger-check-value { color: var(--ok); }
.admin-page .ledger-check.bad .ledger-check-value { color: var(--danger); }
.admin-page .ledger-check-hint {
  color: var(--muted);
  font-size: 12px;
}
.admin-page .ledger-create,
.admin-page .ledger-list {
  margin-top: 18px;
  padding: 16px 18px 18px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-soft);
}
.admin-page .ledger-create h3,
.admin-page .ledger-list-head h3 {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 650;
}
.admin-page .ledger-form {
  display: grid;
  grid-template-columns: minmax(160px, 1.5fr) minmax(110px, 0.9fr) repeat(2, minmax(90px, 0.8fr)) minmax(140px, 1.2fr) auto;
  gap: 10px;
  align-items: end;
}
.admin-page .ledger-form label { margin: 0 0 6px; }
.admin-page .ledger-form .field { min-width: 0; }
.admin-page .ledger-form .field.grow { min-width: 140px; }
.admin-page .ledger-add {
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  white-space: nowrap;
}
.admin-page .ledger-list { background: #fff; }
.admin-page .ledger-list-tools {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.admin-page .ledger-list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.admin-page .ledger-list-head h3 { margin: 0; }
.admin-page .ledger-search {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  padding: 0 12px;
  min-width: min(280px, 100%);
  height: 38px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface-soft);
  color: var(--muted);
  text-transform: none;
  letter-spacing: 0;
  font-weight: 400;
}
.admin-page .ledger-search input {
  width: 100%;
  border: 0;
  padding: 0;
  background: transparent;
  box-shadow: none;
  font-size: 13px;
}
.admin-page .ledger-search input:focus {
  outline: none;
  box-shadow: none;
}
.admin-page .ledger-search:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(28, 25, 21, 0.08);
  background: #fff;
}
.admin-page .tab-ledger .table-wrap {
  border-color: var(--border);
  background: #fff;
}
.admin-page .ledger-table {
  width: 100%;
  min-width: 720px;
  border-collapse: collapse;
  table-layout: fixed;
}
.admin-page .ledger-table th:nth-child(1),
.admin-page .ledger-table td:nth-child(1) { width: 132px; }
.admin-page .ledger-table th:nth-child(2),
.admin-page .ledger-table td:nth-child(2) { width: 26%; }
.admin-page .ledger-table th:nth-child(3),
.admin-page .ledger-table td:nth-child(3) { width: auto; }
.admin-page .ledger-table th:nth-child(4),
.admin-page .ledger-table td:nth-child(4) { width: 110px; }
.admin-page .ledger-table th:nth-child(5),
.admin-page .ledger-table td:nth-child(5) {
  width: 48px;
  padding-left: 4px;
  padding-right: 12px;
}
.admin-page .ledger-table th,
.admin-page .ledger-table td {
  padding: 12px 14px;
  vertical-align: middle;
}
.admin-page .ledger-table td.num {
  text-align: right;
}
.admin-page .ledger-table td.actions {
  text-align: right;
  vertical-align: middle;
}
.admin-page .ledger-table .user-cell.compact {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.admin-page .ledger-table .user-cell.compact .user-channel {
  width: 24px;
  height: 24px;
  flex: 0 0 24px;
  border-radius: 7px;
  margin-top: 0;
}
.admin-page .ledger-table .user-name {
  font-weight: 500;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.admin-page .ledger-op {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.admin-page .kind-badge {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 68px;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 650;
  border: 1px solid transparent;
  line-height: 1.2;
}
.admin-page .kind-badge.kind-topup {
  background: #eef4ff;
  color: #2f4f8c;
  border-color: #d5e0f5;
}
.admin-page .kind-badge.kind-credit {
  background: var(--surface-soft);
  color: var(--text);
  border-color: var(--border);
}
.admin-page .kind-badge.kind-spend {
  background: #f4f1ea;
  color: var(--muted);
  border-color: var(--border);
}
.admin-page .kind-badge.kind-adjust {
  background: var(--warn-soft);
  color: var(--warn);
  border-color: #ecdca8;
}
.admin-page .ledger-note {
  min-width: 0;
  color: var(--muted);
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.admin-page .ledger-amt {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  line-height: 1.25;
}
.admin-page .ledger-usd { font-weight: 600; }
.admin-page .ledger-rub {
  color: var(--muted);
  font-size: 12px;
  font-weight: 400;
}
.admin-page .amt-in .ledger-usd { color: var(--ok); }
.admin-page .amt-out .ledger-usd { color: var(--muted); }
.admin-page .amt-zero .ledger-usd { color: var(--muted); font-weight: 500; }
.admin-page .amt-in { color: var(--ok); font-variant-numeric: tabular-nums; }
.admin-page .amt-out { color: var(--muted); font-variant-numeric: tabular-nums; }
.admin-page button.icon-btn.danger-ghost {
  background: transparent;
  color: var(--muted);
  border: 1px solid transparent;
}
.admin-page button.icon-btn.danger-ghost:hover {
  background: var(--danger-soft);
  color: var(--danger);
  border-color: #e3b4b4;
  transform: none;
}

.admin-page .tab-finance .finance-head {
  align-items: flex-start;
  margin-bottom: 18px;
}
.admin-page .finance-sub { margin: 4px 0 0; }
.admin-page .finance-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}
.admin-page .finance-kpi {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-soft);
}
.admin-page .finance-kpi span {
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}
.admin-page .finance-kpi b {
  font-size: 20px;
  letter-spacing: -0.03em;
  overflow-wrap: anywhere;
}
.admin-page .finance-kpi small {
  color: var(--muted);
  font-size: 12px;
}
.admin-page .finance-kpi.emphasis.ok {
  background: var(--ok-soft);
  border-color: #c7e3d4;
}
.admin-page .finance-kpi.emphasis.ok b { color: var(--ok); }
.admin-page .finance-kpi.emphasis.bad {
  background: var(--danger-soft);
  border-color: #e3b4b4;
}
.admin-page .finance-kpi.emphasis.bad b { color: var(--danger); }
.admin-page .finance-kpi.bad {
  background: var(--danger-soft);
  border-color: #e3b4b4;
}
.admin-page .finance-alert {
  margin: 0 0 14px;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid #e3b4b4;
  background: var(--danger-soft);
  color: var(--danger);
  font-size: 14px;
}
.admin-page .finance-alert b { color: var(--text); }
.admin-page .finance-grid {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 12px;
  margin-bottom: 16px;
}
.admin-page .finance-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 18px;
}
.admin-page .finance-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.admin-page .finance-card-head h3 { margin: 0; }
.admin-page .finance-card-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.admin-page .finance-card-head button.sm,
.admin-page .ledger-list-tools button.sm {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.admin-page .finance-form.stacked {
  grid-template-columns: 1fr;
}
.admin-page .cat-chip {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  color: #fff;
  font-size: 11px;
  font-weight: 650;
}
.admin-page .finance-edit {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}
.admin-page .finance-card {
  padding: 16px 18px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-soft);
}
.admin-page .finance-card.wide { grid-column: 1 / -1; }
.admin-page .finance-card h3 {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 650;
}
.admin-page .finance-breakdown {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
}
.admin-page .finance-breakdown li {
  display: grid;
  grid-template-columns: 18px 1fr auto;
  gap: 8px;
  align-items: baseline;
  font-size: 13px;
}
.admin-page .finance-breakdown .sign { color: var(--muted); }
.admin-page .finance-breakdown.emphasis,
.admin-page .finance-breakdown li.emphasis {
  margin-top: 4px;
  padding-top: 8px;
  border-top: 1px solid var(--border);
  font-weight: 650;
}
.admin-page .finance-breakdown li.ok b { color: var(--ok); }
.admin-page .finance-breakdown li.bad b { color: var(--danger); }
.admin-page .finance-hint { margin: 12px 0 0; }
.admin-page .finance-opening {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 10px;
}
.admin-page .finance-opening input {
  max-width: 180px;
}
.admin-page .finance-form {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr)) auto;
  gap: 10px;
  align-items: end;
}
.admin-page .finance-form .field { min-width: 0; }
.admin-page .finance-form .field.grow { grid-column: span 2; }
.admin-page .finance-form label { margin: 0 0 6px; }
.admin-page .finance-form button { height: 42px; }
.admin-page .finance-list {
  padding: 16px 18px 18px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: #fff;
}
.admin-page .finance-list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.admin-page .finance-list-head h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 650;
}
.admin-page .finance-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.admin-page .finance-filters button.on {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}
.admin-page .finance-table {
  width: 100%;
  min-width: 720px;
  table-layout: fixed;
  border-collapse: collapse;
}
.admin-page .finance-table th,
.admin-page .finance-table td {
  padding: 11px 12px;
  vertical-align: middle;
}
.admin-page .finance-note-cell {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--muted);
  font-size: 13px;
}
.admin-page .kind-badge.fin-income {
  background: var(--ok-soft);
  color: var(--ok);
  border-color: #c7e3d4;
}
.admin-page .kind-badge.fin-expense {
  background: var(--danger-soft);
  color: var(--danger);
  border-color: #e3b4b4;
}
.admin-page .kind-badge.fin-reserve {
  background: var(--warn-soft);
  color: var(--warn);
  border-color: #ecdca8;
}
.admin-page .kind-badge.fin-release {
  background: #eef4ff;
  color: #2f4f8c;
  border-color: #d5e0f5;
}
.admin-page .kind-badge.fin-withdrawal {
  background: #f4f1ea;
  color: var(--text);
  border-color: var(--border);
}
.admin-page .kind-badge.fin-deposit {
  background: #e9f4fb;
  color: #2a6f97;
  border-color: #c9e0ef;
}
@media (max-width: 1100px) {
  .admin-page .finance-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .admin-page .finance-grid,
  .admin-page .finance-split { grid-template-columns: 1fr; }
  .admin-page .finance-form { grid-template-columns: 1fr 1fr; }
  .admin-page .finance-form .field.grow,
  .admin-page .finance-form button { grid-column: 1 / -1; }
}
@media (max-width: 640px) {
  .admin-page .finance-kpis { grid-template-columns: 1fr; }
  .admin-page .finance-form { grid-template-columns: 1fr; }
}

.admin-page .tab-users .users-head {
  align-items: flex-start;
  margin-bottom: 16px;
}
.admin-page .users-sub { margin: 4px 0 0; }
.admin-page .users-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.admin-page .users-search {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  padding: 0 12px;
  min-width: min(280px, 100%);
  height: 38px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface-soft);
  color: var(--muted);
  text-transform: none;
  letter-spacing: 0;
  font-weight: 400;
}
.admin-page .users-search input {
  width: 100%;
  border: 0;
  padding: 0;
  background: transparent;
  box-shadow: none;
  font-size: 13px;
}
.admin-page .users-search input:focus {
  outline: none;
  box-shadow: none;
}
.admin-page .users-search:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(28, 25, 21, 0.08);
  background: #fff;
}
.admin-page .users-table {
  min-width: 860px;
  table-layout: fixed;
  width: 100%;
}
.admin-page .users-table th,
.admin-page .users-table td {
  padding: 12px 14px;
  vertical-align: middle;
}
.admin-page .users-table th:nth-child(1),
.admin-page .users-table td:nth-child(1) { width: 30%; }
.admin-page .users-table th:nth-child(2),
.admin-page .users-table td:nth-child(2) { width: 96px; }
.admin-page .users-table th:nth-child(3),
.admin-page .users-table td:nth-child(3) { width: 140px; }
.admin-page .users-table th:nth-child(4),
.admin-page .users-table td:nth-child(4) { width: 148px; }
.admin-page .users-table th:nth-child(5),
.admin-page .users-table td:nth-child(5) { width: 168px; }
.admin-page .users-table th:nth-child(6),
.admin-page .users-table td:nth-child(6) {
  width: 52px;
  padding-left: 4px;
  padding-right: 12px;
}
.admin-page .user-cell {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
}
.admin-page .user-channel {
  flex: 0 0 28px;
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: 1px solid var(--border);
  margin-top: 1px;
}
.admin-page .user-channel.tg {
  background: #e9f4fb;
  border-color: #c9e0ef;
  color: #2a6f97;
}
.admin-page .user-channel.web {
  background: #f3efe7;
  border-color: #ddd4c6;
  color: #6b645b;
}
.admin-page .user-meta {
  display: grid;
  gap: 4px;
  min-width: 0;
}
.admin-page .user-name {
  font-weight: 550;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.admin-page .user-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.admin-page .user-badges .badge { margin: 0; }
.admin-page .tab-users tr.paid > td {
  background: #f3f8f4;
}
.admin-page .tab-users tr.paid:hover > td {
  background: #eaf3ed;
}
.admin-page .tab-users tr.blocked > td {
  opacity: 0.78;
}
.admin-page .tab-users td.balance {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
.admin-page .tab-users .key-cell code {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  color: var(--muted);
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 2px 6px;
  vertical-align: middle;
}
.admin-page .credit-open {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
}
.admin-page .credit-open.busy,
.admin-page .credit-open:disabled {
  opacity: 0.7;
  cursor: wait;
}
.admin-page .credit-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(28, 25, 21, 0.2);
  border-top-color: var(--text);
  border-radius: 50%;
  display: block;
  animation: credit-spin 0.7s linear infinite;
}
@keyframes credit-spin {
  to { transform: rotate(360deg); }
}
.admin-page .access-cell {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
  white-space: nowrap;
}
.admin-page .access-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
}
.admin-page .access-status::before {
  content: '';
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
}
.admin-page .access-status.on { color: var(--ok); }
.admin-page .access-status.off { color: var(--danger); }
.admin-page .access-block { color: var(--danger); border-color: #e3b4b4; }
@media (max-width: 640px) {
  .admin-page .users-toolbar { width: 100%; }
  .admin-page .users-search { width: 100%; min-width: 0; }
}

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
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface-soft);
  color: var(--text);
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0;
  text-transform: none;
  line-height: 1.2;
  cursor: pointer;
  user-select: none;
}
.admin-page .support-filter:hover {
  border-color: var(--border-strong);
  background: #fff;
}
.admin-page .support-filter input[type='checkbox'] {
  width: 16px;
  height: 16px;
  margin: 0;
  padding: 0;
  flex: 0 0 16px;
  border: 1px solid var(--border-strong);
  border-radius: 4px;
  accent-color: var(--accent);
  box-shadow: none;
  cursor: pointer;
}
.admin-page .support-filter .badge {
  margin: 0;
}
.admin-page .support-layout {
  display: grid;
  grid-template-columns: minmax(220px, 0.9fr) minmax(0, 1.4fr);
  gap: 14px;
  height: min(640px, calc(100vh - 210px));
  min-height: 420px;
  align-items: stretch;
}
.admin-page .support-list {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  overflow: auto;
  min-height: 0;
  height: 100%;
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
  min-height: 0;
  height: 100%;
  background: #fff;
  overflow: hidden;
}
.admin-page .support-chat-head {
  flex-shrink: 0;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  background: var(--surface-soft);
}
.admin-page .support-chat-head p { margin: 2px 0 0; }
.admin-page .admin-support-thread {
  flex: 1 1 0;
  min-height: 0;
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
  flex-shrink: 0;
  border-top: 1px solid var(--border);
  padding: 12px;
  display: grid;
  gap: 8px;
  background: #fff;
}
.admin-page .support-composer textarea {
  width: 100%;
  min-height: 72px;
  max-height: 160px;
  resize: vertical;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  font: inherit;
}
.admin-page .support-composer .row {
  margin-top: 0;
}
.admin-page .support-placeholder {
  margin: auto;
  padding: 24px;
  text-align: center;
}
@media (max-width: 900px) {
  .admin-page .panel-head {
    align-items: flex-start;
  }
  .admin-page .support-filter {
    width: 100%;
    justify-content: flex-start;
    border-radius: var(--radius-sm);
  }
  .admin-page .support-layout {
    grid-template-columns: 1fr;
    height: auto;
    min-height: 0;
    gap: 12px;
  }
  .admin-page .support-list {
    height: auto;
    max-height: 200px;
  }
  .admin-page .support-chat-pane {
    height: min(480px, calc(100dvh - 280px));
    min-height: 320px;
  }
  .admin-page .support-composer {
    padding: 10px;
  }
  .admin-page .support-composer textarea {
    min-height: 64px;
  }
  .admin-page .support-composer button {
    width: 100%;
  }
  .admin-page .support-bubble {
    max-width: 92%;
  }
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
  max-height: calc(100dvh - 36px);
  overflow: auto;
}
.admin-page .modal-box.modal-wide { width: min(480px, 100%); }
.admin-page .modal-box h2 { margin-bottom: 8px; }
.admin-page .modal-sub { margin: 0 0 14px; }
.admin-page .modal-box label {
  display: block;
  margin: 12px 0 6px;
  color: var(--muted);
  font-size: 13px;
}
.admin-page .modal-box label:first-of-type { margin-top: 0; }
.admin-page .modal-box .row { margin-top: 16px; }
.admin-page .modal-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.admin-page .modal-grid label { margin-top: 12px; }
.admin-page .modal-check {
  display: inline-flex !important;
  align-items: center;
  gap: 8px;
  margin-top: 14px !important;
  color: var(--text) !important;
  text-transform: none;
  width: auto;
}

@media (max-width: 1100px) {
  .admin-page .ledger-checks { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 960px) {
  .admin-page .settings-grid, .admin-page .split { grid-template-columns: 1fr; }
  .admin-page .ledger-form { grid-template-columns: 1fr 1fr; }
  .admin-page .ledger-add { grid-column: 1 / -1; width: 100%; }
}
@media (max-width: 640px) {
  .admin-page main { padding: 16px 14px 48px; }
  .admin-page .panel { padding: 18px 16px; }
  .admin-page .ledger-checks { grid-template-columns: 1fr 1fr; }
  .admin-page .ledger-form { grid-template-columns: 1fr; }
  .admin-page .ledger-search { width: 100%; min-width: 0; }
  .admin-page .ledger-create,
  .admin-page .ledger-list { padding: 14px; }
}
</style>
