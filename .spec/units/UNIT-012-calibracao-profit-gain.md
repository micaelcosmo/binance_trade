# UNIT-012 · Aplicar calibração na profit_gain (E4)

- **Status:** Draft (bloqueada por UNIT-010 e aprovação do Micael)
- **Épico:** E4 · **Prioridade:** 2 · **Task:** T-040
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

## Critérios de aceite
- [ ] Parâmetros aprovados pelo Micael (decisão registrada via `track.py decision`).
- [ ] Com defaults, motor se comporta exatamente como antes (teste com mock).
- [ ] Novas chaves documentadas em `user.cfg.exemple`; parse anti-crash no `config.py`.
- [ ] Invariantes preservadas: IA ≥ 90/95, stops com prioridade, fail-closed.
- [ ] Commit `feat(...)` com bump minor (ADR-0011).
