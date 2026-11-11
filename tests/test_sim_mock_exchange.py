"""Testes da exchange mock (sem rede)."""
import pytest

from simulation.mock_exchange import InsufficientBalance, MockExchange, round_trip_multiplier


def test_buy_applies_slippage_and_fee_in_base():
    ex = MockExchange.with_balance(1000.0, fee_rate=0.001, slippage=0.001)
    fill = ex.market_buy_quote("BTCUSDT", 1000.0, ref_price=100.0, ts=1)
    assert fill.price == pytest.approx(100.1)          # compra paga acima
    gross = 1000.0 / 100.1
    assert fill.fee == pytest.approx(gross * 0.001)
    assert ex.balance("BTC") == pytest.approx(gross * 0.999)
    assert ex.balance("USDT") == pytest.approx(0.0)
    assert ex.fills[-1].side == "BUY"


def test_sell_applies_slippage_and_fee_in_quote():
    ex = MockExchange.with_balance(0.0, fee_rate=0.001, slippage=0.002)
    ex.balances["ETH"] = 2.0
    fill = ex.market_sell_qty("ETHUSDT", 2.0, ref_price=50.0)
    assert fill.price == pytest.approx(49.9)           # venda recebe abaixo
    assert ex.balance("USDT") == pytest.approx(2 * 49.9 * 0.999)
    assert ex.balance("ETH") == pytest.approx(0.0)


def test_round_trip_flat_price_loses_fees_and_slippage():
    ex = MockExchange.with_balance(1000.0, fee_rate=0.001, slippage=0.0005)
    ex.market_buy_quote("SOLUSDT", 1000.0, 20.0)
    ex.sell_all("SOLUSDT", 20.0)
    assert ex.balance("USDT") == pytest.approx(1000.0 * round_trip_multiplier(0.001, 0.0005))
    assert ex.balance("USDT") < 1000.0 * (1 - 0.002)  # ~0,3% de custo total


def test_all_in_uses_99_percent():
    ex = MockExchange.with_balance(500.0, fee_rate=0.0, slippage=0.0)
    ex.buy_all_in("XRPUSDT", 1.0)
    assert ex.balance("USDT") == pytest.approx(5.0)
    assert ex.balance("XRP") == pytest.approx(495.0)


def test_rejects_insufficient_balance_and_min_notional():
    ex = MockExchange.with_balance(10.0)
    with pytest.raises(InsufficientBalance):
        ex.market_buy_quote("BTCUSDT", 20.0, 100.0)
    with pytest.raises(InsufficientBalance):
        ex.market_buy_quote("BTCUSDT", 4.0, 100.0)  # < 5 USDT
    with pytest.raises(InsufficientBalance):
        ex.market_sell_qty("BTCUSDT", 1.0, 100.0)


def test_equity_marks_to_market():
    ex = MockExchange.with_balance(100.0, fee_rate=0.0, slippage=0.0)
    ex.market_buy_quote("BTCUSDT", 50.0, 10.0)
    assert ex.equity({"BTC": 12.0}) == pytest.approx(50.0 + 5 * 12.0)
