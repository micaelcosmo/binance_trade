# ADR-0009 · Destino do legado (SQLAlchemy, estratégias default/multiple_coins, api_server, backtest upstream)

- **Status:** Deferred (Micael adiou a decisão)
- **Data:** 2026-07
- **Origem:** ex-planning §5 Fase E, §6 (`adr/0002-legacy-fate.md`, status deferred), §8

## Contexto
A `profit_gain` persiste em JSON e não usa o DB; `database.py`/models SQLAlchemy, `auto_trader.py`, `default_strategy.py`, `multiple_coins_strategy.py`, `api_server.py` e o `backtest.py` do upstream são peso morto para o fluxo atual (DEAD-01). O `painel.py` já foi decidido no ADR-0004. Análise de comportamento das estratégias legadas em UNIT-006.

## Decisão
Nenhuma por enquanto: **não mexer** no legado até decisão explícita.

## Opções em aberto
- Remover/arquivar o legado e isolar a `profit_gain`.
- Atualizar `default`/`multiple_coins` para o ecossistema (bot_status.json, stop, estado persistente).

## Consequências
- `binance_trade_bot/__init__.py` importa `backtest` (sqlitedict) → todo import do pacote, inclusive nos testes, exige deps completas.
- O boot do motor continua criando/migrando o DB SQLAlchemy.
