"""Короткая настройка программ. Файлы лежат на нашем сервере, шаги — свои."""

BASE_URL = "https://router.cheap/v1"
CHAT_URL = "https://router.cheap/v1/chat/completions"
CLAUDE_URL = "https://router.cheap"
RESERVE_OPENAI = "https://direct.router-cheap.com/v1"
RESERVE_CLAUDE = "https://direct.router-cheap.com"

# id в кнопке, название, имя файла, есть ли Linux
APPS: list[tuple[str, str, str, bool]] = [
    ("codex", "Codex", "codex", True),
    ("ccode", "Claude Code", "claude-code", True),
    ("cdesk", "Claude Desktop", "claude-desktop", False),
    ("ocode", "OpenCode", "opencode", True),
    ("hermes", "Hermes", "hermes", True),
    ("grok", "Grok Build", "grok-build", True),
    ("cursor", "Cursor", "cursor", True),
    ("other", "Другое приложение", "", False),
]

OS: list[tuple[str, str, str]] = [
    ("win", "Windows", "windows"),
    ("mac", "macOS", "macos"),
    ("lin", "Linux", "linux"),
]

_APPS = {item[0]: item for item in APPS}
_OS = {item[0]: item for item in OS}

_NETWORK = (
    "<blockquote expandable><b>Если соединение обрывается</b>\n"
    "Сбросы ECONNRESET, таймауты и обрыв потока обычно идут из сети.\n"
    "Запустите настройку снова и выберите пункт <code>3</code> — запасной адрес.\n"
    "Вручную, OpenAI-совместимые программы:\n"
    f"<code>{RESERVE_OPENAI}</code>\n"
    "Claude и Anthropic:\n"
    f"<code>{RESERVE_CLAUDE}</code>\n"
    "Если не помогло, попробуйте VPN, который не рвёт поток. "
    "Одна программа может работать, а другая нет: протоколы разные.</blockquote>"
)


def apps_screen() -> tuple[str, list[list[tuple]]]:
    text = (
        "<b>Инструкция</b>\n\n"
        "Выберите программу. Затем — систему и короткие шаги.\n"
        "Токен из кабинета вставляется в эту программу, адрес API общий."
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
    text = f"<b>{title}</b>\n\nВыберите операционную систему."
    systems = OS if linux else OS[:2]
    rows = [[("cb", name, f"guide:s:{app_id}:{os_id}") for os_id, name, _folder in systems]]
    rows.append([("cb", "← Назад", "guide")])
    return text, rows


def steps_screen(app_id: str, os_id: str, origin: str, token: str = "") -> tuple[str, list[list[tuple]]] | None:
    app = _APPS.get(app_id)
    system = _OS.get(os_id)
    if app is None or system is None or app_id == "other":
        return None
    _id, title, file_id, linux = app
    if os_id == "lin" and not linux:
        return None
    _os_id, os_name, os_folder = system
    filename = _filename(file_id, os_id, os_folder)
    run = _run_file(file_id, os_id)
    text = _steps_text(app_id, title, os_name, run)
    rows: list[list[tuple]] = []
    site = origin.rstrip("/")
    if site:
        rows.append([("url", "Скачать программу", f"{site}/downloads/setup/{filename}", True)])
    if token:
        rows.append([("copy", "Скопировать мой токен", token, True)])
    else:
        rows.append([("cb", "Открыть мой токен", "token", True)])
    rows.append([("cb", "← Назад", f"guide:a:{app_id}")])
    return text, rows


def other_screen() -> tuple[str, list[list[tuple]]]:
    text = (
        "<b>Другое приложение</b>\n\n"
        "В настройках найдите свой провайдер или OpenAI-совместимый API и вставьте значения.\n\n"
        "Провайдер\n<b>OpenAI-compatible</b>\n\n"
        f"Base URL\n<code>{BASE_URL}</code>\n\n"
        "Ключ\nТокен из кнопки «Мой токен».\n\n"
        "Модель\n<code>gpt-5.6-sol</code>\n\n"
        "<blockquote>Если поле просит полный адрес Chat Completions, укажите "
        f"<code>{CHAT_URL}</code>.\n"
        f"Для Claude Messages адрес без /v1: <code>{CLAUDE_URL}</code>.</blockquote>\n\n"
        f"{_NETWORK}"
    )
    rows = [
        [("copy", "Скопировать адрес", BASE_URL, True)],
        [("cb", "← Назад", "guide")],
    ]
    return text, rows


def known_app(app_id: str) -> bool:
    return app_id in _APPS


def _filename(file_id: str, os_id: str, os_folder: str) -> str:
    if os_id == "lin":
        return f"setup-aimarket-{file_id}-ru.sh"
    return f"aimarket-{file_id}-{os_folder}-ru.zip"


def _run_file(file_id: str, os_id: str) -> str:
    if os_id == "win":
        return "start.cmd"
    if os_id == "mac":
        return "start.command"
    return f"bash setup-aimarket-{file_id}-ru.sh"


def _steps_text(app_id: str, title: str, os_name: str, run: str) -> str:
    parts = [f"<b>{title} — {os_name}</b>", ""]
    if app_id == "cdesk":
        parts.append(
            "<blockquote>Скрипт подключает сторонний сервис в Claude Desktop. "
            "Он не выходит из аккаунта и не меняет чаты. Перед запуском сохраняется копия локальных чатов.</blockquote>"
        )
        parts.append("")
    if app_id == "cursor":
        parts.append(
            "<blockquote>Скрипт сохраняет копию настроек Cursor и меняет только ключ, адрес API "
            "и список моделей GPT и Grok. Чаты остаются. Claude через эту настройку не подключается.</blockquote>"
        )
        parts.append("")
    steps = [f"Убедитесь, что {title} уже установлен на этом компьютере."]
    if app_id == "cdesk":
        steps.append("Полностью закройте Claude Desktop, включая фоновый процесс.")
    if app_id == "cursor":
        steps.append("Полностью закройте Cursor, включая иконку в трее.")
    if run.startswith("bash "):
        steps.append("Скачайте файл и не переименовывайте его.")
    else:
        steps.append("Скачайте архив и распакуйте его.")
    steps.append(f"Запустите <code>{run}</code>.")
    steps.append("В меню введите <code>1</code> — это подключение к API.")
    steps.append(f"Перезапустите {title} и отправьте пробный запрос.")
    parts.extend(f"{index}. {step}" for index, step in enumerate(steps, start=1))
    parts.append("")
    parts.append(_NETWORK)
    return "\n".join(parts)
