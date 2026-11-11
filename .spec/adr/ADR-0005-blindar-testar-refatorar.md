# ADR-0005 · Ordem de evolução: blindar → testar → refatorar

- **Status:** Accepted (confirmado pelo Micael)
- **Data:** 2026-07
- **Origem:** ex-planning §5, §6, §8

## Contexto
O motor é um arquivo-deus (ARCH-01) sem testes (TEST-01) e o painel é inseguro (SEC-01). Refatorar primeiro seria cego; expandir primeiro aumentaria a superfície de risco.

## Decisão
Princípio "endurecer antes de expandir":
- **Fase A — Blindagem** (sem mudar comportamento): UNIT-001 (segurança), UNIT-002 (validação IA), UNIT-003 (I/O atômico), contrato de dados (`arch.yaml#data_contracts`).
- **Fase B — Rede de segurança**: UNIT-004 (pytest, fixtures, mocks).
- **Fase C — Refactor do motor**: UNIT-005 (depende de UNIT-004).
- **Fase D — Unificação de UI** (ADR-0004). **Fase E — Limpeza** (ADR-0009).

## Consequências
- SEC-01 é P0 e bloqueia qualquer exposição remota.
- Trabalho de estratégia (E2/E4) acontece sobre o motor atual, validado por simulação/mock (ADR-0013).
