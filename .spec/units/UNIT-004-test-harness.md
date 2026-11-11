# UNIT-004 · Test harness (rede de segurança)

- **Status:** Implemented
- **Épico/fase:** Fase B (testes) · **Prioridade:** P1
- **ADRs:** ADR-0005, ADR-0013
- **Arquitetura:** `arch.yaml#quality`
- **Origem:** `.spec/specs/004-test-harness.md` (migrado integralmente em 2026-11-11, épico E1)

> **Situação atual:** Entregue (commit 281ee17) sem `tests/conftest.py` (previsto em §2). Importar `binance_trade_bot.*` executa o `__init__` do pacote (backtest → sqlitedict, binance), então a suíte exige todas as deps instaladas; no `.venv` de D: hoje a coleta falha por `sqlitedict` ausente. Para virar Verified: instalar deps no `.venv` de D: (ou isolar imports) e registrar como rodar/CI.

<details><summary>Metadados originais</summary>

Título original: `004 · Test Harness (Rede de Segurança)`

> **Status:** Implementado (inicial) · **Prioridade:** P1 · **Fase:** B (Testes)
> **Issue coberta:** `TEST-01` (ausência de testes)
> **Habilita:** UNIT-005 (refactor do motor com regressão garantida)

</details>

---

## 1. Objetivo

Estabelecer infraestrutura de teste (`pytest`) e cobrir com testes as **unidades puras** já entregues na Fase A, criando a rede de segurança mínima antes de tocar no motor.

### Estratégia: testar o que é puro primeiro
O motor (`profit_gain_strategy.py`) está acoplado à rede (Binance) e à IA (Gemini). Testá-lo direto exige mocks pesados (fica para depois do refactor UNIT-005). Então começamos pelas peças **dependency-free**:

```yaml
alvos_testaveis_agora:
  - binance_trade_bot/atomic_io.py       # UNIT-003
  - binance_trade_bot/ai_validation.py   # UNIT-002 (função pura extraída)
  - binance_trade_bot/config.py          # parse anti-crash (parcial)
```

---

## 2. Infra

```yaml
setup:
  runner: pytest
  dep: "pytest (adicionado a requirements.txt como dev dependency)"
  layout:
    tests/__init__.py
    tests/conftest.py          # fixtures compartilhadas + isolamento de cwd/tmp
    tests/test_atomic_io.py
    tests/test_ai_validation.py
  isolation:
    - "escritas atômicas testadas em tmp_path (não polui a raiz do projeto)"
    - "sem rede: nada de Binance/Gemini nos testes desta fase"
run: "python -m pytest -q"
```

---

## 3. Cobertura entregue

```yaml
test_atomic_io:
  - integridade do JSON escrito (round-trip)
  - sobrescrita segura (arquivo sempre válido)
  - ausência de .tmp órfãos após sucesso
  - destino pré-existente preservado quando dumps falha (objeto não-serializável)
test_ai_validation:   # mapeia V1..V10 da UNIT-002
  - confidence string "95" -> int 95        (V1 / AI-01a)
  - ticker fora do batch -> NENHUMA/HOLD     (V2 / AI-01b)
  - ticker sujo "  btcusdt " -> BTC          (V3 / AI-01c)
  - confidence 150 -> clamp 100              (V4 / AI-01d)
  - sem decision_summary -> texto padrão     (V5 / AI-01e)
  - '{}' -> veto seguro                      (V6 / AI-01f)
  - null / não-dict -> ERROR_503             (V7)
  - 'NENHUMA' com 99 -> confidence forçado 0 (V8 / consistência)
  - caminho feliz preservado                 (V10 regressão)
```

---

## 4. Próximos alvos (fases seguintes, fora deste doc)

```yaml
futuro:
  - "mock do binance.Client (fixtures de klines) -> testar get_enriched_data / gatekeeper"
  - "testar risk_manager (trailing/stop/desastre) com séries de preço sintéticas"
  - "só viável de forma limpa após o refactor UNIT-005 extrair essas unidades do arquivo-deus"
```

---

## 5. Definição de pronto

- [x] `pytest` roda (`python -m pytest -q`).
- [x] `atomic_io` e `ai_validation` cobertos e verdes.
- [x] Testes isolados (sem rede, sem poluir a raiz).
- [ ] CI/documentação de como rodar (follow-up leve).
