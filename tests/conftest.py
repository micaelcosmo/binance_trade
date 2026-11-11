"""Fixtures compartilhadas dos testes da profit_gain (T-041).

Tudo offline (ADR-0013): cliente Binance falso sobre ``simulation.mock_exchange``,
IA substituída por stub, ``time.sleep`` neutralizado e diretório de trabalho
temporário em D:\\binance_trade_work\\tmp (o motor grava *_state.json e
bot_status.json no cwd — nunca no repo, nunca lendo o user.cfg real).
"""
import os
import tempfile
import types
import uuid

import pytest

from simulation.mock_exchange import MockExchange

WORK_TMP_ROOT = r"D:\binance_trade_work\tmp"


def _klines(price, n):
    """Velas sintéticas planas (formato get_klines da python-binance)."""
    rows = []
    for i in range(n):
        p = float(price)
        rows.append([i * 60000, str(p), str(p * 1.001), str(p * 0.999), str(p), "1000",
                     i * 60000 + 59999, "0", 10, "0", "0", "0"])
    return rows


class FakeBinanceClient:
    """Subconjunto da API da python-binance usado pela profit_gain, sobre MockExchange.

    ``calls`` registra a ordem das chamadas (nome, símbolo) para os testes de
    sequência (stop antes da mineração).
    """

    def __init__(self, exchange, prices, step_size="0.000001", order_response_mode="full"):
        self.exchange = exchange
        self.prices = dict(prices)          # ex.: {"ETHUSDT": 100.0}
        self.step_size = step_size
        self.order_response_mode = order_response_mode   # full | fills_only | empty
        self.calls = []
        self.orders = []

    def _price(self, symbol):
        return float(self.prices.get(symbol, 1.0))

    def get_ticker(self, symbol):
        self.calls.append(("get_ticker", symbol))
        p = self._price(symbol)
        return {"lastPrice": str(p), "priceChangePercent": "0.0", "openPrice": str(p),
                "lowPrice": str(p), "quoteVolume": "1000000"}

    def get_symbol_ticker(self, symbol):
        self.calls.append(("get_symbol_ticker", symbol))
        return {"price": str(self._price(symbol))}

    def get_klines(self, symbol, interval, limit):
        self.calls.append(("get_klines", symbol))
        return _klines(self._price(symbol), limit)

    def get_asset_balance(self, asset):
        self.calls.append(("get_asset_balance", asset))
        return {"free": str(self.exchange.balance(asset)), "locked": "0"}

    def get_account(self):
        self.calls.append(("get_account", None))
        return {"balances": [{"asset": a, "free": str(q), "locked": "0"}
                             for a, q in self.exchange.balances.items()]}

    def get_open_orders(self, symbol):
        return []

    def cancel_order(self, symbol, orderId):
        return {}

    def get_symbol_info(self, symbol):
        return {"filters": [{"filterType": "PRICE_FILTER", "tickSize": "0.01"},
                            {"filterType": "LOT_SIZE", "stepSize": self.step_size}]}

    def get_my_trades(self, symbol, limit=5):
        return []

    def create_order(self, symbol, side, type, quantity=None, quoteOrderQty=None):
        self.calls.append(("create_order", symbol, side))
        ref = self._price(symbol)
        if side == "BUY":
            fill = self.exchange.market_buy_quote(symbol, float(quoteOrderQty), ref)
        else:
            fill = self.exchange.market_sell_qty(symbol, float(quantity), ref)
        self.orders.append(fill)
        if self.order_response_mode == "empty":
            return {"symbol": symbol, "status": "FILLED"}
        response = {"symbol": symbol, "status": "FILLED",
                    "fills": [{"price": str(fill.price), "qty": str(fill.qty)}]}
        if self.order_response_mode == "full":
            response["executedQty"] = str(fill.qty)
            response["cummulativeQuoteQty"] = str(fill.quote)
        return response


class StubAnalyzer:
    """Substitui MarketAnalyzer (Gemini): sem rede, sempre veta."""

    def __init__(self, logger):
        self.batch_calls = []
        self.swap_calls = []

    def analyze_batch(self, payload):
        self.batch_calls.append(payload)
        return {"winning_coin": "NENHUMA", "final_confidence": 0, "decision_summary": "stub"}

    def analyze_swap(self, payload, *args):
        self.swap_calls.append(payload)
        return {"winning_coin": "HOLD", "final_confidence": 0, "decision_summary": "stub"}


@pytest.fixture
def work_dir(monkeypatch):
    os.makedirs(WORK_TMP_ROOT, exist_ok=True)
    path = tempfile.mkdtemp(prefix=f"pg_{uuid.uuid4().hex[:6]}_", dir=WORK_TMP_ROOT)
    monkeypatch.chdir(path)
    return path


@pytest.fixture
def make_strategy(work_dir, monkeypatch):
    """Fábrica: ``make_strategy(client, config=None)`` → Strategy offline."""
    import binance_trade_bot.strategies.profit_gain_strategy as pg

    monkeypatch.setattr(pg, "MarketAnalyzer", StubAnalyzer)
    monkeypatch.setattr(pg.time, "sleep", lambda *_: None)
    monkeypatch.setattr(pg.Strategy, "_get_current_version", lambda self: "vtest")

    def _factory(client, config=None, logger=None):
        if config is None:
            config = types.SimpleNamespace(BRIDGE="USDT", SUPPORTED_COIN_LIST=["BTC", "ETH", "SOL"])
        logger = logger or types.SimpleNamespace(
            info=lambda *a, **k: None, warning=lambda *a, **k: None, error=lambda *a, **k: None)
        manager = types.SimpleNamespace(binance_client=client)
        return pg.Strategy(manager, None, logger, config)

    return _factory


@pytest.fixture
def exchange():
    return MockExchange.with_balance(1000.0, fee_rate=0.001, slippage=0.001)
