#!/usr/bin/env bash
# Safely configures Claude Desktop's managed 3P inference profile for aimarket.
# Chat databases, local browser storage, account state, and Claude Code sessions are
# never edited. Known local history stores are copied before setup and restore.

set -euo pipefail
umask 077

LANG_CODE=""
ACTION=""
API_KEY=""
ENDPOINT="https://router.cheap"
SKIP_ENDPOINT_TEST=0
SKIP_HISTORY_BACKUP=0
DRY_RUN=0
NORMAL_CONFIG_DIRECTORY=""
THREEP_CONFIG_DIRECTORY=""
BACKUP_DIRECTORY=""
HISTORY_OVERRIDES=()

PROFILE_ID="7c532ace-9355-4acb-a881-3bcf5d893c41"
PROFILE_NAME="aimarket"
SCRIPT_VERSION="1.4"
PREFERRED_MODELS="claude-opus-5,claude-sonnet-5,claude-opus-4-8,claude-haiku-4-5,claude-fable-5,claude-mythos-5,claude-opus-4-7,claude-sonnet-4-6,claude-opus-4-6"

NETWORK_PHASE=0
fail() {
  printf '[FAIL] %s\n' "$*" >&2
  if [[ "$NETWORK_PHASE" -eq 1 ]]; then printf '[WARN] %s\n' "$(msg network_hint)" >&2; fi
  exit 1
}
info() { printf '[INFO] %s\n' "$*"; }
ok() { printf '[OK] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*"; }

msg() {
  local key="$1"
  if [[ "$LANG_CODE" == "ru" ]]; then
    case "$key" in
      title) printf '%s' 'Настройка Claude Desktop для aimarket' ;;
      choose) printf '%s' 'Выберите действие:' ;;
      setup) printf '%s' 'Настроить Claude Desktop для aimarket' ;;
      setup_reserve) printf '%s' 'Настроить Claude Desktop через резервный endpoint' ;;
      network_hint) printf '%s' 'Если соединение обрывается (ECONNRESET, тайм-ауты), повторите настройку с запасным адресом: на странице подключения откройте «Если соединение обрывается» или запустите установщик с --action setup-reserve. Если не помогло, попробуйте VPN, который не рвёт потоковые соединения.' ;;
      running_prompt) printf '%s' 'Claude Desktop сейчас открыт, его нужно закрыть на время настройки. Enter — закрыть Claude Desktop, n — отмена: ' ;;
      closing) printf '%s' 'Закрываю Claude Desktop' ;;
      clipboard_key) printf '%s' 'В буфере обмена найден ключ' ;;
      clipboard_prompt) printf '%s' 'Нажмите Enter, чтобы использовать его, или вставьте другой ключ (ввод скрыт): ' ;;
      setup_key) printf '%s' 'Использую ключ из ссылки установки' ;;
      restore) printf '%s' 'Вернуть предыдущий/официальный профиль Claude Desktop' ;;
      exit) printf '%s' 'Выйти' ;;
      invalid) printf '%s' 'Неверный выбор.' ;;
      close) printf '%s' 'Полностью закройте Claude Desktop и запустите скрипт снова. Приложение должно быть закрыто, чтобы история и настройки оставались целыми.' ;;
      key) printf '%s' 'Вставьте API-ключ aimarket (ввод скрыт)' ;;
      invalid_key) printf '%s' 'API-ключ введён некорректно. Он должен начинаться с sk-. Попробуйте ещё раз.' ;;
      testing) printf '%s' 'Проверяю Anthropic-совместимый шлюз' ;;
      backup) printf '%s' 'Создаю резервную копию настроек и локальной истории/сессий Claude Desktop' ;;
      backup_skipped) printf '%s' 'Копирование локальной истории/сессий явно пропущено; файлы конфигурации всё равно будут сохранены.' ;;
      no_history) printf '%s' 'Локальные хранилища истории/сессий Claude не найдены. Конфигурация всё равно будет сохранена.' ;;
      configuring) printf '%s' 'Записываю управляемый 3P-профиль Claude Desktop' ;;
      restoring) printf '%s' 'Удаляю только профиль aimarket и возвращаю предыдущий выбор' ;;
      done) printf '%s' 'Готово. Хранилища чатов и сессий не изменялись. Полностью закройте и снова откройте Claude Desktop.' ;;
      restored) printf '%s' 'Восстановлено. Хранилища чатов и сессий не изменялись. Полностью закройте и снова откройте Claude Desktop.' ;;
      history_notice) printf '%s' 'Официальные чаты Claude хранятся в аккаунте Anthropic, а чаты стороннего провайдера — локально в отдельном профиле. Надёжно объединить их нельзя. Чтобы снова увидеть официальные чаты, выберите вход Anthropic или выполните Восстановление.' ;;
      nothing) printf '%s' 'Профиль aimarket для Claude Desktop не установлен; ничего не изменено.' ;;
      plaintext) printf '%s' 'Claude Desktop требует хранить ключ шлюза в локальном профиле. Профиль и резервные копии доступны только вашей учётной записи ОС.' ;;
      dry_run) printf '%s' 'Проверочный запуск: файлы не изменены.' ;;
      *) printf '%s' "$key" ;;
    esac
  else
    case "$key" in
      title) printf '%s' 'aimarket Claude Desktop setup' ;;
      choose) printf '%s' 'Choose action:' ;;
      setup) printf '%s' 'Configure Claude Desktop for aimarket' ;;
      setup_reserve) printf '%s' 'Configure Claude Desktop with the reserve endpoint' ;;
      network_hint) printf '%s' "If the connection drops (ECONNRESET, timeouts), rerun setup with the reserve endpoint: open 'If the connection drops' on the setup page, or run the installer with --action setup-reserve. If that does not help, use a VPN that does not reset streaming connections." ;;
      running_prompt) printf '%s' 'Claude Desktop is running and must be closed during setup. Press Enter to close it, or n to cancel: ' ;;
      closing) printf '%s' 'Closing Claude Desktop' ;;
      clipboard_key) printf '%s' 'Found a key in the clipboard' ;;
      clipboard_prompt) printf '%s' 'Press Enter to use it, or paste another key (input is hidden): ' ;;
      setup_key) printf '%s' 'Using the key from the setup link' ;;
      restore) printf '%s' 'Restore the previously active/official Claude Desktop profile' ;;
      exit) printf '%s' 'Exit' ;;
      invalid) printf '%s' 'Invalid choice.' ;;
      close) printf '%s' 'Fully quit Claude Desktop and run this script again. It must be closed so chat storage and configuration stay consistent.' ;;
      key) printf '%s' 'Paste aimarket API key (input is hidden)' ;;
      invalid_key) printf '%s' 'API key is invalid. It must start with sk-. Please try again.' ;;
      testing) printf '%s' 'Testing the Anthropic-compatible gateway' ;;
      backup) printf '%s' 'Creating a safety backup of Claude Desktop configuration and local chat/session state' ;;
      backup_skipped) printf '%s' 'Local chat/session backup was explicitly skipped; configuration files are still backed up.' ;;
      no_history) printf '%s' 'No local Claude chat/session stores were found. Configuration backup will still be created.' ;;
      configuring) printf '%s' 'Writing the managed Claude Desktop 3P profile' ;;
      restoring) printf '%s' 'Removing only the aimarket profile and restoring the previous selection' ;;
      done) printf '%s' 'Configured. Existing chat/session stores were not modified. Fully quit and reopen Claude Desktop.' ;;
      restored) printf '%s' 'Restored. Existing chat/session stores were not modified. Fully quit and reopen Claude Desktop.' ;;
      history_notice) printf '%s' 'Standard Claude chats are stored in your Anthropic account, while third-party-provider chats are stored locally in a separate profile. They cannot be merged reliably. Choose Anthropic sign-in, or run Restore, to see your official chats again.' ;;
      nothing) printf '%s' 'The aimarket Claude Desktop profile is not installed; nothing was changed.' ;;
      plaintext) printf '%s' 'Claude Desktop requires the gateway key in its local profile. The profile and backups are readable only by your OS user account.' ;;
      dry_run) printf '%s' 'Dry run: no files were changed.' ;;
      *) printf '%s' "$key" ;;
    esac
  fi
}

usage() {
  printf '%s\n' 'Usage: setup-aimarket-claude-desktop.sh [options]'
  printf '%s\n' '  --lang en|ru  --action setup|restore  --api-key KEY'
  printf '%s\n' '  --endpoint https://router.cheap  --skip-endpoint-test'
  printf '%s\n' '  --skip-history-backup  --dry-run'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lang) [[ $# -ge 2 ]] || fail '--lang requires a value'; LANG_CODE="$2"; shift 2 ;;
    --lang=*) LANG_CODE="${1#*=}"; shift ;;
    --action) [[ $# -ge 2 ]] || fail '--action requires a value'; ACTION="$2"; shift 2 ;;
    --action=*) ACTION="${1#*=}"; shift ;;
    --api-key) [[ $# -ge 2 ]] || fail '--api-key requires a value'; API_KEY="$2"; shift 2 ;;
    --api-key=*) API_KEY="${1#*=}"; shift ;;
    --endpoint) [[ $# -ge 2 ]] || fail '--endpoint requires a value'; ENDPOINT="$2"; shift 2 ;;
    --endpoint=*) ENDPOINT="${1#*=}"; shift ;;
    --skip-endpoint-test) SKIP_ENDPOINT_TEST=1; shift ;;
    --skip-history-backup) SKIP_HISTORY_BACKUP=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --normal-config-directory) [[ $# -ge 2 ]] || fail '--normal-config-directory requires a value'; NORMAL_CONFIG_DIRECTORY="$2"; shift 2 ;;
    --threep-config-directory) [[ $# -ge 2 ]] || fail '--threep-config-directory requires a value'; THREEP_CONFIG_DIRECTORY="$2"; shift 2 ;;
    --backup-directory) [[ $# -ge 2 ]] || fail '--backup-directory requires a value'; BACKUP_DIRECTORY="$2"; shift 2 ;;
    --history-data-directory) [[ $# -ge 2 ]] || fail '--history-data-directory requires a value'; HISTORY_OVERRIDES+=("$2"); shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) fail "Unknown argument: $1" ;;
  esac
done

[[ "$(uname -s)" == "Darwin" ]] || fail 'Claude Desktop managed 3P setup is supported by this script only on macOS.'
if [[ -z "$LANG_CODE" ]]; then
  case "${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}" in ru*) LANG_CODE="ru" ;; *) LANG_CODE="en" ;; esac
fi
[[ "$LANG_CODE" == "en" || "$LANG_CODE" == "ru" ]] || fail '--lang must be en or ru.'
[[ -z "$ACTION" || "$ACTION" == "setup" || "$ACTION" == "setup-reserve" || "$ACTION" == "restore" ]] || fail '--action must be setup, setup-reserve, or restore.'

ENDPOINT="${ENDPOINT%/}"
case "$ENDPOINT" in */v1) ENDPOINT="${ENDPOINT%/v1}" ;; esac
case "$ENDPOINT" in https://*) ;; *) fail 'Endpoint must be an absolute HTTPS URL.' ;; esac
case "$ENDPOINT" in *\?*|*\#*) fail 'Endpoint must not contain a query string or fragment.' ;; esac

printf '\n%s\n\n' "$(msg title)"
if [[ -z "$ACTION" ]]; then ACTION="setup"; fi

claude_running() {
  /usr/bin/osascript -e 'application "Claude" is running' 2>/dev/null | /usr/bin/grep -q '^true$'
}

if claude_running; then
  [[ -t 0 && "$DRY_RUN" -eq 0 ]] || fail "$(msg close)"
  printf '%s' "$(msg running_prompt)"
  IFS= read -r answer || answer="n"
  case "$answer" in n|N|no|NO|н|Н|нет|Нет) fail "$(msg close)" ;; esac
  ok "$(msg closing)"
  /usr/bin/osascript -e 'tell application "Claude" to quit' >/dev/null 2>&1 || true
  for _ in $(seq 1 20); do
    claude_running || break
    sleep 1
  done
  if claude_running; then fail "$(msg close)"; fi
fi

NORMAL_ROOT="${NORMAL_CONFIG_DIRECTORY:-$HOME/Library/Application Support/Claude}"
THREEP_ROOT="${THREEP_CONFIG_DIRECTORY:-$HOME/Library/Application Support/Claude-3p}"
BACKUP_ROOT="${BACKUP_DIRECTORY:-$HOME/.aimarket/claude-desktop-backups}"
NORMAL_CONFIG="$NORMAL_ROOT/claude_desktop_config.json"
THREEP_CONFIG="$THREEP_ROOT/claude_desktop_config.json"
META_FILE="$THREEP_ROOT/configLibrary/_meta.json"
PROFILE_FILE="$THREEP_ROOT/configLibrary/$PROFILE_ID.json"
STATE_FILE="$BACKUP_ROOT/switch-state.json"

RUNTIME_DIR="$(/usr/bin/mktemp -d "${TMPDIR:-/tmp}/aimarket-claude-desktop.XXXXXX")"
chmod 700 "$RUNTIME_DIR"
cleanup() {
  case "$RUNTIME_DIR" in "${TMPDIR:-/tmp}"/aimarket-claude-desktop.*) /bin/rm -rf "$RUNTIME_DIR" ;; esac
}
trap cleanup EXIT HUP INT TERM
JXA_FILE="$RUNTIME_DIR/manage.js"
KEY_FILE="$RUNTIME_DIR/key"
CATALOG_FILE="$RUNTIME_DIR/models.json"
HEADERS_FILE="$RUNTIME_DIR/headers"
BODY_FILE="$RUNTIME_DIR/request.json"
RESPONSE_FILE="$RUNTIME_DIR/response.json"

/bin/cat >"$JXA_FILE" <<'JXA'
ObjC.import('Foundation');

function exists(path) {
  return $.NSFileManager.defaultManager.fileExistsAtPath($(path));
}
function directory(path) {
  return ObjC.unwrap($(path).stringByDeletingLastPathComponent);
}
function ensureDirectory(path) {
  var error = Ref();
  if (!$.NSFileManager.defaultManager.createDirectoryAtPathWithIntermediateDirectoriesAttributesError($(path), true, $(), error)) {
    throw new Error('Cannot create directory: ' + path);
  }
}
function readText(path) {
  if (!exists(path)) return null;
  var error = Ref();
  var value = $.NSString.stringWithContentsOfFileEncodingError($(path), $.NSUTF8StringEncoding, error);
  if (!value) throw new Error('Cannot read: ' + path);
  return ObjC.unwrap(value);
}
function writeText(path, text) {
  ensureDirectory(directory(path));
  var error = Ref();
  if (!$(text).writeToFileAtomicallyEncodingError($(path), true, $.NSUTF8StringEncoding, error)) {
    throw new Error('Cannot write: ' + path);
  }
}
function removeFile(path) {
  if (!exists(path)) return;
  var error = Ref();
  if (!$.NSFileManager.defaultManager.removeItemAtPathError($(path), error)) {
    throw new Error('Cannot remove: ' + path);
  }
}
function readObject(path) {
  var text = readText(path);
  if (text === null) return {};
  var value;
  try { value = JSON.parse(text); } catch (error) { throw new Error('Invalid JSON in ' + path + ': ' + error); }
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Expected a JSON object in ' + path);
  return value;
}
function writeObject(path, value) { writeText(path, JSON.stringify(value, null, 2) + '\n'); }
function hasEntry(entries, id) {
  for (var i = 0; i < entries.length; i++) if (entries[i] && String(entries[i].id || '') === id) return true;
  return false;
}
function withoutEntry(entries, id) {
  var result = [];
  for (var i = 0; i < entries.length; i++) if (!entries[i] || String(entries[i].id || '') !== id) result.push(entries[i]);
  return result;
}
function snapshot(paths) {
  var result = {};
  for (var i = 0; i < paths.length; i++) result[paths[i]] = readText(paths[i]);
  return result;
}
function rollback(saved) {
  for (var path in saved) {
    try { if (saved[path] === null) removeFile(path); else writeText(path, saved[path]); } catch (_) {}
  }
}
function legacyModeWasManaged(state, profileId) {
  return String(state.profile_id || '') === profileId && !Object.prototype.hasOwnProperty.call(state, 'script_version');
}
function removeLegacyMode(path) {
  if (!exists(path)) return;
  var config = readObject(path);
  if (String(config.deploymentMode || '') === '3p') {
    delete config.deploymentMode;
    writeObject(path, config);
  }
}

function run(argv) {
  var command = argv[0];
  if (command === 'error') {
    var text = String(readText(argv[1]) || '').trim();
    if (!text) return '';
    try {
      var payload = JSON.parse(text);
      if (payload && payload.error && payload.error.message) text = String(payload.error.message);
      else if (payload && payload.message) text = String(payload.message);
    } catch (_) {}
    text = text.replace(/\s+/g, ' ').trim();
    return text.length > 500 ? text.slice(0, 500) + '...' : text;
  }
  if (command === 'models') {
    var catalog = readObject(argv[1]);
    var preferred = argv[2].split(',');
    var available = [];
    var seen = {};
    var data = Array.isArray(catalog.data) ? catalog.data : [];
    var pattern = /^(anthropic\/)?claude-(sonnet|opus|haiku|fable|mythos)-[a-z0-9][a-z0-9._-]*$/i;
    for (var i = 0; i < data.length; i++) {
      var id = String((data[i] || {}).id || '');
      if (pattern.test(id) && !seen[id]) { seen[id] = true; available.push(id); }
    }
    if (!available.length) throw new Error('This key has no Claude Desktop-compatible models in GET /v1/models.');
    var ordered = [];
    for (i = 0; i < preferred.length; i++) if (seen[preferred[i]]) ordered.push(preferred[i]);
    available.sort();
    for (i = 0; i < available.length; i++) if (ordered.indexOf(available[i]) < 0) ordered.push(available[i]);
    return ordered.join(',');
  }

  var normal = argv[1], threep = argv[2], metaPath = argv[3], profilePath = argv[4], statePath = argv[5];
  var profileId = argv[6], profileName = argv[7];
  var meta = readObject(metaPath);
  var entries = Array.isArray(meta.entries) ? meta.entries : [];
  if (command === 'status') return exists(profilePath) || exists(statePath) || hasEntry(entries, profileId) ? 'INSTALLED' : 'NOT_INSTALLED';

  var paths = [normal, threep, metaPath, profilePath, statePath];
  var saved = snapshot(paths);
  try {
    if (command === 'setup') {
      var key = String(readText(argv[8]) || '').replace(/[\r\n]+$/, '');
      var endpoint = argv[9], models = argv[10].split(','), scriptVersion = argv[11];
      var current = String(meta.appliedId || '');
      var oldState = readObject(statePath);
      var previous = current && current !== profileId ? current : String(oldState.previousAppliedId || '');
      entries = withoutEntry(entries, profileId);
      entries.push({id: profileId, name: profileName});
      meta.entries = entries;
      meta.appliedId = profileId;
      var profile = {
        coworkEgressAllowedHosts: ['*'],
        inferenceGatewayApiKey: key,
        inferenceGatewayAuthScheme: 'bearer',
        inferenceGatewayBaseUrl: endpoint,
        inferenceModels: models,
        inferenceProvider: 'gateway'
      };
      if (legacyModeWasManaged(oldState, profileId)) {
        removeLegacyMode(normal);
        removeLegacyMode(threep);
      }
      writeObject(profilePath, profile);
      writeObject(metaPath, meta);
      writeObject(statePath, {profile_id: profileId, script_version: scriptVersion, previousAppliedId: previous, installed_at: new Date().toISOString()});
      return 'OK';
    }
    if (command === 'restore') {
      if (!exists(profilePath) && !exists(statePath) && !hasEntry(entries, profileId)) return 'NOTHING';
      var state = readObject(statePath);
      var currentApplied = String(meta.appliedId || '');
      entries = withoutEntry(entries, profileId);
      var target = '';
      if (currentApplied && currentApplied !== profileId && hasEntry(entries, currentApplied)) target = currentApplied;
      else if (state.previousAppliedId && hasEntry(entries, String(state.previousAppliedId))) target = String(state.previousAppliedId);
      else if (entries.length && entries[0] && entries[0].id) target = String(entries[0].id);
      meta.entries = entries;
      if (target) meta.appliedId = target; else delete meta.appliedId;
      writeObject(metaPath, meta);
      removeFile(profilePath);
      if (legacyModeWasManaged(state, profileId)) {
        removeLegacyMode(normal);
        removeLegacyMode(threep);
      }
      removeFile(statePath);
      return 'OK';
    }
    throw new Error('Unknown action: ' + command);
  } catch (error) {
    rollback(saved);
    throw error;
  }
}
JXA

jxa() { /usr/bin/osascript -l JavaScript "$JXA_FILE" "$@"; }

assert_http_success() {
  local status="$1" response_file="$2" label="$3" detail
  case "$status" in 2??) return ;; esac
  detail="$(jxa error "$response_file" 2>/dev/null || true)"
  if [[ -n "$detail" ]]; then fail "$label failed: HTTP $status $detail"; fi
  fail "$label failed: HTTP $status"
}

HISTORY_SOURCES=()
add_history() { if [[ -e "$1" ]]; then HISTORY_SOURCES+=("$1"); fi; }
if [[ ${#HISTORY_OVERRIDES[@]} -gt 0 ]]; then
  for source in "${HISTORY_OVERRIDES[@]}"; do add_history "$source"; done
else
  for root in "$NORMAL_ROOT" "$THREEP_ROOT"; do
    for relative in 'IndexedDB' 'Local Storage' 'Session Storage' 'local-agent-mode-sessions' 'Partitions' 'WebStorage' 'databases' 'Service Worker' 'shared_proto_db'; do add_history "$root/$relative"; done
    add_history "$root/Network/Cookies"
    add_history "$root/Network/Cookies-journal"
    add_history "$root/Local State"
    add_history "$root/Preferences"
  done
  add_history "$HOME/.claude/projects"
fi

backup_path() {
  local source="$1" target="$2"
  /usr/bin/ditto "$source" "$target"
}

new_safety_backup() {
  local action_name="$1" destination stamp total_kb=0 required_kb available_kb probe index source name relative target
  info "$(msg backup)"
  stamp="$(date '+%Y%m%d-%H%M%S')-$$"
  destination="$BACKUP_ROOT/$stamp-$action_name"
  if [[ "$SKIP_HISTORY_BACKUP" -eq 1 ]]; then
    warn "$(msg backup_skipped)"
  elif [[ ${#HISTORY_SOURCES[@]} -eq 0 ]]; then
    info "$(msg no_history)"
  else
    for source in "${HISTORY_SOURCES[@]}"; do
      total_kb=$((total_kb + $(/usr/bin/du -sk "$source" | /usr/bin/awk '{print $1}')))
    done
  fi

  if [[ "$DRY_RUN" -eq 0 ]]; then
    probe="$BACKUP_ROOT"
    while [[ ! -e "$probe" && "$probe" != "/" ]]; do probe="$(dirname "$probe")"; done
    available_kb="$(/bin/df -Pk "$probe" | /usr/bin/awk 'NR == 2 {print $4}')"
    required_kb=$((total_kb + 65536))
    [[ "$available_kb" =~ ^[0-9]+$ ]] || fail 'Could not determine free space for the safety backup.'
    [[ "$available_kb" -ge "$required_kb" ]] || fail "Not enough free space for the safety backup (required about $((required_kb / 1024)) MiB, available $((available_kb / 1024)) MiB)."
    /bin/mkdir -p "$destination/config" "$destination/history"
    printf 'version\taction\tcreated_at\tkind\tsource\tbackup\n' >"$destination/manifest.tsv"
  fi

  index=0
  for source in "$NORMAL_CONFIG" "$THREEP_CONFIG" "$META_FILE" "$PROFILE_FILE" "$STATE_FILE"; do
    index=$((index + 1))
    if [[ -f "$source" ]]; then
      name="$(basename "$source")"
      relative="config/$(printf '%02d' "$index")-$name"
      if [[ "$DRY_RUN" -eq 0 ]]; then
        target="$destination/$relative"
        backup_path "$source" "$target"
        printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$SCRIPT_VERSION" "$action_name" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" config "$source" "$relative" >>"$destination/manifest.tsv"
      fi
    fi
  done

  if [[ "$SKIP_HISTORY_BACKUP" -eq 0 ]]; then
    index=0
    for source in "${HISTORY_SOURCES[@]}"; do
      index=$((index + 1))
      name="$(basename "$source" | /usr/bin/tr -c 'A-Za-z0-9._-' '_')"
      relative="history/$(printf '%02d' "$index")-$name"
      if [[ "$DRY_RUN" -eq 0 ]]; then
        target="$destination/$relative"
        backup_path "$source" "$target"
        printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$SCRIPT_VERSION" "$action_name" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" history "$source" "$relative" >>"$destination/manifest.tsv"
      fi
    done
  fi
  ok "Safety backup: $destination"
}

if [[ "$ACTION" == "setup-reserve" ]]; then ENDPOINT="https://direct.router-cheap.com"; fi
if [[ "$ACTION" == "restore" ]]; then
  status="$(jxa status "$NORMAL_CONFIG" "$THREEP_CONFIG" "$META_FILE" "$PROFILE_FILE" "$STATE_FILE" "$PROFILE_ID" "$PROFILE_NAME")"
  if [[ "$status" != "INSTALLED" ]]; then info "$(msg nothing)"; exit 0; fi
  new_safety_backup restore
  if [[ "$DRY_RUN" -eq 1 ]]; then info "$(msg dry_run)"; exit 0; fi
  info "$(msg restoring)"
  result="$(jxa restore "$NORMAL_CONFIG" "$THREEP_CONFIG" "$META_FILE" "$PROFILE_FILE" "$STATE_FILE" "$PROFILE_ID" "$PROFILE_NAME")"
  [[ "$result" == "OK" ]] || fail 'Claude Desktop profile restore did not complete.'
  warn "$(msg history_notice)"
  ok "$(msg restored)"
  exit 0
fi

if [[ -z "$API_KEY" && -n "${AIMARKET_SETUP_KEY:-}" ]]; then
  API_KEY="$AIMARKET_SETUP_KEY"
  unset AIMARKET_SETUP_KEY
  ok "$(msg setup_key)"
fi
if [[ -z "$API_KEY" && -t 0 ]]; then
  clipboard="$(/usr/bin/pbpaste 2>/dev/null | tr -d '\r\n\t ' || true)"
  if [[ "$clipboard" =~ ^sk-[A-Za-z0-9_-]{16,200}$ ]]; then
    printf '%s: %s...%s\n' "$(msg clipboard_key)" "${clipboard:0:6}" "${clipboard: -4}"
    printf '%s' "$(msg clipboard_prompt)"
    IFS= read -r -s API_KEY || API_KEY=""
    printf '\n'
    [[ -n "$API_KEY" ]] || API_KEY="$clipboard"
  fi
fi
API_KEY="$(printf '%s' "$API_KEY" | tr -d '\r\n\t ')"
while [[ "$API_KEY" != sk-* ]]; do
  if [[ -n "$API_KEY" ]]; then warn "$(msg invalid_key)"; fi
  [[ -t 0 ]] || fail "$(msg invalid_key)"
  printf '%s: ' "$(msg key)"
  IFS= read -r -s API_KEY
  printf '\n'
  API_KEY="$(printf '%s' "$API_KEY" | tr -d '\r\n\t ')"
done
printf '%s' "$API_KEY" >"$KEY_FILE"
chmod 600 "$KEY_FILE"

if [[ "$SKIP_ENDPOINT_TEST" -eq 1 ]]; then
  MODELS="$PREFERRED_MODELS"
else
  info "$(msg testing)"
  NETWORK_PHASE=1
  printf 'Authorization: Bearer %s\nanthropic-version: 2023-06-01\nAccept-Language: %s\nUser-Agent: aimarket-claude-desktop-setup/%s\nContent-Type: application/json\n' "$API_KEY" "$LANG_CODE" "$SCRIPT_VERSION" >"$HEADERS_FILE"
  chmod 600 "$HEADERS_FILE"
  HTTP_STATUS="$(/usr/bin/curl --silent --show-error --connect-timeout 15 --max-time 45 --header "@$HEADERS_FILE" "$ENDPOINT/v1/models" --output "$CATALOG_FILE" --write-out '%{http_code}')" || fail 'GET /v1/models failed: network error.'
  assert_http_success "$HTTP_STATUS" "$CATALOG_FILE" 'GET /v1/models'
  MODELS="$(jxa models "$CATALOG_FILE" "$PREFERRED_MODELS")"
  FIRST_MODEL="${MODELS%%,*}"
  printf '{"model":"%s","max_tokens":8,"messages":[{"role":"user","content":"Reply with OK."}]}' "$FIRST_MODEL" >"$BODY_FILE"
  HTTP_STATUS="$(/usr/bin/curl --silent --show-error --connect-timeout 15 --max-time 90 --header "@$HEADERS_FILE" --data-binary "@$BODY_FILE" "$ENDPOINT/v1/messages" --output "$RESPONSE_FILE" --write-out '%{http_code}')" || fail 'POST /v1/messages failed: network error.'
  assert_http_success "$HTTP_STATUS" "$RESPONSE_FILE" 'POST /v1/messages'
  NETWORK_PHASE=0
fi
ok "Claude Desktop models: ${MODELS//,/, }"
new_safety_backup setup
if [[ "$DRY_RUN" -eq 1 ]]; then info "$(msg dry_run)"; exit 0; fi

info "$(msg configuring)"
warn "$(msg plaintext)"
result="$(jxa setup "$NORMAL_CONFIG" "$THREEP_CONFIG" "$META_FILE" "$PROFILE_FILE" "$STATE_FILE" "$PROFILE_ID" "$PROFILE_NAME" "$KEY_FILE" "$ENDPOINT" "$MODELS" "$SCRIPT_VERSION")"
[[ "$result" == "OK" ]] || fail 'Claude Desktop profile setup did not complete.'
warn "$(msg history_notice)"
ok "$(msg done)"
