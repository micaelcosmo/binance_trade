# UNIT-005 · Refactor do motor (quebrar o arquivo-deus `profit_gain_strategy.py`)

- **Status:** Draft
- **Épico/fase:** Fase C (refactor) · **Prioridade:** P2
- **Depende de:** UNIT-004 (rede de testes) · **Issue:** ARCH-01
- **ADRs:** ADR-0002, ADR-0005, ADR-0008
- **Arquitetura:** `arch.yaml#components.motor_profit_gain`, `#data_contracts`, `#strategies.profit_gain`
- **Origem:** ex-planning §4 (ARCH-01), §5 Fase B/C, §6 (backlog `005-engine-refactor.md`, nunca escrito)

## Objetivo
Quebrar `binance_trade_bot/strategies/profit_gain_strategy.py` (~1037 LOC: estado, indicadores, filtro, IA, execução, persistência e payload da UI na mesma classe) em colaboradores coesos e testáveis, **sem mudar comportamento**.

## Escopo — módulos propostos
```yaml
proposed_modules:
  indicators.py:   "cálculo puro de indicadores → dataclass/dict, sem efeitos colaterais"
  gatekeeper.py:   "regras do Porteiro Python (filtro determinístico, testável)"
  risk_manager.py: "trailing, stop dinâmico, stop desastre, decisão de venda"
  position.py:     "estado da operação + persistência (load/save)"
  ui_state.py:     "montagem do bot_status.json a partir do estado"
  strategy.py:     "orquestra os acima (fica fino)"
```

## Fora de escopo
- Mudar parâmetros/limiares (isso é UNIT-012).
- Corrigir os problemas de comportamento da UNIT-006 (cada um vira UNIT própria, após o refactor).
- Remover legado (ADR-0009).

## Pré-requisitos de teste (da antiga Fase B)
- Testes de unidade dos filtros matemáticos (`get_enriched_data`, condições do Porteiro) com klines fixos (fixtures).
- Testes do gestor de risco (trailing/stop/desastre) com séries de preço simuladas.
- Mock do cliente Binance + do agente de IA → testar `scan_market` sem rede (ADR-0013). O `simulation/mock_exchange.py` e `simulation/indicators.py` (E2) podem servir de base.

## Critérios de aceite
- [ ] Contratos `bot_status.json`, `profit_gain_state.json` e flags idênticos (`arch.yaml#data_contracts`).
- [ ] Decisões idênticas ao motor atual em replay de klines fixos (golden test).
- [ ] `gatekeeper` e `risk_manager` cobertos por testes puros.
- [ ] Invariantes de `arch.yaml#invariants` preservadas.
- [ ] `arch.yaml#components` atualizado.
- [ ] Revisado e aprovado pelo Micael.
