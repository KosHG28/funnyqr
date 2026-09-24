# Бистро «Для двоих»

Шуточное приложение для пары. На холодильнике висит QR «Что на ужин?».

- **Девушка** сканирует QR камерой телефона. Открывается страница «Шеф интересуется: десерт сегодня подавать?»,
  она выбирает ответ и получает чек «Заказ принят». Ничего ставить не нужно.
- **Парню** приходит пуш в приложение **ntfy**, например «🔥 Десерт сегодня подаётся. Ближе к ночи · Массаж · 🌶🌶🌶».
  Нажатие на пуш открывает тот же чек.

```
QR на холодильнике ──► страница (GitHub Pages) ──POST──► ntfy на вашем сервере (Docker, порт 7090) ──► приложение ntfy у парня
     #ns=…&t=…&k=…            │
                              └ читает фрагмент, сохраняет в localStorage, убирает из адресной строки
```

* Страница: `index.html` + `config.js` (тексты) + `manifest.webmanifest` (можно добавить на главный экран).
  Без сборки и фреймворков, хостинг — GitHub Pages: https://koshg28.github.io/funnyqr/
* Секретов в репозитории нет. Адрес сервера, канал и токен приходят из QR во **фрагменте** URL (`#…`),
  а фрагмент браузер на сервер GitHub не отправляет.
* «Перенесём на завтра» — отложенное сообщение ntfy: сервер сам пришлёт напоминание завтра в 21:00.
  Переживает перезапуск контейнера. Если девушка потом ответит иначе, напоминание отменяется.
* Дискретный режим: в пуше только «Бистро / Ваш заказ принят», подробности — по нажатию.

```
index.html, config.js, manifest.webmanifest, icons/, fonts/   страница
deploy/ntfy/docker-compose.yml, server.yml                    сервер уведомлений
tools/make_qr.py                                              генерация QR (PNG + A6 PDF)
docs/mockup.html                                              исходный макет
```

> Первая версия работала через Home Assistant. Она осталась в истории git (коммит `ece37da`), если когда-нибудь понадобится.

## 1. Сервер ntfy (домашний сервер с Docker)

Отдельный контейнер на порту **7090**, больше ничего не трогает.

```bash
mkdir -p ~/ntfy && cd ~/ntfy
# скопируйте сюда deploy/ntfy/docker-compose.yml и deploy/ntfy/server.yml
nano server.yml          # base-url: "https://ntfy.ваш-домен"
docker compose up -d
curl http://localhost:7090/v1/health      # {"healthy":true}
```

### Пользователи, канал и токен

Сервер закрыт от посторонних (`auth-default-access: deny-all`). Нужны два пользователя:
парень, который только читает, и «страница», которая только пишет.

```bash
TOPIC=bistro_$(openssl rand -hex 6)      # секретное имя канала, запишите его
echo $TOPIC

docker compose exec ntfy ntfy user add paren          # спросит пароль — им вы войдёте в приложении
docker compose exec ntfy ntfy user add bistro-page    # пароль любой, он не понадобится
docker compose exec ntfy ntfy access paren       $TOPIC read-only
docker compose exec ntfy ntfy access bistro-page $TOPIC write-only
docker compose exec ntfy ntfy token add bistro-page   # → tk_…  этот токен пойдёт в QR
```

Токен в QR может только **писать** в этот канал: прочитать им чужие сообщения или писать в другие каналы нельзя.
Если QR потеряется — `ntfy token remove bistro-page tk_…`, новый токен и новый QR.

### Внешний доступ по https

Телефоны обычно в мобильной сети, а страница на `https://…github.io` может обращаться только к `https://`.
Нужен адрес вида `https://ntfy.ваш-домен`, который ведёт на `http://<сервер>:7090`.
Подойдёт то, что у вас уже есть для других сервисов:

* **Nginx Proxy Manager**: новый Proxy Host → `ntfy.ваш-домен` → `http://<ip-сервера>:7090`,
  включить **Websockets Support** и SSL (Let's Encrypt).
* **Caddy**: `ntfy.ваш-домен { reverse_proxy <ip-сервера>:7090 }`.
* **Cloudflare Tunnel**: public hostname `ntfy.ваш-домен` → `http://<ip-сервера>:7090`.

Приложение держит долгое соединение с сервером, поэтому прокси не должен обрывать его через 60 с
(в голом nginx: `proxy_buffering off; proxy_read_timeout 3m;` и заголовки `Upgrade`/`Connection` для WebSocket).

`upstream-base-url: https://ntfy.sh` в `server.yml` нужен для мгновенной доставки на Android без лишнего расхода батареи:
через ntfy.sh уходит только сигнал «проверь сервер», тексты остаются у вас.

### Проверка через curl

```bash
curl -H "Authorization: Bearer tk_…" \
  -d '{"topic":"bistro_…","title":"🔔 Проверка","message":"Если видишь это — всё работает"}' \
  https://ntfy.ваш-домен/
```

Ответ `200` с JSON — сообщение принято. `401` — неверный токен, `403` — у токена нет прав на этот канал.

## 2. Телефон парня

1. Google Play → **ntfy**.
2. «+» → включить **Use another server** → `https://ntfy.ваш-домен`, канал — ваш `$TOPIC`.
3. Войти пользователем `paren` с паролем из шага выше (приложение спросит само или через *Settings → Users*).
4. В настройках Android можно скрыть содержимое уведомлений ntfy на экране блокировки.

## 3. QR на холодильник

```bash
pip install -r tools/requirements.txt
python3 tools/make_qr.py --server https://ntfy.ваш-домен --topic bistro_… --token tk_…
# дискретный режим по умолчанию: добавьте --discreet
```

Появятся `qr/bistro.png` и `qr/bistro-A6.pdf`. Печатайте PDF в масштабе 100 %.
**В QR лежат адрес сервера и токен — не коммитьте и не выкладывайте папку `qr/`** (она в `.gitignore`).

После первого скана: меню браузера → «Добавить на главный экран». Ярлык открывает меню без повторного сканирования.
На экране «Служебный вход» (внизу меню) есть кнопка **«Проверить связь»** — парню придёт «🔔 Связь с кухней есть» —
и переключатель дискретного режима.

## 4. Как это устроено (для отладки)

Страница публикует «простым» запросом `POST https://ntfy…/?auth=<base64url("Bearer tk_…")>` с JSON в теле:

```json
{"topic":"bistro_…","title":"🔥 Десерт сегодня подаётся","message":"…","priority":4,
 "click":"https://koshg28.github.io/funnyqr/#r=<чек>","actions":[{"action":"view","label":"Открыть чек","url":"…"}],
 "sequence_id":"o…"}
```

* Токен в параметре `auth`, а не в заголовке, и без `Content-Type`: браузеру не нужен CORS-preflight,
  и неважно, как конкретный браузер относится к заголовку `Authorization`. ntfy отвечает `Access-Control-Allow-Origin: *`.
* Напоминание: второе сообщение с `"delay": "<unix-время завтра 21:00>"` и `"sequence_id": "bistro-reminder"`.
  Повторный перенос его заменяет, другой ответ отменяет (`DELETE /<канал>/bistro-reminder`). Нужен ntfy ≥ 2.16.
* «Повторить» после ошибки шлёт тот же `sequence_id`, и приложение заменит уведомление, а не продублирует.
* Ошибки на странице: нет интернета, сервер недоступен, таймаут 12 с, 401/403 (токен), 404, 413, 429, 5xx.

## 5. Локальная проверка

```bash
docker run --rm -p 7090:80 binwiederhier/ntfy:v2.25.0 serve     # открытый ntfy без паролей
python3 -m http.server 8000                                     # в корне репо
```

Откройте `http://localhost:8000/#ns=aHR0cDovL2xvY2FsaG9zdDo3MDkw&t=test`
(`aHR0cDovL2xvY2FsaG9zdDo3MDkw` = base64 от `http://localhost:7090`), а сообщения смотрите в
`curl -s "http://localhost:7090/test/json?poll=1"`.

## 6. Как поменять тексты

Всё в `config.js`: вопрос, ответы, варианты, вопросы дня, тексты уведомлений (`notify`) и время напоминания (`reminderTime`).
