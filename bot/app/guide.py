"""Короткая настройка программ. Файлы лежат на нашем сервере, шаги — свои."""

from html import escape

BASE_URL = "https://router.cheap/v1"
CHAT_URL = "https://router.cheap/v1/chat/completions"
CLAUDE_URL = "https://router.cheap"
RESERVE_OPENAI = "https://direct.router-cheap.com/v1"
RESERVE_CLAUDE = "https://direct.router-cheap.com"
DEFAULT_MODEL = "gpt-6-astra"

# id в кнопке, название, имя файла, есть ли Linux
APPS: list[tuple[str, str, str, bool]] = [
    ("codex", "Codex", "codex", True),
    ("ccode", "Claude Code", "claude-code", True),
    ("cdesk", "Claude Desktop", "claude-desktop", False),
    ("ocode", "OpenCode", "opencode", True),
    ("hermes", "Hermes", "hermes", True),
    ("grok", "Grok Build", "grok-build", True),
    ("cursor", "Cursor", "", False),
    ("other", "Другое приложение", "", False),
]

OS: list[tuple[str, str, str]] = [
    ("win", "Windows", "windows"),
    ("mac", "macOS", "macos"),
    ("lin", "Linux", "linux"),
]

_APPS = {item[0]: item for item in APPS}
_OS = {item[0]: item for item in OS}

_NOTES = {
    "cdesk": "Аккаунт и чаты Claude Desktop не трогаются, перед настройкой сохраняется их копия.",
}
_CLOSE_HINT = {
    "cdesk": "Claude Desktop можно не закрывать — установщик предложит это сам.",
}

_NETWORK = (
    "<blockquote expandable><b>Если ответы обрываются</b>\n"
    "Ошибки ECONNRESET, таймауты и обрыв ответа обычно из-за сети. "
    "Нажмите «Запасной адрес» и запустите ту команду так же, как первую.\n"
    "Не помогло — попробуйте другой VPN или выключите его.</blockquote>"
)


def apps_screen() -> tuple[str, list[list[tuple]]]:
    text = (
        "<b>Подключение программы</b>\n\n"
        "Выберите программу. Для Cursor — инструкция в настройках; "
        "для остальных — одна команда, вставьте её, и всё настроится само."
    )
    rows: list[list[tuple]] = []
    pair: list[tuple] = []
    for app_id, title, _file_id, _linux in APPS:
        if app_id == "other":
            if pair:
                rows.append(pair)
                pair = []
            rows.append([("cb", title, f"guide:a:{app_id}")])
            continue
        pair.append(("cb", title, f"guide:a:{app_id}"))
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)
    rows.append([("cb", "← Назад", "cabinet")])
    return text, rows


def os_screen(app_id: str) -> tuple[str, list[list[tuple]]] | None:
    app = _APPS.get(app_id)
    if app is None or app_id == "other":
        return None
    _id, title, _file_id, linux = app
    text = f"<b>{title}</b>\n\nНа каком компьютере настраиваем?"
    systems = OS if linux else OS[:2]
    rows = [[("cb", name, f"guide:s:{app_id}:{os_id}") for os_id, name, _folder in systems]]
    rows.append([("cb", "← Назад", "guide")])
    return text, rows


def install_target(app_id: str, os_id: str) -> tuple[str, str] | None:
    """(файл программы, папка системы) для запроса команды установки."""
    if app_id == "cursor":
        return None
    app = _APPS.get(app_id)
    system = _OS.get(os_id)
    if app is None or system is None or app_id == "other":
        return None
    if os_id == "lin" and not app[3]:
        return None
    file_id = app[2]
    if not file_id:
        return None
    return file_id, system[2]


def cursor_manual_screen(token: str = "") -> tuple[str, list[list[tuple]]]:
    """Cursor настраивается вручную в Settings → Models → OpenAI API."""
    parts = [
        "<b>Cursor — настройка вручную</b>",
        "",
        "Автоустановщик для Cursor отключён: надёжнее прописать ключ и адрес в настройках Cursor.",
        "",
        "1. Откройте <b>Cursor → Settings → Models</b> (Ctrl + ,).",
        "2. Блок <b>OpenAI API Key</b>: вставьте ваш токен.",
        "3. Переключатель <b>Use OpenAI API Key</b> — <b>включён</b> (должно быть «Secret saved»).",
        f"4. <b>Override OpenAI Base URL</b> — <b>включён</b>, адрес:\n<code>{escape(BASE_URL)}</code>",
        "",
        "<b>Модели</b>",
        f"• GPT/Grok (например <code>{DEFAULT_MODEL}</code>): <b>не добавляйте</b> их как custom, если уже есть в списке Cursor — просто включите встроенную модель.",
        "• DeepSeek, GLM и др.: кнопка <b>Add model</b>, id <b>точно</b> как в каталоге (например <code>deepseek-v4-pro</code>).",
        "",
        "5. Новый чат → выберите модель и отправьте пробный запрос.",
        "",
        "<blockquote expandable><b>Claude и Gemini</b>\n"
        "Через Override OpenAI Base URL в Cursor не подключаются — только GPT/Grok и добавленные OpenAI-compatible модели.</blockquote>",
        "<blockquote expandable><b>Отключить aimarket</b>\n"
        "Выключите <b>Use OpenAI API Key</b> и <b>Override OpenAI Base URL</b>, удалите свой ключ из поля, перезапустите Cursor.</blockquote>",
        "<blockquote expandable><b>Если «Model name is not valid»</b>\n"
        "Проверьте, что <b>Use OpenAI API Key</b> включён. Для GPT/Grok не дублируйте id как custom-модель.</blockquote>",
    ]
    if not token:
        parts.extend([
            "",
            "<i>Сначала пополните баланс — после первой оплаты выпустится токен.</i>",
        ])
    rows: list[list[tuple]] = []
    if token:
        rows.append([
            ("copy", "Скопировать адрес", BASE_URL, True),
            ("copy", "Скопировать мой токен", token, True),
        ])
        rows.append([("copy", "Скопировать модель", DEFAULT_MODEL, True)])
    else:
        rows.append([("cb", "Пополнить баланс", "topup")])
    rows.append([("cb", "← Назад", "guide")])
    return "\n".join(parts), rows


def steps_screen(
    app_id: str,
    os_id: str,
    origin: str,
    token: str = "",
    command: str = "",
) -> tuple[str, list[list[tuple]]] | None:
    if install_target(app_id, os_id) is None:
        return None
    if not token:
        return _no_key_screen(app_id, os_id)
    if not command:
        return archive_screen(app_id, os_id, origin, token, fallback=True)
    title = _APPS[app_id][1]
    os_name = _OS[os_id][1]
    intro = " ".join(filter(None, [f"{title} должен быть уже установлен.", _NOTES.get(app_id, "")]))
    parts = [f"<b>{title} — {os_name}</b>", "", f"<i>{intro}</i>", ""]
    steps = [
        "Нажмите «Скопировать команду» ниже.",
        _terminal_step(os_id),
        f"Дождитесь надписи «Готово» и перезапустите {title}.",
    ]
    parts.extend(f"{index}. {step}" for index, step in enumerate(steps, start=1))
    if app_id in _CLOSE_HINT:
        parts.extend(["", _CLOSE_HINT[app_id]])
    parts.extend([
        "",
        f"<code>{escape(command)}</code>",
        "<i>Команда действует 15 минут. В ней ваш токен — не пересылайте её.</i>",
        "",
        _NETWORK,
    ])
    rows = [
        [("copy", "Скопировать команду", command, True)],
        [("cb", "Запасной адрес", f"guide:r:{app_id}:{os_id}"), ("cb", "Без командной строки", f"guide:f:{app_id}:{os_id}")],
        [("cb", "← Назад", f"guide:a:{app_id}")],
    ]
    return "\n".join(parts), rows


def archive_screen(
    app_id: str,
    os_id: str,
    origin: str,
    token: str,
    fallback: bool = False,
) -> tuple[str, list[list[tuple]]] | None:
    if install_target(app_id, os_id) is None:
        return None
    _id, title, file_id, _linux = _APPS[app_id]
    _os_id, os_name, os_folder = _OS[os_id]
    if os_id == "lin":
        run = f"Запустите в терминале <code>bash setup-aimarket-{file_id}.sh</code> из папки с файлом."
    else:
        launcher = "start.cmd" if os_id == "win" else "start.command"
        run = f"Распакуйте архив и откройте файл <code>{launcher}</code>."
    steps = [
        "Нажмите «Скопировать мой токен».",
        "Нажмите «Скачать установщик».",
        run,
        f"Установщик покажет найденный токен — нажмите Enter. Потом перезапустите {title}.",
    ]
    parts = [f"<b>{title} — {os_name}, без командной строки</b>", ""]
    if fallback:
        parts.extend(["Команду сейчас получить не удалось, поэтому — через установщик.", ""])
    parts.extend(f"{index}. {step}" for index, step in enumerate(steps, start=1))
    if os_id == "mac":
        parts.extend(["", "Если macOS не открывает файл: правый клик по нему → «Открыть» → «Открыть»."])
    if app_id in _CLOSE_HINT:
        parts.extend(["", _CLOSE_HINT[app_id]])
    rows: list[list[tuple]] = [[("copy", "Скопировать мой токен", token, True)]]
    site = origin.rstrip("/")
    if site:
        rows.append([("url", "Скачать установщик", f"{site}/downloads/setup/{_filename(file_id, os_id, os_folder)}", True)])
    rows.append([("cb", "← Назад", f"guide:s:{app_id}:{os_id}" if not fallback else f"guide:a:{app_id}")])
    return "\n".join(parts), rows


def reserve_screen(app_id: str, os_id: str, command: str) -> tuple[str, list[list[tuple]]] | None:
    if install_target(app_id, os_id) is None:
        return None
    title = _APPS[app_id][1]
    text = (
        f"<b>{title} — запасной адрес</b>\n\n"
        "Если ответы обрываются, настройте программу заново через запасной адрес. "
        "Запустите эту команду так же, как первую.\n\n"
        f"<code>{escape(command)}</code>\n"
        "<i>Команда действует 15 минут. В ней ваш токен — не пересылайте её.</i>"
    )
    rows = [
        [("copy", "Скопировать команду", command, True)],
        [("cb", "← Назад", f"guide:s:{app_id}:{os_id}")],
    ]
    return text, rows


def other_screen() -> tuple[str, list[list[tuple]]]:
    text = (
        "<b>Другое приложение</b>\n\n"
        "В настройках программы найдите «OpenAI-compatible», «Custom provider» или «Custom endpoint» "
        "и заполните три поля:\n\n"
        f"Адрес (Base URL)\n<code>{BASE_URL}</code>\n\n"
        "Ключ (API key)\nваш токен — кнопка «Мой токен»\n\n"
        f"Модель\n<code>{DEFAULT_MODEL}</code>\n\n"
        "<blockquote expandable><b>Если не подходит</b>\n"
        f"Поле просит полный адрес: <code>{CHAT_URL}</code>\n"
        f"Модели Claude (Anthropic API): <code>{CLAUDE_URL}</code>\n"
        f"Запасной адрес, если ответы обрываются: <code>{RESERVE_OPENAI}</code>, "
        f"для Claude — <code>{RESERVE_CLAUDE}</code></blockquote>"
    )
    rows = [
        [("copy", "Скопировать адрес", BASE_URL, True), ("copy", "Скопировать модель", DEFAULT_MODEL, True)],
        [("cb", "Мой токен", "token")],
        [("cb", "← Назад", "guide")],
    ]
    return text, rows


def known_app(app_id: str) -> bool:
    return app_id in _APPS


def _no_key_screen(app_id: str, os_id: str) -> tuple[str, list[list[tuple]]]:
    title = _APPS[app_id][1]
    text = (
        f"<b>{title} — {_OS[os_id][1]}</b>\n\n"
        "Сначала пополните баланс — после первой оплаты выпустится токен, "
        "и здесь появится команда для установки."
    )
    rows = [
        [("cb", "Пополнить баланс", "topup")],
        [("cb", "← Назад", f"guide:a:{app_id}")],
    ]
    return text, rows


def _filename(file_id: str, os_id: str, os_folder: str) -> str:
    if os_id == "lin":
        return f"setup-aimarket-{file_id}.sh"
    return f"aimarket-{file_id}-{os_folder}.zip"


def _terminal_step(os_id: str) -> str:
    if os_id == "win":
        return "Нажмите <b>Win + R</b>, вставьте команду (Ctrl + V) и нажмите Enter."
    if os_id == "mac":
        return "Откройте <b>Терминал</b> (⌘ + Пробел, наберите «Терминал»), вставьте команду (⌘ + V) и нажмите Enter."
    return "Откройте терминал, вставьте команду (Ctrl + Shift + V) и нажмите Enter."
