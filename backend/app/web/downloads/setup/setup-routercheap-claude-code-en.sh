#!/usr/bin/env bash
# router.cheap setup helper for Codex, Claude Code, OpenCode, Hermes, Grok Build, Cursor, and Factory Droid.
set -Eeuo pipefail

# Resolve bundled assets relative to this script, independent of the caller's cwd.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

LANG_CODE="en"
APP="claude-code"
ACTION=""
API_KEY=""
ENDPOINT="https://router.cheap/v1"
ANTHROPIC_ENDPOINT="https://router.cheap"
TELEMETRY_ENDPOINT="https://router.cheap/api/setup-events"
MODEL="gpt-6-astra"
MODEL_EXPLICIT=0
CLAUDE_MODEL="claude-opus-5"
GROK_MODEL="grok-4.5"
HERMES_REASONING_EFFORT="medium"
HERMES_REASONING_EFFORT_EXPLICIT=0
SCRIPT_VERSION="2.14"
OPENAI_MODELS=""
CLAUDE_MODELS=""
OPENAI_MODELS_VERIFIED=0
CLAUDE_MODELS_VERIFIED=0
OPENAI_MODEL_CANDIDATES='
gpt-6-astra
gpt-5.6-sol
gpt-5.6-terra
gpt-5.6-luna
claude-opus-5
claude-sonnet-5
grok-4.6
grok-4.7
grok-4.5
gpt-5.4
gpt-5
gpt-5-mini
gpt-4.1
gpt-4o
claude-sonnet-4-5
claude-opus-4-5
claude-3-5-sonnet-latest
claude-3-7-sonnet-latest
'
CLAUDE_MODEL_CANDIDATES='
claude-opus-5
claude-sonnet-5
claude-sonnet-4-5
claude-opus-4-5
claude-3-5-sonnet-latest
claude-3-7-sonnet-latest
claude-3-opus-latest
'
SKIP_ENDPOINT_TEST=0
SKIP_LIVE_MODEL_TEST=0
SKIP_CODEX_RUNTIME_TEST=0
ALLOW_MISSING_MODEL=0
INSTALL_CODEX_IF_MISSING=1
# A setup must refresh the environment inherited by a running CLI. We only
# restart a process whose command line is the bare standalone `codex` binary;
# use --no-restart-codex to leave every process untouched.
RESTART_CODEX=1
DRY_RUN=0
CODEX_RESTART_COUNT=0
CODEX_RESTART_COMMAND=""
TELEMETRY_ENABLED=0
TELEMETRY_ACTION=""
TELEMETRY_ERROR_MESSAGE=""
TELEMETRY_ERROR_STEP=""
TELEMETRY_ERROR_FUNCTION=""
TELEMETRY_ERROR_LINE=0
TELEMETRY_EXIT_CODE=0
TELEMETRY_SESSION_ID=""
TELEMETRY_STARTED_AT=0
SETUP_LAST_PROBE_METHOD=""
SETUP_LAST_PROBE_PATH=""
SETUP_LAST_PROBE_STATUS=""
SETUP_MODELS_PROBE_STATUS=""
SETUP_RESPONSES_PROBE_STATUS=""
CODEX_RUNTIME_PROBE_STATUS=""
CODEX_RUNTIME_PROBE_EXIT_CODE=""

usage() {
  cat <<'EOF'
Usage:
  bash setup-routercheap.sh [options]

Options:
  --lang en|ru               Interface language. Default: ru when LANG starts with ru, otherwise en.
  --app codex|claude-code|opencode|hermes|grok-build|cursor|droid
  --action setup|setup-reserve|restore
  --api-key KEY              router.cheap API key for setup mode
  --endpoint URL             OpenAI-compatible base URL, default https://router.cheap/v1
  --anthropic-endpoint URL   Anthropic-compatible root URL, default https://router.cheap
  --telemetry-endpoint URL   Safe setup event endpoint, default https://router.cheap/api/setup-events
  --model MODEL              OpenAI-compatible model, default gpt-6-astra (falls back after live validation)
  --claude-model MODEL       Claude Code model, default claude-opus-5
  --grok-model MODEL         Grok Build model, default grok-4.5
  --hermes-reasoning-effort LEVEL
                             Hermes reasoning: none|minimal|low|medium|high|xhigh|max (default medium; model-specific contracts apply)
  --skip-endpoint-test       Do not test router.cheap before writing config
  --skip-live-model-test     Test /v1/models only, skip /v1/responses
  --skip-codex-runtime-test  Skip the Codex CLI runtime probe after writing config
  --allow-missing-model      Write config even if /v1/models does not list the model
  --install-codex-if-missing Try official standalone Codex installer if codex is missing
  --no-install-codex         Do not install Codex if it is missing
  --restart-codex            Keep the default bare standalone Codex restart behavior (compatibility alias)
  --no-restart-codex         Do not close or relaunch a running Codex process
  --dry-run                  Print planned changes without writing files
  -h, --help                 Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lang) LANG_CODE="${2:-}"; shift 2 ;;
    --app) APP="${2:-}"; shift 2 ;;
    --action) ACTION="${2:-}"; shift 2 ;;
    --api-key) API_KEY="${2:-}"; shift 2 ;;
    --endpoint) ENDPOINT="${2:-}"; shift 2 ;;
    --anthropic-endpoint) ANTHROPIC_ENDPOINT="${2:-}"; shift 2 ;;
    --telemetry-endpoint) TELEMETRY_ENDPOINT="${2:-}"; shift 2 ;;
    --model) MODEL="${2:-}"; MODEL_EXPLICIT=1; shift 2 ;;
    --claude-model) CLAUDE_MODEL="${2:-}"; shift 2 ;;
    --grok-model) GROK_MODEL="${2:-}"; shift 2 ;;
    --hermes-reasoning-effort) HERMES_REASONING_EFFORT="${2:-}"; HERMES_REASONING_EFFORT_EXPLICIT=1; shift 2 ;;
    --skip-endpoint-test) SKIP_ENDPOINT_TEST=1; shift ;;
    --skip-live-model-test) SKIP_LIVE_MODEL_TEST=1; shift ;;
    --skip-codex-runtime-test) SKIP_CODEX_RUNTIME_TEST=1; shift ;;
    --allow-missing-model) ALLOW_MISSING_MODEL=1; shift ;;
    --install-codex-if-missing) INSTALL_CODEX_IF_MISSING=1; shift ;;
    --no-install-codex) INSTALL_CODEX_IF_MISSING=0; shift ;;
    --restart-codex) RESTART_CODEX=1; shift ;;
    --no-restart-codex) RESTART_CODEX=0; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf '[FAIL] Unknown option: %s\n' "$1" >&2; exit 1 ;;
  esac
done

if [[ -z "$LANG_CODE" ]]; then
  case "${LC_ALL:-${LANG:-}}" in
    ru*|RU*) LANG_CODE="ru" ;;
    *) LANG_CODE="en" ;;
  esac
fi
case "$LANG_CODE" in en|ru) ;; *) LANG_CODE="en" ;; esac
case "$HERMES_REASONING_EFFORT" in
  none|minimal|low|medium|high|xhigh|max) ;;
  *) printf '[FAIL] Invalid Hermes reasoning effort: %s\n' "$HERMES_REASONING_EFFORT" >&2; exit 1 ;;
esac

msg() {
  local key="$1"
  if [[ "$LANG_CODE" == "ru" ]]; then
    case "$key" in
      title) printf '%s' 'Настройка приложений router.cheap' ;;
      select_app) printf '%s' 'Выберите приложение:' ;;
      select_action) printf '%s' 'Выберите действие для {app}:' ;;
      configure) printf '%s' 'Настроить {app} на router.cheap' ;;
      configure_reserve) printf '%s' 'Настроить {app} через резервный endpoint' ;;
      network_hint) printf '%s' 'Если вы видите ECONNRESET, повторяющиеся тайм-ауты или сброс потокового соединения, причина обычно на сетевом уровне. Сначала повторите настройку и выберите пункт 3 для резервного endpoint; при ручной настройке используйте https://direct.router-cheap.com/v1 для OpenAI-совместимых приложений или https://direct.router-cheap.com для Anthropic-совместимых. Если резервный endpoint не поможет, подберите надёжный VPN, который не сбрасывает потоковые соединения. Одно приложение может работать, а другое нет, поскольку они используют разные сетевые протоколы.' ;;
      restore) printf '%s' 'Вернуть официальный/обычный endpoint для {app}' ;;
      exit) printf '%s' 'Выйти' ;;
      choice) printf '%s' 'Введите номер' ;;
      bad_choice) printf '%s' 'Неверный выбор.' ;;
      paste_key) printf '%s' 'Вставьте API ключ router.cheap (ввод скрыт): ' ;;
      saved_key_found) printf '%s' 'Найден сохраненный API ключ' ;;
      saved_key_prompt) printf '%s' 'Нажмите Enter, чтобы использовать его, или вставьте новый API ключ (ввод скрыт): ' ;;
      saved_key_using) printf '%s' 'Использую сохраненный API ключ' ;;
      invalid_key) printf '%s' 'API-ключ введён некорректно. Он должен начинаться с sk-. Попробуйте ещё раз.' ;;
      endpoint) printf '%s' 'Endpoint' ;;
      model) printf '%s' 'Модель' ;;
      select_default_model) printf '%s' 'Выберите модель по умолчанию для {app}:' ;;
      select_default_model_hint) printf '%s' 'Введите только номер модели. Нажмите Enter, чтобы оставить {model}.' ;;
      selected_default_model) printf '%s' 'Выбрана модель по умолчанию' ;;
      invalid_model_choice) printf '%s' 'Неверный ввод. Введите номер из списка, например 1.' ;;
      key) printf '%s' 'Ключ' ;;
      testing) printf '%s' 'Проверяю ключ router.cheap' ;;
      writing) printf '%s' 'Записываю настройки' ;;
      codex_history_notice) printf '%s' 'Codex не имеет поддерживаемой команды копирования сессий между провайдерами. Для необязательного переноса метаданных за последние 7 дней полностью закройте Codex и выполните: python3 "$(dirname "$0")/codex-history-migrate.py" --source-provider <текущий-провайдер> --target-provider <новый-провайдер> --days 7 --dry-run; проверьте количество, затем повторите с --yes. Резервная копия для отката создается автоматически; используйте --rollback <каталог-резервной-копии>. Переносятся только метаданные, и зашифрованные рассуждения могут не продолжиться.' ;;
      done) printf '%s' 'Готово. Отдельный Codex перезапущен автоматически; если скрипт предупредил о Desktop/IDE, закройте его и запустите снова перед проверкой.' ;;
      restored) printf '%s' 'Готово. Отдельный Codex перезапущен автоматически; если скрипт предупредил о Desktop/IDE, закройте его и запустите снова перед проверкой.' ;;
      restore_not_needed) printf '%s' 'Возврат endpoint для этого приложения не нужен. Чтобы перестать использовать router.cheap, удалите custom provider/config в настройках приложения.' ;;
      cursor_closed) printf '%s' 'Полностью закройте Cursor, включая фоновый процесс в трее, и запустите настройку снова. Это защищает настройки и базу чатов Cursor.' ;;
      cursor_not_found) printf '%s' 'Не найдены локальное хранилище Cursor или встроенный SQLite runtime. Установите или обновите Cursor, один раз запустите его, полностью закройте и повторите настройку.' ;;
      cursor_configured) printf '%s' 'В Cursor обновлены OpenAI-ключ, Base URL и список доступных совместимых моделей. Существующие чаты, рабочие пространства и посторонние настройки не изменены.' ;;
      cursor_restored) printf '%s' 'Предыдущие OpenAI-ключ, Base URL и видимость моделей Cursor восстановлены. Существующие чаты не изменены.' ;;
      cursor_not_managed) printf '%s' 'Управляемая настройка Cursor для router.cheap не найдена — ничего не изменено.' ;;
      cursor_other_owner) printf '%s' 'Сейчас настройкой Cursor управляет {app}. Для восстановления используйте скрипт этого сервиса, чтобы не перезаписать активную конфигурацию.' ;;
      cursor_limit) printf '%s' 'Ограничение Cursor: Override OpenAI Base URL действует глобально и не перенаправляет Claude/Anthropic-модели. В некоторых версиях Cursor вложения с изображениями также обходят пользовательский OpenAI Base URL. Если картинка должна пройти через router.cheap, используйте Codex, OpenCode или Hermes; Cursor с GPT/Grok используйте для текстовых задач в обычном режиме контекста.' ;;
      telemetry) printf '%s' 'Отправляю безопасное событие настройки в router.cheap (приложение, ОС, действие, результат; API ключ используется только в Authorization header, чтобы определить ваш аккаунт).' ;;
      telemetry_session) printf '%s' 'Идентификатор диагностики: {session}. Сохраните его вместе со временем запуска при сообщении о проблеме Codex: по нему связываются события начала, успеха и ошибки без передачи API-ключа.' ;;
      telemetry_failed) printf '%s' 'Событие настройки не удалось отправить. Продолжаю без телеметрии.' ;;
      claude_login_preserved) printf '%s' 'Сохранённый официальный вход Claude Code оставлен без изменений. Пока настроены переменные шлюза, они имеют приоритет; после Восстановления и перезапуска Claude Code снова сможет использовать сохранённый официальный вход.' ;;
      claude_login_restore) printf '%s' 'Переменные шлюза удалены. Перезапустите Claude Code: сохранённый официальный вход снова будет использоваться без повторной авторизации, если он не истёк и не был удалён отдельно.' ;;
      claude_cache_policy_configured) printf '%s' 'Включён приоритет кэша: full-context Agent(fork) запрещён, обычные subagents остаются доступными.' ;;
      claude_cache_policy_restored) printf '%s' 'Правило запрета Agent(fork), добавленное этим скриптом, удалено. Пользовательские правила сохранены.' ;;
      claude_model_access_hint) printf '%s' 'Claude Code использует модели Claude. Откройте раздел «Маршрутизация» и включите «Автоматическую конвертацию баланса», чтобы оплачивать их из активного баланса, либо вручную конвертируйте баланс в Claude.' ;;
      cross_family_access_hint) printf '%s' 'Откройте раздел «Маршрутизация» и включите «Доступ между семействами моделей» для автоматической конвертации баланса этого запроса либо вручную конвертируйте баланс в блоке «Баланс модели».' ;;
      model_probe_retry) printf '%s' 'Модель {model} есть в каталоге, но тестовый запрос для этого ключа не прошёл. Пробую следующую доступную модель.' ;;
      model_fallback_selected) printf '%s' 'Подтверждена доступная модель по умолчанию' ;;
      model_catalog_limited) printf '%s' 'В конфигурацию добавлены только модели семейства {model}, подтверждённо доступного этому ключу.' ;;
      codex_picker_hint) printf '%s' 'Для Codex задана модель по умолчанию {model}. Custom provider не обязан показывать отдельный список моделей; перезапустите Codex, чтобы он загрузил новую конфигурацию.' ;;
      model_endpoint_hint) printf '%s' 'Выбранная модель или её провайдер не поддерживает API, необходимый этому приложению. Запустите настройку повторно с другой доступной моделью (PowerShell: -Model МОДЕЛЬ; macOS/Linux: --model МОДЕЛЬ).' ;;
      transient_server_hint) printf '%s' 'Обычно это временная ошибка шлюза или провайдера. Скрипт уже повторил запрос один раз; если ошибка осталась, подождите минуту и запустите настройку снова.' ;;
      probe_nonfatal) printf '%s' '{app} завершился временной ошибкой HTTP {model}. Настройки всё равно будут записаны; проверьте приложение после перезапуска.' ;;
      probe_timeout) printf '%s' 'Проверка ответа модели превысила тайм-аут или была отменена. Настройки всё равно будут записаны; проверьте приложение после перезапуска.' ;;
      grok_command) printf '%s' "Используйте защищённый launcher 'grok-routercheap'. Он выбирает Grok 4.5 и передаёт API ключ только дочернему процессу Grok." ;;
      grok_missing) printf '%s' 'Grok Build CLI не найден. Сначала установите официальный CLI с https://x.ai/news/grok-build-cli, затем запустите настройку снова.' ;;
      hermes_env_path) printf '%s' 'Активный файл учётных данных Hermes' ;;
      hermes_protocol) printf '%s' 'Режим API Hermes' ;;
      hermes_reasoning) printf '%s' 'Уровень reasoning Hermes' ;;
      hermes_legacy_cleaned) printf '%s' 'Устаревшие управляемые данные удалены из старого пути Hermes' ;;
      hermes_reasoning_session_fixed) printf '%s' 'Исправление выбора уровня рассуждений для сессий Hermes Desktop применено.' ;;
      hermes_reasoning_session_current) printf '%s' 'Выбор уровня рассуждений для сессий Hermes Desktop уже работает корректно.' ;;
      droid_configured) printf '%s' 'Настройка Factory Droid обновлена. Перезапустите Droid перед проверкой.' ;;
      droid_config_hint) printf '%s' 'Droid использует локальный Factory settings.json, а API-ключ хранится в ROUTER_CHEAP_API_KEY, не в JSON.' ;;
      *) printf '%s' "$key" ;;
    esac
  else
    case "$key" in
      title) printf '%s' 'router.cheap app setup' ;;
      select_app) printf '%s' 'Select application:' ;;
      select_action) printf '%s' 'Select action for {app}:' ;;
      configure) printf '%s' 'Configure {app} for router.cheap' ;;
      configure_reserve) printf '%s' 'Configure {app} with the reserve endpoint' ;;
      network_hint) printf '%s' 'If you see ECONNRESET, repeated timeouts, or streaming connections being reset, the problem is usually at the network level. First rerun setup with option 3 to use the reserve endpoint; when configuring manually, use https://direct.router-cheap.com/v1 for OpenAI-compatible apps or https://direct.router-cheap.com for Anthropic-compatible apps. If the reserve endpoint does not help, use a trusted VPN that does not reset streaming connections. One app may work while another fails because apps use different network protocols.' ;;
      restore) printf '%s' 'Restore official/default {app} endpoint' ;;
      exit) printf '%s' 'Exit' ;;
      choice) printf '%s' 'Enter number' ;;
      bad_choice) printf '%s' 'Invalid choice.' ;;
      paste_key) printf '%s' 'Paste router.cheap API key (input is hidden): ' ;;
      saved_key_found) printf '%s' 'Found saved API key' ;;
      saved_key_prompt) printf '%s' 'Press Enter to use it, or paste a new API key (input is hidden): ' ;;
      saved_key_using) printf '%s' 'Using saved API key' ;;
      invalid_key) printf '%s' 'API key is invalid. It must start with sk-. Please try again.' ;;
      endpoint) printf '%s' 'Endpoint' ;;
      model) printf '%s' 'Model' ;;
      select_default_model) printf '%s' 'Choose the default model for {app}:' ;;
      select_default_model_hint) printf '%s' 'Enter only the model number. Press Enter to keep {model}.' ;;
      selected_default_model) printf '%s' 'Default model selected' ;;
      invalid_model_choice) printf '%s' 'Invalid input. Enter a number from the list, for example 1.' ;;
      key) printf '%s' 'Key' ;;
      testing) printf '%s' 'Testing router.cheap key' ;;
      writing) printf '%s' 'Writing configuration' ;;
      codex_history_notice) printf '%s' 'Codex has no supported cross-provider session-copy command. The setup keeps session files and indexes intact. Please ask Codex: review the optional last-7-day metadata migration dry-run before applying it. To run it, close Codex and execute python3 "$(dirname "$0")/codex-history-migrate.py" --source-provider <current-provider> --target-provider <new-provider> --days 7 --dry-run, then rerun with --yes. A rollback backup is created automatically; use --rollback <backup-directory> to restore. This reclassifies metadata only and encrypted reasoning may not resume.' ;;
      done) printf '%s' 'Done. A bare standalone Codex was restarted automatically; if setup warned about Desktop/IDE, close it and start it again before testing.' ;;
      restored) printf '%s' 'Restored. A bare standalone Codex was restarted automatically; if setup warned about Desktop/IDE, close it and start it again before testing.' ;;
      restore_not_needed) printf '%s' 'Restore is not needed for this app. To stop using router.cheap, remove the custom provider/config in the app settings.' ;;
      cursor_closed) printf '%s' "Close Cursor completely (including its tray/background process), then run the setup again. This protects Cursor's settings and chat database." ;;
      cursor_not_found) printf '%s' "Cursor's local storage or bundled SQLite runtime was not found. Install/update Cursor, start it once, close it completely, and run setup again." ;;
      cursor_configured) printf '%s' "Cursor's OpenAI key, Base URL, and available compatible models were updated. Existing chats, workspaces, and unrelated settings were not changed." ;;
      cursor_restored) printf '%s' "Cursor's previous OpenAI key, Base URL, and model visibility settings were restored. Existing chats were not changed." ;;
      cursor_not_managed) printf '%s' 'No managed Cursor setup for router.cheap was found; nothing was changed.' ;;
      cursor_other_owner) printf '%s' "Cursor is currently managed by {app}. Restore it with that service's setup script so its active configuration is not overwritten." ;;
      cursor_limit) printf '%s' "Cursor limitation: Override OpenAI Base URL is global and does not reroute Claude/Anthropic models. Cursor can also bypass a custom OpenAI Base URL for image attachments in some versions. Use Codex, OpenCode, or Hermes when images must be sent through router.cheap; use GPT/Grok models in Cursor for text-only normal-context work." ;;
      telemetry) printf '%s' 'Sending a safe setup event to router.cheap (app, OS, action, result; the API key is used only in the Authorization header to identify your account).' ;;
      telemetry_session) printf '%s' 'Diagnostic session ID: {session}. Keep this ID with the setup time when reporting a Codex problem; it links the started, success, and failed events without exposing the API key.' ;;
      telemetry_failed) printf '%s' 'Setup event could not be sent. Continuing without telemetry.' ;;
      claude_login_preserved) printf '%s' 'Your saved official Claude Code login was left intact. Gateway variables take priority while configured; after Restore and a restart, Claude Code can use the saved official login again.' ;;
      claude_login_restore) printf '%s' 'Gateway variables were removed. Restart Claude Code; the saved official login can be used again without signing in again unless it has expired or was removed separately.' ;;
      claude_cache_policy_configured) printf '%s' 'Cache-priority policy enabled: full-context Agent(fork) is denied while ordinary subagents remain available.' ;;
      claude_cache_policy_restored) printf '%s' 'The Agent(fork) deny rule added by this setup was removed. Pre-existing user rules were preserved.' ;;
      claude_model_access_hint) printf '%s' "Claude Code uses Claude models. Open Routing and enable 'Automatic balance conversion' to pay for them from the active balance, or manually convert the balance to Claude." ;;
      cross_family_access_hint) printf '%s' "Open Routing and enable 'Cross-family access' to convert balance automatically for this request, or convert it manually in 'Model balance'." ;;
      model_probe_retry) printf '%s' 'Model {model} is listed, but its live request failed for this key. Trying the next available model.' ;;
      model_fallback_selected) printf '%s' 'Confirmed available default model' ;;
      model_catalog_limited) printf '%s' 'Only models from the confirmed usable {model} family were added to the configuration.' ;;
      codex_picker_hint) printf '%s' 'Codex uses {model} as the configured default. A custom provider does not need to expose a separate model picker; restart Codex to load the new configuration.' ;;
      model_endpoint_hint) printf '%s' 'The selected model or its provider does not support the API endpoint required by this app. Rerun setup with another available model (PowerShell: -Model MODEL; macOS/Linux: --model MODEL).' ;;
      transient_server_hint) printf '%s' 'This is usually a temporary gateway or provider error. Setup retried once automatically; wait a minute and run it again if the error persists.' ;;
      probe_nonfatal) printf '%s' '{app} failed with a temporary HTTP {model}. Configuration will still be written; test the app after restart.' ;;
      probe_timeout) printf '%s' 'The model check timed out or was canceled. Configuration will still be written; test the app after restart.' ;;
      grok_command) printf '%s' "Use the secure launcher 'grok-routercheap'. It selects Grok 4.5 and loads the API key only into the Grok child process." ;;
      grok_missing) printf '%s' 'Grok Build CLI was not found. Install the official CLI first from https://x.ai/news/grok-build-cli, then run this setup again.' ;;
      hermes_env_path) printf '%s' 'Hermes active credentials file' ;;
      hermes_protocol) printf '%s' 'Hermes API mode' ;;
      hermes_reasoning) printf '%s' 'Hermes reasoning effort' ;;
      hermes_legacy_cleaned) printf '%s' 'Removed obsolete managed credentials from the legacy Hermes path' ;;
      hermes_reasoning_session_fixed) printf '%s' 'Applied the Hermes Desktop session reasoning compatibility fix.' ;;
      hermes_reasoning_session_current) printf '%s' 'Hermes Desktop session reasoning is already handled correctly.' ;;
      droid_configured) printf '%s' 'Factory Droid custom model was updated. Restart Droid before testing.' ;;
      droid_config_hint) printf '%s' 'Droid uses the local Factory settings.json and keeps the API key in ROUTER_CHEAP_API_KEY, never in JSON.' ;;
      *) printf '%s' "$key" ;;
    esac
  fi
}

fmt_msg() {
  local text app model session
  text="$(msg "$1")"
  app="${2:-}"
  model="${3:-}"
  session="${4:-}"
  text="${text//\{app\}/$app}"
  text="${text//\{model\}/$model}"
  text="${text//\{session\}/$session}"
  printf '%s' "$text"
}

ok() { printf '[OK] %s\n' "$1"; }
warn() { printf '[WARN] %s\n' "$1"; }
section() { printf '\n== %s ==\n' "$1"; }

truncate_setup_text() {
  local value="${1:-}" limit="${2:-2000}"
  value="${value//$'\r'/ }"
  value="${value//$'\n'/ }"
  value="${value//$'\t'/ }"
  if (( ${#value} > limit )); then
    if (( limit > 3 )); then
      printf '%s...' "${value:0:limit-3}"
    else
      printf '%s' "${value:0:limit}"
    fi
  else
    printf '%s' "$value"
  fi
}

json_escape() {
  local value="${1:-}"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\r'/\\n}"
  value="${value//$'\n'/\\n}"
  value="${value//$'\t'/\\t}"
  printf '%s' "$value"
}

set_setup_step() {
  TELEMETRY_ERROR_STEP="${1:-}"
}

record_setup_error() {
  local message="${1:-}"
  if [[ -n "$message" && -z "${TELEMETRY_ERROR_MESSAGE:-}" ]]; then
    TELEMETRY_ERROR_MESSAGE="$(truncate_setup_text "$message" 2000)"
  fi
}

capture_setup_error() {
  local rc="${1:-1}" line="${2:-0}" function="${3:-main}"
  [[ "${TELEMETRY_ENABLED:-0}" -eq 1 ]] || return 0
  [[ -z "${TELEMETRY_ERROR_MESSAGE:-}" ]] || return 0
  TELEMETRY_EXIT_CODE="$rc"
  TELEMETRY_ERROR_LINE="$line"
  TELEMETRY_ERROR_FUNCTION="$(truncate_setup_text "$function" 120)"
  TELEMETRY_ERROR_MESSAGE="Unhandled command failure in ${TELEMETRY_ERROR_FUNCTION:-main} at line $line (exit $rc)"
}

fail() {
  record_setup_error "$1"
  printf '[FAIL] %s\n' "$1" >&2
  exit 1
}

app_label() {
  case "$1" in
    codex) printf '%s' 'Codex' ;;
    claude-code) printf '%s' 'Claude Code' ;;
    opencode) printf '%s' 'OpenCode' ;;
    hermes) printf '%s' 'Hermes' ;;
    grok-build) printf '%s' 'Grok Build' ;;
    cursor) printf '%s' 'Cursor' ;;
    droid) printf '%s' 'Factory Droid' ;;
    *) printf '%s' "$1" ;;
  esac
}

supports_restore() {
  case "$1" in
    opencode|droid) return 1 ;;
    *) return 0 ;;
  esac
}

set_reserve_endpoints() {
  ENDPOINT="https://direct.router-cheap.com/v1"
  ANTHROPIC_ENDPOINT="https://direct.router-cheap.com"
}

choose_app() {
  section "$(msg select_app)"
  printf '1. Codex\n'
  printf '2. Claude Code\n'
  printf '3. OpenCode\n'
  printf '4. Hermes\n'
  printf '5. Grok Build\n'
  printf '6. Cursor\n'
  printf '7. Factory Droid\n'
  printf '8. %s\n' "$(msg exit)"
  printf '%s: ' "$(msg choice)"
  local raw
  IFS= read -r raw
  case "$raw" in
    1) APP="codex" ;;
    2) APP="claude-code" ;;
    3) APP="opencode" ;;
    4) APP="hermes" ;;
    5) APP="grok-build" ;;
    6) APP="cursor" ;;
    7) APP="droid" ;;
    8) exit 0 ;;
    *) fail "$(msg bad_choice)" ;;
  esac
}

choose_action() {
  local label
  label="$(app_label "$APP")"
  section "$(fmt_msg select_action "$label")"
  printf '1. %s\n' "$(fmt_msg configure "$label")"
  if supports_restore "$APP"; then
    printf '2. %s\n' "$(fmt_msg restore "$label")"
    printf '3. %s\n' "$(fmt_msg configure_reserve "$label")"
    printf '4. %s\n' "$(msg exit)"
  else
    printf '2. %s\n' "$(msg exit)"
    printf '3. %s\n' "$(fmt_msg configure_reserve "$label")"
  fi
  printf '%s: ' "$(msg choice)"
  local raw
  IFS= read -r raw
  if supports_restore "$APP"; then
    case "$raw" in
      1) ACTION="setup" ;;
      2) ACTION="restore" ;;
      3) ACTION="setup-reserve" ;;
      4) exit 0 ;;
      *) fail "$(msg bad_choice)" ;;
    esac
  else
    case "$raw" in
      1) ACTION="setup" ;;
      2) exit 0 ;;
      3) ACTION="setup-reserve" ;;
      *) fail "$(msg bad_choice)" ;;
    esac
  fi
}

trim_slashes() {
  local value="$1"
  while [[ "$value" == */ ]]; do value="${value%/}"; done
  printf '%s' "$value"
}

normalize_openai_base_url() {
  local url
  url="$(trim_slashes "$1")"
  [[ "$url" =~ ^https?:// ]] || fail "Endpoint must start with http:// or https://."
  [[ "$url" =~ /(chat/completions|responses)$ ]] && fail "Use the base URL https://router.cheap/v1, not a full endpoint path."
  if [[ "$url" != */v1 ]]; then url="$url/v1"; fi
  printf '%s' "$url"
}

normalize_anthropic_base_url() {
  local url
  url="$(trim_slashes "$1")"
  [[ "$url" =~ ^https?:// ]] || fail "Endpoint must start with http:// or https://."
  if [[ "$url" == */v1 ]]; then url="${url%/v1}"; fi
  printf '%s' "$url"
}

join_url_path() {
  local base path
  base="$(trim_slashes "$1")"
  path="${2#/}"
  printf '%s/%s' "$base" "$path"
}

mask_key() {
  local value="${1:-}"
  if [[ -z "$value" ]]; then
    printf '<empty>'
  elif [[ ${#value} -le 12 ]]; then
    printf '%s...' "${value:0:4}"
  else
    printf '%s...%s' "${value:0:7}" "${value: -4}"
  fi
}

shell_quote() {
  printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"
}

has_python3() {
  command -v python3 >/dev/null 2>&1 && python3 -c 'import json' >/dev/null 2>&1
}

body_message() {
  local file="$1"
  if has_python3; then
    python3 - "$file" <<'PY' 2>/dev/null || true
import json, sys
raw = open(sys.argv[1], "r", encoding="utf-8", errors="replace").read()
try:
    data = json.loads(raw)
    err = data.get("error")
    if isinstance(err, dict) and err.get("message"):
        print(err["message"])
    elif data.get("message"):
        print(data["message"])
    elif err is not None:
        print(json.dumps(err, ensure_ascii=False))
    else:
        print(raw[:500])
except Exception:
    print(raw[:500])
PY
  else
    head -c 500 "$file"
  fi
}

explain_http_failure() {
  local status="$1" file="$2" message advice="" base
  message="$(body_message "$file" | tr '\n' ' ')"
  if [[ "$status" == "403" && "$message" =~ [Cc]redit[[:space:]]wallet|[Qq]uota[[:space:]]insufficient|model/family|not[[:space:]]available[[:space:]]for[[:space:]](GPT|Claude) ]]; then
    advice="$(msg cross_family_access_hint)"
  elif [[ "$status" == 5* && "$message" =~ [Nn]ot[[:space:]]implemented|[Uu]nsupported|does[[:space:]]not[[:space:]]support ]]; then
    advice="$(msg model_endpoint_hint)"
  elif [[ "$status" == 5* ]]; then
    advice="$(msg transient_server_hint)"
  fi
  case "$status" in
    401) base="401 unauthorized: invalid/incomplete key or wrong auth header. Details: $message" ;;
    403) base="403 forbidden: key is valid but this model/family is not allowed. Details: $message" ;;
    404) base="404 not found: endpoint is probably wrong. Details: $message" ;;
    429) base="429 rate/concurrency limit: retry later or reduce parallel requests. Details: $message" ;;
    5*) base="$status upstream/server error. Details: $message" ;;
    *) base="$status request failed. Details: $message" ;;
  esac
  [[ -n "$advice" ]] && base+=" $advice"
  fail "$base"
}

router_http() {
  local method="$1" url="$2" body="${3:-}" output_file="$4" status attempt
  command -v curl >/dev/null 2>&1 || fail "curl is required for endpoint testing. Install curl or rerun with --skip-endpoint-test."
  for attempt in 1 2; do
    if [[ -n "$body" ]]; then
      status="$(curl -sS -L -X "$method" "$url" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -H "User-Agent: routercheap-setup/$SCRIPT_VERSION" \
        --data "$body" --connect-timeout 20 --max-time 75 \
        -o "$output_file" \
        -w "%{http_code}")" || status="000"
    else
      status="$(curl -sS -L -X "$method" "$url" \
        -H "Authorization: Bearer $API_KEY" \
        -H "User-Agent: routercheap-setup/$SCRIPT_VERSION" \
        --connect-timeout 20 --max-time 75 \
        -o "$output_file" \
        -w "%{http_code}")" || status="000"
    fi
    if [[ "$attempt" -eq 1 && ( "$status" == "429" || "$status" == 5* ) ]]; then
      sleep 1
      continue
    fi
    setup_record_probe "$method" "$url" "$status"
    printf '%s' "$status"
    return 0
  done
}

probe_is_transient() {
  local status="$1"
  [[ "$status" == "000" || "$status" == "408" || "$status" == "429" || "$status" == 5* ]]
}

warn_nonfatal_probe() {
  local status="$1" label="$2"
  if [[ "$status" == "000" ]]; then
    warn "$(msg probe_timeout)"
  else
    warn "$(fmt_msg probe_nonfatal "$label" "$status")"
  fi
}

setup_record_probe() {
  local method="$1" url="$2" status="$3" target authority path
  target="${url#*://}"
  authority="${target%%/*}"
  path="/${target#*/}"
  [[ "$target" == */* ]] || path="/"
  SETUP_LAST_PROBE_METHOD="$method"
  SETUP_LAST_PROBE_PATH="${path%%\?*}"
  SETUP_LAST_PROBE_STATUS="$status"
  case "$SETUP_LAST_PROBE_PATH" in
    */models) SETUP_MODELS_PROBE_STATUS="$status" ;;
    */responses) SETUP_RESPONSES_PROBE_STATUS="$status" ;;
  esac
}

model_ids_from_body() {
  local file="$1"
  if has_python3; then
    python3 - "$file" <<'PY' 2>/dev/null || true
import json, sys
raw = open(sys.argv[1], "r", encoding="utf-8", errors="replace").read()
try:
    data = json.loads(raw)
except Exception:
    sys.exit(0)
items = []
if isinstance(data, dict):
    if isinstance(data.get("data"), list):
        items = data["data"]
    elif isinstance(data.get("models"), list):
        items = data["models"]
elif isinstance(data, list):
    items = data
seen = set()
for item in items:
    value = None
    if isinstance(item, dict):
        raw_value = item.get("id") or item.get("name")
        if isinstance(raw_value, str):
            value = raw_value
    elif isinstance(item, str):
        value = item
    if not value:
        continue
    if value.startswith("models/"):
        value = value.split("/", 1)[1]
    if value and value not in seen:
        seen.add(value)
        print(value)
PY
  else
    grep -Eo '"(id|name)"[[:space:]]*:[[:space:]]*"[^"]+"' "$file" 2>/dev/null \
      | sed -E 's/^"(id|name)"[[:space:]]*:[[:space:]]*"([^"]+)".*$/\2/; s#^models/##' \
      | awk 'NF && !seen[$0]++'
  fi
}

contains_model_id() {
  local models="$1" wanted="$2"
  [[ -n "$wanted" ]] && printf '%s\n' "$models" | grep -Fxq "$wanted"
}

is_setup_chat_model() {
  local name lower
  name="$1"
  lower="$(printf '%s' "$name" | tr '[:upper:]' '[:lower:]')"
  case "$lower" in
    *embedding*|*embed*|*rerank*|*whisper*|*tts*|*audio*|*speech*|*transcrib*|*moderation*|*image*|*dall-e*|*midjourney*|*suno*)
      return 1
      ;;
  esac
  return 0
}

model_supports_image_input() {
  local lower
  lower="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$lower" in
    o1-mini|o1-mini[-_.:]*|o3-mini|o3-mini[-_.:]*) return 1 ;;
	    kimi-k3|kimi-k3[-_.:]*|deepseek-v4-flash-vision-exp|deepseek-v4-flash-vision-exp[-_.:]*|claude-*|grok-4.5|grok-4.5[-_.:]*|grok-4.6|grok-4.6[-_.:]*|grok-4.7|grok-4.7[-_.:]*|gpt-6-astra|gpt-6-astra[-_.:]*|gpt-5|gpt-5[-_.:]*|gpt-4o|gpt-4o[-_.:]*|gpt-4.1|gpt-4.1[-_.:]*|o1|o1[-_.:]*|o3|o3[-_.:]*|o4-mini|o4-mini[-_.:]*) return 0 ;;
    *) return 1 ;;
  esac
}

model_matches_family() {
  local name="$1" family="${2:-any}" lower
  [[ "$family" == "any" ]] && return 0
  lower="$(printf '%s' "$name" | tr '[:upper:]' '[:lower:]')"
  case "$family" in
    claude) [[ "$lower" == *claude* ]] ;;
    *) return 0 ;;
  esac
}

choose_available_model() {
  local preferred="$1" models="$2" candidates="$3" family="${4:-any}" candidate
  if contains_model_id "$models" "$preferred" && is_setup_chat_model "$preferred" && model_matches_family "$preferred" "$family"; then
    printf '%s' "$preferred"
    return 0
  fi
  while IFS= read -r candidate; do
    [[ -n "$candidate" ]] || continue
    if contains_model_id "$models" "$candidate" && is_setup_chat_model "$candidate" && model_matches_family "$candidate" "$family"; then
      printf '%s' "$candidate"
      return 0
    fi
  done <<< "$candidates"
  while IFS= read -r candidate; do
    [[ -n "$candidate" ]] || continue
    if is_setup_chat_model "$candidate" && model_matches_family "$candidate" "$family"; then
      printf '%s' "$candidate"
      return 0
    fi
  done <<< "$models"
  return 1
}

model_preview() {
  local models="$1" max="${2:-8}" count=0 output="" model
  while IFS= read -r model; do
    [[ -n "$model" ]] || continue
    if [[ -z "$output" ]]; then output="$model"; else output="$output, $model"; fi
    count=$((count + 1))
    [[ "$count" -ge "$max" ]] && break
  done <<< "$models"
  printf '%s' "${output:-<none>}"
}

available_chat_models() {
  local source model
  source="${OPENAI_MODELS:-$MODEL}"
  while IFS= read -r model; do
    [[ -n "$model" ]] || continue
    is_setup_chat_model "$model" || continue
    printf '%s\n' "$model"
  done <<< "$source" | awk 'NF && !seen[$0]++'
}

ranked_chat_models() {
  local models seen="" candidate
  models="$(available_chat_models)"
  while IFS= read -r candidate; do
    [[ -n "$candidate" ]] || continue
    contains_model_id "$models" "$candidate" || continue
    is_setup_chat_model "$candidate" || continue
    contains_model_id "$seen" "$candidate" && continue
    printf '%s\n' "$candidate"
    seen+="$candidate"$'\n'
  done <<< "$OPENAI_MODEL_CANDIDATES"
  while IFS= read -r candidate; do
    [[ -n "$candidate" ]] || continue
    is_setup_chat_model "$candidate" || continue
    contains_model_id "$seen" "$candidate" && continue
    printf '%s\n' "$candidate"
    seen+="$candidate"$'\n'
  done <<< "$models"
}

model_family() {
  local lower
  lower="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$lower" in
    claude-*) printf '%s' claude ;;
    grok-*) printf '%s' grok ;;
    gpt-*|o[0-9]*) printf '%s' gpt ;;
    *) printf '%s' "$lower" ;;
  esac
}

model_probe_candidates() {
  local family="${1:-any}" candidate seen=""
  printf '%s\n' "$MODEL"
  seen="$MODEL"$'\n'
  [[ "$APP" == "grok-build" ]] && return 0
  while IFS= read -r candidate; do
    [[ -n "$candidate" ]] || continue
    contains_model_id "$seen" "$candidate" && continue
    if [[ "$APP" == "cursor" ]] && ! cursor_compatible_model "$candidate"; then
      continue
    fi
    if [[ "$family" == "responses" ]] && [[ "$(model_family "$candidate")" != "gpt" ]]; then
      continue
    fi
    printf '%s\n' "$candidate"
    seen+="$candidate"$'\n'
  done < <(ranked_chat_models)
}

is_model_access_failure() {
  local status="$1" file="$2" message
  [[ "$status" == "403" ]] || return 1
  message="$(body_message "$file" | tr '[:upper:]' '[:lower:]' | tr '\n' ' ')"
  [[ "$message" =~ model|family|credit[[:space:]]wallet|quota|disabled|access ]]
}

is_retryable_model_probe_failure() {
  local status="$1" file="$2" message
  case "$status" in 400|403|404) ;; *) return 1 ;; esac
  message="$(body_message "$file" | tr '[:upper:]' '[:lower:]' | tr '\n' ' ')"
  [[ "$message" =~ model|family|disabled|unsupported|unknown|not[[:space:]]available|not[[:space:]]found ]]
}

limit_openai_models_to_family() {
  local selected_family candidate filtered=""
  selected_family="$(model_family "$1")"
  while IFS= read -r candidate; do
    [[ -n "$candidate" ]] || continue
    [[ "$(model_family "$candidate")" == "$selected_family" ]] || continue
    filtered+="$candidate"$'\n'
  done <<< "$OPENAI_MODELS"
  [[ -n "$filtered" ]] && OPENAI_MODELS="${filtered%$'\n'}"
}

discover_openai_models() {
  local out status
  [[ -n "$OPENAI_MODELS" ]] && return 0
  [[ "$SKIP_ENDPOINT_TEST" -eq 1 ]] && return 0
  set_setup_step "model_discovery"
  out="$(mktemp)"
  status="$(router_http GET "$(join_url_path "$ENDPOINT" models)" "" "$out")"
  if probe_is_transient "$status"; then
    warn_nonfatal_probe "$status" "GET /v1/models"
    OPENAI_MODELS_VERIFIED=0
    OPENAI_MODELS="$MODEL"
    rm -f "$out"
    return 0
  fi
  [[ "$status" =~ ^2 ]] || explain_http_failure "$status" "$out"
  OPENAI_MODELS="$(model_ids_from_body "$out")"
  OPENAI_MODELS_VERIFIED=1
  rm -f "$out"
  [[ -n "$OPENAI_MODELS" ]] || fail "No OpenAI-compatible models are available for this key."
}

discover_claude_models() {
  local out status url
  [[ -n "$CLAUDE_MODELS" ]] && return 0
  [[ "$SKIP_ENDPOINT_TEST" -eq 1 ]] && return 0
  set_setup_step "model_discovery"
  out="$(mktemp)"
  url="$(join_url_path "$ANTHROPIC_ENDPOINT" v1/models)"
  command -v curl >/dev/null 2>&1 || fail "curl is required for endpoint testing. Install curl or rerun with --skip-endpoint-test."
  status="$(curl -sS -L -X GET "$url" \
    -H "Authorization: Bearer $API_KEY" \
    -H "x-api-key: $API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "User-Agent: routercheap-setup/$SCRIPT_VERSION" \
    --connect-timeout 20 --max-time 75 \
    -o "$out" \
    -w "%{http_code}")" || status="000"
  if probe_is_transient "$status"; then
    warn_nonfatal_probe "$status" "GET /v1/models"
    CLAUDE_MODELS_VERIFIED=0
    CLAUDE_MODELS="$CLAUDE_MODEL"
    rm -f "$out"
    return 0
  fi
  [[ "$status" =~ ^2 ]] || explain_http_failure "$status" "$out"
  CLAUDE_MODELS="$(model_ids_from_body "$out")"
  CLAUDE_MODELS_VERIFIED=1
  rm -f "$out"
  [[ -n "$CLAUDE_MODELS" ]] || fail "No Anthropic-compatible models are available for this key."
}

ensure_openai_model() {
  local selected
  [[ "$SKIP_ENDPOINT_TEST" -eq 1 ]] && return 0
  discover_openai_models
  selected="$(choose_available_model "$MODEL" "$OPENAI_MODELS" "$OPENAI_MODEL_CANDIDATES" any || true)"
  [[ -n "$selected" ]] || fail "No chat model suitable for app setup is available for this key. Available models: $(model_preview "$OPENAI_MODELS")"
  if [[ "$selected" != "$MODEL" ]]; then
    warn "Model '$MODEL' is not available for this key; using '$selected'. Available models: $(model_preview "$OPENAI_MODELS")"
    MODEL="$selected"
  fi
}

ensure_codex_model() {
  local selected
  [[ "$SKIP_ENDPOINT_TEST" -eq 1 ]] && return 0
  discover_openai_models
  selected="$(choose_available_model "$MODEL" "$OPENAI_MODELS" "$OPENAI_MODEL_CANDIDATES" responses || true)"
  if [[ -z "$selected" ]]; then
    if [[ "$ALLOW_MISSING_MODEL" -eq 1 ]]; then
      warn "Model '$MODEL' is not listed as Responses-compatible for this key; keeping it because --allow-missing-model was supplied."
      return 0
    fi
    fail "No GPT/Responses-compatible model is available for this key. Available models: $(model_preview "$OPENAI_MODELS")"
  fi
  if [[ "$selected" != "$MODEL" ]]; then
    warn "Model '$MODEL' is not available for Codex Responses; using '$selected'. Available models: $(model_preview "$OPENAI_MODELS")"
    MODEL="$selected"
  fi
}

ensure_claude_model() {
  local selected
  [[ "$SKIP_ENDPOINT_TEST" -eq 1 ]] && return 0
  discover_claude_models
  selected="$(choose_available_model "$CLAUDE_MODEL" "$CLAUDE_MODELS" "$CLAUDE_MODEL_CANDIDATES" claude || true)"
  [[ -n "$selected" ]] || fail "No Claude model is available for this key. Available models: $(model_preview "$CLAUDE_MODELS"). $(msg claude_model_access_hint)"
  if [[ "$selected" != "$CLAUDE_MODEL" ]]; then
    warn "Claude model '$CLAUDE_MODEL' is not available for this key; using '$selected'. Available models: $(model_preview "$CLAUDE_MODELS")"
    CLAUDE_MODEL="$selected"
  fi
}

ensure_grok_model() {
  MODEL="$GROK_MODEL"
  [[ "$SKIP_ENDPOINT_TEST" -eq 1 ]] && return 0
  discover_openai_models
  if ! printf '%s\n' "$OPENAI_MODELS" | grep -Fxq "$GROK_MODEL"; then
    fail "Model '$GROK_MODEL' is not available for this key. Available models: $(model_preview "$OPENAI_MODELS"). $(msg cross_family_access_hint)"
  fi
}

cursor_compatible_model() {
  local model
  model="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$model" in
    claude-*|gemini-*) return 1 ;;
    *) [[ -n "$model" ]] ;;
  esac
}

ensure_cursor_model() {
  local selected=""
  cursor_compatible_model "$MODEL" && return 0
  while IFS= read -r candidate; do
    cursor_compatible_model "$candidate" || continue
    if [[ "$candidate" == "gpt-6-astra" ]]; then selected="$candidate"; break; fi
    [[ -n "$selected" ]] || selected="$candidate"
  done < <(if [[ -n "$OPENAI_MODELS" ]]; then printf '%s\n' "$OPENAI_MODELS"; else printf '%s\n' "$OPENAI_MODEL_CANDIDATES"; fi)
  [[ -n "$selected" ]] || fail "Cursor's OpenAI Base URL override cannot route Claude/Anthropic models, and no compatible GPT/Grok model is available for this key."
  warn "Model '$MODEL' cannot use Cursor's OpenAI Base URL override; using '$selected'."
  MODEL="$selected"
}

choose_default_openai_model_interactive() {
  local models count default label raw n selected i model
  case "$APP" in
    hermes|cursor|droid) ;;
    *) return 0 ;;
  esac
  [[ "$SKIP_ENDPOINT_TEST" -eq 1 ]] && return 0
  [[ "$MODEL_EXPLICIT" -eq 1 ]] && return 0
  [[ -t 0 ]] || return 0

  models="$(ranked_chat_models)"
  if [[ "$APP" == "cursor" ]]; then
    models="$(while IFS= read -r model; do cursor_compatible_model "$model" && printf '%s\n' "$model"; done <<< "$models")"
  fi
  [[ -n "$models" ]] || return 0
  count="$(printf '%s\n' "$models" | awk 'NF { count++ } END { print count + 0 }')"
  [[ "$count" -gt 0 ]] || return 0
  if [[ "$count" -eq 1 ]]; then
    MODEL="$(printf '%s\n' "$models" | awk 'NF { print; exit }')"
    return 0
  fi

  default="$(choose_available_model "$MODEL" "$models" "$OPENAI_MODEL_CANDIDATES" any || true)"
  [[ -n "$default" ]] || default="$(printf '%s\n' "$models" | awk 'NF { print; exit }')"
  label="$(app_label "$APP")"
  set_setup_step "model_choice"

  while true; do
    section "$(fmt_msg select_default_model "$label")"
    i=1
    while IFS= read -r model; do
      [[ -n "$model" ]] || continue
      if [[ "$model" == "$default" ]]; then
        printf '%d) %s (recommended)\n' "$i" "$model"
      else
        printf '%d) %s\n' "$i" "$model"
      fi
      i=$((i + 1))
    done <<< "$models"
    printf '%s\n' "$(fmt_msg select_default_model_hint "" "$default")"
    printf '%s: ' "$(msg choice)"
    IFS= read -r raw
    raw="${raw#"${raw%%[![:space:]]*}"}"
    raw="${raw%"${raw##*[![:space:]]}"}"
    if [[ -z "$raw" ]]; then
      selected="$default"
      break
    fi
    if [[ "$raw" =~ ^[0-9]+$ ]]; then
      n=$((10#$raw))
      if (( n >= 1 && n <= count )); then
        selected="$(printf '%s\n' "$models" | awk -v n="$n" 'NF { i++; if (i == n) { print; exit } }')"
        [[ -n "$selected" ]] && break
      fi
    fi
    warn "$(msg invalid_model_choice)"
  done

  MODEL="$selected"
  ok "$(msg selected_default_model): $MODEL"
}

prepare_setup_model() {
  case "$APP" in
    codex) ensure_codex_model ;;
    claude-code) ;;
    grok-build) ensure_grok_model ;;
    cursor) ensure_openai_model; ensure_cursor_model ;;
    *) ensure_openai_model ;;
  esac
}

install_codex_if_missing() {
  if command -v codex >/dev/null 2>&1 || [[ "$INSTALL_CODEX_IF_MISSING" -ne 1 ]]; then
    return 0
  fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    warn "DryRun: would run the official standalone Codex installer from https://chatgpt.com/codex/install.sh."
    return 0
  fi
  command -v curl >/dev/null 2>&1 || { warn "codex command was not found and curl is unavailable; install Codex manually before testing."; return 0; }
  warn "codex command was not found. Running the official standalone installer..."
  curl -fsSL https://chatgpt.com/codex/install.sh | sh
}

setup_os_name() {
  case "$(uname -s 2>/dev/null || true)" in
    Darwin*) printf '%s' 'macos' ;;
    *) printf '%s' 'linux' ;;
  esac
}

new_setup_session_id() {
  local candidate=""
  if command -v uuidgen >/dev/null 2>&1; then
    candidate="$(uuidgen 2>/dev/null | tr '[:upper:]' '[:lower:]' || true)"
  elif [[ -r /proc/sys/kernel/random/uuid ]]; then
    candidate="$(tr '[:upper:]' '[:lower:]' < /proc/sys/kernel/random/uuid 2>/dev/null || true)"
  fi
  [[ -n "$candidate" ]] || candidate="$(date +%s 2>/dev/null || printf '0')-$$-$RANDOM"
  printf '%s' "$candidate"
}

setup_duration_ms() {
  local now
  now="$(date +%s 2>/dev/null || true)"
  if [[ "$now" =~ ^[0-9]+$ && "${TELEMETRY_STARTED_AT:-0}" =~ ^[0-9]+$ && "$now" -ge "${TELEMETRY_STARTED_AT:-0}" ]]; then
    printf '%s' "$(( (now - TELEMETRY_STARTED_AT) * 1000 ))"
  fi
}

send_setup_telemetry() {
  local action="$1" result="$2" os body out status duration_ms
  [[ -n "$TELEMETRY_ENDPOINT" ]] || return 0
  [[ -n "${API_KEY:-}" ]] || return 0
  [[ "$DRY_RUN" -eq 0 ]] || return 0
  if [[ "$result" == "started" ]]; then warn "$(msg telemetry)"; fi
  command -v curl >/dev/null 2>&1 || { warn "$(msg telemetry_failed)"; return 0; }
  os="$(setup_os_name)"
  body="{\"app\":\"$(json_escape "$APP")\",\"os\":\"$(json_escape "$os")\",\"action\":\"$(json_escape "$action")\",\"result\":\"$(json_escape "$result")\",\"script_version\":\"$(json_escape "$SCRIPT_VERSION")\",\"script_language\":\"$(json_escape "$LANG_CODE")\",\"dry_run\":false"
  if [[ -n "${TELEMETRY_SESSION_ID:-}" ]]; then
    body+=",\"session_id\":\"$(json_escape "$TELEMETRY_SESSION_ID")\""
  fi
  if [[ "$result" != "started" ]]; then
    duration_ms="$(setup_duration_ms)"
    if [[ "$duration_ms" =~ ^[0-9]+$ && "$duration_ms" -gt 0 ]]; then
      body+=",\"duration_ms\":${duration_ms}"
    fi
  fi
  if [[ "$APP" == "codex" ]]; then
    body+=",\"diagnostics\":$(codex_setup_diagnostics_json \"$ENDPOINT\" \"$MODEL\" \"ROUTER_CHEAP_API_KEY\")"
  fi
  if [[ "$result" == "failed" ]]; then
    if [[ -n "${TELEMETRY_ERROR_MESSAGE:-}" ]]; then
      body+=",\"error_message\":\"$(json_escape "$TELEMETRY_ERROR_MESSAGE")\""
    fi
    if [[ -n "${TELEMETRY_ERROR_STEP:-}" ]]; then
      body+=",\"error_step\":\"$(json_escape "$TELEMETRY_ERROR_STEP")\""
    fi
    if [[ -n "${TELEMETRY_ERROR_FUNCTION:-}" ]]; then
      body+=",\"error_function\":\"$(json_escape "$TELEMETRY_ERROR_FUNCTION")\""
    fi
    if [[ "${TELEMETRY_ERROR_LINE:-0}" -gt 0 ]]; then
      body+=",\"error_line\":${TELEMETRY_ERROR_LINE}"
    fi
    if [[ "${TELEMETRY_EXIT_CODE:-0}" -ne 0 ]]; then
      body+=",\"exit_code\":${TELEMETRY_EXIT_CODE}"
    fi
  fi
  body+="}"
  out="$(mktemp)"
  status="$(curl -sS -L -X POST "$TELEMETRY_ENDPOINT" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -H "User-Agent: routercheap-setup/$SCRIPT_VERSION" \
    --data "$body" \
    -o "$out" \
    -w "%{http_code}")" || {
      rm -f "$out"
      warn "$(msg telemetry_failed)"
      return 0
    }
  rm -f "$out"
  [[ "$status" =~ ^2 ]] || warn "$(msg telemetry_failed)"
}

test_openai_key() {
  local path="${1:-chat}" out status body candidate initial_model access_limited=0 last_status=""
  if [[ "$SKIP_ENDPOINT_TEST" -eq 1 ]]; then warn "Endpoint test skipped."; return; fi
  set_setup_step "endpoint_test"
  section "$(msg testing)"
  ensure_openai_model
  [[ "$OPENAI_MODELS_VERIFIED" -eq 1 ]] && ok "GET /v1/models"
  if [[ "$SKIP_LIVE_MODEL_TEST" -eq 1 ]]; then
    warn "Skipped live model test. /v1/models auth passed, but model execution was not tested."
    return 0
  fi
  out="$(mktemp)"
  initial_model="$MODEL"
  while IFS= read -r candidate; do
    [[ -n "$candidate" ]] || continue
    if [[ "$path" == "responses" ]]; then
      body="{\"model\":\"$candidate\",\"input\":\"Reply with OK.\",\"max_output_tokens\":8,\"stream\":false}"
      status="$(router_http POST "$(join_url_path "$ENDPOINT" responses)" "$body" "$out")"
    else
      body="{\"model\":\"$candidate\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with OK.\"}],\"max_tokens\":8,\"stream\":false}"
      status="$(router_http POST "$(join_url_path "$ENDPOINT" chat/completions)" "$body" "$out")"
    fi
    last_status="$status"
    if probe_is_transient "$status"; then
      warn_nonfatal_probe "$status" "POST /v1/$path"
      rm -f "$out"
      return 0
    fi
    if [[ "$status" =~ ^2 ]]; then
      MODEL="$candidate"
      if [[ "$MODEL" != "$initial_model" ]]; then
        warn "$(msg model_fallback_selected): $MODEL"
        if [[ "$access_limited" -eq 1 ]]; then
          limit_openai_models_to_family "$MODEL"
          warn "$(fmt_msg model_catalog_limited "" "$(model_family "$MODEL")")"
          warn "$(msg cross_family_access_hint)"
        fi
      fi
      if [[ "$path" == "responses" ]]; then ok "POST /v1/responses"; else ok "POST /v1/chat/completions"; fi
      rm -f "$out"
      return 0
    fi
    is_model_access_failure "$status" "$out" && access_limited=1
    if is_retryable_model_probe_failure "$status" "$out" && [[ "$APP" != "grok-build" ]]; then
      warn "$(fmt_msg model_probe_retry "" "$candidate")"
      continue
    fi
    explain_http_failure "$status" "$out"
  done < <(model_probe_candidates "$path")
  explain_http_failure "${last_status:-500}" "$out"
}

test_anthropic_key() {
  local out status body url
  if [[ "$SKIP_ENDPOINT_TEST" -eq 1 ]]; then warn "Endpoint test skipped."; return; fi
  set_setup_step "endpoint_test"
  section "$(msg testing)"
  ensure_claude_model
  [[ "$CLAUDE_MODELS_VERIFIED" -eq 1 ]] && ok "GET /v1/models"
  out="$(mktemp)"
  body="{\"model\":\"$CLAUDE_MODEL\",\"max_tokens\":8,\"messages\":[{\"role\":\"user\",\"content\":\"Reply with OK.\"}]}"
  url="$(join_url_path "$ANTHROPIC_ENDPOINT" v1/messages)"
  command -v curl >/dev/null 2>&1 || fail "curl is required for endpoint testing. Install curl or rerun with --skip-endpoint-test."
  status="$(curl -sS -L -X POST "$url" \
    -H "Authorization: Bearer $API_KEY" \
    -H "x-api-key: $API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "Content-Type: application/json" \
    -H "User-Agent: routercheap-setup/$SCRIPT_VERSION" \
    --data "$body" --connect-timeout 20 --max-time 75 \
    -o "$out" \
    -w "%{http_code}")" || status="000"
  if probe_is_transient "$status"; then
    warn_nonfatal_probe "$status" "POST /v1/messages"
    rm -f "$out"
    return 0
  fi
  [[ "$status" =~ ^2 ]] || explain_http_failure "$status" "$out"
  ok "POST /v1/messages"
  rm -f "$out"
}

test_coding_agent_key() {
  local api_mode out status body url candidate probe_label initial_model access_limited=0 last_status=""
  if [[ "$SKIP_ENDPOINT_TEST" -eq 1 ]]; then warn "Endpoint test skipped."; return; fi
  set_setup_step "endpoint_test"
  section "$(msg testing)"
  discover_openai_models
  [[ "$OPENAI_MODELS_VERIFIED" -eq 1 ]] && ok "GET /v1/models"
  out="$(mktemp)"
  initial_model="$MODEL"
  while IFS= read -r candidate; do
    [[ -n "$candidate" ]] || continue
    api_mode="$(hermes_api_mode "$candidate")"
    case "$api_mode" in
      anthropic_messages)
        probe_label="POST /v1/messages"
        body="{\"model\":\"$candidate\",\"max_tokens\":8,\"messages\":[{\"role\":\"user\",\"content\":\"Reply with OK.\"}]}"
        url="$(join_url_path "$ANTHROPIC_ENDPOINT" v1/messages)"
        command -v curl >/dev/null 2>&1 || fail "curl is required for endpoint testing. Install curl or rerun with --skip-endpoint-test."
        status="$(curl -sS -L -X POST "$url" \
          -H "Authorization: Bearer $API_KEY" \
          -H "x-api-key: $API_KEY" \
          -H "anthropic-version: 2023-06-01" \
          -H "Content-Type: application/json" \
          -H "User-Agent: routercheap-setup/$SCRIPT_VERSION" \
          --data "$body" --connect-timeout 20 --max-time 75 \
          -o "$out" \
          -w "%{http_code}")" || status="000"
        ;;
      codex_responses)
        probe_label="POST /v1/responses"
        body="{\"model\":\"$candidate\",\"input\":\"Reply with OK.\",\"max_output_tokens\":8,\"stream\":false}"
        status="$(router_http POST "$(join_url_path "$ENDPOINT" responses)" "$body" "$out")"
        ;;
      *)
        probe_label="POST /v1/chat/completions"
        body="{\"model\":\"$candidate\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with OK.\"}],\"max_tokens\":8,\"stream\":false}"
        status="$(router_http POST "$(join_url_path "$ENDPOINT" chat/completions)" "$body" "$out")"
        ;;
    esac
      last_status="$status"
    if probe_is_transient "$status"; then
      warn_nonfatal_probe "$status" "$probe_label"
      rm -f "$out"
      return 0
    fi
    if [[ "$status" =~ ^2 ]]; then
      MODEL="$candidate"
      if [[ "$MODEL" != "$initial_model" ]]; then
        warn "$(msg model_fallback_selected): $MODEL"
        if [[ "$access_limited" -eq 1 ]]; then
          limit_openai_models_to_family "$MODEL"
          warn "$(fmt_msg model_catalog_limited "" "$(model_family "$MODEL")")"
          warn "$(msg cross_family_access_hint)"
        fi
      fi
      case "$api_mode" in anthropic_messages) ok "POST /v1/messages" ;; codex_responses) ok "POST /v1/responses" ;; *) ok "POST /v1/chat/completions" ;; esac
      rm -f "$out"
      return 0
    fi
    is_model_access_failure "$status" "$out" && access_limited=1
    if is_retryable_model_probe_failure "$status" "$out"; then
      warn "$(fmt_msg model_probe_retry "" "$candidate")"
      continue
    fi
    explain_http_failure "$status" "$out"
  done < <(model_probe_candidates)
  explain_http_failure "${last_status:-500}" "$out"
}

backup_file() {
  local path="$1" backup
  if [[ -f "$path" ]]; then
    backup="$path.routercheap-backup-$(date +%Y%m%d-%H%M%S)"
    if [[ "$DRY_RUN" -eq 1 ]]; then
      ok "Would create backup: $backup"
    else
      cp -p "$path" "$backup"
      ok "Backup: $backup"
    fi
  fi
}

save_text_file() {
  local path="$1" tmp="$2"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '\n# %s\n' "$path"
    cat "$tmp"
    return
  fi
  local directory staged
  directory="$(dirname "$path")"
  mkdir -p "$directory"
  staged="$directory/.$(basename "$path").tmp.$$"
  rm -f "$staged"
  if [[ -f "$path" ]]; then
    cp -p "$path" "$staged"
    cat "$tmp" > "$staged"
  else
    (umask 077; cat "$tmp" > "$staged")
  fi
  mv -f "$staged" "$path"
}

profile_path() {
  if [[ "${SHELL:-}" == *zsh* || "$(uname -s 2>/dev/null || true)" == "Darwin" ]]; then
    printf '%s/.zshrc' "$HOME"
  else
    printf '%s/.bashrc' "$HOME"
  fi
}

remove_marked_block() {
  local source="$1" dest="$2" begin="$3" end="$4"
  if [[ -f "$source" ]]; then
    awk -v begin="$begin" -v end="$end" '
      $0 == begin { skip = 1; next }
      $0 == end { skip = 0; next }
      !skip { print }
    ' "$source" > "$dest"
  else
    : > "$dest"
  fi
}

write_profile_block() {
  local app="$1" block_file="$2" path begin end tmp
  path="$(profile_path)"
  begin="# routercheap $app setup begin"
  end="# routercheap $app setup end"
  tmp="$(mktemp)"
  remove_marked_block "$path" "$tmp" "$begin" "$end"
  {
    cat "$tmp"
    printf '\n%s\n' "$begin"
    cat "$block_file"
    printf '%s\n' "$end"
  } > "$tmp.next"
  backup_file "$path"
  save_text_file "$path" "$tmp.next"
  rm -f "$tmp" "$tmp.next"
}

remove_profile_block() {
  local app="$1" path begin end tmp
  path="$(profile_path)"
  begin="# routercheap $app setup begin"
  end="# routercheap $app setup end"
  if [[ ! -f "$path" ]]; then return 0; fi
  tmp="$(mktemp)"
  remove_marked_block "$path" "$tmp" "$begin" "$end"
  backup_file "$path"
  save_text_file "$path" "$tmp"
  rm -f "$tmp"
}

codex_config_path() {
  printf '%s/config.toml' "${CODEX_HOME:-$HOME/.codex}"
}

codex_profile_files() {
  local home="${CODEX_HOME:-$HOME/.codex}"
  [[ -d "$home" ]] || return 0
  find "$home" -maxdepth 1 -type f -name '*.config.toml' -print 2>/dev/null || true
}

stop_codex_for_setup() {
  CODEX_RESTART_COUNT=0
  CODEX_RESTART_COMMAND=""
  local pids pid command_line command_name command_path
  if ! command -v pgrep >/dev/null 2>&1; then return 0; fi
  pids="$(pgrep -x codex 2>/dev/null || true)"
  [[ -n "$pids" ]] || return 0
  if [[ "$RESTART_CODEX" -ne 1 ]]; then
    warn "Codex is already running. It will not see the new API-key environment variable until fully restarted. Use --restart-codex for a safe bare-CLI restart, or close Codex and rerun setup."
    return 0
  fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    warn "DryRun: would close and relaunch $(printf '%s\n' "$pids" | wc -l | tr -d ' ') bare standalone Codex process(es)."
    return 0
  fi
  CODEX_RESTART_COMMAND="$(command -v codex)"
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    command_line="$(ps -p "$pid" -o args= 2>/dev/null | sed 's/^[[:space:]]*//')"
    if [[ "$command_line" != "${command_line%%[[:space:]]*}" ]]; then
      CODEX_RESTART_COUNT=0
      CODEX_RESTART_COMMAND=""
      CODEX_RESTART_COUNT=0
      fail "Codex Desktop/IDE/app-server or a CLI with arguments is running. Close it fully and rerun setup so it can receive the new API-key environment. Setup cannot safely reconfigure an already-running Codex process."
      return 0
    fi
    command_path="${command_line#\"}"; command_path="${command_path%\"}"
    command_name="$(basename "$command_path")"
    if [[ "$command_name" != "codex" ]]; then
      CODEX_RESTART_COUNT=0
      CODEX_RESTART_COMMAND=""
      fail "Codex Desktop/IDE/app-server or a CLI with arguments is running. Close it fully and rerun setup so it can receive the new API-key environment. Setup cannot safely reconfigure an already-running Codex process."
      return 0
    fi
  done <<< "$pids"
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    command_line="$(ps -p "$pid" -o args= 2>/dev/null | sed 's/^[[:space:]]*//')"
    command_name="$(basename "${command_line%% *}")"
    kill -TERM "$pid" 2>/dev/null || true
    CODEX_RESTART_COUNT=$((CODEX_RESTART_COUNT + 1))
  done <<< "$pids"
  local attempt
  for ((attempt = 0; attempt < 50; attempt++)); do
    sleep 0.1
    [[ -z "$(pgrep -x codex 2>/dev/null || true)" ]] && break
  done
  if [[ -n "$(pgrep -x codex 2>/dev/null || true)" ]]; then
    while IFS= read -r pid; do [[ -n "$pid" ]] && kill -KILL "$pid" 2>/dev/null || true; done < <(pgrep -x codex 2>/dev/null || true)
  fi
  ok "Closed running standalone Codex process(es) before changing configuration."
}

start_codex_after_setup() {
  local count="$CODEX_RESTART_COUNT" i
  [[ "$DRY_RUN" -eq 0 && "$count" -gt 0 && -n "$CODEX_RESTART_COMMAND" ]] || return 0
  for ((i = 0; i < count; i++)); do
    "$CODEX_RESTART_COMMAND" >/dev/null 2>&1 &
  done
  CODEX_RESTART_COUNT=0
  CODEX_RESTART_COMMAND=""
  ok "Relaunched Codex after configuration."
}

codex_auth_diagnostics() {
  local config_path="$1" profile_names
  [[ -n "${ROUTER_CHEAP_API_KEY:-}" ]] || fail "Codex auth diagnostic failed: ROUTER_CHEAP_API_KEY is missing from the current process."
  [[ -n "$(printenv ROUTER_CHEAP_API_KEY 2>/dev/null || true)" ]] || fail "Codex auth diagnostic failed: ROUTER_CHEAP_API_KEY is missing from the current process."
  ok "Codex auth: provider 'routercheap' uses env_key 'ROUTER_CHEAP_API_KEY' (present in the current process and shell profile)."
  profile_names="$(codex_profile_files | sed 's#^.*/##' | tr '\n' ',' | sed 's/,$//')"
  if [[ -n "$profile_names" ]]; then
    warn "Found named Codex profile file(s): $profile_names. A profile selected with 'codex --profile <name>' can override model/model_provider from $config_path; verify the selected profile after restart."
  fi
}

codex_runtime_probe() {
  local model_name="${1:-$MODEL}" codex_bin help_text probe_dir stdout_file stderr_file output code pid i
  if [[ "$SKIP_CODEX_RUNTIME_TEST" -eq 1 ]]; then
    CODEX_RUNTIME_PROBE_STATUS="skipped"
    warn "Codex runtime probe skipped by request."
    return 0
  fi
  codex_bin="$(command -v codex 2>/dev/null || true)"
  if [[ -z "$codex_bin" ]]; then
    CODEX_RUNTIME_PROBE_STATUS="codex-missing"
    warn "Codex runtime probe skipped because the codex command is not available."
    return 0
  fi
  help_text="$("$codex_bin" exec --help 2>&1 || true)"
  if ! printf '%s' "$help_text" | grep -Eq -- '--ephemeral([[:space:]]|$)'; then
    CODEX_RUNTIME_PROBE_STATUS="unsupported"
    warn "Codex runtime probe skipped because this Codex version has no --ephemeral mode."
    return 0
  fi

  set_setup_step codex_runtime_probe
  probe_dir="$(mktemp -d 2>/dev/null || mktemp -d -t routercheap-codex-probe)"
  stdout_file="$probe_dir/stdout.log"
  stderr_file="$probe_dir/stderr.log"
  code=0
  if command -v timeout >/dev/null 2>&1; then
    if timeout 90s "$codex_bin" exec --ephemeral --sandbox read-only --skip-git-repo-check --json -m "$model_name" 'Reply with exactly OK.' >"$stdout_file" 2>"$stderr_file"; then code=0; else code=$?; fi
  else
    "$codex_bin" exec --ephemeral --sandbox read-only --skip-git-repo-check --json -m "$model_name" 'Reply with exactly OK.' >"$stdout_file" 2>"$stderr_file" &
    pid=$!
    for i in $(seq 1 90); do
      if ! kill -0 "$pid" 2>/dev/null; then break; fi
      sleep 1
    done
    if kill -0 "$pid" 2>/dev/null; then
      kill -TERM "$pid" 2>/dev/null || true
      sleep 1
      kill -KILL "$pid" 2>/dev/null || true
      code=124
    else
      if wait "$pid"; then code=0; else code=$?; fi
    fi
  fi
  CODEX_RUNTIME_PROBE_EXIT_CODE="$code"
  output="$(cat "$stdout_file" "$stderr_file" 2>/dev/null || true)"
  if [[ "$code" -eq 0 ]]; then
    CODEX_RUNTIME_PROBE_STATUS="passed"
    ok "Codex runtime probe passed: the CLI completed through the configured provider."
  elif [[ "$code" -eq 124 ]]; then
    CODEX_RUNTIME_PROBE_STATUS="timeout"
    warn "Codex runtime probe timed out after 90 seconds."
  elif printf '%s' "$output" | grep -Eiq 'api\.openai\.com'; then
    CODEX_RUNTIME_PROBE_STATUS="wrong-provider-openai"
    warn "Codex runtime probe reached api.openai.com instead of router.cheap. Check --profile, -c model_provider, CODEX_HOME, or a stale app-server."
  elif printf '%s' "$output" | grep -Eiq '401|unauthorized|invalid[_ -]?api[_ -]?key'; then
    CODEX_RUNTIME_PROBE_STATUS="failed-401"
    warn "Codex runtime probe received an authorization failure. The configured key/provider was not accepted."
  else
    CODEX_RUNTIME_PROBE_STATUS="failed"
    warn "Codex runtime probe failed (exit $code); setup configuration was still written."
  fi
  rm -rf "$probe_dir"
  return 0
}

codex_toml_setting() {
  local path="$1" table="$2" key="$3"
  awk -v table="$table" -v key="$key" '
    BEGIN { in_table = (table == "") }
    /^[[:space:]]*\[/ {
      in_table = ($0 ~ "^[[:space:]]*\\[" table "\\][[:space:]]*(#.*)?$")
      next
    }
    in_table && $0 ~ "^[[:space:]]*" key "[[:space:]]*=" {
      value = $0
      sub("^[[:space:]]*" key "[[:space:]]*=[[:space:]]*", "", value)
      sub(/[[:space:]]*#.*$/, "", value)
      gsub(/[[:space:]]/, "", value)
      if (value ~ /^".*"$/) { sub(/^"/, "", value); sub(/"$/, "", value) }
      else if (value ~ /^'"'"'.*'"'"'$/) { sub(/^'"'"'/, "", value); sub(/'"'"'$/, "", value) }
      print value
      exit
    }
  ' "$path"
}

assert_codex_provider_configuration() {
  local config_path="$1" provider="$2" endpoint="$3" env_key="$4" model="$5"
  [[ -f "$config_path" ]] || fail "Codex configuration was not written: $config_path"
  local root_provider root_model provider_name provider_base provider_env provider_auth provider_wire profile profile_provider
  root_provider="$(codex_toml_setting "$config_path" "" model_provider)"
  root_model="$(codex_toml_setting "$config_path" "" model)"
  provider_name="$(codex_toml_setting "$config_path" "model_providers.$provider" name)"
  provider_base="$(codex_toml_setting "$config_path" "model_providers.$provider" base_url)"
  provider_env="$(codex_toml_setting "$config_path" "model_providers.$provider" env_key)"
  provider_auth="$(codex_toml_setting "$config_path" "model_providers.$provider" requires_openai_auth)"
  provider_wire="$(codex_toml_setting "$config_path" "model_providers.$provider" wire_api)"
  [[ "$root_provider" == "$provider" && "$root_model" == "$model" && -n "$provider_name" && "$provider_base" == "$endpoint" && "$provider_env" == "$env_key" && "$provider_auth" == "false" && "$provider_wire" == "responses" ]] || fail "Codex configuration verification failed at $config_path. Expected model_provider='$provider', model='$model', base_url='$endpoint', env_key='$env_key', requires_openai_auth=false, wire_api=responses."
  ok "Codex configuration verified: $config_path (provider '$provider', endpoint '$endpoint')."
  warn "If Codex later reports URL https://api.openai.com/v1/responses, that invocation did not use provider '$provider' (usually a --profile/CLI override or an already-running Desktop/IDE app-server)."
  while IFS= read -r profile; do
    [[ -n "$profile" ]] || continue
    profile_provider="$(codex_toml_setting "$profile" "" model_provider)"
    if [[ -n "$profile_provider" && "$profile_provider" != "$provider" ]]; then
      warn "Profile '$(basename "$profile")' selects provider '$profile_provider' and overrides the router.cheap default when used with 'codex --profile'."
    fi
  done < <(codex_profile_files)
}

codex_setup_diagnostics_json() {
  local requested_endpoint="${1:-$ENDPOINT}" requested_model="${2:-$MODEL}" env_key="${3:-ROUTER_CHEAP_API_KEY}"
  local config_path provider base profiles_count other_count providers config_sha version process_state home_path home_sha
  local process_home_source="default" config_exists="false" config_model="" provider_name="" provider_base_host="" provider_base_path="" provider_env="" provider_auth="" provider_wire=""
  config_path="$(codex_config_path)"; provider=""; config_sha=""; version=""; home_sha=""
  [[ -n "${CODEX_HOME:-}" ]] && process_home_source="process"
  home_path="${CODEX_HOME:-$HOME/.codex}"
  if command -v sha256sum >/dev/null 2>&1; then home_sha="$(printf '%s' "$home_path" | sha256sum | awk '{print $1}')"
  elif command -v shasum >/dev/null 2>&1; then home_sha="$(printf '%s' "$home_path" | shasum -a 256 | awk '{print $1}')"; fi
  command -v codex >/dev/null 2>&1 && version="$(codex --version 2>/dev/null | head -n 1 || true)" || version=""
  [[ -f "$config_path" ]] && config_exists="true"
  if [[ "$config_exists" == "true" ]]; then
    if command -v sha256sum >/dev/null 2>&1; then config_sha="$(sha256sum "$config_path" 2>/dev/null | awk '{print $1}')"
    elif command -v shasum >/dev/null 2>&1; then config_sha="$(shasum -a 256 "$config_path" 2>/dev/null | awk '{print $1}')"; fi
    config_model="$(codex_toml_setting "$config_path" "" model || true)"
    provider="$(codex_toml_setting "$config_path" "" model_provider || true)"
    [[ -n "$provider" ]] || provider="routercheap"
    provider_name="$(codex_toml_setting "$config_path" "model_providers.$provider" name || true)"
    base="$(codex_toml_setting "$config_path" "model_providers.$provider" base_url || true)"
    if [[ -n "$base" ]]; then
      target="${base#*://}"; provider_base_host="${target%%/*}"; provider_base_path="/${target#*/}"; [[ "$target" == */* ]] || provider_base_path="/"
      provider_base_path="${provider_base_path%%\?*}"
    fi
    provider_env="$(codex_toml_setting "$config_path" "model_providers.$provider" env_key || true)"
    provider_auth="$(codex_toml_setting "$config_path" "model_providers.$provider" requires_openai_auth || true)"
    provider_wire="$(codex_toml_setting "$config_path" "model_providers.$provider" wire_api || true)"
  fi
  profiles_count=0; other_count=0; providers=""
  while IFS= read -r profile; do
    [[ -n "$profile" ]] || continue
    profiles_count=$((profiles_count + 1))
    profile_provider="$(codex_toml_setting "$profile" "" model_provider || true)"
    [[ -n "$profile_provider" ]] || continue
    [[ -n "$providers" && ",$providers," == *",$profile_provider,"* ]] || providers="${providers:+$providers,}$profile_provider"
    [[ "$profile_provider" == "routercheap" ]] || other_count=$((other_count + 1))
  done < <(codex_profile_files)
  if command -v pgrep >/dev/null 2>&1 && [[ -n "$(pgrep -x codex 2>/dev/null || true)" ]]; then process_state="running"; else process_state="none"; fi
  printf '{"schema":"1","codex_home_source":"%s","codex_home_sha256":"%s","config_exists":"%s"' "$(json_escape "$process_home_source")" "$(json_escape "$home_sha")" "$(json_escape "$config_exists")"
  [[ -n "$version" ]] && printf ',"codex_version":"%s"' "$(json_escape "$version")"
  [[ -n "$config_sha" ]] && printf ',"config_sha256":"%s"' "$(json_escape "$config_sha")"
  printf ',"config_model":"%s","config_model_provider":"%s","provider_name":"%s","provider_base_host":"%s","provider_base_path":"%s","provider_env_key":"%s","provider_requires_openai_auth":"%s","provider_wire_api":"%s"' "$(json_escape "$config_model")" "$(json_escape "$provider")" "$(json_escape "$provider_name")" "$(json_escape "$provider_base_host")" "$(json_escape "$provider_base_path")" "$(json_escape "$provider_env")" "$(json_escape "$provider_auth")" "$(json_escape "$provider_wire")"
  printf ',"profiles_count":"%s","profiles_other_provider_count":"%s"' "$profiles_count" "$other_count"
  [[ -n "$providers" ]] && printf ',"profiles_provider_ids":"%s"' "$(json_escape "$providers")"
  [[ -n "${!env_key:-}" ]] && printf ',"api_key_process_present":"true"' || printf ',"api_key_process_present":"false"'
  [[ -n "${OPENAI_API_KEY:-}" ]] && printf ',"openai_api_key_process_present":"true"' || printf ',"openai_api_key_process_present":"false"'
  [[ -n "${OPENAI_BASE_URL:-}" ]] && printf ',"openai_base_url_process_present":"true"' || printf ',"openai_base_url_process_present":"false"'
  [[ -n "${CODEX_PROFILE:-}" ]] && printf ',"codex_profile_process_present":"true"' || printf ',"codex_profile_process_present":"false"'
  printf ',"codex_process_state":"%s","requested_model":"%s"' "$(json_escape "$process_state")" "$(json_escape "$requested_model")"
  target="${requested_endpoint#*://}"; authority="${target%%/*}"; path="/${target#*/}"; [[ "$target" == */* ]] || path="/"; path="${path%%\?*}"
  printf ',"requested_endpoint_host":"%s","requested_endpoint_path":"%s"' "$(json_escape "$authority")" "$(json_escape "$path")"
  [[ -n "$SETUP_LAST_PROBE_METHOD" ]] && printf ',"last_probe_method":"%s"' "$(json_escape "$SETUP_LAST_PROBE_METHOD")"
  [[ -n "$SETUP_LAST_PROBE_PATH" ]] && printf ',"last_probe_path":"%s"' "$(json_escape "$SETUP_LAST_PROBE_PATH")"
  [[ -n "$SETUP_LAST_PROBE_STATUS" ]] && printf ',"last_probe_status":"%s"' "$(json_escape "$SETUP_LAST_PROBE_STATUS")"
  [[ -n "$SETUP_MODELS_PROBE_STATUS" ]] && printf ',"models_probe_status":"%s"' "$(json_escape "$SETUP_MODELS_PROBE_STATUS")"
  [[ -n "$SETUP_RESPONSES_PROBE_STATUS" ]] && printf ',"responses_probe_status":"%s"' "$(json_escape "$SETUP_RESPONSES_PROBE_STATUS")"
  [[ -n "$CODEX_RUNTIME_PROBE_STATUS" ]] && printf ',"codex_runtime_probe_status":"%s"' "$(json_escape "$CODEX_RUNTIME_PROBE_STATUS")"
  [[ -n "$CODEX_RUNTIME_PROBE_EXIT_CODE" ]] && printf ',"codex_runtime_probe_exit_code":"%s"' "$(json_escape "$CODEX_RUNTIME_PROBE_EXIT_CODE")"
  printf '}'
}

codex_image_tool_root() {
  printf '%s/routercheap-image-tool' "${CODEX_HOME:-$HOME/.codex}"
}

download_verified_codex_image_asset() {
  local url="$1" destination="$2" expected="$3" local_asset="${4:-}" temporary actual
  if [[ "$DRY_RUN" -eq 1 ]]; then
    ok "Would install Codex image component: $destination"
    return
  fi
  temporary="$(mktemp)"
  if [[ -n "$local_asset" && -f "$local_asset" ]]; then
    cp "$local_asset" "$temporary"
  else
    curl -fsSL --connect-timeout 20 --max-time 120 "$url" -o "$temporary" || { rm -f "$temporary"; fail "Failed to download Codex image component: $url"; }
  fi
  if command -v sha256sum >/dev/null 2>&1; then
    actual="$(sha256sum "$temporary" | awk '{print toupper($1)}')"
  elif command -v shasum >/dev/null 2>&1; then
    actual="$(shasum -a 256 "$temporary" | awk '{print toupper($1)}')"
  else
    rm -f "$temporary"
    fail "sha256sum or shasum is required to verify Codex image components."
  fi
  [[ "$actual" == "$expected" ]] || { rm -f "$temporary"; fail "Codex image component checksum mismatch: $url"; }
  mkdir -p "$(dirname "$destination")"
  mv -f "$temporary" "$destination"
}

install_codex_image_tool() {
  local root base assets server command skill
  root="$(codex_image_tool_root)"
  base="${ENDPOINT%/v1}"
  assets="$base/downloads/setup/codex-image-tool"
  skill="${CODEX_HOME:-$HOME/.codex}/skills/routercheap-imagegen/SKILL.md"
  if command -v node >/dev/null 2>&1; then
    server="$root/server.mjs"; command="node"
    download_verified_codex_image_asset "$assets/server.mjs" "$server" "EC68DCF0C8F4A84C12E0B8FE78243DB0256BDE14653623F213FE496D35598B86" "$SCRIPT_DIR/codex-image-tool/server.mjs"
  elif has_python3; then
    server="$root/server.py"; command="python3"
    download_verified_codex_image_asset "$assets/server.py" "$server" "2D0C11FB567C885719A10F3EBB2D1B636606E64C7C8501A585E9B6FCB5B5F2F6" "$SCRIPT_DIR/codex-image-tool/server.py"
    [[ "$DRY_RUN" -eq 1 ]] || chmod 700 "$server"
  else
    fail "Codex image generation needs Node.js or Python 3. Install one and rerun setup."
  fi
  download_verified_codex_image_asset "$assets/SKILL.md" "$skill" "EF623F783117D4CC2A023FD2E00EBF65A35D91B188ABCA4843979F6B79B48F58" "$SCRIPT_DIR/codex-image-tool/SKILL.md"
  if [[ "$DRY_RUN" -eq 0 ]]; then
    rm -rf "${CODEX_HOME:-$HOME/.codex}/relayfast-image-tool" "${CODEX_HOME:-$HOME/.codex}/skills/relayfast-imagegen" "${CODEX_HOME:-$HOME/.codex}/codexrodeo-image-tool" "${CODEX_HOME:-$HOME/.codex}/skills/codexrodeo-imagegen"
  fi
  CODEX_IMAGE_COMMAND="$command"
  CODEX_IMAGE_SERVER="$server"
}

remove_codex_image_tool() {
  local root skill
  root="$(codex_image_tool_root)"; skill="${CODEX_HOME:-$HOME/.codex}/skills/routercheap-imagegen"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    ok "Would remove managed Codex image component: $root"
    ok "Would remove managed Codex image component: $skill"
  else
    rm -rf "$root" "$skill"
  fi
}

droid_config_path() {
  printf '%s/.factory/settings.json' "$HOME"
}

droid_display_name() {
  case "$1" in
    gpt-6-astra) printf '%s' 'router.cheap GPT-6 Astra' ;;
    gpt-5.6-sol) printf '%s' 'router.cheap GPT 5.6 Sol' ;;
    gpt-5.6-terra) printf '%s' 'router.cheap GPT 5.6 Terra' ;;
    gpt-5.6-luna) printf '%s' 'router.cheap GPT 5.6 Luna' ;;
    gpt-5.5) printf '%s' 'router.cheap GPT 5.5' ;;
    *) printf 'router.cheap %s' "$1" ;;
  esac
}

write_droid_config() {
  local path tmp display runtime
  path="$(droid_config_path)"
  display="$(droid_display_name "$MODEL")"
  tmp="$(mktemp)"
  if has_python3; then
    python3 - "$path" "$ENDPOINT" "$MODEL" "$display" > "$tmp" <<'PY'
import json, os, sys
from urllib.parse import urlparse
path, endpoint, model, display = sys.argv[1:5]
if os.path.exists(path):
    raw = open(path, "r", encoding="utf-8-sig").read().strip()
    data = json.loads(raw) if raw else {}
else:
    data = {}
if not isinstance(data, dict):
    raise ValueError("Factory Droid settings root must be a JSON object")
custom = data.get("customModels", [])
if custom is None:
    custom = []
if not isinstance(custom, list):
    raise ValueError("Factory Droid settings customModels must be a JSON array")
managed = {
    "model": model,
    "displayName": display,
    "baseUrl": endpoint,
    "apiKey": "${ROUTER_CHEAP_API_KEY}",
    "provider": "generic-chat-completion-api",
    "maxOutputTokens": 16384,
}
managed_hosts = {"router.cheap", "direct.router-cheap.com"}
def is_managed_router_model(item):
    if item.get("provider") != "generic-chat-completion-api" or item.get("apiKey") != "${ROUTER_CHEAP_API_KEY}":
        return False
    base = str(item.get("baseUrl") or "")
    host = urlparse(base).hostname or ""
    return host.lower() in managed_hosts or base.rstrip("/").lower() == endpoint.rstrip("/").lower()
updated = []
found = False
for item in custom:
    if not isinstance(item, dict):
        raise ValueError("Factory Droid settings customModels must contain JSON objects")
    if item.get("model") == model or is_managed_router_model(item):
        if not found:
            updated.append(managed)
            found = True
        continue
    updated.append(item)
if not found:
    updated.append(managed)
data["customModels"] = updated
print(json.dumps(data, ensure_ascii=False, indent=2))
PY
  else
    if command -v node >/dev/null 2>&1; then
      runtime=(node -)
    elif command -v bun >/dev/null 2>&1; then
      runtime=(bun run -)
    else
      rm -f "$tmp"
      fail "Factory Droid config migration needs python3, node, or bun so existing settings can be preserved safely."
    fi
    "${runtime[@]}" "$path" "$ENDPOINT" "$MODEL" "$display" > "$tmp" <<'JS'
const fs = require("fs");
const [path, endpoint, model, display] = process.argv.slice(-4);
let data = {};
if (fs.existsSync(path)) {
  const raw = fs.readFileSync(path, "utf8").replace(/^\uFEFF/, "").trim();
  data = raw ? JSON.parse(raw) : {};
}
if (!data || Array.isArray(data) || typeof data !== "object") throw new Error("Factory Droid settings root must be a JSON object");
let custom = data.customModels == null ? [] : data.customModels;
if (!Array.isArray(custom)) throw new Error("Factory Droid settings customModels must be a JSON array");
const managed = { model, displayName: display, baseUrl: endpoint, apiKey: "${ROUTER_CHEAP_API_KEY}", provider: "generic-chat-completion-api", maxOutputTokens: 16384 };
const managedHosts = new Set(["router.cheap", "direct.router-cheap.com"]);
function isManagedRouterModel(item) {
  if (item.provider !== "generic-chat-completion-api" || item.apiKey !== "${ROUTER_CHEAP_API_KEY}") return false;
  let host = "";
  try { host = new URL(String(item.baseUrl || "")).hostname.toLowerCase(); } catch (_) {}
  return managedHosts.has(host) || String(item.baseUrl || "").replace(/\/+$/, "").toLowerCase() === endpoint.replace(/\/+$/, "").toLowerCase();
}
const updated = []; let found = false;
for (const item of custom) {
  if (!item || Array.isArray(item) || typeof item !== "object") throw new Error("Factory Droid settings customModels must contain JSON objects");
  if (item.model === model || isManagedRouterModel(item)) { if (!found) { updated.push(managed); found = true; } continue; }
  updated.push(item);
}
if (!found) updated.push(managed);
data.customModels = updated;
process.stdout.write(JSON.stringify(data, null, 2) + "\n");
JS
  fi
  backup_file "$path"
  save_text_file "$path" "$tmp"
  rm -f "$tmp"
}

# Codex session files and SQLite state are intentionally never rewritten when the
# active model provider changes. Codex owns provider-bound resume metadata.

write_codex_config() {
  local path tmp1 tmp2 tmp3 out command_escaped server_escaped
  path="$(codex_config_path)"
  tmp1="$(mktemp)"; tmp2="$(mktemp)"; tmp3="$(mktemp)"; out="$(mktemp)"
  if [[ -f "$path" ]]; then
    awk '
      $0 ~ /^[[:space:]]*\[model_providers\.routercheap(\.[^]]+)?\][[:space:]]*(#.*)?$/ { skip = 1; next }
      $0 ~ /^[[:space:]]*\[mcp_servers\.(routercheap_image|relayfast_image|codexrodeo_image)(\.[^]]+)?\][[:space:]]*(#.*)?$/ { skip = 1; next }
      $0 ~ /^[[:space:]]*\[model_providers\.(openai|ollama|lmstudio)(\.[^]]+)?\][[:space:]]*(#.*)?$/ { skip = 1; next }
      skip && $0 ~ /^\[/ { skip = 0 }
      !skip { print }
    ' "$path" > "$tmp1"
  else
    : > "$tmp1"
  fi
  awk '
    BEGIN { inroot = 1 }
    inroot && $0 ~ /^[[:space:]]*\[/ { inroot = 0 }
    inroot && $0 ~ /^[[:space:]]*model_providers[[:space:]]*=/ { next }
    inroot && $0 ~ /^[[:space:]]*model[[:space:]]*=/ { next }
    inroot && $0 ~ /^[[:space:]]*model_provider[[:space:]]*=/ { next }
    { print }
  ' "$tmp1" > "$tmp2"

  # Codex 0.149+ requires every custom provider table to have a non-empty name.
  # Repair old third-party tables while preserving their other settings.
  tmp_names="$(mktemp)"
  awk '
    function flush(    i) {
      if (!active) return
      print header
      if (!has_name) print "name = \"" provider_id "\""
      for (i = 1; i <= count; i++) print lines[i]
      delete lines; count = 0; has_name = 0; active = 0
    }
    /^[[:space:]]*\[/ {
      flush()
      header = $0
       if ($0 ~ /^[[:space:]]*\[model_providers\.[A-Za-z0-9_-]+\][[:space:]]*(#.*)?$/) {
         provider_id = $0
         sub(/^[[:space:]]*\[model_providers\./, "", provider_id)
         sub(/\].*$/, "", provider_id)
        active = 1
        count = 0
        has_name = 0
      } else {
        print $0
      }
      next
    }
    active {
      count++
      lines[count] = $0
         if ($0 ~ /^[[:space:]]*name[[:space:]]*=/) {
           has_name = 1
           name_value = $0
           sub(/^[[:space:]]*name[[:space:]]*=[[:space:]]*/, "", name_value)
           sub(/[[:space:]]*#.*$/, "", name_value)
           gsub(/[[:space:]]/, "", name_value)
           if (name_value == "\"\"" || name_value == "''") lines[count] = "name = \"" provider_id "\""
         }
      next
    }
    { print }
    END { flush() }
  ' "$tmp2" > "$tmp_names"
  mv -f "$tmp_names" "$tmp2"
  awk -v model="$MODEL" '
    function emit() {
      if (!inserted) {
        print "model = \"" model "\""
        print "model_provider = \"routercheap\""
        print ""
        inserted = 1
      }
    }
    !inserted && $0 ~ /^[[:space:]]*\[/ { emit() }
    { print }
    END { if (!inserted) emit() }
  ' "$tmp2" > "$tmp3"
  command_escaped="$(printf '%s' "$CODEX_IMAGE_COMMAND" | sed 's/\\/\\\\/g; s/"/\\"/g')"
  server_escaped="$(printf '%s' "$CODEX_IMAGE_SERVER" | sed 's/\\/\\\\/g; s/"/\\"/g')"
  {
    cat "$tmp3"
    printf '\n[model_providers.routercheap]\n'
    printf 'name = "router.cheap"\n'
    printf 'base_url = "%s"\n' "$ENDPOINT"
    printf 'env_key = "ROUTER_CHEAP_API_KEY"\n'
    printf 'requires_openai_auth = false\n'
    printf 'wire_api = "responses"\n'
    printf '\n[mcp_servers.routercheap_image]\n'
    printf 'command = "%s"\n' "$command_escaped"
    printf 'args = ["%s"]\n' "$server_escaped"
    printf 'env_vars = ["ROUTER_CHEAP_API_KEY"]\n'
    printf 'env = { CODEX_HOME = "%s", ROUTER_IMAGE_BASE_URL = "%s", ROUTER_IMAGE_API_KEY_ENV = "ROUTER_CHEAP_API_KEY", ROUTER_IMAGE_MODEL = "gpt-image-2", ROUTER_IMAGE_BRAND = "router.cheap" }\n' "${CODEX_HOME:-$HOME/.codex}" "$ENDPOINT"
    printf 'startup_timeout_sec = 20\n'
    printf 'tool_timeout_sec = 900\n'
    printf 'enabled = true\n'
    printf 'required = false\n'
    printf 'default_tools_approval_mode = "approve"\n'
  } > "$out"
  backup_file "$path"
  save_text_file "$path" "$out"
  rm -f "$tmp1" "$tmp2" "$tmp3" "$out"
}

restore_codex_config() {
  local path tmp1 tmp2 out
  path="$(codex_config_path)"
  tmp1="$(mktemp)"; tmp2="$(mktemp)"; out="$(mktemp)"
  if [[ -f "$path" ]]; then
    awk '
      $0 == "[model_providers.routercheap]" { skip = 1; next }
      $0 == "[mcp_servers.routercheap_image]" { skip = 1; next }
      skip && $0 ~ /^\[/ { skip = 0 }
      !skip { print }
    ' "$path" > "$tmp1"
  else
    : > "$tmp1"
  fi
  awk '
    BEGIN { inroot = 1 }
    inroot && $0 ~ /^[[:space:]]*\[/ { inroot = 0 }
    inroot && $0 ~ /^[[:space:]]*model_provider[[:space:]]*=/ { next }
    { print }
  ' "$tmp1" > "$tmp2"
  awk '
    function emit() {
      if (!inserted) {
        print "model_provider = \"openai\""
        print ""
        inserted = 1
      }
    }
    !inserted && $0 ~ /^[[:space:]]*\[/ { emit() }
    { print }
    END { if (!inserted) emit() }
  ' "$tmp2" > "$out"
  backup_file "$path"
  save_text_file "$path" "$out"
  rm -f "$tmp1" "$tmp2" "$out"
}

grok_executable() {
  if command -v grok >/dev/null 2>&1; then
    command -v grok
  elif [[ -x "$HOME/.grok/bin/grok" ]]; then
    printf '%s' "$HOME/.grok/bin/grok"
  else
    return 1
  fi
}

grok_home() {
  printf '%s' "${GROK_HOME:-$HOME/.grok}"
}

render_grok_config() {
  local source="$1" output="$2" cleaned
  cleaned="$(mktemp)"
  if [[ -f "$source" ]]; then
    awk '
      /^[[:space:]]*\[model\.routercheap-grok-4-5\][[:space:]]*(#.*)?$/ { skip = 1; next }
      skip && /^[[:space:]]*\[/ { skip = 0 }
      !skip { print }
    ' "$source" > "$cleaned"
  else
    : > "$cleaned"
  fi
  awk 'NF { pending = pending $0 ORS; next } { if (pending != "") { printf "%s", pending; pending = "" }; print } END { if (pending != "") printf "%s", pending }' "$cleaned" > "$output"
  {
    printf '\n[model.routercheap-grok-4-5]\n'
    printf 'model = "%s"\n' "$GROK_MODEL"
    printf 'base_url = "%s"\n' "$ENDPOINT"
    printf 'name = "Grok 4.5 via router.cheap"\n'
    printf 'description = "Grok 4.5 through the router.cheap OpenAI-compatible Responses API"\n'
    printf 'env_key = "ROUTER_CHEAP_GROK_API_KEY"\n'
    printf 'api_backend = "responses"\n'
    printf 'context_window = 500000\n'
    printf 'supports_reasoning_effort = true\n'
    printf 'reasoning_effort = "high"\n'
    printf 'stream_tool_calls = true\n'
    printf 'supports_backend_search = false\n'
  } >> "$output"
  rm -f "$cleaned"
}

write_grok_config() {
  local executable="$1" home path out validation_home inspect_output
  home="$(grok_home)"
  path="$home/config.toml"
  out="$(mktemp)"
  render_grok_config "$path" "$out"
  validation_home="$(mktemp -d)"
  cp "$out" "$validation_home/config.toml"
  inspect_output="$(GROK_HOME="$validation_home" ROUTER_CHEAP_GROK_API_KEY="$API_KEY" GROK_DISABLE_AUTOUPDATER=1 "$executable" inspect --json 2>&1)" || {
    rm -rf "$validation_home"; rm -f "$out"
    fail "Grok rejected the generated config: $inspect_output"
  }
  rm -rf "$validation_home"
  backup_file "$path"
  save_text_file "$path" "$out"
  rm -f "$out"
  ok "Grok config validated with 'grok inspect'."
}

restore_grok_config() {
  local home path out
  home="$(grok_home)"
  path="$home/config.toml"
  [[ -f "$path" ]] || return 0
  out="$(mktemp)"
  awk '
    /^[[:space:]]*\[model\.routercheap-grok-4-5\][[:space:]]*(#.*)?$/ { skip = 1; next }
    skip && /^[[:space:]]*\[/ { skip = 0 }
    !skip { print }
  ' "$path" > "$out"
  backup_file "$path"
  if [[ -s "$out" ]]; then
    save_text_file "$path" "$out"
  elif [[ "$DRY_RUN" -eq 0 ]]; then
    rm -f "$path"
  fi
  rm -f "$out"
}

write_grok_launcher() {
  local executable="$1" home credential launcher_dir launcher backend profile_block
  home="$(grok_home)"
  credential="$home/credentials/routercheap-api-key"
  backend="$home/credentials/routercheap-backend"
  launcher_dir="$HOME/.grok/bin"
  launcher="$launcher_dir/grok-routercheap"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    ok "Would store the API key in a mode-600 credential file: $credential"
    ok "Would install secure launcher: $launcher"
    return 0
  fi

  mkdir -p "$home/credentials" "$launcher_dir"
  if command -v secret-tool >/dev/null 2>&1 && [[ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ]]; then
    printf '%s' "$API_KEY" | secret-tool store --label='router.cheap Grok Build API key' service router.cheap application grok-build >/dev/null
    printf '%s\n' 'secret-tool' > "$backend"
    rm -f "$credential"
  else
    (umask 077; printf '%s\n' "$API_KEY" > "$credential.tmp")
    mv -f "$credential.tmp" "$credential"
    chmod 600 "$credential"
    printf '%s\n' 'file' > "$backend"
    chmod 600 "$backend"
  fi

  {
    printf '%s\n' '#!/usr/bin/env bash'
    printf '%s\n' 'set -euo pipefail'
    printf 'GROK_EXECUTABLE=%s\n' "$(shell_quote "$executable")"
    printf 'GROK_HOME_VALUE=%s\n' "$(shell_quote "$home")"
    printf 'CREDENTIAL=%s\n' "$(shell_quote "$credential")"
    printf 'BACKEND=%s\n' "$(shell_quote "$backend")"
    cat <<'EOF'
[[ -f "$BACKEND" ]] || { printf '[FAIL] router.cheap Grok credential metadata is missing. Run setup again.\n' >&2; exit 1; }
case "$(cat "$BACKEND")" in
  secret-tool) API_KEY="$(secret-tool lookup service router.cheap application grok-build || true)" ;;
  file) API_KEY="$(cat "$CREDENTIAL" 2>/dev/null || true)" ;;
  *) printf '[FAIL] Unknown router.cheap Grok credential backend. Run setup again.\n' >&2; exit 1 ;;
esac
[[ -n "$API_KEY" ]] || { printf '[FAIL] router.cheap Grok credential is empty. Run setup again.\n' >&2; exit 1; }
export GROK_HOME="$GROK_HOME_VALUE"
export ROUTER_CHEAP_GROK_API_KEY="$API_KEY"
unset API_KEY
exec "$GROK_EXECUTABLE" -m routercheap-grok-4-5 "$@"
EOF
  } > "$launcher.tmp"
  chmod 700 "$launcher.tmp"
  mv -f "$launcher.tmp" "$launcher"

  profile_block="$(mktemp)"
  cat > "$profile_block" <<'EOF'
case ":$PATH:" in
  *":$HOME/.grok/bin:"*) ;;
  *) export PATH="$HOME/.grok/bin:$PATH" ;;
esac
EOF
  write_profile_block grok-build "$profile_block"
  rm -f "$profile_block"
  ok "$(msg grok_command)"
}

restore_grok_launcher() {
  local home backend credential
  home="$(grok_home)"
  backend="$home/credentials/routercheap-backend"
  credential="$home/credentials/routercheap-api-key"
  if [[ -f "$backend" && "$(cat "$backend")" == "secret-tool" ]] && command -v secret-tool >/dev/null 2>&1; then
    secret-tool clear service router.cheap application grok-build >/dev/null 2>&1 || true
  fi
  remove_profile_block grok-build
  if [[ "$DRY_RUN" -eq 1 ]]; then
    ok "Would remove router.cheap Grok launcher and credentials."
  else
    rm -f "$backend" "$credential" "$HOME/.grok/bin/grok-routercheap"
  fi
}

write_claude_settings() {
  local path state_path tmp state_tmp error_file error_message cache_policy_applied key_tmp
  path="$HOME/.claude/settings.json"
  state_path="$HOME/.routercheap/claude-code-cache-policy.json"
  tmp="$(mktemp)"
  state_tmp="$(mktemp)"
  error_file="$(mktemp)"
  cache_policy_applied=0
  if has_python3; then
    if ! python3 - "$path" "$ANTHROPIC_ENDPOINT" "$CLAUDE_MODEL" "$state_path" "$state_tmp" 3<<<"$API_KEY" > "$tmp" 2> "$error_file" <<'PY'
import json, os, sys
path, base, model, state_path, state_tmp = sys.argv[1:6]
with os.fdopen(3, "r", encoding="utf-8") as secret_input:
    key = secret_input.read().rstrip("\r\n")
data = {}
if os.path.exists(path):
    raw = open(path, "r", encoding="utf-8", errors="replace").read().strip()
    if raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}", file=sys.stderr)
            raise SystemExit(2)
if not isinstance(data, dict):
    data = {}
env = data.get("env")
if not isinstance(env, dict):
    env = {}
data["env"] = env
env.pop("ANTHROPIC_API_KEY", None)
env["ANTHROPIC_BASE_URL"] = base
env["ANTHROPIC_AUTH_TOKEN"] = key
env["ANTHROPIC_MODEL"] = model

managed = False
if os.path.exists(state_path):
    state_raw = open(state_path, "r", encoding="utf-8", errors="replace").read().strip()
    if state_raw:
        state = json.loads(state_raw)
        managed = isinstance(state, dict) and state.get("agent_fork_deny_added") is True
permissions = data.get("permissions")
if permissions is None:
    permissions = {}
    data["permissions"] = permissions
if not isinstance(permissions, dict):
    raise ValueError("Claude Code settings permissions must be a JSON object")
deny = permissions.get("deny")
if deny is None:
    deny = []
if not isinstance(deny, list) or any(not isinstance(entry, str) for entry in deny):
    raise ValueError("Claude Code settings permissions.deny must be an array of strings")
if "Agent(fork)" not in deny:
    deny.append("Agent(fork)")
    managed = True
permissions["deny"] = deny
if managed:
    with open(state_tmp, "w", encoding="utf-8") as state_output:
        json.dump({"version": 1, "agent_fork_deny_added": True}, state_output, ensure_ascii=False, indent=2)
        state_output.write("\n")
print(json.dumps(data, ensure_ascii=False, indent=2))
PY
    then
      error_message="$(truncate_setup_text "$(cat "$error_file")" 500)"
      rm -f "$tmp" "$state_tmp" "$error_file"
      [[ -n "$error_message" ]] || error_message="python3 exited without an error message"
      fail "Could not update ~/.claude/settings.json: $error_message"
    fi
    cache_policy_applied=1
  elif command -v node >/dev/null 2>&1 || command -v bun >/dev/null 2>&1; then
    local -a runtime
    if command -v node >/dev/null 2>&1; then runtime=(node -); else runtime=(bun -); fi
    key_tmp="$(mktemp)"
    chmod 600 "$key_tmp"
    printf '%s' "$API_KEY" > "$key_tmp"
    if ! "${runtime[@]}" "$path" "$ANTHROPIC_ENDPOINT" "$CLAUDE_MODEL" "$state_path" "$state_tmp" "$key_tmp" > "$tmp" 2> "$error_file" <<'JS'
const fs = require("fs");
const [path, base, model, statePath, stateTmp, keyPath] = process.argv.slice(2);
const key = fs.readFileSync(keyPath, "utf8").replace(/[\r\n]+$/, "");
let data = {};
if (fs.existsSync(path)) {
  const raw = fs.readFileSync(path, "utf8").trim();
  if (raw) data = JSON.parse(raw);
}
if (!data || Array.isArray(data) || typeof data !== "object") data = {};
if (!data.env || Array.isArray(data.env) || typeof data.env !== "object") data.env = {};
delete data.env.ANTHROPIC_API_KEY;
data.env.ANTHROPIC_BASE_URL = base;
data.env.ANTHROPIC_AUTH_TOKEN = key;
data.env.ANTHROPIC_MODEL = model;

let managed = false;
if (fs.existsSync(statePath)) {
  const raw = fs.readFileSync(statePath, "utf8").trim();
  if (raw) {
    const state = JSON.parse(raw);
    managed = !!state && !Array.isArray(state) && state.agent_fork_deny_added === true;
  }
}
if (data.permissions == null) data.permissions = {};
if (Array.isArray(data.permissions) || typeof data.permissions !== "object") {
  throw new TypeError("Claude Code settings permissions must be a JSON object");
}
let deny = data.permissions.deny;
if (deny == null) deny = [];
if (!Array.isArray(deny) || deny.some((entry) => typeof entry !== "string")) {
  throw new TypeError("Claude Code settings permissions.deny must be an array of strings");
}
if (!deny.includes("Agent(fork)")) {
  deny.push("Agent(fork)");
  managed = true;
}
data.permissions.deny = deny;
if (managed) fs.writeFileSync(stateTmp, JSON.stringify({version: 1, agent_fork_deny_added: true}, null, 2) + "\n");
process.stdout.write(JSON.stringify(data, null, 2) + "\n");
JS
    then
      rm -f "$key_tmp"
      error_message="$(truncate_setup_text "$(cat "$error_file")" 500)"
      rm -f "$tmp" "$state_tmp" "$error_file"
      [[ -n "$error_message" ]] || error_message="the JSON runtime exited without an error message"
      fail "Could not update ~/.claude/settings.json: $error_message"
    fi
    rm -f "$key_tmp"
    cache_policy_applied=1
  else
    warn "python3, node, and bun are missing, so ~/.claude/settings.json was not edited. The shell profile exports were still written."
  fi
  if [[ "$cache_policy_applied" -eq 1 ]]; then
    if [[ -s "$state_tmp" ]]; then save_text_file "$state_path" "$state_tmp"; fi
    backup_file "$path"
    save_text_file "$path" "$tmp"
    ok "$(msg claude_cache_policy_configured)"
  fi
  rm -f "$tmp" "$state_tmp" "$error_file"
}

restore_claude_settings() {
  local path state_path tmp status_tmp managed
  path="$HOME/.claude/settings.json"
  state_path="$HOME/.routercheap/claude-code-cache-policy.json"
  if [[ ! -f "$path" ]]; then
    if [[ -f "$state_path" && "$DRY_RUN" -eq 0 ]]; then rm -f "$state_path"; fi
    return 0
  fi
  tmp="$(mktemp)"
  status_tmp="$(mktemp)"
  if has_python3; then
    python3 - "$path" "$state_path" "$status_tmp" > "$tmp" <<'PY'
import json, os, sys
path, state_path, status_path = sys.argv[1:4]
raw = open(path, "r", encoding="utf-8", errors="replace").read().strip()
data = json.loads(raw) if raw else {}
env = data.get("env")
if isinstance(env, dict):
    for name in ["ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_MODEL"]:
        env.pop(name, None)

managed = False
if os.path.exists(state_path):
    state_raw = open(state_path, "r", encoding="utf-8", errors="replace").read().strip()
    if state_raw:
        state = json.loads(state_raw)
        managed = isinstance(state, dict) and state.get("agent_fork_deny_added") is True
if managed:
    permissions = data.get("permissions")
    if permissions is not None and not isinstance(permissions, dict):
        raise ValueError("Claude Code settings permissions must be a JSON object")
    if isinstance(permissions, dict):
        deny = permissions.get("deny")
        if deny is not None and not isinstance(deny, list):
            raise ValueError("Claude Code settings permissions.deny must be a JSON array")
        if isinstance(deny, list):
            try:
                deny.remove("Agent(fork)")
            except ValueError:
                pass
            if deny:
                permissions["deny"] = deny
            else:
                permissions.pop("deny", None)
        if not permissions:
            data.pop("permissions", None)
with open(status_path, "w", encoding="ascii") as status_output:
    status_output.write("1" if managed else "0")
print(json.dumps(data, ensure_ascii=False, indent=2))
PY
  elif command -v node >/dev/null 2>&1 || command -v bun >/dev/null 2>&1; then
    local -a runtime
    if command -v node >/dev/null 2>&1; then runtime=(node -); else runtime=(bun -); fi
    "${runtime[@]}" "$path" "$state_path" "$status_tmp" > "$tmp" <<'JS'
const fs = require("fs");
const [path, statePath, statusPath] = process.argv.slice(2);
const raw = fs.readFileSync(path, "utf8").trim();
const data = raw ? JSON.parse(raw) : {};
if (data.env && !Array.isArray(data.env) && typeof data.env === "object") {
  for (const name of ["ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_MODEL"]) delete data.env[name];
}
let managed = false;
if (fs.existsSync(statePath)) {
  const stateRaw = fs.readFileSync(statePath, "utf8").trim();
  if (stateRaw) {
    const state = JSON.parse(stateRaw);
    managed = !!state && !Array.isArray(state) && state.agent_fork_deny_added === true;
  }
}
if (managed) {
  if (data.permissions != null && (Array.isArray(data.permissions) || typeof data.permissions !== "object")) {
    throw new TypeError("Claude Code settings permissions must be a JSON object");
  }
  if (data.permissions && data.permissions.deny != null && !Array.isArray(data.permissions.deny)) {
    throw new TypeError("Claude Code settings permissions.deny must be a JSON array");
  }
  if (data.permissions && Array.isArray(data.permissions.deny)) {
    const index = data.permissions.deny.indexOf("Agent(fork)");
    if (index >= 0) data.permissions.deny.splice(index, 1);
    if (data.permissions.deny.length === 0) delete data.permissions.deny;
  }
  if (data.permissions && Object.keys(data.permissions).length === 0) delete data.permissions;
}
fs.writeFileSync(statusPath, managed ? "1" : "0", "ascii");
process.stdout.write(JSON.stringify(data, null, 2) + "\n");
JS
  else
    rm -f "$tmp" "$status_tmp"
    warn "python3, node, and bun are missing, so ~/.claude/settings.json was not edited."
    return
  fi
  managed="$(cat "$status_tmp")"
  backup_file "$path"
  save_text_file "$path" "$tmp"
  if [[ "$managed" == "1" ]]; then
    if [[ "$DRY_RUN" -eq 1 ]]; then
      ok "Would remove: $state_path"
    else
      rm -f "$state_path"
    fi
    ok "$(msg claude_cache_policy_restored)"
  fi
  rm -f "$tmp" "$status_tmp"
}

managed_model_context_length() {
  local model
  model="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$model" in
    gpt-5.4|gpt-5.4[-_.:]*|gpt-5.5|gpt-5.5[-_.:]*) printf '%s' 272000 ;;
	    gpt-5.6|gpt-5.6[-_.:]*) printf '%s' 372000 ;;
	    gpt-6-astra|gpt-6-astra[-_.:]*) printf '%s' 1050000 ;;
    claude-haiku-4-5|claude-haiku-4-5[-_.:]*) printf '%s' 200000 ;;
    claude-sonnet-5|claude-sonnet-5[-_.:]*|claude-sonnet-4-6|claude-sonnet-4-6[-_.:]*|claude-opus-4-6|claude-opus-4-6[-_.:]*|claude-opus-4-7|claude-opus-4-7[-_.:]*|claude-opus-4-8|claude-opus-4-8[-_.:]*|claude-opus-5|claude-opus-5[-_.:]*|claude-fable-5|claude-fable-5[-_.:]*|claude-mythos-5|claude-mythos-5[-_.:]*) printf '%s' 1000000 ;;
    grok-4.5|grok-4.5[-_.:]*|grok-4.6|grok-4.6[-_.:]*|grok-4.7|grok-4.7[-_.:]*) printf '%s' 500000 ;;
    kimi-k3|kimi-k3[-_.:]*) printf '%s' 1048576 ;;
    kimi-k2.6|kimi-k2.6[-_.:]*|kimi-k2.7|kimi-k2.7[-_.:]*|kimi-k2.7-code|kimi-k2.7-code[-_.:]*) printf '%s' 256000 ;;
    gemini-3.1-pro-preview|gemini-3.1-pro-preview[-_.:]*|gemini-3.5-flash|gemini-3.5-flash[-_.:]*|gemini-3.6-flash|gemini-3.6-flash[-_.:]*|gemini-3.7-flash|gemini-3.7-flash[-_.:]*) printf '%s' 1048576 ;;
    deepseek-v4-flash|deepseek-v4-flash[-_.:]*|deepseek-v4.1-flash|deepseek-v4.1-flash[-_.:]*|deepseek-v4-pro|deepseek-v4-pro[-_.:]*) printf '%s' 1000000 ;;
    glm-5.1|glm-5.1[-_.:]*) printf '%s' 200000 ;;
    glm-5.2|glm-5.2[-_.:]*|glm-5.3|glm-5.3[-_.:]*) printf '%s' 1000000 ;;
    hy3|hy3[-_.:]*|hy4) printf '%s' 256000 ;;
    mimo-v2.5|mimo-v2.5[-_.:]*) printf '%s' 1000000 ;;
    minimax-m3|minimax-m3[-_.:]*) printf '%s' 1000000 ;;
    *) printf '%s' '' ;;
  esac
}

opencode_model_config_json() {
  local model="$1" escaped context limit image
  escaped="$(json_escape "$model")"
  context="$(managed_model_context_length "$model")"
  limit=""
  image=""
  if [[ -n "$context" ]]; then
    limit=',"limit":{"context":'"$context"',"output":128000}'
  fi
  if model_supports_image_input "$model"; then
    # OpenCode gates image parts on modalities. The legacy attachment flag is
    # retained for older clients, but is not sufficient in current releases.
    image=',"attachment":true,"modalities":{"input":["text","image"],"output":["text"]}'
  fi
  case "$model" in
	    gpt-6-astra*|gpt-5.6*)
      printf '{"name":"%s","provider":{"npm":"@ai-sdk/openai"},"reasoning":true,"tool_call":true%s,"temperature":false%s,"options":{"reasoningEffort":"medium","reasoningSummary":"auto","include":["reasoning.encrypted_content"]},"variants":{"none":{"reasoningEffort":"none"},"low":{"reasoningEffort":"low"},"medium":{"reasoningEffort":"medium"},"high":{"reasoningEffort":"high"},"xhigh":{"reasoningEffort":"xhigh"},"max":{"reasoningEffort":"max"}}}' "$escaped" "$image" "$limit"
      ;;
    gpt-5.5*|gpt-5.4*)
      printf '{"name":"%s","provider":{"npm":"@ai-sdk/openai"},"reasoning":true,"tool_call":true%s,"temperature":false%s,"options":{"reasoningEffort":"medium","reasoningSummary":"auto","include":["reasoning.encrypted_content"]},"variants":{"none":{"reasoningEffort":"none"},"low":{"reasoningEffort":"low"},"medium":{"reasoningEffort":"medium"},"high":{"reasoningEffort":"high"},"xhigh":{"reasoningEffort":"xhigh"}}}' "$escaped" "$image" "$limit"
      ;;
    grok-4.5|grok-4.5[-_.:]*)
      printf '{"name":"%s","reasoning":true,"tool_call":true%s,"temperature":false%s,"options":{"reasoningEffort":"high"},"variants":{"low":{"reasoningEffort":"low"},"medium":{"reasoningEffort":"medium"},"high":{"reasoningEffort":"high"}}}' "$escaped" "$image" "$limit"
      ;;
    grok-4.6|grok-4.6[-_.:]*)
      printf '{"name":"%s","reasoning":true,"tool_call":true%s,"temperature":false%s,"options":{"reasoningEffort":"high"},"variants":{"low":{"reasoningEffort":"low"},"medium":{"reasoningEffort":"medium"},"high":{"reasoningEffort":"high"},"xhigh":{"reasoningEffort":"xhigh"}}}' "$escaped" "$image" "$limit"
      ;;
    grok-4.7|grok-4.7[-_.:]*)
      printf '{"name":"%s","reasoning":true,"tool_call":true%s,"temperature":false%s,"options":{"reasoningEffort":"high"},"variants":{"low":{"reasoningEffort":"low"},"medium":{"reasoningEffort":"medium"},"high":{"reasoningEffort":"high"},"xhigh":{"reasoningEffort":"xhigh"}}}' "$escaped" "$image" "$limit"
      ;;
    kimi-k3|kimi-k3[-_.:]*)
      printf '{"name":"%s","reasoning":true,"tool_call":true%s,"temperature":false%s,"options":{"reasoningEffort":"max"},"variants":{"low":{"reasoningEffort":"low"},"high":{"reasoningEffort":"high"},"max":{"reasoningEffort":"max"}}}' "$escaped" "$image" "$limit"
      ;;
    kimi-k2.6|kimi-k2.6[-_.:]*)
      printf '{"name":"%s","reasoning":true,"tool_call":true%s,"temperature":false%s,"options":{"thinking":{"type":"enabled"}},"variants":{"enabled":{"thinking":{"type":"enabled"}},"disabled":{"thinking":{"type":"disabled"}}}}' "$escaped" "$image" "$limit"
      ;;
    kimi-k2.7|kimi-k2.7[-_.:]*|kimi-k2.7-code|kimi-k2.7-code[-_.:]*)
      printf '{"name":"%s","reasoning":true,"tool_call":true%s,"temperature":false%s,"options":{"thinking":{"type":"enabled","keep":"all"}}}' "$escaped" "$image" "$limit"
      ;;
    minimax-m3|minimax-m3[-_.:]*)
      printf '{"name":"%s","reasoning":true,"tool_call":true%s,"temperature":false%s,"options":{"thinking":{"type":"adaptive"}},"variants":{"adaptive":{"thinking":{"type":"adaptive"}},"disabled":{"thinking":{"type":"disabled"}}}}' "$escaped" "$image" "$limit"
      ;;
    deepseek-v[4-9]*|deepseek-reasoner|deepseek-reasoner[-_.:]*)
      printf '{"name":"%s","reasoning":true,"tool_call":true%s,"temperature":false%s,"options":{"reasoningEffort":"medium"},"variants":{"low":{"reasoningEffort":"low"},"medium":{"reasoningEffort":"medium"},"high":{"reasoningEffort":"high"},"xhigh":{"reasoningEffort":"xhigh"}}}' "$escaped" "$image" "$limit"
      ;;
    glm-*|gemini-*|gemma-*|learnlm-*)
      printf '{"name":"%s","reasoning":true,"tool_call":true%s,"temperature":false%s,"options":{"reasoningEffort":"medium"},"variants":{"low":{"reasoningEffort":"low"},"medium":{"reasoningEffort":"medium"},"high":{"reasoningEffort":"high"}}}' "$escaped" "$image" "$limit"
      ;;
    claude-sonnet-5*|claude-opus-5*|claude-fable-5*|claude-mythos-5*)
      printf '{"name":"%s","provider":{"npm":"@ai-sdk/anthropic"},"reasoning":true,"interleaved":true,"tool_call":true%s%s,"options":{"effort":"high"},"variants":{"low":{"effort":"low"},"medium":{"effort":"medium"},"high":{"effort":"high"},"xhigh":{"effort":"xhigh"},"max":{"effort":"max"}}}' "$escaped" "$image" "$limit"
      ;;
    claude-opus-4-8*|claude-opus-4-7*)
      printf '{"name":"%s","provider":{"npm":"@ai-sdk/anthropic"},"reasoning":true,"interleaved":true,"tool_call":true%s%s,"options":{"thinking":{"type":"adaptive"},"effort":"high"},"variants":{"low":{"effort":"low"},"medium":{"effort":"medium"},"high":{"effort":"high"},"xhigh":{"effort":"xhigh"},"max":{"effort":"max"}}}' "$escaped" "$image" "$limit"
      ;;
    claude-opus-4-6*|claude-sonnet-4-6*)
      printf '{"name":"%s","provider":{"npm":"@ai-sdk/anthropic"},"reasoning":true,"interleaved":true,"tool_call":true%s%s,"options":{"thinking":{"type":"adaptive"},"effort":"high"},"variants":{"low":{"effort":"low"},"medium":{"effort":"medium"},"high":{"effort":"high"},"max":{"effort":"max"}}}' "$escaped" "$image" "$limit"
      ;;
    claude-opus-4-5*)
      printf '{"name":"%s","provider":{"npm":"@ai-sdk/anthropic"},"tool_call":true%s%s,"options":{"effort":"high"},"variants":{"low":{"effort":"low"},"medium":{"effort":"medium"},"high":{"effort":"high"}}}' "$escaped" "$image" "$limit"
      ;;
    claude-*)
      printf '{"name":"%s","provider":{"npm":"@ai-sdk/anthropic"},"tool_call":true%s%s}' "$escaped" "$image" "$limit"
      ;;
    gpt-5*|o[1-9]|o[1-9]-*)
      printf '{"name":"%s","provider":{"npm":"@ai-sdk/openai"},"tool_call":true%s%s}' "$escaped" "$image" "$limit"
      ;;
    *)
      printf '{"name":"%s"%s%s}' "$escaped" "$image" "$limit"
      ;;
  esac
}

write_opencode_config() {
  local path tmp provider_tmp models first model runtime
  path="$HOME/.config/opencode/routercheap.json"
  tmp="$(mktemp)"
  provider_tmp="$(mktemp)"
  models="$(available_chat_models)"
  [[ -n "$models" ]] || models="$MODEL"
  {
    printf '{\n'
    printf '  "npm": "@ai-sdk/openai-compatible",\n'
    printf '  "name": "router.cheap",\n'
    printf '  "options": {"baseURL":"%s","apiKey":"{env:ROUTER_CHEAP_OPENCODE_API_KEY}"},\n' "$(json_escape "$ENDPOINT")"
    printf '  "models": {\n'
    first=1
    while IFS= read -r model; do
      [[ -n "$model" ]] || continue
      if [[ "$first" -eq 0 ]]; then printf ',\n'; fi
      first=0
      printf '    "%s":' "$(json_escape "$model")"
      opencode_model_config_json "$model"
    done <<< "$models"
    printf '\n  }\n'
    printf '}\n'
  } > "$provider_tmp"

  if has_python3; then
    python3 - "$path" "$provider_tmp" "$MODEL" > "$tmp" <<'PY'
import json, os, sys
path, provider_path, selected_model = sys.argv[1:4]
if os.path.exists(path):
    raw = open(path, "r", encoding="utf-8-sig").read().strip()
    data = json.loads(raw) if raw else {}
else:
    data = {}
if not isinstance(data, dict):
    raise ValueError("OpenCode config root must be a JSON object")
providers = data.get("provider")
if providers is None:
    providers = {}
elif not isinstance(providers, dict):
    raise ValueError("OpenCode config 'provider' must be a JSON object")
managed = json.load(open(provider_path, "r", encoding="utf-8"))
providers["routercheap"] = managed
data["provider"] = providers
data["$schema"] = "https://opencode.ai/config.json"
current_model = data.get("model")
if not isinstance(current_model, str) or not current_model.strip() or current_model.lower().startswith("routercheap/"):
    data["model"] = "routercheap/" + selected_model
if "enabled_providers" in data:
    enabled = data["enabled_providers"]
    if not isinstance(enabled, list) or not all(isinstance(item, str) for item in enabled):
        raise ValueError("OpenCode config 'enabled_providers' must be an array of strings")
    if enabled == ["routercheap"]:
        del data["enabled_providers"]
    else:
        data["enabled_providers"] = list(dict.fromkeys(enabled + ["routercheap"]))
print(json.dumps(data, ensure_ascii=False, indent=2))
PY
  else
    if command -v node >/dev/null 2>&1; then
      runtime=(node -)
    elif command -v bun >/dev/null 2>&1; then
      runtime=(bun run -)
    else
      rm -f "$tmp" "$provider_tmp"
      fail "OpenCode config migration needs python3, node, or bun so existing user settings can be preserved safely."
    fi
    "${runtime[@]}" "$path" "$provider_tmp" "$MODEL" > "$tmp" <<'JS'
const fs = require("fs");
const [path, providerPath, selectedModel] = process.argv.slice(-3);
let data = {};
if (fs.existsSync(path)) {
  const raw = fs.readFileSync(path, "utf8").replace(/^\uFEFF/, "").trim();
  data = raw ? JSON.parse(raw) : {};
}
if (!data || Array.isArray(data) || typeof data !== "object") throw new Error("OpenCode config root must be a JSON object");
let providers = data.provider;
if (providers == null) providers = {};
if (Array.isArray(providers) || typeof providers !== "object") throw new Error("OpenCode config 'provider' must be a JSON object");
providers.routercheap = JSON.parse(fs.readFileSync(providerPath, "utf8"));
data.provider = providers;
data["$schema"] = "https://opencode.ai/config.json";
if (typeof data.model !== "string" || !data.model.trim() || data.model.toLowerCase().startsWith("routercheap/")) data.model = "routercheap/" + selectedModel;
if (Object.prototype.hasOwnProperty.call(data, "enabled_providers")) {
  if (!Array.isArray(data.enabled_providers) || !data.enabled_providers.every(x => typeof x === "string")) throw new Error("OpenCode config 'enabled_providers' must be an array of strings");
  if (data.enabled_providers.length === 1 && data.enabled_providers[0] === "routercheap") delete data.enabled_providers;
  else data.enabled_providers = [...new Set([...data.enabled_providers, "routercheap"])];
}
process.stdout.write(JSON.stringify(data, null, 2) + "\n");
JS
  fi
  backup_file "$path"
  save_text_file "$path" "$tmp"
  rm -f "$tmp" "$provider_tmp"
}

restore_opencode_config() {
  local path
  path="$HOME/.config/opencode/routercheap.json"
  remove_profile_block opencode
  if [[ -f "$path" ]]; then
    backup_file "$path"
    if [[ "$DRY_RUN" -eq 1 ]]; then
      ok "Would remove $path"
    else
      rm -f "$path"
    fi
  fi
}

hermes_api_mode() {
  local model
  model="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$model" in
    claude-*) printf '%s' anthropic_messages ;;
    gpt-*) printf '%s' codex_responses ;;
    *) printf '%s' chat_completions ;;
  esac
}

hermes_supported_reasoning_efforts() {
  local model
  model="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$model" in
    grok-4.5|grok-4.5[-_.:]*) printf '%s' 'low|medium|high' ;;
    grok-4.6|grok-4.6[-_.:]*) printf '%s' 'low|medium|high|xhigh' ;;
    grok-4.7|grok-4.7[-_.:]*) printf '%s' 'low|medium|high|xhigh' ;;
    deepseek-v[4-9]*|deepseek-reasoner|deepseek-reasoner[-_.:]*) printf '%s' 'none|minimal|low|medium|high|xhigh' ;;
    kimi-k3|kimi-k3[-_.:]*) printf '%s' 'low|high|max' ;;
    kimi-k2.6|kimi-k2.6[-_.:]*|kimi-k2.7|kimi-k2.7[-_.:]*|kimi-k2.7-code|kimi-k2.7-code[-_.:]*|minimax-m3|minimax-m3[-_.:]*) printf '%s' '' ;;
    glm-*|gemini-*|gemma-*|learnlm-*) printf '%s' 'low|medium|high' ;;
    *) printf '%s' 'none|minimal|low|medium|high|xhigh' ;;
  esac
}

hermes_effective_reasoning_effort() {
  local model
  model="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  if [[ "$model" == kimi-k3 || "$model" == kimi-k3[-_.:]* ]]; then
    if [[ "$HERMES_REASONING_EFFORT_EXPLICIT" -eq 0 && "$HERMES_REASONING_EFFORT" == medium ]]; then
      printf '%s' max
      return
    fi
  fi
  case "$model" in
    kimi-k2.6|kimi-k2.6[-_.:]*|kimi-k2.7|kimi-k2.7[-_.:]*|kimi-k2.7-code|kimi-k2.7-code[-_.:]*|minimax-m3|minimax-m3[-_.:]*) printf '%s' '' ;;
    *) printf '%s' "$HERMES_REASONING_EFFORT" ;;
  esac
}

validate_hermes_reasoning_effort() {
  local model="$1" supported
  supported="$(hermes_supported_reasoning_efforts "$model")"
  case "|$supported|" in
    *"|$HERMES_REASONING_EFFORT|"*) ;;
    *) fail "Hermes reasoning effort '$HERMES_REASONING_EFFORT' is not supported by $model. Choose one of: ${supported//|/, }." ;;
  esac
}

hermes_managed_provider_name() {
  local model
  model="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$model" in
    claude-*) printf '%s' routercheap-anthropic ;;
    gpt-*|o[1-9]|o[1-9]-*) printf '%s' routercheap ;;
    *) printf '%s' routercheap-compatible ;;
  esac
}

resolve_hermes_launcher_path() {
  local path="$1" target directory depth=0
  [[ -n "$path" ]] || return 1
  case "$path" in
    /*) ;;
    *) path="$(pwd -P)/$path" ;;
  esac
  while [[ -L "$path" ]]; do
    [[ "$depth" -lt 40 ]] || return 1
    target="$(readlink "$path" 2>/dev/null)" || return 1
    case "$target" in
      /*) path="$target" ;;
      *)
        directory="$(cd -P "$(dirname "$path")" 2>/dev/null && pwd)" || return 1
        path="$directory/$target"
        ;;
    esac
    depth=$((depth + 1))
  done
  [[ -e "$path" ]] || return 1
  directory="$(cd -P "$(dirname "$path")" 2>/dev/null && pwd)" || return 1
  printf '%s/%s' "$directory" "$(basename "$path")"
}

hermes_python_from_shebang() {
  local launcher="$1" shebang interpreter name
  [[ -r "$launcher" ]] || return 1
  IFS= read -r shebang < "$launcher" || true
  shebang="${shebang%$'\r'}"
  case "$shebang" in
    '#!'*) interpreter="${shebang#\#!}" ;;
    *) return 1 ;;
  esac
  interpreter="${interpreter#"${interpreter%%[![:space:]]*}"}"
  interpreter="${interpreter%%[[:space:]]*}"
  case "$interpreter" in
    /*) ;;
    *) return 1 ;;
  esac
  name="$(basename "$interpreter")"
  case "$name" in
    python|python[0-9]*|python.exe|python[0-9]*.exe) ;;
    *) return 1 ;;
  esac
  [[ -x "$interpreter" ]] || return 1
  printf '%s' "$interpreter"
}

hermes_python_near_launcher() {
  local launcher="$1" bin root candidate depth next_root
  bin="$(dirname "$launcher")"
  # Windows launchers now live outside the checkout, in HERMES_HOME/bin.
  if [[ "$(basename "$bin")" == "bin" ]]; then
    root="$(dirname "$bin")/hermes-agent"
    for candidate in "$root/venv/Scripts/python.exe" "$root/.venv/Scripts/python.exe" \
      "$root/venv/bin/python3" "$root/.venv/bin/python3"; do
      [[ -x "$candidate" ]] || continue
      printf '%s' "$candidate"
      return 0
    done
  fi
  root="$bin"
  for depth in 0 1 2; do
    for candidate in \
      "$root/python3" "$root/python" "$root/python.exe" \
      "$root/bin/python3" "$root/bin/python" "$root/bin/python.exe" \
      "$root/venv/bin/python3" "$root/venv/bin/python" "$root/venv/Scripts/python.exe" \
      "$root/.venv/bin/python3" "$root/.venv/bin/python" "$root/.venv/Scripts/python.exe" \
      "$root/env/bin/python3" "$root/env/bin/python" "$root/env/Scripts/python.exe" \
      "$root/python/bin/python3" "$root/python/bin/python" "$root/python/python.exe"; do
      [[ -x "$candidate" ]] || continue
      printf '%s' "$candidate"
      return 0
    done
    next_root="$(dirname "$root")"
    [[ "$next_root" == "$root" ]] && break
    root="$next_root"
  done
  return 1
}

hermes_python_path() {
  local hermes_path resolved_path candidate uv_root
  hermes_path="$(command -v hermes 2>/dev/null || true)"
  [[ -n "$hermes_path" ]] || return 1
  resolved_path="$(resolve_hermes_launcher_path "$hermes_path" 2>/dev/null || true)"
  [[ -n "$resolved_path" ]] || resolved_path="$hermes_path"

  candidate="$(hermes_python_from_shebang "$resolved_path" || true)"
  [[ -z "$candidate" ]] || { printf '%s' "$candidate"; return 0; }
  candidate="$(hermes_python_near_launcher "$resolved_path" || true)"
  [[ -z "$candidate" ]] || { printf '%s' "$candidate"; return 0; }
  if [[ "$resolved_path" != "$hermes_path" ]]; then
    candidate="$(hermes_python_near_launcher "$hermes_path" || true)"
    [[ -z "$candidate" ]] || { printf '%s' "$candidate"; return 0; }
  fi

  if command -v uv >/dev/null 2>&1; then
    uv_root="$(uv tool dir 2>/dev/null || true)"
    uv_root="$(normalize_hermes_path_for_shell "$uv_root")"
    for candidate in \
      "$uv_root/hermes-agent/bin/python3" "$uv_root/hermes-agent/bin/python" \
      "$uv_root/hermes-agent/Scripts/python.exe"; do
      [[ -n "$uv_root" && -x "$candidate" ]] || continue
      printf '%s' "$candidate"
      return 0
    done
  fi
  return 1
}

update_hermes_reasoning_session_fix() {
  local restore="${1:-0}" python helper status
  command -v hermes >/dev/null 2>&1 || return 1
  python="$(hermes_python_path || true)"
  [[ -n "$python" ]] || fail "Hermes' Python runtime was not found for the hermes command. Checked the resolved launcher, its shebang, adjacent virtual-environment layouts, and the uv tool directory."
  helper="$(mktemp)"
  cat > "$helper" <<'PY'
import importlib.util
import os
import secrets
import shutil
import sys
from datetime import datetime
from pathlib import Path

restore = sys.argv[1] == "1"
override = os.environ.get("FAKE_HERMES_RUN_AGENT_PATH", "").strip()
if override:
    root = Path(override).resolve().parent
else:
    spec = importlib.util.find_spec("run_agent")
    if spec is None or not spec.origin:
        raise SystemExit("Hermes' run_agent module could not be located.")
    root = Path(spec.origin).resolve().parent

path = root / "tui_gateway" / "server.py"
if not path.is_file():
    raise SystemExit("Hermes' tui_gateway.server module could not be located next to run_agent.py.")

text = path.read_text(encoding="utf-8")
newline = "\r\n" if "\r\n" in text else "\n"
begin = "            # routercheap Hermes session reasoning fix begin"
end = "            # routercheap Hermes session reasoning fix end"
agent_line = '            if session and session.get("agent") is not None:'
legacy_line = '            _write_config_key("agent.reasoning_effort", arg)'

def remove_managed_block(value):
    start = value.find(begin)
    if start < 0:
        return value
    finish = value.find(end, start)
    if finish < 0:
        raise SystemExit("The managed Hermes session reasoning fix is incomplete.")
    finish += len(end)
    if value.startswith("\r\n", finish):
        finish += 2
    elif value.startswith("\n", finish):
        finish += 1
    return value[:start] + value[finish:]

without = remove_managed_block(text)
if restore:
    if without == text:
        print("unchanged")
        raise SystemExit(0)
    agent_index = without.find(agent_line)
    if agent_index < 0:
        raise SystemExit("The managed Hermes session reasoning fix could not be restored safely.")
    candidate = without[:agent_index] + legacy_line + newline + without[agent_index:]
    result = "restored"
else:
    if without != text or 'session["create_reasoning_override"] = parsed' in text:
        print("current")
        raise SystemExit(0)
    legacy = legacy_line + newline + agent_line
    legacy_index = text.find(legacy)
    if legacy_index < 0:
        raise SystemExit("This Hermes version has an unsupported Desktop reasoning layout. Update Hermes and run setup again.")
    block = newline.join((
        begin,
        '            scope = str(params.get("scope") or "").strip().lower()',
        '            if scope == "global" or session is None:',
        '                _write_config_key("agent.reasoning_effort", arg)',
        '                if session is not None:',
        '                    session.pop("create_reasoning_override", None)',
        '            else:',
        '                session["create_reasoning_override"] = parsed',
        end,
    ))
    candidate = text[:legacy_index] + block + newline + agent_line + text[legacy_index + len(legacy):]
    result = "fixed"

compile(candidate, str(path), "exec")
backup = path.with_name(path.name + ".routercheap-backup-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(4))
shutil.copy2(path, backup)
temporary = path.with_name("." + path.name + ".routercheap-" + secrets.token_hex(6) + ".tmp")
try:
    temporary.write_text(candidate, encoding="utf-8", newline="")
    os.chmod(temporary, path.stat().st_mode)
    os.replace(temporary, path)
finally:
    try:
        temporary.unlink()
    except FileNotFoundError:
        pass
print(result)
PY
  if ! status="$("$python" "$helper" "$restore")"; then
    rm -f "$helper"
    fail "Hermes rejected the Desktop session reasoning compatibility fix."
  fi
  rm -f "$helper"
  if [[ "$restore" -eq 0 ]]; then
    case "$status" in
      fixed) ok "$(msg hermes_reasoning_session_fixed)" ;;
      current) ok "$(msg hermes_reasoning_session_current)" ;;
    esac
  fi
}

update_hermes_managed_providers() {
  local restore="${1:-0}" config_path python helper models_file
  command -v hermes >/dev/null 2>&1 || return 1
  python="$(hermes_python_path || true)"
  [[ -n "$python" ]] || fail "Hermes' Python runtime was not found for the hermes command. Checked the resolved launcher, its shebang, adjacent virtual-environment layouts, and the uv tool directory."
  config_path="$(hermes config path 2>/dev/null | awk 'NF { line=$0 } END { print line }')"
  config_path="$(normalize_hermes_path_for_shell "$config_path")"
  [[ -n "$config_path" ]] || fail "Hermes did not return its active config path."
  helper="$(mktemp)"
  models_file="$(mktemp)"
  available_chat_models > "$models_file"
  cat > "$helper" <<'PY'
import sys
from pathlib import Path

from hermes_cli.config import fast_safe_load
from utils import atomic_yaml_write

config_path = Path(sys.argv[1])
endpoint = sys.argv[2]
selected_model = sys.argv[3]
restore = sys.argv[4] == "1"
models_path = Path(sys.argv[5])

def context_length(name):
    value = name.strip().lower()
    def family(prefix):
        return value == prefix or (value.startswith(prefix) and len(value) > len(prefix) and value[len(prefix)] in "-_.:")
    if family("gpt-5.4") or family("gpt-5.5"):
        return 272000
    if family("gpt-5.6"):
        return 372000
    if family("gpt-6-astra"):
        return 1050000
    if family("claude-haiku-4-5"):
        return 200000
    if any(family(prefix) for prefix in (
        "claude-sonnet-5", "claude-sonnet-4-6", "claude-opus-4-6",
        "claude-opus-4-7", "claude-opus-4-8", "claude-opus-5", "claude-fable-5", "claude-mythos-5",
    )):
        return 1000000
    if family("grok-4.5"):
        return 500000
    if family("grok-4.6"):
        return 500000
    if family("grok-4.7"):
        return 500000
    if family("kimi-k3"):
        return 1048576
    if any(family(prefix) for prefix in ("kimi-k2.6", "kimi-k2.7", "kimi-k2.7-code")):
        return 256000
    if any(family(prefix) for prefix in ("gemini-3.1-pro-preview", "gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash")):
        return 1048576
    if any(family(prefix) for prefix in ("deepseek-v4-flash", "deepseek-v4-pro", "deepseek-v4.1-flash")):
        return 1000000
    if family("glm-5.1"):
        return 200000
    if family("glm-5.2") or family("glm-5.3"):
        return 1000000
    if family("hy3") or family("hy4"):
        return 256000
    if family("mimo-v2.5") or family("minimax-m3"):
        return 1000000
    return None

def supports_image_input(name):
    value = name.strip().lower()
    def family(prefix):
        return value == prefix or (value.startswith(prefix) and len(value) > len(prefix) and value[len(prefix)] in "-_.:")
    if family("o1-mini") or family("o3-mini"):
        return False
    return (
        value.startswith("claude-")
        or family("grok-4.5")
        or family("grok-4.6")
        or family("grok-4.7")
        or family("kimi-k3")
        or family("deepseek-v4-flash-vision-exp")
		or family("gpt-5")
		or family("gpt-6-astra")
        or family("gpt-4o")
        or family("gpt-4.1")
        or family("o1")
        or family("o3")
        or family("o4-mini")
    )

def provider_name(name):
    value = name.strip().lower()
    if value.startswith("claude-"):
        return "routercheap-anthropic"
    if value.startswith("gpt-") or (len(value) >= 2 and value[0] == "o" and value[1].isdigit()):
        return "routercheap"
    return "routercheap-compatible"

config = {}
if config_path.exists():
    with config_path.open("r", encoding="utf-8") as handle:
        config = fast_safe_load(handle) or {}
if not isinstance(config, dict):
    raise TypeError("Hermes config root must be a mapping")
providers = config.get("providers")
if providers is None:
    providers = {}
if not isinstance(providers, dict):
    raise TypeError("Hermes config 'providers' must be a mapping")

own = ("routercheap", "routercheap-anthropic", "routercheap-compatible")
other = ("relayfast", "relayfast-anthropic", "relayfast-compatible")
for name in own + (() if restore else other):
    providers.pop(name, None)

if not restore:
    groups = {
        "routercheap": {
            "name": "router.cheap (GPT / Responses)",
            "base_url": endpoint,
            "key_env": "ROUTER_CHEAP_API_KEY",
            "transport": "codex_responses",
            "models": {},
        },
        "routercheap-anthropic": {
            "name": "router.cheap (Claude / Messages)",
            "base_url": endpoint,
            "key_env": "ROUTER_CHEAP_API_KEY",
            "transport": "anthropic_messages",
            "models": {},
        },
        "routercheap-compatible": {
            "name": "router.cheap (OpenAI compatible)",
            "base_url": endpoint,
            "key_env": "ROUTER_CHEAP_API_KEY",
            "transport": "chat_completions",
            "models": {},
        },
    }
    models = [line.strip() for line in models_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not models:
        models = [selected_model]
    for model in dict.fromkeys(models):
        details = {}
        size = context_length(model)
        if size is not None:
            details["context_length"] = size
        if supports_image_input(model):
            details["supports_vision"] = True
        groups[provider_name(model)]["models"][model] = details
    for name, group in groups.items():
        if not group["models"]:
            continue
        group["default_model"] = selected_model if selected_model in group["models"] else next(iter(group["models"]))
        providers[name] = group

if providers:
    config["providers"] = providers
else:
    config.pop("providers", None)
config_path.parent.mkdir(parents=True, exist_ok=True)
atomic_yaml_write(config_path, config, sort_keys=False)
PY
  if [[ "$DRY_RUN" -eq 1 ]]; then
    ok "Would update Hermes' managed provider catalog in $config_path."
  else
    backup_file "$config_path"
    if ! "$python" "$helper" "$config_path" "$ENDPOINT" "$MODEL" "$restore" "$models_file"; then
      rm -f "$helper" "$models_file"
      fail "Hermes rejected the managed provider catalog."
    fi
  fi
  rm -f "$helper" "$models_file"
}

hermes_legacy_env_path() {
  printf '%s' "$HOME/.hermes/.env"
}

normalize_hermes_path_for_shell() {
  local path="$1"
  path="${path%$'\r'}"
  path="${path#\"}"
  path="${path%\"}"
  if command -v cygpath >/dev/null 2>&1 && [[ "$path" =~ ^[A-Za-z]:[\\/] ]]; then
    cygpath -u "$path"
  else
    printf '%s' "$path"
  fi
}

hermes_env_path() {
  local path=""
  if command -v hermes >/dev/null 2>&1; then
    path="$(hermes config env-path 2>/dev/null | awk 'NF { line=$0 } END { print line }')"
    path="$(normalize_hermes_path_for_shell "$path")"
    if [[ -n "$path" ]]; then printf '%s' "$path"; return 0; fi
  fi
  if [[ -n "${HERMES_HOME:-}" ]]; then
    printf '%s' "$HERMES_HOME/.env"
    return 0
  fi
  if [[ -n "${LOCALAPPDATA:-}" && "${OS:-}" == "Windows_NT" ]]; then
    path="$(normalize_hermes_path_for_shell "$LOCALAPPDATA/hermes/.env")"
    printf '%s' "$path"
    return 0
  fi
  hermes_legacy_env_path
}

dotenv_value() {
  local path="$1" name="$2"
  [[ -f "$path" ]] || return 0
  awk -v wanted="$name" '
    {
      line=$0
      sub(/^[[:space:]]*/, "", line)
      split(line, parts, "=")
      key=parts[1]
      sub(/[[:space:]]*$/, "", key)
      if (key != wanted) next
      value=substr(line, index(line, "=") + 1)
      sub(/^[[:space:]]*/, "", value)
      sub(/[[:space:]]*$/, "", value)
      if (length(value) >= 2 && ((substr(value,1,1) == "\"" && substr(value,length(value),1) == "\"") || (substr(value,1,1) == "\047" && substr(value,length(value),1) == "\047"))) {
        value=substr(value,2,length(value)-2)
      }
      found=value
    }
    END { if (found != "") print found }
  ' "$path"
}

hermes_saved_api_key() {
  local active legacy path base value key_name seen=""
  active="$(hermes_env_path)"
  legacy="$(hermes_legacy_env_path)"
  for path in "$active" "$legacy"; do
    [[ -n "$path" && -f "$path" ]] || continue
    [[ "$path" != "$seen" ]] || continue
    seen="$path"
    base="$(dotenv_value "$path" ROUTER_CHEAP_BASE_URL)"
    [[ -n "$base" ]] || base="$(dotenv_value "$path" OPENAI_BASE_URL)"
    [[ "${base%/}" == "${ENDPOINT%/}" ]] || continue
    for key_name in ROUTER_CHEAP_API_KEY OPENAI_API_KEY ANTHROPIC_API_KEY; do
      value="$(dotenv_value "$path" "$key_name")"
      [[ -n "$value" ]] || continue
      API_KEY="$value"
      API_KEY_SOURCE="Hermes credentials file $path"
      return 0
    done
  done
  return 1
}

remove_hermes_managed_blocks_at_path() {
  local path="$1" tmp
  [[ -f "$path" ]] || return 0
  tmp="$(mktemp)"
  remove_marked_block "$path" "$tmp" "# routercheap setup begin" "# routercheap setup end"
  remove_marked_block "$tmp" "$tmp.other" "# relayfast setup begin" "# relayfast setup end"
  if cmp -s "$path" "$tmp.other"; then
    rm -f "$tmp" "$tmp.other"
    return 0
  fi
  backup_file "$path"
  save_text_file "$path" "$tmp.other"
  rm -f "$tmp" "$tmp.other"
}

write_hermes_env() {
  local path legacy_path tmp block api_mode key_name provider_name verified_path saved_key effective_reasoning_effort
  if command -v hermes >/dev/null 2>&1 && [[ "$DRY_RUN" -eq 0 ]]; then
    local python
    set_setup_step "check_hermes_runtime"
    python="$(hermes_python_path || true)"
    [[ -n "$python" ]] || fail "Hermes' Python runtime was not found. Checked the launcher and sibling hermes-agent checkout; configuration files were not changed."
    "$python" -c 'from hermes_cli.config import fast_safe_load; from utils import atomic_yaml_write' >/dev/null 2>&1 ||
      fail "Hermes' Python runtime is missing the configuration helpers. Repair/update Hermes and rerun setup; configuration files were not changed."
  fi
  effective_reasoning_effort="$(hermes_effective_reasoning_effort "$MODEL")"
  path="$(hermes_env_path)"
  legacy_path="$(hermes_legacy_env_path)"
  api_mode="$(hermes_api_mode "$MODEL")"
  provider_name="$(hermes_managed_provider_name "$MODEL")"
  key_name="ROUTER_CHEAP_API_KEY"
  tmp="$(mktemp)"
  block="$(mktemp)"
  {
    printf '%s=%s\n' "$key_name" "$API_KEY"
    printf 'ROUTER_CHEAP_BASE_URL=%s\n' "$ENDPOINT"
    printf 'HERMES_MODEL=%s\n' "$MODEL"
  } > "$block"
  mkdir -p "$(dirname "$path")"
  remove_marked_block "$path" "$tmp" "# routercheap setup begin" "# routercheap setup end"
  remove_marked_block "$tmp" "$tmp.other" "# relayfast setup begin" "# relayfast setup end"
  {
    cat "$tmp.other"
    printf '\n# routercheap setup begin\n'
    cat "$block"
    printf '# routercheap setup end\n'
  } > "$tmp.next"
  backup_file "$path"
  save_text_file "$path" "$tmp.next"
  if [[ "$DRY_RUN" -eq 0 ]]; then chmod 600 "$path" 2>/dev/null || true; fi
  rm -f "$tmp" "$tmp.other" "$tmp.next" "$block"
  if [[ "$path" != "$legacy_path" ]]; then
    remove_hermes_managed_blocks_at_path "$legacy_path"
    ok "$(msg hermes_legacy_cleaned): $legacy_path"
  fi
  if command -v hermes >/dev/null 2>&1; then
    if [[ "$DRY_RUN" -eq 1 ]]; then
      update_hermes_managed_providers 0
      ok "Would select custom:$provider_name in Hermes."
    else
      update_hermes_managed_providers 0
      update_hermes_reasoning_session_fix 0
      hermes config set model.provider "custom:$provider_name" >/dev/null
      hermes config set model.default "$MODEL" >/dev/null
      hermes config set model.base_url "$ENDPOINT" >/dev/null
      hermes config set model.api_mode "$api_mode" >/dev/null
      if [[ -n "$effective_reasoning_effort" ]]; then
        hermes config set agent.reasoning_effort "$effective_reasoning_effort" >/dev/null
      fi
      verified_path="$(hermes_env_path)"
      [[ "$verified_path" == "$path" ]] || fail "Hermes active credentials path changed during setup: $verified_path"
      saved_key="$(dotenv_value "$verified_path" "$key_name")"
      [[ "$saved_key" == "$API_KEY" ]] || fail "Hermes active credentials file does not contain the configured router.cheap API key."
    fi
  else
    warn "hermes command was not found. Install Hermes and rerun setup so the model-specific API mode can be applied."
  fi
  ok "$(msg hermes_env_path): $path"
  ok "$(msg hermes_protocol): $api_mode"
  [[ -n "$effective_reasoning_effort" ]] || effective_reasoning_effort=native-thinking
  ok "$(msg hermes_reasoning): $effective_reasoning_effort (/reasoning $(hermes_supported_reasoning_efforts "$MODEL"))"
}

restore_hermes_env() {
  local path legacy_path
  path="$(hermes_env_path)"
  legacy_path="$(hermes_legacy_env_path)"
  remove_hermes_managed_blocks_at_path "$path"
  if [[ "$path" != "$legacy_path" ]]; then remove_hermes_managed_blocks_at_path "$legacy_path"; fi
  if command -v hermes >/dev/null 2>&1; then
    if [[ "$DRY_RUN" -eq 1 ]]; then
      ok "Would restore Hermes model provider settings."
    else
      update_hermes_managed_providers 1
      update_hermes_reasoning_session_fix 1
      hermes config set model.provider auto >/dev/null 2>&1 || true
      hermes config set model.base_url "" >/dev/null 2>&1 || true
      hermes config set model.api_mode "" >/dev/null 2>&1 || true
    fi
  fi
}

assert_cursor_closed() {
  if command -v pgrep >/dev/null 2>&1 && { pgrep -x Cursor >/dev/null 2>&1 || pgrep -x cursor >/dev/null 2>&1; }; then
    fail "$(msg cursor_closed)"
  fi
  if [[ "${OS:-}" == "Windows_NT" ]] && command -v tasklist.exe >/dev/null 2>&1 && tasklist.exe /FI "IMAGENAME eq Cursor.exe" 2>/dev/null | grep -qi 'Cursor\.exe'; then
    fail "$(msg cursor_closed)"
  fi
}

find_cursor_storage() {
  local uname_value root executable resolved
  local -a roots=()
  CURSOR_DATABASE_PATH=""
  CURSOR_NODE_PATH=""
  CURSOR_SQLITE_MODULE_PATH=""
  uname_value="$(uname -s 2>/dev/null || true)"
  case "$uname_value" in
    Darwin*)
      CURSOR_DATABASE_PATH="$HOME/Library/Application Support/Cursor/User/globalStorage/state.vscdb"
      roots+=("/Applications/Cursor.app/Contents/Resources/app" "$HOME/Applications/Cursor.app/Contents/Resources/app")
      ;;
    MINGW*|MSYS*|CYGWIN*)
      if [[ -n "${APPDATA:-}" ]]; then CURSOR_DATABASE_PATH="$(normalize_hermes_path_for_shell "$APPDATA/Cursor/User/globalStorage/state.vscdb")"; fi
      if [[ -n "${LOCALAPPDATA:-}" ]]; then
        root="$(normalize_hermes_path_for_shell "$LOCALAPPDATA/Programs/cursor/resources/app")"
        roots+=("$root")
      fi
      ;;
    *)
      CURSOR_DATABASE_PATH="${XDG_CONFIG_HOME:-$HOME/.config}/Cursor/User/globalStorage/state.vscdb"
      roots+=("/usr/share/cursor/resources/app" "/opt/Cursor/resources/app" "/opt/cursor/resources/app" "$HOME/.local/share/Cursor/resources/app")
      ;;
  esac
  executable="$(command -v cursor 2>/dev/null || true)"
  if [[ -n "$executable" ]] && command -v readlink >/dev/null 2>&1; then
    resolved="$(readlink -f "$executable" 2>/dev/null || true)"
    if [[ -n "$resolved" ]]; then
      roots+=("$(dirname "$(dirname "$resolved")")/resources/app")
    fi
  fi
  [[ -f "$CURSOR_DATABASE_PATH" ]] || fail "$(msg cursor_not_found)"
  for root in "${roots[@]}"; do
    [[ -x "$root/resources/helpers/node" || -x "$root/resources/helpers/node.exe" ]] || continue
    [[ -d "$root/node_modules/@vscode/sqlite3" ]] || continue
    if [[ -x "$root/resources/helpers/node" ]]; then CURSOR_NODE_PATH="$root/resources/helpers/node"; else CURSOR_NODE_PATH="$root/resources/helpers/node.exe"; fi
    CURSOR_SQLITE_MODULE_PATH="$root/node_modules/@vscode/sqlite3"
    return 0
  done
  fail "$(msg cursor_not_found)"
}

backup_cursor_database() {
  local backup path
  backup="$CURSOR_DATABASE_PATH.routercheap-backup-$(date +%Y%m%d-%H%M%S)-$$"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    ok "Would create Cursor database backup: $backup"
    return 0
  fi
  mkdir -p "$backup"
  chmod 700 "$backup" 2>/dev/null || true
  for path in "$CURSOR_DATABASE_PATH" "$CURSOR_DATABASE_PATH-wal" "$CURSOR_DATABASE_PATH-shm"; do
    [[ -f "$path" ]] || continue
    cp -p "$path" "$backup/$(basename "$path")"
    chmod 600 "$backup/$(basename "$path")" 2>/dev/null || true
  done
  ok "Cursor database backup: $backup"
}

cursor_managed_models() {
  local source model seen="|"
  source="$(available_chat_models)"
  [[ -n "$source" ]] || source="$MODEL"
  while IFS= read -r model; do
    cursor_compatible_model "$model" || continue
    [[ "$seen" != *"|$model|"* ]] || continue
    printf '%s\n' "$model"
    seen+="$model|"
  done <<< "$source"
  if cursor_compatible_model "$MODEL" && [[ "$seen" != *"|$MODEL|"* ]]; then printf '%s\n' "$MODEL"; fi
}

invoke_cursor_storage_update() {
  local mode="$1" helper models_file result cursor_key=""
  assert_cursor_closed
  find_cursor_storage
  backup_cursor_database
  if [[ "$DRY_RUN" -eq 1 ]]; then
    CURSOR_UPDATE_RESULT="{\"status\":\"$([[ "$mode" == setup ]] && printf configured || printf restored)\"}"
    return 0
  fi
  helper="$(mktemp)"
  models_file="$(mktemp)"
  if [[ "$mode" == "setup" ]]; then
    printf '[' > "$models_file"
    local first=1 escaped
    while IFS= read -r model; do
      [[ -n "$model" ]] || continue
      escaped="$(json_escape "$model")"
      [[ "$first" -eq 1 ]] || printf ',' >> "$models_file"
      printf '"%s"' "$escaped" >> "$models_file"
      first=0
    done < <(cursor_managed_models)
    printf ']\n' >> "$models_file"
  else
    printf '[]\n' > "$models_file"
  fi
  cat > "$helper" <<'JS'
"use strict";

const fs = require("fs");
const sqlite3 = require(process.argv[2]);
const databasePath = process.argv[3];
const action = process.argv[4];
const endpoint = process.argv[5];
const owner = process.argv[6];
const modelsPath = process.argv[7];
const applicationKey = "src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl.persistentStorage.applicationUser";
const apiKeyStorageKey = "cursorAuth/openAIKey";
const setupStateKey = "cheap-router/cursorSetupState.v1";

function openDatabase() {
  return new Promise((resolve, reject) => {
    const database = new sqlite3.Database(databasePath, sqlite3.OPEN_READWRITE, error => error ? reject(error) : resolve(database));
  });
}
function get(database, sql, params = []) {
  return new Promise((resolve, reject) => database.get(sql, params, (error, row) => error ? reject(error) : resolve(row)));
}
function run(database, sql, params = []) {
  return new Promise((resolve, reject) => database.run(sql, params, function(error) {
    if (error) reject(error); else resolve({ changes: this.changes });
  }));
}
function close(database) {
  return new Promise((resolve, reject) => database.close(error => error ? reject(error) : resolve()));
}
function clone(value) { return value === undefined ? undefined : JSON.parse(JSON.stringify(value)); }
function capture(object, property) {
  return Object.prototype.hasOwnProperty.call(object, property) ? { exists: true, value: clone(object[property]) } : { exists: false };
}
function restoreProperty(object, property, snapshot) {
  if (snapshot && snapshot.exists) object[property] = clone(snapshot.value); else delete object[property];
}
function stringArray(value, label) {
  if (value === undefined) return [];
  if (!Array.isArray(value) || !value.every(item => typeof item === "string")) throw new TypeError(`Cursor setting '${label}' must be an array of strings`);
  return [...value];
}
async function upsert(database, key, value) {
  const updated = await run(database, "UPDATE ItemTable SET value = ? WHERE key = ?", [value, key]);
  if (updated.changes === 0) await run(database, "INSERT INTO ItemTable(key, value) VALUES(?, ?)", [key, value]);
}

async function main() {
  const database = await openDatabase();
  let transaction = false;
  try {
    await run(database, "BEGIN IMMEDIATE");
    transaction = true;
    const applicationRow = await get(database, "SELECT value FROM ItemTable WHERE key = ?", [applicationKey]);
    if (!applicationRow) throw new Error("Cursor application settings row was not found");
    const application = JSON.parse(String(applicationRow.value));
    if (!application || typeof application !== "object" || Array.isArray(application)) throw new TypeError("Cursor application settings must be a JSON object");
    const stateRow = await get(database, "SELECT value FROM ItemTable WHERE key = ?", [setupStateKey]);
    let state = stateRow ? JSON.parse(String(stateRow.value)) : null;
    if (state && state.version !== 1) throw new Error("Unsupported managed Cursor setup state version");

    if (action === "restore") {
      if (!state) {
        await run(database, "COMMIT"); transaction = false;
        process.stdout.write(JSON.stringify({ status: "not-managed" })); return;
      }
      if (state.owner !== owner) {
        await run(database, "COMMIT"); transaction = false;
        process.stdout.write(JSON.stringify({ status: "other-owner", owner: state.owner })); return;
      }
      const original = state.original;
      restoreProperty(application, "openAIBaseUrl", original.application.openAIBaseUrl);
      restoreProperty(application, "useOpenAIKey", original.application.useOpenAIKey);
      if (original.application.aiSettingsExists) {
        if (!application.aiSettings || typeof application.aiSettings !== "object" || Array.isArray(application.aiSettings)) application.aiSettings = {};
        restoreProperty(application.aiSettings, "userAddedModels", original.application.userAddedModels);
        restoreProperty(application.aiSettings, "modelOverrideEnabled", original.application.modelOverrideEnabled);
        restoreProperty(application.aiSettings, "modelOverrideDisabled", original.application.modelOverrideDisabled);
      } else delete application.aiSettings;
      await upsert(database, applicationKey, JSON.stringify(application));
      if (original.apiKey.exists) await upsert(database, apiKeyStorageKey, original.apiKey.value);
      else await run(database, "DELETE FROM ItemTable WHERE key = ?", [apiKeyStorageKey]);
      await run(database, "DELETE FROM ItemTable WHERE key = ?", [setupStateKey]);
      await run(database, "COMMIT"); transaction = false;
      process.stdout.write(JSON.stringify({ status: "restored" })); return;
    }

    if (action !== "setup") throw new Error(`Unknown Cursor setup action '${action}'`);
    const apiKey = process.env.ROUTER_CHEAP_CURSOR_SETUP_KEY || "";
    if (!apiKey.startsWith("sk-")) throw new Error("Cursor setup API key is missing or malformed");
    const models = JSON.parse(fs.readFileSync(modelsPath, "utf8"));
    if (!Array.isArray(models) || models.length === 0 || !models.every(item => typeof item === "string" && item.trim())) throw new TypeError("Cursor setup model catalog is empty or malformed");
    const uniqueModels = [...new Set(models.map(item => item.trim()))];
    const apiKeyRow = await get(database, "SELECT value FROM ItemTable WHERE key = ?", [apiKeyStorageKey]);
    const aiSettingsExists = Object.prototype.hasOwnProperty.call(application, "aiSettings");
    if (aiSettingsExists && (!application.aiSettings || typeof application.aiSettings !== "object" || Array.isArray(application.aiSettings))) throw new TypeError("Cursor setting 'aiSettings' must be a JSON object");
    if (!state) {
      const aiSettings = aiSettingsExists ? application.aiSettings : {};
      state = {
        version: 1, owner, managedModels: [],
        original: {
          application: {
            openAIBaseUrl: capture(application, "openAIBaseUrl"),
            useOpenAIKey: capture(application, "useOpenAIKey"),
            aiSettingsExists,
            userAddedModels: capture(aiSettings, "userAddedModels"),
            modelOverrideEnabled: capture(aiSettings, "modelOverrideEnabled"),
            modelOverrideDisabled: capture(aiSettings, "modelOverrideDisabled")
          },
          apiKey: apiKeyRow ? { exists: true, value: String(apiKeyRow.value) } : { exists: false }
        }
      };
    }
    if (!application.aiSettings || typeof application.aiSettings !== "object" || Array.isArray(application.aiSettings)) application.aiSettings = {};
    const previousManaged = new Set(Array.isArray(state.managedModels) ? state.managedModels : []);
    const currentManaged = new Set(uniqueModels);
    const originalAdded = new Set(stringArray(state.original.application.userAddedModels.exists ? state.original.application.userAddedModels.value : undefined, "managed original userAddedModels"));
    const originalEnabled = new Set(stringArray(state.original.application.modelOverrideEnabled.exists ? state.original.application.modelOverrideEnabled.value : undefined, "managed original modelOverrideEnabled"));
    const keep = (value, originals) => !previousManaged.has(value) || currentManaged.has(value) || originals.has(value);
    const added = stringArray(application.aiSettings.userAddedModels, "aiSettings.userAddedModels").filter(value => keep(value, originalAdded));
    const enabled = stringArray(application.aiSettings.modelOverrideEnabled, "aiSettings.modelOverrideEnabled").filter(value => keep(value, originalEnabled));
    const disabled = stringArray(application.aiSettings.modelOverrideDisabled, "aiSettings.modelOverrideDisabled").filter(value => !currentManaged.has(value));
    for (const model of uniqueModels) {
      if (!added.includes(model)) added.push(model);
      if (!enabled.includes(model)) enabled.push(model);
    }
    application.openAIBaseUrl = endpoint;
    application.useOpenAIKey = true;
    application.aiSettings.userAddedModels = added;
    application.aiSettings.modelOverrideEnabled = enabled;
    application.aiSettings.modelOverrideDisabled = disabled;
    state.owner = owner;
    state.managedModels = uniqueModels;
    await upsert(database, applicationKey, JSON.stringify(application));
    await upsert(database, apiKeyStorageKey, apiKey);
    await upsert(database, setupStateKey, JSON.stringify(state));
    await run(database, "COMMIT"); transaction = false;
    process.stdout.write(JSON.stringify({ status: "configured", modelCount: uniqueModels.length }));
  } catch (error) {
    if (transaction) { try { await run(database, "ROLLBACK"); } catch (_) {} }
    throw error;
  } finally { await close(database); }
}

main().catch(error => {
  process.stderr.write(String(error && error.stack ? error.stack : error));
  process.exitCode = 1;
});
JS
  if [[ "$mode" == "setup" ]]; then cursor_key="$API_KEY"; fi
  if ! result="$(ROUTER_CHEAP_CURSOR_SETUP_KEY="$cursor_key" "$CURSOR_NODE_PATH" "$helper" "$CURSOR_SQLITE_MODULE_PATH" "$CURSOR_DATABASE_PATH" "$mode" "$ENDPOINT" routercheap "$models_file" 2>&1)"; then
    rm -f "$helper" "$models_file"
    fail "Cursor settings update failed: $result"
  fi
  rm -f "$helper" "$models_file"
  CURSOR_UPDATE_RESULT="$result"
}

write_cursor_config() {
  test_openai_key chat
  section "$(msg writing)"
  set_setup_step "write_cursor_config"
  invoke_cursor_storage_update setup
  ok "$(msg cursor_configured)"
  warn "$(msg cursor_limit)"
}

restore_cursor_config() {
  local owner
  invoke_cursor_storage_update restore
  case "$CURSOR_UPDATE_RESULT" in
    *'"status":"restored"'*) ok "$(msg cursor_restored)" ;;
    *'"status":"not-managed"'*) warn "$(msg cursor_not_managed)" ;;
    *'"status":"other-owner"'*)
      owner="$(printf '%s' "$CURSOR_UPDATE_RESULT" | sed -n 's/.*"owner":"\([^"]*\)".*/\1/p')"
      warn "$(fmt_msg cursor_other_owner "$owner")"
      ;;
    *) fail "Unexpected Cursor restore result: $CURSOR_UPDATE_RESULT" ;;
  esac
}

env_value_to_api_key() {
  local name="$1" value
  value="${!name-}"
  value="$(printf '%s' "$value" | tr -d '\r\n\t ')"
  if [[ -n "$value" ]]; then
    API_KEY="$value"
    API_KEY_SOURCE="$name"
    return 0
  fi
  return 1
}

env_url_matches() {
  local name="$1" expected="$2" value actual_lower expected_lower
  value="${!name-}"
  [[ -n "$value" ]] || return 1
  value="${value%/}"
  expected="${expected%/}"
  actual_lower="$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')"
  expected_lower="$(printf '%s' "$expected" | tr '[:upper:]' '[:lower:]')"
  [[ "$actual_lower" == "$expected_lower" ]]
}

get_saved_api_key() {
  API_KEY_SOURCE=""
  env_value_to_api_key ROUTER_CHEAP_API_KEY && return 0
  env_value_to_api_key ROUTER_CHEAP_OPENCODE_API_KEY && return 0
  if [[ "$APP" == "hermes" ]]; then hermes_saved_api_key && return 0; fi
  if env_url_matches ANTHROPIC_BASE_URL "$ANTHROPIC_ENDPOINT"; then
    env_value_to_api_key ANTHROPIC_AUTH_TOKEN && return 0
  fi
  if env_url_matches OPENAI_BASE_URL "$ENDPOINT"; then
    env_value_to_api_key OPENAI_API_KEY && return 0
  fi
  return 1
}

prompt_api_key() {
  local prompt="$1" entered
  printf '%s' "$prompt"
  IFS= read -r -s entered || entered=""
  printf '\n'
  API_KEY="$entered"
}

api_key_is_valid() {
  [[ "${1:-}" == sk-* ]]
}

get_api_key() {
  local using_saved=0 saved_key=""
  if [[ -z "$API_KEY" ]]; then
    if get_saved_api_key; then
      saved_key="$API_KEY"
      warn "$(msg saved_key_found) ($API_KEY_SOURCE): $(mask_key "$API_KEY")"
      if [[ -t 0 ]]; then
        prompt_api_key "$(msg saved_key_prompt)"
        if [[ -z "$API_KEY" ]]; then
          API_KEY="$saved_key"
          using_saved=1
        fi
      else
        using_saved=1
      fi
    else
      prompt_api_key "$(msg paste_key)"
    fi
  fi
  API_KEY="$(printf '%s' "$API_KEY" | tr -d '\r\n\t ')"
  while ! api_key_is_valid "$API_KEY"; do
    [[ -t 0 ]] || fail "$(msg invalid_key)"
    warn "$(msg invalid_key)"
    using_saved=0
    prompt_api_key "$(msg paste_key)"
    API_KEY="$(printf '%s' "$API_KEY" | tr -d '\r\n\t ')"
  done
  if [[ "$using_saved" -eq 1 ]]; then ok "$(msg saved_key_using) ($API_KEY_SOURCE)."; fi
}

setup_app() {
  get_api_key
  TELEMETRY_ACTION="setup"
  TELEMETRY_ENABLED=1
  TELEMETRY_ERROR_MESSAGE=""
  TELEMETRY_ERROR_STEP="setup"
  TELEMETRY_ERROR_FUNCTION=""
  TELEMETRY_ERROR_LINE=0
  TELEMETRY_EXIT_CODE=0
  TELEMETRY_SESSION_ID="$(new_setup_session_id)"
  TELEMETRY_STARTED_AT="$(date +%s 2>/dev/null || printf '0')"
  warn "$(fmt_msg telemetry_session "" "" "$TELEMETRY_SESSION_ID")"
  send_setup_telemetry setup started
  if [[ "$APP" == "codex" ]]; then install_codex_if_missing; fi
  prepare_setup_model
  choose_default_openai_model_interactive
  ok "$(msg endpoint): $(if [[ "$APP" == "claude-code" ]]; then printf '%s' "$ANTHROPIC_ENDPOINT"; else printf '%s' "$ENDPOINT"; fi)"
  ok "$(msg model): $(if [[ "$APP" == "claude-code" ]]; then printf '%s' "$CLAUDE_MODEL"; elif [[ "$APP" == "grok-build" ]]; then printf '%s' "$GROK_MODEL"; else printf '%s' "$MODEL"; fi)"
  ok "$(msg key): $(mask_key "$API_KEY")"
  case "$APP" in
    codex)
      test_openai_key responses
      section "$(msg writing)"
      stop_codex_for_setup
      set_setup_step "write_shell_profile"
      tmp="$(mktemp)"
      printf 'export ROUTER_CHEAP_API_KEY=%s\n' "$(shell_quote "$API_KEY")" > "$tmp"
      write_profile_block codex "$tmp"
      rm -f "$tmp"
      export ROUTER_CHEAP_API_KEY="$API_KEY"
      set_setup_step "install_codex_image_tool"
      install_codex_image_tool
      set_setup_step "write_codex_config"
      write_codex_config
      if [[ "$DRY_RUN" -eq 1 ]]; then
        warn "DryRun: Codex configuration was not written; provider verification will run after a real setup."
      else
        assert_codex_provider_configuration "$(codex_config_path)" "routercheap" "$ENDPOINT" "ROUTER_CHEAP_API_KEY" "$MODEL"
      fi
      codex_auth_diagnostics "$(codex_config_path)"
      if [[ "$DRY_RUN" -eq 0 ]]; then codex_runtime_probe "$MODEL"; fi
      warn "$(fmt_msg codex_picker_hint "" "$MODEL")"
      warn "$(msg codex_history_notice)"
      start_codex_after_setup
      command -v codex >/dev/null 2>&1 || warn "codex command was not found. Install Codex before testing."
      ;;
    claude-code)
      section "$(msg writing)"
      set_setup_step "write_shell_profile"
      tmp="$(mktemp)"
      {
        printf 'unset ANTHROPIC_API_KEY\n'
        printf 'export ANTHROPIC_BASE_URL=%s\n' "$(shell_quote "$ANTHROPIC_ENDPOINT")"
        printf 'export ANTHROPIC_AUTH_TOKEN=%s\n' "$(shell_quote "$API_KEY")"
        printf 'export ANTHROPIC_MODEL=%s\n' "$(shell_quote "$CLAUDE_MODEL")"
      } > "$tmp"
      write_profile_block claude-code "$tmp"
      rm -f "$tmp"
      set_setup_step "write_claude_settings"
      write_claude_settings
      warn "$(msg claude_login_preserved)"
      ;;
    opencode)
      test_coding_agent_key
      section "$(msg writing)"
      set_setup_step "write_shell_profile"
      tmp="$(mktemp)"
      {
        printf 'export ROUTER_CHEAP_OPENCODE_API_KEY=%s\n' "$(shell_quote "$API_KEY")"
        printf 'export OPENCODE_CONFIG=%s\n' "$(shell_quote "$HOME/.config/opencode/routercheap.json")"
      } > "$tmp"
      write_profile_block opencode "$tmp"
      rm -f "$tmp"
      set_setup_step "write_opencode_config"
      write_opencode_config
      command -v opencode >/dev/null 2>&1 || warn "opencode command was not found. Install OpenCode before testing."
      ;;
    hermes)
      test_coding_agent_key
      effective_reasoning_effort="$(hermes_effective_reasoning_effort "$MODEL")"
      if [[ -n "$effective_reasoning_effort" ]]; then
        HERMES_REASONING_EFFORT="$effective_reasoning_effort"
        validate_hermes_reasoning_effort "$MODEL"
      fi
      section "$(msg writing)"
      set_setup_step "write_hermes_config"
      write_hermes_env
      command -v hermes >/dev/null 2>&1 || warn "hermes command was not found. Install Hermes before testing."
      ;;
    grok-build)
      MODEL="$GROK_MODEL"
      test_openai_key responses
      section "$(msg writing)"
      set_setup_step "find_grok_cli"
      grok_bin="$(grok_executable || true)"
      [[ -n "$grok_bin" ]] || fail "$(msg grok_missing)"
      set_setup_step "write_grok_config"
      write_grok_config "$grok_bin"
      set_setup_step "write_grok_launcher"
      write_grok_launcher "$grok_bin"
      ;;
    cursor)
      write_cursor_config
      ;;
    droid)
      test_openai_key chat
      section "$(msg writing)"
      set_setup_step "write_shell_profile"
      tmp="$(mktemp)"
      printf 'export ROUTER_CHEAP_API_KEY=%s\n' "$(shell_quote "$API_KEY")" > "$tmp"
      write_profile_block droid "$tmp"
      rm -f "$tmp"
      set_setup_step "write_droid_config"
      write_droid_config
      command -v droid >/dev/null 2>&1 || warn "droid command was not found. Install Factory Droid before testing."
      ;;
    *) fail "$(msg bad_choice)" ;;
  esac
  send_setup_telemetry setup success
  TELEMETRY_ENABLED=0
  TELEMETRY_ERROR_STEP=""
  ok "$(msg done)"
}

restore_app() {
  case "$APP" in
    codex) stop_codex_for_setup; remove_profile_block codex; restore_codex_config; remove_codex_image_tool; warn "$(msg codex_history_notice)"; start_codex_after_setup ;;
    claude-code) remove_profile_block claude-code; restore_claude_settings; warn "$(msg claude_login_restore)" ;;
    opencode) restore_opencode_config ;;
    hermes) restore_hermes_env ;;
    grok-build) restore_grok_config; restore_grok_launcher ;;
    cursor) restore_cursor_config ;;
    *) fail "$(msg bad_choice)" ;;
  esac
  ok "$(msg restored)"
}

on_exit() {
  local rc=$?
  start_codex_after_setup || true
  if [[ $rc -ne 0 && "${TELEMETRY_ENABLED:-0}" -eq 1 && -n "${TELEMETRY_ACTION:-}" ]]; then
    TELEMETRY_EXIT_CODE="$rc"
    if [[ -z "${TELEMETRY_ERROR_MESSAGE:-}" ]]; then
      TELEMETRY_ERROR_MESSAGE="Script exited with status $rc"
    fi
    send_setup_telemetry "$TELEMETRY_ACTION" failed || true
  fi
}

trap 'capture_setup_error "$?" "$LINENO" "${FUNCNAME[0]:-main}"' ERR
trap on_exit EXIT

ENDPOINT="$(normalize_openai_base_url "$ENDPOINT")"
ANTHROPIC_ENDPOINT="$(normalize_anthropic_base_url "$ANTHROPIC_ENDPOINT")"

section "$(msg title)"
case "$APP" in ""|codex|claude-code|opencode|hermes|grok-build|cursor|droid) ;; *) fail "$(msg bad_choice)" ;; esac
case "$ACTION" in ""|setup|setup-reserve|restore) ;; *) fail "$(msg bad_choice)" ;; esac

if [[ -z "$APP" ]]; then choose_app; fi
if [[ -z "$ACTION" ]]; then choose_action; fi

if [[ "$ACTION" == "setup-reserve" ]]; then set_reserve_endpoints; fi
ENDPOINT="$(normalize_openai_base_url "$ENDPOINT")"
ANTHROPIC_ENDPOINT="$(normalize_anthropic_base_url "$ANTHROPIC_ENDPOINT")"

if [[ "$ACTION" == "restore" ]] && ! supports_restore "$APP"; then
  fail "$(msg restore_not_needed)"
fi

if [[ "$ACTION" == "setup" || "$ACTION" == "setup-reserve" ]]; then
  setup_app
else
  restore_app
fi
if [[ "$ACTION" == "setup" || "$ACTION" == "setup-reserve" ]]; then warn "$(msg network_hint)"; fi
