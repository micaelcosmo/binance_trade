"""T-041: saídas da profit_gain com exchange mock (sem rede, sem IA real).

- stop/trailing avaliados ANTES da mineração do mercado (UNIT-006 item 2);
- preço de compra = preço médio executado do fill (UNIT-006 item 3);
- trailing / stop ATR / disaster disparam nos limiares.
"""
import pytest

from tests.conftest import FakeBinanceClient

SYMBOL = "ETHUSDT"


def _open_position(strat, client, buy_price=100.0, qty=1.0, dynamic_stop=5.0, peak=0.0):
    """Coloca o motor em operação em ETH com saldo real na exchange mock."""
    client.exchange.balances["ETH"] = qty
    strat.in_operation = True
    strat.current_operation_coin = "ETH"
    strat.active_buy_price = buy_price
    strat.active_altcoin_quantity = qty
    strat.active_dynamic_stop_loss = dynamic_stop
    strat.peak_profit_pct = peak
    strat.operation_start_time = 1.0
    strat.last_switch_time = 9e18          # Tribunal fora de cogitação nestes testes


def _sells(client):
    return [c for c in client.calls if c[0] == "create_order" and c[2] == "SELL"]


# ------------------------------------------------------------ ordem do scan
def test_stop_is_evaluated_before_market_mining(make_strategy, exchange):
    client = FakeBinanceClient(exchange, {SYMBOL: 94.0, "BTCUSDT": 50000.0, "SOLUSDT": 20.0})
    strat = make_strategy(client)
    _open_position(strat, client, buy_price=100.0, dynamic_stop=5.0)

    strat.scan_market()

    sells = _sells(client)
    assert len(sells) == 1
    sell_idx = client.calls.index(sells[0])
    assert not any(c[0] == "get_klines" for c in client.calls[:sell_idx]), \
        "a venda do stop não pode esperar a mineração de klines"
    assert not strat.in_operation
    assert strat.daily_history[-1]["reason"] == "STOP_LOSS_DINAMICO"


def test_position_price_checked_before_klines_when_holding(make_strategy, exchange):
    client = FakeBinanceClient(exchange, {SYMBOL: 100.5, "BTCUSDT": 50000.0, "SOLUSDT": 20.0})
    strat = make_strategy(client)
    _open_position(strat, client, buy_price=100.0, dynamic_stop=5.0)

    strat.scan_market()

    assert _sells(client) == []
    assert strat.in_operation
    first_ticker = client.calls.index(("get_ticker", SYMBOL))
    first_klines = next(i for i, c in enumerate(client.calls) if c[0] == "get_klines")
    assert first_ticker < first_klines
    assert strat.active_monitor_drop_pct == pytest.approx(0.5)


# --------------------------------------------------------- limiares de saída
@pytest.mark.parametrize("price, dynamic_stop, peak, expected", [
    (95.1, 5.0, 0.0, None),                    # -4,9% com stop 5% → segura
    (94.9, 5.0, 0.0, "STOP_LOSS_DINAMICO"),    # -5,1% → stop ATR
    (93.1, 0.0, 0.0, None),                    # sem stop dinâmico → base 7%: -6,9% segura
    (92.9, 0.0, 0.0, "STOP_LOSS_DINAMICO"),    # -7,1% → base_stop_loss_pct
    (85.1, 20.0, 0.0, None),                   # -14,9% < disaster 15% e < stop 20%
    (84.9, 20.0, 0.0, "STOP_DESASTRE"),        # -15,1% → guilhotina vence
    (101.4, 5.0, 1.4, None),                   # pico 1,4% < ativação 1,5% → sem trailing
    (101.8, 5.0, 2.0, None),                   # recuo 0,2 p.p. < 0,3 → segura
    (101.6, 5.0, 2.0, "TAKE_PROFIT"),          # recuo 0,4 p.p. ≥ 0,3 → realiza
])
def test_exit_thresholds(make_strategy, exchange, price, dynamic_stop, peak, expected):
    client = FakeBinanceClient(exchange, {SYMBOL: price})
    strat = make_strategy(client)
    _open_position(strat, client, buy_price=100.0, dynamic_stop=dynamic_stop, peak=peak)

    result = strat._evaluate_open_position(SYMBOL)

    if expected is None:
        assert result["status"] == "hold"
        assert _sells(client) == []
        assert strat.in_operation
    else:
        assert result["status"] == "sold"
        assert len(_sells(client)) == 1
        assert strat.daily_history[-1]["reason"] == expected
        assert not strat.in_operation
        assert exchange.balance("ETH") == pytest.approx(0.0)


def test_trailing_tracks_new_peak(make_strategy, exchange):
    client = FakeBinanceClient(exchange, {SYMBOL: 103.0})
    strat = make_strategy(client)
    _open_position(strat, client, buy_price=100.0, peak=2.0)

    assert strat._evaluate_open_position(SYMBOL)["status"] == "hold"
    assert strat.peak_profit_pct == pytest.approx(3.0)
    # alvo = compra × (1 + (pico − recuo)/100)
    assert strat.active_target_price == pytest.approx(100.0 * (1 + 2.7 / 100))


def test_position_vanished_is_closed_without_order(make_strategy, exchange):
    client = FakeBinanceClient(exchange, {SYMBOL: 100.0})
    strat = make_strategy(client)
    _open_position(strat, client, qty=0.01)   # $1 < min_position_value

    assert strat._evaluate_open_position(SYMBOL)["status"] == "closed"
    assert _sells(client) == []
    assert not strat.in_operation


# ------------------------------------------------------------ preço do fill
@pytest.mark.parametrize("mode", ["full", "fills_only"])
def test_buy_price_is_average_executed_fill(make_strategy, exchange, mode):
    client = FakeBinanceClient(exchange, {SYMBOL: 100.0}, order_response_mode=mode)
    strat = make_strategy(client)

    assert strat.execute_real_trade("ETH", 100.0, 5.0) is True

    fill = client.orders[-1]
    assert fill.price == pytest.approx(100.1)            # slippage contra o usuário
    assert strat.active_buy_price == pytest.approx(fill.price)
    assert strat.active_buy_price != pytest.approx(100.0)
    assert strat.active_target_price == pytest.approx(fill.price * 1.015)
    assert strat.active_dynamic_stop_loss == 5.0


def test_buy_price_falls_back_to_observed_without_fill(make_strategy, exchange):
    client = FakeBinanceClient(exchange, {SYMBOL: 100.0}, order_response_mode="empty")
    strat = make_strategy(client)

    assert strat.execute_real_trade("ETH", 100.0, 5.0) is True
    assert strat.active_buy_price == pytest.approx(100.0)


def test_extract_avg_fill_price_weighted_fills(make_strategy, exchange):
    strat = make_strategy(FakeBinanceClient(exchange, {}))
    response = {"fills": [{"price": "10", "qty": "1"}, {"price": "13", "qty": "2"}]}
    assert strat._extract_avg_fill_price(response, 99.0) == pytest.approx(12.0)
    assert strat._extract_avg_fill_price({"executedQty": "2", "cummulativeQuoteQty": "25"}, 99.0) == pytest.approx(12.5)
    assert strat._extract_avg_fill_price(None, 99.0) == 99.0
    assert strat._extract_avg_fill_price({"fills": [{"price": "x"}]}, 99.0) == 99.0


def test_entry_uses_99_percent_of_balance(make_strategy, exchange):
    client = FakeBinanceClient(exchange, {SYMBOL: 100.0})
    strat = make_strategy(client)
    strat.execute_real_trade("ETH", 100.0, 5.0)
    assert client.orders[-1].quote == pytest.approx(990.0)
