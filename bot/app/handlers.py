import html

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, Message, ReplyKeyboardMarkup

from app.backend import (
    BackendError,
    accept_offer,
    check_topup,
    create_topup,
    get_user,
    issue_key,
    list_products,
    reissue_key,
    upsert_user,
)

router = Router()

MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Баланс"), KeyboardButton(text="Пополнить")],
        [KeyboardButton(text="Выпустить токен"), KeyboardButton(text="Перевыпустить")],
        [KeyboardButton(text="Каталог")],
    ],
    resize_keyboard=True,
)
MENU_TEXTS = {"Баланс", "Пополнить", "Выпустить токен", "Перевыпустить", "Каталог"}
UNAVAILABLE = "Сервис сейчас недоступен. Попробуйте чуть позже."


class Topup(StatesGroup):
    amount = State()


def _usd(value: float) -> str:
    return f"${value:.2f}"


def _explain(exc: BackendError) -> str:
    reasons = {
        "offer": "Сначала примите оферту.",
        "no-offer-url": "Ссылка на оферту ещё не настроена.",
        "balance": "Сначала пополните баланс.",
        "empty": "Лимит нулевой. Сначала пополните баланс.",
        "sales-closed": "Пополнение закрыто: в админке не указана цена доллара.",
        "no-yookassa": "Оплата не настроена.",
        "no-bot": "Не удалось открыть возврат в бота. Проверьте токен бота в настройках.",
        "yookassa": "Платёж сейчас не создаётся. Попробуйте позже.",
        "key-exists": "Токен уже выпущен. Новый секрет делается кнопкой «Перевыпустить».",
        "no-key": "Токена ещё нет. Пополните баланс и нажмите «Выпустить токен».",
        "supplier": "Сейчас нельзя провести операцию: на счёте поставщика не хватает лимита.",
        "reissue-failed": "Старый токен удалён, новый не создался. Лимит сохранён — нажмите «Выпустить токен».",
    }
    if exc.status == 0:
        return UNAVAILABLE
    return reasons.get(exc.detail, UNAVAILABLE)


def _chunks(text: str, limit: int = 3500) -> list[str]:
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


def _offer_text(profile: dict) -> str:
    url = str(profile.get("offer_url") or "")
    if not url:
        return "Ссылка на оферту появится, когда в админке будет указан адрес сайта."
    return (
        "Чтобы пользоваться Aimarket, прочитайте оферту и примите её:\n"
        f"<a href=\"{html.escape(url, quote=True)}\">{html.escape(url)}</a>"
    )


def _offer_keyboard(profile: dict) -> InlineKeyboardMarkup | None:
    if not profile.get("offer_url"):
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Принимаю оферту", callback_data="offer:yes")]]
    )


async def _profile(message: Message) -> dict | None:
    user = message.from_user
    if user is None:
        return None
    try:
        return await upsert_user(user.id, user.username or "", user.first_name or "")
    except BackendError:
        await message.answer(UNAVAILABLE)
        return None


async def _require(message: Message) -> dict | None:
    profile = await _profile(message)
    if profile is None:
        return None
    if not profile["offer_accepted"]:
        await message.answer(_offer_text(profile), reply_markup=_offer_keyboard(profile))
        return None
    return profile


def _secret_text(created: dict) -> str:
    secret = html.escape(str(created["secret"]))
    base = html.escape(str(created["base_url"]))
    limit = _usd(float(created["balance_usd"]))
    return (
        f"Токен выпущен, лимит <b>{limit}</b>.\n"
        "Сохраните его: повторно он не показывается.\n\n"
        f"Адрес API: <code>{base}</code>\n"
        f"Ключ: <code>{secret}</code>"
    )


async def _after_payment(message: Message, topup_id: int, profile: dict) -> None:
    markup = MENU if profile.get("offer_accepted") else _offer_keyboard(profile)
    user = message.from_user
    if user is None:
        return
    try:
        result = await check_topup(user.id, topup_id)
    except BackendError:
        await message.answer(UNAVAILABLE, reply_markup=markup)
        return
    status = str(result.get("status") or "")
    if status == "paid":
        text = f"Оплата прошла. Баланс: <b>{_usd(float(result['balance_usd']))}</b>."
    elif status in {"rejected", "failed"}:
        text = "Платёж не прошёл."
    else:
        text = "Платёж ещё не подтверждён. Через минуту нажмите «Баланс»."
    await message.answer(text, reply_markup=markup)


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, command: CommandObject) -> None:
    await state.clear()
    profile = await _profile(message)
    if profile is None:
        return
    payload = (command.args or "").strip()
    if payload.startswith("paid_"):
        raw = payload.removeprefix("paid_")
        if raw.isdigit():
            await _after_payment(message, int(raw), profile)
            return
    if not profile["offer_accepted"]:
        await message.answer(_offer_text(profile), reply_markup=_offer_keyboard(profile))
        return
    await message.answer("Aimarket. Баланс — это лимит вашего токена.", reply_markup=MENU)


@router.callback_query(F.data == "offer:yes")
async def accept(query: CallbackQuery) -> None:
    user = query.from_user
    try:
        await upsert_user(user.id, user.username or "", user.first_name or "")
        await accept_offer(user.id)
    except BackendError as exc:
        await query.answer(_explain(exc), show_alert=True)
        return
    await query.answer("Оферта принята")
    if query.message is not None:
        await query.message.answer("Оферта принята.", reply_markup=MENU)


@router.message(Command("balance"))
@router.message(F.text == "Баланс")
async def balance(message: Message, state: FSMContext) -> None:
    await state.clear()
    profile = await _require(message)
    if profile is None or message.from_user is None:
        return
    try:
        fresh = await get_user(message.from_user.id)
    except BackendError:
        await message.answer(UNAVAILABLE)
        return
    lines = [f"Баланс: <b>{_usd(float(fresh['balance_usd']))}</b>"]
    if fresh["has_key"]:
        lines.append(f"Токен: <code>{html.escape(str(fresh['key_prefix']))}…</code>")
        lines.append("Остаток сверяется с лимитом ключа.")
    else:
        lines.append("Токен ещё не выпущен.")
    price = float(fresh.get("usd_price_rub") or 0)
    if price > 0:
        lines.append(f"Цена пополнения: {price:.2f} ₽ за $1")
    await message.answer("\n".join(lines))


@router.message(Command("topup"))
@router.message(F.text == "Пополнить")
async def topup_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    profile = await _require(message)
    if profile is None:
        return
    if float(profile.get("usd_price_rub") or 0) <= 0:
        await message.answer(_explain(BackendError(402, "sales-closed")))
        return
    if not profile.get("yookassa_enabled"):
        await message.answer(_explain(BackendError(402, "no-yookassa")))
        return
    await state.set_state(Topup.amount)
    await message.answer("Сумма пополнения в рублях. Например: 500\nОтмена: /cancel")


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.", reply_markup=MENU)


@router.message(F.text == "Выпустить токен")
async def issue_ask(message: Message, state: FSMContext) -> None:
    await state.clear()
    profile = await _require(message)
    if profile is None or message.from_user is None:
        return
    try:
        fresh = await get_user(message.from_user.id)
    except BackendError:
        await message.answer(UNAVAILABLE)
        return
    if fresh["has_key"]:
        await message.answer(_explain(BackendError(409, "key-exists")))
        return
    if float(fresh["balance_usd"]) <= 0:
        await message.answer(_explain(BackendError(402, "balance")))
        return
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Выпустить", callback_data="issue:yes")]]
    )
    await message.answer(
        f"Выпустить токен с лимитом <b>{_usd(float(fresh['balance_usd']))}</b>?",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "issue:yes")
async def issue_confirm(query: CallbackQuery) -> None:
    try:
        created = await issue_key(query.from_user.id)
    except BackendError as exc:
        await query.answer()
        if query.message is not None:
            await query.message.answer(_explain(exc))
        return
    await query.answer("Токен выпущен")
    if query.message is not None:
        await query.message.answer(_secret_text(created))


@router.message(F.text == "Перевыпустить")
async def reissue_ask(message: Message, state: FSMContext) -> None:
    await state.clear()
    profile = await _require(message)
    if profile is None or message.from_user is None:
        return
    try:
        fresh = await get_user(message.from_user.id)
    except BackendError:
        await message.answer(UNAVAILABLE)
        return
    if not fresh["has_key"]:
        await message.answer(_explain(BackendError(409, "no-key")))
        return
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Заменить токен", callback_data="reissue:yes")]]
    )
    await message.answer(
        "Старый токен будет удалён. Новый получит тот же оставшийся лимит "
        f"<b>{_usd(float(fresh['balance_usd']))}</b>.",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "reissue:yes")
async def reissue_confirm(query: CallbackQuery) -> None:
    try:
        created = await reissue_key(query.from_user.id)
    except BackendError as exc:
        await query.answer()
        if query.message is not None:
            await query.message.answer(_explain(exc))
        return
    await query.answer("Токен заменён")
    if query.message is not None:
        await query.message.answer(_secret_text(created))


@router.message(Command("catalog"))
@router.message(F.text == "Каталог")
async def catalog(message: Message, state: FSMContext) -> None:
    await state.clear()
    if await _require(message) is None:
        return
    try:
        items = await list_products()
    except BackendError:
        await message.answer(UNAVAILABLE)
        return
    if not items:
        await message.answer("Каталог пока пуст.")
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
        await message.answer(part)


@router.message(Topup.amount)
async def topup_amount(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip().replace(",", ".")
    if text in MENU_TEXTS:
        await state.clear()
        await message.answer("Нажмите кнопку ещё раз.")
        return
    try:
        amount = float(text)
    except ValueError:
        await message.answer("Нужно число в рублях, например 500.")
        return
    if amount <= 0:
        await message.answer("Сумма должна быть больше нуля.")
        return
    if message.from_user is None:
        return
    try:
        created = await create_topup(message.from_user.id, amount)
    except BackendError as exc:
        await state.clear()
        await message.answer(_explain(exc), reply_markup=MENU)
        return
    await state.clear()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Оплатить", url=str(created["pay_url"]))]]
    )
    await message.answer(
        f"К оплате {created['amount_rub']:.2f} ₽. На баланс придёт {_usd(float(created['amount_usd']))}.\n"
        "После оплаты ЮKassa вернёт вас в этот чат. Если токен уже выпущен, лимит увеличится на эту сумму.",
        reply_markup=keyboard,
    )
