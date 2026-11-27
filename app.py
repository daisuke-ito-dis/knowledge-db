"""ナレッジ管理DB デモアプリ(標準ライブラリのみ: http.server + sqlite3)"""
import os
import signal
import sqlite3
import threading
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PORT = int(os.environ.get("PORT", "8080"))
DB_PATH = os.environ.get("DB_PATH", "/data/knowledge.db")
_lock = threading.Lock()


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            )"""
        )


CSS = """
body{font-family:sans-serif;max-width:900px;margin:0 auto;padding:1rem;background:#f5f5f5;color:#222}
header{background:#c00;color:#fff;padding:.8rem 1rem;border-radius:6px;margin-bottom:1rem}
header a{color:#fff;margin-right:1rem;text-decoration:none;font-weight:bold}
.card{background:#fff;padding:1rem;border-radius:6px;margin-bottom:.8rem;box-shadow:0 1px 3px #0002}
input,textarea{width:100%;padding:.5rem;margin:.3rem 0 .8rem;box-sizing:border-box}
button{background:#c00;color:#fff;border:0;padding:.5rem 1.2rem;border-radius:4px;cursor:pointer}
.meta{color:#666;font-size:.85rem}.tag{background:#eee;border-radius:3px;padding:0 .4rem;margin-right:.3rem}
pre{white-space:pre-wrap;font-family:inherit;margin:.5rem 0 0}
"""


def page(title, content):
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} - ナレッジDB</title><style>{CSS}</style></head><body>
<header><a href="/">検索</a><a href="/new">コンピュート 新規登録</a></header>{content}</body></html>"""


def render_item(r):
    tags = "".join(f'<span class="tag">{escape(t)}</span>' for t in r["tags"].split(",") if t.strip())
    return (
        f'<div class="card"><strong>{escape(r["title"])}</strong>'
        f'<div class="meta">{escape(r["category"])} {tags} / {escape(r["created_at"])}</div>'
        f'<pre>{escape(r["body"])}</pre></div>'
    )


def search_page(q):
    sql = "SELECT * FROM knowledge"
    params = []
    if q:
        sql += " WHERE title LIKE ? OR category LIKE ? OR tags LIKE ? OR body LIKE ?"
        params = [f"%{q}%"] * 4
    sql += " ORDER BY id DESC LIMIT 100"
    with get_conn() as c:
        rows = c.execute(sql, params).fetchall()
    items = "".join(render_item(r) for r in rows) or '<div class="card">該当するナレッジはありません。</div>'
    form = (
        '<form class="card" method="get" action="/"><input name="q" placeholder="キーワード(タイトル・カテゴリ・タグ・本文)" '
        f'value="{escape(q, quote=True)}"><button>検索</button></form>'
    )
    return page("検索", form + f'<p class="meta">{len(rows)} 件</p>' + items)


NEW_FORM = """<form class="card" method="post" action="/new">
<label>タイトル(必須)<input name="title" required maxlength="200"></label>
<label>カテゴリ<input name="category" maxlength="100"></label>
<label>タグ(カンマ区切り)<input name="tags" maxlength="200"></label>
<label>本文(必須)<textarea name="body" rows="8" required maxlength="20000"></textarea></label>
<button>登録</button></form>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="text/html; charset=utf-8", headers=None):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/healthz":
            return self._send(200, "ok", "text/plain")
        if u.path == "/new":
            return self._send(200, page("新規登録", NEW_FORM))
        if u.path == "/":
            q = parse_qs(u.query).get("q", [""])[0].strip()
            return self._send(200, search_page(q))
        self._send(404, page("404", '<div class="card">ページが見つかりません。</div>'))

    def do_POST(self):
        if urlparse(self.path).path != "/new":
            return self._send(404, "not found", "text/plain")
        length = min(int(self.headers.get("Content-Length", 0)), 100_000)
        form = parse_qs(self.rfile.read(length).decode("utf-8"))
        get = lambda k: form.get(k, [""])[0].strip()
        if not get("title") or not get("body"):
            return self._send(400, page("エラー", '<div class="card">タイトルと本文は必須です。</div>'))
        with _lock, get_conn() as c:
            c.execute(
                "INSERT INTO knowledge (title, category, tags, body) VALUES (?,?,?,?)",
                (get("title"), get("category"), get("tags"), get("body")),
            )
        self._send(303, "", "text/plain", {"Location": "/"})


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.daemon_threads = True

    # PID 1 の Python は SIGTERM を無視するため、明示的に停止処理を登録する
    def _stop(signum, frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    print(f"listening on :{PORT}, db={DB_PATH}", flush=True)
    server.serve_forever()
    server.server_close()
    print("shutdown complete", flush=True)
