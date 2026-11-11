# TEMPO — estimado × gasto

> Atualizado em **2026-11-11T00:37:15-03:00** · estimado total **665 min** · gasto total **184 min**. Tempos em minutos (relógio de parede).

## Por task

| task | título | estimado | gasto | Δ | início | fim |
|---|---|---|---|---|---|---|
| T-001 | CLI track.py (STATUS/TEMPO com lock) | 25.0 | 0.3 | -25 | 2026-11-10T23:49:14-03:00 | 2026-11-10T23:49:30-03:00 |
| T-002 | Servidor + UI do painel de dev | 60.0 | 6.7 | -53 | 2026-11-10T23:49:31-03:00 | 2026-11-10T23:56:10-03:00 |
| T-003 | Watchdog de heartbeat no servidor (agente parado = alerta) | 10.0 | — | — | 2026-11-10T23:56:12-03:00 | 2026-11-10T23:56:12-03:00 |
| T-010 | Inventário .spec atual + plano de migração | 15.0 | 11.4 | -4 | 2026-11-10T23:51:53-03:00 | 2026-11-11T00:03:18-03:00 |
| T-011 | arch.yaml único (arquitetura do projeto inteiro) | 45.0 | 3.1 | -42 | 2026-11-11T00:03:27-03:00 | 2026-11-11T00:06:32-03:00 |
| T-012 | ADRs (decisões existentes + novas) | 30.0 | 4.5 | -26 | 2026-11-11T00:06:49-03:00 | 2026-11-11T00:11:16-03:00 |
| T-013 | UNITs (specs migradas + novas unidades) | 40.0 | 5.0 | -35 | 2026-11-11T00:11:18-03:00 | 2026-11-11T00:16:15-03:00 |
| T-014 | .spec/README.md (convenções e índice) | 15.0 | 2.0 | -13 | 2026-11-11T00:16:16-03:00 | 2026-11-11T00:18:19-03:00 |
| T-020 | Coleta de klines públicos (≥8 moedas, 1h/15m/4h/1d) | 30.0 | 23.0 | -7 | 2026-11-10T23:52:08-03:00 | 2026-11-11T00:15:10-03:00 |
| T-021 | Mock exchange + motor de simulação fiel à profit_gain | 90.0 | 16.9 | -73 | 2026-11-10T23:58:19-03:00 | 2026-11-11T00:15:12-03:00 |
| T-022 | Grade ≥50 variações (entrada × stop × stopwin) multi-moeda | 60.0 | 24.0 | -36 | 2026-11-11T00:13:17-03:00 | — |
| T-023 | Relatório + recomendação de parâmetros | 30.0 | — | — | — | — |
| T-030 | Redesign templates/index.html | 60.0 | 44.0 | -16 | 2026-11-10T23:52:10-03:00 | 2026-11-11T00:36:11-03:00 |
| T-031 | Verificação visual com dados mock | 20.0 | 37.4 | +17 | 2026-11-10T23:58:46-03:00 | 2026-11-11T00:36:12-03:00 |
| T-040 | Aplicar valores calibrados (após simulação + aprovação) | 60.0 | — | — | — | — |
| T-041 | Parametrizar profit_gain (defaults atuais) + fix latência do stop e fill real | 75.0 | 5.9 | -69 | 2026-11-11T00:31:20-03:00 | — |

## Por agente

| agente | criado | encerrado | vivo (min) |
|---|---|---|---|
| orquestrador | 2026-11-10T23:49:29-03:00 | — | 47.8 |
| ag-spec | 2026-11-10T23:51:53-03:00 | 2026-11-11T00:18:26-03:00 | 26.6 |
| ag-sim | 2026-11-10T23:52:06-03:00 | — | 45.2 |
| ag-ui | 2026-11-10T23:52:07-03:00 | 2026-11-11T00:36:13-03:00 | 44.1 |
| ag-calib | 2026-11-11T00:31:17-03:00 | — | 6.0 |

<!-- DATA:BEGIN (gerado por devpanel/track.py — não edite à mão) -->
```yaml
tasks:
  T-001:
    estimate_min: 25.0
    started_at: '2026-11-10T23:49:14-03:00'
    spent_min: 0.3
    finished_at: '2026-11-10T23:49:30-03:00'
  T-002:
    estimate_min: 60.0
    spent_min: 6.7
    started_at: '2026-11-10T23:49:31-03:00'
    finished_at: '2026-11-10T23:56:10-03:00'
  T-003:
    estimate_min: 10.0
    spent_min: 0.0
    started_at: '2026-11-10T23:56:12-03:00'
    finished_at: '2026-11-10T23:56:12-03:00'
  T-010:
    estimate_min: 15.0
    spent_min: 11.4
    started_at: '2026-11-10T23:51:53-03:00'
    finished_at: '2026-11-11T00:03:18-03:00'
  T-011:
    estimate_min: 45.0
    spent_min: 3.1
    started_at: '2026-11-11T00:03:27-03:00'
    finished_at: '2026-11-11T00:06:32-03:00'
  T-012:
    estimate_min: 30.0
    spent_min: 4.5
    started_at: '2026-11-11T00:06:49-03:00'
    finished_at: '2026-11-11T00:11:16-03:00'
  T-013:
    estimate_min: 40.0
    spent_min: 5.0
    started_at: '2026-11-11T00:11:18-03:00'
    finished_at: '2026-11-11T00:16:15-03:00'
  T-014:
    estimate_min: 15.0
    spent_min: 2.0
    started_at: '2026-11-11T00:16:16-03:00'
    finished_at: '2026-11-11T00:18:19-03:00'
  T-020:
    estimate_min: 30.0
    spent_min: 23.0
    started_at: '2026-11-10T23:52:08-03:00'
    finished_at: '2026-11-11T00:15:10-03:00'
  T-021:
    estimate_min: 90.0
    spent_min: 16.9
    started_at: '2026-11-10T23:58:19-03:00'
    finished_at: '2026-11-11T00:15:12-03:00'
  T-022:
    estimate_min: 60.0
    spent_min: 24.0
    started_at: '2026-11-11T00:13:17-03:00'
  T-023:
    estimate_min: 30.0
    spent_min: 0.0
  T-030:
    estimate_min: 60.0
    spent_min: 44.0
    started_at: '2026-11-10T23:52:10-03:00'
    finished_at: '2026-11-11T00:36:11-03:00'
  T-031:
    estimate_min: 20.0
    spent_min: 37.4
    started_at: '2026-11-10T23:58:46-03:00'
    finished_at: '2026-11-11T00:36:12-03:00'
  T-040:
    estimate_min: 60.0
    spent_min: 0.0
  T-041:
    estimate_min: 75.0
    started_at: '2026-11-11T00:31:20-03:00'
    spent_min: 5.9
agents:
  orquestrador:
    spawned_at: '2026-11-10T23:49:29-03:00'
    alive_min: 47.8
  ag-spec:
    spawned_at: '2026-11-10T23:51:53-03:00'
    alive_min: 26.6
    ended_at: '2026-11-11T00:18:26-03:00'
  ag-sim:
    spawned_at: '2026-11-10T23:52:06-03:00'
    alive_min: 45.2
  ag-ui:
    spawned_at: '2026-11-10T23:52:07-03:00'
    alive_min: 44.1
    ended_at: '2026-11-11T00:36:13-03:00'
  ag-calib:
    spawned_at: '2026-11-11T00:31:17-03:00'
    alive_min: 6.0
totals:
  estimate_min: 665.0
  spent_min: 184.2
```
<!-- DATA:END -->
