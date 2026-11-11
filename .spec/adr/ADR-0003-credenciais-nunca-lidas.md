# ADR-0003 · Credenciais nunca lidas, logadas ou versionadas

- **Status:** Accepted
- **Data:** 2026-07
- **Origem:** ex-planning (regra de ouro, §7), ex-spec 001 (SEC-02), commit a108e98

## Contexto
`user.cfg` guarda chaves da Binance (com permissão de trade) e do Google Gemini; `.env` pode guardar overrides. Vazamento = perda de capital.

## Decisão
- `user.cfg`, `.env` e qualquer `*.cfg`/`.env` real **nunca** são lidos, abertos, ecoados ou grepados por ferramentas/agentes; só os templates `*.exemple`.
- Quem lê `user.cfg` é o código em runtime (`config.py`; hoje também `models/ai_agent.py` para `GOOGLE_API_KEY`).
- `user.cfg`, `.env`, `*.json`, `*.flag`, `*.log` ficam no `.gitignore`. Novas chaves são documentadas em `user.cfg.exemple` / `.env.exemple` sem valores reais.
- Logs/auditoria nunca registram chaves, JWT, senha ou hash.
- A imagem Docker não carrega segredos (bind mount do host).

## Consequências
- Agentes documentam e estendem o parser sem conhecer valores.
- Auditoria de histórico git por segredos já commitados fica como tarefa opcional (pendência UNIT-001 §9).
