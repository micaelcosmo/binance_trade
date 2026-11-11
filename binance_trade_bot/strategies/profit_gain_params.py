"""Parâmetros de decisão/risco da estratégia profit_gain (T-041 / UNIT-012).

Todos os números mágicos de decisão e risco que antes estavam fixos em
``profit_gain_strategy.py`` vivem aqui como campos de ``ProfitGainParams``.
Os DEFAULTS são exatamente os valores que o motor usava antes da extração —
nenhuma mudança de comportamento implícita. Valores calibrados (UNIT-010/012)
só entram como default novo com aprovação do Micael.

Fontes de valor, em ordem de precedência (a última vence):
  1. defaults desta dataclass;
  2. chaves legadas de ``[binance_user_config]`` já lidas pelo ``config.py``
     (daily_profit_target_pct, max_daily_trades, base_stop_loss_pct,
     disaster_stop_pct, trailing_activation_pct, trailing_drop_pct,
     ai_cooldown_minutes) — continuam funcionando como sempre;
  3. seção opcional ``[profit_gain]`` do user.cfg.

Parse anti-crash: chave ausente → mantém o valor anterior; valor inválido
(não numérico, não finito ou fora da faixa sã) → mantém o valor anterior e
registra aviso. Nunca levanta exceção.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, fields, replace

PROFIT_GAIN_SECTION = "profit_gain"


@dataclass(frozen=True)
class ProfitGainParams:
    # ---------------------------------------------------------- Porteiro
    atr_bottom_multiplier: float = 2.0       # queda mínima 24h exigida = -(N × ATR% 1h)
    bollinger_std_default: float = 2.0       # desvio inicial (a flag bb_std da UI sobrescreve via estado)
    volume_15m_min_pct: float = 80.0         # volume da vela 15m ≥ X% da média das 10 anteriores
    ema21_max_distance_pct: float = -1.0     # preço precisa estar ABAIXO de X% da EMA21 (1h)
    change_24h_max_pct: float = 2.5          # variação 24h ≤ X% (limite inferior = -disaster_stop_pct)
    swap_change_24h_max_pct: float = -0.5    # Tribunal: candidata precisa ter variação 24h ≤ X%

    # ---------------------------------------------------------------- IA
    ai_min_confidence_entry: int = 90        # confiança mínima para compra
    ai_min_confidence_swap: int = 95         # confiança mínima para o Tribunal aprovar swap
    swap_min_candidates: int = 4             # nº mínimo de candidatas para convocar o Tribunal
    ai_503_retry_seconds: float = 300.0      # espera após IA sobrecarregada (ERROR_503)

    # ------------------------------------------------------------- Saída
    trailing_activation_pct: float = 1.5     # arma o trailing ao atingir +X% de pico
    trailing_drop_pct: float = 0.3           # vende ao recuar X p.p. do pico
    atr_stop_multiplier: float = 4.0         # stop dinâmico = N × ATR% 1h (antes dos clamps)
    btc_stop_min_pct: float = 6.0            # clamp do stop dinâmico para BTC
    btc_stop_max_pct: float = 10.5
    alt_stop_min_pct: float = 4.0            # clamp inferior das alts (teto = base_stop_loss_pct)
    base_stop_loss_pct: float = 7.0          # teto do stop das alts e fallback sem stop dinâmico
    disaster_stop_pct: float = 15.0          # guilhotina absoluta
    swap_min_hold_hours: float = 10.0        # Tribunal só após X horas de operação
    swap_loss_min_pct: float = -0.15         # Tribunal só com P/L abaixo de X% ...
    swap_loss_max_pct: float = -2.5          # ... e acima de Y% (abaixo disso só reinicia o relógio)
    ai_cooldown_minutes: float = 45.0        # intervalo do Tribunal / cooldown após veto da IA

    # --------------------------------------------------------- Disciplina
    daily_profit_target_pct: float = 5.0     # meta diária (hiberna até meia-noite)
    max_daily_trades: int = 3                # limite de trades por dia
    motor_cooldown_minutes_default: int = 15  # cooldown após veto do Porteiro (flag cooldown da UI sobrescreve)
    ui_override_cooldown_seconds: float = 60.0  # pausa após venda manual / +1 trade

    # ------------------------------------------------------------ Tamanho
    entry_balance_fraction: float = 0.99     # fração do saldo livre usada na entrada (all-in)
    min_entry_balance: float = 5.1           # saldo mínimo da bridge para tentar comprar
    min_position_value: float = 5.0          # valor mínimo (bridge) para considerar posição viva

    @property
    def golden_rule_cooldown_seconds(self) -> float:
        return float(self.ai_cooldown_minutes) * 60.0


# Faixas sãs (inclusive). Fora delas → valor rejeitado e mantido o anterior.
_BOUNDS = {
    "atr_bottom_multiplier": (0.0, 20.0),
    "bollinger_std_default": (0.1, 10.0),
    "volume_15m_min_pct": (0.0, 1000.0),
    "ema21_max_distance_pct": (-100.0, 100.0),
    "change_24h_max_pct": (-100.0, 1000.0),
    "swap_change_24h_max_pct": (-100.0, 1000.0),
    "ai_min_confidence_entry": (0, 100),
    "ai_min_confidence_swap": (0, 100),
    "swap_min_candidates": (1, 1000),
    "ai_503_retry_seconds": (0.0, 86400.0),
    "trailing_activation_pct": (0.0, 100.0),
    "trailing_drop_pct": (0.0, 100.0),
    "atr_stop_multiplier": (0.0, 50.0),
    "btc_stop_min_pct": (0.0, 100.0),
    "btc_stop_max_pct": (0.0, 100.0),
    "alt_stop_min_pct": (0.0, 100.0),
    "base_stop_loss_pct": (0.0, 100.0),
    "disaster_stop_pct": (0.0, 100.0),
    "swap_min_hold_hours": (0.0, 24.0 * 365),
    "swap_loss_min_pct": (-100.0, 0.0),
    "swap_loss_max_pct": (-100.0, 0.0),
    "ai_cooldown_minutes": (0.0, 24.0 * 60),
    "daily_profit_target_pct": (0.0, 1000.0),
    "max_daily_trades": (0, 1000),
    "motor_cooldown_minutes_default": (0, 24 * 60),
    "ui_override_cooldown_seconds": (0.0, 86400.0),
    "entry_balance_fraction": (0.01, 1.0),
    "min_entry_balance": (0.0, 1e9),
    "min_position_value": (0.0, 1e9),
}

# Chaves legadas de [binance_user_config] → atributo homônimo em Config.
LEGACY_CONFIG_ATTRS = (
    "daily_profit_target_pct",
    "max_daily_trades",
    "base_stop_loss_pct",
    "disaster_stop_pct",
    "trailing_activation_pct",
    "trailing_drop_pct",
    "ai_cooldown_minutes",
)


def _coerce(name, raw, kind):
    """Converte ``raw`` para ``kind`` validando finitude e faixa. Levanta ValueError."""
    text = str(raw).strip()
    if text == "":
        raise ValueError("vazio")
    if kind is int:
        as_float = float(text)
        if not math.isfinite(as_float) or as_float != int(as_float):
            raise ValueError("inteiro esperado")
        value = int(as_float)
    else:
        value = float(text)
        if not math.isfinite(value):
            raise ValueError("não finito")
    low, high = _BOUNDS.get(name, (-math.inf, math.inf))
    if not (low <= value <= high):
        raise ValueError(f"fora da faixa [{low}, {high}]")
    return value


def _field_kinds():
    return {f.name: (int if f.type in ("int", int) else float) for f in fields(ProfitGainParams)}


def _apply(base, values, origin, warn):
    kinds = _field_kinds()
    updates = {}
    for name, raw in values.items():
        if name not in kinds:
            warn(f"[profit_gain] chave desconhecida '{name}' em {origin} — ignorada.")
            continue
        try:
            updates[name] = _coerce(name, raw, kinds[name])
        except (TypeError, ValueError) as err:
            warn(f"[profit_gain] valor inválido para '{name}' em {origin} ({raw!r}: {err}) — "
                 f"mantendo {getattr(base, name)!r}.")
    return replace(base, **updates) if updates else base


def params_from_legacy_config(system_configuration, warn=print, base=None):
    """Monta params a partir dos atributos legados de ``Config`` (getattr seguro)."""
    base = base or ProfitGainParams()
    values = {}
    for name in LEGACY_CONFIG_ATTRS:
        if hasattr(system_configuration, name):
            values[name] = getattr(system_configuration, name)
    return _apply(base, values, "binance_user_config", warn)


def load_profit_gain_params(parser, base=None, warn=print, section=PROFIT_GAIN_SECTION):
    """Aplica a seção ``[profit_gain]`` de um ``ConfigParser`` sobre ``base``.

    Ignora as chaves herdadas de ``[DEFAULT]``. Seção ausente → ``base`` intacto.
    """
    base = base or ProfitGainParams()
    try:
        if parser is None or not parser.has_section(section):
            return base
        defaults = set(parser.defaults().keys())
        values = {key: parser.get(section, key, raw=True)
                  for key in parser[section] if key not in defaults}
    except Exception as err:  # parse anti-crash
        warn(f"[profit_gain] falha ao ler seção: {err} — usando valores anteriores.")
        return base
    return _apply(base, values, f"[{section}]", warn)


def resolve_params(system_configuration, warn=print):
    """Params efetivos para a estratégia: ``Config.PROFIT_GAIN_PARAMS`` se existir,
    senão derivados das chaves legadas (compatível com configs antigos/mocks)."""
    params = getattr(system_configuration, "PROFIT_GAIN_PARAMS", None)
    if isinstance(params, ProfitGainParams):
        return params
    return params_from_legacy_config(system_configuration, warn=warn)
