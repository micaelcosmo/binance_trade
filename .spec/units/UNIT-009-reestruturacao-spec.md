# UNIT-009 · Reestruturação do `.spec/` (E1)

- **Status:** Implemented (aguarda revisão do Micael)
- **Épico:** E1 · **Prioridade:** 1 · **Tasks:** T-010 … T-014
- **ADRs:** ADR-0001, ADR-0010
- **Arquitetura:** `arch.yaml` (todo)

## Objetivo
Reduzir `.spec/` a: `README.md`, `arch.yaml` (único arquivo de arquitetura do projeto inteiro), `STATUS.md`/`TEMPO.md` (gerados), `adr/`, `units/` — sem perder informação dos documentos antigos.

## Escopo
- Migrar `planning/01-planning-overview.md`, `specs/001..004`, `contracts/state-and-flags.md`, `strategies/000` e `strategies/001` para ADRs, UNITs e `arch.yaml` (mapa de migração no `README.md`).
- Escrever `arch.yaml` a partir do código real (componentes, contratos, eventos, serviços externos, parâmetros da profit_gain, deploy, qualidade, dev tooling, roadmap, invariantes).
- Registrar ADRs novas: multi-agente (0010), commits/versão (0011), disco D: (0012), testes só com mock (0013).
- Criar UNITs Draft para E0, E2, E3, E4.
- Remover as pastas antigas.

## Critérios de aceite
- [x] `arch.yaml` carrega com `yaml.safe_load`.
- [x] Nenhum conteúdo dos documentos antigos descartado (specs e strategies migradas integralmente; planning/contrato distribuídos em ADR/arch.yaml/UNIT-005).
- [x] Pastas `planning/`, `specs/`, `contracts/`, `strategies/` removidas.
- [ ] Revisado pelo Micael.
