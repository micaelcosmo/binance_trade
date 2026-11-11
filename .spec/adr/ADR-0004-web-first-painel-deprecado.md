# ADR-0004 · Web-first: `app.py` é a UI canônica; `painel.py` deprecado; deploy Docker

- **Status:** Accepted
- **Data:** 2026-07 (decisão) · 2026-10 (Docker, commit 51757a9)
- **Origem:** ex-planning §5 Fase D e §8; resolve parcialmente o antigo "legacy-fate" (ver ADR-0009)

## Contexto
Duas UIs (Tkinter `painel.py` e Flask `app.py`) mantinham cópias da lógica de flags/estado (ARCH-02), com drift garantido. Há plano de acesso remoto.

## Decisão
- Toda evolução de UI mira exclusivamente `app.py` + `templates/index.html`.
- `painel.py` está congelado e **morre na v3** (sem features; correção só de emergência).
- Deploy oficial via Docker (`Dockerfile` + `compose.yaml` na raiz): container do painel web; o motor sobe como subprocess pelo botão RUN; repo montado por bind mount.

## Consequências
- Funcionalidades que só existem no `painel.py` precisam ser portadas antes da remoção — hoje: consumo de `update_pending.flag` (git reset/pull), ver `arch.yaml#data_contracts.flags`.
- Fase D do roadmap: extrair a "linguagem de comandos" (flags) para um módulo único compartilhado.
