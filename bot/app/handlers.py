import html
import logging
from datetime import datetime
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from pathlib import Path
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    CopyTextButton,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    ErrorEvent,
    Message,
    ReplyKeyboardRemove,
)

from app.guide import apps_screen, known_app, os_screen, other_screen, steps_screen
from app.backend import (
    BackendError,
    accept_offer,
    check_topup,
    create_topup,
    get_history,
    get_key_history,
    get_user,
    toggle_notification,
    issue_key,
    list_products,
    read_key,
    reissue_key,
    upsert_user,
)

router = Router()
log = logging.getLogger("app.handlers")
UNAVAILABLE = "Сервис сейчас недоступен. Попробуйте чуть позже."
_IMAGES = Path(__file__).resolve().parent / "images"
_MSK = ZoneInfo("Europe/Moscow")
_MONTHS = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


class Topup(StatesGroup):
    amount = State()
    confirm = State()


def _usd(value: float) -> str:
    return f"${value:.2f}"


def _spent(value: float) -> str:
    return f"${value:.4f}"


def _when(value: str) -> str:
    if not value:
        return "только что"
    moment = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(_MSK)
    return f"{moment.day} {_MONTHS[moment.month - 1]} {moment.year}, {moment:%H:%M}"


def _date_short(value: str) -> str:
    if not value:
        return "—"
    moment = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(_MSK)
    return moment.strftime("%d.%m.%Y")


def _ago(value: str) -> str:
    if not value:
        return "ещё не было"
    moment = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(_MSK)
    secs = int((datetime.now(_MSK) - moment).total_seconds())
    if secs < 0:
        return "только что"
    if secs < 60:
        return "только что" if secs < 10 else f"{secs} сек назад"
    mins = secs // 60
    if mins < 60:
        return f"{mins} мин назад"
    hours = mins // 60
    if hours < 24:
        return f"{hours} ч назад"
    days = hours // 24
    if days < 30:
        return f"{days} дн назад"
    return _date_short(value)


def _mask_key(secret: str) -> str:
    if len(secret) <= 12:
        return secret
    return f"{secret[:8]}...{secret[-4:]}"


def _explain(exc: BackendError) -> str:
    reasons = {
        "offer": "Сначала примите все условия.",
        "blocked": "Доступ к сервису ограничён. Подробности — в главном меню.",
        "no-offer-url": "Ссылки на документы ещё не настроены.",
        "balance": "Сначала пополните баланс.",
        "empty": "Лимит нулевой. Сначала пополните баланс.",
        "sales-closed": "Пополнение закрыто: в админке не указана цена доллара.",
        "min-topup": "Минимальная сумма пополнения — 10 $.",
        "no-yookassa": "Оплата не настроена.",
        "no-bot": "Не удалось открыть возврат в бота. Проверьте токен бота в настройках.",
        "yookassa": "Платёж сейчас не создаётся. Попробуйте позже.",
        "key-exists": "Токен уже выпущен. Откройте «Мой токен».",
        "no-key": "Токена ещё нет. Пополните баланс и нажмите «Выпустить токен».",
        "supplier": "Сейчас нельзя провести операцию: на счёте поставщика не хватает лимита.",
        "reissue-failed": "Старый токен удалён, новый не создался. Лимит сохранён — нажмите «Выпустить токен».",
    }
    if exc.status == 0:
        return UNAVAILABLE
    return reasons.get(exc.detail, UNAVAILABLE)


def _button(
    text: str,
    *,
    callback: str = "",
    url: str = "",
    copy: str = "",
    green: bool = False,
) -> InlineKeyboardButton:
    extra: dict = {"style": "success"} if green else {}
    if copy:
        return InlineKeyboardButton(text=text, copy_text=CopyTextButton(text=copy), **extra)
    if url:
        return InlineKeyboardButton(text=text, url=url, **extra)
    return InlineKeyboardButton(text=text, callback_data=callback, **extra)


def _back_row() -> list[InlineKeyboardButton]:
    return [_button("← Назад", callback="cabinet")]


def _markup(rows: list[list[tuple]]) -> InlineKeyboardMarkup:
    built: list[list[InlineKeyboardButton]] = []
    for row in rows:
        buttons: list[InlineKeyboardButton] = []
        for item in row:
            kind, label, value = item[0], item[1], item[2]
            green = len(item) > 3 and bool(item[3])
            if kind == "url":
                buttons.append(_button(label, url=value, green=green))
            elif kind == "copy":
                buttons.append(_button(label, copy=value, green=green))
            else:
                buttons.append(_button(label, callback=value, green=green))
        built.append(buttons)
    return InlineKeyboardMarkup(inline_keyboard=built)


def _site(profile: dict) -> str:
    url = str(profile.get("offer_url") or "").strip().rstrip("/")
    if url.endswith("/offer"):
        url = url[: -len("/offer")]
    return url


def _offer_screen(profile: dict) -> tuple[str, InlineKeyboardMarkup]:
    privacy = str(profile.get("privacy_url") or "")
    consent = str(profile.get("consent_url") or "")
    offer = str(profile.get("offer_url") or "")
    text = (
        "🤖 <b>Добро пожаловать в AI-Market!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Здесь вы получаете доступ к API лучших ИИ-моделей через единый ключ.\n\n"
        "✅ Без абонентской платы\n"
        "✅ Оплата картой в рублях (Без привязки карты)\n"
        "✅ Списание с баланса по факту использования\n"
        "✅ Поддержка OpenAI, Anthropic и Google форматов\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Перед началом работы необходимо ознакомиться и принять следующие документы:\n\n"
        "📜 Политика конфиденциальности\n"
        "📋 Согласие на обработку персональных данных\n"
        "📄 Публичная оферта\n\n"
        "Жмите «Принять все условия»."
    )
    rows: list[list[InlineKeyboardButton]] = []
    if privacy and consent and offer:
        rows.append([
            _button("📜 Политика", url=privacy),
            _button("📋 Согласие", url=consent),
            _button("📄 Оферта", url=offer),
        ])
    else:
        text += "\n\nСсылки на документы появятся, когда в админке будет указан адрес сайта."
    rows.append([_button("✅ Принять все условия", callback="offer:yes", green=True)])
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def _blocked_screen(profile: dict) -> tuple[str, InlineKeyboardMarkup]:
    support = str(profile.get("support_username") or "").strip().lstrip("@")
    text = (
        "🚫 <b>Доступ к сервису ограничён</b>\n\n"
        "Ваш аккаунт заблокирован по решению администрации за нарушение принятых правил.\n"
    )
    if support:
        safe = html.escape(support)
        text += (
            f"Если вы считаете, что это ошибка, обратитесь в поддержку: "
            f'<a href="https://t.me/{safe}">@{safe}</a>'
        )
    else:
        text += "Если вы считаете, что это ошибка, обратитесь в поддержку."
    rows: list[list[InlineKeyboardButton]] = []
    if support:
        rows.append([_button("📞 Поддержка", url=f"https://t.me/{support}")])
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def _welcome_buttons(profile: dict) -> list[list[InlineKeyboardButton]]:
    return [
        [
            _button("💳 Пополнить баланс", callback="topup", green=True),
            _button("🔑 Мой ключ", callback="keys"),
        ],
        [_button("📊 История транзакций", callback="history")],
        [
            _button("📖 Инструкция", callback="guide"),
            _button("❓ FAQ", callback="faq"),
        ],
        [
            _button("🔔 Уведомления", callback="notifications"),
            _button("📞 Поддержка", callback="support"),
        ],
    ]


def _week_chart(days: list[dict]) -> str:
    if not days:
        return ""
    amounts = [float(item.get("usd") or 0) for item in days]
    peak = max(amounts) if amounts else 0.0
    if peak <= 0:
        return "📊 <b>Расход за 7 дней</b>\nнет данных"
    width = 10
    lines: list[str] = []
    for item in days:
        usd = float(item.get("usd") or 0)
        label = str(item.get("label") or "??")[:2]
        bar_len = round(usd / peak * width) if usd > 0 else 0
        bar = "█" * bar_len if bar_len else "▏"
        amount = _spent(usd) if usd > 0 else "$0"
        lines.append(f"{label} {bar} {amount}")
    return "📊 <b>Расход за 7 дней</b>\n<pre>" + html.escape("\n".join(lines)) + "</pre>"


def _error_screen(profile: dict | None = None) -> tuple[str, InlineKeyboardMarkup]:
    support = str((profile or {}).get("support_username") or "").strip().lstrip("@")
    text = "⚠️ <b>Произошла ошибка</b>\n\nПопробуйте позже или обратитесь в поддержку:"
    if support:
        safe = html.escape(support)
        text += f' <a href="https://t.me/{safe}">@{safe}</a>'
    markup = InlineKeyboardMarkup(
        inline_keyboard=[[_button("🏠 Главное меню", callback="cabinet", green=True)]]
    )
    return text, markup


def _support_line(profile: dict) -> str:
    support = str(profile.get("support_username") or "").strip().lstrip("@")
    if support:
        safe = html.escape(support)
        return (
            "😊 Я понимаю кнопки и команды — если у вас есть вопрос, напишите в поддержку: "
            f'<a href="https://t.me/{safe}">@{safe}</a>'
        )
    return "😊 Я понимаю кнопки и команды — если у вас есть вопрос, напишите в поддержку."


def _plain_text_screen(profile: dict) -> tuple[str, InlineKeyboardMarkup]:
    balance = float(profile.get("balance_usd") or 0)
    keys = 1 if profile.get("has_key") else 0
    week = profile.get("spent_week_usd") or []
    text = (
        f"{_support_line(profile)}\n\n"
        f"💰 Баланс: <b>{_usd(balance)}</b>\n"
        f"🔑 Ключей: <b>{keys}</b>\n\n"
        f"{_week_chart(week if isinstance(week, list) else [])}"
    )
    return text, InlineKeyboardMarkup(inline_keyboard=_welcome_buttons(profile))


def _unknown_command_screen(profile: dict) -> tuple[str, InlineKeyboardMarkup]:
    balance = float(profile.get("balance_usd") or 0)
    week = profile.get("spent_week_usd") or []
    text = (
        "🤔 Не знаю такой команды\n\n"
        f"💰 Баланс: <b>{_usd(balance)}</b>\n\n"
        f"{_week_chart(week if isinstance(week, list) else [])}"
    )
    return text, InlineKeyboardMarkup(inline_keyboard=_welcome_buttons(profile))


def _cabinet_screen(profile: dict) -> tuple[str, InlineKeyboardMarkup]:
    balance = float(profile.get("balance_usd") or 0)
    week = profile.get("spent_week_usd") or []
    text = (
        "<b>Личный кабинет</b>\n\n"
        f"Баланс: <b>{_usd(balance)}</b>\n"
        f"Расход сегодня: {_spent(float(profile.get('spent_today_usd') or 0))}\n"
        f"Расход за месяц: {_spent(float(profile.get('spent_month_usd') or 0))}\n\n"
        f"{_week_chart(week if isinstance(week, list) else [])}"
    )
    return text, InlineKeyboardMarkup(inline_keyboard=_welcome_buttons(profile))


def _welcome_screen(profile: dict, *, just_accepted: bool = False) -> tuple[str, InlineKeyboardMarkup]:
    if profile.get("blocked"):
        return _blocked_screen(profile)
    if not just_accepted:
        return _cabinet_screen(profile)
    text = (
        "✅ <b>Условия приняты!</b>\n\n"
        "🎉 <b>Добро пожаловать в AI-Market!</b>\n\n"
        "Теперь вам доступны все функции:\n"
        "💳 Пополнение баланса\n"
        "🔑 Создание и управление API-ключами\n"
        "🤖 Использование ИИ-моделей\n\n"
        "Чтобы получить ключ и начать использовать ИИ пополните баланс.\n"
        "Инструкцию по подключению можно найти в разделе «📖 Инструкция»."
    )
    return text, InlineKeyboardMarkup(inline_keyboard=_welcome_buttons(profile))


_FAQ_TOPICS: tuple[tuple[str, str], ...] = (
    ("topup", "💳 Как пополнить баланс?"),
    ("key", "🔑 Как получить ключ?"),
    ("price", "💰 Какая цена у токенов?"),
    ("models", "🤖 Какие модели доступны?"),
    ("safe", "🔒 Безопасно ли это?"),
    ("billing", "⚡ Как списываются токены?"),
    ("refund", "🔄 Можно ли вернуть деньги?"),
    ("support", "📞 Как связаться с поддержкой?"),
    ("broken", "🚫 Ключ не работает?"),
)
_POPULAR_MODELS = (
    "gpt-4o",
    "gpt-4o-mini",
    "claude-3-5-sonnet",
    "claude-3-5-sonnet-latest",
    "gemini-1.5-pro",
    "gemini-1.5-pro-latest",
)


def _faq_nav() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _button("⬅️ Назад к вопросам", callback="faq"),
                _button("🏠 Главное меню", callback="cabinet"),
            ]
        ]
    )


def _faq_list_screen() -> tuple[str, InlineKeyboardMarkup]:
    text = "❓ <b>Часто задаваемые вопросы</b>"
    rows = [[_button(label, callback=f"faq:q:{topic}")] for topic, label in _FAQ_TOPICS]
    rows.append([_button("🏠 Главное меню", callback="cabinet")])
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def _support_tag(profile: dict) -> str:
    support = str(profile.get("support_username") or "").strip().lstrip("@")
    if support:
        safe = html.escape(support)
        return f'<a href="https://t.me/{safe}">@{safe}</a>'
    return "поддержку сервиса"


def _model_provider(name: str) -> str:
    lower = name.lower()
    if "claude" in lower:
        return "anthropic"
    if "gemini" in lower:
        return "google"
    if any(token in lower for token in ("gpt", "o1", "o3", "chatgpt")):
        return "openai"
    if "grok" in lower:
        return "grok"
    if "deepseek" in lower:
        return "deepseek"
    if "llama" in lower or "meta-" in lower:
        return "meta"
    return "other"


def _provider_title(provider: str) -> str:
    titles = {
        "openai": "🔵 OpenAI",
        "anthropic": "🟣 Anthropic",
        "google": "🟢 Google",
        "grok": "⚫ xAI",
        "deepseek": "🟠 DeepSeek",
        "meta": "🔷 Meta",
        "other": "⚪ Другие",
    }
    return titles.get(provider, "⚪ Другие")


def _price_million(value: float) -> str:
    return f"${value:.2f}"


def _faq_price_lines(products: list[dict]) -> list[str]:
    by_name = {str(item.get("model_name") or ""): item for item in products}
    lines: list[str] = []
    seen: set[str] = set()
    for wanted in _POPULAR_MODELS:
        item = by_name.get(wanted)
        if item is None:
            continue
        name = str(item.get("model_name") or wanted)
        if name in seen:
            continue
        seen.add(name)
        inp = float(item.get("input_usd_per_million") or 0)
        out = float(item.get("output_usd_per_million") or 0)
        request = item.get("request_usd")
        if request is not None:
            lines.append(f"• {html.escape(name)} — {_price_million(float(request))} за запрос")
        else:
            lines.append(
                f"• {html.escape(name)} — {_price_million(inp)} in / {_price_million(out)} out"
            )
        if len(lines) >= 4:
            break
    if not lines:
        for item in products[:4]:
            name = str(item.get("model_name") or "—")
            inp = float(item.get("input_usd_per_million") or 0)
            out = float(item.get("output_usd_per_million") or 0)
            request = item.get("request_usd")
            if request is not None:
                lines.append(f"• {html.escape(name)} — {_price_million(float(request))} за запрос")
            else:
                lines.append(
                    f"• {html.escape(name)} — {_price_million(inp)} in / {_price_million(out)} out"
                )
    return lines


def _faq_models_lines(products: list[dict], api_base: str) -> list[str]:
    grouped: dict[str, list[str]] = {}
    total = 0
    for item in products:
        name = str(item.get("model_name") or "").strip()
        if not name:
            continue
        provider = _model_provider(name)
        grouped.setdefault(provider, []).append(name)
        total += 1
    order = ("openai", "anthropic", "google", "grok", "deepseek", "meta", "other")
    lines = [
        "Через один ключ доступны все поддерживаемые модели.\n"
        "Укажите идентификатор модели в поле <code>model</code> запроса к API:\n"
    ]
    shown = 0
    max_models = 40
    for provider in order:
        names = grouped.get(provider) or []
        if not names:
            continue
        remaining = max_models - shown
        if remaining <= 0:
            break
        chunk = names[:remaining]
        shown += len(chunk)
        labels = ", ".join(f"<code>{html.escape(name)}</code>" for name in chunk)
        lines.append(f"\n{_provider_title(provider)}:\n{labels}")
    if total > shown:
        lines.append(f"\n…и ещё {total - shown} моделей. Полный каталог — команда /catalog")
    endpoint = html.escape(api_base.rstrip("/"))
    lines.append(
        f"\n<b>Как обратиться к модели</b>\n"
        f"POST <code>{endpoint}/chat/completions</code>\n"
        "Authorization: <code>Bearer &lt;ваш_ключ&gt;</code>\n"
        'Тело: <code>{"model": "gpt-4o", "messages": [...]}</code>\n\n'
        "Для Claude: <code>POST .../messages</code> с тем же ключом.\n"
        "Список моделей: <code>GET .../models</code>"
    )
    return lines


def _fit_caption(text: str, limit: int = 950) -> str:
    if len(text) <= limit:
        return text
    trimmed = text[: limit - 1].rsplit("\n", 1)[0]
    return trimmed + "\n…"


def _faq_answer(
    topic: str,
    profile: dict,
    products: list[dict] | None = None,
) -> tuple[str, InlineKeyboardMarkup]:
    support = _support_tag(profile)
    api_base = str(profile.get("api_base_url") or "https://router.cheap/v1").strip()
    items = products or []

    if topic == "topup":
        text = (
            "💳 <b>Как пополнить баланс?</b>\n\n"
            "1️⃣ Нажмите «Пополнить баланс» в главном меню\n"
            "2️⃣ Выберите сумму ($10, $25, $50, $100) или введите свою\n"
            "3️⃣ Оплатите картой (Visa, MasterCard, МИР) или через СБП\n"
            "4️⃣ Баланс зачислится автоматически\n\n"
            "💵 Минимальная сумма пополнения: $10\n"
            "📊 Курс покупки показывается и вы принимаете перед оплатой"
        )
    elif topic == "key":
        text = (
            "🔑 <b>Как получить API-ключ?</b>\n\n"
            "1️⃣ Пополните баланс (минимум $10)\n"
            "2️⃣ Откройте «🔑 Мой ключ» → «Создать ключ»\n"
            "3️⃣ Скопируйте ключ и адрес API"
        )
    elif topic == "price":
        price_lines = _faq_price_lines(items)
        body = "\n".join(price_lines) if price_lines else "Каталог цен временно недоступен."
        text = (
            "💰 <b>Какая цена у токенов?</b>\n\n"
            "Цена токенов соответствует официальным ценам провайдеров без наценки. "
            "Вы платите только за токены.\n\n"
            "Актуальные цены за 1 миллион токенов на популярные модели:\n\n"
            f"{body}\n\n"
            "💡 Актуальные цены всегда можно посмотреть в разделе «🔑 Мой ключ»."
        )
    elif topic == "models":
        if items:
            text = "🤖 <b>Какие модели доступны?</b>\n\n" + "\n".join(
                _faq_models_lines(items, api_base)
            )
        else:
            text = (
                "🤖 <b>Какие модели доступны?</b>\n\n"
                "Через один ключ доступны все поддерживаемые модели.\n"
                "Укажите идентификатор модели в поле <code>model</code> запроса к API.\n\n"
                f"Endpoint: <code>{html.escape(api_base.rstrip('/'))}/chat/completions</code>\n"
                "Список моделей: <code>GET .../models</code>"
            )
    elif topic == "safe":
        text = (
            "🔒 <b>Безопасно ли это?</b>\n\n"
            "✅ Ваш ключ хранится в зашифрованном виде\n"
            "✅ Мы не имеем доступа к содержимому ваших запросов\n"
            "✅ Все платежи через сертифицированный платёжный шлюз ЮKassa (защита 3D Secure)\n"
            "✅ Мы не передаём ваши данные третьим лицам\n"
            "✅ Вы можете отозвать любой ключ в любой момент\n"
            "✅ Все операции логируются для разрешения споров"
        )
    elif topic == "billing":
        text = (
            "⚡ <b>Как списываются токены?</b>\n\n"
            "Списание происходит в реальном времени:\n\n"
            "1️⃣ Вы отправляете запрос к API\n"
            "2️⃣ Прокси-сервер обрабатывает запрос и передаёт его провайдеру\n"
            "3️⃣ Провайдер возвращает ответ и количество токенов (usage)\n"
            "4️⃣ Прокси списывает стоимость с вашего баланса\n\n"
            "📊 Проверить историю списаний можно в разделе «История транзакций».\n\n"
            "🔔 Вы можете включить уведомления о каждой операции в разделе «🔔 Уведомления»."
        )
    elif topic == "refund":
        text = (
            "🔄 <b>Можно ли вернуть деньги?</b>\n\n"
            "Возврат неизрасходованного баланса возможен через обращение в поддержку.\n\n"
            "📋 <b>Условия возврата:</b>\n"
            "• Возврат только на ту же карту, с которой производилась оплата\n"
            "• Возврат возможен в течение 14 дней с момента пополнения\n"
            "• Баланс не должен быть израсходован\n\n"
            f"📞 Для возврата свяжитесь с поддержкой: {support}"
        )
    elif topic == "support":
        text = (
            "📞 <b>Как связаться с поддержкой?</b>\n\n"
            f"💬 Telegram: {support}\n"
            "⏰ Время работы: Пн–Пт, 10:00–22:00 (МСК)\n"
            "⏱ Среднее время ответа: до 24 часов"
        )
    elif topic == "broken":
        endpoint = html.escape(api_base.rstrip("/"))
        text = (
            "🚫 <b>Что делать, если ключ не работает?</b>\n\n"
            "Проверьте следующее:\n\n"
            "1️⃣ 💰 Баланс больше нуля?\n"
            "   → Проверьте в «Главное меню»\n\n"
            "2️⃣ ✅ Ключ активен?\n"
            "   → Проверьте статус в «🔑 Мой ключ»\n\n"
            "3️⃣ 🎯 Лимит ключа не исчерпан?\n"
            "   → Проверьте остаток в «🔑 Мой ключ»\n\n"
            f"4️⃣ 🌐 Правильный эндпоинт?\n"
            f"   → <code>{endpoint}</code>\n\n"
            "5️⃣ 🔀 Правильный формат запроса?\n"
            "   → См. «📖 Инструкция»\n\n"
            f"Если всё проверено и ключ не работает — обратитесь в поддержку: {support}"
        )
    else:
        text = "❓ <b>Часто задаваемые вопросы</b>"
        return _faq_list_screen()
    return text, _faq_nav()


def _notify_icon(enabled: bool) -> str:
    return "✅" if enabled else "❌"


def _notify_state(enabled: bool) -> str:
    return "ВКЛ" if enabled else "ВЫКЛ"


def _notifications_screen(prefs: dict) -> tuple[str, InlineKeyboardMarkup]:
    spend = bool(prefs.get("spend"))
    low = bool(prefs.get("low_balance"))
    limit = bool(prefs.get("limit_exhausted"))
    topup = True
    text = (
        "🔔 <b>Настройки уведомлений</b>\n\n"
        "Выберите, какие уведомления получать:\n\n"
        f"{_notify_icon(spend)} Каждая трата\n"
        f"{_notify_icon(low)} Низкий баланс &lt; $5\n"
        f"{_notify_icon(limit)} Лимит исчерпан\n"
        f"{_notify_icon(topup)} Пополнение баланса"
    )
    rows = [
        [_button(f"{_notify_icon(spend)} Каждая трата: {_notify_state(spend)}", callback="notif:t:spend")],
        [_button(f"{_notify_icon(low)} Низкий баланс: {_notify_state(low)}", callback="notif:t:low_balance")],
        [_button(f"{_notify_icon(limit)} Лимит исчерпан: {_notify_state(limit)}", callback="notif:t:limit_exhausted")],
        [_button(f"✅ Пополнение: ВКЛ", callback="notif:t:topup")],
        [_button("🏠 Главное меню", callback="cabinet")],
    ]
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def _support_screen(profile: dict) -> tuple[str, InlineKeyboardMarkup]:
    support = _support_tag(profile)
    text = (
        "📞 <b>Поддержка</b>\n\n"
        f"💬 Telegram: {support}\n"
        "⏰ Время работы: Пн–Пт, 10:00–22:00 (МСК)\n"
        "⏱ Среднее время ответа: до 24 часов\n\n"
        "💡 Перед обращением рекомендуем проверить раздел «FAQ» — "
        "возможно, ответ уже есть там."
    )
    rows = [
        [
            _button("❓ FAQ", callback="faq"),
            _button("🏠 Главное меню", callback="cabinet"),
        ]
    ]
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def _history_short_when(value: str) -> str:
    if not value:
        return "— — —"
    moment = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(_MSK)
    return moment.strftime("%d.%m %H:%M")


def _tokens_short(count: int) -> str:
    value = int(count or 0)
    if value >= 1_000_000:
        text = f"{value / 1_000_000:.1f}M"
        return text.replace(".0M", "M")
    if value >= 1000:
        text = f"{value / 1000:.1f}K"
        return text.replace(".0K", "K")
    return str(value)


def _history_amount(value: float, *, income: bool) -> str:
    amount = abs(float(value or 0))
    if income:
        return f"+{_usd(amount)}"
    if amount >= 0.01:
        return f"-{_usd(amount)}"
    return f"-${amount:.4f}"


def _history_desc(item: dict) -> str:
    if item.get("entry_type") == "income":
        label = html.escape(str(item.get("label") or "Пополнение"))
        rub = float(item.get("amount_rub") or 0)
        if str(item.get("kind") or "") == "topup" and rub > 0:
            return f"{label} ({rub:.0f} ₽)"
        return label
    model = html.escape(str(item.get("model") or "—"))
    prompt = int(item.get("prompt_tokens") or 0)
    completion = int(item.get("completion_tokens") or 0)
    if prompt or completion:
        return f"{model} ({_tokens_short(prompt)} in / {completion} out)"
    return model


def _history_line(item: dict) -> str:
    income = item.get("entry_type") == "income"
    icon = "📥" if income else "📤"
    when = _history_short_when(str(item.get("created_at") or ""))
    amount = _history_amount(float(item.get("amount_usd") or 0), income=income)
    desc = _history_desc(item)
    return f"{icon} {when}  {amount}  {desc}"


def _history_markup(data: dict) -> InlineKeyboardMarkup:
    items = data.get("items") or []
    filter_kind = str(data.get("filter") or "all")
    rows: list[list[InlineKeyboardButton]] = []
    top: list[InlineKeyboardButton] = []
    if data.get("has_more"):
        top.append(
            _button("📊 Показать ещё", callback=f"hist:l:{len(items) + 5}:{filter_kind}")
        )
    top.append(_button("🔍 Фильтр", callback=f"hist:filter:{filter_kind}"))
    rows.append(top)
    rows.append([_button("🏠 Главное меню", callback="cabinet")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _history_screen(data: dict) -> tuple[str, InlineKeyboardMarkup]:
    items = data.get("items") or []
    offset = int(data.get("offset") or 0)
    if not items and offset == 0:
        if not data.get("has_any", True):
            text = (
                "📊 <b>История транзакций</b>\n\n"
                "Транзакций пока нет 📭\n\n"
                "После первого пополнения и использования API здесь появится "
                "детализация ваших операций."
            )
            return text, InlineKeyboardMarkup(
                inline_keyboard=[[_button("🏠 Главное меню", callback="cabinet")]]
            )
        filter_kind = str(data.get("filter") or "all")
        if filter_kind != "all":
            labels = {"income": "пополнений", "spend": "списаний"}
            text = (
                "📊 <b>История транзакций</b>\n\n"
                f"Операций типа «{labels.get(filter_kind, filter_kind)}» пока нет 📭"
            )
            return text, _history_markup(data)
    lines = ["📊 <b>История транзакций</b>\n"]
    lines.extend(_history_line(item) for item in items)
    return "\n\n".join(lines), _history_markup(data)


def _history_filter_screen(active: str = "all") -> tuple[str, InlineKeyboardMarkup]:
    text = "🔍 <b>Фильтр транзакций</b>"
    rows = [
        [
            _button("📋 Все", callback="hist:f:all"),
            _button("📥 Пополнения", callback="hist:f:income"),
            _button("📤 Списания", callback="hist:f:spend"),
        ],
        [_button("⬅️ Назад", callback=f"hist:b:{active}")],
    ]
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def _topup_screen(profile: dict) -> tuple[str, InlineKeyboardMarkup]:
    price = float(profile.get("usd_price_rub") or 0)
    text = (
        "💳 Чтобы пополнить баланс, выберите нужную сумму по кнопке "
        "или напишите сумму в рублях\n\n"
        "Минимальная сумма: $10\n"
        f"Курс: 1 $ = {price:.2f} ₽"
    )
    rows = [
        [_button("$10", callback="topup:usd:10"), _button("$25", callback="topup:usd:25")],
        [_button("$50", callback="topup:usd:50"), _button("$100", callback="topup:usd:100")],
        [_button("⬅️ Назад", callback="cabinet")],
    ]
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


async def _process_topup_rub(
    amount_rub: float,
    profile: dict,
    user_id: int,
    state: FSMContext,
) -> tuple[str, InlineKeyboardMarkup, bool]:
    """Показывает подтверждение. Оплата создаётся по кнопке «Оплатить»."""
    price = float(profile.get("usd_price_rub") or 0)
    amount_usd = _rub_to_usd(amount_rub, price)
    await state.update_data(amount_rub=amount_rub)
    await state.set_state(Topup.confirm)
    text, markup = _pay_confirm_screen(amount_rub, amount_usd, price)
    return text, markup, False


def _rub_to_usd(amount_rub: float, price_rub: float) -> float:
    amount = Decimal(str(amount_rub)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    price = Decimal(str(price_rub))
    if price <= 0:
        return 0.0
    return float((amount / price).quantize(Decimal("0.01"), rounding=ROUND_DOWN))


def _payment_success_screen(
    profile: dict,
    amount_usd: float,
    balance_usd: float,
) -> tuple[str, InlineKeyboardMarkup]:
    text = (
        "✅ <b>Оплата прошла успешно!</b>\n\n"
        f"💵 Зачислено: <b>{_usd(amount_usd)}</b>\n"
        f"💰 Текущий баланс: <b>{_usd(balance_usd)}</b>"
    )
    key_label = "🔑 Мой ключ" if profile.get("has_key") else "🔑 Создать ключ"
    rows = [
        [
            _button(key_label, callback="keys"),
            _button("🏠 Главное меню", callback="cabinet"),
        ]
    ]
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def _pay_confirm_text(amount_rub: float, amount_usd: float, price_rub: float) -> str:
    return (
        "💳 <b>Подтверждение пополнения</b>\n\n"
        f"💵 Сумма: <b>{_usd(amount_usd)}</b>\n"
        f"📊 Курс: 1 $ = {price_rub:.2f} ₽\n"
        f"💰 К оплате: <b>{amount_rub:.2f} ₽</b>\n\n"
        "💳 Оплата: МИР, СБП, TPay, SberPay\n\n"
        "После оплаты баланс пополнится автоматически.\n"
        "Если API-ключ уже выпущен, лимит увеличится на сумму пополнения "
        "(если не установлено ограничение расхода на ключ — в таком случае его нужно будет вручную)."
    )


def _pay_confirm_screen(amount_rub: float, amount_usd: float, price_rub: float) -> tuple[str, InlineKeyboardMarkup]:
    rows = [
        [_button("💳 Оплатить", callback="topup:pay", green=True)],
        [
            _button("✏️ Изменить сумму", callback="topup:edit"),
            _button("⬅️ Назад", callback="cabinet"),
        ],
    ]
    return _pay_confirm_text(amount_rub, amount_usd, price_rub), InlineKeyboardMarkup(inline_keyboard=rows)


def _pay_screen(created: dict, price_rub: float) -> tuple[str, InlineKeyboardMarkup]:
    amount_rub = float(created["amount_rub"])
    amount_usd = float(created["amount_usd"])
    text = _pay_confirm_text(amount_rub, amount_usd, price_rub)
    rows = [
        [_button("💳 Оплатить", url=str(created["pay_url"]), green=True)],
        [_button("⬅️ Назад", callback="cabinet")],
    ]
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def _empty_balance_screen() -> tuple[str, InlineKeyboardMarkup]:
    text = (
        "⛔ <b>Недостаточно средств на балансе</b>\n\n"
        "Для создания API-ключа необходимо пополнить баланс"
    )
    rows = [
        [
            _button("💳 Пополнить баланс", callback="topup", green=True),
            _button("🏠 Главное меню", callback="cabinet"),
        ]
    ]
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def _token_screen(key: dict) -> tuple[str, InlineKeyboardMarkup]:
    secret = str(key.get("secret") or "")
    shown = html.escape(_mask_key(secret)) if secret else "—"
    spent = float(key.get("spent_usd") or 0)
    limit = float(key.get("limit_usd") or key.get("balance_usd") or 0)
    remain = float(key.get("quota_usd") or key.get("balance_usd") or 0)
    prompt = int(key.get("prompt_tokens") or 0)
    completion = int(key.get("completion_tokens") or 0)
    text = (
        f"🔑 Ключ: <code>{shown}</code>\n"
        f"💸 Потрачено: <b>{_usd(spent)}</b> / <b>{_usd(limit)}</b>\n"
        f"💰 Остаток лимита: <b>{_usd(remain)}</b>\n"
        f"📈 Токенов: <b>{prompt}</b> in / <b>{completion}</b> out\n"
        f"🕒 Последний запрос: {_ago(str(key.get('last_request_at') or ''))}\n"
        f"📅 Создан: {_date_short(str(key.get('created_at') or ''))}"
    )
    rows = [
        [
            _button("📊 Статистика", callback="key:stats"),
            _button("📋 История по ключу", callback="key:history"),
        ],
        [_button("⬅️ Назад", callback="cabinet")],
    ]
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def _key_stats_screen(profile: dict, key: dict) -> tuple[str, InlineKeyboardMarkup]:
    week = key.get("spent_week_usd") or profile.get("spent_week_usd") or []
    text = (
        "<b>📊 Статистика ключа</b>\n\n"
        f"💸 Потрачено: <b>{_usd(float(key.get('spent_usd') or 0))}</b> / "
        f"<b>{_usd(float(key.get('limit_usd') or 0))}</b>\n"
        f"💰 Остаток: <b>{_usd(float(key.get('quota_usd') or 0))}</b>\n"
        f"Сегодня: {_spent(float(key.get('spent_today_usd') or profile.get('spent_today_usd') or 0))}\n"
        f"За месяц: {_spent(float(key.get('spent_month_usd') or profile.get('spent_month_usd') or 0))}\n\n"
        f"{_week_chart(week if isinstance(week, list) else [])}"
    )
    rows = [[_button("⬅️ Назад", callback="keys")]]
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def _key_history_line(item: dict) -> str:
    when = _history_short_when(str(item.get("created_at") or ""))
    amount = _history_amount(float(item.get("amount_usd") or 0), income=False)
    model = html.escape(str(item.get("model") or "—"))
    return f"📤 {when}  {amount}  {model}"


def _key_history_screen(data: dict) -> tuple[str, InlineKeyboardMarkup]:
    items = data.get("items") or []
    offset = int(data.get("offset") or 0)
    key_name = html.escape(str(data.get("key_name") or "API-ключ"))
    total_requests = int(data.get("total_requests") or 0)
    total_usd = float(data.get("total_usd") or 0)
    if not items and offset == 0:
        text = (
            f"📊 <b>История по ключу:</b> «{key_name}»\n\n"
            "Пока нет запросов. После первого обращения к API они появятся здесь."
        )
        return text, InlineKeyboardMarkup(inline_keyboard=[[_button("⬅️ Назад", callback="keys")]])
    lines = [f"📊 <b>История по ключу:</b> «{key_name}»\n"]
    lines.extend(_key_history_line(item) for item in items)
    lines.append("")
    lines.append(f"🔢 Всего: {total_requests} запросов на {_spent(total_usd)}")
    rows: list[list[InlineKeyboardButton]] = []
    if data.get("has_more"):
        rows.append([_button("📊 Показать ещё", callback=f"key:hist:l:{len(items) + 5}")])
    rows.append([_button("⬅️ Назад", callback="keys")])
    return "\n\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)


def _chunks(text: str, limit: int = 900) -> list[str]:
    parts: list[str] = []
    current = ""
    for line in text.split("\n"):
        piece = line if not current else f"{current}\n{line}"
        if len(piece) > limit and current:
            parts.append(current)
            current = line
        else:
            current = piece
    if current:
        parts.append(current)
    return parts


async def _profile_of(user_id: int, username: str, first_name: str) -> dict:
    await upsert_user(user_id, username, first_name)
    return await get_user(user_id)


def _plain(markup: InlineKeyboardMarkup) -> InlineKeyboardMarkup:
    rows = []
    for row in markup.inline_keyboard:
        rows.append(
            [
                InlineKeyboardButton(
                    text=button.text,
                    callback_data=button.callback_data,
                    url=button.url,
                    copy_text=button.copy_text,
                )
                for button in row
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _photo(scene: str) -> FSInputFile:
    name = "welcome-banner" if scene == "welcome" else scene
    return FSInputFile(_IMAGES / f"{name}.png")


def _media(scene: str, text: str) -> InputMediaPhoto:
    return InputMediaPhoto(media=_photo(scene), caption=text, parse_mode=ParseMode.HTML)


async def _say(message: Message, text: str) -> Message:
    return await message.answer_photo(_photo("notice"), caption=text)


async def _deliver(message: Message, scene: str, text: str, markup: InlineKeyboardMarkup) -> Message:
    try:
        return await message.answer_photo(_photo(scene), caption=text, reply_markup=markup)
    except TelegramBadRequest:
        return await message.answer_photo(_photo(scene), caption=text, reply_markup=_plain(markup))


async def _edit(message: Message, scene: str, text: str, markup: InlineKeyboardMarkup) -> None:
    try:
        await message.edit_media(media=_media(scene, text), reply_markup=markup)
    except TelegramBadRequest as exc:
        if "not modified" in str(exc).lower():
            return
        try:
            await message.edit_media(media=_media(scene, text), reply_markup=_plain(markup))
        except TelegramBadRequest:
            await _deliver(message, scene, text, markup)


async def _open(message: Message, scene: str, text: str, markup: InlineKeyboardMarkup) -> Message:
    hidden = await message.answer("\u2060", reply_markup=ReplyKeyboardRemove())
    try:
        await hidden.delete()
    except TelegramBadRequest:
        pass
    return await _deliver(message, scene, text, markup)


async def _show_callback(query: CallbackQuery, scene: str, text: str, markup: InlineKeyboardMarkup) -> None:
    await query.answer()
    if query.message is not None:
        await _edit(query.message, scene, text, markup)


async def _remember_screen(state: FSMContext, message: Message) -> None:
    await state.set_state(Topup.amount)
    await state.update_data(screen_chat_id=message.chat.id, screen_message_id=message.message_id)


async def _replace_saved_screen(
    message: Message,
    state: FSMContext,
    scene: str,
    text: str,
    markup: InlineKeyboardMarkup,
) -> None:
    data = await state.get_data()
    edited = False
    chat_id = data.get("screen_chat_id")
    message_id = data.get("screen_message_id")
    if chat_id and message_id:
        try:
            await message.bot.edit_message_media(
                media=_media(scene, text),
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=markup,
            )
            edited = True
        except TelegramBadRequest:
            edited = False
    if not edited:
        await _deliver(message, scene, text, markup)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, command: CommandObject) -> None:
    await state.clear()
    user = message.from_user
    if user is None:
        return
    try:
        profile = await _profile_of(user.id, user.username or "", user.first_name or "")
    except BackendError:
        await _say(message, UNAVAILABLE)
        return
    payload = (command.args or "").strip()
    if payload.startswith("paid_"):
        raw = payload.removeprefix("paid_")
        if raw.isdigit():
            paid = await _payment_return(user.id, int(raw))
            try:
                profile = await get_user(user.id)
            except BackendError:
                pass
            if paid.get("status") == "paid":
                text, markup = _payment_success_screen(
                    profile,
                    float(paid.get("amount_usd") or 0),
                    float(paid.get("balance_usd") or profile.get("balance_usd") or 0),
                )
                await _open(message, "pay", text, markup)
                return
            if paid.get("notice"):
                await _say(message, paid["notice"])
                return
    if profile.get("blocked"):
        text, markup = _blocked_screen(profile)
        await _open(message, "welcome", text, markup)
        return
    if not profile["offer_accepted"]:
        text, markup = _offer_screen(profile)
        await _open(message, "offer", text, markup)
        return
    text, markup = _welcome_screen(profile)
    await _open(message, "welcome", text, markup)


async def _payment_return(telegram_id: int, topup_id: int) -> dict:
    try:
        result = await check_topup(telegram_id, topup_id)
    except BackendError:
        return {"notice": "Не удалось проверить платёж."}
    status = str(result.get("status") or "")
    if status == "paid":
        return {
            "status": "paid",
            "amount_usd": float(result.get("amount_usd") or 0),
            "balance_usd": float(result.get("balance_usd") or 0),
        }
    if status in {"rejected", "failed"}:
        return {"notice": "Платёж не прошёл."}
    return {"notice": "Платёж ещё не подтверждён. Баланс обновится, когда оплата дойдёт."}


@router.callback_query(F.data == "offer:yes")
async def accept(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = query.from_user
    try:
        await upsert_user(user.id, user.username or "", user.first_name or "")
        await accept_offer(user.id)
        profile = await get_user(user.id)
    except BackendError as exc:
        await query.answer(_explain(exc), show_alert=True)
        return
    text, markup = _welcome_screen(profile, just_accepted=True)
    await _show_callback(query, "welcome", text, markup)


@router.callback_query(F.data == "cabinet")
async def cabinet(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = query.from_user
    try:
        profile = await _profile_of(user.id, user.username or "", user.first_name or "")
    except BackendError:
        await query.answer(UNAVAILABLE, show_alert=True)
        return
    if profile.get("blocked"):
        text, markup = _blocked_screen(profile)
        await _show_callback(query, "welcome", text, markup)
        return
    if not profile["offer_accepted"]:
        text, markup = _offer_screen(profile)
        await _show_callback(query, "offer", text, markup)
        return
    text, markup = _welcome_screen(profile)
    await _show_callback(query, "welcome", text, markup)


@router.callback_query(F.data == "keys")
async def keys_open(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = query.from_user
    try:
        profile = await _profile_of(user.id, user.username or "", user.first_name or "")
    except BackendError:
        await query.answer(UNAVAILABLE, show_alert=True)
        return
    if profile.get("has_key"):
        await _show_token(query)
        return
    if float(profile.get("balance_usd") or 0) <= 0:
        text, markup = _empty_balance_screen()
        await _show_callback(query, "empty", text, markup)
        return
    await query.answer()
    try:
        created = await issue_key(user.id)
    except BackendError as exc:
        await query.answer(_explain(exc), show_alert=True)
        return
    text, markup = _token_screen(created)
    if query.message is not None:
        await _edit(query.message, "token", text, markup)


@router.callback_query(F.data == "history")
async def history_open(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        data = await get_history(query.from_user.id)
    except BackendError:
        await query.answer(UNAVAILABLE, show_alert=True)
        return
    text, markup = _history_screen(data)
    await _show_callback(query, "cabinet", text, markup)


@router.callback_query(F.data.startswith("hist:"))
async def history_actions(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    parts = (query.data or "").split(":")
    action = parts[1] if len(parts) > 1 else ""
    if action == "filter":
        active = parts[2] if len(parts) > 2 else "all"
        text, markup = _history_filter_screen(active)
        await _show_callback(query, "cabinet", text, markup)
        return
    if action == "f" and len(parts) > 2:
        filter_kind = parts[2]
        try:
            data = await get_history(query.from_user.id, filter=filter_kind, offset=0)
        except BackendError:
            await query.answer(UNAVAILABLE, show_alert=True)
            return
        text, markup = _history_screen(data)
        await _show_callback(query, "cabinet", text, markup)
        return
    if action == "b" and len(parts) > 2:
        filter_kind = parts[2]
        try:
            data = await get_history(query.from_user.id, filter=filter_kind, offset=0)
        except BackendError:
            await query.answer(UNAVAILABLE, show_alert=True)
            return
        text, markup = _history_screen(data)
        await _show_callback(query, "cabinet", text, markup)
        return
    if action == "l" and len(parts) > 3:
        limit = int(parts[2])
        filter_kind = parts[3]
        try:
            data = await get_history(query.from_user.id, filter=filter_kind, offset=0, limit=limit)
        except BackendError:
            await query.answer(UNAVAILABLE, show_alert=True)
            return
        text, markup = _history_screen(data)
        await _show_callback(query, "cabinet", text, markup)
        return
    await query.answer()


@router.callback_query(F.data == "faq")
async def faq_open(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    text, markup = _faq_list_screen()
    await _show_callback(query, "cabinet", text, markup)


@router.callback_query(F.data.startswith("faq:q:"))
async def faq_question(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    parts = (query.data or "").split(":")
    topic = parts[2] if len(parts) > 2 else ""
    user = query.from_user
    try:
        profile = await _profile_of(user.id, user.username or "", user.first_name or "")
    except BackendError:
        await query.answer(UNAVAILABLE, show_alert=True)
        return
    products: list[dict] = []
    if topic in {"price", "models"}:
        try:
            products = await list_products()
        except BackendError:
            products = []
    if topic not in {item[0] for item in _FAQ_TOPICS}:
        text, markup = _faq_list_screen()
    else:
        text, markup = _faq_answer(topic, profile, products)
        if topic == "models":
            text = _fit_caption(text)
    await _show_callback(query, "cabinet", text, markup)


@router.callback_query(F.data == "notifications")
async def notifications_open(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = query.from_user
    try:
        profile = await _profile_of(user.id, user.username or "", user.first_name or "")
    except BackendError:
        await query.answer(UNAVAILABLE, show_alert=True)
        return
    text, markup = _notifications_screen(profile.get("notifications") or {})
    await _show_callback(query, "cabinet", text, markup)


@router.callback_query(F.data.startswith("notif:t:"))
async def notifications_toggle(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    parts = (query.data or "").split(":")
    key = parts[2] if len(parts) > 2 else ""
    if key == "topup":
        await query.answer("Уведомления о пополнении нельзя отключить.", show_alert=True)
        return
    user = query.from_user
    try:
        result = await toggle_notification(user.id, key)
    except BackendError:
        await query.answer(UNAVAILABLE, show_alert=True)
        return
    prefs = result.get("notifications") or {}
    text, markup = _notifications_screen(prefs)
    await _show_callback(query, "cabinet", text, markup)


@router.callback_query(F.data == "support")
async def support_open(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = query.from_user
    try:
        profile = await _profile_of(user.id, user.username or "", user.first_name or "")
    except BackendError:
        await query.answer(UNAVAILABLE, show_alert=True)
        return
    text, markup = _support_screen(profile)
    await _show_callback(query, "cabinet", text, markup)


@router.callback_query(F.data == "guide")
async def guide(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    text, rows = apps_screen()
    await _show_callback(query, "catalog", text, _markup(rows))


@router.callback_query(F.data.startswith("guide:"))
async def guide_pick(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    parts = (query.data or "").split(":")
    if len(parts) == 3 and parts[1] == "a" and known_app(parts[2]):
        app_id = parts[2]
        if app_id == "other":
            text, rows = other_screen()
        else:
            screen = os_screen(app_id)
            if screen is None:
                await query.answer("Такой программы нет.", show_alert=True)
                return
            text, rows = screen
        await _show_callback(query, "catalog", text, _markup(rows))
        return
    if len(parts) == 4 and parts[1] == "s":
        origin = ""
        try:
            profile = await get_user(query.from_user.id)
            origin = _site(profile)
        except BackendError:
            origin = ""
        token = ""
        try:
            key = await read_key(query.from_user.id)
            token = str(key.get("secret") or "")
        except BackendError:
            token = ""
        screen = steps_screen(parts[2], parts[3], origin, token)
        if screen is None:
            await query.answer("Такой инструкции нет.", show_alert=True)
            return
        text, rows = screen
        await _show_callback(query, "catalog", text, _markup(rows))
        return
    await query.answer("Такой инструкции нет.", show_alert=True)


@router.callback_query(F.data == "topup")
async def topup_open(query: CallbackQuery, state: FSMContext) -> None:
    user = query.from_user
    try:
        profile = await _profile_of(user.id, user.username or "", user.first_name or "")
    except BackendError:
        await query.answer(UNAVAILABLE, show_alert=True)
        return
    if not profile["offer_accepted"]:
        await query.answer("Сначала примите все условия.", show_alert=True)
        return
    if profile.get("blocked"):
        await query.answer(_explain(BackendError(403, "blocked")), show_alert=True)
        return
    if float(profile.get("usd_price_rub") or 0) <= 0:
        await query.answer(_explain(BackendError(402, "sales-closed")), show_alert=True)
        return
    text, markup = _topup_screen(profile)
    await _show_callback(query, "topup", text, markup)
    if query.message is not None:
        await _remember_screen(state, query.message)


@router.message(Topup.amount)
async def topup_amount(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().replace(",", ".")
    if raw.lower() in {"/cancel", "отмена"}:
        await cabinet_from_message(message, state)
        return
    try:
        amount = float(raw)
    except ValueError:
        await _say(message, "Нужно число в рублях, например 500.")
        return
    if message.from_user is None:
        return
    try:
        profile = await get_user(message.from_user.id)
    except BackendError as exc:
        await _say(message, _explain(exc))
        return
    if profile.get("blocked"):
        await _say(message, _explain(BackendError(403, "blocked")))
        return
    min_rub = float(profile.get("min_topup_rub") or 0)
    if min_rub > 0 and amount < min_rub:
        await _say(message, "Минимальная сумма пополнения — 10 $.")
        return
    try:
        text, markup, clear = await _process_topup_rub(amount, profile, message.from_user.id, state)
    except BackendError as exc:
        await state.clear()
        await _say(message, _explain(exc))
        return
    await _replace_saved_screen(message, state, "pay", text, markup)
    if clear:
        await state.clear()


@router.callback_query(F.data.startswith("topup:usd:"))
async def topup_preset(query: CallbackQuery, state: FSMContext) -> None:
    raw = (query.data or "").rsplit(":", 1)[-1]
    try:
        usd = float(raw)
    except ValueError:
        await query.answer("Неверная сумма.", show_alert=True)
        return
    user = query.from_user
    try:
        profile = await _profile_of(user.id, user.username or "", user.first_name or "")
    except BackendError:
        await query.answer(UNAVAILABLE, show_alert=True)
        return
    if not profile["offer_accepted"]:
        await query.answer("Сначала примите все условия.", show_alert=True)
        return
    if profile.get("blocked"):
        await query.answer(_explain(BackendError(403, "blocked")), show_alert=True)
        return
    price = float(profile.get("usd_price_rub") or 0)
    if price <= 0:
        await query.answer(_explain(BackendError(402, "sales-closed")), show_alert=True)
        return
    amount_rub = float(
        (Decimal(str(usd)) * Decimal(str(price))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )
    min_rub = float(profile.get("min_topup_rub") or 0)
    if min_rub > 0 and amount_rub < min_rub:
        await query.answer("Минимальная сумма пополнения — 10 $.", show_alert=True)
        return
    await query.answer()
    try:
        text, markup, clear = await _process_topup_rub(amount_rub, profile, user.id, state)
    except BackendError as exc:
        await query.answer(_explain(exc), show_alert=True)
        return
    if clear:
        await state.clear()
    if query.message is not None:
        await _edit(query.message, "pay", text, markup)


@router.callback_query(F.data == "topup:pay")
async def topup_pay(query: CallbackQuery, state: FSMContext) -> None:
    user = query.from_user
    data = await state.get_data()
    amount = data.get("amount_rub")
    try:
        profile = await _profile_of(user.id, user.username or "", user.first_name or "")
    except BackendError:
        await query.answer(UNAVAILABLE, show_alert=True)
        return
    if not profile.get("yookassa_enabled"):
        await query.answer(_explain(BackendError(402, "no-yookassa")), show_alert=True)
        return
    min_rub = float(profile.get("min_topup_rub") or 0)
    if not isinstance(amount, (int, float)) or (min_rub > 0 and float(amount) < min_rub):
        await query.answer("Минимальная сумма пополнения — 10 $.", show_alert=True)
        return
    await query.answer()
    try:
        created = await create_topup(user.id, float(amount))
    except BackendError as exc:
        if query.message is not None:
            await _say(query.message, _explain(exc))
        return
    price = float(profile.get("usd_price_rub") or 0)
    text, markup = _pay_screen(created, price)
    await state.clear()
    if query.message is not None:
        await _edit(query.message, "pay", text, markup)


@router.callback_query(F.data == "topup:edit")
async def topup_edit(query: CallbackQuery, state: FSMContext) -> None:
    user = query.from_user
    try:
        profile = await _profile_of(user.id, user.username or "", user.first_name or "")
    except BackendError:
        await query.answer(UNAVAILABLE, show_alert=True)
        return
    if float(profile.get("usd_price_rub") or 0) <= 0:
        await query.answer(_explain(BackendError(402, "sales-closed")), show_alert=True)
        return
    text, markup = _topup_screen(profile)
    await state.set_state(Topup.amount)
    await _show_callback(query, "topup", text, markup)
    if query.message is not None:
        await _remember_screen(state, query.message)


@router.callback_query(F.data == "issue")
async def issue(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = query.from_user
    try:
        profile = await _profile_of(user.id, user.username or "", user.first_name or "")
    except BackendError:
        await query.answer(UNAVAILABLE, show_alert=True)
        return
    if profile.get("has_key"):
        await _show_token(query)
        return
    if float(profile["balance_usd"]) <= 0:
        text, markup = _empty_balance_screen()
        await _show_callback(query, "empty", text, markup)
        return
    await query.answer()
    try:
        created = await issue_key(user.id)
    except BackendError as exc:
        if query.message is not None:
            await _say(query.message, _explain(exc))
        return
    text, markup = _token_screen(created)
    if query.message is not None:
        await _edit(query.message, "token", text, markup)


@router.callback_query(F.data == "token")
async def token(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _show_token(query)


async def _show_token(query: CallbackQuery) -> None:
    try:
        key = await read_key(query.from_user.id)
    except BackendError as exc:
        await query.answer(_explain(exc), show_alert=True)
        return
    text, markup = _token_screen(key)
    await _show_callback(query, "token", text, markup)


@router.callback_query(F.data == "key:stats")
async def key_stats_open(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = query.from_user
    try:
        profile = await _profile_of(user.id, user.username or "", user.first_name or "")
        key = await read_key(user.id)
    except BackendError as exc:
        await query.answer(_explain(exc), show_alert=True)
        return
    text, markup = _key_stats_screen(profile, key)
    await _show_callback(query, "token", text, markup)


@router.callback_query(F.data == "key:history")
async def key_history_open(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        data = await get_key_history(query.from_user.id)
    except BackendError as exc:
        await query.answer(_explain(exc), show_alert=True)
        return
    text, markup = _key_history_screen(data)
    await _show_callback(query, "token", text, markup)


@router.callback_query(F.data.startswith("key:hist:l:"))
async def key_history_more(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    parts = (query.data or "").split(":")
    if len(parts) < 4:
        await query.answer()
        return
    try:
        limit = int(parts[3])
        data = await get_key_history(query.from_user.id, offset=0, limit=limit)
    except (BackendError, ValueError):
        await query.answer(UNAVAILABLE, show_alert=True)
        return
    text, markup = _key_history_screen(data)
    await _show_callback(query, "token", text, markup)


@router.callback_query(F.data == "reissue")
async def reissue_ask(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = query.from_user
    try:
        profile = await get_user(user.id)
    except BackendError:
        await query.answer(UNAVAILABLE, show_alert=True)
        return
    text = (
        "<b>Перевыпуск</b>\n\n"
        "Старый токен будет удалён. Новый получит тот же оставшийся лимит "
        f"<b>{_usd(float(profile['balance_usd']))}</b>."
    )
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [_button("Перевыпустить", callback="reissue:yes")],
            _back_row(),
        ]
    )
    await _show_callback(query, "reissue", text, markup)


@router.callback_query(F.data == "reissue:yes")
async def reissue_confirm(query: CallbackQuery) -> None:
    await query.answer()
    try:
        created = await reissue_key(query.from_user.id)
    except BackendError as exc:
        if query.message is not None:
            await _say(query.message, _explain(exc))
        return
    text, markup = _token_screen(created)
    if query.message is not None:
        await _edit(query.message, "token", text, markup)


@router.message(Command("cancel"))
@router.message(F.text.in_({"Баланс", "Пополнить", "Выпустить токен", "Перевыпустить", "Каталог"}))
async def legacy_menu(message: Message, state: FSMContext) -> None:
    text = message.text or ""
    if text == "Пополнить":
        user = message.from_user
        if user is None:
            return
        try:
            profile = await _profile_of(user.id, user.username or "", user.first_name or "")
        except BackendError:
            await _say(message, UNAVAILABLE)
            return
        if not profile["offer_accepted"]:
            body, markup = _offer_screen(profile)
            await _open(message, "offer", body, markup)
            return
        body, markup = _topup_screen(profile)
        sent = await _open(message, "topup", body, markup)
        await _remember_screen(state, sent)
        return
    if text == "Каталог":
        await catalog(message, state)
        return
    await cabinet_from_message(message, state)


async def cabinet_from_message(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    if user is None:
        return
    try:
        profile = await _profile_of(user.id, user.username or "", user.first_name or "")
    except BackendError:
        await _say(message, UNAVAILABLE)
        return
    if profile.get("blocked"):
        text, markup = _blocked_screen(profile)
        await _open(message, "welcome", text, markup)
        return
    if not profile["offer_accepted"]:
        text, markup = _offer_screen(profile)
        await _open(message, "offer", text, markup)
        return
    text, markup = _welcome_screen(profile)
    await _open(message, "welcome", text, markup)


@router.message(Command("catalog"))
async def catalog(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    if user is None:
        return
    try:
        profile = await upsert_user(user.id, user.username or "", user.first_name or "")
    except BackendError:
        await _say(message, UNAVAILABLE)
        return
    if not profile["offer_accepted"]:
        text, markup = _offer_screen(profile)
        await _open(message, "offer", text, markup)
        return
    try:
        items = await list_products()
    except BackendError:
        await _say(message, UNAVAILABLE)
        return
    if not items:
        await _say(message, "Каталог пока пуст.")
        return
    lines = ["Модели, которые открывает токен:\n"]
    for item in items:
        name = html.escape(str(item["model_name"]))
        label = str(item.get("price_label") or "")
        if label:
            lines.append(f"<b>{name}</b> — {html.escape(label)}")
        else:
            lines.append(f"• {name}")
    for part in _chunks("\n".join(lines)):
        await message.answer_photo(_photo("catalog"), caption=part)


@router.message(F.text.startswith("/"), StateFilter(None))
async def unknown_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    if user is None:
        return
    try:
        profile = await _profile_of(user.id, user.username or "", user.first_name or "")
    except BackendError:
        await _say(message, UNAVAILABLE)
        return
    if profile.get("blocked"):
        text, markup = _blocked_screen(profile)
        await _open(message, "welcome", text, markup)
        return
    if not profile["offer_accepted"]:
        text, markup = _offer_screen(profile)
        await _open(message, "offer", text, markup)
        return
    text, markup = _unknown_command_screen(profile)
    await _open(message, "welcome", text, markup)


@router.message(F.text, ~F.text.startswith("/"), StateFilter(None))
async def plain_text(message: Message) -> None:
    user = message.from_user
    if user is None:
        return
    try:
        profile = await _profile_of(user.id, user.username or "", user.first_name or "")
    except BackendError:
        await _say(message, UNAVAILABLE)
        return
    if profile.get("blocked"):
        text, markup = _blocked_screen(profile)
        await _open(message, "welcome", text, markup)
        return
    if not profile["offer_accepted"]:
        text, markup = _offer_screen(profile)
        await _open(message, "offer", text, markup)
        return
    text, markup = _plain_text_screen(profile)
    await _open(message, "welcome", text, markup)


def _user_from_update(update) -> object | None:
    if update.message and update.message.from_user:
        return update.message.from_user
    if update.callback_query and update.callback_query.from_user:
        return update.callback_query.from_user
    return None


async def _send_error_notice(bot: Bot, event: ErrorEvent, text: str, markup: InlineKeyboardMarkup) -> None:
    update = event.update
    if update.callback_query:
        query = update.callback_query
        try:
            await query.answer("Произошла ошибка.", show_alert=True)
        except TelegramBadRequest:
            pass
        if query.message is not None:
            await _deliver(query.message, "notice", text, markup)
            return
    if update.message is not None:
        await _deliver(update.message, "notice", text, markup)
        return
    user = _user_from_update(update)
    if user is not None:
        await bot.send_photo(user.id, _photo("notice"), caption=text, reply_markup=markup)


@router.errors()
async def bot_error(event: ErrorEvent, bot: Bot) -> None:
    log.exception("ошибка бота", exc_info=event.exception)
    user = _user_from_update(event.update)
    profile = None
    if user is not None:
        try:
            profile = await get_user(user.id)
        except BackendError:
            profile = None
    text, markup = _error_screen(profile)
    try:
        await _send_error_notice(bot, event, text, markup)
    except Exception:
        log.exception("не удалось отправить сообщение об ошибке")
