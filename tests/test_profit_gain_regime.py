"""T-040: gate de regime SMA200 diário da profit_gain (sim-001), com exchange mock.

- bloqueia abaixo da SMA, libera acima;
- fail-closed com histórico curto ou erro de rede;
- só velas diárias FECHADAS entram no cálculo;
- cache: 1 chamada de klines 1d por moeda por dia;
- regime_filter_sma200=False desliga (nenhuma chamada);
- aplicado no Porteiro (antes da IA) e no Tribunal de Swap.
"""
import time
import types

import pytest

from binance_trade_bot.strategies.profit_gain_params import ProfitGainParams
from tests.conftest import FakeBinanceClient, daily_klines

SYMBOL = "SOLUSDT"
DAY_MS = 86_400_000


def _now_ms():
    return int(time.time() * 1000)


def _closes(last, n=200, base=100.0):
    """n fechamentos: n-1 em ``base`` e o último em ``last``."""
    return [base] * (n - 1) + [last]


def _daily_calls(client, symbol=SYMBOL):
    return [c for c in client.calls if c[0] == "get_klines" and c[1] == symbol and c[2] == "1d"]


def _cfg(**overrides):
    return types.SimpleNamespace(BRIDGE="USDT", SUPPORTED_COIN_LIST=["SOL"],
                                 PROFIT_GAIN_PARAMS=ProfitGainParams(**overrides))


@pytest.fixture
def client(exchange):
    return FakeBinanceClient(exchange, {SYMBOL: 20.0, "ETHUSDT": 99.0, "BTCUSDT": 50000.0})


# ----------------------------------------------------------- gate unitário
def test_blocks_below_sma(make_strategy, client):
    client.daily_klines[SYMBOL] = daily_klines(_closes(90.0), _now_ms() - 1000)
    strat = make_strategy(client)
    payload = {}
    assert strat._regime_allows_entry(SYMBOL, payload) is False
    assert payload["above_sma200_daily"] is False
    assert payload["sma200_daily_distance_pct"] < 0


def test_allows_above_sma(make_strategy, client):
    client.daily_klines[SYMBOL] = daily_klines(_closes(120.0), _now_ms() - 1000)
    strat = make_strategy(client)
    payload = {}
    assert strat._regime_allows_entry(SYMBOL, payload) is True
    assert payload["above_sma200_daily"] is True
    # SMA = (199×100 + 120)/200 = 100,1 → distância ≈ +19,88%
    assert payload["sma200_daily_distance_pct"] == pytest.approx((120 - 100.1) / 100.1 * 100, abs=0.01)
    assert _daily_calls(client)[0] == ("get_klines", SYMBOL, "1d")


def test_fail_closed_with_short_history(make_strategy, client):
    client.daily_klines[SYMBOL] = daily_klines(_closes(150.0, n=150), _now_ms() - 1000)
    strat = make_strategy(client)
    payload = {}
    assert strat._regime_allows_entry(SYMBOL, payload) is False
    assert payload["above_sma200_daily"] is None
    assert "insuficiente" in strat._daily_regime(SYMBOL)["reason"]


def test_fail_closed_on_network_error_and_retries_later(make_strategy, client):
    client.daily_klines[SYMBOL] = ConnectionError("rede caiu")
    strat = make_strategy(client)
    t0 = time.time()
    assert strat._daily_regime(SYMBOL, now=t0)["ok"] is False
    assert strat._regime_allows_entry(SYMBOL) is False
    assert len(_daily_calls(client)) == 1                      # erro em cache curto
    client.daily_klines[SYMBOL] = daily_klines(_closes(120.0), _now_ms() - 1000)
    assert strat._daily_regime(SYMBOL, now=t0 + strat.REGIME_ERROR_RETRY_SECONDS + 1)["above"] is True
    assert len(_daily_calls(client)) == 2


def test_open_daily_candle_is_ignored(make_strategy, client):
    now_ms = _now_ms()
    closed = daily_klines(_closes(120.0), now_ms - 1000)
    open_candle = daily_klines([1.0], now_ms + DAY_MS // 2)    # vela do dia corrente, ainda aberta
    client.daily_klines[SYMBOL] = closed + open_candle
    strat = make_strategy(client)
    assert strat._regime_allows_entry(SYMBOL) is True          # o 1.0 da vela aberta não conta


def test_open_candle_does_not_complete_history(make_strategy, client):
    now_ms = _now_ms()
    client.daily_klines[SYMBOL] = (daily_klines(_closes(120.0, n=199), now_ms - 1000)
                                   + daily_klines([120.0], now_ms + DAY_MS // 2))
    strat = make_strategy(client)
    assert strat._regime_allows_entry(SYMBOL) is False         # 199 fechadas < 200 → fail-closed


def test_cache_one_call_per_day(make_strategy, client):
    client.daily_klines[SYMBOL] = daily_klines(_closes(120.0), _now_ms() - 1000)
    strat = make_strategy(client)
    # 00:30 UTC de um dia qualquer → expira na virada para o dia seguinte (+60 s)
    day_start = (_now_ms() // DAY_MS) * DAY_MS / 1000.0
    t0 = day_start + 1800
    for offset in (0, 60, 3600, 20 * 3600):
        strat._daily_regime(SYMBOL, now=t0 + offset)
    assert len(_daily_calls(client)) == 1
    strat._daily_regime(SYMBOL, now=day_start + 86400 + 120)   # dia UTC seguinte
    assert len(_daily_calls(client)) == 2


def test_flag_false_disables_gate(make_strategy, client):
    client.daily_klines[SYMBOL] = daily_klines(_closes(50.0), _now_ms() - 1000)
    strat = make_strategy(client, config=_cfg(regime_filter_sma200=False))
    payload = {}
    assert strat._regime_allows_entry(SYMBOL, payload) is True
    assert payload == {}
    assert _daily_calls(client) == []


def test_custom_period(make_strategy, client):
    client.daily_klines[SYMBOL] = daily_klines(_closes(120.0, n=60), _now_ms() - 1000)
    strat = make_strategy(client, config=_cfg(regime_sma_period=50))
    assert strat._regime_allows_entry(SYMBOL) is True


# ------------------------------------------------- integração no scan_market
def _porteiro_ok_payload(coin="SOL", price=20.0):
    """Payload que passa em todos os filtros do Porteiro."""
    return {
        "coin": coin, "current_price": price,
        "change_24h_pct": "-3.00%", "min_24h_change_pct": "-6.00%", "required_atr_bottom_pct": "-4.00%",
        "touched_lower_band_1h": True, "touched_lower_band_15m": False,
        "volume_15m_above_avg": True, "ema21_1h_distance_pct": "-2.00%",
        "suggested_atr_stop_loss": 5.0,
    }


@pytest.mark.parametrize("last_close, expect_ai", [(90.0, False), (120.0, True)])
def test_porteiro_gate_before_ai(make_strategy, client, last_close, expect_ai):
    client.daily_klines[SYMBOL] = daily_klines(_closes(last_close), _now_ms() - 1000)
    strat = make_strategy(client, config=_cfg())
    strat.get_enriched_data = lambda symbol: (_porteiro_ok_payload(), False)

    strat.scan_market()

    assert bool(strat.ai_agent.batch_calls) is expect_ai
    assert strat.last_dossier and "above_sma200_daily" in strat.last_dossier[0]


@pytest.mark.parametrize("last_close, expect_swap", [(90.0, False), (120.0, True)])
def test_tribunal_respects_gate(make_strategy, client, last_close, expect_swap):
    client.daily_klines[SYMBOL] = daily_klines(_closes(last_close), _now_ms() - 1000)
    strat = make_strategy(client, config=types.SimpleNamespace(
        BRIDGE="USDT", SUPPORTED_COIN_LIST=["ETH", "SOL"],
        PROFIT_GAIN_PARAMS=ProfitGainParams(swap_min_candidates=1)))
    strat.get_enriched_data = lambda symbol: (
        (_porteiro_ok_payload(), False) if symbol == SYMBOL else (None, False))
    # posição presa: ETH −1%, 11h, Tribunal liberado
    client.exchange.balances["ETH"] = 1.0
    strat.in_operation, strat.current_operation_coin = True, "ETH"
    strat.active_buy_price, strat.active_dynamic_stop_loss = 100.0, 5.0
    strat.operation_start_time = time.time() - 11 * 3600
    strat.last_switch_time = 0.0

    strat.scan_market()

    assert bool(strat.ai_agent.swap_calls) is expect_swap
    assert strat.in_operation                                   # stub ordena HOLD
