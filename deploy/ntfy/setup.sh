#!/usr/bin/env bash
# Один раз генерирует .env для docker-compose: канал, токен для QR, хеши паролей.
# Нужен только Docker. Запуск: ./setup.sh   (повторно: ./setup.sh --force)
set -euo pipefail
cd "$(dirname "$0")"

IMAGE=binwiederhier/ntfy:v2.25.0
ntfy() {  # ntfy CLI из того же образа (или локальный бинарник через NTFY_BIN — для тестов)
  if [ -n "${NTFY_BIN:-}" ]; then "$NTFY_BIN" "$@"; else docker run --rm -i "$IMAGE" "$@"; fi
}
rand() { LC_ALL=C tr -dc 'a-z0-9' </dev/urandom | head -c "$1" || true; }
hash_pw() { printf '%s\n%s\n' "$1" "$1" | ntfy user hash 2>/dev/null | grep -oE '\$2[aby]\$[0-9]+\$[./A-Za-z0-9]{53}'; }

if [ -f .env ] && [ "${1:-}" != "--force" ]; then
  echo ".env уже есть. Чтобы создать заново (новый канал и токен → новый QR): ./setup.sh --force"
  exit 1
fi

echo "Бистро «Для двоих» — настройка сервера уведомлений"
read -rp "Внешний https-адрес ntfy (например https://ntfy.example.ru): " BASE_URL
BASE_URL="${BASE_URL%/}"
case "$BASE_URL" in https://*) ;; http://*) echo "⚠  http:// не заработает со страницы на GitHub Pages — нужен https." ;; *) echo "Адрес должен начинаться с https://"; exit 1 ;; esac
read -rp "Логин для твоего телефона [paren]: " USER_NAME; USER_NAME="${USER_NAME:-paren}"
while true; do
  read -rsp "Пароль для входа в приложении ntfy: " PW; echo
  read -rsp "Ещё раз: " PW2; echo
  [ -n "$PW" ] && [ "$PW" = "$PW2" ] && break
  echo "Пароли пустые или не совпадают, ещё раз."
done
read -rp "Дискретный режим по умолчанию (в пуше только «Ваш заказ принят»)? [y/N]: " DISC
case "$DISC" in y|Y|д|Д) DISC=1 ;; *) DISC= ;; esac

echo "Генерирую канал, токен и хеши…"
TOPIC="bistro_$(rand 12)"
TOKEN="$(ntfy token generate | tr -d '[:space:]')"
USER_HASH="$(hash_pw "$PW")"
PAGE_HASH="$(hash_pw "$(rand 32)")"   # пароль страницы не нужен никому — только токен
[ -n "$USER_HASH" ] && [ -n "$PAGE_HASH" ] && [[ "$TOKEN" == tk_* ]] || { echo "Не удалось сгенерировать секреты"; exit 1; }

umask 077
cat > .env <<ENV
# Создано ./setup.sh $(date '+%Y-%m-%d %H:%M'). Секреты — не коммитить и не публиковать.
NTFY_BASE_URL='$BASE_URL'
NTFY_PORT=7090
TZ=Europe/Moscow
BISTRO_TOPIC='$TOPIC'
BISTRO_USER='$USER_NAME'
BISTRO_USER_HASH='$USER_HASH'
BISTRO_PAGE_HASH='$PAGE_HASH'
BISTRO_TOKEN='$TOKEN'
BISTRO_DISCREET=$DISC
ENV

cat <<MSG

Готово, настройки в .env

  Сервер:  $BASE_URL   (reverse proxy → http://<этот сервер>:7090)
  Канал:   $TOPIC
  Логин:   $USER_NAME   (пароль — который ввели)

Дальше:
  1. docker compose up -d
  2. docker compose run --rm qr          → ../../qr/bistro-A6.pdf — распечатать
  3. Телефон: ntfy → «+» → Use another server: $BASE_URL
     канал $TOPIC, войти как $USER_NAME
MSG
