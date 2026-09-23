import html
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    CopyTextButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardRemove,
)

from app.backend import (
    BackendError,
    accept_offer,
    check_topup,
    create_topup,
    get_user,
    issue_key,
    list_products,
    read_key,
    reissue_key,
    upsert_user,
)

router = Router()
UNAVAILABLE = "Сервис сейчас недоступен. Попробуйте чуть позже."
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


def _usd(value: float) -> str:
    return f"${value:.2f}"


def _spent(value: float) -> str:
    return f"${value:.4f}"


def _when(value: str) -> str:
    if not value:
        return "только что"
    moment = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(_MSK)
    return f"{moment.day} {_MONTHS[moment.month - 1]} {moment.year}, {moment:%H:%M}"


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


def _offer_screen(profile: dict) -> tuple[str, InlineKeyboardMarkup]:
    url = str(profile.get("offer_url") or "")
    text = (
        "<b>Aimarket</b>\n\n"
        "Перед началом прочитайте оферту и примите её.\n"
        "После этого откроется личный кабинет: баланс, пополнение и токен."
    )
    if not url:
        text += "\n\nСсылка на оферту появится, когда в админке будет указан адрес сайта."
    rows = [[_button("✅ Принимаю", callback="offer:yes", green=True)]]
    if url:
        rows.append([_button("Оферта", url=url)])
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def _cabinet_screen(profile: dict, notice: str = "") -> tuple[str, InlineKeyboardMarkup]:
    head = f"{notice}\n\n" if notice else ""
    text = (
        f"{head}<b>Личный кабинет</b>\n\n"
        f"Баланс\n<b>{_usd(float(profile['balance_usd']))}</b>\n\n"
        f"Расход сегодня: {_spent(float(profile.get('spent_today_usd') or 0))}\n"
        f"Расход за месяц: {_spent(float(profile.get('spent_month_usd') or 0))}"
    )
    action = "token" if profile.get("has_key") else "issue"
    label = "Мой токен" if profile.get("has_key") else "Выпустить токен"
    rows = [
        [_button("Пополнить баланс", callback="topup", green=True)],
        [_button(label, callback=action)],
    ]
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def _topup_screen(profile: dict) -> tuple[str, InlineKeyboardMarkup]:
    price = float(profile.get("usd_price_rub") or 0)
    text = (
        "<b>Пополнение</b>\n\n"
        f"1 $ стоит {price:.2f} ₽.\n"
        "Напишите сумму в рублях, минимум 1.\n"
        "Например: <b>500</b>"
    )
    return text, InlineKeyboardMarkup(inline_keyboard=[_back_row()])


def _pay_screen(created: dict) -> tuple[str, InlineKeyboardMarkup]:
    text = (
        "<b>Оплата</b>\n\n"
        f"К оплате <b>{float(created['amount_rub']):.2f} ₽</b>\n"
        f"На баланс придёт <b>{_usd(float(created['amount_usd']))}</b>\n\n"
        "После оплаты ЮKassa вернёт вас в этот чат. "
        "Если токен уже выпущен, лимит увеличится на эту сумму."
    )
    rows = [
        [_button("Оплатить", url=str(created["pay_url"]), green=True)],
        _back_row(),
    ]
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def _empty_balance_screen() -> tuple[str, InlineKeyboardMarkup]:
    text = (
        "<b>Токен</b>\n\n"
        "Баланс нулевой, выпускать пока нечего.\n"
        "Пополните баланс — токен получит весь этот лимит."
    )
    rows = [
        [_button("Пополнить баланс", callback="topup", green=True)],
        _back_row(),
    ]
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def _token_screen(key: dict, title: str = "Ваш токен") -> tuple[str, InlineKeyboardMarkup]:
    secret = str(key.get("secret") or "")
    base = html.escape(str(key.get("base_url") or ""))
    shown = html.escape(secret) if secret else "не удалось получить ключ"
    text = (
        f"<b>{html.escape(title)}</b>\n\n"
        f"Выпущен: {_when(str(key.get('created_at') or ''))}\n"
        f"Лимит: <b>{_usd(float(key.get('balance_usd') or 0))}</b>\n\n"
        f"Адрес API\n<code>{base}</code>\n\n"
        f"Ключ\n<code>{shown}</code>"
    )
    rows = []
    if secret:
        rows.append([_button("Скопировать токен", copy=secret, green=True)])
    rows.append([_button("Перевыпустить", callback="reissue")])
    rows.append(_back_row())
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


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


async def _profile_of(user_id: int, username: str, first_name: str) -> dict:
    await upsert_user(user_id, username, first_name)
    return await get_user(user_id)


async def _edit(message: Message, text: str, markup: InlineKeyboardMarkup) -> None:
    try:
        await message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return
        await message.answer(text, reply_markup=markup)


async def _open(message: Message, text: str, markup: InlineKeyboardMarkup) -> Message:
    sent = await message.answer(text, reply_markup=ReplyKeyboardRemove())
    try:
        await sent.edit_reply_markup(reply_markup=markup)
    except TelegramBadRequest:
        await sent.edit_text(text, reply_markup=markup)
    return sent


async def _show_callback(query: CallbackQuery, text: str, markup: InlineKeyboardMarkup) -> None:
    await query.answer()
    if query.message is not None:
        await _edit(query.message, text, markup)


async def _remember_screen(state: FSMContext, message: Message) -> None:
    await state.set_state(Topup.amount)
    await state.update_data(screen_chat_id=message.chat.id, screen_message_id=message.message_id)


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, command: CommandObject) -> None:
    await state.clear()
    user = message.from_user
    if user is None:
        return
    try:
        profile = await _profile_of(user.id, user.username or "", user.first_name or "")
    except BackendError:
        await message.answer(UNAVAILABLE)
        return
    payload = (command.args or "").strip()
    notice = ""
    if payload.startswith("paid_"):
        raw = payload.removeprefix("paid_")
        if raw.isdigit():
            notice = await _payment_notice(user.id, int(raw))
            try:
                profile = await get_user(user.id)
            except BackendError:
                pass
    if not profile["offer_accepted"]:
        text, markup = _offer_screen(profile)
        await _open(message, text, markup)
        return
    text, markup = _cabinet_screen(profile, notice)
    await _open(message, text, markup)


async def _payment_notice(telegram_id: int, topup_id: int) -> str:
    try:
        result = await check_topup(telegram_id, topup_id)
    except BackendError:
        return "Не удалось проверить платёж."
    status = str(result.get("status") or "")
    if status == "paid":
        return "Оплата прошла."
    if status in {"rejected", "failed"}:
        return "Платёж не прошёл."
    return "Платёж ещё не подтверждён. Баланс обновится, когда оплата дойдёт."


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
    text, markup = _cabinet_screen(profile, "Оферта принята.")
    await _show_callback(query, text, markup)


@router.callback_query(F.data == "cabinet")
async def cabinet(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = query.from_user
    try:
        profile = await _profile_of(user.id, user.username or "", user.first_name or "")
    except BackendError:
        await query.answer(UNAVAILABLE, show_alert=True)
        return
    if not profile["offer_accepted"]:
        text, markup = _offer_screen(profile)
        await _show_callback(query, text, markup)
        return
    text, markup = _cabinet_screen(profile)
    await _show_callback(query, text, markup)


@router.callback_query(F.data == "topup")
async def topup_open(query: CallbackQuery, state: FSMContext) -> None:
    user = query.from_user
    try:
        profile = await _profile_of(user.id, user.username or "", user.first_name or "")
    except BackendError:
        await query.answer(UNAVAILABLE, show_alert=True)
        return
    if not profile["offer_accepted"]:
        await query.answer("Сначала примите оферту.", show_alert=True)
        return
    if float(profile.get("usd_price_rub") or 0) <= 0:
        await query.answer(_explain(BackendError(402, "sales-closed")), show_alert=True)
        return
    if not profile.get("yookassa_enabled"):
        await query.answer(_explain(BackendError(402, "no-yookassa")), show_alert=True)
        return
    text, markup = _topup_screen(profile)
    await _show_callback(query, text, markup)
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
        await message.answer("Нужно число в рублях, например 500.")
        return
    if amount < 1:
        await message.answer("Минимальная сумма — 1 ₽.")
        return
    if message.from_user is None:
        return
    try:
        created = await create_topup(message.from_user.id, amount)
    except BackendError as exc:
        await state.clear()
        await message.answer(_explain(exc))
        return
    text, markup = _pay_screen(created)
    data = await state.get_data()
    await state.clear()
    edited = False
    chat_id = data.get("screen_chat_id")
    message_id = data.get("screen_message_id")
    if chat_id and message_id:
        try:
            await message.bot.edit_message_text(
                text,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=markup,
            )
            edited = True
        except TelegramBadRequest:
            edited = False
    if not edited:
        await message.answer(text, reply_markup=markup)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass


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
        await _show_token(query, "Ваш токен")
        return
    if float(profile["balance_usd"]) <= 0:
        text, markup = _empty_balance_screen()
        await _show_callback(query, text, markup)
        return
    await query.answer()
    try:
        created = await issue_key(user.id)
    except BackendError as exc:
        if query.message is not None:
            await query.message.answer(_explain(exc))
        return
    text, markup = _token_screen(created, "Токен выпущен")
    if query.message is not None:
        await _edit(query.message, text, markup)


@router.callback_query(F.data == "token")
async def token(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _show_token(query, "Ваш токен")


async def _show_token(query: CallbackQuery, title: str) -> None:
    try:
        key = await read_key(query.from_user.id)
    except BackendError as exc:
        await query.answer(_explain(exc), show_alert=True)
        return
    text, markup = _token_screen(key, title)
    await _show_callback(query, text, markup)


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
    await _show_callback(query, text, markup)


@router.callback_query(F.data == "reissue:yes")
async def reissue_confirm(query: CallbackQuery) -> None:
    await query.answer()
    try:
        created = await reissue_key(query.from_user.id)
    except BackendError as exc:
        if query.message is not None:
            await query.message.answer(_explain(exc))
        return
    text, markup = _token_screen(created, "Новый токен")
    if query.message is not None:
        await _edit(query.message, text, markup)


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
            await message.answer(UNAVAILABLE)
            return
        if not profile["offer_accepted"]:
            body, markup = _offer_screen(profile)
            await _open(message, body, markup)
            return
        body, markup = _topup_screen(profile)
        sent = await _open(message, body, markup)
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
        await message.answer(UNAVAILABLE)
        return
    if not profile["offer_accepted"]:
        text, markup = _offer_screen(profile)
    else:
        text, markup = _cabinet_screen(profile)
    await _open(message, text, markup)


@router.message(Command("catalog"))
async def catalog(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    if user is None:
        return
    try:
        profile = await upsert_user(user.id, user.username or "", user.first_name or "")
    except BackendError:
        await message.answer(UNAVAILABLE)
        return
    if not profile["offer_accepted"]:
        text, markup = _offer_screen(profile)
        await _open(message, text, markup)
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
