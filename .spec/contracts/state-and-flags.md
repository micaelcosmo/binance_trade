# Contrato · Estado, Flags e Eventos (UI ⇄ Motor)

> **Status:** Draft · **Prioridade:** P0 · **Fase:** A (Blindagem)
> **Issues relacionadas:** `DATA-01` (contrato implícito), `DATA-02` (race de I/O)
> **Fonte:** extraído do código atual — `profit_gain_strategy.py::_write_json_ui/_save_state`, `app.py` (handlers/threads), `config.py`.
> **Propósito:** congelar o contrato **de fato** hoje, para que qualquer refactor (spec 005) ou blindagem (spec 003) preserve o comportamento. Este é o "estado verdade" atual, não o ideal.

---

## 0. Topologia da comunicação

```text
        MOTOR (binance_trade_bot)                 UI (app.py / painel.py)
   ┌──────────────────────────────┐          ┌──────────────────────────────┐
   │ escreve a cada scan/heartbeat│          │ poll ~1s lê bot_status.json   │
   │   bot_status.json  ──────────┼──────────┼─► monitor_bot_status()        │
   │   profit_gain_state.json     │          │   emite socket 'update_metrics'│
   │ consome+apaga *.flag ◄───────┼──────────┼── cria *.flag (comandos)      │
   └──────────────────────────────┘          │   gui_state.json (saldo)      │
                                              └──────────────────────────────┘
```

Princípios do contrato atual:
- **Unidirecional por canal:** motor→UI via `bot_status.json`; UI→motor via `*.flag`.
- **Sem lock:** leituras/escritas concorrentes sem sincronização (origem de `DATA-02`).
- **Best-effort:** quase todo I/O está em `try/except: pass` — falha silenciosa.
- **Encoding:** `bot_status.json` é gravado com `ensure_ascii=False, indent=2`; demais JSON sem indent.

---

## 1. `bot_status.json` — canal Motor → UI

Gravado por `_write_json_ui()`. **Sobrescrito por completo** a cada chamada (não é merge).

### 1.1 Campos escritos pelo MOTOR

```yaml
bot_status:
  coin:                str    # moeda em operação, ou base_coin (USDT) se parado
  status:              str    # texto de status UI (ex.: "Em Operação (BTC)", "Minerando métricas...")
  cooldown_until:      float  # epoch; quando a próxima análise é liberada (ai_cooldown_until)
  last_heartbeat_ts:   float  # epoch do último update_values()
  current_coin_change: float  # variação 24h % da moeda ativa
  btc_price:           float
  btc_change:          float  # variação 24h % do BTC
  buy_price:           float  # preço de entrada da operação ativa (0 se parado)
  current_price:       float
  target_price:        float  # gatilho de trailing/take-profit corrente
  active_qty:          float  # quantidade de altcoin em carteira
  buy_time:            float  # epoch do início da operação (operation_start_time)
  chart_data:          list   # ver 1.3 (candles + bollinger, últimos ~30 de 15m)
  trades_won:          int
  trades_lost:         int
  current_detail:      str    # linha-resumo central do painel (duração/SL/gatilho/meta)
  hot_cache:           list[str]  # moedas em uptrend, formatado p/ UI
  cold_cache:          list[str]  # moedas em downtrend
  daily_trades:        int
  max_daily_trades:    int
  full_ai_report:      str    # parecer completo da IA (multiline)
  daily_history:       list   # ver 1.4
  last_dossier:        list   # ver 1.5 (dossiê do motor quantitativo)
  motor_cooldown_minutes: int   # 15 | 30 | 45
  bollinger_std:       float    # 2.0 | 1.8 | 1.5
```

### 1.2 Campos ENRIQUECIDOS pela UI (não persistidos pelo motor)

`monitor_bot_status()` em `app.py` adiciona estes campos ao objeto antes de emitir `update_metrics`:

```yaml
ui_derived:
  countdown_str:     str   # "⏳ Próxima Análise: MM:SS" derivado de cooldown_until
  unlock_add_trade:  bool  # libera botão "add trade" quando daily_trades subiu
  hb_str:            str   # last_heartbeat_ts formatado HH:MM:SS
  hb_color:          str   # '#10b981' | '#f59e0b' | '#ef4444' (saúde do heartbeat)
  current_motor_cooldown: int    # espelha estado da UI (cooldown vigente)
  current_bb_std:    float       # espelha estado da UI (bb std vigente)
# Regra de saúde do heartbeat: delta<=80s verde, <=300s amarelo, senão vermelho.
```

### 1.3 Sub-schema `chart_data[]` (candle + bollinger)

```yaml
candle:
  o:   float  # open
  h:   float  # high
  l:   float  # low
  c:   float  # close
  bbu: float  # bollinger upper
  bbm: float  # bollinger middle
  bbl: float  # bollinger lower
# Origem: klines 15m, length=20, std=bollinger_std. Janela: últimos 30.
```

### 1.4 Sub-schema `daily_history[]`

```yaml
trade_record:
  time:   str   # "HH:MM:SS"
  coin:   str   # ticker (ex.: "BTC")
  result: str   # "+1.52%" | "-3.10%"  (com sinal)
  reason: str   # TAKE_PROFIT | STOP_LOSS_DINAMICO | STOP_DESASTRE | VENDA_MANUAL(...) | SWAP_IA_95%
# COMPAT: a UI também aceita chaves legadas 'resultado'/'motivo' (app.py faz fallback).
```

### 1.5 Sub-schema `last_dossier[]` (saída do "Porteiro Python")

Subconjunto do payload de `get_enriched_data()`. Campos que a UI renderiza:

```yaml
dossier_item:
  coin:                       str
  current_price:              float
  change_24h_pct:             str    # "+/-N.NN%"
  min_24h_change_pct:         str    # "+/-N.NN%"
  required_atr_bottom_pct:    str    # "+/-N.NN%" (limiar 2x ATR)
  touched_lower_band_15m:     bool
  touched_lower_band_1h:      bool
  lowest_15m_val:             float
  bbl_15m_target:             float
  lowest_1h_val:              float
  bbl_1h_target:              float
  macd_1h_shifting_up:        bool
  macd_histogram_15m_positive:bool
  volume_15m_above_avg:       bool
  volume_15m_pct:             float
  ema21_1h_distance_pct:      str    # "+/-N.NN%" (esperado < -1.00%)
# Nota: get_enriched_data() produz mais campos (rsi_*, price_action_1h_last_12, etc.);
# o dossiê os carrega, mas a UI só exibe os listados acima.
```

---

## 2. `profit_gain_state.json` — persistência do MOTOR

Gravado por `_save_state()`, lido por `_load_state()`. Sobrevive a reinícios.

```yaml
profit_gain_state:
  operation_start_time:   float  # epoch início da operação
  last_switch_time:       float  # epoch do último ciclo do Tribunal de Swap
  active_altcoin_quantity:float
  trades_won:             int    # placar acumulado (não diário)
  trades_lost:            int
  active_buy_price:       float
  peak_profit_pct:        float  # pico para o trailing
  active_dynamic_stop_loss:float # % de SL dinâmico armado
  current_date:           str    # "YYYY-MM-DD" — usado p/ reset diário
  daily_profit_pct:       float  # só válido se current_date == hoje
  daily_trades:           int
  daily_history:          list   # mesmo schema 1.4
  full_ai_report:         str
  max_daily_trades:       int    # pode crescer via add_trade.flag
  motor_cooldown_minutes: int
  bollinger_std:          float
# Regra de carga: campos "diários" só são restaurados se current_date == data de hoje;
# caso contrário, _check_daily_reset() zera metas/histórico.
```

---

## 3. `gui_state.json` — persistência da UI

```yaml
gui_state:
  saldo_inicial: float   # capital inicial p/ cálculo de P&L (gravado por app.py)
```

---

## 4. Arquivos-FLAG — canal UI → Motor

Comando one-shot: a UI **cria** o arquivo, o motor **lê e apaga** (`_check_ui_flags()`).
Todos são gravados com `encoding="utf-8"`.

```yaml
flags:
  force_sell.flag:
    payload: "trigger_manual_sell"   # conteúdo ignorado; presença = comando
    effect:  "venda forçada a mercado da posição ativa (_execute_forced_sell)"
    sensitive: true   # AAA scope: trade:sell
  reset_trades.flag:
    payload: "reset"
    effect:  "zera trades_won/lost, metas diárias e histórico"
    sensitive: true   # trade:control
  add_trade.flag:
    payload: "1"
    effect:  "max_daily_trades += 1; força próxima análise em 60s"
    sensitive: true   # trade:control
  cooldown.flag:
    payload: "15|30|45"   # int (minutos)
    effect:  "motor_cooldown_minutes = valor"
    sensitive: true   # trade:control
  bb_std.flag:
    payload: "2.0|1.8|1.5"  # float
    effect:  "bollinger_std = valor (afeta cálculo de bandas)"
    sensitive: true   # trade:control
  update_pending.flag:
    payload: "pending"
    effect:  "motor agenda git pull / auto-update"
    sensitive: true   # system:update
consumo:
  ordem: "checadas a cada scout() e update_values() via _check_ui_flags()"
  idempotencia: "removidas após processar; recriar = novo comando"
  observacao: "conteúdo de cooldown/bb_std é parseado; demais flags = presença basta"
```

> **`gitignore`:** `*.flag` e `*.json` já são ignorados — flags e estado nunca são versionados.

---

## 5. Eventos SocketIO — `app.py` ⇄ front (`index.html`)

```yaml
client_to_server:   # emitidos pelo front, recebidos por @socketio.on
  connect:               { scope: read }
  start_bot:             { scope: "trade:control" }
  stop_bot:              { scope: "trade:control" }
  reset_initial_balance: { scope: "trade:control" }
  reset_scoreboard:      { scope: "trade:control" }
  add_trade_chance:      { scope: "trade:control" }
  cycle_cooldown:        { scope: "trade:control", args: { current: int } }
  cycle_bb_std:          { scope: "trade:control", args: { current: float } }
  force_sell_action:     { scope: "trade:sell" }
  request_update:        { scope: "system:update" }
  request_ai_report:     { scope: read }
  request_daily_history: { scope: read }
  request_dossier:       { scope: read }

server_to_client:   # emitidos pelo servidor
  update_balance:   { inicial: float, atual: float, pl: float, pl_perc: float, ping: int }
  update_metrics:   "objeto bot_status.json enriquecido (seções 1.1 + 1.2)"
  new_log:          { message: str }
  status_parado:    {}   # sinaliza bot parado
  lock_add_trade:   {}
  update_button_states: { cooldown?: int, bb_std?: float }
  show_modal_html:  { title: str, content: str }   # relatório IA / histórico / dossiê
# NOTA: os 'scope' acima ainda NÃO existem no código — são o contrato-alvo da spec 001 (AAA).
# Hoje todos os eventos são abertos. Este bloco documenta o destino, marcando a lacuna.
```

---

## 6. Invariantes do contrato (não quebrar em refactor)

```yaml
invariants:
  - "bot_status.json é escrita ATÔMICA do ponto de vista da UI: ou o objeto antigo, ou o novo completo (objetivo da spec 003)."
  - "Nomes/tipos de campo em 1.1 e nos sub-schemas são estáveis: a UI depende deles literalmente."
  - "Flags são one-shot e idempotentes; remover após consumir é obrigatório."
  - "daily_history aceita chaves novas (result/reason) e legadas (resultado/motivo) — manter o fallback até migração completa."
  - "Campos 'ui_derived' (1.2) são responsabilidade da UI; o motor nunca os escreve."
  - "Reset diário depende de current_date == hoje; não remover essa checagem."
```

---

## 7. Lacunas conhecidas (endereçadas em outras specs)

```yaml
gaps:
  - ref: DATA-02 / spec 003
    issue: "escrita não-atômica → UI pode ler JSON parcial/corrompido"
    fix:   "write-temp + os.replace (rename atômico)"
  - ref: DATA-01 / este doc
    issue: "contrato era implícito"
    fix:   "este arquivo + validação leve de schema na borda (futuro)"
  - ref: SEC-01 / spec 001
    issue: "eventos socket sem escopo/auth"
    fix:   "event_scope_map (seção 5) aplicado via JWT/AAA"
  - ref: COMPAT
    issue: "chaves legadas resultado/motivo em daily_history"
    fix:   "migração única + remover fallback depois"
```
