# Бистро «Для двоих»

Шуточное приложение для пары: QR «Что на ужин?» на холодильнике → девушка открывает статическую страницу
«десерт сегодня подавать?» → страница публикует сообщение в self-hosted ntfy → пуш парню в приложение ntfy.

## Архитектура
- `index.html` — вся страница (экраны, логика, стили), без сборки и фреймворков. Хостинг: GitHub Pages.
- `config.js` — все тексты, варианты ответов и тексты уведомлений (`window.BISTRO`). Тексты правятся только здесь.
- `manifest.webmanifest`, `icons/`, `fonts/` — PWA и локальные шрифты (без Google Fonts и прочих внешних запросов).
- Конфиг приходит из QR во фрагменте URL: `#ns=<base64url(адрес ntfy)>&t=<канал>&k=<токен>[&d=1]`.
  Страница сохраняет его в `localStorage` (`bistro.ntfy.v1`) и сразу убирает фрагмент из адресной строки.
- `#r=<base64url(JSON чека)>` — ссылка из уведомления: показывает чек только для просмотра.
- Публикация: «простой» `POST <server>/?auth=<base64url("Bearer tk")>` с JSON без заголовков (без CORS-preflight).
  Напоминание — отложенное сообщение (`delay`, `sequence_id: bistro-reminder`), отмена — `DELETE /<topic>/bistro-reminder`.
- `deploy/ntfy/` — docker-compose (порт 7090) и `server.yml` (deny-all, cache-file, upstream ntfy.sh).
- `tools/make_qr.py` — QR-наклейка PNG + A6 PDF.

## Правило: никаких секретов в репозитории
- Никогда не коммитить адрес реального сервера, имя канала, токены, пароли и сгенерированные QR (`qr/`).
- В примерах использовать плейсхолдеры (`ntfy.example.ru`, `bistro_…`, `tk_…`).

## Проверка
- Локально: `docker run -p 7090:80 binwiederhier/ntfy serve` + `python3 -m http.server 8000`,
  затем `http://localhost:8000/#ns=aHR0cDovL2xvY2FsaG9zdDo3MDkw&t=test` (см. README).
