#!/usr/bin/env python3
"""Мок вебхука Home Assistant для проверки страницы без настоящего HA.

Ведёт себя как HA: CORS для любого Origin (включая preflight), на любой
webhook_id отвечает 200. Специальные webhook_id для проверки ошибок:
  fail-500   → 500      slow-hook → ответ через 20 с (таймаут страницы)
  method-405 → 405      любой другой → 200

Запуск:
  python3 tools/mock_ha.py            # http://localhost:8123
  python3 -m http.server 8000         # в корне репо — сама страница
Открыть (ha = base64("http://localhost:8123")):
  http://localhost:8000/#ha=aHR0cDovL2xvY2FsaG9zdDo4MTIz&wh=test-webhook&from=Аня
"""
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8123


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        origin = self.headers.get("Origin")
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def _hook_id(self):
        prefix = "/api/webhook/"
        return self.path[len(prefix):] if self.path.startswith(prefix) else None

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.send_header("Access-Control-Allow-Methods", "POST")
        self.send_header("Access-Control-Allow-Headers", "CONTENT-TYPE")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        hook = self._hook_id()
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if hook is None:
            status = 404
        elif hook == "fail-500":
            status = 500
        elif hook == "method-405":
            status = 405
        else:
            status = 200
            if hook == "slow-hook":
                time.sleep(20)
        try:
            shown = json.dumps(json.loads(body), ensure_ascii=False)
        except ValueError:
            shown = body.decode("utf-8", "replace")
        print(f"[mock HA] {status} {hook}: {shown}", flush=True)
        self.send_response(status)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"mock HA on http://localhost:{PORT}  (Ctrl+C — выход)")
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()
