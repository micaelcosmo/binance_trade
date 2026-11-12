# STATUS — acompanhamento de desenvolvimento

> Atualizado em **2026-11-11T22:36:45-03:00** · branch `check_strategies` · versão `v3.13.3` · 21/21 tasks concluídas.
> Fonte de verdade = bloco YAML no fim. Atualize via `python devpanel/track.py ...`. Painel: `python devpanel/server.py` → http://127.0.0.1:5055

## Agentes

| id | nome | status | task | step atual | heartbeat |
|---|---|---|---|---|---|
| orquestrador | Orquestrador | waiting | — | aguardando o Micael | 2026-11-11T22:36:45-03:00 |
| ag-spec | Arquiteto .spec | done | T-014 | concluído | 2026-11-11T00:18:26-03:00 |
| ag-sim | Simulador | done | T-024 | concluído (T-024) | 2026-11-11T01:14:20-03:00 |
| ag-ui | Designer do app | done | T-031 | concluído | 2026-11-11T00:36:13-03:00 |
| ag-calib | Calibrador | done | T-040 | concluído T-040 | 2026-11-11T00:53:50-03:00 |

## Épicos

| id | P | épico | status |
|---|---|---|---|
| E0 | 0 | Painel de acompanhamento do desenvolvimento | done |
| E1 | 1 | Reestruturar .spec (README, arch.yaml, ADRs, UNITs) | done |
| E2 | 1 | Simulação ≥50 variações (mock) p/ calibrar previsão, entrada, stoploss/stopwin | done |
| E3 | 2 | Repaginar página do app (amigável/futurista, sóbria) | done |
| E4 | 2 | Aplicar calibração na profit_gain (após simulação) | review |

## Tasks

| id | épico | task | status | agente | steps |
|---|---|---|---|---|---|
| T-001 | E0 | CLI track.py (STATUS/TEMPO com lock) | done | orquestrador | 3/3 |
| T-002 | E0 | Servidor + UI do painel de dev | done | orquestrador | 4/4 |
| T-003 | E0 | Watchdog de heartbeat no servidor (agente parado = alerta) | done | orquestrador | 1/1 |
| T-010 | E1 | Inventário .spec atual + plano de migração | done | ag-spec | 3/3 |
| T-011 | E1 | arch.yaml único (arquitetura do projeto inteiro) | done | ag-spec | 2/2 |
| T-012 | E1 | ADRs (decisões existentes + novas) | done | ag-spec | 2/2 |
| T-013 | E1 | UNITs (specs migradas + novas unidades) | done | ag-spec | 2/3 |
| T-014 | E1 | .spec/README.md (convenções e índice) | done | ag-spec | 2/2 |
| T-020 | E2 | Coleta de klines públicos (≥8 moedas, 1h/15m/4h/1d) | done | ag-sim | 3/3 |
| T-021 | E2 | Mock exchange + motor de simulação fiel à profit_gain | done | ag-sim | 5/5 |
| T-022 | E2 | Grade ≥50 variações (entrada × stop × stopwin) multi-moeda | done | ag-sim | 4/4 |
| T-023 | E2 | Relatório + recomendação de parâmetros | done | ag-sim | 3/3 |
| T-030 | E3 | Redesign templates/index.html | done | ag-ui | 4/4 |
| T-031 | E3 | Verificação visual com dados mock | done | ag-ui | 3/3 |
| T-040 | E4 | Aplicar gate SMA200 diária (único ajuste robusto da sim-001), configurável | done | ag-calib | 5/5 |
| T-041 | E4 | Parametrizar profit_gain (defaults atuais) + fix latência do stop e fill real | done | ag-calib | 6/6 |
| T-004 | E0 | Painel: evitar re-render a cada 4s (clique/scroll estáveis) + verificação visual | done | orquestrador | 2/2 |
| T-024 | E2 | sim-002: variações estruturais (R:R, confirmação, custos) | done | ag-sim | 4/4 |
| T-005 | E0 | Painel com a cara do modelo pedido (ao vivo, Agora, fluxo n8n, agentes, pendências) | done | orquestrador | 6/6 |
| T-006 | E0 | Painel: tile/card de UNITs reais e 'tudo concluído' no progresso | done | orquestrador | 3/3 |
| T-007 | E0 | Fluxo: faixa com UNITs sem task, cor pelo status da spec | done | orquestrador | 3/3 |

## Decisões para o Micael

| id | bloqueante | pergunta | opções | status | resposta |
|---|---|---|---|---|---|
| D-001 | não | O painel de referência (trycloudflare) devolve 403 para acesso automatizado; o layout foi desenhado a partir da sua descrição (agentes, tasks, steps, tempos). Está ok ou quer me passar print/HTML? | Ok assim / Mandar print para ajustar | pending | — |
| D-002 | não | O trabalho migrou para D:\binance_trade (cópia integral, inclusive user.cfg sem leitura). A pasta em C:\...\Documents\binance_trade ficou defasada. Apagar a cópia de C: depois? | Apagar C: após conferir / Manter as duas | pending | — |
| D-301 | não | Remover Tailwind CDN (sem versão) e usar CSS próprio + classes de compatibilidade para o HTML gerado pelo app.py nos modais? | A: remover e mapear classes / B: manter Tailwind CDN | pending | — |
| D-101 | não | update_pending.flag só é consumida pelo painel.py (deprecado); no modo web/Docker o botão 'Atualizar bot' não faz nada. Como tratar? | Portar git pull para app.py (escopo system:update, UNIT-001) / Remover o botão até a UNIT-001 / Manter como está | pending | — |
| D-102 | não | A suíte pytest não coleta no .venv de D: (falta sqlitedict: binance_trade_bot/__init__ importa backtest). Instalar requirements completos no .venv de D: ou isolar os imports do pacote? | Instalar requirements no .venv D: / Tornar __init__ do pacote leve (imports tardios) | answered | Resolvido pelo orquestrador: venv313 (Py 3.13 + requirements-docker.lock + unicorn 2.13.0) → 17 passed |
| D-201 | não | Simulação: profit_gain não paga custos (BASE −0,30%/trade; melhor variação ≈ break-even e frágil). O que fazer com o live? | A: IA em shadow-mode medindo acerto antes de all-in / B: operar com gate SMA200 e tamanho reduzido / C: pausar live até revisão estrutural | pending | — |
| D-202 | não | Edge bruto ≈ custo de round-trip. Ativar desconto de taxa em BNB? | A: ativar BNB (0,075%/lado) / B: manter 0,1% | pending | — |
| D-203 | não | Clamp do stop do BTC (6–10,5%) parece largo; BTC foi a pior moeda na REC | A: manter / B: igualar alts 4–7% / C: 3–6% | pending | — |
| D-204 | não | Relação alvo ~+1,3% vs stop 4–7% exige >79% de acerto; revisar tese/all-in em nova spec? | A: abrir spec de revisão estrutural / B: não | pending | — |
| D-401 | não | UNIT-006 item 4: com USDT < $5 a recuperação de estado assume a 1ª moeda da carteira com valor >= $5, mesmo uma que o bot nunca comprou (e passa a vendê-la pelos stops). Corrigir? | A: só assumir moeda registrada no profit_gain_state.json (current coin/qty salvos) / B: assumir só se houver compra recente via get_my_trades / C: manter como está | pending | — |
| D-402 | não | UNIT-006 item 5: Tribunal de Swap exige >= 4 candidatas aprovadas ao mesmo tempo, então quase nunca convoca (e adia +45 min). Qual o mínimo? | A: 1 candidata / B: 2 candidatas / C: manter 4 | pending | — |
| D-403 | não | UNIT-006 item 6: durante o cooldown do motor (ai_cooldown_until) a mineração pesada de klines continua rodando a cada scout; só a chamada à IA é poupada. Pular a mineração no cooldown quando fora de operação? | A: pular mineração em cooldown (manter só heartbeat/UI) / B: minerar em intervalo reduzido (ex. a cada N scouts) para manter hot/cold da UI / C: manter | pending | — |
| D-404 | não | UNIT-006 item 7: daily_profit_pct soma % por trade (não compõe, ignora capital). Meta de 5% e hibernação disparam sobre número aproximado. Trocar? | A: retorno real do dia = equity atual / equity na 1ª operação do dia - 1 / B: produto composto (1+r1)(1+r2)...-1 / C: manter soma | pending | — |
| D-405 | não | UNIT-006 item 8: entrada all-in (99% do saldo). Agora configurável via [profit_gain] entry_balance_fraction (default 0.99, comportamento inalterado). Mudar o default? | A: manter 0.99 / B: dimensionar por risco (ex. risco 1-2% do capital / stop ATR) / C: fração fixa menor (ex. 0.5) | pending | — |
| D-406 | não | UNIT-006 item 9: maximum_hold_time_seconds = 7200 é definido e nunca usado (não há timeout de posição). O que fazer? | A: remover o atributo morto / B: implementar timeout de posição (venda após X h) parametrizado / C: manter | pending | — |
| D-407 | não | Gate SMA200 diário ligado por padrão (regime_filter_sma200=true). Mantém? | Manter ligado / Desligar por padrão | pending | — |
| D-210 | não | sim-002: entrada limit −0,6% válida 1h (+taxa BNB) é a única melhora relevante (carteira IS +0,05%/trade), mas depende do modelo de fill. Implementar? | A: implementar em shadow/paper e medir fill real / B: não implementar | pending | — |
| D-211 | não | 190 configurações (sim-001+002) sem edge líquido robusto na profit_gain; problema está no sinal (edge bruto ≈ custo). O que fazer? | A: live com tamanho mínimo + IA em shadow-mode / B: pausar live / C: spec de nova tese de entrada | pending | — |
| D-008 | não | Ligar o hook do feed Agora (.claude/settings.json → devpanel/registrar_atividade.py em PreToolUse/PostToolUse/UserPromptSubmit/Stop/SubagentStop)? Só vale abrindo o Claude Code em D:\binance_trade. | Ligar / Não ligar | pending | — |

## Últimos eventos

- `2026-11-11T22:36:44-03:00` **orquestrador** — commit v3.13.3: UNITs sem task no fluxo do plano
- `2026-11-11T22:36:43-03:00` **orquestrador** — T-007 doing → done
- `2026-11-11T22:36:43-03:00` **orquestrador** — T-007 todo → doing
- `2026-11-11T22:36:43-03:00` **orquestrador** — T-007 ✓ print tema escuro
- `2026-11-11T22:36:43-03:00` **orquestrador** — T-007 ✓ faixa no canvas
- `2026-11-11T22:36:43-03:00` **orquestrador** — T-007 ✓ coletor backlog
- `2026-11-11T22:33:36-03:00` **orquestrador** — commit v3.13.2: UNITs reais no painel; app web no ar em :5000
- `2026-11-11T22:33:35-03:00` **orquestrador** — T-006 doing → done
- `2026-11-11T22:33:35-03:00` **orquestrador** — T-006 todo → doing
- `2026-11-11T22:33:35-03:00` **orquestrador** — T-006 ✓ tile + card UNITs
- `2026-11-11T22:33:35-03:00` **orquestrador** — T-006 ✓ coletor unitSpecs
- `2026-11-11T22:33:35-03:00` **orquestrador** — T-006 ✓ UNIT-011 atualizada
- `2026-11-11T22:22:22-03:00` **orquestrador** — status → waiting
- `2026-11-11T22:22:21-03:00` **orquestrador** — commit v3.13.0: painel refeito com a cara do modelo
- `2026-11-11T22:22:20-03:00` **orquestrador** — decisão aberta D-008: Ligar o hook do feed Agora (.claude/settings.json → devpanel/registrar_atividade.py em PreToolUse/PostToolUse/UserPromptSubmit/Stop/SubagentStop)? Só vale abrindo o Claude Code em D:\binance_trade.

<!-- DATA:BEGIN (gerado por devpanel/track.py — não edite à mão) -->
```yaml
project:
  name: binance_trade
  branch: check_strategies
  version: v3.13.3
  goal: Painel de dev (P0), .spec ADR/UNIT/arch.yaml, simulação ≥50 variações p/ calibrar entrada/stop, repaginar
    app
  repo: D:\binance_trade
  session_started_at: '2026-11-10T23:49:02-03:00'
  session_deadline: '2026-11-11T04:48:59-03:00'
agents:
- id: orquestrador
  name: Orquestrador
  role: Planeja, cria/encerra agentes, commita
  task: —
  step: aguardando o Micael
  kind: orchestrator
  status: waiting
  heartbeat: '2026-11-11T22:36:45-03:00'
  step_log:
  - at: '2026-11-10T23:54:05-03:00'
    step: testando painel
  - at: '2026-11-11T00:10:41-03:00'
    step: supervisionando ag-spec, ag-sim, ag-ui; venv 3.13 p/ suíte completa
  - at: '2026-11-11T00:10:56-03:00'
    step: aguardando conclusão dos workers (acorda por notificação)
  - at: '2026-11-11T00:27:10-03:00'
    step: revisando e commitando E1
  - at: '2026-11-11T00:31:19-03:00'
    step: aguardando ag-sim, ag-ui, ag-calib
  - at: '2026-11-11T00:37:08-03:00'
    step: commit E3 (UI do app)
  - at: '2026-11-11T00:40:01-03:00'
    step: aguardando ag-sim (grade estágio 2) e ag-calib
  - at: '2026-11-11T00:43:29-03:00'
    step: commit E2 (simulação)
  - at: '2026-11-11T00:43:48-03:00'
    step: aguardando ag-calib (T-041) para encadear T-040
  - at: '2026-11-11T00:44:24-03:00'
    step: commit T-041
  - at: '2026-11-11T00:44:56-03:00'
    step: aguardando ag-calib (T-040 SMA200) e ag-sim (T-024 sim-002)
  - at: '2026-11-11T00:55:53-03:00'
    step: commit T-040
  - at: '2026-11-11T00:57:31-03:00'
    step: aguardando ag-sim (sim-002)
  - at: '2026-11-11T01:15:22-03:00'
    step: commit sim-002
  - at: '2026-11-11T01:15:48-03:00'
    step: fim do fluxo autônomo — aguardando decisões do Micael
  - at: '2026-11-11T22:15:59-03:00'
    step: coletor estado.json
  - at: '2026-11-11T22:21:11-03:00'
    step: verificação visual do painel novo
  - at: '2026-11-11T22:22:22-03:00'
    step: painel refeito; aguardando o Micael
  - at: '2026-11-11T22:33:37-03:00'
    step: app web :5000 e painel :5055 no ar
  - at: '2026-11-11T22:36:45-03:00'
    step: aguardando o Micael
- id: ag-spec
  name: Arquiteto .spec
  role: Reestrutura .spec
  task: T-014
  step: concluído
  kind: worker
  status: done
  heartbeat: '2026-11-11T00:18:26-03:00'
  step_log:
  - at: '2026-11-10T23:51:53-03:00'
    step: inventário
  - at: '2026-11-10T23:55:52-03:00'
    step: lendo código
  - at: '2026-11-11T00:03:29-03:00'
    step: escrevendo arch.yaml
  - at: '2026-11-11T00:07:05-03:00'
    step: ADRs migradas
  - at: '2026-11-11T00:10:27-03:00'
    step: ADRs novas (0010-0013)
  - at: '2026-11-11T00:11:21-03:00'
    step: migrando specs para UNITs
  - at: '2026-11-11T00:13:58-03:00'
    step: UNITs novas E0-E4
  - at: '2026-11-11T00:16:19-03:00'
    step: README.md
  - at: '2026-11-11T00:18:26-03:00'
    step: concluído
- id: ag-sim
  name: Simulador
  role: Mock exchange + backtests de calibração
  task: T-024
  step: concluído (T-024)
  kind: worker
  status: done
  heartbeat: '2026-11-11T01:14:20-03:00'
  step_log:
  - at: '2026-11-11T00:45:06-03:00'
    step: estendendo engine (breakeven, parcial, confirmação, maker)
  - at: '2026-11-11T00:51:28-03:00'
    step: engine estendido, 24 testes ok; montando grade sim-002
  - at: '2026-11-11T00:54:47-03:00'
    step: 'sim-002 stage1: variação 5/53 (91s)'
  - at: '2026-11-11T00:55:22-03:00'
    step: 'sim-002 stage1: variação 10/53 (114s)'
  - at: '2026-11-11T00:57:40-03:00'
    step: 'sim-002 stage1: variação 15/53 (250s)'
  - at: '2026-11-11T00:59:25-03:00'
    step: 'sim-002 stage1: variação 20/53 (364s)'
  - at: '2026-11-11T01:01:29-03:00'
    step: 'sim-002 stage1: variação 25/53 (485s)'
  - at: '2026-11-11T01:03:07-03:00'
    step: 'sim-002 stage1: variação 30/53 (587s)'
  - at: '2026-11-11T01:04:17-03:00'
    step: 'sim-002 stage1: variação 35/53 (659s)'
  - at: '2026-11-11T01:05:35-03:00'
    step: 'sim-002 stage1: variação 40/53 (742s)'
  - at: '2026-11-11T01:05:51-03:00'
    step: 'sim-002 stage1: variação 45/53 (759s)'
  - at: '2026-11-11T01:07:15-03:00'
    step: 'sim-002 stage1: variação 50/53 (842s)'
  - at: '2026-11-11T01:07:58-03:00'
    step: 'sim-002 stage1: variação 53/53 (885s)'
  - at: '2026-11-11T01:09:37-03:00'
    step: 'sim-002 check: variação 5/28 (984s)'
  - at: '2026-11-11T01:09:54-03:00'
    step: 'sim-002 check: variação 10/28 (1001s)'
  - at: '2026-11-11T01:10:10-03:00'
    step: 'sim-002 check: variação 15/28 (1018s)'
  - at: '2026-11-11T01:10:29-03:00'
    step: 'sim-002 check: variação 20/28 (1036s)'
  - at: '2026-11-11T01:10:53-03:00'
    step: 'sim-002 check: variação 25/28 (1060s)'
  - at: '2026-11-11T01:11:09-03:00'
    step: 'sim-002 check: variação 28/28 (1075s)'
  - at: '2026-11-11T01:14:20-03:00'
    step: concluído (T-024)
- id: ag-ui
  name: Designer do app
  role: Repagina templates/index.html
  task: T-031
  step: concluído
  kind: worker
  status: done
  heartbeat: '2026-11-11T00:36:13-03:00'
  step_log:
  - at: '2026-11-10T23:52:07-03:00'
    step: lendo template atual
  - at: '2026-11-10T23:55:58-03:00'
    step: reescrevendo template (CSS próprio, sem Tailwind runtime)
  - at: '2026-11-10T23:58:42-03:00'
    step: 'montando harness mock + instalando playwright no D:'
  - at: '2026-11-11T00:04:51-03:00'
    step: aguardando download do Chromium; harness e diff de paridade prontos
  - at: '2026-11-11T00:28:40-03:00'
    step: revisando screenshots após ajustes (prefixo veredito, emoji status, tag do gráfico)
  - at: '2026-11-11T00:36:13-03:00'
    step: concluído
- id: ag-calib
  name: Calibrador
  role: Parametriza profit_gain + correções de stop
  task: T-040
  step: concluído T-040
  kind: worker
  status: done
  heartbeat: '2026-11-11T00:53:50-03:00'
  step_log:
  - at: '2026-11-11T00:31:17-03:00'
    step: lendo estratégia
  - at: '2026-11-11T00:36:10-03:00'
    step: ligando params na estratégia
  - at: '2026-11-11T00:39:42-03:00'
    step: escrevendo testes mock
  - at: '2026-11-11T00:43:19-03:00'
    step: concluído
  - at: '2026-11-11T00:44:47-03:00'
    step: lendo sim-001 e engine
  - at: '2026-11-11T00:47:24-03:00'
    step: testes do gate SMA200
  - at: '2026-11-11T00:53:50-03:00'
    step: concluído T-040
epics:
- id: E0
  title: Painel de acompanhamento do desenvolvimento
  status: done
  priority: 0
- id: E1
  title: Reestruturar .spec (README, arch.yaml, ADRs, UNITs)
  priority: 1
  status: done
- id: E2
  title: Simulação ≥50 variações (mock) p/ calibrar previsão, entrada, stoploss/stopwin
  priority: 1
  status: done
- id: E3
  title: Repaginar página do app (amigável/futurista, sóbria)
  priority: 2
  status: done
- id: E4
  title: Aplicar calibração na profit_gain (após simulação)
  priority: 2
  status: review
  note: Gate SMA200 aplicado; aguarda D-407 e D-201
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
  status: done
  steps:
  - name: ler specs antigas
    done: true
    at: '2026-11-10T23:55:50-03:00'
  - name: ler código
    done: true
    at: '2026-11-11T00:03:18-03:00'
  - name: plano de migração
    done: true
    at: '2026-11-11T00:03:18-03:00'
  agent: ag-spec
  note: 'plano: 13 ADRs, 12 UNITs, arch.yaml; specs migradas integralmente'
- id: T-011
  title: arch.yaml único (arquitetura do projeto inteiro)
  epic: E1
  status: done
  steps:
  - name: rascunho arch.yaml
    done: true
    at: '2026-11-11T00:06:32-03:00'
  - name: validar yaml.safe_load
    done: true
    at: '2026-11-11T00:06:32-03:00'
  agent: ag-spec
  deliverable: .spec/arch.yaml
- id: T-012
  title: ADRs (decisões existentes + novas)
  epic: E1
  status: done
  steps:
  - name: ADRs migradas (0001-0009)
    done: true
    at: '2026-11-11T00:10:25-03:00'
  - name: ADRs novas (0010-0013)
    done: true
    at: '2026-11-11T00:11:16-03:00'
  agent: ag-spec
  deliverable: .spec/adr/ADR-0001..0013
- id: T-013
  title: UNITs (specs migradas + novas unidades)
  epic: E1
  status: done
  steps:
  - name: migrar specs 001-004 + refactor 005
    done: true
    at: '2026-11-11T00:13:56-03:00'
  - name: migrar strategies (006-007)
    done: false
  - name: UNITs novas E0-E4 (008-012)
    done: true
    at: '2026-11-11T00:16:15-03:00'
  agent: ag-spec
  deliverable: .spec/units/UNIT-001..012
- id: T-014
  title: .spec/README.md (convenções e índice)
  epic: E1
  status: done
  steps:
  - name: escrever README
    done: true
    at: '2026-11-11T00:17:21-03:00'
  - name: remover pastas antigas + validar
    done: true
    at: '2026-11-11T00:18:19-03:00'
  agent: ag-spec
  deliverable: .spec/README.md
- id: T-020
  title: Coleta de klines públicos (≥8 moedas, 1h/15m/4h/1d)
  epic: E2
  status: done
  steps:
  - name: ler estratégia e specs
    done: true
    at: '2026-11-10T23:58:12-03:00'
  - name: downloader klines publicos
    done: true
    at: '2026-11-10T23:58:13-03:00'
  - name: baixar 10+ moedas 15m/1h/4h/1d
    done: true
    at: '2026-11-11T00:15:09-03:00'
  agent: ag-sim
- id: T-021
  title: Mock exchange + motor de simulação fiel à profit_gain
  epic: E2
  status: done
  steps:
  - name: mock_exchange (taxa/slippage/fills)
    done: true
    at: '2026-11-11T00:03:34-03:00'
  - name: indicadores pandas/numpy sem look-ahead
    done: true
    at: '2026-11-11T00:03:35-03:00'
  - name: Porteiro + oráculo mock
    done: true
    at: '2026-11-11T00:03:37-03:00'
  - name: saídas intra-vela conservadoras + latência
    done: true
    at: '2026-11-11T00:05:13-03:00'
  - name: testes pytest
    done: true
    at: '2026-11-11T00:05:14-03:00'
  agent: ag-sim
- id: T-022
  title: Grade ≥50 variações (entrada × stop × stopwin) multi-moeda
  epic: E2
  status: done
  steps:
  - name: montar grade estágio 1 (69 variações one-at-a-time)
    done: true
    at: '2026-11-11T00:13:51-03:00'
  - name: rodar estágio 1 em 11 moedas
    done: true
    at: '2026-11-11T00:36:31-03:00'
  - name: 'estágio 2: combinações dos melhores IS'
    done: true
    at: '2026-11-11T00:40:45-03:00'
  - name: 'checagens: latência (close) e slippage 0,2%'
    done: true
    at: '2026-11-11T00:40:46-03:00'
  agent: ag-sim
- id: T-023
  title: Relatório + recomendação de parâmetros
  epic: E2
  status: done
  steps:
  - name: análise por trimestre e moeda
    done: true
    at: '2026-11-11T00:40:49-03:00'
  - name: escrever sim-001-calibracao.md
    done: true
    at: '2026-11-11T00:42:20-03:00'
  - name: registrar decisões do Micael
    done: true
    at: '2026-11-11T00:42:26-03:00'
  agent: ag-sim
- id: T-030
  title: Redesign templates/index.html
  epic: E3
  status: done
  steps:
  - name: ler app.py e template
    done: true
    at: '2026-11-10T23:55:57-03:00'
  - name: inventariar eventos/IDs
    done: true
    at: '2026-11-10T23:55:57-03:00'
  - name: reescrever CSS/HTML
    done: true
    at: '2026-11-10T23:58:44-03:00'
  - name: ajustes pós-screenshot
    done: true
    at: '2026-11-11T00:36:11-03:00'
  agent: ag-ui
- id: T-031
  title: Verificação visual com dados mock
  epic: E3
  status: done
  steps:
  - name: harness Flask mock
    done: true
    at: '2026-11-11T00:04:52-03:00'
  - name: screenshots desktop/mobile
    done: true
    at: '2026-11-11T00:36:12-03:00'
  - name: diff de paridade IDs/eventos
    done: true
    at: '2026-11-11T00:04:52-03:00'
  agent: ag-ui
- id: T-040
  title: Aplicar gate SMA200 diária (único ajuste robusto da sim-001), configurável
  epic: E4
  status: done
  steps:
  - name: Params regime_filter_sma200/regime_sma_period
    done: true
    at: '2026-11-11T00:47:22-03:00'
  - name: Gate SMA200 diário com cache 24h (Porteiro + Tribunal)
    done: true
    at: '2026-11-11T00:47:22-03:00'
  - name: Testes mock + suíte
    done: true
    at: '2026-11-11T00:53:27-03:00'
  - name: Atualizar arch.yaml e UNIT-012
    done: true
    at: '2026-11-11T00:53:27-03:00'
  - name: Decisão D-407
    done: true
    at: '2026-11-11T00:53:27-03:00'
  note: Trailing 0,2 / stop×3 NÃO aplicados (marginais, quebram com latência/slippage). Aguarda fim do T-041 (mesmo
    arquivo).
  agent: ag-calib
- id: T-041
  title: Parametrizar profit_gain (defaults atuais) + fix latência do stop e fill real
  epic: E4
  agent: ag-calib
  status: done
  steps:
  - name: Extrair ProfitGainParams
    done: true
    at: '2026-11-11T00:36:09-03:00'
  - name: Carregar [profit_gain] no config.py + user.cfg.exemple
    done: true
    at: '2026-11-11T00:39:41-03:00'
  - name: Fix stop antes da mineração
    done: true
    at: '2026-11-11T00:39:41-03:00'
  - name: Fix preço de compra = fill médio
    done: true
    at: '2026-11-11T00:39:41-03:00'
  - name: Testes mock + suíte
    done: true
    at: '2026-11-11T00:42:49-03:00'
  - name: Registrar decisões D-4xx (itens 4-9)
    done: true
    at: '2026-11-11T00:43:18-03:00'
- id: T-004
  title: 'Painel: evitar re-render a cada 4s (clique/scroll estáveis) + verificação visual'
  epic: E0
  agent: orquestrador
  status: done
  steps:
  - name: re-render só com dados novos
    done: true
    at: '2026-11-11T00:39:50-03:00'
  - name: screenshots desktop/mobile
    done: true
    at: '2026-11-11T00:39:50-03:00'
- id: T-024
  title: 'sim-002: variações estruturais (R:R, confirmação, custos)'
  epic: E2
  agent: ag-sim
  status: done
  steps:
  - name: 'estender engine: stop fixo, breakeven, parcial, time-stop, confirmação, maker'
    done: true
    at: '2026-11-11T00:51:13-03:00'
  - name: testes novos
    done: true
    at: '2026-11-11T00:51:15-03:00'
  - name: grade estrutural >=50 var
    done: true
    at: '2026-11-11T01:14:16-03:00'
  - name: relatório sim-002
    done: true
    at: '2026-11-11T01:14:17-03:00'
- id: T-005
  title: Painel com a cara do modelo pedido (ao vivo, Agora, fluxo n8n, agentes, pendências)
  epic: E0
  agent: orquestrador
  status: done
  steps:
  - name: estudar o modelo (layout + contrato)
    done: true
    at: '2026-11-11T22:15:58-03:00'
  - name: coletor estado.json com nossas fontes
    done: true
    at: '2026-11-11T22:21:11-03:00'
  - name: página adaptada
    done: true
    at: '2026-11-11T22:21:11-03:00'
  - name: hook do feed Agora
    done: true
    at: '2026-11-11T22:22:20-03:00'
  - name: testes testes/sim no card
    done: true
    at: '2026-11-11T22:21:11-03:00'
  - name: verificação visual 1440/390
    done: true
    at: '2026-11-11T22:22:20-03:00'
  note: hook pronto; ligar em .claude/settings.json aguarda aprovação
- id: T-006
  title: 'Painel: tile/card de UNITs reais e ''tudo concluído'' no progresso'
  epic: E0
  agent: orquestrador
  status: done
  steps:
  - name: UNIT-011 atualizada
    done: true
    at: '2026-11-11T22:33:35-03:00'
  - name: coletor unitSpecs
    done: true
    at: '2026-11-11T22:33:35-03:00'
  - name: tile + card UNITs
    done: true
    at: '2026-11-11T22:33:35-03:00'
- id: T-007
  title: 'Fluxo: faixa com UNITs sem task, cor pelo status da spec'
  epic: E0
  agent: orquestrador
  status: done
  steps:
  - name: coletor backlog
    done: true
    at: '2026-11-11T22:36:43-03:00'
  - name: faixa no canvas
    done: true
    at: '2026-11-11T22:36:43-03:00'
  - name: print tema escuro
    done: true
    at: '2026-11-11T22:36:43-03:00'
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
- id: D-101
  question: update_pending.flag só é consumida pelo painel.py (deprecado); no modo web/Docker o botão 'Atualizar
    bot' não faz nada. Como tratar?
  options:
  - Portar git pull para app.py (escopo system:update, UNIT-001)
  - Remover o botão até a UNIT-001
  - Manter como está
  recommendation: Portar para app.py junto com a UNIT-001 (auth antes de expor git pull)
  status: pending
  blocking: false
  opened_at: '2026-11-11T00:18:15-03:00'
- id: D-102
  question: 'A suíte pytest não coleta no .venv de D: (falta sqlitedict: binance_trade_bot/__init__ importa backtest).
    Instalar requirements completos no .venv de D: ou isolar os imports do pacote?'
  options:
  - 'Instalar requirements no .venv D:'
  - Tornar __init__ do pacote leve (imports tardios)
  recommendation: Orquestrador criou D:\binance_trade_work\venv313 (Python 3.13 = Docker) com requirements-docker.lock;
    o .venv 3.14 não compila unicorn
  status: answered
  blocking: false
  opened_at: '2026-11-11T00:18:17-03:00'
  answer: 'Resolvido pelo orquestrador: venv313 (Py 3.13 + requirements-docker.lock + unicorn 2.13.0) → 17 passed'
- id: D-201
  question: 'Simulação: profit_gain não paga custos (BASE −0,30%/trade; melhor variação ≈ break-even e frágil).
    O que fazer com o live?'
  options:
  - 'A: IA em shadow-mode medindo acerto antes de all-in'
  - 'B: operar com gate SMA200 e tamanho reduzido'
  - 'C: pausar live até revisão estrutural'
  recommendation: A + B com tamanho reduzido
  status: pending
  blocking: false
  opened_at: '2026-11-11T00:42:22-03:00'
- id: D-202
  question: Edge bruto ≈ custo de round-trip. Ativar desconto de taxa em BNB?
  options:
  - 'A: ativar BNB (0,075%/lado)'
  - 'B: manter 0,1%'
  recommendation: A
  status: pending
  blocking: false
  opened_at: '2026-11-11T00:42:23-03:00'
- id: D-203
  question: Clamp do stop do BTC (6–10,5%) parece largo; BTC foi a pior moeda na REC
  options:
  - 'A: manter'
  - 'B: igualar alts 4–7%'
  - 'C: 3–6%'
  recommendation: A até rodada específica (efeito pooled neutro)
  status: pending
  blocking: false
  opened_at: '2026-11-11T00:42:24-03:00'
- id: D-204
  question: Relação alvo ~+1,3% vs stop 4–7% exige >79% de acerto; revisar tese/all-in em nova spec?
  options:
  - 'A: abrir spec de revisão estrutural'
  - 'B: não'
  recommendation: A
  status: pending
  blocking: false
  opened_at: '2026-11-11T00:42:25-03:00'
- id: D-401
  question: 'UNIT-006 item 4: com USDT < $5 a recuperação de estado assume a 1ª moeda da carteira com valor >= $5,
    mesmo uma que o bot nunca comprou (e passa a vendê-la pelos stops). Corrigir?'
  options:
  - 'A: só assumir moeda registrada no profit_gain_state.json (current coin/qty salvos)'
  - 'B: assumir só se houver compra recente via get_my_trades'
  - 'C: manter como está'
  recommendation: 'A (com B como fallback): persistir current_operation_coin no estado e só recuperar essa moeda;
    demais saldos ficam intocados e logados'
  task: T-041
  status: pending
  blocking: false
  opened_at: '2026-11-11T00:43:14-03:00'
- id: D-402
  question: 'UNIT-006 item 5: Tribunal de Swap exige >= 4 candidatas aprovadas ao mesmo tempo, então quase nunca
    convoca (e adia +45 min). Qual o mínimo?'
  options:
  - 'A: 1 candidata'
  - 'B: 2 candidatas'
  - 'C: manter 4'
  recommendation: 'Decidir via simulação (UNIT-010): já parametrizado como swap_min_candidates (default 4); sugerir
    A ou B só se a grade mostrar ganho'
  task: T-041
  status: pending
  blocking: false
  opened_at: '2026-11-11T00:43:15-03:00'
- id: D-403
  question: 'UNIT-006 item 6: durante o cooldown do motor (ai_cooldown_until) a mineração pesada de klines continua
    rodando a cada scout; só a chamada à IA é poupada. Pular a mineração no cooldown quando fora de operação?'
  options:
  - 'A: pular mineração em cooldown (manter só heartbeat/UI)'
  - 'B: minerar em intervalo reduzido (ex. a cada N scouts) para manter hot/cold da UI'
  - 'C: manter'
  recommendation: 'B: preserva a UI (hot/cold, dossiê) e corta ~90% das chamadas; com posição aberta o stop já não
    depende da mineração (fix T-041)'
  task: T-041
  status: pending
  blocking: false
  opened_at: '2026-11-11T00:43:15-03:00'
- id: D-404
  question: 'UNIT-006 item 7: daily_profit_pct soma % por trade (não compõe, ignora capital). Meta de 5% e hibernação
    disparam sobre número aproximado. Trocar?'
  options:
  - 'A: retorno real do dia = equity atual / equity na 1ª operação do dia - 1'
  - 'B: produto composto (1+r1)(1+r2)...-1'
  - 'C: manter soma'
  recommendation: B (simples, sem depender de saldo/depósitos) e exibir A como informativo na UI
  task: T-041
  status: pending
  blocking: false
  opened_at: '2026-11-11T00:43:15-03:00'
- id: D-405
  question: 'UNIT-006 item 8: entrada all-in (99% do saldo). Agora configurável via [profit_gain] entry_balance_fraction
    (default 0.99, comportamento inalterado). Mudar o default?'
  options:
  - 'A: manter 0.99'
  - 'B: dimensionar por risco (ex. risco 1-2% do capital / stop ATR)'
  - 'C: fração fixa menor (ex. 0.5)'
  recommendation: A até a simulação (UNIT-010) medir B; B é o padrão de mercado para limitar perda por trade a 1-2%
    do capital
  task: T-041
  status: pending
  blocking: false
  opened_at: '2026-11-11T00:43:16-03:00'
- id: D-406
  question: 'UNIT-006 item 9: maximum_hold_time_seconds = 7200 é definido e nunca usado (não há timeout de posição).
    O que fazer?'
  options:
  - 'A: remover o atributo morto'
  - 'B: implementar timeout de posição (venda após X h) parametrizado'
  - 'C: manter'
  recommendation: A agora (não muda comportamento); B só se a simulação mostrar ganho, como UNIT própria
  task: T-041
  status: pending
  blocking: false
  opened_at: '2026-11-11T00:43:17-03:00'
- id: D-407
  question: Gate SMA200 diário ligado por padrão (regime_filter_sma200=true). Mantém?
  options:
  - Manter ligado
  - Desligar por padrão
  recommendation: 'Manter ligado (sim-001: único ganho robusto IS e OOS)'
  task: T-040
  status: pending
  blocking: false
  opened_at: '2026-11-11T00:53:25-03:00'
- id: D-210
  question: 'sim-002: entrada limit −0,6% válida 1h (+taxa BNB) é a única melhora relevante (carteira IS +0,05%/trade),
    mas depende do modelo de fill. Implementar?'
  options:
  - 'A: implementar em shadow/paper e medir fill real'
  - 'B: não implementar'
  recommendation: A (só paper)
  status: pending
  blocking: false
  opened_at: '2026-11-11T01:14:14-03:00'
- id: D-211
  question: 190 configurações (sim-001+002) sem edge líquido robusto na profit_gain; problema está no sinal (edge
    bruto ≈ custo). O que fazer?
  options:
  - 'A: live com tamanho mínimo + IA em shadow-mode'
  - 'B: pausar live'
  - 'C: spec de nova tese de entrada'
  recommendation: A + C
  status: pending
  blocking: false
  opened_at: '2026-11-11T01:14:16-03:00'
- id: D-008
  question: Ligar o hook do feed Agora (.claude/settings.json → devpanel/registrar_atividade.py em PreToolUse/PostToolUse/UserPromptSubmit/Stop/SubagentStop)?
    Só vale abrindo o Claude Code em D:\binance_trade.
  options:
  - Ligar
  - Não ligar
  recommendation: Ligar
  status: pending
  blocking: false
  opened_at: '2026-11-11T22:22:20-03:00'
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
- at: '2026-11-10T23:58:12-03:00'
  who: ag-sim
  msg: T-020 ✓ ler estratégia e specs
- at: '2026-11-10T23:58:13-03:00'
  who: ag-sim
  msg: T-020 ✓ downloader klines publicos
- at: '2026-11-10T23:58:17-03:00'
  who: ag-sim
  msg: 'download de klines públicos iniciado: 11 moedas, 15m/1h/4h/1d, jul/2024→nov/2026'
- at: '2026-11-10T23:58:19-03:00'
  who: ag-sim
  msg: T-021 todo → doing
- at: '2026-11-10T23:58:44-03:00'
  who: ag-ui
  msg: T-030 ✓ reescrever CSS/HTML
- at: '2026-11-10T23:58:46-03:00'
  who: ag-ui
  msg: T-031 todo → doing
- at: '2026-11-11T00:03:18-03:00'
  who: ag-spec
  msg: T-010 ✓ ler código
- at: '2026-11-11T00:03:18-03:00'
  who: ag-spec
  msg: T-010 ✓ plano de migração
- at: '2026-11-11T00:03:18-03:00'
  who: ag-spec
  msg: T-010 doing → done
- at: '2026-11-11T00:03:19-03:00'
  who: ag-spec
  msg: 'inventário .spec concluído; pytest no .venv de D: falha por falta de sqlitedict (deps não instaladas)'
- at: '2026-11-11T00:03:27-03:00'
  who: ag-spec
  msg: T-011 todo → doing
- at: '2026-11-11T00:03:34-03:00'
  who: ag-sim
  msg: T-021 ✓ mock_exchange (taxa/slippage/fills)
- at: '2026-11-11T00:03:35-03:00'
  who: ag-sim
  msg: T-021 ✓ indicadores pandas/numpy sem look-ahead
- at: '2026-11-11T00:03:37-03:00'
  who: ag-sim
  msg: T-021 ✓ Porteiro + oráculo mock
- at: '2026-11-11T00:04:52-03:00'
  who: ag-ui
  msg: T-031 ✓ harness Flask mock
- at: '2026-11-11T00:04:52-03:00'
  who: ag-ui
  msg: T-031 ✓ diff de paridade IDs/eventos
- at: '2026-11-11T00:05:13-03:00'
  who: ag-sim
  msg: T-021 ✓ saídas intra-vela conservadoras + latência
- at: '2026-11-11T00:05:14-03:00'
  who: ag-sim
  msg: T-021 ✓ testes pytest
- at: '2026-11-11T00:05:16-03:00'
  who: ag-sim
  msg: engine + mock_exchange prontos; 17 testes test_sim_* passando
- at: '2026-11-11T00:06:32-03:00'
  who: ag-spec
  msg: T-011 ✓ rascunho arch.yaml
- at: '2026-11-11T00:06:32-03:00'
  who: ag-spec
  msg: T-011 ✓ validar yaml.safe_load
- at: '2026-11-11T00:06:32-03:00'
  who: ag-spec
  msg: T-011 doing → done
- at: '2026-11-11T00:06:49-03:00'
  who: ag-spec
  msg: T-012 todo → doing
- at: '2026-11-11T00:10:25-03:00'
  who: ag-spec
  msg: T-012 ✓ ADRs migradas (0001-0009)
- at: '2026-11-11T00:10:56-03:00'
  who: orquestrador
  msg: status → waiting
- at: '2026-11-11T00:11:06-03:00'
  who: ag-sim
  msg: 'smoke BASE (BTC/ETH/SOL): win 74% mas expectância −0,34%/trade (ganho ~+1,4% vs stop ~−5,3%)'
- at: '2026-11-11T00:11:16-03:00'
  who: ag-spec
  msg: T-012 ✓ ADRs novas (0010-0013)
- at: '2026-11-11T00:11:16-03:00'
  who: ag-spec
  msg: T-012 doing → done
- at: '2026-11-11T00:11:18-03:00'
  who: ag-spec
  msg: T-013 todo → doing
- at: '2026-11-11T00:13:17-03:00'
  who: ag-sim
  msg: T-022 todo → doing
- at: '2026-11-11T00:13:51-03:00'
  who: ag-sim
  msg: T-022 ✓ montar grade estágio 1 (69 variações one-at-a-time)
- at: '2026-11-11T00:13:56-03:00'
  who: ag-spec
  msg: T-013 ✓ migrar specs 001-004 + refactor 005
- at: '2026-11-11T00:15:09-03:00'
  who: ag-sim
  msg: T-020 ✓ baixar 10+ moedas 15m/1h/4h/1d
- at: '2026-11-11T00:15:10-03:00'
  who: ag-sim
  msg: T-020 doing → done
- at: '2026-11-11T00:15:11-03:00'
  who: ag-sim
  msg: 'T-020 concluída: 11 moedas × 4 TFs, jul/2024→out/2026 (alta 2024-25, baixa Q4/25–Q2/26, recuperação Q3/26),
    0 gaps'
- at: '2026-11-11T00:15:12-03:00'
  who: ag-sim
  msg: T-021 doing → done
- at: '2026-11-11T00:16:15-03:00'
  who: ag-spec
  msg: T-013 ✓ UNITs novas E0-E4 (008-012)
- at: '2026-11-11T00:16:15-03:00'
  who: ag-spec
  msg: T-013 doing → done
- at: '2026-11-11T00:16:16-03:00'
  who: ag-spec
  msg: T-014 todo → doing
- at: '2026-11-11T00:17:21-03:00'
  who: ag-spec
  msg: T-014 ✓ escrever README
- at: '2026-11-11T00:18:15-03:00'
  who: ag-spec
  msg: 'decisão aberta D-101: update_pending.flag só é consumida pelo painel.py (deprecado); no modo web/Docker
    o botão ''Atualizar bot'' não faz nada. Como tratar?'
- at: '2026-11-11T00:18:17-03:00'
  who: ag-spec
  msg: 'decisão aberta D-102: A suíte pytest não coleta no .venv de D: (falta sqlitedict: binance_trade_bot/__init__
    importa backtest). Instalar requirements completos no .venv de D: ou isolar os imports do pacote?'
- at: '2026-11-11T00:18:19-03:00'
  who: ag-spec
  msg: T-014 ✓ remover pastas antigas + validar
- at: '2026-11-11T00:18:19-03:00'
  who: ag-spec
  msg: T-014 doing → done
- at: '2026-11-11T00:18:21-03:00'
  who: ag-spec
  msg: 'E1 concluído: .spec = README + arch.yaml + 13 ADRs + 12 UNITs; planning/specs/contracts/strategies removidas'
- at: '2026-11-11T00:18:26-03:00'
  who: ag-spec
  msg: status → done
- at: '2026-11-11T00:20:48-03:00'
  who: ag-sim
  msg: grade estágio 1 em execução (~22 s/variação, 11 moedas)
- at: '2026-11-11T00:27:10-03:00'
  who: orquestrador
  msg: status → active
- at: '2026-11-11T00:27:14-03:00'
  who: orquestrador
  msg: 'commit v3.7.1: .spec reestruturada (ADR/UNIT/arch.yaml)'
- at: '2026-11-11T00:31:17-03:00'
  who: ag-calib
  msg: status → active
- at: '2026-11-11T00:31:17-03:00'
  who: ag-calib
  msg: agente criado (Calibrador)
- at: '2026-11-11T00:31:19-03:00'
  who: orquestrador
  msg: status → waiting
- at: '2026-11-11T00:31:20-03:00'
  who: ag-calib
  msg: T-041 todo → doing
- at: '2026-11-11T00:36:09-03:00'
  who: ag-calib
  msg: T-041 ✓ Extrair ProfitGainParams
- at: '2026-11-11T00:36:11-03:00'
  who: ag-ui
  msg: T-030 ✓ ajustes pós-screenshot
- at: '2026-11-11T00:36:11-03:00'
  who: ag-ui
  msg: T-030 doing → done
- at: '2026-11-11T00:36:12-03:00'
  who: ag-ui
  msg: T-031 ✓ screenshots desktop/mobile
- at: '2026-11-11T00:36:12-03:00'
  who: ag-ui
  msg: T-031 doing → done
- at: '2026-11-11T00:36:13-03:00'
  who: ag-ui
  msg: 'E3: index.html repaginado; paridade 29/29 IDs, 12/12 emits, 7/7 listeners; screenshots em D:\binance_trade_work\ui_check\shots'
- at: '2026-11-11T00:36:13-03:00'
  who: ag-ui
  msg: status → done
- at: '2026-11-11T00:36:31-03:00'
  who: ag-sim
  msg: T-022 ✓ rodar estágio 1 em 11 moedas
- at: '2026-11-11T00:36:33-03:00'
  who: ag-sim
  msg: 'estágio 1 ok (69 var). Melhores IS: entrada sma200=asset/both, ema<-2; saída trail_drop=0.2/trail_act=2.0;
    stop_mult=3/5, clamp 4-12'
- at: '2026-11-11T00:37:08-03:00'
  who: orquestrador
  msg: status → active
- at: '2026-11-11T00:37:15-03:00'
  who: orquestrador
  msg: 'commit v3.8.0: repaginação da página do app'
- at: '2026-11-11T00:39:41-03:00'
  who: ag-calib
  msg: T-041 ✓ Carregar [profit_gain] no config.py + user.cfg.exemple
- at: '2026-11-11T00:39:41-03:00'
  who: ag-calib
  msg: T-041 ✓ Fix stop antes da mineração
- at: '2026-11-11T00:39:41-03:00'
  who: ag-calib
  msg: T-041 ✓ Fix preço de compra = fill médio
- at: '2026-11-11T00:39:44-03:00'
  who: ag-calib
  msg: profit_gain parametrizada (ProfitGainParams) + pré-check de stop antes da mineração + preço de compra = fill
    médio
- at: '2026-11-11T00:39:50-03:00'
  who: orquestrador
  msg: T-004 ✓ re-render só com dados novos
- at: '2026-11-11T00:39:50-03:00'
  who: orquestrador
  msg: T-004 ✓ screenshots desktop/mobile
- at: '2026-11-11T00:39:50-03:00'
  who: orquestrador
  msg: T-004 todo → doing
- at: '2026-11-11T00:39:51-03:00'
  who: orquestrador
  msg: T-004 doing → done
- at: '2026-11-11T00:39:52-03:00'
  who: orquestrador
  msg: 'commit v3.8.1: fix re-render do painel'
- at: '2026-11-11T00:40:01-03:00'
  who: orquestrador
  msg: status → waiting
- at: '2026-11-11T00:40:45-03:00'
  who: ag-sim
  msg: 'T-022 ✓ estágio 2: combinações dos melhores IS'
- at: '2026-11-11T00:40:46-03:00'
  who: ag-sim
  msg: 'T-022 ✓ checagens: latência (close) e slippage 0,2%'
- at: '2026-11-11T00:40:46-03:00'
  who: ag-sim
  msg: T-022 doing → done
- at: '2026-11-11T00:40:47-03:00'
  who: ag-sim
  msg: 'T-022 ok: 101 variações. Nenhuma lucrativa com robustez; melhor (SMA200 ativo + trail_drop 0.2 + stop_mult
    3) ≈ break-even (carteira IS −16,7% vs BASE −83,7%; OOS −2,0% vs −59,3%), mas frágil a latência/slippage'
- at: '2026-11-11T00:40:48-03:00'
  who: ag-sim
  msg: T-023 todo → doing
- at: '2026-11-11T00:40:49-03:00'
  who: ag-sim
  msg: T-023 ✓ análise por trimestre e moeda
- at: '2026-11-11T00:42:20-03:00'
  who: ag-sim
  msg: T-023 ✓ escrever sim-001-calibracao.md
- at: '2026-11-11T00:42:22-03:00'
  who: ag-sim
  msg: 'decisão aberta D-201: Simulação: profit_gain não paga custos (BASE −0,30%/trade; melhor variação ≈ break-even
    e frágil). O que fazer com o live?'
- at: '2026-11-11T00:42:23-03:00'
  who: ag-sim
  msg: 'decisão aberta D-202: Edge bruto ≈ custo de round-trip. Ativar desconto de taxa em BNB?'
- at: '2026-11-11T00:42:24-03:00'
  who: ag-sim
  msg: 'decisão aberta D-203: Clamp do stop do BTC (6–10,5%) parece largo; BTC foi a pior moeda na REC'
- at: '2026-11-11T00:42:25-03:00'
  who: ag-sim
  msg: 'decisão aberta D-204: Relação alvo ~+1,3% vs stop 4–7% exige >79% de acerto; revisar tese/all-in em nova
    spec?'
- at: '2026-11-11T00:42:26-03:00'
  who: ag-sim
  msg: T-023 ✓ registrar decisões do Micael
- at: '2026-11-11T00:42:35-03:00'
  who: ag-sim
  msg: T-023 doing → done
- at: '2026-11-11T00:42:35-03:00'
  who: ag-sim
  msg: 'T-023 ok: relatório simulation/reports/sim-001-calibracao.md; recomendação: gate SMA200 diária (seguro),
    trail_drop 0.2 e stop_mult 3 opcionais; D-201..D-204 abertas'
- at: '2026-11-11T00:42:36-03:00'
  who: ag-sim
  msg: status → done
- at: '2026-11-11T00:42:49-03:00'
  who: ag-calib
  msg: T-041 ✓ Testes mock + suíte
- at: '2026-11-11T00:43:14-03:00'
  who: ag-calib
  msg: 'decisão aberta D-401: UNIT-006 item 4: com USDT < $5 a recuperação de estado assume a 1ª moeda da carteira
    com valor >= $5, mesmo uma que o bot nunca comprou (e passa a vendê-la pelos stops). Corrigir?'
- at: '2026-11-11T00:43:15-03:00'
  who: ag-calib
  msg: 'decisão aberta D-402: UNIT-006 item 5: Tribunal de Swap exige >= 4 candidatas aprovadas ao mesmo tempo,
    então quase nunca convoca (e adia +45 min). Qual o mínimo?'
- at: '2026-11-11T00:43:15-03:00'
  who: ag-calib
  msg: 'decisão aberta D-403: UNIT-006 item 6: durante o cooldown do motor (ai_cooldown_until) a mineração pesada
    de klines continua rodando a cada scout; só a chamada à IA é poupada. Pular a mineração no cooldown quando fora
    de operação?'
- at: '2026-11-11T00:43:15-03:00'
  who: ag-calib
  msg: 'decisão aberta D-404: UNIT-006 item 7: daily_profit_pct soma % por trade (não compõe, ignora capital). Meta
    de 5% e hibernação disparam sobre número aproximado. Trocar?'
- at: '2026-11-11T00:43:16-03:00'
  who: ag-calib
  msg: 'decisão aberta D-405: UNIT-006 item 8: entrada all-in (99% do saldo). Agora configurável via [profit_gain]
    entry_balance_fraction (default 0.99, comportamento inalterado). Mudar o default?'
- at: '2026-11-11T00:43:17-03:00'
  who: ag-calib
  msg: 'decisão aberta D-406: UNIT-006 item 9: maximum_hold_time_seconds = 7200 é definido e nunca usado (não há
    timeout de posição). O que fazer?'
- at: '2026-11-11T00:43:18-03:00'
  who: ag-calib
  msg: T-041 ✓ Registrar decisões D-4xx (itens 4-9)
- at: '2026-11-11T00:43:18-03:00'
  who: ag-calib
  msg: T-041 doing → done
- at: '2026-11-11T00:43:19-03:00'
  who: ag-calib
  msg: 'T-041 concluída: 29 params extraídos, stop pré-mineração, fill médio; pytest 62 passed; decisões D-401..D-406
    abertas'
- at: '2026-11-11T00:43:19-03:00'
  who: ag-calib
  msg: status → done
- at: '2026-11-11T00:43:29-03:00'
  who: orquestrador
  msg: status → active
- at: '2026-11-11T00:43:30-03:00'
  who: orquestrador
  msg: 'commit v3.9.0: simulação 101 variações; baseline perde (−0,30%/trade); SMA200 é o único ganho robusto'
- at: '2026-11-11T00:43:48-03:00'
  who: orquestrador
  msg: status → waiting
- at: '2026-11-11T00:44:24-03:00'
  who: orquestrador
  msg: status → active
- at: '2026-11-11T00:44:26-03:00'
  who: orquestrador
  msg: 'commit v3.10.0: profit_gain parametrizada; stop antes da varredura; fill real (62 testes)'
- at: '2026-11-11T00:44:40-03:00'
  who: ag-calib
  msg: T-040 todo → doing
- at: '2026-11-11T00:44:47-03:00'
  who: ag-calib
  msg: status → active
- at: '2026-11-11T00:44:56-03:00'
  who: orquestrador
  msg: status → waiting
- at: '2026-11-11T00:45:05-03:00'
  who: ag-sim
  msg: T-024 todo → doing
- at: '2026-11-11T00:45:06-03:00'
  who: ag-sim
  msg: status → active
- at: '2026-11-11T00:47:22-03:00'
  who: ag-calib
  msg: T-040 ✓ Params regime_filter_sma200/regime_sma_period
- at: '2026-11-11T00:47:22-03:00'
  who: ag-calib
  msg: T-040 ✓ Gate SMA200 diário com cache 24h (Porteiro + Tribunal)
- at: '2026-11-11T00:51:13-03:00'
  who: ag-sim
  msg: 'T-024 ✓ estender engine: stop fixo, breakeven, parcial, time-stop, confirmação, maker'
- at: '2026-11-11T00:51:15-03:00'
  who: ag-sim
  msg: T-024 ✓ testes novos
- at: '2026-11-11T00:53:12-03:00'
  who: ag-sim
  msg: 'sim-002: grade estrutural iniciada (53 var estágio 1 + combinações + 28 checagens de robustez), todas com
    gate SMA200'
- at: '2026-11-11T00:53:25-03:00'
  who: ag-calib
  msg: 'decisão aberta D-407: Gate SMA200 diário ligado por padrão (regime_filter_sma200=true). Mantém?'
- at: '2026-11-11T00:53:27-03:00'
  who: ag-calib
  msg: T-040 ✓ Testes mock + suíte
- at: '2026-11-11T00:53:27-03:00'
  who: ag-calib
  msg: T-040 ✓ Atualizar arch.yaml e UNIT-012
- at: '2026-11-11T00:53:27-03:00'
  who: ag-calib
  msg: T-040 ✓ Decisão D-407
- at: '2026-11-11T00:53:27-03:00'
  who: ag-calib
  msg: T-040 doing → done
- at: '2026-11-11T00:53:35-03:00'
  who: ag-calib
  msg: 'T-040 concluída: gate SMA200 diário (Porteiro+Tribunal, fail-closed, cache diário) na profit_gain; D-407
    aberta'
- at: '2026-11-11T00:53:50-03:00'
  who: ag-calib
  msg: status → done
- at: '2026-11-11T00:55:53-03:00'
  who: orquestrador
  msg: status → active
- at: '2026-11-11T00:56:22-03:00'
  who: orquestrador
  msg: 'commit v3.11.0: gate de regime SMA200 diária (89 testes)'
- at: '2026-11-11T00:57:31-03:00'
  who: orquestrador
  msg: status → waiting
- at: '2026-11-11T01:14:14-03:00'
  who: ag-sim
  msg: 'decisão aberta D-210: sim-002: entrada limit −0,6% válida 1h (+taxa BNB) é a única melhora relevante (carteira
    IS +0,05%/trade), mas depende do modelo de fill. Implementar?'
- at: '2026-11-11T01:14:16-03:00'
  who: ag-sim
  msg: 'decisão aberta D-211: 190 configurações (sim-001+002) sem edge líquido robusto na profit_gain; problema
    está no sinal (edge bruto ≈ custo). O que fazer?'
- at: '2026-11-11T01:14:16-03:00'
  who: ag-sim
  msg: T-024 ✓ grade estrutural >=50 var
- at: '2026-11-11T01:14:17-03:00'
  who: ag-sim
  msg: T-024 ✓ relatório sim-002
- at: '2026-11-11T01:14:18-03:00'
  who: ag-sim
  msg: T-024 doing → done
- at: '2026-11-11T01:14:19-03:00'
  who: ag-sim
  msg: 'T-024 ok: sim-002 (89 config, todas c/ SMA200). Nenhuma positiva e robusta; R:R/breakeven/parcial/time-stop
    pioram; só limit −0,6%×1h + BNB ≈ empate (IS +0,05%/trade, OOS −0,14%, @close −0,19/−0,52). D-210/D-211 abertas'
- at: '2026-11-11T01:14:20-03:00'
  who: ag-sim
  msg: status → done
- at: '2026-11-11T01:15:22-03:00'
  who: orquestrador
  msg: status → active
- at: '2026-11-11T01:15:25-03:00'
  who: orquestrador
  msg: 'commit v3.12.0: sim-002 (89 variações estruturais): nenhuma robusta; problema é o sinal'
- at: '2026-11-11T01:15:46-03:00'
  who: orquestrador
  msg: 'sessão autônoma encerrada: tudo commitado até v3.12.0; pendências = decisões do Micael'
- at: '2026-11-11T01:15:48-03:00'
  who: orquestrador
  msg: status → idle
- at: '2026-11-11T22:15:58-03:00'
  who: orquestrador
  msg: T-005 ✓ estudar o modelo (layout + contrato)
- at: '2026-11-11T22:15:58-03:00'
  who: orquestrador
  msg: T-005 todo → doing
- at: '2026-11-11T22:15:59-03:00'
  who: orquestrador
  msg: status → active
- at: '2026-11-11T22:21:11-03:00'
  who: orquestrador
  msg: T-005 ✓ coletor estado.json com nossas fontes
- at: '2026-11-11T22:21:11-03:00'
  who: orquestrador
  msg: T-005 ✓ página adaptada
- at: '2026-11-11T22:21:11-03:00'
  who: orquestrador
  msg: T-005 ✓ testes testes/sim no card
- at: '2026-11-11T22:22:20-03:00'
  who: orquestrador
  msg: T-005 ✓ verificação visual 1440/390
- at: '2026-11-11T22:22:20-03:00'
  who: orquestrador
  msg: T-005 ✓ hook do feed Agora
- at: '2026-11-11T22:22:20-03:00'
  who: orquestrador
  msg: T-005 doing → done
- at: '2026-11-11T22:22:20-03:00'
  who: orquestrador
  msg: 'decisão aberta D-008: Ligar o hook do feed Agora (.claude/settings.json → devpanel/registrar_atividade.py
    em PreToolUse/PostToolUse/UserPromptSubmit/Stop/SubagentStop)? Só vale abrindo o Claude Code em D:\binance_trade.'
- at: '2026-11-11T22:22:21-03:00'
  who: orquestrador
  msg: 'commit v3.13.0: painel refeito com a cara do modelo'
- at: '2026-11-11T22:22:22-03:00'
  who: orquestrador
  msg: status → waiting
- at: '2026-11-11T22:33:35-03:00'
  who: orquestrador
  msg: T-006 ✓ UNIT-011 atualizada
- at: '2026-11-11T22:33:35-03:00'
  who: orquestrador
  msg: T-006 ✓ coletor unitSpecs
- at: '2026-11-11T22:33:35-03:00'
  who: orquestrador
  msg: T-006 ✓ tile + card UNITs
- at: '2026-11-11T22:33:35-03:00'
  who: orquestrador
  msg: T-006 todo → doing
- at: '2026-11-11T22:33:35-03:00'
  who: orquestrador
  msg: T-006 doing → done
- at: '2026-11-11T22:33:36-03:00'
  who: orquestrador
  msg: 'commit v3.13.2: UNITs reais no painel; app web no ar em :5000'
- at: '2026-11-11T22:36:43-03:00'
  who: orquestrador
  msg: T-007 ✓ coletor backlog
- at: '2026-11-11T22:36:43-03:00'
  who: orquestrador
  msg: T-007 ✓ faixa no canvas
- at: '2026-11-11T22:36:43-03:00'
  who: orquestrador
  msg: T-007 ✓ print tema escuro
- at: '2026-11-11T22:36:43-03:00'
  who: orquestrador
  msg: T-007 todo → doing
- at: '2026-11-11T22:36:43-03:00'
  who: orquestrador
  msg: T-007 doing → done
- at: '2026-11-11T22:36:44-03:00'
  who: orquestrador
  msg: 'commit v3.13.3: UNITs sem task no fluxo do plano'
updated_at: '2026-11-11T22:36:45-03:00'
proxima:
  texto: 'Revisar o painel novo e aprovar o hook do feed Agora (.claude/settings.json); depois decidir D-201/D-211
    (o que fazer com o live: a estratégia não paga os custos na simulação) e D-407 (manter o filtro SMA200 ligado).'
  quando: agora
  duracao: ~10 min
  atualizado_em: '2026-11-11T22:21:47-03:00'
links:
- titulo: Web app do bot
  url: http://127.0.0.1:5000/
  nota: painel do trade bot (app.py); fora do ar enquanto o bot não roda
  desde: '2026-11-11T22:21:48-03:00'
```
<!-- DATA:END -->
