"""Testes da escrita atômica (spec 003 / DATA-02)."""

import glob
import json
import os

import pytest

from binance_trade_bot.atomic_io import atomic_write_json, atomic_write_text


def test_write_json_roundtrip(tmp_path):
    target = tmp_path / "state.json"
    payload = {"a": 1, "b": [1, 2, 3], "acento": "ção"}

    atomic_write_json(str(target), payload, ensure_ascii=False, indent=2)

    assert json.loads(target.read_text(encoding="utf-8")) == payload


def test_overwrite_keeps_file_valid(tmp_path):
    target = tmp_path / "state.json"
    atomic_write_json(str(target), {"v": 1})
    atomic_write_json(str(target), {"v": 2})

    assert json.loads(target.read_text(encoding="utf-8")) == {"v": 2}


def test_no_orphan_tmp_files(tmp_path):
    target = tmp_path / "status.json"
    for i in range(5):
        atomic_write_json(str(target), {"i": i})

    leftovers = glob.glob(str(tmp_path / ".tmp_*"))
    assert leftovers == [], f"arquivos temporários órfãos: {leftovers}"


def test_failed_dump_preserves_existing_file(tmp_path):
    target = tmp_path / "state.json"
    atomic_write_json(str(target), {"ok": True})

    # objeto não-serializável => json.dumps lança; destino deve permanecer intacto.
    with pytest.raises(TypeError):
        atomic_write_json(str(target), {"bad": object()})

    assert json.loads(target.read_text(encoding="utf-8")) == {"ok": True}
    assert glob.glob(str(tmp_path / ".tmp_*")) == []


def test_write_text_atomic(tmp_path):
    target = tmp_path / "cmd.flag"
    atomic_write_text(str(target), "trigger_manual_sell")

    assert target.read_text(encoding="utf-8") == "trigger_manual_sell"
