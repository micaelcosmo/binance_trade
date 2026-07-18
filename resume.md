# 📈 Binance Trade Bot Pro — AI Edition · Resumo Técnico do Projeto

> Documento de visão geral gerado a partir da revisão completa do código-fonte (branch `micael_development_web-view`, versão ~v3.6.6).
> **Aviso:** os arquivos `user.cfg` e `.env` contêm credenciais e **não devem ser lidos/versionados**. Este resumo foi montado apenas a partir do código e dos templates de exemplo.

---

## 1. O que é

Terminal de **trading algorítmico automatizado** para a corretora Binance, focado em **Swing Trade curto** de criptomoedas. O sistema combina:

- **Matemática local de indicadores** (Pandas-TA) como filtro primário ("Porteiro Python").
- **Comitê de IA (Google Gemini)** como segunda camada de decisão preditiva.
- **Painel de controle em tempo real** (Web/Flask + legado Desktop/Tkinter).

A filosofia central: a matemática local filtra os ruídos e só envia para a IA os ativos que passaram por critérios estatísticos rígidos — economizando tokens e blindando contra "alucinações".

---

## 2. Arquitetura (alto nível)

```
┌─────────────────────────────────────────────────────────────┐
│  CAMADA DE INTERFACE (UI)                                     │
│  ├─ app.py            → WebView Flask + SocketIO (NOVO)       │
│  ├─ painel.py         → Dashboard Desktop Tkinter (LEGADO)   │
│  └─ templates/index.html → Front-end Tailwind + SocketIO     │
└───────────────┬─────────────────────────────────────────────┘
                │  comunicação por ARQUIVOS-FLAG + bot_status.json
┌───────────────▼─────────────────────────────────────────────┐
│  CAMADA DE MOTOR (binance_trade_bot/)                         │
│  ├─ __main__.py       → bootstrap, scheduler, patch WS       │
│  ├─ config.py         → parse seguro do user.cfg             │
│  ├─ strategies/profit_gain_strategy.py → MOTOR PRINCIPAL     │
│  ├─ models/ai_agent.py → Comitê de IA (Gemini)              │
│  ├─ binance_api_manager.py → wrapper da API Binance         │
│  ├─ database.py / models/ → SQLAlchemy (legado)             │
│  └─ scheduler.py / logger.py / notifications.py             │
└─────────────────────────────────────────────────────────────┘
```

### Comunicação entre UI e Motor (desacoplada)
O painel **não** chama o motor diretamente. Em vez disso:
- O motor escreve estado em **`bot_status.json`** (lido pela UI a cada ~1s).
- A UI envia comandos criando **arquivos-flag** que o motor consome e apaga:
  - `force_sell.flag` → venda manual (Panic Button)
  - `reset_trades.flag` → zera placar
  - `add_trade.flag` → aumenta limite de trades do dia
  - `cooldown.flag` → ajusta intervalo de scan (15/30/45 min)
  - `bb_std.flag` → ajusta desvio padrão do Bollinger (2.0/1.8/1.5)
  - `update_pending.flag` → dispara auto-update (git pull)
- Estado persistido: `profit_gain_state.json` (motor) e `gui_state.json` (saldo inicial).

---

## 3. Componentes principais

### `binance_trade_bot/__main__.py` — Bootstrap
- Força `WindowsSelectorEventLoopPolicy` + UTF-8 no Windows.
- **Patch condicional:** se a estratégia for `profit_gain`, injeta um `FakeStreamManager` para **matar o WebSocket** (a estratégia usa só REST/klines). Na estratégia `default`, o WebSocket volta a funcionar.
- Inicializa Config → Database → BinanceAPIManager → Strategy.
- Agenda com `SafeScheduler`: `scout` (a cada `SCOUT_SLEEP_TIME`s), `update_values` (1 min) e podas de histórico.

### `strategies/profit_gain_strategy.py` — Motor Quantitativo (1038 linhas, o coração)
É a estratégia **proprietária/customizada** do projeto. Fluxo:

1. **Mineração** (`get_enriched_data`): para cada moeda, busca klines 4h/1h/15m e calcula RSI, EMA9/21, MACD, ATR, Bollinger Bands, Price Action das últimas 12h, distância da EMA, volume relativo etc. Monta um "Dossiê Quantitativo" (JSON).
2. **Filtro Python ("Porteiro")** (`scan_market`): só aprova ativos que:
   - Caíram mais que **2× o próprio ATR** (True Bottom);
   - **Furaram a banda inferior** de Bollinger (15m ou 1H);
   - Têm **volume ≥ 80%** da média;
   - Estão **< -1.00%** distantes da EMA21 (1H).
3. **Comitê de IA** (`analyze_batch`): só o lote filtrado vai ao Gemini, que projeta se há força para **+2.00%** nas próximas horas. Compra só se confiança **≥ 90%**.
4. **Gestão da operação ativa:**
   - **Trailing Stop invisível** (gatilho em +1.50%, persegue o pico e corta em recuos).
   - **Stop Loss dinâmico** atrelado ao ATR (teto -7% altcoins / -10.5% BTC) + **Stop de Desastre** (-15%).
   - **Tribunal de Swap** (`analyze_swap`): se preso > 10h numa moeda em prejuízo, a IA avalia migrar para um setup melhor — só com **confiança ≥ 95%**.
5. **Metas diárias:** hiberna até a meia-noite ao bater meta de lucro ou limite de trades.
6. **Recuperação de estado:** ao iniciar, detecta posições já abertas na carteira e assume o controle.

### `models/ai_agent.py` — Comitê de IA
- Usa o SDK nativo **`google-genai`** com modelo **`gemini-2.5-flash`** (response em JSON).
- Lê a chave de `GOOGLE_API_KEY` (env var → fallback no `user.cfg`).
- Sem chave → modo "cego" (bypass, `ERROR_503`).
- `_clean_payload_for_ai`: higieniza o dossiê para economizar tokens.
- Dois prompts: `analyze_batch` (compra) e `analyze_swap` (Tribunal de troca).

### `app.py` — WebView Flask (a novidade desta branch)
- Flask + **Flask-SocketIO** (`async_mode='threading'`), porta 5000.
- Sobe o motor como **subprocess** (`python -m binance_trade_bot`) e faz streaming dos logs via socket.
- Threads de background: `monitor_bot_status` (lê `bot_status.json`), `update_stats_loop` (calcula saldo/P&L total em USDT via API).
- Eventos socket: start/stop, reset saldo/placar, ciclar cooldown/BB, venda forçada, update, e modais (relatório IA, histórico diário, dossiê visual).

### `painel.py` — Dashboard Desktop (legado Tkinter, 766 linhas)
Versão anterior da interface, mesma lógica de flags/JSON. Coexiste com o `app.py`.

### Camada legada herdada do projeto original (`edeng23/binance-trade-bot`)
- `database.py`, `models/` (SQLAlchemy), `auto_trader.py`, `binance_api_manager.py`, `binance_stream_manager.py`, `backtest.py`, `scheduler.py`, `notifications.py`, e as estratégias `default_strategy.py` / `multiple_coins_strategy.py`. Mantidas por compatibilidade, mas a `profit_gain` é a estratégia ativa.

---

## 4. Configuração (sem expor segredos)

- **`user.cfg`** (NÃO versionar — copiar de `user.cfg.exemple`): chaves Binance, `GOOGLE_API_KEY`, e parâmetros (`strategy=profit_gain`, metas, stops, trailing, cooldowns).
- **`supported_coin_list.txt`** (copiar de `supported_coin_list.exemple`): moedas a minerar, uma por linha, sem o par USDT.
- `config.py` faz parse **anti-crash**: fallbacks institucionais para todo valor ausente/vazio, e aceita override por variáveis de ambiente (deploy cloud).

---

## 5. Stack / Dependências

| Categoria | Bibliotecas |
|---|---|
| Web/UI | Flask 3.1, flask-socketio, python-socketio, flask-cors, Tkinter |
| Exchange | python-binance, unicorn-binance-websocket-api (==2.10.2) |
| Análise técnica | pandas, pandas-ta |
| IA | google-genai (Gemini 2.5 Flash) |
| Infra | schedule, SQLAlchemy 1.4, sqlitedict, apprise (notificações) |

> ⚠️ Conflito conhecido: `unicorn-binance-websocket-api` exige `websockets==11.0.3`.

---

## 6. Como executar (resumo)

```bash
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt
# criar user.cfg e supported_coin_list.txt a partir dos .exemple
python app.py        # interface web (http://localhost:5000)  [NOVO]
# ou
python painel.py     # interface desktop (legado)
```

---

## 7. Observações / pontos de atenção (revisão)

- **Segurança de credenciais:** `user.cfg` traz chaves Binance + Google. Garantir que esteja no `.gitignore` (templates `.exemple` são versionados; os reais não devem ser). Recomendação do próprio README: desativar permissão de saque na Binance.
- **`SECRET_KEY` hardcoded** em `app.py` (`'binance_bot_pro_dev_key_secure'`) e `host='0.0.0.0'` com `debug=True` — adequado para uso local, mas **inseguro para exposição pública**.
- **Acoplamento por arquivos-flag:** simples e robusto para single-host, mas não escala para múltiplas instâncias e depende de I/O de disco.
- **Resiliência:** há tratamento abrangente de exceções de rede (`ConnectionError`, timeouts) e persistência de estado para sobreviver a reinícios.
- **Risco financeiro:** software experimental/educacional; opera capital real a mercado. Auditar em ambiente controlado antes de alocar capital (ver Disclaimer do README).

---

## 8. Mapa rápido de arquivos

| Arquivo | Papel | LOC |
|---|---|---|
| `strategies/profit_gain_strategy.py` | Motor quantitativo principal | 1038 |
| `painel.py` | Dashboard desktop (legado) | 766 |
| `app.py` | WebView Flask + SocketIO | 518 |
| `binance_api_manager.py` | Wrapper API Binance | 450 |
| `database.py` | Persistência SQLAlchemy (legado) | 295 |
| `models/ai_agent.py` | Comitê de IA Gemini | 165 |
| `config.py` | Parse seguro de config | 95 |
| `templates/index.html` | Front-end do painel web | 552 |
| `__main__.py` | Bootstrap + scheduler | 87 |
```
