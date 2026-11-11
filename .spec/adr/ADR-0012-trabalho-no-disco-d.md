# ADR-0012 · Trabalho no disco D:

- **Status:** Accepted
- **Data:** 2026-11-10
- **Origem:** sessão E0–E4 (decisão D-002 relacionada, sobre apagar a cópia em C:)

## Contexto
O repositório estava em `C:\Users\...\Documents\binance_trade`. Simulações (klines em cache, relatórios) e ambientes virtuais ocupam espaço; o disco C: deve ficar livre de artefatos de desenvolvimento.

## Decisão
- Repositório de trabalho canônico: `D:\binance_trade` (Git Bash: `/d/binance_trade`).
- Python: `D:\binance_trade\.venv\Scripts\python.exe`.
- Temporários: `D:\binance_trade_work\tmp` (exportar `TMP`/`TEMP` para lá). Nada é escrito em C:.
- A cópia em C: está defasada; seu destino é a decisão D-002 do Micael.

## Consequências
- Caches de simulação ficam em `data/sim/` (gitignored) dentro de D:.
- O `.venv` de D: precisa de todas as deps (`requirements.txt`) para rodar a suíte de testes — hoje faltam (ex.: `sqlitedict`).
