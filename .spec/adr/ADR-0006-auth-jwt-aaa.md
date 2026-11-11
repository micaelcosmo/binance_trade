# ADR-0006 · Autenticação do painel: JWT com mentalidade AAA, configurável via `user.cfg`

- **Status:** Accepted (decisão) · implementação pendente em UNIT-001
- **Data:** 2026-07
- **Origem:** ex-spec 001 (decisão-base de auth, §9.1)

## Contexto
O painel controla capital real (venda forçada, start/stop, git pull) e terá acesso remoto. Hoje nenhum evento exige autenticação.

## Decisão
- **Authentication:** login emite JWT (access + refresh opcional), verificado por assinatura/exp/iss em HTTP e no socket.
- **Authorization:** escopos no claim (`read`, `trade:control`, `trade:sell`, `system:update`) mapeados por evento (`arch.yaml#events`).
- **Accounting:** auditoria append-only NDJSON em `logs/audit.log` (ok/negado/erro), sem segredos.
- Parâmetros em nova seção `[panel_auth]` do `user.cfg`; precedência env > user.cfg > default seguro; prod sem segredo aborta o boot.
- TLS via proxy reverso ou túnel (hospedagem pendente).

## Consequências
- Nova dependência PyJWT. Single-user hoje, extensível a RBAC.
- Pendências do Micael listadas em UNIT-001 §9 (refresh, granularidade de escopos, hospedagem, auditoria de histórico).
