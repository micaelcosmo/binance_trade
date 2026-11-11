# UNIT-010 · Simulação ≥ 50 variações com mock exchange para calibrar previsão, entrada, stoploss e stopwin (E2)

- **Status:** Implemented (101 variações × 11 moedas; relatório `simulation/reports/sim-001-calibracao.md`) — aguarda revisão do Micael (D-201…D-204)
- **Épico:** E2 · **Prioridade:** 1 · **Tasks:** T-020, T-021, T-022, T-023
- **ADRs:** ADR-0002, ADR-0012, ADR-0013
- **Arquitetura:** `arch.yaml#components.simulation`, `#strategies.profit_gain`, `#external_services.binance_rest.public_klines_sim`
- **Insumos:** UNIT-006 (problemas de comportamento), UNIT-007 (técnicas candidatas)

## Objetivo
Medir, sem capital real, o desempenho da `profit_gain` atual e de ≥ 50 variações de parâmetros de entrada, stoploss e stopwin (trailing) em várias moedas, para recomendar uma calibração a aplicar em E4.

## Escopo
- **Dados (T-020):** klines públicos da Binance (sem auth) para ≥ 8 moedas em 15m/1h/4h/1d — `simulation/data.py`, cache em `data/sim/*.csv.gz` (gitignored), download incremental respeitando rate limit.
- **Mock + motor (T-021):** `simulation/mock_exchange.py` (spot, ordens market, taxa 0,1%, slippage contra o usuário, fill real registrado) e `simulation/engine.py` (candle a candle, decisão no fechamento da vela de 15m, execução no open seguinte, sem look-ahead; indicadores em `simulation/indicators.py`). Fiel ao Porteiro e às saídas da profit_gain (`arch.yaml#strategies.profit_gain`). A camada de IA é substituída por regra/proxy determinístico documentado.
- **Grade (T-022):** `simulation/run_grid.py` — ≥ 50 variações (entrada × stop × stopwin) multi-moeda; split temporal IS 70% / OOS 30%; seleção só no IS.
- **Relatório (T-023):** `simulation/reports/sim-NNN-*.csv|json` + relatório com recomendação de parâmetros e riscos.

## Fora de escopo
- Alterar `binance_trade_bot/` (isso é UNIT-012/E4).
- Qualquer ordem real, testnet ou leitura de `user.cfg` (ADR-0003, ADR-0013).

## Critérios de aceite
- [ ] ≥ 8 moedas × 4 intervalos baixados e cacheados.
- [ ] Baseline reproduz a lógica atual (parâmetros de `arch.yaml#strategies.profit_gain`) e diferenças conhecidas para o live estão documentadas (ex.: vela aberta vs. fechada).
- [ ] ≥ 50 variações executadas; métricas por variação × moeda × segmento (IS/OOS): retorno, win rate, drawdown, nº de trades, profit factor.
- [ ] Recomendação justificada por OOS, com custo (taxa+slippage) incluído.
- [ ] Decisão do Micael registrada antes de E4.
