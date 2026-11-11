# simulation/ — calibração offline da profit_gain

Tudo aqui roda **sem conta da Binance e sem saldo real**: dados vêm só do endpoint
público de klines e as ordens vão para uma exchange mock.

| Arquivo | O que é |
|---|---|
| `data.py` | downloader/cache de klines públicos (15m/1h/4h/1d) → `data/sim/*.csv.gz` (gitignored) |
| `mock_exchange.py` | exchange mock: saldo USDT, ordens market com taxa (0,1%) e slippage, histórico de fills |
| `indicators.py` | RSI/EMA/MACD/ATR/Bollinger/ADX/estocástico/IBS/divergências/AVWAP em pandas/numpy |
| `engine.py` | motor candle-a-candle sem look-ahead: Porteiro + oráculo mock + saídas (`Params`) |
| `run_grid.py` | grade de variações (IS 70% / OOS 30%), modos carteira e por moeda |
| `reports/` | relatório `sim-001-calibracao.md` + CSVs |

## Como rodar (Windows, Git Bash)

```bash
export PYTHONUTF8=1 TMP='D:\binance_trade_work\tmp' TEMP='D:\binance_trade_work\tmp'
PY=.venv/Scripts/python

$PY -m simulation.data                 # baixa/atualiza (incremental) ~11 moedas
$PY -m simulation.run_grid --quick     # smoke: BASE em 3 moedas (~1 min)
$PY -m simulation.run_grid             # grade completa (~30–40 min)
$PY -m pytest -q tests/test_sim_*.py   # testes (sintéticos, sem rede)
```

Rodar uma variação avulsa:

```python
from simulation import engine as E
from simulation.run_grid import load_features, ms
feats = load_features(["BTCUSDT", "ETHUSDT"])
p = E.BASELINE.with_(name="teste", trail_act=2.0, trail_drop=0.5)
trades = E.run(p, feats, ms("2024-07-15"), ms("2026-11-01"))
print(E.metrics(trades))
```

## Limitações importantes

- **A IA (Gemini) não é simulada.** O "oráculo mock" é um score de confluência
  determinístico (doc 001); `score_min=None` aprova tudo que passa no Porteiro.
- Indicadores usam só velas **fechadas**; o bot real usa a vela ainda aberta.
- Tribunal de Swap, flags da UI e recuperação de estado não são simulados.
- Stop intra-vela é executado no nível do stop (ou na abertura, em gap) +
  slippage; o modo `check="close"` simula a latência do scout.
