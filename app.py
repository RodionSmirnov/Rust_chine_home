#!/usr/bin/env python3
"""Rust loot catalogue: Python 3.10+, offline, no dependencies."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse, unquote
from catalog import Catalog

ROOT = Path(__file__).resolve().parent
CATALOG = Catalog()


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body, mime='application/json; charset=utf-8'):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/crates':
            return self.reply(200, CATALOG.containers())
        if parsed.path == '/api/loot':
            key = parse_qs(parsed.query).get('crate', ['all'])[0]
            if key not in CATALOG.containers():
                return self.reply(400, {'error': 'Неизвестный контейнер'})
            return self.reply(200, CATALOG.response(key))
        if parsed.path.startswith('/icons/'):
            name = unquote(parsed.path.removeprefix('/icons/'))
            if '/' in name or '\\' in name or not name.endswith('.webp'):
                return self.reply(404, {'error': 'Изображение не найдено'})
            icon = ROOT / 'data' / 'icons' / name
            if not icon.is_file():
                return self.reply(404, {'error': 'Изображение не найдено'})
            return self.reply(200, icon.read_bytes(), 'image/webp')
        files = {'/': ('index.html', 'text/html; charset=utf-8'),
                 '/style.css': ('style.css', 'text/css; charset=utf-8'),
                 '/main.js': ('main.js', 'text/javascript; charset=utf-8')}
        if parsed.path in files:
            name, mime = files[parsed.path]
            return self.reply(200, (ROOT / 'static' / name).read_bytes(), mime)
        self.reply(404, {'error': 'Не найдено'})


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
