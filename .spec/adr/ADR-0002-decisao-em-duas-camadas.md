# ADR-0002 · Decisão em duas camadas: matemática antes da IA

- **Status:** Accepted
- **Data:** 2026-07
- **Origem:** ex-planning §1, §3, §7 (previsto lá como `adr/0001-two-layer-decision.md`)

## Contexto
A IA (Gemini) é cara, probabilística e sujeita a alucinação. Submeter todo o mercado a ela gasta tokens e expõe decisões a "facas caindo" sem contexto. A separação "matemática primeiro, IA depois" foi apontada como a melhor decisão de design do projeto.

## Decisão
1. **Porteiro Python** (determinístico, barato) filtra candidatas: queda aguda validada por ATR, toque na banda inferior de Bollinger, volume, distância da EMA21 (regras em `arch.yaml#strategies.profit_gain.gatekeeper`).
2. **Comitê de IA** só avalia o lote já filtrado. Compra exige confiança **≥ 90%**; swap **≥ 95%**.
3. Stops (desastre, dinâmico, trailing) têm prioridade sobre qualquer decisão de IA.
4. O motor nunca depende da UI viva para operar/proteger a posição.

## Consequências
- Invariante de arquitetura (`arch.yaml#invariants`): a IA nunca decide sobre ativo fora do Porteiro.
- Custo de IA proporcional às oportunidades, não ao universo de moedas; menos alucinação.
- Evoluções (UNIT-007, UNIT-012) devem refinar o Porteiro ou o payload, nunca inverter a ordem.
