# STATUS — acompanhamento de desenvolvimento

> Atualizado em **2026-11-10T23:56:15-03:00** · branch `check_strategies` · versão `v3.7.0` · 3/15 tasks concluídas.
> Fonte de verdade = bloco YAML no fim. Atualize via `python devpanel/track.py ...`. Painel: `python devpanel/server.py` → http://127.0.0.1:5055

## Agentes

| id | nome | status | task | step atual | heartbeat |
|---|---|---|---|---|---|
| orquestrador | Orquestrador | active | T-002 | testando painel | 2026-11-10T23:54:05-03:00 |
| ag-spec | Arquiteto .spec | active | T-010 | lendo código | 2026-11-10T23:55:52-03:00 |
| ag-sim | Simulador | active | T-020 | coleta de klines | 2026-11-10T23:52:06-03:00 |
| ag-ui | Designer do app | active | T-030 | reescrevendo template (CSS próprio, sem Tailwind runtime) | 2026-11-10T23:55:58-03:00 |

## Épicos

| id | P | épico | status |
|---|---|---|---|
| E0 | 0 | Painel de acompanhamento do desenvolvimento | doing |
| E1 | 1 | Reestruturar .spec (README, arch.yaml, ADRs, UNITs) | todo |
| E2 | 1 | Simulação ≥50 variações (mock) p/ calibrar previsão, entrada, stoploss/stopwin | todo |
| E3 | 2 | Repaginar página do app (amigável/futurista, sóbria) | todo |
| E4 | 2 | Aplicar calibração na profit_gain (após simulação) | todo |

## Tasks

| id | épico | task | status | agente | steps |
|---|---|---|---|---|---|
| T-001 | E0 | CLI track.py (STATUS/TEMPO com lock) | done | orquestrador | 3/3 |
| T-002 | E0 | Servidor + UI do painel de dev | done | orquestrador | 4/4 |
| T-003 | E0 | Watchdog de heartbeat no servidor (agente parado = alerta) | done | orquestrador | 1/1 |
| T-010 | E1 | Inventário .spec atual + plano de migração | doing | ag-spec | 1/3 |
| T-011 | E1 | arch.yaml único (arquitetura do projeto inteiro) | todo | — | 0/0 |
| T-012 | E1 | ADRs (decisões existentes + novas) | todo | — | 0/0 |
| T-013 | E1 | UNITs (specs migradas + novas unidades) | todo | — | 0/0 |
| T-014 | E1 | .spec/README.md (convenções e índice) | todo | — | 0/0 |
| T-020 | E2 | Coleta de klines públicos (≥8 moedas, 1h/15m/4h/1d) | doing | ag-sim | 0/3 |
| T-021 | E2 | Mock exchange + motor de simulação fiel à profit_gain | todo | — | 0/0 |
| T-022 | E2 | Grade ≥50 variações (entrada × stop × stopwin) multi-moeda | todo | — | 0/0 |
| T-023 | E2 | Relatório + recomendação de parâmetros | todo | — | 0/0 |
| T-030 | E3 | Redesign templates/index.html | doing | ag-ui | 2/4 |
| T-031 | E3 | Verificação visual com dados mock | todo | — | 0/0 |
| T-040 | E4 | Parametrizar profit_gain e aplicar calibração aprovada | todo | — | 0/0 |

## Decisões para o Micael

| id | bloqueante | pergunta | opções | status | resposta |
|---|---|---|---|---|---|
| D-001 | não | O painel de referência (trycloudflare) devolve 403 para acesso automatizado; o layout foi desenhado a partir da sua descrição (agentes, tasks, steps, tempos). Está ok ou quer me passar print/HTML? | Ok assim / Mandar print para ajustar | pending | — |
| D-002 | não | O trabalho migrou para D:\binance_trade (cópia integral, inclusive user.cfg sem leitura). A pasta em C:\...\Documents\binance_trade ficou defasada. Apagar a cópia de C: depois? | Apagar C: após conferir / Manter as duas | pending | — |
| D-301 | não | Remover Tailwind CDN (sem versão) e usar CSS próprio + classes de compatibilidade para o HTML gerado pelo app.py nos modais? | A: remover e mapear classes / B: manter Tailwind CDN | pending | — |

## Últimos eventos

- `2026-11-10T23:56:15-03:00` **orquestrador** — commit v3.7.0: devpanel
- `2026-11-10T23:56:12-03:00` **orquestrador** — T-003 todo → done
- `2026-11-10T23:56:12-03:00` **orquestrador** — T-003 ✓ stale > 15min no /api/state
- `2026-11-10T23:56:10-03:00` **orquestrador** — T-002 doing → done
- `2026-11-10T23:56:10-03:00` **orquestrador** — T-002 ✓ auto-refresh + teste
- `2026-11-10T23:56:00-03:00` **ag-ui** — decisão aberta D-301: Remover Tailwind CDN (sem versão) e usar CSS próprio + classes de compatibilidade para o HTML gerado pelo app.py nos modais?
- `2026-11-10T23:55:57-03:00` **ag-ui** — T-030 ✓ inventariar eventos/IDs
- `2026-11-10T23:55:57-03:00` **ag-ui** — T-030 ✓ ler app.py e template
- `2026-11-10T23:55:50-03:00` **ag-spec** — T-010 ✓ ler specs antigas
- `2026-11-10T23:54:00-03:00` **orquestrador** — T-002 ✓ timeline + decisões + tempos
- `2026-11-10T23:54:00-03:00` **orquestrador** — T-002 ✓ layout agentes/tasks/steps
- `2026-11-10T23:54:00-03:00` **orquestrador** — T-002 ✓ API /api/state
- `2026-11-10T23:52:10-03:00` **ag-ui** — T-030 todo → doing
- `2026-11-10T23:52:08-03:00` **ag-sim** — T-020 todo → doing
- `2026-11-10T23:52:07-03:00` **ag-ui** — agente criado (Designer do app)

<!-- DATA:BEGIN (gerado por devpanel/track.py — não edite à mão) -->
```yaml
project:
  name: binance_trade
  branch: check_strategies
  version: v3.7.0
  goal: Painel de dev (P0), .spec ADR/UNIT/arch.yaml, simulação ≥50 variações p/ calibrar entrada/stop, repaginar
    app
  repo: D:\binance_trade
  session_started_at: '2026-11-10T23:49:02-03:00'
  session_deadline: '2026-11-11T04:48:59-03:00'
agents:
- id: orquestrador
  name: Orquestrador
  role: Planeja, cria/encerra agentes, commita
  task: T-002
  step: testando painel
  kind: orchestrator
  status: active
  heartbeat: '2026-11-10T23:54:05-03:00'
  step_log:
  - at: '2026-11-10T23:49:29-03:00'
    step: construindo painel
  - at: '2026-11-10T23:54:05-03:00'
    step: testando painel
- id: ag-spec
  name: Arquiteto .spec
  role: Reestrutura .spec
  task: T-010
  step: lendo código
  kind: worker
  status: active
  heartbeat: '2026-11-10T23:55:52-03:00'
  step_log:
  - at: '2026-11-10T23:51:53-03:00'
    step: inventário
  - at: '2026-11-10T23:55:52-03:00'
    step: lendo código
- id: ag-sim
  name: Simulador
  role: Mock exchange + backtests de calibração
  task: T-020
  step: coleta de klines
  kind: worker
  status: active
  heartbeat: '2026-11-10T23:52:06-03:00'
  step_log:
  - at: '2026-11-10T23:52:06-03:00'
    step: coleta de klines
- id: ag-ui
  name: Designer do app
  role: Repagina templates/index.html
  task: T-030
  step: reescrevendo template (CSS próprio, sem Tailwind runtime)
  kind: worker
  status: active
  heartbeat: '2026-11-10T23:55:58-03:00'
  step_log:
  - at: '2026-11-10T23:52:07-03:00'
    step: lendo template atual
  - at: '2026-11-10T23:55:58-03:00'
    step: reescrevendo template (CSS próprio, sem Tailwind runtime)
epics:
- id: E0
  title: Painel de acompanhamento do desenvolvimento
  status: doing
  priority: 0
- id: E1
  title: Reestruturar .spec (README, arch.yaml, ADRs, UNITs)
  priority: 1
  status: todo
- id: E2
  title: Simulação ≥50 variações (mock) p/ calibrar previsão, entrada, stoploss/stopwin
  priority: 1
  status: todo
- id: E3
  title: Repaginar página do app (amigável/futurista, sóbria)
  priority: 2
  status: todo
- id: E4
  title: Aplicar calibração na profit_gain (após simulação)
  priority: 2
  status: todo
tasks:
- id: T-001
  title: CLI track.py (STATUS/TEMPO com lock)
  epic: E0
  agent: orquestrador
  status: done
  steps:
  - name: modelo de dados
    done: true
    at: '2026-11-10T23:49:14-03:00'
  - name: CLI + lock atômico
    done: true
    at: '2026-11-10T23:49:14-03:00'
  - name: render md
    done: true
    at: '2026-11-10T23:49:14-03:00'
- id: T-002
  title: Servidor + UI do painel de dev
  epic: E0
  agent: orquestrador
  status: done
  steps:
  - name: API /api/state
    done: true
    at: '2026-11-10T23:54:00-03:00'
  - name: layout agentes/tasks/steps
    done: true
    at: '2026-11-10T23:54:00-03:00'
  - name: timeline + decisões + tempos
    done: true
    at: '2026-11-10T23:54:00-03:00'
  - name: auto-refresh + teste
    done: true
    at: '2026-11-10T23:56:10-03:00'
- id: T-003
  title: Watchdog de heartbeat no servidor (agente parado = alerta)
  epic: E0
  status: done
  steps:
  - name: stale > 15min no /api/state
    done: true
    at: '2026-11-10T23:56:12-03:00'
  agent: orquestrador
- id: T-010
  title: Inventário .spec atual + plano de migração
  epic: E1
  status: doing
  steps:
  - name: ler specs antigas
    done: true
    at: '2026-11-10T23:55:50-03:00'
  - name: ler código
    done: false
    doing: true
  - name: plano de migração
    done: false
  agent: ag-spec
- id: T-011
  title: arch.yaml único (arquitetura do projeto inteiro)
  epic: E1
  status: todo
  steps: []
- id: T-012
  title: ADRs (decisões existentes + novas)
  epic: E1
  status: todo
  steps: []
- id: T-013
  title: UNITs (specs migradas + novas unidades)
  epic: E1
  status: todo
  steps: []
- id: T-014
  title: .spec/README.md (convenções e índice)
  epic: E1
  status: todo
  steps: []
- id: T-020
  title: Coleta de klines públicos (≥8 moedas, 1h/15m/4h/1d)
  epic: E2
  status: doing
  steps:
  - name: ler estratégia e specs
    done: false
    doing: true
  - name: downloader klines publicos
    done: false
  - name: baixar 10+ moedas 15m/1h/4h/1d
    done: false
  agent: ag-sim
- id: T-021
  title: Mock exchange + motor de simulação fiel à profit_gain
  epic: E2
  status: todo
  steps: []
- id: T-022
  title: Grade ≥50 variações (entrada × stop × stopwin) multi-moeda
  epic: E2
  status: todo
  steps: []
- id: T-023
  title: Relatório + recomendação de parâmetros
  epic: E2
  status: todo
  steps: []
- id: T-030
  title: Redesign templates/index.html
  epic: E3
  status: doing
  steps:
  - name: ler app.py e template
    done: true
    at: '2026-11-10T23:55:57-03:00'
  - name: inventariar eventos/IDs
    done: true
    at: '2026-11-10T23:55:57-03:00'
  - name: reescrever CSS/HTML
    done: false
    doing: true
  - name: ajustes pós-screenshot
    done: false
  agent: ag-ui
- id: T-031
  title: Verificação visual com dados mock
  epic: E3
  status: todo
  steps: []
- id: T-040
  title: Parametrizar profit_gain e aplicar calibração aprovada
  epic: E4
  status: todo
  steps: []
decisions:
- id: D-001
  question: O painel de referência (trycloudflare) devolve 403 para acesso automatizado; o layout foi desenhado
    a partir da sua descrição (agentes, tasks, steps, tempos). Está ok ou quer me passar print/HTML?
  options:
  - Ok assim
  - Mandar print para ajustar
  recommendation: Ok assim; ajusto com print depois
  status: pending
  blocking: false
  opened_at: '2026-11-10T23:50:00-03:00'
- id: D-002
  question: 'O trabalho migrou para D:\binance_trade (cópia integral, inclusive user.cfg sem leitura). A pasta em
    C:\...\Documents\binance_trade ficou defasada. Apagar a cópia de C: depois?'
  options:
  - 'Apagar C: após conferir'
  - Manter as duas
  recommendation: 'Conferir o D: e apagar o C: você mesmo'
  status: pending
  blocking: false
  opened_at: '2026-11-10T23:50:02-03:00'
- id: D-301
  question: Remover Tailwind CDN (sem versão) e usar CSS próprio + classes de compatibilidade para o HTML gerado
    pelo app.py nos modais?
  options:
  - 'A: remover e mapear classes'
  - 'B: manter Tailwind CDN'
  recommendation: A
  status: pending
  blocking: false
  opened_at: '2026-11-10T23:56:00-03:00'
events:
- at: '2026-11-10T23:49:14-03:00'
  who: orquestrador
  msg: T-001 ✓ modelo de dados
- at: '2026-11-10T23:49:14-03:00'
  who: orquestrador
  msg: T-001 ✓ CLI + lock atômico
- at: '2026-11-10T23:49:14-03:00'
  who: orquestrador
  msg: T-001 ✓ render md
- at: '2026-11-10T23:49:14-03:00'
  who: orquestrador
  msg: T-001 todo → doing
- at: '2026-11-10T23:49:29-03:00'
  who: orquestrador
  msg: status → active
- at: '2026-11-10T23:49:29-03:00'
  who: orquestrador
  msg: agente criado (Orquestrador)
- at: '2026-11-10T23:49:30-03:00'
  who: orquestrador
  msg: T-001 doing → done
- at: '2026-11-10T23:49:31-03:00'
  who: orquestrador
  msg: T-002 todo → doing
- at: '2026-11-10T23:50:00-03:00'
  who: orquestrador
  msg: 'decisão aberta D-001: O painel de referência (trycloudflare) devolve 403 para acesso automatizado; o layout
    foi desenhado a partir da sua descrição (agentes, tasks, steps, tempos). Está ok ou quer me passar print/HTML?'
- at: '2026-11-10T23:50:02-03:00'
  who: orquestrador
  msg: 'decisão aberta D-002: O trabalho migrou para D:\binance_trade (cópia integral, inclusive user.cfg sem leitura).
    A pasta em C:\...\Documents\binance_trade ficou defasada. Apagar a cópia de C: depois?'
- at: '2026-11-10T23:51:53-03:00'
  who: ag-spec
  msg: status → active
- at: '2026-11-10T23:51:53-03:00'
  who: ag-spec
  msg: agente criado (Arquiteto .spec)
- at: '2026-11-10T23:51:53-03:00'
  who: ag-spec
  msg: T-010 todo → doing
- at: '2026-11-10T23:52:06-03:00'
  who: ag-sim
  msg: status → active
- at: '2026-11-10T23:52:06-03:00'
  who: ag-sim
  msg: agente criado (Simulador)
- at: '2026-11-10T23:52:07-03:00'
  who: ag-ui
  msg: status → active
- at: '2026-11-10T23:52:07-03:00'
  who: ag-ui
  msg: agente criado (Designer do app)
- at: '2026-11-10T23:52:08-03:00'
  who: ag-sim
  msg: T-020 todo → doing
- at: '2026-11-10T23:52:10-03:00'
  who: ag-ui
  msg: T-030 todo → doing
- at: '2026-11-10T23:54:00-03:00'
  who: orquestrador
  msg: T-002 ✓ API /api/state
- at: '2026-11-10T23:54:00-03:00'
  who: orquestrador
  msg: T-002 ✓ layout agentes/tasks/steps
- at: '2026-11-10T23:54:00-03:00'
  who: orquestrador
  msg: T-002 ✓ timeline + decisões + tempos
- at: '2026-11-10T23:55:50-03:00'
  who: ag-spec
  msg: T-010 ✓ ler specs antigas
- at: '2026-11-10T23:55:57-03:00'
  who: ag-ui
  msg: T-030 ✓ ler app.py e template
- at: '2026-11-10T23:55:57-03:00'
  who: ag-ui
  msg: T-030 ✓ inventariar eventos/IDs
- at: '2026-11-10T23:56:00-03:00'
  who: ag-ui
  msg: 'decisão aberta D-301: Remover Tailwind CDN (sem versão) e usar CSS próprio + classes de compatibilidade
    para o HTML gerado pelo app.py nos modais?'
- at: '2026-11-10T23:56:10-03:00'
  who: orquestrador
  msg: T-002 ✓ auto-refresh + teste
- at: '2026-11-10T23:56:10-03:00'
  who: orquestrador
  msg: T-002 doing → done
- at: '2026-11-10T23:56:12-03:00'
  who: orquestrador
  msg: T-003 ✓ stale > 15min no /api/state
- at: '2026-11-10T23:56:12-03:00'
  who: orquestrador
  msg: T-003 todo → done
- at: '2026-11-10T23:56:15-03:00'
  who: orquestrador
  msg: 'commit v3.7.0: devpanel'
updated_at: '2026-11-10T23:56:15-03:00'
```
<!-- DATA:END -->
