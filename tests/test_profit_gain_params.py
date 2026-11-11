"""T-041: ProfitGainParams — defaults == valores históricos; override por [profit_gain]."""
import configparser
import dataclasses
import os

import pytest

from binance_trade_bot.strategies.profit_gain_params import (
    ProfitGainParams,
    load_profit_gain_params,
    params_from_legacy_config,
    resolve_params,
)

# Valores que estavam fixos no código antes da extração (UNIT-006/UNIT-012).
OLD_VALUES = {
    "atr_bottom_multiplier": 2.0,
    "bollinger_std_default": 2.0,
    "volume_15m_min_pct": 80.0,
    "ema21_max_distance_pct": -1.0,
    "change_24h_max_pct": 2.5,
    "swap_change_24h_max_pct": -0.5,
    "ai_min_confidence_entry": 90,
    "ai_min_confidence_swap": 95,
    "swap_min_candidates": 4,
    "ai_503_retry_seconds": 300.0,
    "trailing_activation_pct": 1.5,
    "trailing_drop_pct": 0.3,
    "atr_stop_multiplier": 4.0,
    "btc_stop_min_pct": 6.0,
    "btc_stop_max_pct": 10.5,
    "alt_stop_min_pct": 4.0,
    "base_stop_loss_pct": 7.0,
    "disaster_stop_pct": 15.0,
    "swap_min_hold_hours": 10.0,
    "swap_loss_min_pct": -0.15,
    "swap_loss_max_pct": -2.5,
    "ai_cooldown_minutes": 45.0,
    "daily_profit_target_pct": 5.0,
    "max_daily_trades": 3,
    "motor_cooldown_minutes_default": 15,
    "ui_override_cooldown_seconds": 60.0,
    "entry_balance_fraction": 0.99,
    "min_entry_balance": 5.1,
    "min_position_value": 5.0,
}

LEGACY_ENV_VARS = ["DAILY_PROFIT_TARGET_PCT", "MAX_DAILY_TRADES", "BASE_STOP_LOSS_PCT",
                   "DISASTER_STOP_PCT", "TRAILING_ACTIVATION_PCT", "TRAILING_DROP_PCT",
                   "AI_COOLDOWN_MINUTES"]


def test_defaults_match_historical_values():
    params = ProfitGainParams()
    assert dataclasses.asdict(params) == OLD_VALUES
    assert params.golden_rule_cooldown_seconds == 2700.0


def test_every_field_is_covered_by_old_values():
    assert {f.name for f in dataclasses.fields(ProfitGainParams)} == set(OLD_VALUES)


def test_strategy_with_default_config_keeps_old_attributes(make_strategy, exchange):
    from tests.conftest import FakeBinanceClient

    strat = make_strategy(FakeBinanceClient(exchange, {}))
    assert strat.params == ProfitGainParams()
    assert strat.daily_profit_target_pct == 5.0
    assert strat.max_daily_trades == 3
    assert strat.base_stop_loss_pct == 7.0
    assert strat.disaster_stop_pct == 15.0
    assert strat.trailing_activation_pct == 1.5
    assert strat.trailing_drop_pct == 0.3
    assert strat.golden_rule_cooldown_seconds == 2700.0
    assert strat.motor_cooldown_minutes == 15
    assert strat.bollinger_std == 2.0


def _parser(text):
    parser = configparser.ConfigParser()
    parser["DEFAULT"] = {"bridge": "USDT", "strategy": "profit_gain"}
    parser.read_string(text)
    return parser


def test_section_absent_returns_base():
    warnings = []
    params = load_profit_gain_params(_parser("[binance_user_config]\nbridge=USDT\n"), warn=warnings.append)
    assert params == ProfitGainParams()
    assert warnings == []


def test_invalid_values_fall_back_to_default_and_warn():
    warnings = []
    params = load_profit_gain_params(_parser(
        "[profit_gain]\n"
        "volume_15m_min_pct = abc\n"
        "ai_min_confidence_entry = 150\n"
        "max_daily_trades = 2.5\n"
        "atr_stop_multiplier =\n"
        "entry_balance_fraction = nan\n"
        "chave_que_nao_existe = 1\n"
    ), warn=warnings.append)
    assert params == ProfitGainParams()
    assert len(warnings) == 6
    # chaves herdadas do [DEFAULT] não são tratadas como desconhecidas
    assert not any("bridge" in w or "strategy" in w for w in warnings)


def test_legacy_attrs_then_section_precedence():
    legacy = type("Cfg", (), {"disaster_stop_pct": 12.0, "max_daily_trades": 5})()
    base = params_from_legacy_config(legacy)
    assert base.disaster_stop_pct == 12.0 and base.max_daily_trades == 5
    params = load_profit_gain_params(_parser("[profit_gain]\ndisaster_stop_pct = 14\n"), base=base)
    assert params.disaster_stop_pct == 14.0      # seção [profit_gain] vence
    assert params.max_daily_trades == 5          # legado preservado


def test_resolve_params_without_config_attr_uses_legacy_getattr():
    cfg = type("Cfg", (), {"trailing_drop_pct": 0.5})()
    assert resolve_params(cfg).trailing_drop_pct == 0.5
    assert resolve_params(object()) == ProfitGainParams()


@pytest.fixture
def clean_env(monkeypatch):
    for var in LEGACY_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_config_reads_temporary_user_cfg(work_dir, clean_env, capsys):
    """Config() real lendo um user.cfg TEMPORÁRIO criado no cwd de teste (nunca o do repo)."""
    assert os.path.abspath(work_dir).lower().startswith(r"d:\binance_trade_work\tmp")
    with open(os.path.join(work_dir, "user.cfg"), "w", encoding="utf-8") as fh:
        fh.write(
            "[binance_user_config]\n"
            "api_key=fake\napi_secret_key=fake\nbridge=USDT\n"
            "disaster_stop_pct=12.0\n"
            "\n[profit_gain]\n"
            "atr_stop_multiplier = 3.5\n"
            "swap_min_candidates = 2\n"
            "entry_balance_fraction = 0.5\n"
            "volume_15m_min_pct = muito\n"
        )
    from binance_trade_bot.config import Config

    cfg = Config()
    params = cfg.PROFIT_GAIN_PARAMS
    assert params.atr_stop_multiplier == 3.5
    assert params.swap_min_candidates == 2
    assert params.entry_balance_fraction == 0.5
    assert params.volume_15m_min_pct == 80.0     # inválido → default
    assert params.disaster_stop_pct == 12.0      # chave legada continua valendo
    assert "volume_15m_min_pct" in capsys.readouterr().out


def test_config_without_profit_gain_section_is_default(work_dir, clean_env):
    with open(os.path.join(work_dir, "user.cfg"), "w", encoding="utf-8") as fh:
        fh.write("[binance_user_config]\napi_key=fake\napi_secret_key=fake\n")
    from binance_trade_bot.config import Config

    assert Config().PROFIT_GAIN_PARAMS == ProfitGainParams()


def test_strategy_uses_overridden_params(make_strategy, exchange):
    from tests.conftest import FakeBinanceClient

    cfg = type("Cfg", (), {"BRIDGE": "USDT", "SUPPORTED_COIN_LIST": ["ETH"],
                           "PROFIT_GAIN_PARAMS": ProfitGainParams(trailing_activation_pct=2.0,
                                                                   disaster_stop_pct=10.0)})()
    strat = make_strategy(FakeBinanceClient(exchange, {}), config=cfg)
    assert strat.trailing_activation_pct == 2.0
    assert strat.disaster_stop_pct == 10.0
