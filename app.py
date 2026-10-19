#!/usr/bin/env python3
"""Local Rust loot viewer. Python 3.10+, no third-party dependencies."""
import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from loot import CRATES, SOURCE, parse_loot

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / '.cache'
LOCK = threading.Lock()
MAX_BYTES = 5 * 1024 * 1024


def load_crate(crate, refresh=False):
    path = CACHE / f'{crate}.json'
    with LOCK:
        cached = json.loads(path.read_text()) if path.exists() else None
        if cached and not refresh:
            return {**cached, 'cached': True}
        try:
            request = Request(f'{SOURCE}/entity/{crate}', headers={'User-Agent': 'RustLootViewer/1.0'})
            with urlopen(request, timeout=20) as response:
                raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError('Страница слишком большая.')
            data = make_data(crate, raw.decode('utf-8'), 'website')
            save_data(crate, data)
            return data
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            if cached:
                return {**cached, 'cached': True, 'warning': f'Обновление не удалось: {exc}'}
            raise ValueError('Не удалось загрузить реальные данные. Проверьте доступ к wiki.rustclash.com или импортируйте HTML-страницу таблицы. ' + str(exc)) from exc


def make_data(crate, html, origin):
    return {'crate': crate, 'items': parse_loot(html), 'source': f'{SOURCE}/entity/{crate}',
            'updated': datetime.now(timezone.utc).isoformat(), 'origin': origin, 'cached': False}


def save_data(crate, data):
    CACHE.mkdir(exist_ok=True)
    temporary = CACHE / f'{crate}.tmp'
    temporary.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    temporary.replace(CACHE / f'{crate}.json')


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body, mime='application/json; charset=utf-8'):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/crates':
            return self.reply(200, CRATES)
        if parsed.path == '/api/loot':
            query = parse_qs(parsed.query)
            crate = query.get('crate', [''])[0]
            if crate not in CRATES:
                return self.reply(400, {'error': 'Неизвестный ящик'})
            try:
                return self.reply(200, load_crate(crate, query.get('refresh') == ['1']))
            except ValueError as exc:
                return self.reply(502, {'error': str(exc)})
        files = {'/': ('index.html', 'text/html; charset=utf-8'),
                 '/style.css': ('style.css', 'text/css; charset=utf-8'),
                 '/main.js': ('main.js', 'text/javascript; charset=utf-8')}
        if parsed.path in files:
            name, mime = files[parsed.path]
            return self.reply(200, (ROOT / 'static' / name).read_bytes(), mime)
        self.reply(404, {'error': 'Не найдено'})

    def do_POST(self):
        parsed = urlparse(self.path)
        crate = parse_qs(parsed.query).get('crate', [''])[0]
        if parsed.path != '/api/import' or crate not in CRATES:
            return self.reply(400, {'error': 'Неизвестный ящик'})
        # Browser requests must originate from this local application.
        if self.headers.get('Origin') not in (None, f"http://{self.headers.get('Host')}"):
            return self.reply(403, {'error': 'Недопустимый источник запроса'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_BYTES:
                return self.reply(413, {'error': 'Допустим HTML-файл до 5 МБ'})
            data = make_data(crate, self.rfile.read(length).decode('utf-8-sig'), 'import')
            with LOCK:
                save_data(crate, data)
            self.reply(200, data)
        except (ValueError, UnicodeError) as exc:
            self.reply(400, {'error': str(exc)})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Rust Loot: http://127.0.0.1:{args.port} — Ctrl+C для выхода', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
