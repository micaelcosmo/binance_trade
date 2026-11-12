"""Rastreador de desenvolvimento: mantém .spec/STATUS.md e .spec/TEMPO.md.

Cada arquivo é markdown legível + um bloco YAML (entre marcadores) que é a
fonte de verdade lida pelo painel (devpanel/server.py). Toda escrita passa por
lock exclusivo + escrita atômica, então vários agentes podem chamar em paralelo.

Uso rápido (sempre a partir da raiz do repo):
  python devpanel/track.py agent ag-sim --name "Simulador" --status active --task T-020 --step "baixando klines"
  python devpanel/track.py task T-020 --status doing --agent ag-sim --step-done "baixar klines"
  python devpanel/track.py task T-020 --add-step "rodar grade" --estimate 90
  python devpanel/track.py event "grade de 60 variações iniciada" --who ag-sim
  python devpanel/track.py decision D-003 --question "..." --options "A|B" --blocking
  python devpanel/track.py show
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import os
import sys
import tempfile
import time

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SPEC = os.path.join(ROOT, ".spec")
STATUS_MD = os.path.join(SPEC, "STATUS.md")
TEMPO_MD = os.path.join(SPEC, "TEMPO.md")
LOCK = os.path.join(SPEC, ".track.lock")

BEGIN = "<!-- DATA:BEGIN (gerado por devpanel/track.py — não edite à mão) -->"
END = "<!-- DATA:END -->"

AGENT_STATUS = ("active", "idle", "waiting", "done", "killed", "error")
TASK_STATUS = ("todo", "doing", "blocked", "review", "done", "cancelled")
MAX_EVENTS = 300


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def parse_ts(value):
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(str(value))
    except ValueError:
        return None


def minutes_between(start, end=None) -> float:
    s = parse_ts(start)
    if not s:
        return 0.0
    e = parse_ts(end) or dt.datetime.now().astimezone()
    return round(max((e - s).total_seconds(), 0) / 60, 1)


# --------------------------------------------------------------------------- io
@contextlib.contextmanager
def locked(timeout: float = 20.0):
    os.makedirs(SPEC, exist_ok=True)
    deadline = time.time() + timeout
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            break
        except FileExistsError:
            # lock órfão (processo morreu) — expira após 30s
            with contextlib.suppress(OSError):
                if time.time() - os.path.getmtime(LOCK) > 30:
                    os.remove(LOCK)
                    continue
            if time.time() > deadline:
                raise TimeoutError("lock de .spec ocupado")
            time.sleep(0.1)
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            os.remove(LOCK)


def atomic_write(path: str, text: str) -> None:
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-", suffix=".md")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    for _ in range(20):  # Windows: leitor pode segurar o arquivo por instantes
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(0.05)
    os.replace(tmp, path)


def read_block(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if BEGIN not in text:
        return {}
    chunk = text.split(BEGIN, 1)[1].split(END, 1)[0]
    chunk = chunk.strip().removeprefix("```yaml").removesuffix("```")
    return yaml.safe_load(chunk) or {}


def load() -> tuple[dict, dict]:
    status = read_block(STATUS_MD)
    tempo = read_block(TEMPO_MD)
    status.setdefault("project", {"name": "binance_trade"})
    for key in ("agents", "epics", "tasks", "decisions", "events"):
        status.setdefault(key, [])
    tempo.setdefault("tasks", {})
    tempo.setdefault("agents", {})
    return status, tempo


def dump_yaml(data: dict) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=110)


# ------------------------------------------------------------------- rendering
def _cell(v) -> str:
    return str(v if v not in (None, "") else "—").replace("|", "/").replace("\n", " ")


def _table(headers, rows) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(_cell(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def render_status(s: dict) -> str:
    p = s["project"]
    tasks = s["tasks"]
    done = sum(1 for t in tasks if t.get("status") == "done")
    lines = [
        "# STATUS — acompanhamento de desenvolvimento",
        "",
        f"> Atualizado em **{s.get('updated_at', '—')}** · branch `{p.get('branch', '—')}` · "
        f"versão `{p.get('version', '—')}` · {done}/{len(tasks)} tasks concluídas.",
        "> Fonte de verdade = bloco YAML no fim. Atualize via `python devpanel/track.py ...`. "
        "Painel: `python devpanel/server.py` → http://127.0.0.1:5055",
        "",
        "## Agentes",
        "",
        _table(["id", "nome", "status", "task", "step atual", "heartbeat"],
               [[a.get("id"), a.get("name"), a.get("status"), a.get("task"), a.get("step"),
                 a.get("heartbeat")] for a in s["agents"]]),
        "",
        "## Épicos",
        "",
        _table(["id", "P", "épico", "status"],
               [[e.get("id"), e.get("priority"), e.get("title"), e.get("status")] for e in s["epics"]]),
        "",
        "## Tasks",
        "",
        _table(["id", "épico", "task", "status", "agente", "steps"],
               [[t.get("id"), t.get("epic"), t.get("title"), t.get("status"), t.get("agent"),
                 f"{sum(1 for x in t.get('steps', []) if x.get('done'))}/{len(t.get('steps', []))}"]
                for t in tasks]),
        "",
        "## Decisões para o Micael",
        "",
        _table(["id", "bloqueante", "pergunta", "opções", "status", "resposta"],
               [[d.get("id"), "sim" if d.get("blocking") else "não", d.get("question"),
                 " / ".join(d.get("options", []) or []), d.get("status"), d.get("answer")]
                for d in s["decisions"]]),
        "",
        "## Últimos eventos",
        "",
        "\n".join(f"- `{e.get('at')}` **{e.get('who')}** — {e.get('msg')}" for e in s["events"][-15:][::-1])
        or "- —",
        "",
        BEGIN,
        "```yaml",
        dump_yaml(s).rstrip(),
        "```",
        END,
        "",
    ]
    return "\n".join(lines)


def render_tempo(s: dict, t: dict) -> str:
    rows, tot_est, tot_spent = [], 0.0, 0.0
    for task in s["tasks"]:
        rec = t["tasks"].get(task["id"], {})
        est = float(rec.get("estimate_min") or 0)
        spent = minutes_between(rec.get("started_at"), rec.get("finished_at")) if rec.get("started_at") else 0.0
        rec["spent_min"] = spent
        tot_est += est
        tot_spent += spent
        delta = f"{spent - est:+.0f}" if est and spent else "—"
        rows.append([task["id"], task.get("title"), est or "—", spent or "—", delta,
                     rec.get("started_at"), rec.get("finished_at")])
    arows = []
    for aid, rec in t["agents"].items():
        rec["alive_min"] = minutes_between(rec.get("spawned_at"), rec.get("ended_at"))
        arows.append([aid, rec.get("spawned_at"), rec.get("ended_at"), rec["alive_min"]])
    t["totals"] = {"estimate_min": round(tot_est, 1), "spent_min": round(tot_spent, 1)}
    lines = [
        "# TEMPO — estimado × gasto",
        "",
        f"> Atualizado em **{s.get('updated_at', '—')}** · estimado total **{tot_est:.0f} min** · "
        f"gasto total **{tot_spent:.0f} min**. Tempos em minutos (relógio de parede).",
        "",
        "## Por task",
        "",
        _table(["task", "título", "estimado", "gasto", "Δ", "início", "fim"], rows),
        "",
        "## Por agente",
        "",
        _table(["agente", "criado", "encerrado", "vivo (min)"], arows),
        "",
        BEGIN,
        "```yaml",
        dump_yaml(t).rstrip(),
        "```",
        END,
        "",
    ]
    return "\n".join(lines)


def save(s: dict, t: dict) -> None:
    s["updated_at"] = now()
    s["events"] = s["events"][-MAX_EVENTS:]
    atomic_write(STATUS_MD, render_status(s))
    atomic_write(TEMPO_MD, render_tempo(s, t))


# --------------------------------------------------------------------- helpers
def find(items: list, item_id: str, create: bool = True) -> dict | None:
    for it in items:
        if it.get("id") == item_id:
            return it
    if not create:
        return None
    it = {"id": item_id}
    items.append(it)
    return it


def event(s: dict, who: str, msg: str) -> None:
    s["events"].append({"at": now(), "who": who, "msg": msg})


def match_step(steps: list, key: str) -> dict | None:
    if key.isdigit() and int(key) < len(steps):
        return steps[int(key)]
    for st in steps:
        if st["name"] == key:
            return st
    for st in steps:
        if key.lower() in st["name"].lower():
            return st
    return None


# ------------------------------------------------------------------- commands
def cmd_agent(a, s, t):
    ag = find(s["agents"], a.id)
    rec = t["agents"].setdefault(a.id, {})
    is_new = "spawned_at" not in rec
    if is_new:
        rec["spawned_at"] = now()
    for field in ("name", "role", "task", "step", "kind"):
        val = getattr(a, field)
        if val is not None:
            ag[field] = val
    if a.status:
        if a.status not in AGENT_STATUS:
            sys.exit(f"status inválido: {AGENT_STATUS}")
        prev = ag.get("status")
        ag["status"] = a.status
        if a.status in ("done", "killed", "error"):
            rec["ended_at"] = now()
            ag["step"] = a.step or ag.get("step")
        elif prev in ("done", "killed", "error"):
            rec.pop("ended_at", None)
        if prev != a.status:
            event(s, a.id, f"status → {a.status}")
    ag.setdefault("status", "active")
    ag["heartbeat"] = now()
    if a.step:
        hist = ag.setdefault("step_log", [])
        if not hist or hist[-1]["step"] != a.step:
            hist.append({"at": now(), "step": a.step})
            ag["step_log"] = hist[-20:]
    if is_new:
        event(s, a.id, f"agente criado ({ag.get('name', a.id)})")


def cmd_task(a, s, t):
    existente = find(s["tasks"], a.id, create=False)
    if existente and not a.force:
        for campo, novo in (("title", a.title), ("epic", a.epic)):
            if novo is not None and existente.get(campo) and existente[campo] != novo:
                sys.exit(f"{a.id} já existe com {campo}={existente[campo]!r}; use outro id ou --force")
    tk = find(s["tasks"], a.id)
    rec = t["tasks"].setdefault(a.id, {})
    for field in ("title", "epic", "agent", "note", "deliverable"):
        val = getattr(a, field)
        if val is not None:
            tk[field] = val
    tk.setdefault("status", "todo")
    tk.setdefault("steps", [])
    if a.estimate is not None:
        rec["estimate_min"] = a.estimate
    for name in a.add_step or []:
        if not any(st["name"] == name for st in tk["steps"]):
            tk["steps"].append({"name": name, "done": False})
    for key in a.step_done or []:
        st = match_step(tk["steps"], key)
        if st is None:
            st = {"name": key, "done": False}
            tk["steps"].append(st)
        if not st["done"]:
            st["done"] = True
            st["at"] = now()
            event(s, a.who or tk.get("agent") or "?", f"{a.id} ✓ {st['name']}")
    if a.step_doing:
        for st in tk["steps"]:
            st.pop("doing", None)
        st = match_step(tk["steps"], a.step_doing)
        if st is None:
            st = {"name": a.step_doing, "done": False}
            tk["steps"].append(st)
        st["doing"] = True
    if a.status:
        if a.status not in TASK_STATUS:
            sys.exit(f"status inválido: {TASK_STATUS}")
        prev = tk["status"]
        tk["status"] = a.status
        if a.status == "doing" and not rec.get("started_at"):
            rec["started_at"] = now()
        if a.status in ("done", "cancelled"):
            rec.setdefault("started_at", now())
            rec["finished_at"] = now()
            for st in tk["steps"]:
                st.pop("doing", None)
        elif prev in ("done", "cancelled"):
            rec.pop("finished_at", None)
        if prev != a.status:
            event(s, a.who or tk.get("agent") or "?", f"{a.id} {prev} → {a.status}")


def cmd_epic(a, s, t):
    ep = find(s["epics"], a.id)
    for field in ("title", "status", "note"):
        val = getattr(a, field)
        if val is not None:
            ep[field] = val
    if a.priority is not None:
        ep["priority"] = a.priority
    ep.setdefault("status", "todo")


def cmd_decision(a, s, t):
    d = find(s["decisions"], a.id)
    is_new = "question" not in d
    if a.question:
        d["question"] = a.question
    if a.options:
        d["options"] = [o.strip() for o in a.options.split("|")]
    if a.recommendation:
        d["recommendation"] = a.recommendation
    if a.blocking:
        d["blocking"] = True
    if a.task:
        d["task"] = a.task
    if a.answer:
        d["answer"] = a.answer
        d["status"] = "answered"
    if a.status:
        d["status"] = a.status
    d.setdefault("status", "pending")
    d.setdefault("blocking", False)
    d.setdefault("opened_at", now())
    if is_new:
        event(s, a.who or "orquestrador", f"decisão aberta {a.id}: {d.get('question')}")


def cmd_event(a, s, t):
    event(s, a.who or "orquestrador", a.msg)


def cmd_project(a, s, t):
    for field in ("name", "branch", "version", "goal", "repo"):
        val = getattr(a, field)
        if val is not None:
            s["project"][field] = val
    if a.session_start:
        s["project"]["session_started_at"] = now()
    if a.session_deadline:
        s["project"]["session_deadline"] = a.session_deadline


def cmd_proxima(a, s, t):
    """Cartão "Próxima interação do Micael" do painel."""
    p = s.setdefault("proxima", {})
    for field in ("texto", "quando", "duracao"):
        val = getattr(a, field)
        if val is not None:
            p[field] = val
    p["atualizado_em"] = now()


def cmd_link(a, s, t):
    """Botões da caixa "Links" do painel (só http/https). --remover apaga pelo título."""
    links = s.setdefault("links", [])
    links[:] = [ln for ln in links if ln.get("titulo") != a.titulo]
    if a.remover:
        return
    if not str(a.url or "").lower().startswith(("http://", "https://")):
        sys.exit("url precisa começar com http:// ou https://")
    links.append({"titulo": a.titulo, "url": a.url, "nota": a.nota or "", "desde": now()})


def cmd_show(a, s, t):
    print(render_status(s).split(BEGIN)[0])


def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    ag = sub.add_parser("agent")
    ag.add_argument("id")
    for f in ("name", "role", "status", "task", "step", "kind"):
        ag.add_argument(f"--{f}")
    ag.set_defaults(fn=cmd_agent)

    tk = sub.add_parser("task")
    tk.add_argument("id")
    for f in ("title", "epic", "status", "agent", "note", "deliverable", "who"):
        tk.add_argument(f"--{f}")
    tk.add_argument("--estimate", type=float, help="minutos estimados")
    tk.add_argument("--add-step", action="append")
    tk.add_argument("--step-done", action="append", help="nome, trecho ou índice do step")
    tk.add_argument("--step-doing", help="marca step em andamento")
    tk.add_argument("--force", action="store_true", help="permite trocar título/épico de task existente")
    tk.set_defaults(fn=cmd_task)

    ep = sub.add_parser("epic")
    ep.add_argument("id")
    for f in ("title", "status", "note"):
        ep.add_argument(f"--{f}")
    ep.add_argument("--priority", type=int)
    ep.set_defaults(fn=cmd_epic)

    de = sub.add_parser("decision")
    de.add_argument("id")
    for f in ("question", "options", "recommendation", "answer", "status", "task", "who"):
        de.add_argument(f"--{f}")
    de.add_argument("--blocking", action="store_true")
    de.set_defaults(fn=cmd_decision)

    ev = sub.add_parser("event")
    ev.add_argument("msg")
    ev.add_argument("--who")
    ev.set_defaults(fn=cmd_event)

    pr = sub.add_parser("project")
    for f in ("name", "branch", "version", "goal", "repo", "session-deadline"):
        pr.add_argument(f"--{f}")
    pr.add_argument("--session-start", action="store_true")
    pr.set_defaults(fn=cmd_project)

    px = sub.add_parser("proxima", help="cartão 'Próxima interação do Micael'")
    for f in ("texto", "quando", "duracao"):
        px.add_argument(f"--{f}")
    px.set_defaults(fn=cmd_proxima)

    lk = sub.add_parser("link", help="botão na caixa de Links do painel")
    lk.add_argument("titulo")
    lk.add_argument("--url")
    lk.add_argument("--nota")
    lk.add_argument("--remover", action="store_true")
    lk.set_defaults(fn=cmd_link)

    sh = sub.add_parser("show")
    sh.set_defaults(fn=cmd_show)
    return p


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    with locked():
        s, t = load()
        args.fn(args, s, t)
        if args.cmd != "show":
            save(s, t)


if __name__ == "__main__":
    main()
