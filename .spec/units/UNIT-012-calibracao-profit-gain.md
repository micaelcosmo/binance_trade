# UNIT-012 · Aplicar calibração na profit_gain (E4)

- **Status:** Implemented (gate SMA200 aplicado; default ligado aguarda confirmação do Micael em D-407)
- **Épico:** E4 · **Prioridade:** 2 · **Tasks:** T-041 (parametrização, v3.10.0), T-040 (gate de regime)
- **Depende de:** UNIT-010 (relatório e recomendação aprovados)
- **ADRs:** ADR-0002, ADR-0003, ADR-0011, ADR-0013
- **Arquitetura:** `arch.yaml#strategies.profit_gain`, `#runtime.config.keys`

## Objetivo
Parametrizar a `profit_gain` e aplicar os parâmetros aprovados a partir da simulação, sem alterar a arquitetura de duas camadas.

## Escopo
- Tornar configuráveis (via `config.py` + documentação em `user.cfg.exemple`, nunca lendo o `user.cfg` real) os parâmetros hoje fixos no código que a simulação calibrar — candidatos: multiplicador do stop ATR (4×), clamps (BTC 6–10,5%; alts 4–`base_stop_loss_pct`), limiares do Porteiro (2×ATR, faixa 24h −disaster…+2,5%, volume 80%, EMA21 < −1%), tamanho de posição (99%).
- Defaults = comportamento atual (sem mudança implícita); valores calibrados entram como recomendação documentada / default novo só com aprovação.
- Atualizar `arch.yaml#strategies.profit_gain` com os valores vigentes.

## Fora de escopo
- Técnicas novas da UNIT-007 (cada uma exige UNIT própria e validação em simulação).
- Correções da UNIT-006 não cobertas pela calibração.

## O que foi aplicado (resultado da sim-001)

Referência: `simulation/reports/sim-001-calibracao.md` (ag-sim, T-020…T-023).

**Aplicado (T-040):** gate de regime **SMA200 diária do ativo**. Foi o único ajuste robusto da grade de 101 variações: melhorou IS e OOS, nos modos carteira e por moeda, e cortou quase todo o prejuízo da baixa de 2025Q4–2026Q2.
- **Regra:** só compra se o fechamento da última vela 1d **fechada** estiver acima da SMA(`regime_sma_period`) diária. É o mesmo cálculo do `gate_sma200="asset"` de `simulation/engine.py`.
- **Onde é aplicado:** nas candidatas do Porteiro **antes** da IA (economiza tokens) e no filtro de candidatas do Tribunal de Swap.
- **Fail-closed:** histórico < N velas fechadas (moeda nova) ou erro de rede bloqueia a candidata, com log uma vez por dia por moeda e motivo.
- **Cache:** em memória por símbolo até a próxima virada de dia UTC (≤ 24h, 1 chamada `get_klines(1d, N+5)` por dia por moeda, só para quem passou o resto do Porteiro). Erro de rede fica em cache só 15 min.
- **Dossiê:** ganhou `above_sma200_daily` e `sma200_daily_distance_pct`. O prompt da IA não muda, porque `_clean_payload_for_ai` usa lista branca de campos.
- **Params:** `regime_filter_sma200` (default `true`) e `regime_sma_period` (default `200`) em `[profit_gain]`.

**NÃO aplicados (decisão do orquestrador com base na sim-001):**
- `trailing_drop 0,2` e `stop_mult 3`: o ganho é marginal (0,05–0,1 p.p./trade, dentro do ruído). A combinação REC quebra com latência (carteira IS −80,8%) e com slippage de 0,2% (−75,3%).
- Demais alavancas da grade: neutras ou piores (TP fixo, AVWAP, timeout, veto ADX, RSI2 obrigatório).

**Ressalva da sim-001 (vale para o Micael):** mesmo com o gate, a carteira simulada fica perto do break-even ou negativa. O Porteiro atual não tem edge que pague taxa + slippage, a menos que a IA real filtre muito melhor que o oráculo mock (ver D-201).

## Critérios de aceite
- [ ] Parâmetros aprovados pelo Micael (decisão registrada via `track.py decision`): **D-407** aberta (gate ligado por padrão).
- [x] Com defaults, motor se comporta exatamente como antes (teste com mock), exceto o gate SMA200, que é ligado por padrão de propósito e só bloqueia compras (`tests/test_profit_gain_params.py`, `tests/test_profit_gain_regime.py`).
- [x] Novas chaves documentadas em `user.cfg.exemple` (seção `[profit_gain]`); parse anti-crash no `config.py`.
- [x] Invariantes preservadas: IA ≥ 90/95, stops com prioridade (agora avaliados antes da mineração), fail-closed (o gate bloqueia quando não há dados).
- [ ] Commit `feat(...)` com bump minor (ADR-0011).
