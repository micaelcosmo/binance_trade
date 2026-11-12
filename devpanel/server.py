"""Servidor do painel de desenvolvimento (stdlib, só leitura).

    .venv/Scripts/python devpanel/server.py [--port 5055]   →  http://127.0.0.1:5055

Rotas fixas, só GET/HEAD: /, /index.html, /estado.json (montado pelo coletor, cache de 2 s),
/arch.yaml (o de .spec/), /papel (view do modo papel) e /papel.json (diário de data/paper/). Qualquer outro caminho → 404; outros métodos → 405.
X-Painel-Versao = mtime do index.html: abas abertas recarregam sozinhas quando a página muda.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coletor  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PAGINA = os.path.join(HERE, "index.html")
PAGINA_PAPEL = os.path.join(HERE, "papel.html")
ARCH = os.path.join(coletor.SPEC, "arch.yaml")
CACHE_S = 2.0

_cache = {"t": 0.0, "corpo": b""}
_trava = threading.Lock()


def estado_json() -> bytes:
    with _trava:
        if time.time() - _cache["t"] > CACHE_S:
            proc = {"servidor": {"pid": os.getpid(), "vivo": True}}
            _cache["corpo"] = json.dumps(coletor.coletar(proc), ensure_ascii=False).encode("utf-8")
            _cache["t"] = time.time()
        return _cache["corpo"]


class Handler(BaseHTTPRequestHandler):
    server_version = "painel-dev"

    def _enviar(self, corpo: bytes, tipo: str, so_cabecalho: bool = False, pagina: str = PAGINA):
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Painel-Versao", str(int(os.path.getmtime(pagina))))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        if not so_cabecalho:
            self.wfile.write(corpo)

    def _rota(self, so_cabecalho: bool):
        caminho = self.path.split("?", 1)[0]
        if "%" in caminho or "\\" in caminho:
            return self.send_error(404)
        try:
            if caminho in ("/", "/index.html"):
                with open(PAGINA, "rb") as f:
                    return self._enviar(f.read(), "text/html; charset=utf-8", so_cabecalho)
            if caminho == "/estado.json":
                return self._enviar(estado_json(), "application/json; charset=utf-8", so_cabecalho)
            if caminho in ("/papel", "/papel.html"):
                with open(PAGINA_PAPEL, "rb") as f:
                    return self._enviar(f.read(), "text/html; charset=utf-8", so_cabecalho, PAGINA_PAPEL)
            if caminho == "/papel.json":
                corpo = json.dumps(coletor.papel_completo(), ensure_ascii=False).encode("utf-8")
                return self._enviar(corpo, "application/json; charset=utf-8", so_cabecalho, PAGINA_PAPEL)
            if caminho == "/arch.yaml":
                with open(ARCH, "rb") as f:
                    return self._enviar(f.read(), "text/plain; charset=utf-8", so_cabecalho)
        except OSError:
            return self.send_error(503)
        self.send_error(404)

    def do_GET(self):
        self._rota(False)

    def do_HEAD(self):
        self._rota(True)

    def _nao_permitido(self):
        self.send_response(405)
        self.send_header("Allow", "GET, HEAD")
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_POST = do_PUT = do_DELETE = do_PATCH = _nao_permitido

    def log_message(self, *args):  # silencioso: o poll de 3 s encheria o log
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5055)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"Painel de dev em http://{a.host}:{a.port}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
