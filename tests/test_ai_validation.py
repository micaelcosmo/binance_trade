"""
Testes da validação da saída da IA (spec 002 / AI-01).
Mapeiam a matriz V1..V10 da spec.
"""

from binance_trade_bot.ai_validation import (
    SENTINEL_ERROR,
    SENTINEL_HOLD,
    SENTINEL_NONE,
    normalize_verdict,
)

BATCH = ["BTC", "SOL", "ADA"]


def test_v1_confidence_string_coerced():
    out = normalize_verdict(
        {"winning_coin": "BTC", "final_confidence": "95", "decision_summary": "ok"}, BATCH
    )
    assert out["final_confidence"] == 95
    assert isinstance(out["final_confidence"], int)


def test_v2_hallucinated_ticker_demoted_to_veto():
    out = normalize_verdict(
        {"winning_coin": "DOGE", "final_confidence": 92, "decision_summary": "x"}, BATCH
    )
    assert out["winning_coin"] == SENTINEL_NONE
    assert out["final_confidence"] == 0


def test_v2_swap_hallucination_uses_hold():
    out = normalize_verdict(
        {"winning_coin": "DOGE", "final_confidence": 99}, BATCH, mode="swap"
    )
    assert out["winning_coin"] == SENTINEL_HOLD


def test_v3_dirty_ticker_normalized():
    out = normalize_verdict(
        {"winning_coin": "  btcusdt ", "final_confidence": 91, "decision_summary": "y"}, BATCH
    )
    assert out["winning_coin"] == "BTC"


def test_v4_confidence_clamped():
    out = normalize_verdict({"winning_coin": "BTC", "final_confidence": 150}, BATCH)
    assert out["final_confidence"] == 100


def test_v5_missing_summary_gets_default():
    out = normalize_verdict({"winning_coin": "BTC", "final_confidence": 90}, BATCH)
    assert isinstance(out["decision_summary"], str)
    assert out["decision_summary"].strip() != ""


def test_v6_empty_dict_is_safe_veto():
    out = normalize_verdict({}, BATCH)
    assert out["winning_coin"] == SENTINEL_NONE
    assert out["final_confidence"] == 0


def test_v7_non_dict_is_error():
    assert normalize_verdict(None, BATCH)["winning_coin"] == SENTINEL_ERROR
    assert normalize_verdict("texto", BATCH)["winning_coin"] == SENTINEL_ERROR
    assert normalize_verdict(42, BATCH)["winning_coin"] == SENTINEL_ERROR


def test_v8_veto_forces_zero_confidence():
    out = normalize_verdict({"winning_coin": "NENHUMA", "final_confidence": 99}, BATCH)
    assert out["winning_coin"] == SENTINEL_NONE
    assert out["final_confidence"] == 0


def test_v9_garbage_confidence_becomes_zero():
    out = normalize_verdict({"winning_coin": "BTC", "final_confidence": "muito alta"}, BATCH)
    assert out["final_confidence"] == 0


def test_v10_happy_path_preserved():
    raw = {"winning_coin": "BTC", "final_confidence": 96, "decision_summary": "forte reversão"}
    out = normalize_verdict(raw, BATCH)
    assert out == {
        "winning_coin": "BTC",
        "final_confidence": 96,
        "decision_summary": "forte reversão",
    }


def test_audit_callback_receives_corrections():
    notes = []
    normalize_verdict(
        {"winning_coin": "DOGE", "final_confidence": 92}, BATCH, audit=notes.append
    )
    assert any("alucinacao" in n for n in notes)
