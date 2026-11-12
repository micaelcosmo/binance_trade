"""Monta o estado.json do painel de desenvolvimento.

Fontes (cada uma isolada em try/except; falha vira {"erro": "..."}):
- .spec/STATUS.md e .spec/TEMPO.md (bloco YAML do track.py): épicos → fases, tasks → units,
  agentes, decisões abertas → pendências, próxima interação e links;
- .spec/units/UNIT-*.md: status da spec de cada épico; .spec/adr/ADR-*.md: decisões;
- git, disco (C:/D:), versão do Python;
- bot: web app em 127.0.0.1:5000, bot_status.json (heartbeat do motor), profit_gain_state.json;
- devpanel/atividade.jsonl (hook do Claude Code) → feed "Agora", "rodando" e "tarefa";
- devpanel/testes.json (python devpanel/rodar_testes.py) e simulation/reports/ → card "Testes".

Nunca lê user.cfg/.env. Só copia campos conhecidos.

    python devpanel/coletor.py --uma-vez   # imprime o estado e sai
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import track  # noqa: E402

ROOT = track.ROOT
DEVPANEL = os.path.join(ROOT, "devpanel")
SPEC = track.SPEC
ATIVIDADE = os.path.join(DEVPANEL, "atividade.jsonl")
TESTES = os.path.join(DEVPANEL, "testes.json")
WEBAPP_URL = os.environ.get("PAINEL_WEBAPP_URL", "http://127.0.0.1:5000/")
SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)

ATIVIDADE_N = 25
ATIVIDADE_BYTES = 64 * 1024
FOLGA_DA_MESMA_LEVA_S = 3
LIMITE_PRIMEIRO_PLANO_S = 15 * 60
LIMITE_SEGUNDO_PLANO_S = 60 * 60
EVENTOS_QUE_FECHAM = ("PreToolUse", "Stop", "SubagentStop", "Tarefa")
MOTOR_PARADO_S = 180
MOTOR_DESLIGADO_S = 24 * 3600   # sem sinal há mais de 1 dia: bot desligado, dados são históricos

TASK_ESTADO = {"todo": "pendente", "doing": "andamento", "done": "concluida", "blocked": "bloqueada",
               "review": "aguardando", "cancelled": "concluida"}
AGENTE_ESTADO = {"active": "ativo", "waiting": "ativo", "idle": "previsto", "done": "entregue",
                 "killed": "encerrado", "error": "encerrado"}
SPEC_ESTADO = {"DRAFT": "pendente", "APPROVED": "aguardando", "IMPLEMENTED": "concluida", "VERIFIED": "concluida"}
ADR_STATUS = {"accepted": "aceita", "proposed": "proposta", "deferred": "adiada", "rejected": "rejeitada",
              "superseded": "substituida"}


def iso_local(epoch: float) -> str:
    return dt.datetime.fromtimestamp(epoch).astimezone().isoformat(timespec="seconds")


def epoch_de(iso) -> float | None:
    d = track.parse_ts(iso)
    return d.timestamp() if d else None


def seguro(fn):
    try:
        return fn()
    except Exception as e:  # o painel nunca cai por causa de uma fonte
        return {"erro": f"{type(e).__name__}: {str(e)[:120]}"}


def rel(path: str) -> str:
    return os.path.relpath(path, SPEC).replace("\\", "/")


# ------------------------------------------------------------------ .spec
def _cabecalho_md(path: str) -> dict:
    """Lê as linhas '- **Chave:** valor' do topo de um ADR/UNIT."""
    out, titulo = {}, None
    with open(path, encoding="utf-8") as f:
        for i, linha in enumerate(f):
            if i > 25:
                break
            if titulo is None and linha.startswith("# "):
                titulo = linha[2:].strip()
            m = re.match(r"^-\s+\*\*([^*:]+):\*\*\s*(.+)$", linha.strip())
            if m:
                out[m.group(1).strip().lower()] = m.group(2).strip()
    out["_titulo"] = titulo or os.path.basename(path)
    return out


def _units_por_epico() -> dict:
    """{E2: ('units/UNIT-010-....md', 'IMPLEMENTED')} a partir dos cabeçalhos das UNITs."""
    mapa = {}
    for path in sorted(glob.glob(os.path.join(SPEC, "units", "UNIT-*.md"))):
        cab = _cabecalho_md(path)
        m = re.search(r"\bE(\d+)\b", cab.get("épico", "") or cab.get("epico", ""))
        if not m:
            continue
        status = (cab.get("status", "") or "").split()[0].strip("*,.;") if cab.get("status") else ""
        mapa.setdefault(f"E{m.group(1)}", (rel(path), status.upper() or None))
    return mapa


def _unit_specs() -> list:
    """Todas as UNITs de .spec/units/ com status, épico e prioridade (tile e card "UNITs")."""
    out = []
    for path in sorted(glob.glob(os.path.join(SPEC, "units", "UNIT-*.md"))):
        cab = _cabecalho_md(path)
        bruto = cab.get("status", "") or ""
        palavra = bruto.split()[0].strip("*,.;") if bruto else ""
        detalhe = bruto[len(palavra):].strip(" —-()") if palavra else ""
        epico = re.search(r"\bE\d+\b", cab.get("épico", "") or cab.get("epico", "") or "")
        out.append({
            "id": os.path.basename(path)[:8], "titulo": re.sub(r"^UNIT-\d+\s*[·—:-]\s*", "", cab["_titulo"]),
            "status": palavra.upper() or "SEM STATUS", "detalhe": detalhe[:200] or None,
            "epico": epico.group(0) if epico else None, "arquivo": rel(path),
        })
    return out


def _adrs() -> list:
    adrs = []
    for path in sorted(glob.glob(os.path.join(SPEC, "adr", "ADR-*.md"))):
        cab = _cabecalho_md(path)
        bruto = (cab.get("status", "") or "").split()
        st = bruto[0].strip("*,.;").lower() if bruto else "proposed"
        titulo = re.sub(r"^ADR-\d+\s*[—·:-]\s*", "", cab["_titulo"])
        data = re.search(r"\d{4}-\d{2}-\d{2}", cab.get("data", "") or cab.get("status", ""))
        adrs.append({
            "id": os.path.basename(path)[:8], "titulo": titulo, "status": ADR_STATUS.get(st, st),
            "arquivo": rel(path), "data": data.group(0) if data else None, "afeta": [], "resumo": None,
        })
    return adrs


def coletar_spec() -> dict:
    s, t = track.load()
    unit_de = _units_por_epico()
    fases = [{"id": e["id"], "titulo": e.get("title", e["id"]), "objetivo": e.get("note")}
             for e in sorted(s["epics"], key=lambda e: (e.get("priority", 9), e["id"]))]
    units = []
    for tk in s["tasks"]:
        rec = t["tasks"].get(tk["id"], {})
        steps = tk.get("steps", [])
        feitos = sum(1 for x in steps if x.get("done"))
        doing = next((x["name"] for x in steps if x.get("doing") and not x.get("done")), None)
        spec_path, spec_st = unit_de.get(tk.get("epic"), (None, None))
        est = rec.get("estimate_min")
        nota = tk.get("note") or ""
        if steps:
            nota = (f"steps {feitos}/{len(steps)}" + (f" · agora: {doing}" if doing else "")
                    + (f" · {nota}" if nota else ""))
        units.append({
            "id": tk["id"], "titulo": tk.get("title", tk["id"]), "fase": tk.get("epic"),
            "estado": TASK_ESTADO.get(tk.get("status"), "pendente"), "quem": tk.get("agent"),
            "spec": spec_path, "specStatus": spec_st,
            "previsto": f"{int(est)} min" if est else None, "depends_on": [],
            "arquivos": [tk["deliverable"]] if tk.get("deliverable") else [], "nota": nota,
            "entregue_em": (rec.get("finished_at") or "")[:10] or None,
            "steps": [{"nome": x["name"], "feito": bool(x.get("done")), "agora": bool(x.get("doing"))} for x in steps],
            "gastoMin": track.minutes_between(rec["started_at"], rec.get("finished_at")) if rec.get("started_at") else None,
        })
    agentes = []
    for a in s["agents"]:
        rec = t["agents"].get(a["id"], {})
        cuida = [u["id"] for u in units if u.get("quem") == a["id"]]
        agentes.append({
            "id": a["id"], "papel": a.get("role") or a.get("name"),
            "fixo": a.get("kind") == "orchestrator", "paralelo": a.get("kind") != "orchestrator",
            "estado": AGENTE_ESTADO.get(a.get("status"), "previsto"), "cuida_de": cuida,
            "desde": (rec.get("spawned_at") or "")[:16].replace("T", " ") or None,
            "nota": (f"{a.get('task')}: {a['step']}" if a.get("step") else None),
        })
    # orquestrador primeiro (a raia de agentes liga a partir dele)
    agentes.sort(key=lambda a: 0 if a["id"] == "orquestrador" else 1)
    pendencias = [{"id": d["id"], "texto": d.get("question"), "quem": "Micael",
                   "estado": "fechada" if d.get("status") == "answered" else "aberta",
                   "recomendacao": d.get("recommendation"), "bloqueante": bool(d.get("blocking")),
                   "opcoes": d.get("options") or []}
                  for d in s["decisions"]]
    # UNITs sem task viram uma faixa própria no fluxo (cor pelo status da spec);
    # ficam fora do progresso e da tabela, que contam só tasks
    specs = _unit_specs()
    epicos_com_task = {u["fase"] for u in units}
    backlog = [{
        "id": sp["id"], "titulo": sp["titulo"], "fase": "UN", "kind": "spec",
        "estado": SPEC_ESTADO.get(sp["status"], "pendente"), "quem": sp.get("epico") or "sem épico",
        "spec": sp["arquivo"], "specStatus": sp["status"], "previsto": None, "depends_on": [], "arquivos": [],
        "nota": sp.get("detalhe"), "entregue_em": None, "steps": [], "gastoMin": None,
    } for sp in specs if sp.get("epico") not in epicos_com_task]
    backlog_fase = {"id": "UN", "titulo": "UNITs sem task", "objetivo": "specs anteriores e backlog; cor = status da spec"}
    links = [ln for ln in s.get("links", []) if str(ln.get("url", "")).lower().startswith(("http://", "https://"))]
    p = s["project"]
    mtime = os.path.getmtime(track.STATUS_MD)
    arch_mtime = os.path.getmtime(os.path.join(SPEC, "arch.yaml"))
    return {
        "projeto": {"nome": p.get("name", "binance_trade"), "branch": p.get("branch"), "versao": p.get("version"),
                    "atualizado": (s.get("updated_at") or "")[:10], "objetivo": p.get("goal"),
                    "sessaoInicio": p.get("session_started_at"), "sessaoPrazo": p.get("session_deadline")},
        "proximaInteracao": s.get("proxima") or {},
        "fases": fases, "units": units, "unitSpecs": specs, "backlog": backlog, "backlogFase": backlog_fase,
        "adrs": _adrs(), "agentes": agentes, "pendencias": pendencias,
        "links": links[:20], "linksRecusados": len(s.get("links", [])) - len(links),
        "statusMtimeEpoch": round(mtime, 3), "archMtimeEpoch": round(arch_mtime, 3), "archIso": iso_local(arch_mtime),
        "tempo": t.get("totals", {}),
    }


# ------------------------------------------------------------------ git / disco
def _git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                       timeout=8, creationflags=SEM_JANELA)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:100] or f"git {args[0]} falhou")
    return r.stdout.strip()


def coletar_git() -> dict:
    h, assunto, quando = _git("log", "-1", "--pretty=format:%h%x1f%s%x1f%cI").split("\x1f")
    try:
        upstream = _git("rev-parse", "--abbrev-ref", "@{u}")
        behind, ahead = (int(x) for x in _git("rev-list", "--left-right", "--count", "@{u}...HEAD").split())
    except RuntimeError:
        upstream, ahead, behind = None, 0, 0
    linhas = [ln for ln in _git("status", "--porcelain").splitlines() if ln.strip()]
    try:
        tag = _git("describe", "--tags", "--abbrev=0")
    except RuntimeError:
        tag = None
    try:
        descricao = _git("describe", "--tags", "--always")
    except RuntimeError:
        descricao = None
    return {
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "commit": {"hash": h, "assunto": assunto, "quando": quando},
        "upstream": upstream, "ahead": ahead, "behind": behind,
        "modificados": sum(1 for ln in linhas if not ln.startswith("??")),
        "naoVersionados": sum(1 for ln in linhas if ln.startswith("??")),
        "tag": tag, "descricao": descricao,
    }


def coletar_disco() -> dict:
    out = {}
    for letra in ("C", "D"):
        try:
            u = shutil.disk_usage(f"{letra}:\\")
            out[letra] = {"livreGB": round(u.free / 1e9, 1), "totalGB": round(u.total / 1e9, 1)}
        except OSError as e:
            out[letra] = {"erro": str(e)[:60]}
    return out


# ------------------------------------------------------------------ bot
def _ler_json(nome: str):
    path = os.path.join(ROOT, nome)
    if not os.path.exists(path):
        return None, None
    with open(path, encoding="utf-8") as f:
        return json.load(f), os.path.getmtime(path)


def coletar_bot() -> dict:
    out = {}
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(WEBAPP_URL, timeout=1.0) as r:
            out["web"] = {"ok": 200 <= r.status < 400, "codigo": r.status,
                          "ms": round((time.perf_counter() - t0) * 1000)}
    except urllib.error.HTTPError as e:
        out["web"] = {"erro": f"HTTP {e.code}", "ms": round((time.perf_counter() - t0) * 1000)}
    except (TimeoutError, OSError) as e:
        motivo = "tempo esgotado" if "timed out" in str(e).lower() else "sem resposta"
        out["web"] = {"erro": motivo, "ms": round((time.perf_counter() - t0) * 1000)}
    st, mt = _ler_json("bot_status.json")
    if st is None:
        out["motor"] = {"existe": False}
    else:
        hb = st.get("last_heartbeat_ts")
        hb = float(hb) if isinstance(hb, (int, float)) else mt
        out["motor"] = {
            "existe": True, "heartbeatEpoch": hb, "parado": (time.time() - hb) > MOTOR_PARADO_S,
            "desligado": (time.time() - hb) > MOTOR_DESLIGADO_S,
            "status": str(st.get("status") or "")[:80], "moeda": st.get("coin"),
            "tradesHoje": st.get("daily_trades"), "maxTrades": st.get("max_daily_trades"),
            "ganhos": st.get("trades_won"), "perdas": st.get("trades_lost"),
        }
    pg, _ = _ler_json("profit_gain_state.json")
    if pg is not None:
        out["estado"] = {"dia": pg.get("current_date"), "lucroDiaPct": pg.get("daily_profit_pct"),
                         "emOperacao": bool(pg.get("active_altcoin_quantity"))}
    return out


# ------------------------------------------------------------------ testes e simulações
def coletar_testes() -> dict:
    out = {"existe": False}
    if os.path.exists(TESTES):
        with open(TESTES, encoding="utf-8") as f:
            out = json.load(f)
        out["existe"] = True
    sims = []
    for path in sorted(glob.glob(os.path.join(ROOT, "simulation", "reports", "sim-*.md"))):
        cab = _cabecalho_md(path)
        sims.append({"arquivo": os.path.relpath(path, ROOT).replace("\\", "/"),
                     "titulo": re.sub(r"^sim-\d+\s*[—·-]\s*", "", cab["_titulo"])[:120],
                     "quandoEpoch": os.path.getmtime(path)})
    out["simulacoes"] = sims
    return out


# ------------------------------------------------------------------ atividade (hook)
def _ler_eventos() -> list:
    if not os.path.exists(ATIVIDADE):
        return []
    with open(ATIVIDADE, "rb") as f:
        f.seek(0, 2)
        tam = f.tell()
        f.seek(max(0, tam - ATIVIDADE_BYTES))
        bruto = f.read().decode("utf-8", "replace").splitlines()
    if tam > ATIVIDADE_BYTES:
        bruto = bruto[1:]
    eventos = []
    for linha in bruto:
        try:
            ev = json.loads(linha)
        except ValueError:
            continue
        if isinstance(ev, dict):
            ev["epoch"] = epoch_de(ev.get("hora"))
            eventos.append(ev)
    return eventos


def _eventos_do_tracker() -> list:
    """Eventos do STATUS.md (track.py) no formato do feed, mais um "Stop" sintético quando o
    orquestrador está marcado como aguardando. Assim o "Agora" reflete o trabalho real mesmo
    sem o hook do Claude Code ligado."""
    s, _ = track.load()
    out = []
    for ev in s["events"][-ATIVIDADE_N:]:
        who = ev.get("who") or "orquestrador"
        if who == "micael":
            continue
        out.append({"hora": ev.get("at"), "evento": "Track", "ferramenta": "track", "descricao": ev.get("msg"),
                    "agente": "" if who == "orquestrador" else who, "epoch": epoch_de(ev.get("at"))})
    orq = next((a for a in s["agents"] if a["id"] == "orquestrador"), None)
    if orq and orq.get("status") in ("waiting", "idle") and orq.get("heartbeat"):
        out.append({"hora": orq["heartbeat"], "evento": "Stop", "ferramenta": "", "descricao": orq.get("step") or "",
                    "agente": "", "epoch": epoch_de(orq["heartbeat"])})
    return out


def coletar_atividade() -> list:
    evs = [e for e in _ler_eventos() if e.get("evento") != "PostToolUse"] + _eventos_do_tracker()
    evs = [e for e in evs if e.get("epoch") is not None]
    evs.sort(key=lambda e: e["epoch"])
    campos = ("hora", "evento", "ferramenta", "descricao", "agente", "epoch")
    return [{k: e.get(k) for k in campos} for e in evs[-ATIVIDADE_N:]]


def coletar_rodando(agora=None) -> list:
    agora = agora or time.time()
    evs = _ler_eventos()
    fins = {}
    for e in evs:
        if e.get("evento") == "PostToolUse" and e.get("id"):
            fins[e["id"]] = e
    rodando = []
    for i, ini in enumerate(evs):
        if ini.get("evento") != "PreToolUse" or not ini.get("id") or ini.get("epoch") is None:
            continue
        fim = fins.get(ini["id"])
        fundo = bool(fim and fim.get("fundo"))
        if fim and not fundo:
            continue
        idade = agora - ini["epoch"]
        if idade > (LIMITE_SEGUNDO_PLANO_S if fundo else LIMITE_PRIMEIRO_PLANO_S):
            continue
        if not fundo and any(
            e.get("agente", "") == ini.get("agente", "") and e.get("evento") in EVENTOS_QUE_FECHAM
            and (e.get("epoch") or 0) - ini["epoch"] > FOLGA_DA_MESMA_LEVA_S for e in evs[i + 1:]
        ):
            continue
        rodando.append({"descricao": ini.get("descricao"), "ferramenta": ini.get("ferramenta"),
                        "agente": ini.get("agente", ""), "desde": ini.get("hora"), "desdeEpoch": ini["epoch"],
                        "fundo": fundo})
    return rodando


def coletar_tarefa():
    """Tarefa atual: a mais recente entre o evento "Tarefa" do hook e a task do orquestrador no STATUS."""
    hook = None
    for e in reversed(_ler_eventos()):
        if e.get("evento") == "Tarefa":
            hook = {"descricao": e.get("descricao"), "desde": e.get("hora"), "desdeEpoch": e.get("epoch")}
            break
    s, t = track.load()
    orq = next((a for a in s["agents"] if a["id"] == "orquestrador"), None)
    tk = next((x for x in s["tasks"] if orq and x["id"] == orq.get("task")), None)
    status = None
    if tk and tk.get("status") not in ("done", "cancelled"):
        ini = t["tasks"].get(tk["id"], {}).get("started_at") or orq.get("heartbeat")
        status = {"descricao": f"{tk['id']} · {tk.get('title')}", "desde": ini, "desdeEpoch": epoch_de(ini)}
    candidatos = [c for c in (hook, status) if c and c.get("desdeEpoch")]
    return max(candidatos, key=lambda c: c["desdeEpoch"]) if candidatos else None


# ------------------------------------------------------------------ montagem
def coletar(processos: dict | None = None) -> dict:
    agora = time.time()
    return {
        "geradoEm": iso_local(agora), "geradoEmEpoch": round(agora, 3), "pid": os.getpid(), "intervaloS": 3,
        "python": sys.version.split()[0],
        "spec": seguro(coletar_spec), "git": seguro(coletar_git), "disco": seguro(coletar_disco),
        "bot": seguro(coletar_bot), "testes": seguro(coletar_testes),
        "atividade": seguro(coletar_atividade), "rodando": seguro(coletar_rodando), "tarefa": seguro(coletar_tarefa),
        "processos": processos or {},
    }


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(coletar(), ensure_ascii=False, indent=1)[:4000])
