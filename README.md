# Бистро «Для двоих»

Шуточное приложение для пары. На холодильнике висит QR «Что на ужин?». Партнёр
сканирует его камерой, открывается страница «Шеф интересуется: десерт сегодня
подавать?». Ответ уходит в Home Assistant, и HA присылает пуш второму партнёру.

```
QR на холодильнике ──► index.html (GitHub Pages) ──POST JSON──► HA webhook ──► notify.mobile_app_<телефон второго>
       │                        │
       └ #ha=…&wh=…&from=…      └ читает фрагмент, сохраняет в localStorage, убирает из адресной строки
```

* Страница: один `index.html` + `config.js` (тексты) + `manifest.webmanifest` (PWA). Без сборки и фреймворков.
* Секретов в репозитории нет. Адрес HA и `webhook_id` приходят из QR во **фрагменте** URL (`#…`),
  а фрагмент браузер на сервер GitHub не отправляет.

```
index.html                 все экраны и логика
config.js                  тексты, варианты ответов, вопросы дня — правьте здесь
manifest.webmanifest, icons/, fonts/   PWA и шрифты (Yeseva One, Manrope — OFL)
ha/packages/dessert_bistro.yaml        пакет Home Assistant
tools/make_qr.py           генерация QR (PNG + A6 PDF)
tools/mock_ha.py           мок вебхука HA для локальной проверки
```

## 1. Публикация на GitHub Pages

1. Слейте ветку с кодом в `main`.
2. **Settings → Pages → Build and deployment → Source: Deploy from a branch**, ветка `main`, папка `/ (root)` → Save.
3. Через минуту страница будет на `https://koshg28.github.io/funnyqr/`.

> Репозиторий сейчас **приватный**. GitHub Pages для приватных репозиториев работает только на платных
> планах (Pro / Team / Enterprise). На бесплатном плане сделайте репозиторий публичным: секретов в нём нет.
> У приватного репо на Pro страница всё равно открыта всем, кто знает адрес: это нормально, ключи лежат только в QR.

Файл `.nojekyll` отключает обработку Jekyll, так что всё отдаётся как есть.

## 2. Home Assistant (свой сервер)

### Пакет

1. Скопируйте `ha/packages/dessert_bistro.yaml` в `<config>/packages/`.
2. В `configuration.yaml`:
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
   Если у вас нет `default_config:`, добавьте ещё строку `webhook:`.
3. В `secrets.yaml` добавьте длинный случайный id:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   ```yaml
   bistro_webhook_id: "сюда-строку-из-команды"
   ```
4. В начале пакета, в блоке **НАСТРОЙКИ**, впишите имена и сервисы уведомлений:
   ```yaml
   partners:
     "Аня": notify.mobile_app_pixel_7     # имя ровно как в QR (--names)
     "Макс": notify.mobile_app_galaxy_s23
   ```
   Точные имена сервисов видны в *Инструменты разработчика → Действия* (`notify.mobile_app_…`).
5. Перезапустите HA (новые хелперы и пакет подхватываются только перезапуском).

Что создаёт пакет:

| Сущность | Зачем |
|---|---|
| `automation` «Бистро: ответ со страницы» | webhook-триггер, `allowed_methods: [POST]`, `local_only: false`; проверяет JSON, отбрасывает дубли, шлёт пуш |
| `script.bistro_notify` | отправка пуша с учётом дискретного режима; здесь же все настройки |
| `input_boolean.bistro_discreet` | **дискретный режим**: на экране «Бистро / Ваш заказ принят» и кнопка «Показать детали» |
| `input_datetime.bistro_reminder_at`, `input_boolean.bistro_reminder_pending`, `input_text.bistro_reminder_to` | «Перенесём на завтра»: напоминание второму партнёру в 21:00. Хранится в хелперах, без `delay`, поэтому переживает перезапуск. Если HA был выключен в 21:00, напомнит после старта (в пределах 3 часов) |
| `counter.bistro_yes / maybe / no / postponed` | счётчики для статистики |
| `sensor.bistro_last_order` | последний заказ с атрибутами (кто, кому, детали). Его история в Recorder и есть лог ответов |
| закомментированная сцена | при «Да» приглушить свет и включить музыку; впишите свои `entity_id` вместо `ZAMENITE_…` |

Дискретный режим включается переключателем `input_boolean.bistro_discreet` в интерфейсе HA.

### Внешний доступ

Телефон партнёра обычно в мобильной сети, поэтому HA должен открываться снаружи **по https**.
Страница на `https://…github.io` не может обращаться к `http://`: браузер это блокирует (mixed content).

Для своего сервера: домен + reverse proxy с сертификатом (nginx / Caddy / Nginx Proxy Manager / Cloudflare Tunnel).
Проверьте, что прокси:
* пропускает методы `POST` **и `OPTIONS`** на `/api/webhook/…`;
* не закрывает `/api/webhook/` своей авторизацией (Authelia, basic auth и т. п.): вебхук должен быть доступен без логина;
* прописан в HA: `http: use_x_forwarded_for: true` и `trusted_proxies: [<ip прокси>]`.

(Вместо своего домена подойдёт и Nabu Casa: адрес вида `https://xxxx.ui.nabu.casa`.)

### CORS: что выбрано и почему

Страница (`koshg28.github.io`) и HA живут на разных доменах. Это проверено по исходникам HA
(`homeassistant/components/webhook/__init__.py`, `http/cors.py`, ветка dev, 2026.x) и на живом HA 2026.2:

* `WebhookView` объявлен с `cors_allowed = True`, поэтому для `/api/webhook/*` HA сам разрешает CORS
  **с любого Origin**, включая preflight-запрос `OPTIONS` с заголовком `Content-Type`.
* **`http: cors_allowed_origins` в configuration.yaml НЕ нужен.** Он влияет только на остальные API, а не на вебхуки.
* Поэтому страница шлёт обычный `fetch` с `Content-Type: application/json`, и тело попадает в `trigger.json`.
  Трюк с «простым запросом без preflight» (form-urlencoded, `mode: no-cors`) не понадобился: при нём
  страница не видела бы ответ и не могла бы показать ошибку.

Как страница показывает ошибки:

| Ситуация | Что видит пользователь |
|---|---|
| нет интернета | «Нет интернета…» + «Повторить» |
| HA выключен / DNS / прокси не отвечает / CORS отрезан прокси | «Не достучались до Home Assistant…» + «Повторить» |
| нет ответа 12 с | «Кухня долго не отвечает…» + «Повторить» |
| 404 / 405 / 5xx | текст с кодом и подсказкой |
| **неверный `webhook_id`** | HA **намеренно отвечает 200** на любой несуществующий вебхук, чтобы нельзя было перебирать id. Страница этого различить не может. Поэтому на экране «Служебный вход» есть кнопка **«Проверить связь»**: она шлёт `answer: ping`, и HA присылает пуш «Связь с кухней есть» *самому отправителю*. Нет пуша — неверный id или имя |

«Повторить» отправляет тот же `id` заказа, и HA не пришлёт партнёру дубль, если первый запрос всё-таки дошёл.

### Проверка вебхука через curl

```bash
HA=https://ha.example.ru
WH=ваш_webhook_id

# preflight, как делает браузер: ждём 200 и Access-Control-Allow-Origin
curl -i -X OPTIONS "$HA/api/webhook/$WH" \
  -H "Origin: https://koshg28.github.io" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type"

# проверка связи — пуш придёт Ане
curl -i -X POST "$HA/api/webhook/$WH" -H "Content-Type: application/json" \
  -d '{"v":1,"id":"otest1","from":"Аня","answer":"ping","details":{}}'

# настоящий заказ — пуш придёт Максу
curl -i -X POST "$HA/api/webhook/$WH" -H "Content-Type: application/json" \
  -d '{"v":1,"id":"otest2","from":"Аня","answer":"yes","details":{"time":"Ближе к ночи","setting":["Свечи"],"dish":"Удиви меня","spice":"🌶🌶 Средне","spice_level":2},"ts":"2026-09-24T19:00:00Z"}'
```

Ответ всегда `200`, даже при неверном id. Смотрите, пришёл ли пуш, и загляните в *Настройки → Система → Журналы*:
отклонённые запросы пишутся туда с пометкой `bistro`.

Формат JSON:

```jsonc
{
  "v": 1, "id": "o3f9…", "from": "Аня", "answer": "yes" | "maybe" | "no" | "ping", "ts": "ISO-8601",
  "details": {
    // yes:   {"time": "...", "setting": ["..."], "dish": "...", "spice": "🌶🌶 Средне", "spice_level": 2}
    // maybe: {"helps": ["..."], "custom": "..."}
    // no:    {"option": "hug" | "series" | "tomorrow" | "talk", "label": "..."}
  }
}
```

## 3. QR-коды

```bash
pip install -r tools/requirements.txt   # или: pip install "qrcode[pil]"
python3 tools/make_qr.py --ha https://ha.example.ru --webhook "ваш_webhook_id" --names Аня Макс
```

Появится `qr/bistro-Аня.png`, `qr/bistro-Аня-A6.pdf` и то же для второго имени. Печатайте PDF в масштабе 100 %.
QR с именем Ани вешается для Ани: `from=Аня`, и уведомление уйдёт Максу.

Один QR на двоих: добавьте `--one`, и при первом открытии страница спросит «Кто ты?» и запомнит ответ.
Другие опции: `--page` (другой адрес страницы), `--no-label` (без имени на наклейке), `--out`.

Папка `qr/` в `.gitignore`: **в QR лежат адрес HA и webhook_id, не коммитьте и не выкладывайте их.**

На телефоне после первого скана: меню Chrome → «Добавить на главный экран». Ярлык открывает меню
без повторного сканирования, настройки хранятся в `localStorage`.

## 4. Локальная проверка без HA

```bash
python3 tools/mock_ha.py              # мок вебхука на :8123 (CORS как у HA)
python3 -m http.server 8000           # в корне репо
```

Откройте `http://localhost:8000/#ha=aHR0cDovL2xvY2FsaG9zdDo4MTIz&wh=test-webhook&from=Аня`
(`aHR0cDovL2xvY2FsaG9zdDo4MTIz` = base64 от `http://localhost:8123`). Ответы печатаются в консоли мока.
Ошибки можно проверить через `wh=fail-500`, `wh=method-405` и `wh=slow-hook` (таймаут).
Если открыть страницу без фрагмента, она покажет «Отсканируй QR с холодильника».

## 5. Как поменять тексты

Всё в `config.js`: вопрос, ответы, варианты подачи и сервировки, условия «может быть», варианты вечера,
вопросы дня. Если меняете время напоминания, поправьте его в двух местах: `reminderTime` в `config.js`
(текст на странице) и `reminder_time` в пакете HA (само напоминание).
