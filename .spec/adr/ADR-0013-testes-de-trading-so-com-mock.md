# ADR-0013 · Testes de trading só com mock (sem saldo real)

- **Status:** Accepted
- **Data:** 2026-11-10
- **Origem:** sessão E0–E4 (épico E2)

## Contexto
O bot opera com chaves de trade reais e a `profit_gain` entra all-in (99% do saldo). Calibrar entrada/stoploss/stopwin exige muitas execuções; fazer isso contra a conta real ou mesmo a testnet arrisca capital e credenciais.

## Decisão
- Teste, simulação e calibração de trading usam **somente** exchange mock (`simulation/mock_exchange.py`) alimentada por klines **públicos** (sem autenticação, `simulation/data.py`).
- Nenhum teste/simulação instancia `binance.Client` com chaves, cria ordem real, ou lê `user.cfg` (ADR-0003).
- Gemini também é mockado/estubado em testes; nada de chamada paga em suíte automatizada.
- Mock deve ser **conservador**: taxa padrão 0,1%, slippage contra o usuário, preço executado registrado no fill.

## Consequências
- Resultados de simulação são estimativas; antes de aplicar em produção (E4) passam por revisão do Micael.
- `testnet=True` não substitui o mock para calibração.
