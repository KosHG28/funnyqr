# Бистро «Для двоих»

Шуточное приложение для пары: QR «Что на ужин?» на холодильнике → статическая страница
«десерт сегодня подавать?» → POST в webhook Home Assistant → пуш второму партнёру.

## Архитектура
- `index.html` — вся страница (экраны, логика, стили), без сборки и фреймворков. Хостинг: GitHub Pages.
- `config.js` — все тексты и варианты ответов (`window.BISTRO`). Тексты правятся только здесь.
- `manifest.webmanifest`, `icons/`, `fonts/` — PWA и локальные шрифты (без Google Fonts и прочих внешних запросов).
- Конфиг приходит из QR во фрагменте URL: `#ha=<base64url(url HA)>&wh=<webhook_id>&from=<имя>`
  (или `&names=А,Б` → экран «Кто ты?»). Страница сохраняет его в `localStorage` (`bistro.config.v1`)
  и сразу убирает фрагмент из адресной строки.
- JSON в HA: `{v, id, from, answer: yes|maybe|no|ping, details, ts}`. `id` нужен HA, чтобы отбросить повтор.
- `ha/packages/dessert_bistro.yaml` — пакет HA. Настройки (partners → notify-сервисы, время напоминания)
  лежат в `script.bistro_notify.variables` под YAML-якорем `&bistro_settings`, автоматизации берут их через `*bistro_settings`.
- CORS: у вебхуков HA `cors_allowed = True` (любой Origin), поэтому `cors_allowed_origins` не нужен.
  На неизвестный webhook HA отвечает 200, и проверить id можно только через `answer: ping`.

## Правило: никаких секретов в репозитории
- Никогда не коммитить адрес HA, webhook_id, токены, реальные имена notify-сервисов и сгенерированные QR (`qr/`).
- В пакете HA webhook_id берётся только через `!secret bistro_webhook_id`.
- В примерах использовать плейсхолдеры (`ha.example.ru`, `notify.mobile_app_anya_phone`).

## Проверка
- Страница: `python3 tools/mock_ha.py` + `python3 -m http.server 8000`, затем открыть URL с фрагментом (см. README).
- YAML: `hass --script check_config -c <config>` на копии конфига с пакетом.
