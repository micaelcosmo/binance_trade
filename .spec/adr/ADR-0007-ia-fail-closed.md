# ADR-0007 · Saída da IA é não-confiável: validação rígida e fail-closed

- **Status:** Accepted (implementado — UNIT-002)
- **Data:** 2026-07 · commit 206af01
- **Origem:** ex-spec 002 (princípio e §4)

## Contexto
`json.loads` direto da resposta do Gemini permitia tipos errados, ticker alucinado e confiança fora de faixa — num caminho que move capital real (AI-01).

## Decisão
- Toda saída passa por `normalize_verdict` (função pura em `binance_trade_bot/ai_validation.py`) antes de chegar à estratégia.
- Em qualquer anomalia: veto (`NENHUMA`/`HOLD`/`ERROR_503`) com `final_confidence = 0`. Sentinela de veto sempre força confiança 0.
- Correções são auditadas (`logger.warning`) sem vazar a chave.

## Consequências
- Pior caso vira "perdeu uma entrada", nunca "entrou errado".
- Vetos por validação precisam ser observáveis para não mascarar degradação da IA.
