"""Painel de acompanhamento do desenvolvimento.

Lê .spec/STATUS.md e .spec/TEMPO.md (bloco YAML gerado por devpanel/track.py)
e serve um dashboard em http://127.0.0.1:5055 com auto-refresh.

    .venv/Scripts/python devpanel/server.py [--port 5055]
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys

from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, os.path.dirname(__file__))
import track  # noqa: E402

STALE_MIN = 15  # agente "active" sem heartbeat há mais que isso = alerta
HERE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=None)


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=track.ROOT, capture_output=True, text=True,
                              encoding="utf-8", timeout=5).stdout.strip()
    except Exception:
        return ""


def git_info() -> dict:
    log = _git("log", "-8", "--pretty=format:%h\x1f%s\x1f%cI\x1f%D")
    commits = []
    for line in filter(None, log.splitlines()):
        h, subj, when, refs = (line.split("\x1f") + ["", "", ""])[:4]
        tag = next((r.strip()[5:] for r in refs.split(",") if r.strip().startswith("tag: ")), None)
        commits.append({"hash": h, "subject": subj, "at": when, "tag": tag})
    dirty = [ln for ln in _git("status", "--porcelain").splitlines() if ln.strip()]
    return {
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "last_tag": _git("describe", "--tags", "--abbrev=0"),
        "commits": commits,
        "dirty_files": len(dirty),
    }


def build_state() -> dict:
    s, t = track.load()
    now = dt.datetime.now().astimezone()
    for a in s["agents"]:
        hb = track.parse_ts(a.get("heartbeat"))
        a["heartbeat_age_min"] = round((now - hb).total_seconds() / 60, 1) if hb else None
        a["stale"] = a.get("status") == "active" and (a["heartbeat_age_min"] or 0) > STALE_MIN
        rec = t["agents"].get(a["id"], {})
        a["spawned_at"] = rec.get("spawned_at")
        a["ended_at"] = rec.get("ended_at")
        a["alive_min"] = track.minutes_between(rec.get("spawned_at"), rec.get("ended_at"))
    for tk in s["tasks"]:
        rec = t["tasks"].get(tk["id"], {})
        tk["estimate_min"] = rec.get("estimate_min")
        tk["started_at"] = rec.get("started_at")
        tk["finished_at"] = rec.get("finished_at")
        tk["spent_min"] = track.minutes_between(rec["started_at"], rec.get("finished_at")) \
            if rec.get("started_at") else 0
    p = s["project"]
    p["session_elapsed_min"] = track.minutes_between(p.get("session_started_at"))
    dl = track.parse_ts(p.get("session_deadline"))
    p["session_remaining_min"] = round((dl - now).total_seconds() / 60, 1) if dl else None
    s["git"] = git_info()
    s["server_time"] = now.isoformat(timespec="seconds")
    s["stale_threshold_min"] = STALE_MIN
    return s


@app.get("/")
def index():
    return send_from_directory(os.path.join(HERE, "static"), "index.html")


@app.get("/static/<path:name>")
def static_files(name):
    return send_from_directory(os.path.join(HERE, "static"), name)


@app.get("/api/state")
def api_state():
    resp = jsonify(build_state())
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.post("/api/decisions/<did>")
def answer_decision(did):
    body = request.get_json(silent=True) or {}
    answer = str(body.get("answer", "")).strip()
    if not answer:
        return jsonify({"error": "resposta vazia"}), 400
    with track.locked():
        s, t = track.load()
        d = track.find(s["decisions"], did, create=False)
        if d is None:
            return jsonify({"error": "decisão não encontrada"}), 404
        d["answer"] = answer[:2000]
        d["status"] = "answered"
        d["answered_at"] = track.now()
        track.event(s, "micael", f"respondeu {did}: {answer[:120]}")
        track.save(s, t)
    return jsonify({"ok": True})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5055)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    print(f"Painel de dev em http://{a.host}:{a.port}")
    app.run(host=a.host, port=a.port, debug=False, threaded=True)
