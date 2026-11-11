# ADR-0001 · Spec-driven development e estrutura do `.spec/`

- **Status:** Accepted (revisado em 2026-11-11 pelo épico E1)
- **Data:** 2026-07 (original) · 2026-11-11 (revisão)
- **Origem:** ex-`.spec/planning/01-planning-overview.md` §0

## Contexto
O projeto opera capital real e já acumulava dívida técnica (arquivo-deus, UI duplicada, segurança fraca). Mudanças precisavam ser rastreáveis e revisáveis pelo Micael antes de virar código. A primeira convenção (`planning/`, `specs/`, `contracts/`, `adr/`) espalhava arquitetura em vários documentos e duplicava contratos.

## Decisão
- Nada de código novo significativo sem uma **UNIT** correspondente.
- Estrutura única: `README.md`, `arch.yaml` (único arquivo de arquitetura do projeto inteiro), `adr/ADR-NNNN-kebab.md`, `units/UNIT-NNN-kebab.md`, `STATUS.md`/`TEMPO.md` (gerados por `devpanel/track.py`).
- Ciclo de vida de UNIT: `Draft → Approved (Micael) → Implemented → Verified`.
- Trechos de baixo nível (schemas, estados) em YAML para serem máquina-legíveis e diffáveis.

## Consequências
- Contratos de dados, componentes, eventos e parâmetros vivem só no `arch.yaml`; UNITs referenciam seções dele.
- Mudança de arquitetura exige atualizar `arch.yaml` no mesmo commit.
- Pastas `planning/`, `specs/`, `contracts/`, `strategies/` foram removidas; conteúdo migrado para ADRs/UNITs/`arch.yaml` (mapa no `README.md`).
