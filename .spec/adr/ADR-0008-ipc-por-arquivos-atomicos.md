# ADR-0008 · Comunicação UI ⇄ motor por arquivos (estado JSON + flags one-shot) com escrita atômica

- **Status:** Accepted
- **Data:** 2026-07 (contrato) · commit 89faec9 (atomicidade)
- **Origem:** ex-`contracts/state-and-flags.md`, ex-spec 003, ex-planning §3

## Contexto
O motor roda como processo separado da UI; falha na UI não pode derrubar o trading. A troca já era feita por arquivos, sem lock e sem schema explícito (DATA-01, DATA-02).

## Decisão
- Canal motor→UI: `bot_status.json` (sobrescrito por completo). Persistência: `profit_gain_state.json` (motor) e `gui_state.json` (UI).
- Canal UI→motor: `*.flag` one-shot (UI cria, consumidor lê e apaga).
- Toda escrita via `atomic_io` (tmp no mesmo diretório + fsync + `os.replace`); leitura mantém try/except.
- Contrato de fato congelado em `arch.yaml#data_contracts` e `#events`.

## Consequências
- Nenhum leitor observa arquivo parcial. Sem lock: continua last-writer-wins.
- Mudança de campo exige UNIT + atualização do `arch.yaml`.
- `painel.py` (deprecado) não foi migrado para escrita atômica.
