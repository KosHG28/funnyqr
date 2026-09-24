#!/usr/bin/env python3
"""Генератор QR-наклейки «Что на ужин?» для холодильника.

Делает PNG и PDF формата A6 (105×148 мм, 300 dpi). Адрес сервера ntfy,
канал и токен зашиваются во фрагмент ссылки (#…), который браузер не
отправляет на сервер GitHub.

ВНИМАНИЕ: готовый QR содержит токен. Не коммитьте папку qr/ (она в .gitignore).

Пример:
  python3 tools/make_qr.py --server https://ntfy.example.ru --topic bistro --token tk_xxxxxxxx

Зависимости: pip install -r tools/requirements.txt
"""
import argparse
import base64
import re
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit

try:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_M
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit('Нужны библиотеки: pip install "qrcode[pil]"')

ROOT = Path(__file__).resolve().parent.parent
FONT_TITLE = ROOT / "fonts" / "YesevaOne-Regular.ttf"
FONT_BODY = ROOT / "fonts" / "Manrope-Variable.ttf"

DEFAULT_PAGE = "https://koshg28.github.io/funnyqr/"

DPI = 300
A6_MM = (105, 148)
PAPER = "#FBF0EB"
INK = "#3A0F1E"
INK_SOFT = "#7A4A57"
ROSE = "#C23C63"


def mm(v):
    return round(v / 25.4 * DPI)


def b64url(s):
    return base64.urlsafe_b64encode(s.encode("utf-8")).decode("ascii").rstrip("=")


def build_url(page, server, topic, token=None, discreet=False):
    frag = f"ns={b64url(server)}&t={quote(topic, safe='')}"
    if token:
        frag += f"&k={quote(token, safe='')}"
    if discreet:
        frag += "&d=1"
    return f"{page}#{frag}"


def font(path, size, weight=None):
    try:
        f = ImageFont.truetype(str(path), size)
    except OSError:
        sys.exit(f"Не найден шрифт {path}")
    if weight:
        try:
            f.set_variation_by_axes([weight])
        except (OSError, ValueError):
            pass
    return f


def centered(draw, width, y, text, fnt, fill):
    w = draw.textlength(text, font=fnt)
    draw.text(((width - w) / 2, y), text, font=fnt, fill=fill)


def make_card(url, label):
    W, H = mm(A6_MM[0]), mm(A6_MM[1])
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    # «магнит» сверху
    r = mm(5)
    cx = W // 2
    d.ellipse((cx - r, mm(9) - r, cx + r, mm(9) + r), fill=ROSE)

    centered(d, W, mm(18), "Что на ужин?", font(FONT_TITLE, mm(11)), INK)

    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, border=0)
    qr.add_data(url)
    qr.make(fit=True)
    modules = qr.modules_count
    target = mm(74)
    box = max(1, target // modules)
    q = qr.make_image(fill_color=INK, back_color="white").get_image().convert("RGB")
    q = q.resize((modules * box, modules * box), Image.NEAREST)
    pad = mm(5)
    frame = Image.new("RGB", (q.width + 2 * pad, q.height + 2 * pad), "white")
    frame.paste(q, (pad, pad))
    fx = (W - frame.width) // 2
    fy = mm(38)
    img.paste(frame, (fx, fy))

    y = fy + frame.height + mm(7)
    centered(d, W, y, "Наведи камеру телефона", font(FONT_BODY, mm(4.2), 500), INK_SOFT)
    if label:
        centered(d, W, H - mm(12), label, font(FONT_BODY, mm(3.2), 600), INK_SOFT)
    # тонкая рамка для вырезания
    d.rectangle((mm(2), mm(2), W - mm(2), H - mm(2)), outline="#E3C8C0", width=2)
    return img, qr.version


def slug(s):
    s = re.sub(r"[^\w\-]+", "_", s, flags=re.UNICODE).strip("_")
    return s or "qr"


def main():
    ap = argparse.ArgumentParser(description="QR-наклейка «Что на ужин?» (PNG + A6 PDF)")
    ap.add_argument("--server", required=True, help="внешний адрес ntfy, https://…")
    ap.add_argument("--topic", required=True, help="канал ntfy, на который подписан телефон партнёра")
    ap.add_argument("--token", default="", help="токен с правом записи в канал (tk_…)")
    ap.add_argument("--discreet", action="store_true", help="дискретный режим: в уведомлении только «Ваш заказ принят»")
    ap.add_argument("--page", default=DEFAULT_PAGE, help=f"адрес страницы (по умолчанию {DEFAULT_PAGE})")
    ap.add_argument("--out", default=str(ROOT / "qr"), help="куда сохранить (по умолчанию qr/)")
    ap.add_argument("--label", default="", help="подпись мелким шрифтом внизу наклейки")
    a = ap.parse_args()

    server = a.server.strip().rstrip("/")
    parts = urlsplit(server)
    if parts.scheme not in ("https", "http") or not parts.netloc:
        sys.exit("--server должен быть полным адресом, например https://ntfy.example.ru")
    if parts.scheme == "http":
        print("⚠  Адрес на http:// — со страницы на GitHub Pages (https) браузер его заблокирует.", file=sys.stderr)
    if not re.fullmatch(r"[-_A-Za-z0-9]{1,64}", a.topic):
        sys.exit("--topic: 1–64 символа из A–Z a–z 0–9 _ -")
    if a.token and not re.fullmatch(r"[A-Za-z0-9_\-.]{8,200}", a.token):
        sys.exit("--token выглядит неправильно (ожидается tk_…)")
    page = a.page if a.page.endswith("/") or a.page.endswith(".html") else a.page + "/"

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    url = build_url(page, server, a.topic, a.token, a.discreet)
    img, version = make_card(url, a.label or None)
    base = out / "bistro"
    img.save(base.with_suffix(".png"), dpi=(DPI, DPI))
    img.save(f"{base}-A6.pdf", "PDF", resolution=DPI)
    print(f"✓ {base}.png, {base}-A6.pdf  (QR версии {version}, {len(url)} символов)")
    print(f"  ссылка: {url}")
    print("\nВ этих файлах адрес сервера и токен — не публикуйте их и не коммитьте.")


if __name__ == "__main__":
    main()
