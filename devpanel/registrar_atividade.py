"""Hook do Claude Code → devpanel/atividade.jsonl (feed "Agora" do painel).

Ligado em .claude/settings.json para PreToolUse, PostToolUse, UserPromptSubmit, Stop e
SubagentStop. Grava só texto seguro: a descrição curta que a própria ferramenta declara, o
caminho relativo do arquivo ou o tipo do evento. Nunca o comando, conteúdo de arquivo ou o
texto do Micael. Sempre sai com código 0 (um hook quebrado não pode travar a sessão).

Uso direto pelo orquestrador no começo de cada pedido:
    .venv/Scripts/python devpanel/registrar_atividade.py --tarefa "texto curto"
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ARQUIVO = os.path.join(AQUI, "atividade.jsonl")
MARCA_REPO = "/binance_trade/"
LIMITE_DESCRICAO = 160
PODA_BYTES = 200 * 1024
PODA_LINHAS = 400

COM_DESCRICAO = ("Bash", "PowerShell", "Agent", "Task", "Workflow")
DE_ARQUIVO = ("Read", "Edit", "Write", "NotebookEdit")
DE_BUSCA = ("Grep", "Glob", "ToolSearch")
SEM_FERRAMENTA = {
    "UserPromptSubmit": ("", "mensagem do Micael"),
    "Stop": ("", "terminou a vez"),
    "SubagentStop": ("", "agente terminou"),
}


def _agora() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _descrever(ferramenta: str, entrada: dict) -> str:
    if ferramenta in COM_DESCRICAO:
        return entrada.get("description") or "(sem descrição)"
    if ferramenta in DE_ARQUIVO:
        caminho = (entrada.get("file_path") or entrada.get("notebook_path") or "").replace("\\", "/")
        return caminho.split(MARCA_REPO)[-1] or "(arquivo)"
    if ferramenta in DE_BUSCA:
        return "busca no código"
    if ferramenta == "AskUserQuestion":
        return "pergunta com opções para o Micael"
    if ferramenta == "SendMessage":
        return "mensagem para um agente"
    return ferramenta


def _foi_para_segundo_plano(dados: dict) -> bool:
    entrada = dados.get("tool_input") or {}
    if isinstance(entrada, dict) and entrada.get("run_in_background"):
        return True
    resposta = dados.get("tool_response")
    return isinstance(resposta, dict) and bool(resposta.get("backgroundTaskId"))


def _gravar(linha: dict) -> None:
    with open(ARQUIVO, "a", encoding="utf-8") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")
    if os.path.getsize(ARQUIVO) > PODA_BYTES:
        with open(ARQUIVO, encoding="utf-8") as f:
            ultimas = f.readlines()[-PODA_LINHAS:]
        tmp = ARQUIVO + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.writelines(ultimas)
        os.replace(tmp, ARQUIVO)


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "--tarefa":
        _gravar({"hora": _agora(), "evento": "Tarefa", "ferramenta": "orquestrador",
                 "descricao": " ".join(sys.argv[2:])[:LIMITE_DESCRICAO], "agente": ""})
        return
    dados = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
    evento = dados.get("hook_event_name") or "PreToolUse"
    if evento in SEM_FERRAMENTA:
        ferramenta, descricao = SEM_FERRAMENTA[evento]
    else:
        ferramenta = dados.get("tool_name") or "?"
        entrada = dados.get("tool_input") or {}
        descricao = _descrever(ferramenta, entrada if isinstance(entrada, dict) else {})
    linha = {"hora": _agora(), "evento": evento, "ferramenta": ferramenta,
             "descricao": str(descricao)[:LIMITE_DESCRICAO],
             "agente": dados.get("agent_type") or dados.get("agent_id") or ""}
    if evento in ("PreToolUse", "PostToolUse"):
        linha["id"] = str(dados.get("tool_use_id") or "")
    if evento == "PostToolUse":
        linha["fundo"] = _foi_para_segundo_plano(dados)
    _gravar(linha)


if __name__ == "__main__":
    try:
        main()
    except Exception:  # hook nunca derruba a sessão
        pass
    sys.exit(0)
