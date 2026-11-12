# UNIT-008 · Painel de acompanhamento do desenvolvimento (E0)

- **Status:** Implemented (T-001…T-005; painel refeito em 2026-11-11 com a cara do modelo pedido pelo Micael) — hook do feed "Agora" aguarda aprovação
- **Épico:** E0 · **Prioridade:** 0 · **Tasks:** T-001, T-002, T-003
- **ADRs:** ADR-0010
- **Arquitetura:** `arch.yaml#dev_tooling`, `#runtime.processes.devpanel`, `#components.devpanel`

## Objetivo
Dar ao Micael visibilidade em tempo real do trabalho multi-agente: agentes, tasks, steps, tempos, eventos e decisões pendentes, com possibilidade de responder decisões pela UI.

## Escopo
- `devpanel/track.py` — CLI com subcomandos `agent|task|epic|decision|event|project|show`; mantém `.spec/STATUS.md` e `.spec/TEMPO.md` (markdown + bloco YAML fonte de verdade) com lock `.spec/.track.lock` + escrita atômica (T-001).
- `devpanel/server.py` + `devpanel/static/index.html` — Flask em `127.0.0.1:5055`; `GET /api/state` (STATUS+TEMPO+git log/tags), `POST /api/decisions/<id>` (resposta do Micael) (T-002).
- Watchdog de heartbeat: agente `active` sem heartbeat há > 15 min = alerta (T-003).

## Fora de escopo
- Qualquer integração com o bot de trading ou com o painel do produto (`app.py`).
- Exposição fora de localhost.

## Critérios de aceite
- [x] `track.py` grava STATUS/TEMPO concorrente sem corromper (T-001).
- [ ] Painel lista agentes/épicos/tasks/steps/tempos/decisões/eventos com auto-refresh (T-002).
- [ ] Responder decisão pela UI atualiza STATUS.md (`status: answered`) e gera evento.
- [ ] Alerta visível de agente parado (T-003).
- [ ] Layout validado pelo Micael (decisão D-001).

## Revisão 2026-11-11 (T-005)

O Micael pediu a mesma cara de um painel modelo que ele já usa. A página passou a seguir esse modelo (tema claro/escuro, cartão "Próxima interação", Links, faixa "ao vivo", feed "Agora", card Testes, progresso por épico, tiles, canvas de fluxo com raia de agentes, Agentes | Pendências, ADRs, tabela de tasks). Nenhum nome ou arquivo do projeto modelo entra aqui.

- `devpanel/coletor.py` monta `estado.json`; `devpanel/server.py` passou a stdlib, só leitura (decisões são respondidas no chat, não pelo painel).
- `devpanel/registrar_atividade.py` (hook) e `devpanel/rodar_testes.py` alimentam "Agora" e "Testes".
- Pendente: ligar o hook em `.claude/settings.json` (aprovação do Micael).
